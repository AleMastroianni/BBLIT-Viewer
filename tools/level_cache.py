"""A level's already-built pieces, on disk: going back to a level you have seen
is cheap even after opening others, or after closing the viewer.

A piece (a ground block, an object, a clone: `viewer.Level`) depends
only on the `.bze` and on the viewer's code; the chosen state (poses, bridges) is
already in its key. The file lives in the level's cache,
`extracted/<LEVEL>/pieces.pkl`, with a signature: size and date of the `.bze`
and a hash of the `tools/` sources (in the executable, that of the sources
it was built from). If the signature does not match, the file is ignored and
rewritten. Test: `tools/diagnostics/check_level_cache.py` (same level
from the cache and from scratch, group by group).
"""

from __future__ import annotations

import hashlib
import os
import pickle
import sys

CACHE_VERSION = 1
NAME = "pieces.pkl"
FINGERPRINT_FILE = "code_hash.txt"
_fingerprint = None


def sources_fingerprint(folder: str) -> str:
    """The hash of a folder's `.py` sources (that of `tools/`)."""
    h = hashlib.sha1()
    for entry_name in sorted(os.listdir(folder)):
        if entry_name.endswith(".py"):
            with open(os.path.join(folder, entry_name), "rb") as f:
                h.update(entry_name.encode() + b"\0" + f.read())
    return h.hexdigest()


def _code_fingerprint() -> str:
    """From the sources; in the executable, that of the sources it was
    built from (`code_hash.txt`, written by build_exe.py): so the sources
    and the executable, when they share `extracted/`, use the same cache
    instead of rewriting each other's."""
    global _fingerprint
    if _fingerprint is None:
        if getattr(sys, "frozen", False):
            try:
                with open(os.path.join(sys._MEIPASS, FINGERPRINT_FILE), encoding="ascii") as f:
                    _fingerprint = f.read().strip()
            except OSError:
                st = os.stat(sys.executable)
                _fingerprint = hashlib.sha1(
                    f"{sys.executable}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()
        else:
            _fingerprint = sources_fingerprint(os.path.dirname(os.path.abspath(__file__)))
    return _fingerprint


def signature(bze_path: str) -> str:
    st = os.stat(bze_path)
    return f"{CACHE_VERSION}|{st.st_size}|{st.st_mtime_ns}|{_code_fingerprint()}"


def _cache_path(cache: str, name: str) -> str:
    return os.path.join(cache, name, NAME)


def fetch(cache: str, name: str, expected_signature: str) -> dict | None:
    """The saved pieces, or None if missing or from other code or another file."""
    try:
        with open(_cache_path(cache, name), "rb") as f:
            stored_signature, pieces = pickle.load(f)
    except (OSError, EOFError, pickle.UnpicklingError, ValueError, TypeError, AttributeError,
            ImportError, IndexError):
        return None
    return pieces if stored_signature == expected_signature and isinstance(pieces, dict) else None


def store(cache: str, name: str, current_signature: str, pieces: dict) -> None:
    """Writes to a temporary file and swaps it in: a viewer closed halfway
    does not leave a broken file. A write error does not stop the viewer."""
    file_path = _cache_path(cache, name)
    tmp = file_path + ".tmp"
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(tmp, "wb") as f:
            pickle.dump((current_signature, pieces), f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, file_path)
    except OSError as e:
        print(f"piece cache not saved for {name}: {e}")
