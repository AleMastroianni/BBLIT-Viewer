"""A level's already-built pieces, on disk: going back to a level you have seen
is cheap even after opening others, or after closing the viewer.

A piece (a ground block, an object, a clone: `viewer.Level`) depends
only on the `.bze` and on the viewer's code; the chosen state (poses, bridges) is
already in its key. The file lives in the level's cache,
`extracted/<LEVEL>/pieces.pkl`, with a signature: size and date of the `.bze`
and a hash of the `bblit/` sources (in the executable, that of the sources
it was built from). If the signature does not match, the file is ignored and
rewritten. Test: `checks/check_level_cache.py` (same level
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
    """The hash of every `.py` source under a folder, subfolders included
    (that of `bblit/`): a change anywhere in the program must invalidate the
    pieces built before it."""
    h = hashlib.sha1()
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for entry_name in sorted(files):
            if entry_name.endswith(".py"):
                relative = os.path.relpath(os.path.join(root, entry_name), folder).replace(os.sep, "/")
                with open(os.path.join(root, entry_name), "rb") as f:
                    h.update(relative.encode() + b"\0" + f.read())
    return h.hexdigest()


def executable_mismatch(project_dir: str) -> str | None:
    """None when the executable next to the project (`_internal/code_hash.txt`,
    written by build_exe.py) was built from the `bblit/` sources there now;
    otherwise what is wrong, in words. The copies (Current, Portable, the
    release) check it before copying: an old executable must not go out
    under new sources."""
    try:
        with open(os.path.join(project_dir, "_internal", FINGERPRINT_FILE), encoding="ascii") as f:
            built = f.read().strip()
    except OSError:
        return "the executable has no code_hash.txt: run packaging/build_exe.py again"
    if built != sources_fingerprint(os.path.join(project_dir, "bblit")):
        return ("the executable was built from other sources than those in bblit/ now: "
                "run packaging/build_exe.py again")
    return None


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
            _fingerprint = sources_fingerprint(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def _alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x102   # still running
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def remove_orphans(cache: str, name: str) -> int:
    """The half-written `pieces.pkl.<pid>.tmp` of a process that no longer
    runs (the flag builder is stopped with terminate() at a level change,
    and can be stopped in the middle of `store`): removed, since nobody will
    ever finish or swap them in. Only this program's own temporary files of
    that level, never the saved pieces. How many were removed."""
    folder = os.path.join(cache, name)
    removed = 0
    try:
        entries = os.listdir(folder)
    except OSError:
        return 0
    for entry in entries:
        parts = entry.split(".")
        if not (entry.startswith(NAME + ".") and entry.endswith(".tmp") and len(parts) == 4
                and parts[2].isdigit()):
            continue
        pid = int(parts[2])
        if pid == os.getpid() or _alive(pid):
            continue
        try:
            os.remove(os.path.join(folder, entry))
            removed += 1
        except OSError:
            pass
    return removed


def stale_pieces(cache: str, folder: str) -> list[str]:
    """The saved pieces nobody will read again: written by other code, or
    for a `.bze` that changed or is not in the levels folder any more. The
    viewer ignores them and rewrites them when a level is opened, but until
    then they take space (124 MB in a cache used for a few weeks)."""
    try:
        names = os.listdir(cache)
    except OSError:
        return []
    levels = {os.path.splitext(f)[0].lower(): os.path.join(folder, f)
              for f in (os.listdir(folder) if folder and os.path.isdir(folder) else ())
              if f.lower().endswith(".bze")}
    stale = []
    for name in names:
        path = _cache_path(cache, name)
        if not os.path.isfile(path):
            continue
        bze = levels.get(name.lower())
        try:
            with open(path, "rb") as f:
                saved = _read_signature(f)
            current = signature(bze) if bze else None
        except OSError:
            continue
        if saved != current:
            stale.append(path)
    return stale


def to_recycle_bin(paths: list[str]) -> bool:
    """Sends files to the Recycle Bin (Windows), never deletes them: the
    user empties it. False when it could not."""
    if not paths or os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_SILENT, FOF_NOERRORUI = 3, 0x40, 0x10, 0x4, 0x400
    op = SHFILEOPSTRUCTW(None, FO_DELETE, "\0".join(os.path.abspath(p) for p in paths) + "\0\0", None,
                         FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI, False, None, None)
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0


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
