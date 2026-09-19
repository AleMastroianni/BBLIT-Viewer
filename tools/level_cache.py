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

The file: the signature (u32 length + ASCII), then the pickled pieces
compressed with zlib level 1, lossless: 17-18 MB -> about 2 MB a level,
+0.03 s to read. The signature alone can be read without
the rest (`is_current`, used by cache_warmer.py).
"""

from __future__ import annotations

import hashlib
import os
import pickle
import struct
import sys
import zlib

CACHE_VERSION = 2
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


def _read_signature(f) -> str | None:
    head = f.read(4)
    if len(head) != 4:
        return None
    n = struct.unpack("<I", head)[0]
    raw = f.read(n) if n < 4096 else b""
    return raw.decode("ascii", "replace") if len(raw) == n else None


def is_current(cache: str, name: str, expected_signature: str) -> bool:
    """Whether the saved pieces match the signature, reading only the signature."""
    try:
        with open(_cache_path(cache, name), "rb") as f:
            return _read_signature(f) == expected_signature
    except OSError:
        return False


def fetch(cache: str, name: str, expected_signature: str) -> dict | None:
    """The saved pieces, or None if missing or from other code or another file."""
    try:
        with open(_cache_path(cache, name), "rb") as f:
            if _read_signature(f) != expected_signature:
                return None
            pieces = pickle.loads(zlib.decompress(f.read()))
    except (OSError, EOFError, pickle.UnpicklingError, ValueError, TypeError, AttributeError,
            ImportError, IndexError, zlib.error):
        return None
    return pieces if isinstance(pieces, dict) else None


def store(cache: str, name: str, current_signature: str, pieces: dict) -> None:
    """Writes to a temporary file and swaps it in: a viewer closed halfway
    does not leave a broken file. The temporary name carries the process id:
    the viewer and cache_warmer.py may save the same level at the same time.
    A write error does not stop the viewer."""
    file_path = _cache_path(cache, name)
    tmp = f"{file_path}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        signature_bytes = current_signature.encode("ascii", "replace")
        data = zlib.compress(pickle.dumps(pieces, protocol=pickle.HIGHEST_PROTOCOL), 1)
        with open(tmp, "wb") as f:
            f.write(struct.pack("<I", len(signature_bytes)) + signature_bytes)
            f.write(data)
        os.replace(tmp, file_path)
    except OSError as e:
        print(f"piece cache not saved for {name}: {e}")
        try:
            os.remove(tmp)   # our own half-written copy, if any
        except OSError:
            pass
