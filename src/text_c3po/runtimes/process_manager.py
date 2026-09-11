"""whisper-server lifecycle owner (E2-3): spawn, health-check, restart, cleanup.

One ProcessManager owns one whisper-server subprocess serving transcribe-only
HTTP on 127.0.0.1:9001 (``--inference-path /inference``; ``--translate`` is
never passed so translation stays exclusively with the LLM per AD-7). The
``-l`` flag value always comes from the single 23-language constant
(AD-10): a known code passes through, anything else falls back to ``auto``.

Subprocess creation and the readiness probe are injectable so unit tests run
headless and deterministic with zero real processes. Nothing here raises on
runtime failures — ``start``/``wait_ready`` return bools and
``ensure_running`` returns a status string callers use to label missed
utterances as gaps (never silently dropped) during a restart.
"""

import atexit
import os
import socket
import subprocess
import time

from text_c3po.languages import LANGUAGE_CODES

WHISPER_HOST = "127.0.0.1"
WHISPER_PORT = 9001
WHISPER_INFERENCE_PATH = "/inference"
DEFAULT_MODEL_FILENAME = "ggml-small.bin"
AUTO_LANGUAGE = "auto"
READY_TIMEOUT_S = 5.0
PROBE_TIMEOUT_S = 1.0
STOP_TIMEOUT_S = 5.0


def default_model_path(search_dirs=None, filename=None, env=None, root=None):
    """Return the first existing whisper model file, or None when absent.

    Honors ``WHISPER_MODEL`` first, then ``models/<filename>`` under the
    repo root (via the shared ``paths.find_project_root`` helper per the
    A6 convention — never ``__file__`` joins), then the sibling
    live-translate models dir (present in this workspace today). Pure
    filesystem lookup; never raises.
    """
    try:
        from text_c3po.paths import find_project_root
    except Exception:
        find_project_root = None
    try:
        name = filename or DEFAULT_MODEL_FILENAME
        mapping = env if env is not None else os.environ
        try:
            override = (mapping.get("WHISPER_MODEL") or "").strip()
        except Exception:
            override = ""
        if override and os.path.isfile(override):
            return override
        if search_dirs is None:
            try:
                base = root or (
                    find_project_root() if find_project_root else os.getcwd()
                )
            except Exception:
                base = os.getcwd()
            search_dirs = [
                os.path.join(base, "models"),
                os.path.join(os.path.dirname(base), "live-translate", "models"),
            ]
        for directory in search_dirs or []:
            try:
                candidate = os.path.join(directory, name)
            except Exception:
                continue
            try:
                if os.path.isfile(candidate):
                    return candidate
            except Exception:
                continue
    except Exception:
        pass
    return None


def install_exit_cleanup(manager) -> bool:
    """Stop the owned process on interpreter exit and signals. Never raises.

    atexit covers normal exits; SIGTERM/SIGINT handlers cover kills
    (CPython does not run atexit on signals). Handlers re-raise the
    signal with default disposition after cleanup so exit semantics
    (exit code, Ctrl-C) are unchanged.
    """
    try:
        try:
            atexit.register(manager.stop)
        except Exception:
            return False
        try:
            import signal as _signal

            def _on_signal(signum, frame):
                try:
                    manager.stop()
                except Exception:
                    pass
                try:
                    _signal.signal(signum, _signal.SIG_DFL)
                    os.kill(os.getpid(), signum)
                except Exception:
                    pass

            for name in ("SIGTERM", "SIGINT"):
                try:
                    _signal.signal(getattr(_signal, name), _on_signal)
                except Exception:
                    pass
        except Exception:
            pass
        return True
    except Exception:
        return False


def resolve_language_code(code) -> str:
    """Return a valid ``-l`` value: the code when known, else ``auto``.

    Pure helper; never raises.
    """
    try:
        if isinstance(code, str) and code.strip() in LANGUAGE_CODES:
            return code.strip()
        return AUTO_LANGUAGE
    except Exception:
        return AUTO_LANGUAGE


def probe_serving(host=WHISPER_HOST, port=WHISPER_PORT) -> bool:
    """True when something accepts TCP on the whisper port. Never raises."""
    try:
        with socket.create_connection((host, int(port)), timeout=PROBE_TIMEOUT_S):
            return True
    except Exception:
        return False


class ProcessManager:
    """Owns one whisper-server subprocess from spawn to cleanup."""

    def __init__(
        self,
        model_path=None,
        port=WHISPER_PORT,
        language_code=AUTO_LANGUAGE,
        popen_factory=None,
        probe_fn=None,
        sleep_fn=None,
    ) -> None:
        self.model_path = model_path
        try:
            self.port = int(port)
        except Exception:
            self.port = WHISPER_PORT
        self.language_code = resolve_language_code(language_code)
        self._popen_factory = popen_factory or subprocess.Popen
        if probe_fn is not None:
            self._probe_fn = probe_fn
        else:
            # Bind the default probe to this manager's port (review: the
            # bare probe_serving default always checked 9001).
            host, port = WHISPER_HOST, self.port
            self._probe_fn = lambda: probe_serving(host, port)
        self._sleep_fn = sleep_fn or time.sleep
        self._process = None

    def build_command(self) -> "list[str] | None":
        """Return the transcribe-only argv, or None when the model file is missing.

        Never raises.
        """
        try:
            if not self.model_path or not os.path.isfile(self.model_path):
                return None
            return [
                "whisper-server",
                "-m",
                str(self.model_path),
                "--host",
                WHISPER_HOST,
                "--port",
                str(self.port),
                "--inference-path",
                WHISPER_INFERENCE_PATH,
                "-l",
                self.language_code,
            ]
        except Exception:
            return None

    def start(self) -> bool:
        """Spawn the server (idempotent while alive). Never raises."""
        try:
            if self.is_alive():
                return True
            cmd = self.build_command()
            if cmd is None:
                self._process = None
                return False
            self._process = self._popen_factory(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return self.is_alive()
        except Exception:
            self._process = None
            return False

    def stop(self) -> None:
        """Terminate, wait, kill on hang, forget. Never raises; no orphans."""
        try:
            proc = self._process
            self._process = None
            if proc is None:
                return
            try:
                if proc.poll() is not None:
                    return
            except Exception:
                return
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=STOP_TIMEOUT_S)
                return
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=STOP_TIMEOUT_S)
            except Exception:
                pass
        except Exception:
            pass

    def is_alive(self) -> bool:
        """True when the owned process is currently running. Never raises."""
        try:
            proc = self._process
            if proc is None:
                return False
            return proc.poll() is None
        except Exception:
            return False

    def wait_ready(self, timeout_s=READY_TIMEOUT_S) -> bool:
        """True once the probe succeeds within the timeout. Never raises."""
        try:
            limit = float(timeout_s)
        except Exception:
            limit = READY_TIMEOUT_S
        try:
            deadline = time.monotonic() + max(0.0, limit)
            while True:
                try:
                    if self._probe_fn():
                        return True
                except Exception:
                    pass
                try:
                    if time.monotonic() >= deadline:
                        return False
                except Exception:
                    return False
                try:
                    self._sleep_fn(0.1)
                except Exception:
                    return False
        except Exception:
            return False

    def ensure_running(self) -> str:
        """Restart on crash and report: ``ready`` | ``restarted`` | ``failed``.

        Never raises. Callers label utterances missed during a ``restarted``
        window as gaps.
        """
        try:
            if self.is_alive():
                return "ready"
            if self.start() and self.wait_ready():
                return "restarted"
            return "failed"
        except Exception:
            return "failed"

    def __enter__(self):
        """Context-manager entry: start and return self. Never raises."""
        try:
            self.start()
        except Exception:
            pass
        return self

    def __exit__(self, *args) -> bool:
        """Context-manager exit: always stop; never suppress exceptions."""
        try:
            self.stop()
        except Exception:
            pass
        return False
