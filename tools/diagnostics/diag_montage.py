"""How should the part transforms be composed?

The docs say two different things. Finding 33 claims that a pose gives the
COMPLETE transform of each part, and that accumulating along the parent
chain breaks the model apart; a section of MODELFORMAT says instead that
the transforms are concatenated. Here we do not choose by gut feeling: the
objects are assembled in all three ways and we measure which gives a
coherent body.

The measure is the one used in the docs for Bugs: object size and how many
parts touch at least one other part. A wrong assembly produces either a
heap at the origin or a scattered figure.
"""

from __future__ import annotations

import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import export_obj as geo  # noqa: E402
import rig as rigmod  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))
res = {r["id"]: r for r in lvl["resources"]}


def part_points(model_off):
    """Vertices per TMD part, in local space."""
    _m, _f, nobj = struct.unpack_from("<III", sec4, model_off)
    basis = model_off + 12
    output = []
    for i in range(nobj):
        vt, n_vert, _a, _b, _pt, _np, _s = struct.unpack_from("<7i", sec4, basis + 28 * i)
        points = [struct.unpack_from("<fff", sec4, basis + vt + 16 * v) for v in range(n_vert)]
        output.append(points)
    return output


def apply_transform(m, t, p):
    return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + t[0],
            m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + t[1],
            m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + t[2])


def assemble(model_off, parts, mode):
    """mode: 'origin' (all at the origin), 'absolute', 'chained'."""
    per_part = part_points(model_off)
    face_groups = []
    for d in parts.values():
        if not d.mesh or d.mesh - 1 >= len(per_part):
            continue
        points = per_part[d.mesh - 1]
        if mode == "origin":
            face_groups.append(list(points))
            continue
        m, t = rigmod.matrix(d)
        if mode == "chained":
            parent_ref = parts.get(d.parent_ref)
            hops = 0
            while parent_ref is not None and hops < 16:
                mo, to = rigmod.matrix(parent_ref)
                m = tuple(tuple(sum(mo[i][k] * m[k][j] for k in range(3)) for j in range(3))
                          for i in range(3))
                t = apply_transform(mo, to, t)
                parent_ref = parts.get(parent_ref.parent_ref)
                hops += 1
        face_groups.append([apply_transform(m, t, p) for p in points])
    return face_groups


def measure_groups(face_groups):
    all_levels = [p for g in face_groups for p in g]
    if not all_levels:
        return None
    mi = [min(p[k] for p in all_levels) for k in range(3)]
    ma = [max(p[k] for p in all_levels) for k in range(3)]
    measure = [ma[k] - mi[k] for k in range(3)]

    part_boxes = []
    for g in face_groups:
        if not g:
            continue
        part_boxes.append(([min(p[k] for p in g) for k in range(3)],
                      [max(p[k] for p in g) for k in range(3)]))
    touching = 0
    for i, (lo1, hi1) in enumerate(part_boxes):
        for j, (lo2, hi2) in enumerate(part_boxes):
            if i == j:
                continue
            if all(lo1[k] <= hi2[k] and lo2[k] <= hi1[k] for k in range(3)):
                touching += 1
                break
    return measure, touching, len(part_boxes)


ONLY_MODELS = [int(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else None
done = set()
print(f"{'model':>8} {'parts':>6}  {'assembly':>10}  {'size (units)':>24}  parts touching")
for o in lvl["objects"]:
    if not o["position"] or o["block_type"] == 0x08:
        continue
    mid = next((i for i in o["resources"] if i in res and res[i]["data_kind"] == "model"
                and res[i]["size"] > 12), None)
    if mid is None or mid in done:
        continue
    nobj = struct.unpack_from("<I", sec4, res[mid]["offset"] + 8)[0]
    if nobj <= 1 or (ONLY_MODELS and mid not in ONLY_MODELS):
        continue
    rigs = [i for i in o["resources"] if i in res and res[i]["data_kind"] == "stream"
            and rigmod.is_stream(sec4, res[i]["offset"]) == 1]
    poses = [i for i in o["resources"] if i in res and res[i]["data_kind"] == "stream"
             and rigmod.is_stream(sec4, res[i]["offset"]) == 2]
    if not rigs:
        continue
    done.add(mid)
    r = res[rigs[0]]
    p = res[poses[0]] if poses else None
    parts = rigmod.construct(sec4, r["offset"], r["size"],
                        p["offset"] if p else None, p["size"] if p else 0)
    for mode in ("origin", "absolute", "chained"):
        output = measure_groups(assemble(res[mid]["offset"], parts, mode))
        if output is None:
            continue
        measure, touching, n = output
        print(f"{mid:>8} {nobj:>6}  {mode:>10}  "
              f"{measure[0]:>7.0f} {measure[1]:>7.0f} {measure[2]:>7.0f}  {touching}/{n}")
