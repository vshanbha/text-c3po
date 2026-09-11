#!/bin/sh
# text-c3po clean-machine setup (E4-1): macOS Apple Silicon only.
#
# Installs system deps, Python deps, the default whisper model, and the
# default Ollama model, then runs the fast unit suite. Idempotent: safe
# to re-run; every step skips when already satisfied. Never writes
# secrets (there are none — local-first by design).
#
# Usage: ./setup.sh [--medium]     # --medium also fetches ggml-medium.bin
set -eu

cd "$(dirname "$0")"

WHISPER_MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
MODELS_DIR="models"
HAVE_MEDIUM=0
if [ "${1:-}" = "--medium" ]; then
  HAVE_MEDIUM=1
fi

fail() {
  echo "setup.sh: $1" >&2
  exit 1
}

need_macos() {
  [ "$(uname -s)" = "Darwin" ] || fail "macOS only (found $(uname -s))."
  [ "$(uname -m)" = "arm64" ] || echo "setup.sh: warning: non-Apple-Silicon ($(uname -m)); continuing."
}

need_brew() {
  command -v brew >/dev/null 2>&1 || fail "Homebrew missing — install from https://brew.sh first."
}

brew_pkg() {
  # brew_pkg <formula> <binary>: install only when the binary is absent.
  if command -v "$2" >/dev/null 2>&1; then
    echo "setup.sh: $2 present, skipping."
  else
    echo "setup.sh: brew install $1 ..."
    brew install "$1"
  fi
}

need_macos
need_brew

brew_pkg ffmpeg ffmpeg
brew_pkg whisper-cpp whisper-server
# PortAudio is a library (no binary to probe) — ask brew directly.
if brew list portaudio >/dev/null 2>&1; then
  echo "setup.sh: portaudio present, skipping."
else
  echo "setup.sh: brew install portaudio ..."
  brew install portaudio
fi
brew_pkg ollama ollama

if [ ! -d "/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ] \
  && [ ! -d "$HOME/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ]; then
  echo "setup.sh: installing BlackHole 2ch (system-audio loopback) ..."
  brew install --cask blackhole-2ch || echo "setup.sh: warning: BlackHole install failed — live mic still works; file mode unaffected."
else
  echo "setup.sh: BlackHole present, skipping."
fi

if ! command -v uv >/dev/null 2>&1; then
  fail "uv missing — install from https://docs.astral.sh/uv/ first."
fi

echo "setup.sh: syncing Python deps (incl. dev group for pytest) ..."
uv sync --quiet || uv pip install --quiet -e . pytest

mkdir -p "$MODELS_DIR"
fetch_model() {
  if [ -f "$MODELS_DIR/$1" ]; then
    echo "setup.sh: $MODELS_DIR/$1 present, skipping."
  else
    echo "setup.sh: downloading $1 (~500 MB for small) ..."
    # Atomic fetch: a dropped transfer must never pass the -f check above.
    curl -fL --retry 3 -o "$MODELS_DIR/$1.tmp" "$WHISPER_MODEL_URL/$1" \
      && mv "$MODELS_DIR/$1.tmp" "$MODELS_DIR/$1"
  fi
}
fetch_model ggml-small.bin
if [ "$HAVE_MEDIUM" = "1" ]; then
  fetch_model ggml-medium.bin
fi

if ollama list 2>/dev/null | grep -q "^lfm2\.5"; then
  echo "setup.sh: lfm2.5 present, skipping."
else
  echo "setup.sh: ollama pull lfm2.5 (needs 'ollama serve' running) ..."
  if ollama pull lfm2.5; then
    echo "setup.sh: lfm2.5 ready."
  else
    echo "setup.sh: warning: ollama pull failed — start 'ollama serve' and re-run './setup.sh'."
  fi
fi

echo "setup.sh: fast unit suite ..."
# --no-sync: run against the .venv this script just synced; a fresh
# re-sync here would re-hit the network and fail offline.
uv run --no-sync pytest -q

cat <<'EOF'
setup.sh: done.
  Run:            ollama serve   # if not already running
                  uv run text-c3po
  Manual checks:  TEST-PLAN.md (top to bottom after any epic)
  Live gate:      PYTHONPATH=src uv run python -m text_c3po.services.eval_harness --models lfm2.5:latest
  BlackHole routing (optional, for system-audio capture): Audio MIDI Setup ->
  create a Multi-Output Device (speakers + BlackHole, Drift Correction on),
  set it as the system output.
EOF
