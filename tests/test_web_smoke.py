"""Web-serve smoke: the app boots in Flet web mode and serves its UI.

Spawns the real app once as a subprocess with FLET_FORCE_WEB_SERVER
(the flag that actually switches ft.run to an HTTP site — FLET_SERVER_PORT
alone only moves the desktop client's port), polls GET / until 200, and
asserts the Flutter bootstrap is served. No browser, no Ollama, no
whisper (TEXT_C3PO_NO_WHISPER), no mic needed: the shell renders with
Ollama down.

Slow (~10 s for server boot) but deterministic; teardown kills the whole
process group and asserts the port is freed.
"""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

from text_c3po.paths import find_project_root

BOOT_TIMEOUT_S = 60.0
POLL_STEP_S = 0.5


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _port_closed(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return False
    except Exception:
        return True


def _whisper_pids():
    # Returns None (not empty) when pgrep is missing, so callers can tell
    # "cannot observe" apart from "nothing running".
    import shutil

    if shutil.which("pgrep") is None:
        return None
    try:
        out = subprocess.run(
            ["pgrep", "-f", "whisper-server"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return set(out.stdout.split())
    except Exception:
        return set()


def test_web_serve_smoke(tmp_path):
    import tempfile

    root = find_project_root()
    port = _free_port()
    before = _whisper_pids()
    env = dict(os.environ)
    env["FLET_FORCE_WEB_SERVER"] = "true"
    env["FLET_SERVER_PORT"] = str(port)
    env["PYTHONPATH"] = os.path.join(root, "src")
    env["TEXT_C3PO_NO_WHISPER"] = "1"
    log_path = os.path.join(str(tmp_path), "web-smoke.log")
    log_handle = open(log_path, "wb")
    proc = subprocess.Popen(
        [sys.executable, "-m", "text_c3po.app"],
        cwd=root,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        body = None
        deadline = time.monotonic() + BOOT_TIMEOUT_S
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:{}/".format(port), timeout=5
                ) as response:
                    if response.status == 200:
                        body = response.read()
                        break
            except Exception:
                time.sleep(POLL_STEP_S)
        if body is None:
            try:
                log_handle.flush()
                with open(log_path, "rb") as handle:
                    tail = handle.read()[-2000:].decode("utf-8", "replace")
            except Exception:
                tail = "<unreadable>"
            raise AssertionError(
                "web server never served GET / on :{} (exit={}); log tail:\n{}".format(
                    port, proc.poll(), tail
                )
            )
        lowered = body.lower()
        assert b"flutter_bootstrap" in lowered
    finally:
        try:
            log_handle.close()
        except Exception:
            pass
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            proc.wait(timeout=15)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
    assert _port_closed(port), "port {} still open after teardown".format(port)
    after = _whisper_pids()
    if before is None or after is None:
        pass  # pgrep missing: leak observation impossible, skip the check
    else:
        assert after <= before, "web smoke spawned whisper-server"
