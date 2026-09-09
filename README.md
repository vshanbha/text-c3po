# 🤖 Text C-3PO — Local-first Translator (v2)

Flet desktop app. Type text → local Ollama model → structured translation
(formal / informal / commentary / detected language). No API keys, no cloud:
after the first model download, everything runs on loopback.

Inspired by the Star Wars character C-3PO. Product direction lives in
[blueprint.md](blueprint.md); planning artifacts in `_bmad-output/`.

## Prerequisites

All paths below need these installed first:

- **Python 3.12** (check with `python3 --version`) including **pip**
  (`python3 -m pip --version`)
- **Ollama** ([ollama.com](https://ollama.com)) with at least one model
  pulled: `ollama pull lfm2.5` (the default; any installed model works via
  the in-app picker)

## Run

All commands run from the repo root. First install the local package once
(no PYTHONPATH needed afterwards):

With plain pip (one-time setup):

```sh
pip install -e .   # flet==0.86.5 (pinned), langchain-ollama; exposes `text-c3po`
```

Then:

```sh
ollama serve                                  # or the Ollama desktop app
text-c3po                                     # or: python -m text_c3po.app
```

Prefer `uv` (no activation step — it auto-uses the project `.venv`).
The trailing dot matters — it means "install this folder":

```sh
uv pip install --editable .   # one-time setup (same as: uv pip install -e .)
uv run text-c3po              # or: uv run python -m text_c3po.app
```

Live speech and file modes (whisper-server + sounddevice) land in E2/E3;
their placeholders are visible in the UI.

## Testing

- Fast unit checks (no Ollama, default): `pytest` — or `uv run pytest`
- Manual Ollama-backed tests (opt-in, never CI): `pytest -m integration`
- E1 translation gate, repeatable (serial, lfm2.5-first):  
  `python -m text_c3po.services.eval_harness --models lfm2.5:latest`
  Scores append to the model-quality `research.md` under
  `_bmad-output/planning-artifacts/research/`. Full policy (serial-only,
  memory-hog exclusions) is documented in `pyproject.toml` and the harness
  docstring — CI runs unit tests only, by design.

## Layout

- `src/text_c3po/` — product code (src layout): `app.py` (Flet entry;
  run `text-c3po`), `ui/`, `services/`
  (translation + eval harness), `runtimes/` (Ollama client), `languages.py`
  (23-language constant)
- `tests/` — fast unit tests (run `pytest` from the repo root)
- Provenance: an earlier live-translate proof-of-concept validated the
  speech-to-translation pipeline; its patterns are re-implemented here,
  never imported
- `_bmad-output/` — brief, PRD, UX, architecture spine, epic specs, eval
  research, sprint status, E1 retrospective
- `docs/` — MkDocs Material site published to GitHub Pages (sources are
  symlinks to the repo markdown; regenerate with `mkdocs build`, or
  `uv run --no-project --with mkdocs --with mkdocs-material mkdocs build`)
