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


_LIGHTHOUSE_PARAS = [
    "The old lighthouse stood at the edge of the cliff, its lamp long extinguished.",
    "Every morning the keeper climbed the ninety-seven steps to polish the great lens.",
    "Gulls nested in the eaves, and their cries echoed across the cold grey water.",
    "One autumn evening a storm rolled in, black clouds swallowing the horizon.",
    "The keeper lit the reserve lantern and kept watch until dawn broke clear.",
    "Ships in the channel below altered course, guided by that single point of light.",
    "By spring the lighthouse board sent engineers to restore the electric lamp.",
    "The village celebrated with music, bread, and wine on the harbour wall.",
    "Years later the keeper would say those were the finest days of his life.",
    "And the light never went dark again, not once in all the years that followed.",
]


def test_unsupported_target_echoes_input_live():
    """Documents current accepted behavior for targets lfm2.5 cannot render.

    Kannada/Marathi are offered in the 23-language picker, but lfm2.5
    echoes the English input back as valid JSON (silent wrong-language
    success — no error, no retry). Owner-accepted for now (2026-09-14);
    MODEL-scoped: owner-verified gemma4:e4b-mlx genuinely translates
    both, so this documents lfm2.5, not the software. If lfm2.5 itself
    ever translates, this test MUST fail so the acceptance is revisited
    — do not weaken it to match.
    """
    _require_model()
    from text_c3po.services.translation import translate_text

    text = "Good morning. How are you today?"
    for target in ("Kannada", "Marathi"):
        out = translate_text(text, target, MODEL)
        assert isinstance(out, dict) and not out.get("error"), out
        from text_c3po.services.eval_harness import normalize_text

        formal = (out.get("formal") or "").strip()
        assert formal, out
        assert normalize_text(formal) == normalize_text(text), out


def test_spanish_multipara_collapse_recreates_live():
    """Recreates the TEST-PLAN B6 early-stop flake against live lfm2.5.

    The 10-paragraph lighthouse text into Spanish collapses to the
    first-sentence-only formal (~3/5 runs, byte-identical when it fires)
    with a clean done_reason='stop'. Up to five serial attempts: the
    collapse must be observed at least once. MODEL-scoped to lfm2.5
    (owner-verified gemma4:e4b-mlx renders both scenarios fully). If
    this test starts failing because the collapse NEVER appears, the
    model improved — celebrate by deleting the test and closing B6,
    not by retrying harder.
    """
    _require_model()
    from text_c3po.services.translation import translate_text

    text = "\n\n".join(_LIGHTHOUSE_PARAS)
    assert len(text) > 700
    # Documented B6 signature: the byte-identical 78-char first sentence.
    # Length alone could misread a legitimate short-but-complete render.
    seen_collapse = False
    for _attempt in range(5):
        out = translate_text(text, "Spanish", MODEL)
        assert isinstance(out, dict) and not out.get("error"), out
        formal = (out.get("formal") or "").strip()
        assert formal, out
        if formal.startswith("El viejo faro se encontraba") and len(formal) < 150:
            seen_collapse = True
            break
    assert seen_collapse, (
        "collapse never appeared in 5 attempts — model may have improved; "
        "see TEST-PLAN B6"
    )
