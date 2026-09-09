"""Shared project-root resolution (A6 close-out).

E1's eval_harness grew a cwd-anchored ``_find_project_root()`` because
``__file__``-relative joins mis-resolved under relative invocations and
doubled/synthetic paths. E2 file-decode and whisper-server paths must reuse
this helper instead of inventing their own ``__file__`` joins.
"""

import os
import sys

_MARKER = os.path.join("src", "text_c3po", "services", "eval_harness.py")


def find_project_root(start=None):
    """Return the nearest ancestor holding src/text_c3po/, else cwd."""
    here = os.path.realpath(start or __file__)
    path = os.path.dirname(here)
    for _ in range(8):
        if os.path.isfile(os.path.join(path, _MARKER)):
            return path
        # Also accept the src-layout parent itself.
        if os.path.basename(path) == "src" and os.path.isdir(
            os.path.join(path, "text_c3po")
        ):
            return os.path.dirname(path)
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return os.path.abspath(os.getcwd())


def ensure_src_on_path():
    """Insert <root>/src at sys.path[0] if missing; return the src dir."""
    src_root = os.path.join(find_project_root(), "src")
    if src_root not in sys.path:
        sys.path.insert(0, src_root)
    return src_root
