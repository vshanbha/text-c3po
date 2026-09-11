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


def test_web_serve_smoke():
    root = find_project_root()
    port = _free_port()
    before = _whisper_pids()
    env = dict(os.environ)
    env["FLET_FORCE_WEB_SERVER"] = "true"
    env["FLET_SERVER_PORT"] = str(port)
    env["PYTHONPATH"] = os.path.join(root, "src")
    env["TEXT_C3PO_NO_WHISPER"] = "1"
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "text_c3po.app"],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
        assert body is not None, "web server never served GET / on :{}".format(port)
        lowered = body.lower()
        assert b"flutter_bootstrap" in lowered or b"flet" in lowered
    finally:
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
    assert _whisper_pids() <= before, "web smoke spawned whisper-server"
