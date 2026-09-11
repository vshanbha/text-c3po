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


def test_all_languages_cover_constant_with_codes():
    from text_c3po.services.eval_harness import ALL_LANGUAGES, _code_for

    assert len(ALL_LANGUAGES) == 23
    assert set(ALL_LANGUAGES) == {e["name"] for e in LANGUAGES}
    for name in ALL_LANGUAGES:
        assert _code_for(name) != name


def test_resolve_languages_forms():
    from text_c3po.services.eval_harness import (
        ALL_LANGUAGES,
        MATRIX_LANGUAGES,
        resolve_languages,
    )

    assert resolve_languages(None) == MATRIX_LANGUAGES
    assert resolve_languages("matrix") == MATRIX_LANGUAGES
    assert resolve_languages("all") == ALL_LANGUAGES
    assert resolve_languages("German,French") == ["German", "French"]
    assert resolve_languages("German, German") == ["German"]
    assert resolve_languages("Klingon") is None
    assert resolve_languages("") == MATRIX_LANGUAGES
    assert resolve_languages(42) is None


def test_run_matrix_custom_languages_stubbed():
    from text_c3po.services.eval_harness import run_matrix

    def stub(text, target, model):
        return {"formal": text} if target == "German" else {"error": "x"}

    results = run_matrix(
        models=["m"], translate_fn=stub, languages=["German", "French"]
    )
    summary = results["m"]
    assert (summary["valid"], summary["total"]) == (5, 10)
    assert summary["per_language"] == {"German": 5, "French": 0}
    assert len(summary["failures"]) == 5


def test_format_table_custom_languages():
    from text_c3po.services.eval_harness import format_table

    table = format_table(
        {"m": {"valid": 5, "total": 10, "per_language": {"German": 5}}},
        ["German", "French"],
    )
    assert "| de | fr |" in table
    assert table.count("---") == 6


def test_record_results_custom_label(tmp_path):
    from text_c3po.services.eval_harness import record_results

    target = tmp_path / "r.md"
    record_results(
        {"m": {"valid": 10, "total": 10, "per_language": {}, "failures": []}},
        str(target),
        date="2026-09-11",
        languages=["German", "French"],
        label="E4 gate — 2x5 full matrix",
    )
    body = target.read_text()
    assert "## E4 gate — 2x5 full matrix (2026-09-11)" in body
    assert "2 sentences x 2 languages" not in body
    assert "5 sentences x 2 languages" in body


def test_main_rejects_unknown_languages(monkeypatch):
    import text_c3po.services.eval_harness as harness

    monkeypatch.setattr(harness, "check_ollama", lambda: (True, ["m"]))
    assert harness.main(["--languages", "Klingon"]) == harness.EXIT_ABORT
    parsed = harness._parse_args(["--languages", "all"])
    assert parsed.languages == "all"
    assert harness._parse_args([]).languages == "matrix"


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


def test_text_view_refs_and_char_count():
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
        "copy_button",
        "style_toggle",
        "formal_text",
        "informal_text",
        "origin_caption",
    ):
        assert key in refs
    assert "swap_button" not in refs  # no source selection: target-only UI
    refs["input_field"].value = "hello world, this is a test"
    refs["input_field"].on_change(None)
    assert refs["char_count"].value.startswith("27 / ")


def test_render_result_detected_language_wording():
    from text_c3po.app import _render_translation_result

    class Fake:
        def __init__(self):
            self.value = ""

    class FakePage:
        def update(self):
            pass

    refs = {
        "formal_text": Fake(),
        "informal_text": Fake(),
        "origin_caption": Fake(),
    }
    _render_translation_result(
        refs,
        FakePage(),
        {"formal": "Hallo", "informal": "Hi", "origin_language": "English"},
        lambda: None,
    )
    assert refs["formal_text"].value == "Hallo"
    assert refs["informal_text"].value == "Hi"
    assert refs["origin_caption"].value == "Detected: English"


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


def test_appbar_hosts_model_and_status_top_right():
    # Model picker plus status dot live top-right; dot click re-probes,
    # hover carries detail plus the fix. Constructs on flet 0.86.5.
    from text_c3po.ui.top_strip import build_appbar

    tapped = []
    bar = build_appbar(
        ollama_connected=True,
        models=["m"],
        selected_model="m",
        on_model_change=lambda e: None,
        on_status_click=lambda e: tapped.append(True),
        ollama_url="http://127.0.0.1:11434",
    )
    assert set(bar.data.keys()) == {"model_dropdown", "dot", "label", "status"}
    dropdown, status = bar.data["model_dropdown"], bar.data["status"]
    assert dropdown.value == "m" and dropdown.dense is True
    assert "model" in (dropdown.tooltip or "").lower()
    assert "127.0.0.1:11434" in (status.tooltip or "")
    assert bar.data["label"].value == "Connected"
    status.on_tap(None)
    assert tapped == [True]


def test_toolbar_is_toggle_only():
    from text_c3po.ui.top_strip import build_toolbar

    strip = build_toolbar(lambda e: None)
    assert set(strip.data.keys()) == {"toggle"}


def test_status_dot_down_is_error_red_with_fix_in_hover():
    from text_c3po.ui.top_strip import (
        DOWN_LABEL,
        ERROR_DOT,
        SUCCESS_DOT,
        refresh_ollama_status,
        status_detail,
    )

    assert "connected" in status_detail(True, "http://x").lower()
    down = status_detail(False)
    assert "ollama serve" in down and "click" in down.lower()

    class FakeDot:
        def __init__(self):
            self.bgcolor = None

    class FakeLabel:
        def __init__(self):
            self.value = None
            self.color = "sentinel"

    class FakeStatus:
        def __init__(self):
            self.tooltip = None

    class FakeStrip:
        def __init__(self, dot, label, status):
            self.data = {"dot": dot, "label": label, "status": status}

    dot, label, status = FakeDot(), FakeLabel(), FakeStatus()
    refresh_ollama_status(FakeStrip(dot, label, status), True, None, "http://x")
    assert dot.bgcolor == SUCCESS_DOT and "connected" in status.tooltip.lower()
    assert label.value == "Connected" and label.color is None
    refresh_ollama_status(FakeStrip(dot, label, status), False)
    assert dot.bgcolor == ERROR_DOT and "ollama serve" in status.tooltip
    assert label.value == DOWN_LABEL and label.color == ERROR_DOT


def test_disconnect_snackbar_carries_fix_and_retry():
    from text_c3po.app import _show_snackbar

    seen = []

    class FakeOverlay(list):
        pass

    class FakePage:
        def __init__(self):
            self.overlay = FakeOverlay()
            self.updated = 0

        def update(self):
            self.updated += 1

    page = FakePage()
    _show_snackbar(page, "Ollama disconnected — start it.", lambda: seen.append(True))
    assert len(page.overlay) == 1
    snack = page.overlay[0]
    assert "disconnected" in snack.content.value.lower()
    assert snack.action == "Retry"
    snack.on_action(None)
    assert seen == [True]
    assert page.updated >= 1


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

    strip = build_toolbar(lambda e: None)
    assert set(strip.data.keys()) == {"toggle"}
    view = build_text_view()
    assert view.data["stop_button"].visible is False
    assert view.data["progress_ring"].visible is False
    assert "copy_float" not in view.data and "style_float" not in view.data


def test_file_view_builds_picker_refs_headless():
    from text_c3po.ui.file_view import build_file_view

    view = build_file_view()
    assert set(view.data.keys()) == {
        "source_dropdown",
        "target_dropdown",
        "pick_button",
        "status_text",
        "result_text",
    }
    assert view.data["pick_button"].content == "Pick audio file"
    assert view.data["status_text"].value == ""
    seen = []
    wired = build_file_view(lambda e: seen.append(True))
    assert wired.data["pick_button"].on_click is not None


def test_normalize_and_as_text():
    from text_c3po.services.translation import _as_text, _normalize

    assert _as_text("x") == "x"
    assert _as_text(None) == ""
    assert _as_text(["a", "b"]) == "a, b"
    assert _as_text(3) == "3"
    out = _normalize(
        {"Formal": "Guten Tag", "INFORMAL": ["Hi"], "origin_language": "en"}
    )
    assert out == {"formal": "Guten Tag", "informal": "Hi", "origin_language": "en"}
    assert _normalize("shapeless") is None
    assert _normalize(None) is None


def test_extract_partial_formal_prefixes():
    from text_c3po.services.translation import extract_partial_formal

    assert extract_partial_formal("") == ""
    assert extract_partial_formal(None) == ""
    assert extract_partial_formal('{"other": 1}') == ""
    assert extract_partial_formal('{"formal"') == ""
    assert extract_partial_formal('{"formal": "Guten') == "Guten"
    assert extract_partial_formal('{"formal": "Hi\\nthere') == "Hi there"
    assert extract_partial_formal('{"formal": 42}') == ""


def test_chunk_text_shapes():
    from text_c3po.services.translation import _chunk_text

    class StrChunk:
        content = "hello"

    class BlockChunk:
        content = ["a", {"text": "b"}, None]

    assert _chunk_text(StrChunk()) == "hello"
    assert _chunk_text(BlockChunk()) == "ab"
    assert _chunk_text("raw") == ""
    assert _chunk_text(None) == ""


def test_close_stream_and_cancel_inflight_empty():
    from text_c3po.services.translation import _close_stream, cancel_inflight

    assert cancel_inflight() == 0
    seen = []

    class Closer:
        def close(self):
            seen.append(True)

    class Raiser:
        def close(self):
            raise OSError("stuck")

    _close_stream(Closer())
    _close_stream(Raiser())
    _close_stream(None)
    assert seen == [True]


def test_cancel_inflight_hits_registered_stream():
    from text_c3po.services import translation as tmod

    closed = []

    class Stream:
        def close(self):
            closed.append(True)

    tmod._ACTIVE_STREAMS.add(Stream())
    try:
        assert tmod.cancel_inflight() >= 1
    finally:
        tmod._ACTIVE_STREAMS.clear()
    assert closed


def test_parse_args_defaults_and_overrides():
    from text_c3po.services.eval_harness import _parse_args

    assert _parse_args([]).models is None
    parsed = _parse_args(["--models", "a", "b", "--research-path", "/tmp/r.md"])
    assert parsed.models == ["a", "b"]
    assert parsed.research_path == "/tmp/r.md"


def test_record_results_appends_dated_section(tmp_path):
    from text_c3po.services.eval_harness import record_results

    target = tmp_path / "research.md"
    target.write_text("# prior\n")
    results = {
        "m:latest": {
            "valid": 25,
            "total": 25,
            "per_language": {},
            "failures": [],
        }
    }
    assert record_results(results, str(target), date="2026-09-11") == str(target)
    body = target.read_text()
    assert body.startswith("# prior\n")
    assert "## E1 gate" in body and "2026-09-11" in body
    assert "m:latest" in body


def test_name_for_code_never_raises():
    from text_c3po.languages import name_for_code

    assert name_for_code(123) == ""
    assert name_for_code(object()) == ""


def test_services_lazy_loader_errors():
    import text_c3po.services as services

    try:
        services.__getattr__("no_such_entry")
        raised = False
    except AttributeError:
        raised = True
    assert raised is True
    assert callable(services.translate_text)
    assert callable(services.run_matrix)
    assert callable(services.transcribe_file)
    assert callable(services.VadChunker)
    assert callable(services.SessionController)
    assert callable(services.LiveRunner)


def _session_controller():
    import datetime

    from text_c3po.services.session import SessionController

    ticks = {"n": 0}

    def clock():
        ticks["n"] += 1
        return datetime.datetime(
            2026, 9, 11, 12, 0, ticks["n"], tzinfo=datetime.timezone.utc
        )

    def translate(text, target, model):
        if text == "boom":
            raise RuntimeError("llm down")
        if text == "badshape":
            return {"error": "Couldn't parse that one. Retry.", "retryable": True}
        return {"formal": "[{}] {}".format(target, text)}

    return SessionController(
        target_language="English", model="m", translate_fn=translate, clock=clock
    )


def test_session_ordering_and_timestamps():
    ctl = _session_controller()
    assert ctl.start_session() == 1
    assert ctl.is_active() is True
    assert ctl.post_utterance("Hallo", "de") is True
    assert ctl.post_utterance("Welt", "de") is True
    assert ctl.pending() == 2
    added = ctl.drain()
    assert [c["seq"] for c in added] == [1, 2]
    assert [c["translation"] for c in added] == ["[English] Hallo", "[English] Welt"]
    assert added[0]["at"] < added[1]["at"]
    assert added[0]["source_lang"] == "de"
    assert ctl.pending() == 0


def test_session_drops_blanks_and_closed_posts():
    ctl = _session_controller()
    assert ctl.post_utterance("early") is False
    ctl.start_session()
    assert ctl.post_utterance("") is False
    assert ctl.post_utterance("   ") is False
    assert ctl.post_utterance(None) is False
    ctl.end_session()
    assert ctl.is_active() is False
    assert ctl.post_utterance("late") is False
    assert ctl.mark_gap("x") is None
    assert ctl.drain() == []
    assert ctl.captions() == []


def test_session_translate_failures_become_error_captions():
    ctl = _session_controller()
    ctl.start_session()
    ctl.post_utterance("boom")
    ctl.post_utterance("badshape")
    ctl.post_utterance("ok")
    added = ctl.drain()
    assert [c["kind"] for c in added] == ["error", "error", "caption"]
    assert [c["seq"] for c in added] == [1, 2, 3]
    assert "Retry" in added[0]["text"]


def test_session_gaps_labeled_and_sequenced():
    ctl = _session_controller()
    ctl.start_session()
    ctl.post_utterance("a")
    ctl.drain()
    gap = ctl.mark_gap("restart")
    assert gap["kind"] == "gap" and gap["seq"] == 2
    assert "restart" in gap["text"]
    assert [c["seq"] for c in ctl.captions()] == [1, 2]


def test_session_restart_clears_and_bumps_id():
    ctl = _session_controller()
    ctl.start_session()
    ctl.post_utterance("a")
    ctl.drain()
    assert ctl.start_session() == 2
    assert ctl.captions() == []
    ctl.post_utterance("b")
    assert [c["seq"] for c in ctl.drain()] == [1]


def test_session_captions_are_copies():
    ctl = _session_controller()
    ctl.start_session()
    ctl.post_utterance("a")
    ctl.drain()
    snapshot = ctl.captions()
    snapshot[0]["text"] = "MUTATED"
    snapshot.clear()
    assert ctl.captions()[0]["text"] == "a"


def test_retry_caption_flips_and_fails():
    import datetime

    from text_c3po.services.session import SessionController

    states = {"fail": True}

    def flip(text, target, model):
        if states["fail"]:
            return {"error": "down", "retryable": True}
        return {"formal": "OK:" + text}

    clock = lambda: datetime.datetime(
        2026, 9, 11, 12, 0, 0, tzinfo=datetime.timezone.utc
    )
    ctl = SessionController(
        target_language="English", model="m", translate_fn=flip, clock=clock
    )
    ctl.start_session()
    ctl.post_utterance("Hallo")
    assert ctl.drain()[0]["kind"] == "error"
    assert ctl.retry_caption(999) is None
    still = ctl.retry_caption(1)
    assert still["kind"] == "error" and still["text"] == "down"
    states["fail"] = False
    fixed = ctl.retry_caption(1)
    assert fixed["kind"] == "caption"
    assert fixed["text"] == "Hallo" and fixed["translation"] == "OK:Hallo"
    assert ctl.captions()[0]["kind"] == "caption"
    ctl.end_session()
    ctl.post_utterance("after")
    ctl.drain()
    assert ctl.retry_caption(1)["kind"] == "caption"


def test_retry_caption_passthrough_and_sourceless():
    from text_c3po.services.session import SessionController

    ctl = SessionController(
        target_language="English",
        model="m",
        translate_fn=lambda text, target, model: {"formal": text},
    )
    ctl.start_session()
    ctl.post_utterance("ok")
    ctl.drain()
    assert ctl.retry_caption(1)["kind"] == "caption"
    ctl._captions.append({"seq": 99, "kind": "error"})
    assert ctl.retry_caption(99)["kind"] == "error"
    assert ctl.retry_caption("nope") is None


def test_session_concurrent_posts_drain_complete():
    import threading

    ctl = _session_controller()
    ctl.start_session()

    def post_many(prefix):
        for i in range(25):
            assert ctl.post_utterance("{}-{}".format(prefix, i)) is True

    threads = [threading.Thread(target=post_many, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert ctl.pending() == 100
    added = ctl.drain()
    assert len(added) == 100
    assert sorted(c["seq"] for c in added) == list(range(1, 101))


def test_verbatim_names_malformed():
    from text_c3po.runtimes.ollama_client import _verbatim_names

    assert _verbatim_names({"models": "nope"}) is None
    assert _verbatim_names({"models": [42]}) is None
    assert _verbatim_names({"models": [{"name": ""}]}) is None
    assert _verbatim_names({"models": [{"nope": 1}]}) is None
    assert _verbatim_names({"models": [{"name": "a"}, {"name": "b"}]}) == ["a", "b"]


def test_refresh_status_with_partial_refs():
    from text_c3po.ui.top_strip import refresh_model_picker, refresh_ollama_status

    class FakeStrip:
        def __init__(self, data):
            self.data = data

    refresh_ollama_status(FakeStrip({}), True)
    refresh_ollama_status(FakeStrip(None), False)
    refresh_ollama_status(object(), True)

    class FakeDropdown:
        pass

    holder = FakeStrip({"model_dropdown": FakeDropdown()})
    refresh_model_picker(holder, [], None)
    assert holder.data["model_dropdown"].value is None
    refresh_model_picker(FakeStrip({}), ["m"], "m")


def test_audio_file_generic_run_failure():
    import json

    from text_c3po.runtimes.audio_file import decode_to_wav

    def boom(argv):
        raise RuntimeError("sandbox denied")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"fake")
        path = tmp.name
    out = decode_to_wav(path, run_fn=boom)
    assert out["retryable"] is True
    assert "Could not decode" in out["error"]


def test_hostile_names_never_raise():
    from text_c3po.runtimes.audio_devices import has_blackhole, pick_default_device

    class EvilStr(str):
        def lower(self):
            raise RuntimeError("hostile")

    assert has_blackhole([EvilStr("mic")]) is False
    assert pick_default_device([EvilStr("mic")]) is None


def test_ollama_client_transport_failure(monkeypatch):
    import urllib.request

    from text_c3po.runtimes.ollama_client import check_ollama, list_models

    def down(*args, **kwargs):
        raise ConnectionRefusedError("down")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    assert check_ollama() == (False, [])
    assert list_models() == []


def test_ollama_client_malformed_body(monkeypatch):
    import io
    import urllib.request

    from text_c3po.runtimes.ollama_client import check_ollama

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"nope"))
    assert check_ollama() == (False, [])


def test_sounddevice_absent_yields_empty(monkeypatch):
    import sys

    from text_c3po.runtimes.audio_devices import list_devices

    monkeypatch.setitem(sys.modules, "sounddevice", None)
    assert list_devices() == []


def test_audio_devices_rejects_non_list():
    from text_c3po.runtimes.audio_devices import list_devices

    assert list_devices(query_fn=lambda: 42) == []


def test_paths_helpers(tmp_path, monkeypatch):
    import os
    import sys

    from text_c3po.paths import ensure_src_on_path, find_project_root

    marker = tmp_path / "src" / "text_c3po" / "services"
    marker.mkdir(parents=True)
    (marker / "eval_harness.py").write_text("# marker\n")
    # The walk starts at the start-path's parent (__file__ semantics).
    assert find_project_root(start=str(tmp_path / "sub" / "x.py")) == str(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert find_project_root(start=str(tmp_path / "nowhere")) == os.path.abspath(
        os.getcwd()
    )
    src = ensure_src_on_path()
    assert src in sys.path


def test_refresh_options_with_fakes():
    from text_c3po.ui.device_picker import refresh_device_options
    from text_c3po.ui.model_picker import refresh_model_options

    class FakeDropdown:
        pass

    for refresh in (refresh_device_options, refresh_model_options):
        fake = FakeDropdown()
        refresh(fake, ["a", "b"], "a")
        assert [o.key for o in fake.options] == ["a", "b"]
        assert fake.value == "a"


def test_top_strip_model_handler_and_detail():
    from text_c3po.ui.top_strip import build_appbar, status_detail

    seen = []
    bar = build_appbar(
        ollama_connected=True, models=["m"], on_model_change=lambda e: seen.append(True)
    )
    dropdown = bar.data["model_dropdown"]
    assert dropdown.on_select is not None
    dropdown.on_select(None)
    assert seen == [True]
    # The format-fallback branch is unreachable with the constant template
    # (extra args never raise str.format) — normal path asserted instead.
    assert status_detail(True, "http://x") == "Ollama connected at http://x."


def test_audio_file_junk_completed_and_isfile_raise(tmp_path, monkeypatch):
    import os

    from text_c3po.runtimes.audio_file import decode_to_wav

    src = tmp_path / "x.wav"
    src.write_bytes(b"fake")
    assert decode_to_wav(str(src), run_fn=lambda a: object())["retryable"] is True

    def boom(path):
        raise PermissionError("denied")

    monkeypatch.setattr(os.path, "isfile", boom)
    out = decode_to_wav("/tmp/x.wav", run_fn=lambda a: None)
    assert out["retryable"] is False


def test_audio_file_stderr_decode_failure(tmp_path):
    from text_c3po.runtimes.audio_file import decode_to_wav

    class BadErr:
        def decode(self, *a, **k):
            raise ValueError("bad")

    class Completed:
        returncode = 1
        stdout = b""
        stderr = BadErr()

    src = tmp_path / "c.mp3"
    src.write_bytes(b"fake")
    out = decode_to_wav(str(src), run_fn=lambda a: Completed())
    assert out["retryable"] is False
    assert "Could not decode" in out["error"]


def test_asr_stage_exceptions():
    from text_c3po.services.asr import _is_blank, transcribe_file

    assert _is_blank(None) is True
    assert _is_blank("   ") is True
    assert _is_blank("[blank_audio] x") is True
    assert _is_blank("Hallo") is False

    def raising_decode(path):
        raise OSError("disk gone")

    out = transcribe_file("/tmp/a.wav", "English", "m", decode_fn=raising_decode)
    assert out["retryable"] is True

    def raising_transcribe(wav):
        raise ConnectionError("gone")

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "m",
        decode_fn=lambda p: {"wav": b"W"},
        transcribe_fn=raising_transcribe,
    )
    assert out["retryable"] is True

    def raising_translate(text, target, model):
        raise RuntimeError("llm down")

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "m",
        decode_fn=lambda p: {"wav": b"W"},
        transcribe_fn=lambda w: {"text": "Hallo"},
        translate_fn=raising_translate,
    )
    assert out["retryable"] is True

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "m",
        decode_fn=lambda p: {"weird": 1},
        translate_fn=lambda *a: (_ for _ in ()).throw(AssertionError("unreached")),
    )
    assert out["retryable"] is True


def test_manager_stop_poll_raising_and_enter_raising(monkeypatch):
    from text_c3po.runtimes.process_manager import ProcessManager

    class PollRaiser:
        def poll(self):
            raise OSError("gone")

    mgr = ProcessManager(model_path=__file__)
    mgr._process = PollRaiser()
    mgr.stop()
    assert mgr._process is None

    mgr2 = ProcessManager(model_path=__file__)

    def boom():
        raise RuntimeError("no spawn")

    monkeypatch.setattr(mgr2, "start", boom)
    with mgr2:
        pass
    assert mgr2._process is None


def test_install_exit_cleanup_stops_then_resignals(monkeypatch):
    import os
    import signal as sig

    from text_c3po.runtimes.process_manager import install_exit_cleanup

    stops = []

    class FakeMgr:
        def stop(self):
            stops.append(True)

    handlers = {}

    def record(num, handler):
        handlers[num] = handler

    monkeypatch.setattr(sig, "signal", record)
    killed = []
    monkeypatch.setattr(os, "kill", lambda pid, num: killed.append((pid, num)))
    assert install_exit_cleanup(FakeMgr()) is True
    term = handlers.get(sig.SIGTERM)
    assert callable(term)
    term(sig.SIGTERM, None)
    assert stops
    assert handlers.get(sig.SIGTERM) is sig.SIG_DFL
    assert killed and killed[0][1] == sig.SIGTERM


def test_manager_build_command_isfile_raise(monkeypatch):
    import os

    from text_c3po.runtimes.process_manager import ProcessManager

    def boom(path):
        raise PermissionError("denied")

    monkeypatch.setattr(os.path, "isfile", boom)
    assert ProcessManager(model_path="/m.bin").build_command() is None


def test_whisper_object_wav():
    from text_c3po.runtimes.whisper_client import transcribe_wav

    assert transcribe_wav(object())["retryable"] is True


def test_probe_serving_bad_args():
    from text_c3po.runtimes.process_manager import probe_serving

    assert probe_serving("127.0.0.1", "notaport") is False
    assert probe_serving(None, None) is False


def _stub_devices():
    return [
        {
            "name": "MacBook Air Microphone",
            "max_input_channels": 1,
            "max_output_channels": 0,
        },
        {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 2},
        {
            "name": "MacBook Air Speakers",
            "max_input_channels": 0,
            "max_output_channels": 2,
        },
    ]


def test_list_devices_lists_inputs_verbatim():
    from text_c3po.runtimes.audio_devices import list_devices

    assert list_devices(query_fn=_stub_devices) == [
        "MacBook Air Microphone",
        "BlackHole 2ch",
    ]


def test_list_devices_never_raises():
    from text_c3po.runtimes.audio_devices import list_devices

    def boom():
        raise OSError("no PortAudio")

    assert list_devices(query_fn=boom) == []
    assert list_devices(query_fn=lambda: None) == []
    assert list_devices(query_fn=lambda: [{"name": "", "max_input_channels": 1}]) == []


def test_has_blackhole_case_insensitive():
    from text_c3po.runtimes.audio_devices import has_blackhole

    assert has_blackhole(["Mic", "BlackHole 2ch"]) is True
    assert has_blackhole(["mic", "blackhole 16ch"]) is True
    assert has_blackhole(["Mic", "Speakers"]) is False
    assert has_blackhole([]) is False
    assert has_blackhole(None) is False


def test_list_devices_skips_bad_entries():
    from text_c3po.runtimes.audio_devices import list_devices

    mixed = [
        {"name": "Mic", "max_input_channels": 1},
        {"name": "", "max_input_channels": 1},
        {"name": "Ghost"},
        "not-a-device",
        {"name": "Speakers", "max_input_channels": 0},
    ]
    assert list_devices(query_fn=lambda: mixed) == ["Mic"]


def test_pick_default_device_prefers_mic():
    from text_c3po.runtimes.audio_devices import pick_default_device

    assert pick_default_device(["MacBook Air Microphone", "BlackHole 2ch"]) == (
        "MacBook Air Microphone"
    )
    assert pick_default_device(["BlackHole 2ch", "USB Mic"]) == "USB Mic"
    assert pick_default_device(["BlackHole 2ch"]) == "BlackHole 2ch"
    assert pick_default_device([]) is None
    assert pick_default_device(None) is None


def test_live_view_builds_device_picker_headless():
    from text_c3po.ui.live_view import build_live_view

    view = build_live_view(["Mic", "BlackHole 2ch"], "Mic")
    dropdown = view.data["device_dropdown"]
    assert dropdown.value == "Mic"
    assert [o.key for o in dropdown.options] == ["Mic", "BlackHole 2ch"]
    empty = build_live_view([], None)
    assert empty.data["device_dropdown"].options == []
    seen = []
    wired = build_live_view(["Mic"], "Mic", lambda e: seen.append(True))
    assert wired.data["device_dropdown"].on_select is not None
    wired.data["device_dropdown"].on_select(None)
    assert seen == [True]
    assert "captions_pane" in wired.data


def _caption(seq, **over):
    base = {
        "seq": seq,
        "kind": "caption",
        "text": "Hallo",
        "translation": "Hello",
        "source_lang": "de",
        "at": "2026-09-11T12:00:{:02d}+00:00".format(seq),
    }
    base.update(over)
    return base


def test_captions_sync_appends_in_order_once():
    from text_c3po.ui.captions import build_captions_pane, sync_captions

    pane = build_captions_pane()
    assert sync_captions(pane, []) == 0
    assert sync_captions(pane, [_caption(1), _caption(2)]) == 2
    assert sync_captions(pane, [_caption(1), _caption(2), _caption(3)]) == 1
    feed = pane.data["list"]
    assert len(feed.controls) == 3
    assert pane.data["rendered"] == [1, 2, 3]
    assert sync_captions(None, [_caption(9)]) == 0
    assert sync_captions(pane, None) == 0


def test_captions_rows_carry_timestamps_and_announcements():
    from text_c3po.ui.captions import _announce, build_captions_pane, sync_captions

    pane = build_captions_pane()
    sync_captions(
        pane,
        [
            _caption(1),
            _caption(2, kind="gap", text="…(restart)…", translation=""),
            _caption(
                3, kind="error", text="Couldn't parse that one. Retry.", translation=""
            ),
        ],
    )
    rows = pane.data["list"].controls
    assert len(rows) == 3
    assert rows[0].label.startswith("Hello")
    assert "Gap in captions" in rows[1].label
    assert "failed" in rows[2].label
    assert _announce(None) == ""
    assert _announce({}) == ""


def test_captions_error_row_retry_and_follow():
    from text_c3po.ui.captions import (
        build_captions_pane,
        jump_to_latest,
        on_pane_scroll,
        sync_captions,
    )

    seen = []
    pane = build_captions_pane(on_retry=lambda seq: seen.append(seq))
    sync_captions(pane, [_caption(1, kind="error", text="Boom", translation="")])
    error_row = pane.data["list"].controls[0].content
    retry = [c for c in error_row.controls if getattr(c, "on_click", None)]
    assert len(retry) == 1
    retry[0].on_click(None)
    assert seen == [1]
    assert pane.data["list"].auto_scroll is True
    assert pane.data["jump"].visible is False
    on_pane_scroll(pane)
    assert pane.data["follow"]["on"] is False
    assert pane.data["jump"].visible is True
    assert pane.data["list"].auto_scroll is False
    jump_to_latest(pane)
    assert pane.data["follow"]["on"] is True
    assert pane.data["jump"].visible is False
    on_pane_scroll(pane)
    assert pane.data["follow"]["on"] is False
    jump_to_latest(object())
    on_pane_scroll(None)
    jump_to_latest(None)


def test_jump_async_awaits_scroll():
    import asyncio

    from text_c3po.ui.captions import (
        build_captions_pane,
        jump_to_latest_async,
        sync_captions,
    )

    async def drive():
        pane = build_captions_pane()
        sync_captions(pane, [_caption(1)])
        await asyncio.wait_for(jump_to_latest_async(pane), timeout=5)
        return pane

    pane = asyncio.run(drive())
    assert pane.data["follow"]["on"] is True
    assert pane.data["jump"].visible is False


def _vad_frame(value, n=8000):
    import struct

    return struct.pack("<" + "h" * n, *([value] * n))


def _wav_samples(payload):
    import io
    import struct
    import wave

    with wave.open(io.BytesIO(payload), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 16000
        raw = w.readframes(w.getnframes())
    return [s for (s,) in struct.iter_unpack("<h", raw)]


def test_frame_rms_constant_values():
    from text_c3po.services.vad import frame_rms

    assert frame_rms(_vad_frame(1000)) == 1000.0
    assert frame_rms(_vad_frame(-1000)) == 1000.0
    assert frame_rms(_vad_frame(0)) == 0.0
    assert frame_rms(b"") == 0.0
    assert frame_rms(_vad_frame(100)) == 100.0


def test_silence_threshold_boundary_is_speech():
    from text_c3po.services.vad import VadChunker

    speech, silence = _vad_frame(350), _vad_frame(349)
    chunker = VadChunker()
    assert chunker.feed(speech) == []
    assert chunker.feed(silence) == []
    assert chunker.flush() is not None
    chunker2 = VadChunker()
    assert chunker2.feed(silence) == []
    assert chunker2.flush() is None


def test_leading_silence_ignored():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker()
    for _ in range(3):
        assert chunker.feed(_vad_frame(0)) == []
    assert chunker.flush() is None


def test_two_silent_frames_flush_with_trailing_silence():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker()
    speech, silence = _vad_frame(1000), _vad_frame(0)
    assert chunker.feed(speech) == []
    assert chunker.feed(speech) == []
    assert chunker.feed(silence) == []
    out = chunker.feed(silence)
    assert len(out) == 1
    samples = _wav_samples(out[0])
    assert samples == [1000] * 16000 + [0] * 16000
    assert chunker.flush() is None


def test_single_silent_frame_does_not_flush():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker()
    assert chunker.feed(_vad_frame(1000)) == []
    assert chunker.feed(_vad_frame(0)) == []
    assert chunker.flush() is not None


def test_max_utterance_forces_flush_mid_speech():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker(max_utterance_s=1.0)
    assert chunker.feed(_vad_frame(1000)) == []
    out = chunker.feed(_vad_frame(1000))
    assert len(out) == 1
    assert _wav_samples(out[0]) == [1000] * 16000
    assert chunker.flush() is None


def test_state_resets_after_flush():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker()
    chunker.feed(_vad_frame(1000))
    chunker.feed(_vad_frame(0))
    first = chunker.feed(_vad_frame(0))
    assert len(first) == 1
    chunker.feed(_vad_frame(2000))
    chunker.feed(_vad_frame(0))
    second = chunker.feed(_vad_frame(0))
    assert len(second) == 1
    assert _wav_samples(second[0]) == [2000] * 8000 + [0] * 16000


def test_flush_emits_pending_without_trailing_silence():
    from text_c3po.services.vad import VadChunker

    chunker = VadChunker()
    chunker.feed(_vad_frame(1000))
    out = chunker.flush()
    assert out is not None
    assert _wav_samples(out) == [1000] * 8000
    assert chunker.flush() is None


def test_vad_never_raises_on_malformed_input():
    from text_c3po.services.vad import VadChunker, frame_rms, utterance_to_wav

    chunker = VadChunker(silence_rms="bad", max_utterance_s=None)
    assert chunker.feed(b"") == []
    assert chunker.feed(b"\x01") == []
    assert chunker.feed(None) == []
    assert chunker.flush() is None
    assert frame_rms(None) == 0.0
    assert isinstance(utterance_to_wav([0, 1, -1]), bytes)


class _FakeProcess:
    def __init__(self, alive=True, hang_on_wait=False):
        self._alive = alive
        self.hang_on_wait = hang_on_wait
        self.calls = []

    def poll(self):
        return None if self._alive else 0

    def terminate(self):
        self.calls.append("terminate")
        if not self.hang_on_wait:
            self._alive = False

    def kill(self):
        self.calls.append("kill")
        self._alive = False

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        if self.hang_on_wait and "kill" not in self.calls:
            raise TimeoutError("hung")
        self._alive = False
        return 0


def _manager(process=None, probe=None, model_path=None, **kwargs):
    from text_c3po.runtimes.process_manager import ProcessManager

    made = {}
    if model_path is None:
        model_path = __file__

    def factory(cmd, **kw):
        made["cmd"] = cmd
        if isinstance(process, Exception):
            raise process
        return process

    probes = {"calls": 0}

    def probe_fn():
        probes["calls"] += 1
        if isinstance(probe, list):
            return probe.pop(0) if probe else False
        return bool(probe)

    slept = []
    mgr = ProcessManager(
        model_path=model_path,
        popen_factory=factory,
        probe_fn=probe_fn,
        sleep_fn=slept.append,
        **kwargs,
    )
    return mgr, made, probes, slept


def test_resolve_language_code_uses_constant_or_auto():
    from text_c3po.runtimes.process_manager import resolve_language_code

    assert resolve_language_code("de") == "de"
    assert resolve_language_code("xx") == "auto"
    assert resolve_language_code(None) == "auto"
    assert resolve_language_code(" de ") == "de"


def test_build_command_transcribe_only():
    mgr, _, _, _ = _manager(process=_FakeProcess())
    cmd = mgr.build_command()
    assert cmd[0] == "whisper-server"
    assert "--translate" not in cmd
    assert cmd == [
        "whisper-server",
        "-m",
        mgr.model_path,
        "--host",
        "127.0.0.1",
        "--port",
        "9001",
        "--inference-path",
        "/inference",
        "-l",
        "auto",
    ]


def test_start_refuses_missing_model_without_spawning():
    from text_c3po.runtimes.process_manager import ProcessManager

    spawned = []
    mgr = ProcessManager(
        model_path="/does/not/exist.bin",
        popen_factory=lambda *a, **k: spawned.append(a) or _FakeProcess(),
    )
    assert mgr.start() is False
    assert spawned == []
    assert mgr.is_alive() is False


def test_start_spawn_failure_is_false_not_raise():
    mgr, made, _, _ = _manager(process=OSError("no binary"))
    assert mgr.start() is False
    assert "cmd" in made
    assert mgr._process is None
    assert mgr.is_alive() is False


def test_stop_terminates_and_forgets():
    mgr, _, _, _ = _manager(process=_FakeProcess())
    assert mgr.start() is True
    mgr.stop()
    assert mgr.is_alive() is False
    mgr.stop()


def test_stop_kills_hung_process():
    proc = _FakeProcess(hang_on_wait=True)
    mgr, _, _, _ = _manager(process=proc)
    assert mgr.start() is True
    mgr.stop()
    assert "terminate" in proc.calls
    assert "kill" in proc.calls
    assert mgr.is_alive() is False


def test_wait_ready_polls_until_serving():
    mgr, _, probes, slept = _manager(process=_FakeProcess(), probe=[False, False, True])
    assert mgr.wait_ready(timeout_s=5.0) is True
    assert probes["calls"] == 3
    assert len(slept) == 2


def test_wait_ready_times_out():
    mgr, _, probes, _ = _manager(process=_FakeProcess(), probe=[])
    assert mgr.wait_ready(timeout_s=0) is False
    assert probes["calls"] >= 1


def test_wait_ready_bad_timeout_forms():
    mgr, _, _, _ = _manager(process=_FakeProcess(), probe=True)
    assert mgr.wait_ready(timeout_s=None) is True
    assert mgr.wait_ready(timeout_s=-5) is True


def test_default_probe_uses_manager_port():
    import text_c3po.runtimes.process_manager as pm

    from text_c3po.runtimes.process_manager import ProcessManager

    seen = []
    orig = pm.probe_serving
    pm.probe_serving = lambda host, port=9001: seen.append((host, port)) or False
    try:
        mgr = ProcessManager(
            model_path=__file__,
            port=9999,
            sleep_fn=lambda s: None,
        )
        assert mgr.wait_ready(timeout_s=0) is False
    finally:
        pm.probe_serving = orig
    assert seen and seen[0] == ("127.0.0.1", 9999)


def test_default_model_path_resolution(tmp_path):
    from text_c3po.runtimes.process_manager import default_model_path

    assert default_model_path(search_dirs=[str(tmp_path)]) is None
    model = tmp_path / "ggml-small.bin"
    model.write_bytes(b"fake")
    assert default_model_path(search_dirs=[str(tmp_path)]) == str(model)
    assert default_model_path(
        search_dirs=[str(tmp_path)], env={"WHISPER_MODEL": str(model)}
    ) == str(model)
    assert default_model_path(
        search_dirs=[str(tmp_path)], env={"WHISPER_MODEL": "/nope.bin"}
    ) == str(model)
    # Root-anchored default search (shared paths helper, no __file__
    # joins): a models/ dir under the given root resolves, and anything
    # returned must exist.
    import os

    assert default_model_path(env={}, root=str(tmp_path / "empty")) is None
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "ggml-small.bin").write_bytes(b"fake")
    resolved = default_model_path(env={}, root=str(tmp_path))
    assert resolved == str(models_dir / "ggml-small.bin")
    assert os.path.isfile(resolved)


def test_ensure_running_reports_ready_restarted_failed():
    mgr, _, _, _ = _manager(process=_FakeProcess(), probe=True)
    assert mgr.start() is True
    assert mgr.ensure_running() == "ready"

    restarted, _, _, _ = _manager(process=_FakeProcess(), probe=[True])
    restarted._process = _FakeProcess(alive=False)
    assert restarted.ensure_running() == "restarted"

    dead, _, _, _ = _manager(process=_FakeProcess(), probe=[])
    dead._process = _FakeProcess(alive=False)
    dead.wait_ready = lambda timeout_s=0: False
    assert dead.ensure_running() == "failed"


def test_context_manager_stops_on_exit():
    mgr, _, _, _ = _manager(process=_FakeProcess(), probe=True)
    with mgr as entered:
        assert entered is mgr
        assert mgr.is_alive() is True
    assert mgr.is_alive() is False


class _FakeCompleted:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body


def test_decode_rejects_before_any_subprocess(tmp_path):
    from text_c3po.runtimes.audio_file import decode_to_wav

    txt = tmp_path / "song.txt"
    txt.write_bytes(b"notes")
    calls = []
    out = decode_to_wav(str(txt), run_fn=lambda a: calls.append(a))
    assert calls == []
    assert out["retryable"] is False
    assert "mp3" in out["error"]
    missing = decode_to_wav("/tmp/no-such-file.wav", run_fn=lambda a: calls.append(a))
    assert calls == []
    assert missing["retryable"] is False
    assert decode_to_wav("", run_fn=lambda a: calls.append(a))["retryable"] is False


def test_decode_to_wav_success_and_failures(tmp_path):
    from text_c3po.runtimes.audio_file import decode_to_wav

    src = tmp_path / "clip.MP3"
    src.write_bytes(b"fake")
    seen = []

    def ok(argv):
        seen.append(argv)
        return _FakeCompleted(returncode=0, stdout=b"RIFF....WAVE")

    out = decode_to_wav(str(src), run_fn=ok)
    assert out == {"wav": b"RIFF....WAVE"}
    assert seen[0][:3] == ["ffmpeg", "-hide_banner", "-loglevel"]
    assert "-ac" in seen[0] and "1" in seen[0]
    assert "-ar" in seen[0] and "16000" in seen[0]

    bad = decode_to_wav(
        str(src), run_fn=lambda a: _FakeCompleted(returncode=1, stderr=b"boom")
    )
    assert bad["retryable"] is False
    assert "boom" in bad["error"]

    def no_ffmpeg(argv):
        raise FileNotFoundError("ffmpeg")

    gone = decode_to_wav(str(src), run_fn=no_ffmpeg)
    assert gone["retryable"] is True
    assert "ffmpeg" in gone["error"].lower()

    empty = decode_to_wav(str(src), run_fn=lambda a: _FakeCompleted(stdout=b""))
    assert empty["retryable"] is False


def test_transcribe_wav_success_and_failures():
    import json

    from text_c3po.runtimes.whisper_client import transcribe_wav

    seen = []

    def ok(request):
        seen.append(request)
        return _FakeResponse(json.dumps({"text": "  hallo welt "}).encode())

    assert transcribe_wav(b"WAVE", urlopen_fn=ok) == {"text": "hallo welt"}
    assert "multipart/form-data" in seen[0].get_header("Content-type")

    def down(request):
        raise ConnectionRefusedError("down")

    failed = transcribe_wav(b"WAVE", urlopen_fn=down)
    assert failed == {
        "error": "Couldn't reach whisper-server. Retry.",
        "retryable": True,
    }
    assert (
        transcribe_wav(b"WAVE", urlopen_fn=lambda r: _FakeResponse(b"nope"))[
            "retryable"
        ]
        is True
    )
    assert (
        transcribe_wav(
            b"WAVE",
            urlopen_fn=lambda r: _FakeResponse(json.dumps({"nada": 1}).encode()),
        )["retryable"]
        is True
    )
    assert (
        transcribe_wav(
            b"WAVE",
            urlopen_fn=lambda r: _FakeResponse(json.dumps([1, 2]).encode()),
        )["retryable"]
        is True
    )
    assert (
        transcribe_wav(
            b"WAVE",
            urlopen_fn=lambda r: _FakeResponse(json.dumps({"text": 123}).encode()),
        )["retryable"]
        is True
    )
    assert transcribe_wav(b"")["retryable"] is True


def test_transcribe_file_end_to_end_with_stubs():
    from text_c3po.services.asr import transcribe_file

    calls = []

    def decode(path):
        calls.append(("decode", path))
        return {"wav": b"WAVE"}

    def transcribe(wav):
        calls.append(("transcribe", wav))
        return {"text": "Guten Morgen"}

    def translate(text, target, model):
        calls.append(("translate", text, target, model))
        return {"formal": "Good morning", "informal": "Morning!"}

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "lfm2.5:latest",
        decode_fn=decode,
        transcribe_fn=transcribe,
        translate_fn=translate,
    )
    assert out == {"formal": "Good morning", "informal": "Morning!"}
    assert calls == [
        ("decode", "/tmp/a.wav"),
        ("transcribe", b"WAVE"),
        ("translate", "Guten Morgen", "English", "lfm2.5:latest"),
    ]


def test_transcribe_file_short_circuits():
    from text_c3po.services.asr import transcribe_file

    calls = []

    def boom_decode(path):
        return {"error": "Unsupported container '.txt'", "retryable": False}

    def translate(text, target, model):
        calls.append(text)
        return {"formal": text}

    out = transcribe_file(
        "/tmp/a.txt", "English", "m", decode_fn=boom_decode, translate_fn=translate
    )
    assert out["retryable"] is False
    assert calls == []

    def blank_transcribe(wav):
        return {"text": " [BLANK_AUDIO]\n"}

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "m",
        decode_fn=lambda p: {"wav": b"WAVE"},
        transcribe_fn=blank_transcribe,
        translate_fn=translate,
    )
    assert out == {"error": "No speech found in that file.", "retryable": False}
    assert calls == []

    def down_transcribe(wav):
        return {"error": "Couldn't reach whisper-server. Retry.", "retryable": True}

    out = transcribe_file(
        "/tmp/a.wav",
        "English",
        "m",
        decode_fn=lambda p: {"wav": b"WAVE"},
        transcribe_fn=down_transcribe,
        translate_fn=translate,
    )
    assert out["retryable"] is True
    assert calls == []


def test_reset_pane_clears_for_new_session():
    from text_c3po.ui.captions import (
        build_captions_pane,
        on_pane_scroll,
        reset_pane,
        sync_captions,
    )

    pane = build_captions_pane()
    sync_captions(pane, [_caption(1), _caption(2)])
    on_pane_scroll(pane)
    reset_pane(pane)
    assert pane.data["list"].controls == []
    assert pane.data["rendered"] == []
    assert pane.data["follow"]["on"] is True
    assert pane.data["jump"].visible is False
    reset_pane(None)
    reset_pane(object())


def test_paint_status_with_fakes():
    from text_c3po.ui.status import LIVE_RED, paint_status, status_dot

    class Fake:
        pass

    dot, label = Fake(), Fake()
    paint_status(dot, label, LIVE_RED, "Live")
    assert (dot.bgcolor, label.value) == (LIVE_RED, "Live")
    paint_status(None, None, LIVE_RED, "x")
    paint_status(object(), object(), LIVE_RED, "x")
    assert status_dot(LIVE_RED).bgcolor == LIVE_RED


def test_live_view_session_controls():
    from text_c3po.ui.live_view import build_live_view

    view = build_live_view(["Mic"], "Mic")
    assert view.data["start_button"].content == "Start"
    assert view.data["stop_button"].visible is False
    assert view.data["capture_label"].value == "Idle"
    assert view.data["whisper_label"].value == "Whisper: ?"
    assert view.data["model_label"].value == "Model: ?"


class _FakeStream:
    def __init__(self, frames):
        self._frames = list(frames)
        self.started = False
        self.closed = False
        self.aborted = False

    def start(self):
        self.started = True

    def read(self, n):
        if not self._frames:
            raise RuntimeError("stream ended")
        return self._frames.pop(0), False

    def abort(self):
        self.aborted = True

    def stop(self):
        pass

    def close(self):
        self.closed = True


def _speech_frames(value=1000, n=2):
    return [_vad_frame(value) for _ in range(n)]


def _runner_controller():
    from text_c3po.services.session import SessionController

    return SessionController(
        target_language="English",
        model="m",
        translate_fn=lambda text, target, model: {"formal": text},
    )


def test_runner_posts_utterance_with_source_lang():
    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    fired = []
    stream = _FakeStream(_speech_frames() + [_vad_frame(0)] * 2)
    runner = LiveRunner(
        ctl,
        device="Mic",
        source_lang="German",
        transcribe_fn=lambda wav: {"text": "Hallo"},
        stream_factory=lambda device: stream,
        on_utterance=lambda: fired.append(True),
    )
    assert runner.is_running() is False
    assert runner.run() == 1
    assert stream.closed is True
    assert fired
    assert ctl.pending() == 1
    added = ctl.drain()
    assert added[0]["source_lang"] == "German"
    assert added[0]["translation"] == "Hallo"


def test_runner_gap_on_transcribe_failure():
    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    stream = _FakeStream(_speech_frames() + [_vad_frame(0)] * 2)

    def down(wav):
        raise ConnectionError("down")

    runner = LiveRunner(ctl, transcribe_fn=down, stream_factory=lambda device: stream)
    assert runner.run() == 0
    assert ctl.drain() == []
    gaps = [c for c in ctl.captions() if c["kind"] == "gap"]
    assert len(gaps) == 1
    assert "whisper" in gaps[0]["text"].lower()


def test_runner_no_stream_returns_zero(monkeypatch):
    import sys

    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()

    def no_factory(device):
        raise OSError("no PortAudio")

    assert LiveRunner(ctl, stream_factory=no_factory).run() == 0
    assert LiveRunner(ctl, stream_factory=lambda device: None).run() == 0
    # Default factory without sounddevice/PortAudio (monkeypatched away so
    # the test never touches real hardware): clean zero, no raise.
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    assert LiveRunner(ctl, transcribe_fn=lambda w: {"text": "x"}).run() == 0


def test_runner_stop_is_prompt():
    import threading
    import time

    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    stream = _FakeStream([_vad_frame(0)] * 100000)
    runner = LiveRunner(
        ctl,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: stream,
    )
    done = []
    worker = threading.Thread(target=lambda: done.append(runner.run()))
    started = time.monotonic()
    worker.start()
    time.sleep(0.3)
    assert runner.is_running() is True
    assert runner.run() == 0
    runner.request_stop()
    worker.join(timeout=5)
    assert done == [0]
    assert time.monotonic() - started < 5
    assert runner.is_running() is False
    assert stream.closed is True


def test_runner_stop_before_run():
    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    reads = []
    stream = _FakeStream([_vad_frame(0)])
    orig_read = stream.read
    stream.read = lambda n: reads.append(n) or orig_read(n)
    runner = LiveRunner(
        ctl,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: stream,
    )
    runner.request_stop()
    assert runner.run() == 0
    assert reads == []


def test_runner_reports_open_status():
    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    statuses = []
    stream = _FakeStream([_vad_frame(0)])
    runner = LiveRunner(
        ctl,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: stream,
        on_status=lambda opened, reason="": statuses.append((opened, reason)),
    )
    stream.read = lambda n: (_ for _ in ()).throw(RuntimeError("end"))
    assert runner.run() == 0
    assert statuses[0] == (True, "open")

    ctl2 = _runner_controller()
    ctl2.start_session()
    statuses2 = []
    runner2 = LiveRunner(
        ctl2,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: (_ for _ in ()).throw(OSError("nope")),
        on_status=lambda opened, reason="": statuses2.append((opened, reason)),
    )
    assert runner2.run() == 0
    assert statuses2 == [(False, "open-failed")]

    ctl3 = _runner_controller()
    ctl3.start_session()
    statuses3 = []
    runner3 = LiveRunner(
        ctl3,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: _FakeStream([]),
        on_status=lambda opened, reason="": statuses3.append((opened, reason)),
    )
    runner3.request_stop()
    assert runner3.run() == 0
    assert statuses3 == [(False, "stop")]


def test_runner_flushes_tail_on_stream_end():
    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    stream = _FakeStream(_speech_frames())
    runner = LiveRunner(
        ctl,
        transcribe_fn=lambda wav: {"text": "Hallo"},
        stream_factory=lambda device: stream,
    )
    assert runner.run() == 1
    assert ctl.drain()[0]["translation"] == "Hallo"


def test_runner_aborts_stream_on_stop():
    import threading
    import time

    from text_c3po.services.live_runner import LiveRunner

    ctl = _runner_controller()
    ctl.start_session()
    stream = _FakeStream([_vad_frame(0)] * 100000)
    runner = LiveRunner(
        ctl,
        transcribe_fn=lambda wav: {"text": "x"},
        stream_factory=lambda device: stream,
    )
    worker = threading.Thread(target=runner.run)
    worker.start()
    time.sleep(0.2)
    runner.request_stop()
    worker.join(timeout=5)
    assert stream.aborted is True
    assert stream.closed is True


def test_open_input_stream_closes_on_start_failure(monkeypatch):
    import sys
    import types

    from text_c3po.services.live_runner import open_input_stream

    made = []

    class FailingStream:
        def __init__(self, *args, **kwargs):
            made.append(self)
            self.closed = False

        def start(self):
            raise OSError("denied")

        def close(self):
            self.closed = True

    fake_sd = types.SimpleNamespace(InputStream=FailingStream)
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    try:
        open_input_stream(device="Mic")
        raised = False
    except OSError:
        raised = True
    assert raised is True
    assert made and made[0].closed is True


def test_concurrent_drains_keep_unique_seqs():
    import threading

    ctl = _session_controller()
    ctl.start_session()
    for i in range(50):
        assert ctl.post_utterance("u{}".format(i)) is True

    def drain_all():
        while ctl.pending():
            ctl.drain()

    threads = [threading.Thread(target=drain_all) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    seqs = sorted(c["seq"] for c in ctl.captions())
    assert seqs == list(range(1, 51))


def test_non_dict_translate_becomes_error_caption():
    from text_c3po.services.session import SessionController

    ctl = SessionController(
        target_language="English",
        model="m",
        translate_fn=lambda text, target, model: ["not", "a", "dict"],
    )
    ctl.start_session()
    ctl.post_utterance("Hallo")
    added = ctl.drain()
    assert len(added) == 1
    assert added[0]["kind"] == "error"
    assert "Retry" in added[0]["text"]


def test_retry_flips_row_in_place():
    from text_c3po.services.session import SessionController
    from text_c3po.ui.captions import build_captions_pane, sync_captions

    states = {"fail": True}

    def flip(text, target, model):
        if states["fail"]:
            return {"error": "down", "retryable": True}
        return {"formal": "OK:" + text}

    ctl = SessionController(target_language="English", model="m", translate_fn=flip)
    ctl.start_session()
    ctl.post_utterance("Hallo")
    ctl.drain()
    pane = build_captions_pane()
    assert sync_captions(pane, ctl.captions()) == 1
    assert len(pane.data["list"].controls) == 1
    states["fail"] = False
    assert ctl.retry_caption(1)["kind"] == "caption"
    assert sync_captions(pane, ctl.captions()) == 1
    assert len(pane.data["list"].controls) == 1
    body = pane.data["list"].controls[0].content.controls[1]
    assert body.value == "OK:Hallo"


def test_scroll_filter_user_only():
    from flet.controls.scrollable_control import ScrollType

    from text_c3po.ui.captions import build_captions_pane, on_pane_scroll, sync_captions

    class FakeEvent:
        def __init__(self, event_type):
            self.event_type = event_type

    pane = build_captions_pane()
    sync_captions(pane, [_caption(1)])
    on_pane_scroll(pane, FakeEvent(ScrollType.UPDATE))
    assert pane.data["follow"]["on"] is True
    assert pane.data["jump"].visible is False
    on_pane_scroll(pane, FakeEvent(ScrollType.USER))
    assert pane.data["follow"]["on"] is False
    assert pane.data["jump"].visible is True


def test_jump_empty_leaves_follow_armed():
    from text_c3po.ui.captions import (
        build_captions_pane,
        jump_to_latest,
        on_pane_scroll,
    )

    pane = build_captions_pane()
    jump_to_latest(pane)
    assert pane.data["follow"]["on"] is True
    on_pane_scroll(pane, None)
    assert pane.data["follow"]["on"] is False
