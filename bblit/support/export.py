"""Level options -> Export: the textures and the 3D of a level, and the
textures of the whole disc, written to the user's disk.

Four folders next to the settings file (`Documents\\BBLIT Viewer\\Export`,
or `userdata\\Export` in a portable copy); every name inside is in English
whatever the interface language:

    Levels\\<era>\\<level>\\3D_and_tex\\      the eras as in Load level (the
                                           Era selector under Eras)
    Extra\\Cutscenes\\<name>\\3D_and_tex\\, Extra\\Menu and credits\\...,
    Extra\\256-colour versions\\...           the files of the Extra page
    Loading screens\\<group>\\<file>.png     one per loading-screen file
                                           (group L_Pdock, ...; Other)
    Whole game\\                            unique\\, index.csv, info.txt

One folder per level, so moving it never breaks the links between the
model and its images:

* `t<id>.png`: one per texture slot, the disc's colours straight from the
  TIM (`tim.read_tim`), the see-through texels kept as transparency; an
  animated texture comes out as its slots;
* `sky_textures\\`: a copy of the textures the level's sky draws;
* `sheet.png`: every texture small with its number under it, the sky's
  marked with the word SKY;
* `index.csv`: id, size, see-through texels, sky;
* with the 3D export: `level.obj` + `level.mtl`, `sky.obj` + `sky.mtl`,
  `collision.obj` and `info.txt`. A file that would be empty is not
  written; info.txt says so.

The 3D export is always the same, whatever is on screen: no flag, no
option, no choice of `preferences.py`. It is the level as the game opens
it: every object in the role the game starts it in, the gates in the
game's starting state, no cloned template, Bugs as the group "Bugs", the
starting sky in `sky.obj` (in the game it follows the camera). Metres,
Y up. `collision.obj` is the heightmap as the file has it: every 40-unit
sub-cell with ground as a flat square at its height, nothing where the
game says "no ground" (0x7E, 0x7F), one group per block; no class.

Exporting again first deletes the files the export writes (and only
those) from the folder it writes to. A file another program holds open
is skipped and named at the end. One export at a time, even across
windows: a lock file in the export folder names the process doing it.

The work runs in a process of its own (`viewer.py --export JOB TARGET`),
like the filling of the piece cache (cache_warmer.py), and writes its
progress to a file of the viewer that started it; it stops between two
files when that viewer is closed, and what is finished stays.
"""

from __future__ import annotations

import csv
import errno
import hashlib
import json
import os
import re
import shutil
import time
import traceback

from game import collision
from game import family_names
from game import levels
from game import loadscript
from game import textures as texmod
from game import tim
from support import cache_warmer
from support import paths
from support import version

FOLDER = "3D_and_tex"
LEVELS = "Levels"
EXTRA = "Extra"
LOADING = "Loading screens"
WHOLE_GAME = "Whole game"
LOCK = ".export_running"
# the sections of the level table that are not an era, and where they go
SECTIONS = {"extra.hub": (LEVELS, "Eras"), "extra.films": (EXTRA, "Cutscenes"),
            "extra.menu": (EXTRA, "Menu and credits"), "extra.variants": (EXTRA, "256-colour versions")}
# the characters Windows does not allow in a file name
NOT_IN_NAMES = '<>:"/\\|?*'
# what the export writes in a level's folder: deleted before it writes again
TEXTURE_FILES = re.compile(r"(t\d+\.png|sheet\.png|index\.csv)$")
THREE_D_FILES = re.compile(r"(level|sky)\.(obj|mtl)$|collision\.obj$|info\.txt$")
# the loading screens' versions, as read on the pictures of L_Pdock (the
# title written in each); which one the game shows was not looked at
LANGUAGE_NOTE = ("The six versions of a loading screen (_0 to _5) carry the title in six "
                 "languages: read on the pictures of L_Pdock, _0 English, _1 French, _2 German, "
                 "_3 Spanish, _4 Italian, _5 Dutch. Which one the game shows, and how it "
                 "chooses, was not checked.")
REPLACE_NOTE = ("Exporting again replaces the files with these names, even if they were "
                "changed by hand; other files in the folder are left alone.")
SHEET_CELL = 64        # the sheet's thumbnail box, in pixels
SHEET_COLUMNS = 16
SHEET_LABEL = 12       # room under a thumbnail for its number
LEVEL_CATEGORIES = ("terrain", "props")
SKY_CATEGORY = "sky_dome"


# ------------------------------------------------------------------ names and places

def export_root() -> str:
    """`Export` next to the settings file (ui/settings.py)."""
    from ui import settings as settings_mod
    return os.path.join(os.path.dirname(settings_mod.route()), "Export")


def folder_name(name: str) -> str:
    """A name as a folder name: only the characters Windows does not allow
    are dropped, and the dots and spaces at the end."""
    out = "".join(c for c in name if c not in NOT_IN_NAMES and ord(c) >= 32)
    return out.rstrip(". ") or "level"


def level_code(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0]


def level_title(file_path: str) -> str:
    code = level_code(file_path)
    return levels.official_name(code, in_english=True) or code


def _english(key: str) -> str:
    from ui import texts
    return texts.TEXTS[key][1]


def section_of(code: str) -> str | None:
    """The level table's section of a file (an era key, or one of
    SECTIONS), None for a file that is not in the table."""
    return next((entry[2] for entry in levels.all_entries() if entry[1].upper() == code.upper()), None)


def kind_of(code: str) -> str | None:
    """"level" (the 52 you play), "extra", or None (not in the table)."""
    section = section_of(code)
    if section is None:
        return None
    return "level" if section.startswith("era.") or SECTIONS.get(section, ("",))[0] == LEVELS else "extra"


def level_folder(file_path: str, root: str | None = None) -> str:
    section = section_of(level_code(file_path))
    parent = (LEVELS, _english(section)) if section and section.startswith("era.") \
        else SECTIONS.get(section, (EXTRA, "Other"))
    return os.path.join(root or export_root(), *parent, folder_name(level_title(file_path)), FOLDER)


def loading_folder(code: str, root: str | None = None) -> str:
    group = re.sub(r"_\d+$", "", code) if code.upper().startswith("L_") else "Other"
    return os.path.join(root or export_root(), LOADING, group)


# ------------------------------------------------------------------ the work, and what went wrong

class Job:
    """What an export did: the files it could not write because another
    program holds them open."""

    def __init__(self):
        self.skipped: list[str] = []

    def write(self, path, write_fn) -> bool:
        try:
            write_fn(path)
            return True
        except PermissionError:
            if os.path.isdir(os.path.dirname(path)) and os.path.exists(path):
                if path not in self.skipped:    # there, but held by another program
                    self.skipped.append(path)
                return False
            raise                               # the folder itself: not writable

    def clear(self, folder, pattern):
        """Deletes the files the export writes there, and only those."""
        if not os.path.isdir(folder):
            return
        for sub in ("", "sky_textures"):
            here = os.path.join(folder, sub)
            if not os.path.isdir(here):
                continue
            for name in os.listdir(here):
                path = os.path.join(here, name)
                if os.path.isfile(path) and (pattern.fullmatch(name) or sub):
                    try:
                        os.remove(path)
                    except PermissionError:
                        if path not in self.skipped:
                            self.skipped.append(path)
            if sub and not os.listdir(here):
                os.rmdir(here)


def classify(why: BaseException) -> tuple[str, str]:
    """(kind, folder) of an error that stopped an export: "disk_full",
    "not_writable" (a folder that cannot be written, a path too long), or
    "other" (the details go to errors.txt)."""
    winerror = getattr(why, "winerror", None)
    if isinstance(why, OSError) and (why.errno == errno.ENOSPC or winerror in (39, 112)):
        return "disk_full", ""
    if (isinstance(why, (PermissionError, FileNotFoundError, NotADirectoryError, FileExistsError))
            or winerror in (3, 5, 206, 267)):
        name = getattr(why, "filename", None) or ""
        return "not_writable", os.path.dirname(name) if os.path.splitext(name)[1] else name
    return "other", ""


def log_error(why: BaseException):
    try:
        with open(os.path.join(paths.APP_DIR, "errors.txt"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M ") + "export:\n"
                    + "".join(traceback.format_exception(type(why), why, why.__traceback__)) + "\n")
    except OSError:
        pass


# ------------------------------------------------------------------ the level as the game opens it

def _object_label(code: str, number: int, model: int) -> str:
    """`obj<number>`, with the name of the Animations menu when the thing
    has one (`game/family_names.py`): `obj40_Merlin`."""
    key = (family_names.EXEMPLARS.get((code.upper(), ("placed", number)))
           or family_names.MODELS.get((code.upper(), model)))
    if key is None:
        return f"obj{number}"
    words = _english(key).replace("({n})", "").strip()
    return f"obj{number}_" + "".join(c if c.isalnum() else "_" for c in words).strip("_")


def game_start(file_path: str, cache: str, table=None):
    """The level built as the game opens it (see the module's docstring),
    listened to while it is built. Returns (scene, captured), `captured`
    a list of (category, group name, vertices, faces, transform) with the
    first frame of what animates."""
    from window import scene as scenemod

    class Listener(scenemod.Level):
        def __init__(self, *a, **kw):
            self.captured = []
            self._label = None
            super().__init__(*a, **kw)

        def _terrain_block(self, t, *a, **kw):
            self._label = f"terrain_{self.lvl['terrain'].index(t)}"
            try:
                return super()._terrain_block(t, *a, **kw)
            finally:
                self._label = None

        def _placed_object(self, n, o, model, role, *a, **kw):
            self._label = "Bugs" if o.get("start") else _object_label(self.name, n, model["id"])
            try:
                return super()._placed_object(n, o, model, role, *a, **kw)
            finally:
                self._label = None

        def _clone(self, t, n_t, model, role, pos, rot, category, *a, **kw):
            # no cloned template: they come from the viewer's reading of
            # the rules, not from the file's placements. Except the sky: in
            # many levels it is a template a rule clones, and the viewer
            # draws it whatever Cloned templates says (scene._clone). Where
            # two skies take turns and neither is there at the start
            # (The Carrot-henge Mystery 3 starts in a cave), no sky
            alternating = {role for role, _n, _at in self.sky_choices}
            none_at_start = bool(alternating) and not any(at for _r, _n, at in self.sky_choices)
            sky = scenemod.carried_by_camera(t) and not (none_at_start and t["role"] in alternating)
            saved, self._label = self._label, (f"sky_clone{n_t}" if sky else None)
            try:
                return super()._clone(t, n_t, model, role, pos, rot, category, *a, **kw)
            finally:
                self._label = saved

        def _add_faces(self, vertices, faces, category, *, rot=None, scale_factor=1.0, pos=(0, 0, 0),
                       anim=None, **kw):
            if (self._label is not None and category in LEVEL_CATEGORIES + (SKY_CATEGORY,)
                    and (anim is None or anim[1] == 0)):
                self.captured.append((category, self._label, vertices, faces,
                                      {"rot": rot, "scale_factor": scale_factor, "pos": pos}))
            return super()._add_faces(vertices, faces, category, rot=rot, scale_factor=scale_factor,
                                      pos=pos, anim=anim, **kw)

    if table is None:
        table = texmod.construct(os.path.dirname(file_path), level_code(file_path), cache)
    level = Listener(file_path, cache, table, None, {}, families=(), gate_state="game",
                     use_preferences=False)
    return level, level.captured


def sky_texture_ids(captured) -> set:
    return {f.tex_id for category, _l, _v, faces, _k in captured if category == SKY_CATEGORY
            for f in faces if f.tex_id is not None}


# ------------------------------------------------------------------ textures

def _checkerboard(size, pale, square=8):
    """A chequer behind a texture, so a see-through texel shows as a hole:
    pale behind a dark texture, dark behind a pale one."""
    from PIL import Image
    light, dark = ((210, 210, 210), (170, 170, 170)) if pale else ((90, 90, 90), (60, 60, 60))
    img = Image.new("RGB", size, light)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            if ((x // square) + (y // square)) % 2:
                px[x, y] = dark
    return img


def _is_pale(rgba) -> bool:
    total = n = 0
    for i in range(0, len(rgba), 4):
        if rgba[i + 3]:
            total += (rgba[i] * 299 + rgba[i + 1] * 587 + rgba[i + 2] * 114) // 1000
            n += 1
    return bool(n) and total / n > 128


def contact_sheet(entries, path, sky=()):
    """One PNG with every texture of a level, its number written under it,
    and SKY after the number of the sky's textures (a word, not a colour)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default()
    rows = (len(entries) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    cell_h = SHEET_CELL + SHEET_LABEL
    sheet = Image.new("RGB", (SHEET_COLUMNS * SHEET_CELL, rows * cell_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for k, (tex_id, w, h, rgba) in enumerate(entries):
        img = Image.frombytes("RGBA", (w, h), bytes(rgba))
        scale = min(SHEET_CELL / max(1, w), SHEET_CELL / max(1, h))
        box = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(box, Image.NEAREST)
        back = _checkerboard(box, pale=not _is_pale(rgba))
        back.paste(img, (0, 0), img)
        x = (k % SHEET_COLUMNS) * SHEET_CELL + (SHEET_CELL - box[0]) // 2
        y = (k // SHEET_COLUMNS) * cell_h + (SHEET_CELL - box[1]) // 2
        sheet.paste(back, (x, y))
        draw.rectangle([x - 1, y - 1, x + box[0], y + box[1]], outline=(120, 120, 120))
        draw.text(((k % SHEET_COLUMNS) * SHEET_CELL + 2, (k // SHEET_COLUMNS) * cell_h + SHEET_CELL),
                  f"{tex_id} SKY" if tex_id in sky else f"{tex_id}", fill=(0, 0, 0), font=font)
    sheet.save(path)


def _write_csv(path, header, rows):
    """Written to a side file and moved in place: a half-written index is
    never left behind."""
    part = path + ".part"
    with open(part, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(part, path)


def _png_writer(w, h, rgba):
    return lambda path: tim._png(path, w, h, rgba)


def export_textures(file_path: str, cache: str, root: str | None = None, table=None, sky=None,
                    unique_dir: str | None = None, unique=None, job: Job | None = None) -> list[dict]:
    """The level's textures into its folder (see the module's docstring),
    after deleting the ones written before. `sky`: the sky's texture ids
    (read from the level as the game opens it when not given). With
    `unique_dir`, every image not yet in `unique` ({sha1: file name}) is
    written there once. Returns one row per texture."""
    job = job or Job()
    if table is None:
        table = texmod.construct(os.path.dirname(file_path), level_code(file_path), cache)
    if sky is None:
        _level, captured = game_start(file_path, cache, table)
        sky = sky_texture_ids(captured)
    folder = level_folder(file_path, root)
    os.makedirs(folder, exist_ok=True)
    job.clear(folder, TEXTURE_FILES)
    rows, entries = [], []
    for tex_id in sorted(table.slots):
        data, offset = table.slots[tex_id]
        try:
            w, h, rgba = tim.read_tim(data, offset)
        except Exception:  # noqa: BLE001
            continue            # a slot that does not decode: nothing to write
        name = f"t{tex_id}.png"
        job.write(os.path.join(folder, name), _png_writer(w, h, rgba))
        if tex_id in sky:
            os.makedirs(os.path.join(folder, "sky_textures"), exist_ok=True)
            job.write(os.path.join(folder, "sky_textures", name), _png_writer(w, h, rgba))
        digest = hashlib.sha1(bytes(rgba) + f"{w}x{h}".encode("ascii")).hexdigest()
        unique_name = _unique(unique_dir, unique, digest, w, h, rgba, job)
        rows.append({"id": tex_id, "width": w, "height": h,
                     "see_through": any(rgba[i] != 255 for i in range(3, len(rgba), 4)),
                     "sky": tex_id in sky, "file": name, "unique": unique_name, "sha1": digest})
        entries.append((tex_id, w, h, rgba))
    if entries:
        job.write(os.path.join(folder, "sheet.png"), lambda p: contact_sheet(entries, p, sky))
        job.write(os.path.join(folder, "index.csv"), lambda p: _write_csv(
            p, ["id", "width", "height", "see_through", "sky"],
            [[r["id"], r["width"], r["height"], "yes" if r["see_through"] else "no",
              "yes" if r["sky"] else "no"] for r in rows]))
    return rows


def _unique(unique_dir, unique, digest, w, h, rgba, job):
    if unique_dir is None:
        return None
    name = unique.get(digest)
    if name is None:
        name = f"{w}x{h}_{digest[:8]}.png"
        job.write(os.path.join(unique_dir, name), _png_writer(w, h, rgba))
        unique[digest] = name
    return name


def loading_screen(file_path: str, cache: str):
    """(width, height, rgba, missing pixels) of a loading-screen file: one
    texture, no terrain; None for a file that is not one.

    Fifteen of them (L_Pload_*, L_Thall_*, Screen1-3) end a few bytes
    before their picture does: the size the .bze declares for the section
    is that short (524,288 to 524,305 bytes for a 512 x 512 16-bit TIM of
    524,308), so it is the disc, not the decompressor. The missing bytes
    are read as 0, a see-through texel, and counted."""
    import struct
    from viewer import sections
    sec = sections(file_path, cache)
    if 1 not in sec or 3 not in sec:
        return None
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    if lvl["terrain"] or len(lvl["textures"]) != 1:
        return None
    data, offset = sec[3], lvl["textures"][0]["offset"]
    missing = 0
    try:
        _magic, flags = struct.unpack_from("<II", data, offset)
        pos = offset + 8 + (struct.unpack_from("<I", data, offset + 8)[0] if flags & 8 else 0)
        need = pos + struct.unpack_from("<I", data, pos)[0]
        if need > len(data):
            bpp = {0: 4, 1: 8, 2: 16}.get(flags & 7, 16)
            missing = ((need - len(data)) * 8 + bpp - 1) // bpp
            data = data + bytes(need - len(data))
    except struct.error:
        return None
    w, h, rgba = tim.read_tim(data, offset)
    return w, h, rgba, missing


# ------------------------------------------------------------------ 3D

def collision_squares(grid_blocks):
    """Every sub-cell with ground, inside its block's extent: (block,
    x0, z0, x1, z1, y) in game units, Y down."""
    for k, b in enumerate(grid_blocks):
        w, _h, cells = collision.subcell_map(b)
        for i, v in enumerate(cells):
            if v in collision.NO_GROUND:
                continue
            sx, sz = (i % w) * collision.SUBCELL, (i // w) * collision.SUBCELL
            if sx >= b.ext_x or sz >= b.ext_z:
                continue
            yield (k, b.ox + sx, b.oz + sz, b.ox + sx + collision.SUBCELL, b.oz + sz + collision.SUBCELL,
                   collision.height_units(b, v))


def write_collision(path, grid_blocks) -> int:
    """`collision.obj`: one flat square per sub-cell with ground, one group
    per block. Metres, Y up, as level.obj. Returns the number of squares."""
    from game.geometry import UNITS_PER_METER as m
    part = path + ".part"
    count = 0
    with open(part, "w", encoding="utf-8") as f:
        f.write("# the collision heightmap as the file has it: every 40-unit sub-cell\n"
                "# with ground, a flat square at its height; none where the game says\n"
                "# \"no ground\" (0x7E, 0x7F). One group per block.\n")
        current = None
        index = {}          # a corner shared by squares at the same height is written once
        for k, x0, z0, x1, z1, y in collision_squares(grid_blocks):
            if k != current:
                f.write(f"g block_{k}\n")
                current = k
            corners = []
            # game (x, y, z) Y down -> (x, -y, -z) Y up; this order faces up
            for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
                key = (x, y, z)
                if key not in index:
                    index[key] = len(index) + 1
                    f.write(f"v {x / m:.4f} {-y / m:.4f} {-z / m:.4f}\n")
                corners.append(index[key])
            f.write("f " + " ".join(map(str, corners)) + "\n")
            count += 1
    os.replace(part, path)
    return count


def export_3d(file_path: str, cache: str, root: str | None = None, job: Job | None = None) -> dict:
    """level.obj, sky.obj, collision.obj and info.txt into the level's
    folder, with its textures, after deleting what was written before."""
    from game.obj_writer import ObjWriter
    job = job or Job()
    table = texmod.construct(os.path.dirname(file_path), level_code(file_path), cache)
    level, captured = game_start(file_path, cache, table)
    folder = level_folder(file_path, root)
    os.makedirs(folder, exist_ok=True)
    job.clear(folder, THREE_D_FILES)
    export_textures(file_path, cache, root, table, sky_texture_ids(captured), job=job)
    level_obj, sky_obj = ObjWriter(level.sizes), ObjWriter(level.sizes)
    for category, label, vertices, faces, transform in captured:
        writer = sky_obj if category == SKY_CATEGORY else level_obj
        writer.add_group(label, vertices, faces, meters=True, **transform)

    def texture_file(t):
        return f"t{t}.png"

    written = []
    for name, writer in (("level", level_obj), ("sky", sky_obj)):
        if writer.face_groups:
            path = os.path.join(folder, name + ".obj")
            if job.write(path, lambda p, w=writer: w.write_obj(p, texture_file=texture_file,
                                                               cut_outs=level.cut_outs)):
                written.append(name + ".obj")
    squares = [0]

    def collision_file(p):
        squares[0] = write_collision(p, level.collision_blocks)

    if any(True for _ in collision_squares(level.collision_blocks)):
        if job.write(os.path.join(folder, "collision.obj"), collision_file):
            written.append("collision.obj")
    groups = list(level_obj.face_groups)
    summary = {"level": level_title(file_path), "code": level_code(file_path),
               "faces": level_obj.face_count(), "groups": len(groups), "bugs": "Bugs" in groups,
               "sky_faces": sky_obj.face_count(), "squares": squares[0],
               "blocks": len(level.collision_blocks), "textures": len(table.slots), "written": written}
    job.write(os.path.join(folder, "info.txt"), lambda p: _write_info(p, summary))
    return summary


def _write_info(path, s):
    lines = [
        f"Level: {s['level']} ({s['code']})",
        f"Viewer: {version.window_title('BBLIT Viewer')}",
        f"Written: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "The level as the game opens it: the terrain and the objects the file",
        "places, every object in the role and pose the game starts it in, the",
        "gates in the game's starting state. No flag, option or choice of the",
        "viewer is applied, and no cloned template is included.",
        "",
    ]
    if "level.obj" in s["written"]:
        lines += [f"- level.obj + level.mtl: {s['groups']} groups, {s['faces']} triangles; the terrain",
                  "  blocks are terrain_<n>, the objects obj<number> (with the name of",
                  "  the Animations menu when there is one)"
                  + (", Bugs is the group \"Bugs\" at his" if s["bugs"] else "; no Bugs in this file."),
                  *(["  starting point, in his starting pose."] if s["bugs"] else []),
                  "  Vertex colours are the game's light painted on the vertices."]
    else:
        lines.append("- no level.obj: nothing to draw in this file, or it could not be written.")
    if "sky.obj" in s["written"]:
        lines += [f"- sky.obj + sky.mtl: the sky the level starts with, {s['sky_faces']} triangles. In the",
                  "  game it follows the camera; here it stands where the game builds it."]
    else:
        lines.append("- no sky.obj: this level has no sky.")
    if "collision.obj" in s["written"]:
        lines += [f"- collision.obj: the collision heightmap as the file has it, {s['squares']} squares",
                  f"  in {s['blocks']} blocks: every 40-unit sub-cell with ground, flat at its",
                  "  height; nothing where the game says \"no ground\"; no class."]
    else:
        lines.append("- no collision.obj: this file has no collision ground.")
    lines += [f"- t<id>.png: the level's {s['textures']} texture slots, the disc's colours; the",
              "  MTL files point at them in this folder. sheet.png shows them all,",
              "  index.csv lists them, sky_textures holds the sky's.",
              "",
              "Units: metres (128 game units = 1 metre), Y up.",
              "",
              REPLACE_NOTE]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ------------------------------------------------------------------ the job, in its own process

def progress_path(cache: str, viewer_pid: int) -> str:
    """The progress of the export started by that viewer: one file per
    window, so a window never reads another's, nor an old one."""
    return os.path.join(cache, f"export_progress_{viewer_pid}.json")


def write_progress(path: str | None, **state):
    if not path:
        return
    part = path + ".part"
    try:
        with open(part, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(part, path)
    except OSError:
        pass


def read_progress(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def running_elsewhere(viewer_pid: int, root: str | None = None) -> bool:
    """An export of another viewer window is running (its lock names a
    live process). A lock left by a process that died does not count."""
    lock = read_progress(os.path.join(root or export_root(), LOCK))
    return bool(lock) and lock.get("viewer") != viewer_pid and cache_warmer.parent_alive(lock.get("pid"))


def whole_disc(folder: str, cache: str, parent_pid: int | None = None, root: str | None = None,
               progress: str | None = None, job: Job | None = None) -> dict:
    """Every file of the disc's levels folder: the playable levels and the
    Extra files as levels (textures only), the loading screens one PNG
    each; `Whole game\\` rebuilt from scratch with the images once each, a
    general index and info.txt. Stops between two files when the viewer
    that started it is closed."""
    root = root or export_root()
    job = job or Job()
    whole = os.path.join(root, WHOLE_GAME)
    unique_dir = os.path.join(whole, "unique")
    if os.path.isdir(unique_dir):
        for name in os.listdir(unique_dir):
            if re.fullmatch(r"\d+x\d+_[0-9a-f]{8}\.png", name):
                try:
                    os.remove(os.path.join(unique_dir, name))
                except PermissionError:
                    job.skipped.append(os.path.join(unique_dir, name))
    os.makedirs(unique_dir, exist_ok=True)
    on_disc = {level_code(f).upper(): os.path.join(folder, f) for f in os.listdir(folder)
               if f.lower().endswith(".bze")}
    expected = {"level": [], "extra": []}
    for entry in levels.all_entries():
        kind = kind_of(entry[1])
        if entry[1].upper() not in {c for k in expected.values() for c in k}:
            expected[kind].append(entry[1].upper())
    table_files = {c for k in expected.values() for c in k}
    screens = sorted(c for c in on_disc if c not in table_files)
    work = ([("level", c) for c in expected["level"] if c in on_disc]
            + [("extra", c) for c in expected["extra"] if c in on_disc]
            + [("loading", c) for c in screens])
    missing = {k: [c for c in expected[k] if c not in on_disc] for k in expected}
    done = {"level": 0, "extra": 0, "loading": 0}
    totals = {"level": len(expected["level"]), "extra": len(expected["extra"]), "loading": len(screens)}
    unreadable, rows, unique, short = [], [], {}, []
    started = time.time()

    def report(state, n, current="", **more):
        left = (time.time() - started) / n * (len(work) - n) if n else None
        write_progress(progress, job="all", state=state, done=n, total=len(work), eta=left,
                       level=current, source=folder, folder=root, counts=done, totals=totals,
                       missing={k: len(v) for k, v in missing.items()}, unreadable=len(unreadable),
                       skipped=[os.path.relpath(p, root) for p in job.skipped][:20], **more)

    for n, (kind, code) in enumerate(work):
        if not cache_warmer.parent_alive(parent_pid):
            report("stopped", n)
            return {"stopped": n}
        file_path = on_disc[code]
        name = level_title(file_path) if kind != "loading" else level_code(file_path)
        report("running", n, name, phase=kind, phase_done=done[kind], phase_total=totals[kind])
        try:
            if kind == "loading":
                picture = loading_screen(file_path, cache)
                if picture is None:
                    unreadable.append((kind, code, "not a loading screen"))
                    continue
                w, h, rgba, missing_pixels = picture
                if missing_pixels:
                    short.append((level_code(file_path), missing_pixels))
                out = loading_folder(level_code(file_path), root)
                os.makedirs(out, exist_ok=True)
                job.write(os.path.join(out, level_code(file_path) + ".png"), _png_writer(w, h, rgba))
                digest = hashlib.sha1(bytes(rgba) + f"{w}x{h}".encode("ascii")).hexdigest()
                rows.append(["loading", os.path.basename(file_path), level_code(file_path), "", w, h,
                             "yes" if any(rgba[i] != 255 for i in range(3, len(rgba), 4)) else "no", "no",
                             os.path.relpath(os.path.join(out, level_code(file_path) + ".png"), root)
                             .replace(os.sep, "/"),
                             "unique/" + _unique(unique_dir, unique, digest, w, h, rgba, job), digest])
            else:
                folder_out = level_folder(file_path, root)
                for r in export_textures(file_path, cache, root, unique_dir=unique_dir, unique=unique, job=job):
                    rows.append([kind, os.path.basename(file_path), name, r["id"], r["width"], r["height"],
                                 "yes" if r["see_through"] else "no", "yes" if r["sky"] else "no",
                                 os.path.relpath(os.path.join(folder_out, r["file"]), root).replace(os.sep, "/"),
                                 f"unique/{r['unique']}", r["sha1"]])
            done[kind] += 1
        except OSError:
            raise                               # disk full, folder not writable: the job stops
        except Exception as why:  # noqa: BLE001
            unreadable.append((kind, code, str(why)[:120] or type(why).__name__))
    job.write(os.path.join(whole, "index.csv"), lambda p: _write_csv(
        p, ["kind", "source_file", "name", "id", "width", "height", "see_through", "sky", "file",
            "unique_file", "sha1"], rows))
    job.write(os.path.join(whole, "info.txt"),
              lambda p: _write_whole_info(p, folder, done, totals, missing, unreadable, short, job, root))
    report("done", len(work), unique=len(unique))
    return {"done": done, "totals": totals, "missing": missing, "unreadable": unreadable,
            "unique": len(unique), "rows": len(rows)}


def _write_whole_info(path, folder, done, totals, missing, unreadable, short, job, root):
    names = {"level": "Levels", "extra": "Extra files", "loading": "Loading screens"}
    lines = [f"Viewer: {version.window_title('BBLIT Viewer')}",
             f"Written: {time.strftime('%Y-%m-%d %H:%M')}",
             f"From: {folder}", ""]
    for kind in ("level", "extra", "loading"):
        lines.append(f"{names[kind]}: {done[kind]} of {totals[kind]} exported.")
        if missing.get(kind):
            lines.append("  Missing from the folder: " + ", ".join(missing[kind]))
        bad = [f"{code} ({why})" for k, code, why in unreadable if k == kind]
        if bad:
            lines.append("  Unreadable: " + ", ".join(bad))
        if kind == "loading" and short:
            lines += ["  Shorter on the disc than their picture (the .bze declares that size), the",
                      "  last pixels left see-through: "
                      + ", ".join(f"{code} ({n} pixels)" for code, n in short)]
    if job.skipped:
        lines += ["", "Not written, open in another program:",
                  *[f"  {os.path.relpath(p, root)}" for p in job.skipped]]
    lines += ["", "Levels\\ and Extra\\ hold one folder per file with its textures; Loading",
              "screens\\ one PNG per file; unique\\ here every different image once;",
              "index.csv every texture with the file it comes from (source_file).",
              "", LANGUAGE_NOTE, "", REPLACE_NOTE]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(job_name: str, target: str, cache: str, parent_pid: int | None = None,
        root: str | None = None) -> None:
    """`job_name`: "textures" or "3d" (target: the file's .bze), "all"
    (target: the levels folder). The outcome goes to the progress file."""
    root = root or export_root()
    progress = progress_path(cache, parent_pid) if parent_pid else None
    title = level_title(target) if job_name != "all" else ""
    job = Job()
    lock = os.path.join(root, LOCK)
    try:
        if running_elsewhere(parent_pid, root):
            write_progress(progress, job=job_name, state="busy")
            return
        os.makedirs(root, exist_ok=True)
        write_progress(lock, pid=os.getpid(), viewer=parent_pid)
        if job_name == "all":
            whole_disc(target, cache, parent_pid, root, progress, job)
            return
        write_progress(progress, job=job_name, state="running", level=title)
        if job_name == "textures":
            export_textures(target, cache, root, job=job)
        else:
            export_3d(target, cache, root, job=job)
        write_progress(progress, job=job_name, state="done", level=title, folder=level_folder(target, root),
                       skipped=[os.path.relpath(p, root) for p in job.skipped][:20])
    except Exception as why:  # noqa: BLE001
        kind, where = classify(why)
        if kind == "other":
            log_error(why)
        write_progress(progress, job=job_name, state="failed", level=title, error=kind, where=where,
                       folder=root)
    finally:
        lock_state = read_progress(lock)
        if lock_state and lock_state.get("pid") == os.getpid():
            try:
                os.remove(lock)
            except OSError:
                pass


def start(job_name: str, target: str, cache: str):
    """Launches run() in a process of its own; returns it, or None. The
    progress files of windows closed since are removed first."""
    try:
        for name in os.listdir(cache):
            m = re.fullmatch(r"export_progress_(\d+)\.json", name)
            if m and not cache_warmer.parent_alive(int(m.group(1))):
                os.remove(os.path.join(cache, name))
    except OSError:
        pass
    write_progress(progress_path(cache, os.getpid()), job=job_name, state="starting",
                   level=level_title(target) if job_name != "all" else "")
    return cache_warmer._launch(["--export", job_name, target, "--cache", cache])
