"""The textures enlarged x2 / x4 (Video options -> Texture scale), on disk:
scale2x in pure Python costs seconds a level (1.7 s at x2 and 8.8 s at x4 on
Hey... What's up, Dock? 1), paid again at every opening.

One file per level and scale, `extracted/<LEVEL>/upscale_x<N>.bin`, next to
the level's other caches (never in `userdata`): the signature (the hash of
`upscale.py`, the enlarging code) then zlib level 1 of a pickled dictionary
{key: (width, height, rgba)}. The key is the hash of the texture BEFORE it is
enlarged (width, height and its RGBA, blend alpha included): the same pixels
in, the same pixels out, whatever file or slot they come from. A file with
another signature is ignored and rewritten.

Weight, measured on the 52 levels with every (texture, blend mode) they draw,
compressed (the enlarged pixels repeat a lot): all 52 at x4 63 MB, at x2 25 MB,
the heaviest level at x4 2.0 MB (uncompressed 1,748 and 437 MB). "Clean the
cache" (General options) sends these files to the Recycle Bin too, all but
the one of the level open at the scale in use.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import struct
import zlib

NAME = "upscale_x{}.bin"
_code_hash = None


def _code_signature() -> str:
    global _code_hash
    if _code_hash is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "upscale.py"), "rb") as f:
            _code_hash = "1|" + hashlib.sha1(f.read()).hexdigest()
    return _code_hash


def path_of(cache: str, level: str, factor: int) -> str:
    return os.path.join(cache, level, NAME.format(factor))


def key_of(width: int, height: int, rgba) -> str:
    h = hashlib.sha1(f"{width}x{height}|".encode())
    h.update(bytes(rgba))
    return h.hexdigest()


def load(cache: str, level: str, factor: int) -> dict:
    """The saved enlargements of a level at a scale, or {}."""
    try:
        with open(path_of(cache, level, factor), "rb") as f:
            n = struct.unpack("<I", f.read(4))[0]
            if f.read(n).decode("ascii", "replace") != _code_signature():
                return {}
            data = pickle.loads(zlib.decompress(f.read()))
    except (OSError, struct.error, EOFError, pickle.UnpicklingError, ValueError, zlib.error,
            TypeError, AttributeError, ImportError, IndexError):
        return {}
    return data if isinstance(data, dict) else {}


def store(cache: str, level: str, factor: int, entries: dict) -> None:
    """Written to a temporary file and swapped in, as the piece cache."""
    path = path_of(cache, level, factor)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        signature = _code_signature().encode("ascii")
        data = zlib.compress(pickle.dumps(entries, protocol=pickle.HIGHEST_PROTOCOL), 1)
        with open(tmp, "wb") as f:
            f.write(struct.pack("<I", len(signature)) + signature)
            f.write(data)
        os.replace(tmp, path)
    except OSError as e:
        print(f"texture scale cache not saved for {level}: {e}")
        try:
            os.remove(tmp)
        except OSError:
            pass


def files(cache: str, keep=()) -> list[str]:
    """Every saved enlargement of the cache, less the paths in `keep`: what
    "Clean the cache" may send to the Recycle Bin."""
    keep = {os.path.abspath(k) for k in keep}
    out = []
    try:
        names = os.listdir(cache)
    except OSError:
        return []
    for name in names:
        folder = os.path.join(cache, name)
        if not os.path.isdir(folder):
            continue
        for f in os.listdir(folder):
            if f.startswith("upscale_x") and f.endswith(".bin"):
                p = os.path.abspath(os.path.join(folder, f))
                if p not in keep:
                    out.append(p)
    return out
