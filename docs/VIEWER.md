# BBLIT Viewer: the viewer and the tools

Italian version: [VIEWER_Ita.md](VIEWER_Ita.md)

BBLIT Viewer is a free-camera level viewer for the PC game *Bugs Bunny: Lost
in Time* (1999). It reads the game's `.bze` level files directly and builds
everything in memory; there is no intermediate format. The same `tools/`
folder also holds command-line tools that extract textures and export levels
to OBJ.

- **PC version only.** The PlayStation version is not supported.
- **No game data is included.** You need your own copy of the game. Files are
  only read, never modified.

---

## Running it

### The release

Unzip the release and start `BBLIT Viewer.exe`. Requirements: Windows 10 or
11, 64-bit, and a graphics driver with OpenGL 3.3. Python and its libraries
are already inside `_internal/`: there is nothing to install.

### From source

Requires Python 3.10 or newer and pyglet 2.x (developed with pyglet 2.1).
The folder dialog uses `tkinter`, which comes with the python.org installer.

```bash
pip install pyglet
python tools/viewer.py            # opens the main menu
python tools/viewer.py L03A       # opens a level directly (file name, any case)
```

A level name that is not in the levels folder opens the main menu instead.
Run the commands from the repository root.

Other packages are needed only for side jobs: PyInstaller to build the
executable, Pillow for the scripts in `branding/` that draw the icon and logo.
The tools in `tools/` use only the standard library, except the viewer
(pyglet).

### Where the levels come from

The viewer needs the game's `Datas\bze` folder (the `.bze` files). It looks
for them in this order and uses the first folder that has at least one `.bze`:

1. `--data FOLDER` on the command line, otherwise the folder chosen in
   **General options -> Levels folder** (remembered in the settings). In that
   dialog the game folder works too: `Datas\bze` (or `bze`) is looked for
   inside it.
2. `bze_levels/` next to the viewer: copy the contents of `Datas\bze` there.
3. The `BBLIT_DATA` environment variable, if set: a game folder or a
   `Datas\bze` folder.

`BBLIT_DATA` is also the default data folder of the command-line tools (their
`--data` option).

Without levels the viewer starts anyway, on a blue background, with a page
that explains what to copy and buttons to open `bze_levels`, choose the
folder, try again, reach General options or quit. In **Load level** the
entries whose file is missing are greyed out.

The viewer reads only the `.bze` of the level it opens, and only its sections
1 (load script), 3 (textures) and 4 (models and terrain). Level titles in the
menu come from `tools/levels.py`, not from the game files.

---

## Controls

### In the scene

| key / mouse | effect |
|---|---|
| right mouse button (hold) | look around |
| W A S D | move forward / left / back / right |
| E / Q | up / down |
| Shift / left Ctrl (hold) | 5x faster / 5x slower |
| mouse wheel | base camera speed (x1.2 per notch) |
| T | textures on/off |
| O | objects (props) on/off |
| H | sky dome on/off |
| M | semi-transparent blending on/off |
| F | wireframe on/off |
| N | animated textures on/off (eyes, sun, water: finding 275) |
| G | cloned templates: off / at start / all |
| P | pause / resume all animations (models, textures, rotating objects) |
| `-` / `+` | animation ticks per second, 1 to 60 (default 15, measured on the PlayStation: finding 278) |
| L | bilinear filtering (like the PC, default) / sharp texels |
| `[` / `]` | previous / next level file in the levels folder (alphabetical, loading screens excluded) |
| R | camera back to the initial view |
| Esc | open / close the menu |
| Alt+Enter | full screen on/off |

The viewer never quits on Esc: use **Quit** in the menu or close the window.
Scene keys work only with a level open and the menu closed.

Rotating objects advance 2 rule passes per animation tick; that ratio is not
measured (finding 280).

### In the menu

| key / mouse | effect |
|---|---|
| Up / Down, or W / S | select |
| Page Up / Page Down | jump 10 rows |
| Left / Right, or A / D, or mouse wheel | change the value (Shift: numbers change 10 steps at a time) |
| Enter, Space, left click | confirm / open |
| Backspace, M, right click | back |
| mouse hover | select |
| Esc | close the menu (it reopens where you left it) |

With the menu open the camera stays still and scene keys do nothing. With no
level open the menu stays open.

---

## The menu pages

| page | contents |
|---|---|
| Main | Resume (greyed out with no level), Load level, Level options, Video options, General options, Help, Quit |
| Load level | the five eras (Stone Age, Medieval Period, Pirate Years, The 1930s, Dimension X), then Nowhere (opens directly), then **Extra**: the Era selector (`LS01`), also opened at the centre of each era, and the `_8` variants that are on the disc but not in the game's level table. In an era page the levels are listed by title and part, with the file name on the right (a dot marks the open level), the full name and LevID in the description, and a Bonus section where the era has one |
| Level options | **Flags** (below); Rendering: Textures, Objects, Sky, Semi-transparency, Wireframe; Entities: Animations (Playing / Paused / Starting pose), Ticks per second, Animated textures, Cloned templates, plus the group states of the level, if it has any |
| Video options | Full screen, VSync, Texture filtering, Texture scale (x1 to x4, scale2x/scale3x), Colour (PC, or PSX x2: finding 268), Field of view (40 to 100 degrees, default 65) |
| General options | Language (English, default, or Italian), Status bar, Levels folder, Open the bze_levels folder |
| Help | the keys |

Every row has a description at the bottom of the panel.

**Group states.** Some levels have objects whose state the game decides at
run time. For those, `tools/preferences.py` fixes a default and declares the
alternatives (`entity_groups`); at present only `L03A` has them: drawbridges
(raised, one third, two thirds, lowered), barrels in the water (rising,
floating) and green crates (falling, on the ground). A state chosen in the
menu rebuilds the level and lasts for the session only.

**Status bar** (bottom): level, position in game units and in metres (these
are the `x,y,z` of `--camera`), camera speed, triangles drawn, animation state
when not playing.

The credit line "BBLIT Viewer by AleMastroianni" is shown at the bottom right
on the main menu page, and whenever no level is open.

### Flags

Overlays for glitch hunting. They are **always off at start**, are not saved,
and have **no keys**: turn them on in **Level options -> Flags**, or with the
command-line options below. Background: findings 282-288.

| flag | what it shows |
|---|---|
| Invisible walls | what stops you with nothing drawn: the collision heightmap's hard walls (`0x7F`) where there is no visible wall. Magenta |
| No collision | walkable-looking faces with no collision: bright cyan where the fall lands you safely, dark cyan where it ends in a death, damage or teleport zone |
| Collision boxes | each object's collision box as the game tests it (it can be much bigger than the object). Orange |
| Death zones | zones that kill you, with a respawn at the checkpoint (red), or respawn you directly at a fixed point (violet) |
| Death floor | death zones at least half the size of the level: the sea, the abyss under the level. Not every level has one |
| Ground | the ground you really stand on (the heightmap): faint green under visible faces, bright green where nothing is drawn, white with beams for isolated 40-unit spots |
| Hard walls | the heightmap's `0x7F` walls, which stop you at any height. Blue, drawn 5 m tall |
| Area boxes | the collision volume of each mini area (heightmap blocks, base to top); still to be checked in the game |
| 0x1000 faces | faces of the `0x1000` terrain sectors: the game does not draw them and they do not stop you; maybe triggers or loading areas. Grey |

---

## Command-line options

`python tools/viewer.py [LEVEL] [options]`, or the same options after
`"BBLIT Viewer.exe"`.

| option | effect |
|---|---|
| `LEVEL` | level file to open, without extension (e.g. `L03A`, `MERLIN`); without it, the main menu |
| `--data FOLDER` | folder with the `.bze` files, for this run (takes precedence over the saved Levels folder) |
| `--cache FOLDER` | cache folder (default `extracted/` next to the viewer) |
| `--screenshot FILE.png` | open, wait 0.6 s, save the window to a PNG and exit. Mouse and keys are ignored, and settings are neither read nor written, so the image depends only on the options |
| `--camera x,y,z,yaw,pitch` | start camera: position in viewer metres, yaw and pitch in degrees |
| `--menu PAGE` | open a menu page at start: `main`, `load`, `level`, `flags`, `video`, `general`, `help`, `extra` |
| `--language it\|en` | interface language |
| `--tick N` | freeze all animations on tick N (reproducible screenshots) |
| `--tps N` | animation ticks per second (default 15) |
| `--clones 0\|1\|2` | cloned templates: off / at start / all |
| `--albedo F` | factor on the vertex colour of textured faces: 1 is the PC (default), 2 the PlayStation |
| `--scale-factor N` | upscale textures with scale2x/scale3x: 1, 2, 3, 4, 6 or 8 |
| `--sky` | show the sky dome |
| `--no-blend` | draw semi-transparent faces as opaque |
| `--invisible-walls`, `--nocollision`, `--boxes`, `--deathzones`, `--deathfloor`, `--ground`, `--hardwalls`, `--areaboxes`, `--faces1000` | turn on the flag of the same name |

Example, a reproducible picture (take `x,y,z` from the "m" values of the
status bar):

```bash
python tools/viewer.py L03A --camera 10,5,-20,-90,-15 --tick 0 --screenshot l03a.png
```

Except for the flags, values set on the command line (language, sky,
clones, texture scale...) are saved like the menu choices when the menu or the
window is closed, unless `--screenshot` is used.

---

## Settings and cache

**Settings** persist from one run to the next, in
`Documents\BBLIT Viewer\settings.json`. If a file named `portable.flag` sits
next to the viewer (next to `BBLIT Viewer.exe`, or the repository root when
run from source), they go to `userdata\settings.json` there instead. They are
saved when the menu is closed with Esc and when the window is closed, and
include what was changed with the scene keys. Not saved: flags, group states,
paused animations. An unknown or malformed entry is ignored.

**Cache**, in `extracted/<LEVEL>/` next to the viewer (or `--cache`):

- `<LEVEL>_id01.bin`, `_id03.bin`, `_id04.bin`: the decompressed sections
  (decompressing in Python takes a few seconds per level);
- `pieces.pkl`: the level already built, piece by piece (`tools/level_cache.py`).
  It carries a signature (size and date of the `.bze`, plus a hash of the
  `tools/` sources, or of the sources the executable was built from) and is
  rebuilt automatically when the code or the level file changes. A level
  already seen reopens in a fraction of a second.

The glitch-hunting overlays are built only when one of their flags is
turned on (the heightmap takes a few seconds on large levels); after that
they are in the cache too, and turning the flag off only hides them.

The decompressed sections carry the size and date of the `.bze` they come
from (`sections.json`): if you replace a level file, they are decompressed
again by themselves. Deleting `extracted/` is always safe: it is rebuilt.

An error at startup is appended to `errors.txt` next to the viewer; the
executable also shows it in a message box.

---

## Building the executable

```bash
pip install pyinstaller
python tools/build_exe.py
```

Builds a one-folder, console-less PyInstaller app and puts `BBLIT Viewer.exe`
and `_internal/` in the repository root. `_internal/` contains Python, the
libraries, `resources/` (the golden carrot icon and the blue background) and
`code_hash.txt`, the hash of the sources, so the executable and
`python tools/viewer.py` share the piece cache. PyInstaller's work files stay
in `build/`. If the viewer is running, the script stops without touching
anything. With Python 3.10.0 exactly, the script works around a bug in `dis`
that stops PyInstaller.

`python tools/make_release.py` builds the release folder and its zip: the
executable with `_internal/`, `README`, `README_Ita`, `LICENSE`,
`THIRD_PARTY_LICENSES.txt` (the licences of Python, pyglet, Pillow and
PyInstaller's bootloader, bundled in the executable) and
`bze_levels/README.txt`.

---

## The tools

| file | what it does |
|---|---|
| `viewer.py` | the viewer |
| `bze.py` | `.bze` container and LZ77 decompressor (reconstruction of the game's `FUN_00430ff0`) |
| `loadscript.py` | reads the load script (section 1), with the opcode table **per block type**; writes a JSON extract |
| `tim.py` | PlayStation TIM textures -> PNG |
| `textures.py` | the texture table: registered slots and animated slots (finding 275) |
| `export_obj.py` | terrain and props -> OBJ + MTL, in metres and Y up |
| `render_obj.py` | renders an OBJ to PNG with no graphics engine, to check the data |
| `model_sheet.py` | contact sheet of a level's models |
| `rig.py` | `0x50` streams: rig, poses, parent chain (finding 261) |
| `montage.py` | picks an object's rig and pose and produces the part transforms, also per frame |
| `collision.py` | the collision heightmap (load script block `0x36`) |
| `zones.py` | zones that kill (`0x200000`) or respawn you directly (teleport `0x40000000`) |
| `upscale.py` | scale2x / scale3x for textures |
| `bmp.py` | the game's `.bmp` files -> PNG |
| `census.py` | census of rendering defects, one row per level |
| `levels.py` | levels by era, with LevID and titles, for the menu |
| `preferences.py` | chosen default states of some levels (not readings of the format) and the `entity_groups` the menu can change |
| `level_cache.py` | the on-disk piece cache |
| `menu.py`, `texts.py`, `settings.py`, `paths.py` | menu engine, interface texts (English and Italian), saved settings, data folders |

All tools write PNG files by hand with `zlib`: no image library is needed.
Tools that take a `--data` option default to `BBLIT_DATA`; their cache is
`extracted` in the current directory.

### Example: from a `.bze` to a textured OBJ

```bash
python tools/bze.py "C:/Games/Lost in Time/Datas/bze/L03A.bze" -o extracted/L03A
python tools/loadscript.py extracted/L03A/L03A_id01.bin --json extracted/L03A/l03a.json
python tools/tim.py extracted/L03A/L03A_id03.bin extracted/L03A/l03a.json -o out/L03A/textures
python tools/export_obj.py extracted/L03A/L03A_id04.bin extracted/L03A/l03a.json --section3 extracted/L03A/L03A_id03.bin -o out/L03A/L03A.obj
python tools/render_obj.py out/L03A/L03A.obj -o out/L03A/check.png --textures out/L03A/textures
python tools/model_sheet.py extracted/L03A -o out/L03A/models.png --assemble
```

(Adjust the first path to where your `.bze` files are.) Useful options:
`bze.py --raw` (no decompression); `tim.py --scale-factor N [--soft]`;
`export_obj.py --no-props` (terrain only), `--units` (game units instead of
metres), `--textures-dir` (folder named in the `.mtl`, default `textures`);
`model_sheet.py --model ID`, `--columns`, `--cell-size`. `textures.py [DATA]
[LEVEL]` prints where a level's texture slots come from, and
`bmp.py IN.bmp OUT.png` converts one bitmap.

`census.py` counts, with the viewer's own reading, everything drawn badly or
not drawn, split by cause (terrain, textures, modes, props):

```bash
python tools/census.py                       # L03A, L03ACOM, L03A2
python tools/census.py --all-levels --json census.json
```

The columns are not summed: an empty model is the file saying "draw nothing",
not an error. Since finding 265, all the reading columns are zero on the three
`L03A` levels.

### How they are connected

```
.bze  --bze.py-->  decompressed sections (cache in extracted/)
                     | id 1  load script  --loadscript.py-->  objects, resources, terrain, textures, zones
                     | id 3  asset block  --tim.py--------->  TIM textures
                     | id 4  model block
                     |         +-- magic 0x41  --export_obj.read_model-->  geometry
                     |         +-- magic 0x50  --rig.py / montage.py--->  assembly of the parts
                     +- id 5+ audio banks (not used)
```

---

## Coordinate conversion

- **128 game units = 1 metre.**
- The game is **left-handed** with Y pointing down. The conversion is
  `(x, -y, -z)`, which has determinant +1, **plus reversing the vertex order
  of every face**. Negating Y alone mirrors the whole level (Ombelll's finding
  180).
- Rotations: 4096 units = one full turn, composed as `Rx * Ry * Rz`
  (Ombelll's finding 32).

The viewer's `--camera` and the "m" values of the status bar are in the
converted system; the "game" values are the original units.

---

## What is verified, and with what proof

Findings 256-288 are in [FORMAT_NOTES.md](FORMAT_NOTES.md). Lower numbers and
the format documents are Ombelll's:
<https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered>.
Figures are for `L03A` unless stated.

| claim | proof | reference |
|---|---|---|
| container and decompression | compression ratio exactly 8/9 (0.91x) on the audio banks, and every `FORM` header is a valid `AIFF` | Ombelll's format documents; `bze.py` prints the ratio per section |
| load script | consumed 100%, 1 unknown byte; 282 objects, 150 with a position, as in Ombelll's documents | `loadscript.py` prints both |
| resource offsets | 79/79 models with magic `0x41`, 274/274 streams with `0x50`, 442/442 textures on a TIM header | |
| terrain | 158 sectors, sum of the counters 3058 = `n_prim`, every sector ends on the expected byte, chain ending on `vert_top` | finding 256; `export_obj.py` prints the counts |
| primitives | 2773/2773 read in the models, 2742/2742 in the terrain, none rejected | |
| solid-colour textures | the 45 referenced by modes `0x4A`/`0x4E` are all 4x4 and uniform | finding 258 |
| UV `FF FF` | 1158/1158 have a registered texture id, 0/1158 have all UVs at `FF` | finding 259 |
| PC vertex colour factor 1, not 2 | colour of the `L03A` sea measured in the game | finding 268 |
| 15 animation ticks per second | measured frame by frame on the PlayStation version | finding 278 |

The checks behind these figures are the scripts in `tools/diagnostics/`
(`check_*.py`, `diag_*.py`); they read the levels from `BBLIT_DATA` and can be
rerun.
