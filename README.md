<p align="center"><img src="branding/logo.png" alt="BBLIT Viewer" width="640"></p>

<p align="center">A level viewer for <i>Bugs Bunny: Lost in Time</i> (PC, 1999), with glitch-hunting overlays.</p>

<p align="center"><b><a href="../../releases/latest">Download the latest release</a></b> · <a href="README_Ita.md">Italiano</a></p>

<p align="center"><img src="docs/images/dock_L03A.png" alt="The dock of L03A in the viewer" width="900"></p>

## Requirements

- Windows 10 or 11, 64-bit;
- a graphics card with an OpenGL 3.3 driver (any card from the last ten
  years, with its driver installed);
- the level files of your own copy of the game, PC version (below).

Nothing to install: unzip the release anywhere and run `BBLIT Viewer.exe`
(Python and its libraries are inside `_internal\`). The program is not
signed, so Windows may warn about an unknown publisher: "More info" → "Run
anyway".

## Getting the levels

**No game data is included**, neither here nor in the release. The viewer reads
the level files (`.bze`) of your own copy of the **PC version**: they are in the
game's `Datas\bze` folder, on the CD or in the installation folder. The
PlayStation version is not supported.

- Copy the `.bze` files into `bze_levels\`, next to the viewer. All of them or
  only some: the levels without a file show greyed out in the menu.
- Or leave them where they are: **General options → Levels folder**, and pick
  the game folder or its `Datas\bze`. The choice is remembered.

Without levels the viewer opens on a page that explains this, with buttons to
open `bze_levels\` or choose a folder. The game files are only read, never
changed.

## What it does

- **The viewer**: every level of the game, era by era, with the hub
  (Nowhere), the Era selector and the `_8` variants. Terrain, props in their
  starting pose, animations at the game's 15 ticks per second, animated
  textures, the sky dome, semi-transparent blends and the template clones the
  level's rules spawn. Free camera; menus in English and Italian.
- **Glitch-hunting overlays** (Level options → Flags): see below.
- **Command-line tools** in `tools/`, usable on their own:
  - `bze.py`: unpacks and decompresses the `.bze` container;
  - `export_obj.py`: exports a level's terrain and props to OBJ + MTL, with
    textures, for Blender and similar;
  - `tim.py`: exports the TIM textures to PNG.

## Controls

| key | action |
|---|---|
| W A S D | move the camera |
| Q / E | camera up / down |
| right mouse | look (hold) |
| wheel | camera speed |
| Shift / Ctrl | faster / slower |
| Esc | open / close the menu |
| ↑ ↓ ← → Enter | in the menu: select, change, confirm |
| Backspace / M | in the menu: back |
| [ ] | previous / next level |
| R | camera back to the start |
| T / O / H / M / F | textures / props / sky / blends / wireframe |
| N / G | animated textures / template clones |
| P | pause / resume the animations |
| - / + | ticks per second |
| L | bilinear filter |
| Alt+Enter | full screen |

From the sources, `python tools/viewer.py L03A` opens a level directly; `python
tools/viewer.py --help` lists the options (framing with `--camera`, a PNG with
`--screenshot`, frozen animations with `--tick`, the overlays, the language...).
The full guide is in [docs/VIEWER.md](docs/VIEWER.md).

## The flags

Overlays for glitch hunting, all off at every start. Some are **read** straight
from the level data; others are **deduced** by combining what the data says
with what is drawn: they are a guide to where to look, not a proof.

| flag | what it shows | how it is made |
|---|---|---|
| Hard walls | the heightmap's `0x7F` walls: they stop you at any height | read |
| Ground | the ground you really stand on (the heightmap) | read |
| Collision boxes | each object's collision box, as the game tests it | read |
| Death zones | zones that kill and respawn you, or grab you and put you back | read |
| 0x1000 faces | the terrain faces the game never draws; they are not walls | read |
| Invisible walls | hard walls where nothing visible stands | deduced |
| No collision | faces you see but cannot stand on: where the fall lands you safely, and where it ends in a death zone | deduced |
| Death floor | death zones at least half the size of the level (sea, abyss) | deduced |
| Area boxes | each heightmap block as a box, base to top | deduced, not checked in the game |

<p align="center">
  <img src="docs/images/collision_boxes_L03D1.png" alt="Collision boxes in L03D1" width="440">
  <img src="docs/images/wireframe_L02A1.png" alt="Wireframe of L02A1" width="440">
</p>

The findings behind each flag are in [docs/FORMAT_NOTES.md](docs/FORMAT_NOTES.md)
(282-288).

## Building

Python 3.10 or newer, on Windows (the viewer uses OpenGL 3.3):

- [pyglet](https://pyglet.org/) — the window and OpenGL: enough to run
  `python tools/viewer.py`;
- [Pillow](https://python-pillow.org/) — only for the scripts in `branding/`;
- [PyInstaller](https://pyinstaller.org/) — for the executable.

```
python -m venv .venv
.venv\Scripts\pip install pyglet pillow pyinstaller
.venv\Scripts\python tools\build_exe.py
.venv\Scripts\python tools\make_release.py
```

`build_exe.py` writes `BBLIT Viewer.exe` and `_internal\` in the project
folder; `make_release.py` puts them, with this README, the licence and an empty
`bze_levels\`, into `release\BBLIT Viewer\` and a zip, and prints the zip's SHA-256
for the release notes (the executable is not signed). The release is portable:
its settings stay in `userdata\` next to it. A level's pieces are cached in
`extracted\` after the first opening.

## Notes on the format

[docs/FORMAT_NOTES.md](docs/FORMAT_NOTES.md) collects what this project found
about the data (findings 256-288), each with the test that could have proved
it wrong. They continue the numbering of
[Ombelll's reverse-engineering documentation](https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered),
which this viewer is built on; where a finding corrects it, it says so.

## Contributing

Please open an **issue**: a level that looks wrong, a flag that does not
match the game, a reading of the format. For anything about how the game
behaves, a screenshot or a short capture from the game next to the viewer's
helps a lot. Pull requests are not accepted: the fixes are made here, from
the issues. Please never attach game files.

## Community

The *Bugs Bunny: Lost in Time* speedrun, TAS and glitch-hunting community is
on Discord: **https://discord.gg/PThM9ucHmu**. Thanks to everyone there for
the help with TAS and glitch hunting.

## Credits

- **Ombelll** — the [reverse-engineering documentation](https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered)
  of the container, load script, models, animations and terrain.
- **quantumdude836** — [BugsDecomp](https://github.com/quantumdude836/BugsDecomp),
  the decompilation, used for reference.
- **CTR viewer** — the model for the interface (menus, options, portable
  settings). No code was taken from it.
- Logo font: [Luckiest Guy](https://fonts.google.com/specimen/Luckiest+Guy)
  by Astigmatic (Apache 2.0). Logo, icon and background are drawn by the
  scripts in `branding/`.

## Legal

This is an unofficial fan project, not affiliated with or endorsed by Warner
Bros., Atari or Behaviour Interactive. *Bugs Bunny*, *Looney Tunes* and all
related characters are trademarks of Warner Bros. Entertainment Inc. The
repository and the release contain no game code or data; you need your own
copy of the game.

## Licence

[GPL-3.0](LICENSE).

---

2026, AleMastroianni
