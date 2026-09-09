# Deep Recon — Model quality smoke (technical, E1 gate precursor)

Date: 2026-09-08 · Target: blueprint §5 E1 gate (5-lang × 5-sentence matrix, recorded in research.md)

Method: /api/chat with format:json, temp 0. Prompt: Translate to {lang}, respond JSON {"text":"...","source_lang":"en"} only. 5 EN sentences → German + French, on lfm2.5:latest and mistral:latest. 20/20 calls succeeded, 20/20 JSON-valid.

## Results

| Model | Lang | JSON-valid | Latency warm avg | Sample |
|---|---|---|---|---|
| lfm2.5:latest | German | 5/5 | ~3.5s (cold 6.8s) | Wo ist der Bahnhof? / Vielen Dank für Ihre Hilfe. |
| lfm2.5:latest | French | 5/5 | ~3.5s | Où se trouve la gare ? / Je voudrais un café, s'il vous plaît. |
| mistral:latest | German | 5/5 | ~1.4s (cold 4.8s) | Wo befindet sich der Bahnhof? / Die Sitzung beginnt um drei Uhr. |
| mistral:latest | French | 5/5 | ~1.5s | La réunion débute à trois heures. / Où se trouve la gare de trains ? |

Qualitative:
- lfm2.5 consistent formal-Sie in German; mistral mixes informal opening with formal close, drops article (Ich hätte gerne Kaffee).
- French both use polite vous-forms; mistral calque "gare de trains" vs native "la gare".
- mistral ~2.3x faster warm; both fit utterance-level latency budget when paired with ASR ~0.4s/9s audio.

## Implications for E1

- Structured JSON contract holds 100% without parse-retry loop for both models.
- Default lfm2.5 justified on register consistency; mistral is speed alternative.
- Full harness must extend to all 23 blueprint languages and record per-language scores; repeatable so new Ollama models can be tested anytime.
- Backend stays model-agnostic; languages stay aspirational per blueprint §2.1.

## Next

- E1 story: build repeatable eval harness (5 sentences × N languages × M models → research.md table).
- E4 story: full 23-language matrix + latency budget verification (<3s end-to-end per utterance).

## E1 gate — 5x5 smoke (2026-09-08)

Target: http://127.0.0.1:11434 (loopback only). Matrix: 5 sentences x 5 languages.

| Model | de | fr | es | hi | zh | Valid | Score | Gate |
|---|---|---|---|---|---|---|---|---|
| lfm2.5:latest | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 25/25 | 100% | PASS |

No invalid cells — every model cell JSON-valid.

## E1 gate — 5x5 smoke (2026-09-09)

Target: http://127.0.0.1:11434 (loopback only). Matrix: 5 sentences x 5 languages.

| Model | de | fr | es | hi | zh | Valid | Score | Gate |
|---|---|---|---|---|---|---|---|---|
| lfm2.5:latest | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 25/25 | 100% | PASS |

No invalid cells — every model cell JSON-valid.
