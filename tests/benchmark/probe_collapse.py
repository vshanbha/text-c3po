"""Optional benchmark probe: Spanish multi-paragraph early-stop (ex TEST-PLAN B6).

Not a test — never collected by pytest (``probe_*`` matches no
``python_files`` pattern) and exits 0 whether or not the collapse
appears. Run manually, serially, when model behavior (not app code) is
the question::

    PYTHONPATH=src uv run python tests/benchmark/probe_collapse.py [model]

Reports full vs collapsed per attempt over up to five serial runs. A
vanishing collapse means the model improved, not that anything broke.
"""

import sys

LIGHTHOUSE_PARAS = [
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

COLLAPSE_PREFIX = "El viejo faro se encontraba"


def main(model="lfm2.5:latest", attempts=5):
    from text_c3po.services.translation import translate_text

    text = "\n\n".join(LIGHTHOUSE_PARAS)
    print("model={} in_chars={} attempts={}".format(model, len(text), attempts))
    for attempt in range(1, attempts + 1):
        try:
            result = translate_text(text, "Spanish", model)
        except Exception as exc:  # noqa: BLE001 — probe reports, never raises
            print("attempt {}: transport failure {!r}".format(attempt, exc))
            continue
        if not isinstance(result, dict) or result.get("error"):
            print("attempt {}: error {}".format(attempt, result))
            continue
        formal = (result.get("formal") or "").strip()
        collapsed = formal.startswith(COLLAPSE_PREFIX) and len(formal) < 150
        print(
            "attempt {}: out_chars={} {}".format(
                attempt, len(formal), "COLLAPSED" if collapsed else "full"
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "lfm2.5:latest"))
