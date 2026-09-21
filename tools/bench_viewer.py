"""How quick the viewer is, in numbers: opening a level the first time and
from the piece cache, the first frame, how long turning a flag on takes, and
the milliseconds a frame with the flags off, with one heavy flag and with all
of them.

    .venv/Scripts/python tools/bench_viewer.py [LEVEL ...]

Without arguments: a big level and a small one. It moves the level's
`pieces.pkl` aside to measure the first opening honestly, and puts it back.
The frame is measured with the camera moving, or the sorted list of the
semi-transparent faces would never be sorted again and the number would
flatter us. Run it before and after anything that touches the drawing: the
viewer has to stay immediate.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "bblit"))
import pyglet  # noqa: E402
import viewer  # noqa: E402
from support import paths  # noqa: E402
from pyglet.math import Vec3  # noqa: E402
from window.overlays import OVERLAYS  # noqa: E402

HEAVY = "show_hard_walls"          # the heightmap: the heaviest family
FLAGS = sorted(set(OVERLAYS.values()))
LEVELS = sys.argv[1:] or ["L03A", "L01C"]


def frame_ms(v, n=30):
    for _ in range(4):
        v.on_draw()
    t0 = time.perf_counter()
    for i in range(n):
        v.pos = Vec3(v.pos.x + 0.01, v.pos.y, v.pos.z)
        v.on_draw()
    return (time.perf_counter() - t0) / n * 1000.0


for name in LEVELS:
    path = os.path.join(paths.DATA_BZE, name + ".bze")
    cache = os.path.join("extracted", name)
    pieces = os.path.join(cache, "pieces.pkl")
    cold = os.path.join(cache, "pieces.pkl.bench")
    if os.path.exists(pieces):
        shutil.move(pieces, cold)          # the first time: no pieces on disc
    t0 = time.perf_counter()
    v = viewer.Viewer([path], "extracted", 0, screenshot="nessuna.png")
    v.screenshot = None
    first_open = time.perf_counter() - t0
    t0 = time.perf_counter()
    v.on_draw()
    first_frame = time.perf_counter() - t0
    off = frame_ms(v)
    setattr(v, HEAVY, True)
    t0 = time.perf_counter()
    v.ensure_overlays()
    heavy_on = time.perf_counter() - t0
    one = frame_ms(v)
    t0 = time.perf_counter()
    for attr in FLAGS:
        setattr(v, attr, True)
    v.ensure_overlays()
    all_on = time.perf_counter() - t0
    every = frame_ms(v)
    triangles = v.current_level.stat["triangles"]
    v.close()
    if os.path.exists(cold):               # again, this time from the cache
        pass
    t0 = time.perf_counter()
    v = viewer.Viewer([path], "extracted", 0, screenshot="nessuna.png")
    warm_open = time.perf_counter() - t0
    v.close()
    if os.path.exists(cold):
        if os.path.exists(pieces):
            os.remove(pieces)
        shutil.move(cold, pieces)
    print(f"\n=== {name} ({triangles} triangoli) ===")
    print(f"  apertura la prima volta (senza pezzi su disco): {first_open:6.2f} s")
    print(f"  apertura dalla cache dei pezzi:                 {warm_open:6.2f} s")
    print(f"  primo disegno:                                  {first_frame * 1000:6.1f} ms")
    print(f"  accendere una flag pesante ({HEAVY}): {heavy_on:6.2f} s")
    print(f"  accendere tutte le flag:                        {all_on:6.2f} s")
    print(f"  fotogramma, flag spente:        {off:6.2f} ms")
    print(f"  fotogramma, una flag pesante:   {one:6.2f} ms")
    print(f"  fotogramma, tutte le flag:      {every:6.2f} ms")
