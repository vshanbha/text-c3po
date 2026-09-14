"""Optional benchmark probe: unsupported-target echoes (ex TEST-PLAN B7).

Not a test — never collected by pytest (``probe_*`` matches no
``python_files`` pattern) and exits 0 whatever the model renders. Run
manually, serially, when model behavior (not app code) is the question::

    PYTHONPATH=src uv run python tests/benchmark/probe_echo.py [model]

Reports per target whether the formal output echoes the English input
(the model cannot render the target) or renders something else. An
improving model flips cells from ECHO to RENDERED — that is news, not
failure.
"""

import sys


def main(model="lfm2.5:latest"):
    from text_c3po.services.eval_harness import normalize_text
    from text_c3po.services.translation import translate_text

    text = "Good morning. How are you today?"
    print("model={}".format(model))
    for target in ("Kannada", "Marathi", "Hindi", "Spanish"):
        try:
            result = translate_text(text, target, model)
        except Exception as exc:  # noqa: BLE001 — probe reports, never raises
            print("{}: transport failure {!r}".format(target, exc))
            continue
        if not isinstance(result, dict) or result.get("error"):
            print("{}: error {}".format(target, result))
            continue
        formal = (result.get("formal") or "").strip()
        verdict = (
            "ECHO" if normalize_text(formal) == normalize_text(text) else "RENDERED"
        )
        print(
            "{}: {} out_chars={} {!r}".format(target, verdict, len(formal), formal[:60])
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "lfm2.5:latest"))
