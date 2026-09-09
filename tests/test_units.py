"""Fast unit tests: pure logic, zero LLM calls, no Ollama daemon needed.

Covers languages.name_for_code, runtimes.ollama_client parsing/defaults,
and services.eval_harness scoring math (run_matrix runs against an injected
stub, never the network). Live-model coverage stays manual-only under
@pytest.mark.integration plus the eval-harness gate script.
"""

from text_c3po.languages import LANGUAGES, LANGUAGE_CODES, name_for_code
from text_c3po.runtimes.ollama_client import (
    _verbatim_names,
    check_ollama,
    list_models,
    pick_default_model,
)
from text_c3po.services.eval_harness import (
    MATRIX_LANGUAGES,
    SENTENCES,
    format_table,
    is_valid,
    passes_gate,
    run_matrix,
)


def test_languages_count_and_codes():
    assert len(LANGUAGES) == 23
    assert len(LANGUAGE_CODES) == 23
    assert {e["code"] for e in LANGUAGES} == set(LANGUAGE_CODES)


def test_name_for_code_known():
    assert name_for_code("de") == "German"
    assert name_for_code("zh") == "Chinese"
    assert name_for_code("en") == "English"


def test_name_for_code_round_trips_all():
    for entry in LANGUAGES:
        assert name_for_code(entry["code"]) == entry["name"]


def test_name_for_code_unknown_is_blank():
    assert name_for_code("xx") == ""
    assert name_for_code("") == ""
    assert name_for_code(None) == ""
    assert name_for_code("  ") == ""


def test_matrix_languages_are_known_names():
    known = {e["name"] for e in LANGUAGES}
    assert len(SENTENCES) == 5
    assert len(MATRIX_LANGUAGES) == 5
    assert set(MATRIX_LANGUAGES) <= known


def test_pick_default_model_prefers_lfm2():
    models = ["mistral:latest", "lfm2.5:latest", "qwen3.5:9b-mlx"]
    assert pick_default_model(models) == "lfm2.5:latest"


def test_pick_default_model_falls_back_to_first():
    assert pick_default_model(["mistral:latest"]) == "mistral:latest"


def test_pick_default_model_empty_or_bad():
    assert pick_default_model([]) is None
    assert pick_default_model(None) is None
    assert pick_default_model("lfm2.5:latest") is None


def test_verbatim_names_happy_path():
    payload = {"models": [{"name": "a"}, {"name": "b"}]}
    assert _verbatim_names(payload) == ["a", "b"]


def test_verbatim_names_malformed_is_none():
    assert _verbatim_names(None) is None
    assert _verbatim_names({}) is None
    assert _verbatim_names({"models": "nope"}) is None
    assert _verbatim_names({"models": [{"name": ""}]}) is None
    assert _verbatim_names({"models": [{}]}) is None


def test_is_valid_narrow_contract():
    assert is_valid({"formal": "x"}) is True
    assert is_valid({"error": "boom", "retryable": True}) is False
    assert is_valid("nope") is False
    assert is_valid(None) is False


def test_passes_gate_boundary():
    assert passes_gate(25, 25) is True
    assert passes_gate(24, 25) is True
    assert passes_gate(23, 25) is False
    assert passes_gate(0, 0) is False
    assert passes_gate(5, 0) is False


def test_run_matrix_stub_all_valid():
    stub = lambda t, lang, m: {"formal": "f"}  # noqa: E731 - zero LLM calls
    results = run_matrix(models=["m"], translate_fn=stub)
    assert results["m"]["valid"] == 25
    assert results["m"]["total"] == 25
    assert results["m"]["failures"] == []
    assert all(v == 5 for v in results["m"]["per_language"].values())


def test_run_matrix_stub_counts_failures_per_cell():
    def stub(text, lang, model):
        if lang == "Hindi":
            return {"error": "x", "retryable": True}
        return {"formal": "f"}

    results = run_matrix(models=["m"], translate_fn=stub)
    assert results["m"]["valid"] == 20
    assert results["m"]["per_language"]["Hindi"] == 0
    assert len(results["m"]["failures"]) == 5
    assert passes_gate(results["m"]["valid"], results["m"]["total"]) is False


def test_run_matrix_stub_exception_counts_invalid():
    def stub(text, lang, model):
        raise RuntimeError("down")

    results = run_matrix(models=["m"], translate_fn=stub)
    assert results["m"]["valid"] == 0
    assert len(results["m"]["failures"]) == 25


def test_format_table_marks_pass_fail():
    results = {
        "good": {
            "valid": 25,
            "total": 25,
            "per_language": {lang: 5 for lang in MATRIX_LANGUAGES},
            "failures": [],
        },
        "bad": {
            "valid": 20,
            "total": 25,
            "per_language": {
                lang: (0 if lang == "Hindi" else 5) for lang in MATRIX_LANGUAGES
            },
            "failures": [],
        },
    }
    table = format_table(results)
    assert "| good " in table and "25/25" in table and "PASS" in table
    assert "| bad " in table and "20/25" in table and "FAIL" in table


def test_probe_helpers_never_raise_without_daemon(monkeypatch):
    import urllib.error

    def boom(*args, **kwargs):
        raise urllib.error.URLError("down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert check_ollama() == (False, [])
    assert list_models() == []


def test_apply_mode_visibility_exactly_one():
    from text_c3po.app import apply_mode_visibility

    class Fake:
        def __init__(self):
            self.visible = False

    views = {"text": Fake(), "live": Fake(), "file": Fake()}
    assert apply_mode_visibility(views, "live") == "live"
    assert views["live"].visible is True
    assert views["text"].visible is False
    assert views["file"].visible is False
    apply_mode_visibility(views, "file")
    assert views["file"].visible is True
    assert views["live"].visible is False


def test_find_project_root_points_at_repo():
    import os

    from text_c3po.paths import ensure_src_on_path, find_project_root

    root = find_project_root()
    assert os.path.isdir(os.path.join(root, "src", "text_c3po"))
    src = ensure_src_on_path()
    assert src.endswith("src")


def test_is_current_request_generation():
    from text_c3po.app import is_current_request

    assert is_current_request(3, 3) is True
    assert is_current_request(2, 3) is False


def test_set_translating_toggles_stop_and_progress():
    from text_c3po.app import _set_translating

    class Fake:
        def __init__(self):
            self.disabled = False
            self.visible = False
            self.value = ""

    class FakePage:
        def __init__(self):
            self.updated = 0

        def update(self):
            self.updated += 1

    refs = {
        "translate_button": Fake(),
        "stop_button": Fake(),
        "progress_ring": Fake(),
        "status_text": Fake(),
    }
    page = FakePage()
    _set_translating(refs, page, True, "Translating…")
    assert refs["translate_button"].disabled is True
    assert refs["stop_button"].visible is True
    assert refs["progress_ring"].visible is True
    assert refs["status_text"].value == "Translating…"
    _set_translating(refs, page, False, "")
    assert refs["translate_button"].disabled is False
    assert refs["stop_button"].visible is False
    assert page.updated >= 2


def test_cancel_inflight_never_raises_and_closes():
    from text_c3po.services.translation import _ACTIVE_LLMS, cancel_inflight

    class FakeClient:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeLLM:
        def __init__(self):
            self._client = FakeClient()

    fake = FakeLLM()
    try:
        _ACTIVE_LLMS.add(fake)
        assert cancel_inflight() >= 1
        assert fake._client.closed is True
    finally:
        _ACTIVE_LLMS.discard(fake)
    assert cancel_inflight() == 0


def _make_fake_llm(chunks, closed_box):
    class FakeStream:
        def __init__(self):
            self._it = iter(chunks)
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._it)

        def close(self):
            self.closed = True
            closed_box["closed"] = True

    class FakeClient:
        def close(self):
            pass

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self._client = FakeClient()
            closed_box["kwargs"] = kwargs

        def stream(self, messages):
            s = FakeStream()
            closed_box["stream"] = s
            return s

    return FakeLLM


def test_streaming_accumulates_split_json_single_prompt(monkeypatch):
    import threading

    import text_c3po.services.translation as tr

    closed_box = {}
    calls = {"prompts": 0}

    class Chunk:
        def __init__(self, content):
            self.content = content

    parts = [
        '{"formal": "Hal',
        'lo", "informal": "Hi", "origin_language": "English"}',
    ]
    monkeypatch.setattr(
        tr, "ChatOllama", _make_fake_llm([Chunk(p) for p in parts], closed_box)
    )
    orig_build = tr._build_request

    def counting_build(text, lang, parser):
        calls["prompts"] += 1
        return orig_build(text, lang, parser)

    monkeypatch.setattr(tr, "_build_request", counting_build)
    seen = []
    result = tr.translate_text(
        "Hello",
        "German",
        "m",
        on_token=lambda piece, total: seen.append((piece, total)),
        stop_event=threading.Event(),
    )
    assert result.get("formal") == "Hallo"
    assert result.get("origin_language") == "English"
    assert calls["prompts"] == 1  # one prompt, streamed — not multiple calls
    assert "".join(p for p, _ in seen) == "".join(parts)
    assert tr._ACTIVE_LLMS == set()
    assert tr._ACTIVE_STREAMS == set()


def test_streaming_stop_event_returns_cancelled(monkeypatch):
    import threading

    import text_c3po.services.translation as tr

    closed_box = {}

    class Chunk:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr(
        tr,
        "ChatOllama",
        _make_fake_llm([Chunk('{"formal": "x"}')], closed_box),
    )
    event = threading.Event()
    event.set()  # stopped before first token
    result = tr.translate_text("Hello", "German", "m", stop_event=event)
    assert result.get("cancelled") is True
    assert tr._ACTIVE_LLMS == set()
    assert tr._ACTIVE_STREAMS == set()


def test_text_view_deepl_refs_and_swap():
    from text_c3po.ui.text_view import build_text_view

    view = build_text_view()
    refs = view.data
    for key in (
        "input_field",
        "target_dropdown",
        "translate_button",
        "stop_button",
        "progress_ring",
        "status_text",
        "hint",
        "char_count",
        "swap_button",
        "copy_button",
        "style_toggle",
        "formal_text",
        "informal_text",
        "origin_caption",
    ):
        assert key in refs
    refs["input_field"].value = "hello"
    refs["formal_text"].value = "Hallo"
    refs["swap_button"].on_click(None)
    assert refs["input_field"].value == "Hallo"
    assert refs["formal_text"].value == "hello"
    assert refs["char_count"].value.startswith("5 / ")


def test_style_toggle_flips_pages_without_tabs():
    from text_c3po.ui.text_view import build_text_view

    view = build_text_view()
    refs = view.data
    assert "tabs" not in refs
    toggle = refs["style_toggle"]
    assert list(toggle.selected) == ["formal"]
    assert refs["formal_text"].visible is True
    assert refs["informal_text"].visible is False
    assert refs["copy_button"].tooltip == "Copy shown translation"

    class FakeControl:
        def __init__(self, selected):
            self.selected = selected

    class FakeEvent:
        def __init__(self, selected):
            self.control = FakeControl(selected)

    toggle.on_change(FakeEvent(["informal"]))
    assert refs["formal_text"].visible is False
    assert refs["informal_text"].visible is True
    toggle.on_change(FakeEvent(["formal"]))
    assert refs["formal_text"].visible is True
    assert refs["informal_text"].visible is False


def test_appbar_is_title_only():
    # Retry/Models live on the toolbar status row now; the bar carries no
    # actions. Still constructs on flet 0.86.5 (see TextButton lesson).
    from text_c3po.ui.top_strip import build_appbar

    bar = build_appbar(ollama_connected=False, on_retry=None, on_refresh_models=None)
    assert list(bar.actions or []) == []
    assert bar.data == {}


def test_toolbar_status_is_clickable_retry_with_hover_detail():
    # The dot/label is the retry control: click re-probes, hover explains.
    from text_c3po.ui.top_strip import build_toolbar

    tapped = []
    strip = build_toolbar(
        lambda e: None,
        ollama_connected=True,
        models=["m"],
        on_status_click=lambda e: tapped.append(True),
        ollama_url="http://127.0.0.1:11434",
    )
    assert set(strip.data.keys()) == {
        "toggle",
        "dot",
        "label",
        "status",
        "model_dropdown",
    }
    status = strip.data["status"]
    assert "127.0.0.1:11434" in (status.tooltip or "")
    assert "click" in (status.tooltip or "").lower()
    status.on_tap(None)
    assert tapped == [True]


def test_ollama_state_changed_only_on_flip():
    from text_c3po.app import ollama_state_changed

    assert ollama_state_changed((True, ["m"]), True, ["m"]) is False
    assert ollama_state_changed((True, ["m"]), False, []) is True
    assert ollama_state_changed((True, ["m"]), True, ["m", "n"]) is True


def test_toolbar_and_text_view_construct():
    # Smoke: every surface the app mounts must build headless. Catches
    # constructor API drift (e.g. padding helper renames) before launch.
    from text_c3po.ui.text_view import build_text_view
    from text_c3po.ui.top_strip import build_toolbar

    strip = build_toolbar(lambda e: None, ollama_connected=True, models=["m"])
    assert set(strip.data.keys()) == {
        "toggle",
        "dot",
        "label",
        "status",
        "model_dropdown",
    }
    view = build_text_view()
    assert view.data["stop_button"].visible is False
    assert view.data["progress_ring"].visible is False
