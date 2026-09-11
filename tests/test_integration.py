"""Live integration tests: real Ollama / whisper-server / ffmpeg over loopback.

MANUAL ONLY, SERIAL ONLY — never CI (pyproject deselects this module by
default; run explicitly with ``pytest -m integration``). One LLM request
at a time (single loaded model); lfm2.5-first; memory hogs such as
gemma4:e4b-mlx stay out. Every test skips readably when its service is
down so the module is green-or-skipped on any machine. The full 5x5
translation gate stays a manual script (see TEST-PLAN.md F1), not a test.
"""

import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration

MODEL = "lfm2.5:latest"


def _ollama_models():
    from text_c3po.runtimes.ollama_client import check_ollama

    try:
        ok, models = check_ollama()
    except Exception:
        return False, []
    return bool(ok), list(models or [])


def _require_ollama():
    ok, models = _ollama_models()
    if not ok:
        pytest.skip("ollama down at 127.0.0.1:11434")
    return models


def _require_model():
    models = _require_ollama()
    if MODEL not in models:
        pytest.skip("{} not installed".format(MODEL))
    return models


def _require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")


@pytest.fixture(scope="module")
def whisper_server():
    from text_c3po.runtimes.process_manager import (
        ProcessManager,
        default_model_path,
        probe_serving,
    )

    model = default_model_path()
    if not model:
        pytest.skip("no whisper model file resolved")
    if probe_serving():
        pytest.skip(
            "port 9001 already serving: refusing to test against a foreign server"
        )
    mgr = ProcessManager(model_path=model)
    try:
        assert mgr.start() is True
        assert mgr.wait_ready(timeout_s=60.0) is True
    except BaseException:
        # Setup asserts run before yield: without this the spawned server
        # leaks across pytest exit and squats :9001 for the next launch.
        try:
            mgr.stop()
        except Exception:
            pass
        raise
    yield mgr
    mgr.stop()


def test_ollama_probe_live():
    from text_c3po.runtimes.ollama_client import check_ollama

    ok, models = check_ollama()
    assert ok is True
    assert isinstance(models, list)


def test_translate_live_lfm25():
    _require_model()
    from text_c3po.services.translation import translate_text

    out = translate_text("Good morning", "German", MODEL)
    assert isinstance(out, dict) and "formal" in out, out
    formal = out["formal"].strip()
    assert formal
    # A translation must differ from the input: an English echo would
    # prove the target-language contract broken while staying JSON-valid.
    assert formal != "Good morning"


def test_whisper_lifecycle_live(whisper_server):
    assert whisper_server.ensure_running() == "ready"


def test_transcribe_silence_live(whisper_server):
    import io
    import struct
    import wave

    from text_c3po.runtimes.whisper_client import transcribe_wav

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<8000h", *([0] * 8000)))
    out = transcribe_wav(buf.getvalue())
    assert isinstance(out, dict) and "text" in out, out


def test_decode_live_ffmpeg(tmp_path):
    _require_ffmpeg()
    import wave

    from text_c3po.runtimes.audio_file import decode_to_wav

    src = str(tmp_path / "tone.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-ac",
            "1",
            "-ar",
            "16000",
            src,
        ],
        check=True,
        timeout=60,
    )
    out = decode_to_wav(src)
    assert "wav" in out, out
    with wave.open(__import__("io").BytesIO(out["wav"]), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 16000)
        assert w.getnframes() > 15000


def test_file_pipeline_shape_live(whisper_server, tmp_path):
    _require_model()
    _require_ffmpeg()
    from text_c3po.services.asr import transcribe_file

    src = str(tmp_path / "tone.wav")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            src,
        ],
        check=True,
        timeout=60,
    )

    # Stub translate with a real formal shape: decode + transcribe run
    # live. A sine tone may transcribe to text (flows into translate) or
    # to blank (no-speech error) depending on the model build — both are
    # honest pipeline outcomes; anything else is a real breakage.
    calls = []

    def stub_translate(text, target, model):
        calls.append(text)
        return {"formal": "stub:" + text.strip()}

    out = transcribe_file(src, "English", MODEL, translate_fn=stub_translate)
    assert isinstance(out, dict), out
    if calls:
        assert out.get("formal", "").startswith("stub:"), out
    else:
        assert out == {
            "error": "No speech found in that file.",
            "retryable": False,
        }, out
