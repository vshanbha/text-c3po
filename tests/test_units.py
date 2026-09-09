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
