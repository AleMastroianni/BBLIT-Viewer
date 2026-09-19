# Format notes: findings 256-288

Italiano: [FORMAT_NOTES_Ita.md](FORMAT_NOTES_Ita.md)

Technical notes on the level data of *Bugs Bunny: Lost in Time* (PC, 1999)
and on what the game does with it, found while building the level viewer in
this repository (`tools/viewer.py`), mostly on `L03A` (*Hey... What's Up,
Dock?*, first section) and then checked on the rest of the levels. The
numbering continues [Ombelll's reverse-engineering notes](https://github.com/Ombelll/Bugs-bunny-lost-in-time-reverse-engineered),
which end at 255: "Ombelll's finding N", "Ombelll's MODELFORMAT" and
"Ombelll's SPEEDRUN notes" refer to that repository, and so do function names
such as `FUN_00423eb0` (related work: [BugsDecomp](https://github.com/quantumdude836/BugsDecomp)).
The rule is the same: **a reading counts only after a test that could have
failed**, and each finding gives that test and its numbers. Evidence tags
(`PROVEN_RAW_DATA`, `PROVEN_BINARY`, `REBUILD_VERIFIED`, `STRONG`, `OPEN`)
are used as in those notes. Where a finding corrects Ombelll's documents, it
says so.

| # | Finding |
|---|---|
| 256 | A terrain sector header always consumes at least one bounding face |
| 257 | A quad is Z-shaped, not a fan |
| 258 | Modes `0x4A` and `0x4E` are textured, with a solid-color texture |
| 259 | `FF FF` in the first UV is the (255,255) corner, not padding |
| 260 | DISPROVED by 275: "the texture table is cumulative across files" |
| 261 | A model's parts are assembled with the rig and chained on their parents |
| 262 | UVs are scaled by (size − 1), not divided by 256 |
| 263 | The `.bmp` files in `Datas/bze` are not level previews |
| 264 | Two builds of `Bugs.exe`: the data addresses hold, the code addresses do not |
| 265 | Type 4 streams are animations |
| 266 | REJECTED: "semi-transparent `0x4A`/`0x4E` faces are drawn opaque" |
| 267 | The sky dome follows the camera |
| 268 | The x2 factor on the vertex color is wrong for the PC |
| 269 | CLOSED by 275: the sun's halo uses textures that no static file has |
| 270 | The sky dome, part by part |
| 271 | The texture v coordinate is counted from the bottom |
| 272 | An object's pose is the one the game starts, not the one with the most records |
| 273 | Semi-transparent blending was off from the second frame on (viewer defect) |
| 274 | Blue chests, falling crates and flames are template clones |
| 275 | Eyes, sun halo, water and ripples are animated textures filled by objects |
| 276 | A vertex with bit `0x8000` is a copy of a vertex of another part and must be welded |
| 277 | In the `0x3C` triangle the first vertex is the one at +28, not at +14 |
| 278 | An animation has one block per tick, and each block carries only what changes |
| 279 | Sprites, nested clones and attachment points: the torches |
| 280 | Anchors: parts removed from the pose (type 8, flag 0xB) and the rotation of action `0x26` |
| 281 | The `_8` variants are not in the level table |
| 282 | The `0x1000` sectors: one quad per record, in two vertex orders |
| 283 | Faces you can see and cannot stand on |
| 284 | One box per object: the invisible wall above the glass in `L05A3C` |
| 285 | Zone rules: effects at +16; the zones that kill or bring you back |
| 286 | What you see against what you stand on: invisible ground, landing pixels, fake walls |
| 287 | Collision blocks are stacked slabs; their top as a ceiling is only a candidate |
| 288 | The viewer's collision flags, revised against the game |

---

## 256 — A terrain sector header always consumes at least one bounding face

`PROVEN_RAW_DATA`. A sector with `mode 0x0000` declares `n_bound_faces = 0`,
but its point block is not at +8: it is at **`8 + max(n_doos, 1) * 8`**. The
dispatcher step skips one face even when there are none, which matches the
table of "single" modes (16, 16, 56, 56, 20 bytes) that Ombelll's MODELFORMAT
extracts from `FUN_00423eb0`.

**Proof:** with this reading the sector chain of `L03A` closes exactly: 158
sectors, sum of the `+0` fields **3058 = `n_prim`**, every polygon chain
ending on the last byte of its own record, and the last sector ending on
`vert_top`. With the point block at +8 the parser stops after **3 sectors of
158**.

## 257 — A quad is Z-shaped, not a fan

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. The two triangles of a quad are
`(0,1,2)` and `(1,3,2)`. Writing `f v0 v1 v2 v3` to an OBJ and letting the
importer close the polygon gives `(0,1,2)` and `(0,2,3)`: the other diagonal.

**Proof:** in `L03A` 87% of the terrain faces are quads, and **516 of the
2378 (22%) change area** between the two readings; drawn as fans they show
light and dark sawteeth along all the piers. The format itself is not in
question (Ombelll's documents state it in one line about exporting), but an
exporter that writes polygons instead of triangles loses it.

## 258 — Modes `0x4A` and `0x4E` are textured, with a solid-color texture

`PROVEN_RAW_DATA`. Ombelll's MODELFORMAT gives "texture index at +4, no UV in
the record", which invites the conclusion that these are flat-color faces.
They are not: the field at +4 names a real texture, and the record carries no
UV because none is needed.

**Proof:** of the 45 textures referenced by the UV-less modes in `L03A`,
**45 of 45 are 4×4 and perfectly uniform**, a single repeated color, so any
sample point gives the same result. Drawn with the vertex color alone, which
is almost neutral, these faces (almost half of the level's) come out white or
gray.

**A test that does NOT discriminate, kept as a warning:** "the id at +4 is
registered by the level" scores 100%, but a random number in the same range
scores **97%**, because the level registers 442 ids out of 456.

## 259 — `FF FF` in the first UV is the (255,255) corner, not padding

`PROVEN_RAW_DATA`. **Corrects Ombelll's MODELFORMAT**, which says: *"For
untextured primitives, those spots hold `FF FF` as padding"*.

**Proof:** in `L03A`, **1158 faces of 3048** in UV modes have the first pair
at `FF FF`. Of these:

- the texture id is a registered slot in **1158 cases of 1158**;
- **0 of 1158** have *all* UVs at `FF FF`;
- the pairs are regular corners, for example `(255,255), (255,0), (0,255),
  (0,0)`.

Treating them as untextured loses **38%** of the textured faces. The right
criterion is not in those bytes: a face is untextured when its id **does not
exist in the slot table**.

## 260 — DISPROVED by 275: "the texture table is cumulative across files"

> **Disproved by finding 275.** The 8 ids that `L03A` references without
> registering them are animated texture slots, filled by objects of the same
> level. That other files register those slots proved nothing: almost every
> file registers 3-7 and 291/293.

The claim was: the game registers every TIM in a numbered slot
(`FUN_004229a0`, table at `0x52fd60`) and does not clear the table on level
change (unlike the sound registry, Ombelll's finding 152), so `L03A` would
take six of its 8 missing ids from `L03ACOM` and two (7 and 307) from
`title.bze`. That the table is not cleared remains true in the code (see
275), but no drawn face depends on it.

## 261 — A model's parts are assembled with the rig and chained on their parents

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. The vertices of each TMD part are in
local space; they are positioned by the rig (role 4, stream `0x50` type 1)
and by the opening pose of an animation (type 2). In `L03A`, **58 placed
objects of 77 have a multi-part model, and all 58 have a rig**.

Ombelll's documents disagree on how the transforms compose: their finding 33
says a pose gives the full transform of every part, while a section of
MODELFORMAT says they are concatenated. **The chain is right**, measured the
way the documents measure Bugs: assembled without the chain he is 150 units
tall and sits in a heap; with the chain he is **285**, a standing figure.

Two details:

- **The first block of an animation is not always a pose.** For model 112 it
  holds only "create part" records and leaves the object stacked on the
  origin. Blocks are read until every part with a mesh has received its
  transform.
- **Which pose** (rule superseded by 272): choosing by role number picked a
  degenerate stream; choosing the stream with the most TRS records turned
  model 112 from a heap into a recognizable **pirate**.

## 262 — UVs are scaled by (size − 1), not divided by 256

`PROVEN_BINARY` in Ombelll's documents (`FUN_0041cd50`), applied here. The
pixel coordinate is `u/255 · (size − 1)`, sampled at the **texel center**.
Dividing by 256 shifts by half a texel: invisible with nearest filtering,
visible with linear filtering or mipmaps (on a 16×16 texture half a texel is
3% of the surface). The direction of v is corrected by 271.

## 263 — The `.bmp` files in `Datas/bze` are not level previews

`PROVEN_RAW_DATA`. They are all 328,758 bytes, and the header declares
**256×1280 at 8 bits**: video memory dumps, not screenshots. They give no
ground truth for how a level looks.

## 264 — Two builds of `Bugs.exe`: the data addresses hold, the code addresses do not

`PROVEN_BINARY`. Ombelll's finding 208 describes two retail builds of
`Bugs.exe`, both 772,096 bytes, with identical level data: SHA-256
`6E15F920…`, to which every code address in Ombelll's documents belongs, and
`74AB71E1…` ("BBLIT release" in Ombelll's NATIVE_TRACE). The code addresses
in these notes (finding 280) come from `74AB71E1…`.

On that build the `.data` addresses of Ombelll's documents read correctly
(the level table, 111 entries of 24 bytes from `..\BZE\TITLE.BZE;1`), while
the `.text` addresses must be located again by byte signature: the shift is
not constant (+0x1A0 for the `CreateFileA` call sites in Ombelll's 208, +0x90
for the handlers of actions 0x17 and 0x19 here). The level files are the
same: `MERLIN.BZE` has the documented hash.

## 265 — Type 4 streams are animations

`PROVEN_RAW_DATA` + `REBUILD_VERIFIED`. The header of a `0x50` stream
carries a type at +2: 1 (rig), 2 (animation) and 4. Ombelll's MODELFORMAT
mentions 4 only once, with a question mark.

**Proof:** the chain of pose blocks (`u32` record count, `u32` time, then the
self-describing records) closes **exactly on the last byte of the resource in
205 type 4 streams of 205** (`L01A`, `MERLIN`, `L03A`, `L03ACOM`, `L03A2`),
as for types 1 and 2. They contain ordinary TRS records (107, 36, 181 per
stream in the examples) and almost always a box (type 9) per block: they are
animations of moving objects.

**Effect:** the census (`tools/census.py`) counted 35 dock objects
(10 + 6 + 19) with a multi-part model, a rig and **no pose**, hence assembled
with the identity, parts heaped on the origin. Accepting type 4 brings them
down to zero: model 161 is a standing palm again, 285 a sloping gangway, and
the mooring rope stops being a giant plank. The counter alone does not show
that the pose found is the right one; the before and after picture does.

**Not established:** what distinguishes 4 from 2. "4 carries a box per block,
2 does not" fits the counts but is not measured.

## 266 — REJECTED: "semi-transparent `0x4A`/`0x4E` faces are drawn opaque"

The reader takes the blend mode only in UV modes, because in modes
`0x4A`/`0x4E` the word at +10 falls inside the colors; faces of those modes
with bit 3 of the flag set would be drawn opaque. **Measured:** in the three
dock sections **0 faces of 4899** in mode `0x4A`/`0x4E` have bit 3 (their
flags are only `0x01` and `0x03`). Rejected for the dock only: the census over
all 53 playable levels finds **30** (L03C1 6, L04C3 6, L05A3c 12, L04C1,
L04D1, L04D2 2 each), and what the game does with them is not established
(census column `semi0`).

Side note from the same census: modes `0x34` and `0x38` do not appear in the
three dock sections, and flag bit `0x02` (double-sided in the PlayStation
TMD) is set on about a fifth of the faces of every mode. Whether it means
double-sided here is not measured.

## 267 — The sky dome follows the camera

`REBUILD_VERIFIED`, with a ground truth. In `L03A` object 0 (model 1, 231
faces) is at (0,0,0) and measures **367 x 245 x 367 m**, centered on the
origin: sky, sun, clouds and sea up to the horizon. The starting point is
about 187 m from the origin, on the edge of the dome: drawn fixed, only two
gray tips of it are visible.

Drawn first, without depth and translated with the camera, the scene matches
screenshots of the game: **the sun sets behind the stack of crates with the
ship's wheel**, which is impossible with a fixed dome.

Open: whether it also rotates partially with the view. The screenshots rule
out full rotation (the sun does not appear in every direction), not a partial
one.

## 268 — The x2 factor on the vertex color is wrong for the PC

`PROVEN_RAW_DATA` (pixels of the PC game) + `REBUILD_VERIFIED`. **Corrects
Ombelll's finding 16 for the PC version**: texture × vertex color × 2
(128 = neutral, "255 doubles") is the PlayStation convention, not the port's.
With x2 the viewer is about **twice as bright on everything** as screenshots
of the PC game in the same framing: salmon-pink hull instead of brown, bright
blue sea instead of navy blue. The sea is made of `0x4A`/`0x4E` faces
(solid-color 4x4 textures, 258), so it goes through the factor too. With
factor 1, hull, sea and sky come back almost identical to the game.

**The measurement** (median of corresponding zones, a PC screenshot against
the viewer in the same framing):

| zone | game | viewer x2 | viewer x1 |
|---|---|---|---|
| sea (solid-color face) | (0, 0, 63) | (0, 0, 125) — ratio 0.50 | **(0, 0, 63)** — ratio 1.00 |
| upper sky | (32, 58, 88) | (37, 113, 170) — 0.86 / 0.51 / 0.52 | (18, 57, 85) — 1.78 / 1.02 / 1.04 |
| hull | (89, 52, 41) | (163, 87, 65) — about 0.6 | (82, 44, 32) — about 1.1-1.3 |

The sea is the clean sample: a solid color, and it matches exactly. The red
of the sky and the hull diverge more because the zones are not the same pixel
for pixel and the color varies across the surface, but no zone is compatible
with x2. The viewer uses 1 by default; `--albedo 2` remains for comparison.

## 269 — CLOSED by 275: the sun's halo uses textures that no static file has

> **Closed by 275:** slots 3-7 are filled every frame by five type 2 objects
> with frames 361-364, faded yellow bands.

The glow around the sun is 10 faces of model 1 with blend 3 (B + F/4), almost
uniform yellow vertex color (about 255,255,50) and UVs over the whole
texture, so the faded shape must come from the texture: slots **3-7**, which
`L03A` does not register and no `.bze` file fills with anything resembling a
glow. The cumulative reading of 260 drew them as a striped olive fan, largely
a viewer blending defect as well (273).

## 270 — The sky dome, part by part

`PROVEN_RAW_DATA` for the structure; the orientation, left `OPEN` here, is
settled by 271. Model 1 of `L03A` has 7 parts, with a rig (resource 3) and an
animation (resource 4, role 131):

| part | height in the world | texture | what it is |
|---|---|---|---|
| 0 | from -8 to +151 m | 393 (4x4) + 1 and 2 (128x128) | sky vault and 14 **billboards**: islets with palms (1) and distant ships (2) on the horizon |
| 1 | from +18 to +55 m | 394 (4x4) | the yellow clouds |
| 2 | from -7 to +42 m | 395 (4x4) + slots 3-7 blended | the sun and its halo (269, 275) |
| 3 | from -94 to -6 m | 396 (4x4) | the sea up to the horizon |
| 4, 5, 6 | from -18 to 0 m | 8 (64x64) | the **sun's reflections on the water**; the animation moves exactly these three parts every frame |

Everything is consistent with the `(x, -y, -z)` conversion: sky above, sea
below, reflections below the horizon in the direction of the sun. The
billboards do not rotate; since the dome travels with the camera (267) they
always stay at the same distance, so the background depends on where the
camera looks, not on where it is.

**Billboard orientation (resolved by 271).** With v counted from the top the
14 billboards come out upside down; in the game they are upright. In their
records (`0x40`, flag `0x01`, UVs at the corners, indices `4c 4d 4f 4e`) the
bottom row of the texture (v = 255) is on the upper vertices, and u runs
backwards too: a 180-degree rotation. The dome's pose is the identity for all
parts, so the pose does not explain it. A count on vertical faces (L03A,
L01A, MERLIN) had the terrain mapped "upside down" about 3 times in 4 and the
props half and half; on symmetric textures such as wood and rock the
direction does not show, so that count alone did not decide.

## 271 — The texture v coordinate is counted from the bottom

`REBUILD_VERIFIED`, with ground truth. **Corrects 262** for the direction
(the scaling by size − 1 stays). The reading of `FUN_0041cd50` in Ombelll's
documents does not say which side v starts from; counting it from the top, as
for an image, is wrong.

**The symptom** was spread over four defects that looked independent:
"HANDLE WITH CARE" and "ACME" upside down on the crates (lines in reverse
order, letters flipped, reading left to right: a vertical flip, not a
mirror); the 14 billboards of the dome upside down (270); the white band with
the portholes missing on the ship; white and black triangles at the stern.

**The proofs:**

* with `v' = 255 - v` all four look as in screenshots of the game;
* a measurement that could have failed: on vertical terrain faces, with v
  from the top the texture comes out upside down **696 times against 238** in
  `L03A` (MERLIN 748 against 245, L01A 1065 against 854); with v from the
  bottom the same numbers become "upright". Walls, rocks and pier sides are
  drawn to stand upright, and a direction that flips them 3 times in 4 is the
  wrong one. The count alone is not enough (on wood and rock the direction
  does not show), but it points the same way as the lettering.

Textures exported as PNG do not change: they are already upright (the islet
billboard has the palms at the top). Only the mapping changes, in
`export_obj.uv_to_texture` (`tools/export_obj.py`), shared by the viewer and
the OBJ export.

## 272 — An object's pose is the one the game starts, not the one with the most records

`REBUILD_VERIFIED`, with the chain taken from Ombelll's findings; **replaces
the pose-choice rule of 261**.

Choosing, among an object's animations, the one with the most TRS records
picks role 185 for the normal carrot (model 55), whose initial pose has the
body **squashed to scale 0 vertically** (the carrot popping out of the
ground): it comes out short and stuck on the planks, while in the game it
floats tilted.

The game's chain: for type 14 objects (`FUN_00440120`, Ombelll's finding 188)
the initial state is **2, or 1 if 2 is missing**; slot 0 of its playlist is a
**key** (Ombelll's finding 89) looked up among the object's steps (`0x30`,
and `0x34` for the player); the step carries at +2 the **role** of the
animation (Ombelll's finding 84). `loadscript.export_level` exports states
and steps, and `montage.start_role` follows this chain.

**The proofs:**

* the chain reaches an animation the object actually owns for **73 rigged
  objects of 77** in `L03A` (L03ACOM 28/29, L03A2 100/108, L01A 135/139,
  MERLIN 28/39); the rest have no states, or their animation has no
  transforms, and fall back to the record count (census column `pos~`);
* four carrots of five start from role **163**, whose pose is **tilted by
  about 40 degrees and raised by 0.7 m**: the carrot floats whole, as in
  screenshots of the game;
* the fifth (object 114) starts from role 131, a neutral pose, and has a
  second state (236) leading to 185, "pops out of the ground": it is the
  carrot the game makes appear later, and it is no longer shown in its final
  form;
* Bugs (the player, whose steps are the `0x34` records) starts from role 35:
  hands on hips, as in the screenshots, instead of holding out a carrot.

Declared simplification: the still view draws the pose of the first block of
the animation (the running animation is in 278).

## 273 — Semi-transparent blending was off from the second frame on (viewer defect)

`REBUILD_VERIFIED`. A viewer defect, recorded because it hid other results.
The four PlayStation blend modes were implemented correctly but active only
in the first frame: the viewer enabled `GL_BLEND` once at startup, and the
pyglet HUD **disables** it after drawing text (`pyglet/text/layout/base.py`,
line 780: `glDisable(GL_BLEND)`). From the second frame on every
semi-transparent face was drawn opaque, including in every viewer capture
(taken after 0.6 s, i.e. dozens of frames).

**The symptom and the proof:** black squares under the island's plants. The
plant (model 192) has a shadow face in subtractive blend (type 2, B − F) with
a 64x64 texture 77% black and a dark gray silhouette (33,33,33): subtracted,
black removes nothing and the silhouette darkens the grass; drawn opaque it
is a black square. With blending "on" and "off" the square was identical, and
the terrain under the plant has no dark textures: the cause was OpenGL state,
not the data reading.

**After the fix** (blending and depth test re-enabled at the start of every
frame): plant shadows are soft silhouettes, underwater island edges are
transparent, the sun halo is semi-transparent. **Revises 269:** the "olive
fan" halo was largely additive faces (B + F/4) drawn opaque.

## 274 — Blue chests, falling crates and flames are template clones

`PROVEN_RAW_DATA` for who requests them and under what condition, `STRONG`
for the chests' placement, `REBUILD_VERIFIED` on screen.

Objects that the game shows (PC and PlayStation) but that are not placed by
the level are **templates** (block 0x08, with no position) cloned by a `0x31`
rule of a live object with effect `0x100`/`0x40000`, role at field +28, at
the parent's position and rotation (Ombelll's finding 194). `loadscript`
exports the `0x31` rules of every object. In `L03A`:

| what | who requests it | condition |
|---|---|---|
| **3 blue chests** (model 305, roles 764-766) | object 83, empty model with rig | `tabel1[114]` == 1, 2 or 3: three rules lay them out in three orders; other rules assign 1/2/3 with effect `0x2` (probability, thresholds 25000 and 20000). The order is **randomly drawn** |
| **8 green crates** (model 311) | 8 triggers on the piers | effect `0x8200100`: player target, radius 640; one bit of `tabel1[106/107]` per crate. In the game they fall when Bugs gets close |
| the "little dome" with the propeller (object 138/139, model 392) | it is a placed object | requests roles 902 (model 88) and 904 (model 95) |

**The chests' placement.** Their rule also carries bit `0x80`, and field +24
is 1, 2 or 3. The rig of object 83 has three child parts at
**x = -400, 0, +400**: reading "+24 = k-th child part" puts the three chests
in a row, as in a screenshot of the PlayStation version. A consistent
reading, not read in the code (refined in 279).

**In the viewer**, flag Cloned templates (`--clones 0/1/2`): Off (default),
At start (condition true with empty tables, Ombelll's finding 161, and no
distance target), All (whatever can appear). Rules are not evaluated over
time: the chests, ordered at random at runtime, appear only with All. Many
clones are transient effects (explosion stars, digging holes, carrots jumping
out), hence off by default.

**Open at this point:** the animated torch was found neither among the clones
nor among the objects (see 279); object 138 is not a torch but the little dome
with the propeller, which in the viewer is semi-transparent (all 14 faces in
additive blend) while on the PlayStation it looks solid; a "!" high in the
sky comes from At start clones.

## 275 — Eyes, sun halo, water and ripples are animated textures filled by objects

`PROVEN_RAW_DATA` for the rule and its numbers, `REBUILD_VERIFIED` on screen.
Corrects **260** and closes **269**.

**The rule.** An object of type **2** or **20** (opcode `0x13`) that carries
opcode **`0x0B`** is not drawn: every frame it writes into the texture slot
named by `0x0B` (u32) a frame chosen as follows:

* the frames are in one of its resources with opcode **`0x40`** (u32 offset,
  u32 size in section 4): a `0x41` model made only of 16-byte **`0x64`**
  primitives, texture id at +10, width and height at +12/+14. Frame k is the
  k-th record;
* type 2: the sequence is in a resource with opcode **`0x3F`** (u32 number of
  pairs, u32 offset, u32 size): byte pairs **(frame, duration in ticks)**;
* type 20: no sequence; `0x42` = **(first, last, duration)**, a loop.

**The proof that could have failed.** Across all the `.bze` files there are
**520** objects with `0x0B` in 79 files, all of type 2 (391) or 20 (129).
**None** of the 520 slots is registered by its own file, and they cover
**518 of the 545** ids that faces reference without the file registering them
(7875 faces). The remaining 27 are in models that no object places: over all
levels (`tools/census.py --all-levels`), drawn faces referencing an empty
slot are **0 of 277,588**.

Bugs's head shows the pattern: in **every** file it uses 8 consecutive ids,
and the 5th and 7th are never registered (L03A 291/293, title 241/243, L02A1
136/138, L03B 184/186, ...). They are the eyes.

**What they are in `L03A`** (14 slots, all filled by objects of the level):

| slot | frames | what | used by |
|---|---|---|---|
| 3-7 | 361-364, 16x32, faded yellow bands, back and forth 4 ticks each | **sun halo** | sky, 10 faces, blend B + F/4 |
| 202, 203 | 365-372 and 373-380, 32x32, loop of 8 at 2 ticks (type 20) | scrolling clouds and water with foam | model 104 |
| 204, 272 | 381-386, light stripes, then the empty 386 for 15 or 30 ticks | reflections on the water | models 104 and 239 |
| 336 | empty 386, then 381-385 | ripples | **96 terrain faces**, B + F/4 |
| 353 | 387-391, widening circles, then pause | circles in the water | **146 terrain faces**, B + F/4 |
| 291, 293 | 392, 64x32 | **Bugs's eyes** (a single frame, the same for both eyes) | model 315 |
| 307 | 311 | **Merlin's eye** | model 372 |

The 242 terrain faces of 336/353 are the bases of the posts in the water:
without their texture they come out as **lighter squares** (vertex color in
additive blend), which the game does not show. With the texture, almost
entirely black, only the stripes and circles remain in additive blend.

**What it corrects.** 260 explained the same slots with a table cumulative
across files (`title -> L03ACOM -> L03A`). That proof was weak: almost every
file registers slots 3-7 and 291/293, so any "companion" file would have
filled them; on screen it gave a barrel strap in place of the eyes and an
olive fan in place of the halo (269). After 275 no level has a drawn face
left to explain with the chain, and `textures.construct` (`tools/textures.py`)
no longer adds companion files (they can still be requested with `extra`).
That the game's table survives level changes remains true in the code (no
clearing routine), but nothing needs it to be drawn.

**In the viewer** animated slots change frame over time (flag Animated
textures; when off, the first frame of the sequence is shown). The tick
length, first assumed at 25 per second, is measured in 278: 15 per second.

**Still open:** in the game the halo is a solid, larger yellow disc; in the
viewer it has the right shape but is fainter (frame, blend or vertex color,
to be compared). Who chooses the starting phase: the five objects 3-7 share
the sequence, and the viewer starts them together.

## 276 — A vertex with bit `0x8000` is a copy of a vertex of another part and must be welded

`PROVEN_RAW_DATA` for the correspondence, `REBUILD_VERIFIED` on screen.

In a part's vertex list (16-byte records: x, y, z float, u32 id), some ids
carry bit **`0x8000`**. Every such id has **exactly one** vertex with the
same id without the bit, in another part: **2876 copies of 2876** in 8 files
(`L03A`, `L03A2`, `L03ACOM`, `L01a`, `MERLIN`, `L02A1`, `L04A1`, `L05A1`),
none orphaned, none with two owners. Faces name the id without the bit.

**The proof that could have failed.** With the starting pose (272) the copy
is at a median of **3.7 units** from its original, against 44 in local
coordinates: it is the same point expressed in its own part's system, right
in the modeling pose and wrong as soon as the parts move (up to **620
units**). Null hypothesis: among all the vertices of the **other** parts, the
declared original is the nearest to the copy **2197 times of 2876** (at
random it would be about 1 in a few hundred; most of the rest are nearly
coincident vertices).

**The rule**, in `export_obj.read_model`: the copy takes the position of the
original, already transformed with its part. It is the skin that holds the
joints together: without it Bugs's shoulders and arms and Merlin's robe and
face are open. `read_model(..., weld=False)` gives the old reading.

## 277 — In the `0x3C` triangle the first vertex is the one at +28, not at +14

`PROVEN_RAW_DATA`, `REBUILD_VERIFIED` on screen.

The textured Gouraud triangle (`0x3C`, 32 bytes) carries three UVs (+4, +8,
+12), three colors (+16, +20, +24) and three vertex indices (+14, +28, +30).
UV and color k go with the indices in the order **+28, +30, +14**, not
+14, +28, +30.

**The proof that could have failed.** Two triangles sharing an edge must give
the shared vertices the same UV and the same color. Trying the 6
permutations, and discarding pairs where all or none match:

| test | old reading | +28, +30, +14 | others (max) |
|---|---|---|---|
| colors, model triangles, 7 files | 6 | **1195** | 64 |
| UV, model triangles, 7 files | 27 | **418** | 67 |
| UV, `L03A` terrain, ripples (336/353) | **0** | **48** | 0 |
| UV, `L01a` terrain | 35 | **151** | 25 |

The same test on the `0x40` quads (24 permutations) confirms their current
reading (4706 against 2492 for the runner-up): the defect is only in the
triangles. The new order is a rotation, so the face winding does not change.

**On screen:** the ripples around the posts, previously split into two offset
half circles, are whole rings centered on the post; the spiral decoration on
the edge of the piers and the skull of the pirate flag (top left from the
camera at (202, 18, -117)) are fixed too.

**Not proven:** the flat triangle `0x34` has the same shape (first index at
+14, right after the third UV) but only 50 primitives in all the data and no
adjacent pair in the files tested: it keeps the old reading.

## 278 — An animation has one block per tick, and each block carries only what changes

`PROVEN_RAW_DATA` for the structure, `REBUILD_VERIFIED` on screen.

In animation streams (types 2 and 4) block times are 0, 1, 2, ... with no
gaps: a block is a tick. The first block carries the full pose, the following
ones only the TRS records of the parts that move (carrot 111: 17 blocks, from
the second on only the rotation of part 2). State therefore **accumulates**
block by block, with no interpolation. `rig.animation` returns the transforms
of every frame starting from the pose that `rig.construct` uses for the still
view (same block).

In `L03A` 29 placed objects have a starting animation that actually changes
something (spinning carrots and golden carrots, life buoys with the
propeller, pirates, ...). The carrot at ticks 0, 4, 8 is tilted left, facing
forward, tilted right.

**Ticks per second: 15, measured** in BizHawk on the PlayStation version
(NTSC-U), frame by frame, in front of a normal carrot: one turn in 68, 68 and
67 frames (203 in 3 turns). The carrot's animation has **17 blocks** and the
PlayStation shows them all before starting over: 17 ticks every 67.7 frames
at 60 Hz = **15.07 ticks per second**, one block exactly every 4 frames (the
logic runs at 30 per second, 0x76010).

**The last block is an end-of-loop placeholder**: it changes no part, so it
repeats the second-to-last frame. This holds for **135 animations of 135** in
L03A, L03A2, L03ACOM, L01a and MERLIN. In the PC game the carrot spins
without stopping, whereas keeping the block stops it for one tick every turn;
`rig.animation` drops it. Measured on the PlayStation; the PC should have the
same logic, not measured. The viewer repeats every animation in a loop, so
one-shot animations (a carrot popping out) are seen repeating.

**The barrel in the water** (model 239, templates 89 and 211) has two steps:
199, the rise, with which the game starts it (the top goes from 0 to 1.85 m
above the water in 30 frames), and 202, floating in a loop (31 frames, top at
about 1.96 m). Clones are animated too.

**The drawbridge** (objects 85 and 127-130, model 217) has four still stages
of 3 blocks: 118 raised, 119, 120, 121 lowered (depth 2.6 / 6.2 / 9.4 /
12.0 m), and the transitions 140, 141, 142 between one stage and the next,
198 all the way down, 199 all the way up. The game starts from 118.

## 279 — Sprites, nested clones and attachment points: the torches

`PROVEN_RAW_DATA` for the chain and for sprite blending, `STRONG` for the
attachment (a reading consistent with the data, not read in the code).

**Sprites.** A template with a `0x40` resource (frames, 275) and without
`0x0B` is a world sprite: `L03A` has 20. The `0x64` record carries width and
height at +12/+14 in world units, and the blend with the **same encoding as
faces**: bit 3 of the flag at +2 = semi-transparent, mode in bits 5-6 of the
word at +6. The torch glow (texture 250, black background) has flag 0x09 and
word 0x20: additive. The flame (218-222, 32x64, 5 frames of 3 ticks) has flag
0x01: opaque, with transparent pixels.

**The torch chain.** Two triggers (0x0A, at (23310, -1400, 9125) and
(10100, -1420, 8125)) clone the torch template (roles 671 and 861, model 165,
1.4 m tall). The torch, in its starting step (key 3), in turn clones the flame
(657/866) and the glow onto its own part 3, the top. The rule that clones the
flame a second time has key 157, another step (the torch going out?), and
does not apply at startup.

**Attachment.** With bit `0x80` of the effect, field +24 selects a part of
the parent. The **type 0xA** records of the animations mark one part per
tick: the top of the torch (part 3), the hand of the throwing pirate (part 23
of object 108), the three chest spots (parts 4, 3, 2). Reading adopted: the
k-th part marked `0xA`, and without markings the k-th child of the root
(274). It puts the flame at the top of the torch; the old reading would put
it at the base.

**In the viewer** clones are recursive up to three levels; in templates the
rules of the starting step that are true at startup apply. Sprites are
camera-facing squares at the attachment point.

**Sprite origin:** the `0x64` record carries no origin. In the game the flame
**rests** on the top of the torch (also in a PlayStation screenshot with the
torch lit on the islet), so the viewer draws every sprite with its bottom
edge on the attachment point. For the other sprites this is an extension, not
a measurement.

**Open:** the two models cloned together with the flame (670, 659).

## 280 — Anchors: parts removed from the pose (type 8, flag 0xB) and the rotation of action `0x26`

`PROVEN_RAW_DATA` for the removed parts, `PROVEN_BINARY` for the rotation
axis, `REBUILD_VERIFIED` on screen. **The speed is not measured.**

**What they are.** The anchors are the template of role **533** (model 168),
cloned by **4 triggers** (type 16, objects 145-148) with condition `0x27`
"bit off" on `tabel1[124]`, true at startup. The rig has three parts with a
mesh: 2 is the anchor, 3 the shadow, 4 a third piece. In the starting step
(key 267, role 248) the anchor is **2000 units (15.6 m) above** the trigger
and the shadow stays on the ground at scale 0.4.

**1. The type 8 record with flag 0xB removes a part.** In the rig, type 8
(flag 0) creates a part (Ombelll's finding 25); in animations type 8
**always** has flag 0xB (3914 records of 3914 in seven levels), and it had
not been read. Part 4 of the anchor receives it in pose 248 and no transform,
so it was drawn at the object's origin, a dark shape on the ground.

*The proof that could have failed:* if the record removes the part, a part
that comes back must be set again from scratch. After a `t8 fB` the part's
first TRS is **complete (flag 0xE) in 638 cases of 638**, against 2443 of
249k (about 1%) for an arbitrary TRS, which usually carries only the
rotation (flag 2).

*The rule:* `rig._apply_records` marks the part as removed until a TRS puts it
back; `rig.transforms` gives it a null matrix (degenerate faces, not drawn;
the OBJ export skips them). For the still pose a removed part counts as
decided, but a block that removes **everything** is not a pose: many streams
open like this (pirate, Merlin) and the real pose arrives in the next block.

*What changes* (161 objects of 1104 in L03A, L03A2, L03ACOM, L01a, MERLIN;
the census stays at zero): the pirates have one club instead of two; the
rabbit hole (model 108, 3 in L03A) shows the hole, previously covered by a
second mesh; a water ring at Bugs's feet disappears; carrot 114 is visible
only in its upper part; several objects whose pose never came out complete
now animate. 10 objects of L01a and MERLIN whose starting pose removes all
meshes stay invisible: in the game they start invisible (effects, emitters).

**2. Action `0x26` rotates around the vertical.** The addresses here are
those of build `74AB71E1…` (finding 264), whose code is shifted from the
addresses in Ombelll's documents (checked on the action table: handlers 0x17
and 0x19 fall 0x90 later): on the other build they should be located by byte
signature. The handler, at
`0x0042D070` (action table at `0x004AC6E0`), does
`[obj+0xC0]+0x12 += value*16 + index` (s16 at +4 and +6 of the action record,
i.e. `p[16]` and `p[18]` of the rule). `obj+0xC0` points to `obj+0xCC`
(`lea edx,[eax+0xCC]; mov [eax+0xC0],edx`, also in the loader at
`0x0042FEFB`), so the field is `obj+0xDE`, and the loader (`0x00430250`)
copies there the **second** s16 of the load script rotation: the Y.
`loadscript` exports the whole word as the fourth element of `action`
(Ombelll's finding 138).

The anchor's first rule in step 267 is `[0x26, 0, 136]`, with no condition
and with `0x8000`: the type 14 handler walks the step every tick (Ombelll's
finding 188), so the anchor turns by **136/4096 of a turn every logic tick**.
The other rules of the step describe the fall: rule 2 resets the object's
clock (action 25) with the player within 300, rule 5 looks for a role 725
(the pirates) within 160, rule 4 changes state when the clock (`0x16`,
`obj+0x22`) passes 30. State 501: 153 (the shadow grows), 348 (falls), 198
(on the ground).

**In the viewer** the groups of a rotating object have their own matrix:
rotation around the vertical through the object's point (exact when the base
rotation has zero X and Z, as for all 4 anchors). By default the anchors are
always shown (`tools/preferences.py`, role 533): in the air, spinning, with
the shadow on the ground. The fall is not simulated.

**Not measured: the speed.** With 2 rule passes per animation tick (logic at
30 per second, 278) one turn is 4096/136 = 30.1 passes, **1.0 s** (60
PlayStation frames). If rules ran once per animation tick it would be 2.0 s
(120 frames). A frame-by-frame measurement in BizHawk decides
(`RULE_PASSES_PER_TICK` in `tools/viewer.py`).

**Deliberately excluded:** pirate 110 rotates by 60×16 = 960 (84°) in each of
its four states, and each state ends when it gets near a waypoint (roles 58,
139, 140; effect `0x10000000` without `0x8000`): a patrol round, not a
continuous rotation. `_spin_speed` does not spin objects with such a step;
this belongs with moving enemies.

**The removed parts, object by object:**

* *The "vortex" at Bugs's feet* is not in the game at that spot. It is part
  36 (mesh 34, 1.56 m disc, additive, texture 303: a pinwheel), a child of
  the root. Pose 35 removes it; among Bugs's animations in L03A only **28**
  (state 30, step 37) places it, **3 m above the root** and rotating for 14
  ticks: the propeller ears with which Bugs slows his fall. With no pose
  placing it, it had been drawn at the part's origin, inside the planks. The
  same holds for parts 37 and 38 (two 2.5 m additive squares, textures 304
  and 305, trail rings): 38 appears only in 365 (states 21 and 90, 4 ticks),
  37 never in L03A. Bugs's model carries the meshes of all his effects; the
  animation decides which are visible.
* *The pirates' second club* (mesh 10, identical to mesh 15 of the one in
  hand) is removed **explicitly in all 19** of the pirate's animations in
  L03A and receives a position in none of them; likewise in the 27 of the
  L03A2 pirate (model 256). L03ACOM does not have this pirate. Pirates with
  two clubs in other levels are not ruled out; not checked. Not removed, it
  sat at the origin of part 11, child of 9: in the other hand, which is why it
  looked natural.
* *The rabbit hole* (model 108) has two meshes of the same shape with
  different textures: 1 with the hole (207/208), 2 without (208/209). The
  object has a single animation (149), used by both its states, which always
  removes 2: from the object's data alone the hole always looks open. L03A
  has three. **100** (221.1; -116.0 m) is under a crate that Bugs moves;
  **99** (236.3; -155.9) is on the island: roles 210 and 209, a pair. In the
  game, entering the hole under the crate activates the hole of the other.
  In the data both always let you in (action 47, within 200); what changes
  the look of 99 is not in its animation and has not been found. **62**
  (22.9; -32.5, near the start) lets you in (within 400) only with bit 0x80
  of `tabel1[102]`, which object 97 sets in step 199. Object 97 is the
  **explosive barrel** (model 157) sitting on the hole; in the game the hole
  opens after the barrel explodes, lit with the torch. In step 199 the barrel
  clones the explosion (roles 548 and 669, the white star) and its pieces
  (662), sets the bit and switches itself off (effect 0x10000). The link with
  the torch is NOT proven: state 3 of the barrel has condition `0x0C`
  (`player+0x17c`) on value 69, perhaps "Bugs is holding the torch". The
  viewer shows all the holes open.

**Open:** the anchor is tilted by about 40° in its own plane (edge-on, the
shank is vertical): that is how the model is, to be compared with the game.
The third piece (part 4) appears in state 404 (roles 371 and 211) at +398 in
z: perhaps the planted anchor.

## 281 — The `_8` variants are not in the level table

`PROVEN_BINARY` for the table, `PROVEN_RAW_DATA` for the files.

The level table of `bugs.exe` (111 entries of 24 bytes starting from
`..\BZE\TITLE.BZE;1`; the index is the LevID) names 111 files. The game data
contains nine `_8` files that do not appear in it: `L01D1_8`, `L01D2_8`,
`L03A_8`, `L03A2_8`, `L03ACOM_8`, `L03B_8`, `L03C_8`, `L04B3_8`, `LB04_8`.
They have the same number of objects with a model as the levels of the same
name (for example 77 for `L03A` and `L03a_8`), so they are copies or variants.
Without an entry in the table the game does not load them by LevID; the
viewer lists them under Extra.

**What differs** (six pairs: `L03A`, `L03A2`, `L03ACOM`, `L01D1`, `LB04`,
`L04B3`): both files have 10 sections; sections 2 and 5-10 are identical byte
for byte, only 1 (load script), 3 (textures) and 4 (models and terrain)
differ, by a few KB. `L03a_8` has 281 objects against 282 and 439 textures
against 442; `L04b3_8` has identical textures. They are **not** 8-bit texture
versions: the share of 4-bit and 8-bit TIMs is the same (`L03A` 413/29,
`L03a_8` 407/32). Nor are they the language suffix (`_0`, `_1`, `_3`), which
only concerns the `L_*` loading screens. Most likely another revision of the
same levels; which objects and textures change has not been listed.

**Cross-check.** The table agrees with an independent LevID spreadsheet (row
r = LevID r + 1) for all 70 entries the viewer uses: title and note are
compared word for word by `tools/diagnostics/check_levels.py`, which catches a
swapped file or a wrong note introduced on purpose. The table also names
files that are not in the game data: `LANGUAGE`, `LB05`, the five `DEMO*`,
`SCREEN4`, `SCREEN5`.

## 282 — The `0x1000` sectors: one quad per record, in two vertex orders

`PROVEN_RAW_DATA`.

Ombelll's finding 15 and MODELFORMAT ("Modus 0x10") describe terrain sectors
with modus `0x1000` as invisible boundary and collision faces: a 20-byte
record with one quad in the chunk's global vertex indices. Measured on the 79
levels of the viewer's menu (`tools/diagnostics/check_walls.py`):

- **1527** records in **26** levels (none in `L03A`); all 20 bytes long,
  `n_bound_faces` 0, count 1. One record in `CCEND` reads as 16384 bytes long:
  that level does not build anyway.
- The four `u16` at `+8` are **all** within the chunk's vertex count (1527 of
  1527), and **all** 1527 quads are vertical (normal within 0.2 of the
  horizontal plane): "curtains".
- **The vertex order is not fixed.** Taken as a fan (0,1,2,3) the quad is
  convex in 1434 cases (11 of them in both orders), taken in PlayStation Z
  order (0,1,3,2) in 104; 93 quads are convex **only** in Z order. The viewer
  takes the order that gives a convex quad.
- The last 4 bytes (`+16`, a `u32`) hold small numbers (most often 5, 9, 6,
  4, 2): **not read**. A surface or collision type is a guess.

The viewer draws them only on request (flag 0x1000 faces, off by default).
Every other group, the terrain bounds (the starting camera) and the triangle
count are byte-identical with and without them in 78 of 78 levels. Whether
they act as walls in the game: see 288.

## 283 — Faces you can see and cannot stand on

`PROVEN_RAW_DATA` for the reading, a declared rule for the classification.

The game does not collide with the terrain it draws but with the collision
heightmap (block `0x36`, Ombelll's findings 110-116). `tools/collision.py`
reads it as those findings describe: 68-byte records, a `u16` per 320-unit
cell, 8×8 tiles of signed height bytes, `0x7E`/`0x7F` = no ground, offsets
relative to the record count. Checks (`tools/diagnostics/check_collision.py`,
79 menu levels):

- **479 of 479** records have cells × 320 == extent on both axes;
- at the centre of the visible walkable faces the heightmap ground is a
  median **7 units** (about 5 cm) from the face, against **147** for a random
  cell of the same block: game coordinates are vertex + chunk displacement,
  Y down, as for the rest of the terrain.

**Which way is up.** Among the faces with matching ground below, 8384 have a
positive Y normal (in the game's Y-down space, with the file's winding) and
59 a negative one: positive is up. Faces with a negative normal are the
undersides of docks and platforms, and they are left out.

**The rule** (viewer flag No collision): a face with an up normal within
about 45° of vertical has no collision if, at its centre, no block has ground
within **100 units** of it, the game's step height (Ombelll's finding 116).
Over the menu levels that is **20,967** faces. On a 1-in-5 sample the reasons
are: sub-cell marked `0x7E`/`0x7F` 2693; ground more than 100 units lower
(you drop) 646; higher (the face is under the real floor) 455; outside every
block 298. In `L03A` it marks the shallow-water rims of the islands and under
the edges of the docks, not the planks you walk on.

Not covered: walls and ceilings (swept, not queried), objects (their own
boxes, 284), faces only partly over ground (only the centre is tested).

## 284 — One box per object: the invisible wall above the glass in `L05A3C`

`PROVEN_RAW_DATA` for the boxes; that this box is the invisible wall met in
the game is an explanation, not yet measured in the game.

Above the glass fence in `L05A3C` (the Mastermind room) there is an invisible
wall that is not a `0x1000` sector (282), and the collision heightmap has no
hard wall there either. It is an object's box. Objects collide through the
box in record type 9 of their animation (Ombelll's finding 123: six `s16`
corners in the object's space, tested rotated with the object by
`FUN_004313a0`). The viewer draws it (flag Collision boxes;
`montage.collision_box`: the first type 9 record of the starting pose
stream).

- Object **24** (model 81) is the glass fence with its two pillars, standing
  across the 4×4 grid of floor tiles (objects 25-40, one 320-unit box each).
  Its box is a slab **2648** units wide, **102** deep and **748** high (about
  20.7 × 0.8 × 5.8 m): the full height of the pillars across the full width.
  The glass is lower; above it the box goes on, hence a wall you do not see.
- Object **84** (model 292), the column of stars in the middle of the room,
  has a box **1300 × 19,332 × 1300**: about 150 m tall.
- In both cases the box is exactly the extent of the model's vertices: one
  box around the whole model, so every gap under it collides.

3892 boxes over the menu levels (boxes as large as the level in plan, sky
domes and sea, are left out: they would cover everything). With and without
them every other group is byte-identical (`check_walls.py`).

## 285 — Zone rules: effects at +16; the zones that kill or bring you back

`PROVEN_RAW_DATA`.

In the 32-byte `0x33` record of a zone the effect word is at **+16**, not at
+20 as in the object rules (`0x31`): condition at +8, action at +11, effects
at +16, the three parameters at +20/+24/+28 (Ombelll's finding 100 counts
three parameter words). Check: the six recovery-net zones of `L04A2` carry
effect `0x40000000` and parameters **(7900, −15520, 5000)** at +20..+28, the
landing point given in Ombelll's SPEEDRUN notes, in zones 33, 35, 36 and 37.
With the effects read at +20 no rule in the corpus has either bit. The zone's
box is origin + (extent X, extent Z), and in Y from its plane up by the
negative "lower bound" of opcode `0x1C`; the fourth word is the plan radius as
a `u16` (40,481 for `L03A`'s 32,569 × 24,041, √ = 40,480).

Over the menu levels: **165** zones with effect `0x200000` (death: animation
series and life counter cleared, Ombelll's finding 169) in 46 levels, 15
teleport zones in 4, 9 damage zones (action `0x48`) in 3, 70 checkpoints in
57. The largest death zones cover the whole level: the sea of `L03A` at
Y −300, the abyss of `L05A5`. The viewer calls a zone covering at least half
the terrain plan the **death floor** (flag Death floor, 23 zones); the other
153 are death zones (flag Death zones). Rule conditions are not evaluated.

## 286 — What you see against what you stand on: invisible ground, landing pixels, fake walls

`PROVEN_RAW_DATA` for the heightmap reading (283); the classifications are
declared rules, matched against cases known from the game.

- **Invisible ground** (part of flag Ground): heightmap ground with no
  visible up face within 100 units at the centre of its 40-unit sub-cell. In
  `L01A` it draws, floating in the pit, the octagonal platform that only the
  night variant `L01D1` shows.
- **Landing pixels**: a sub-cell with ground whose 4 neighbours in the same
  block have none: 40 × 40 units, about 30 cm. `L01B` has 18 (in the game one
  can land on one in free fall in the pit); 601 over the menu levels.
- **Hard walls**: the edges of the `0x7F` sub-cells, walls at any height
  (Ombelll's finding 116). In `L03D1` they line both sides of the round door
  and of the gate; above the gate the object box (284) is the invisible wall
  met in the game.
- **Fake walls** (withdrawn in 288): vertical terrain faces you pass through.
  The open side is the one opposite the file normal (on vertical faces with
  ground on both sides it is the lower side 2094 times in 2528, the same
  convention as for the up faces); standing there at your ground's height,
  behind the face there is neither a `0x7F` sub-cell nor ground more than 100
  units above you. 20,936 faces over the menu levels; in `L01B` they are the
  inner walls of the canyon ring, which in the game have no collision.

Every other group is byte-identical with and without these overlays in 78 of
78 levels (`check_walls.py`). Not covered: object faces and platforms.

## 287 — Collision blocks are stacked slabs; their top as a ceiling is only a candidate

`PROVEN_RAW_DATA` for the stacking; the ceiling is a hypothesis with a
counter-example count.

Field +24 of a collision record is called "bottom Y" in Ombelll's finding
110; with the game's Y pointing down it is always **above** the +20 plane,
i.e. the top of the block. The block is a slab from +20 up to +24, and the
blocks of one area stack exactly, base on top (`L01B` area 9: 960 → −1920 →
−2448 → −2880 → −9280). The box at +36 repeats it (origin, then size with
height +24 − +20). `L03D1` is a single layer everywhere, 0 → −6400, about
22 m above its highest terrain.

The top of the highest slab of each stack is the natural candidate for a
ceiling that closes a level. It is not a ceiling everywhere: in **37 of 297**
stacks over the menu levels the collision ground of the stack rises above
that top, and nothing can stand above a real ceiling. Median distance
between the highest collision ground and the top in the other 260: 4440
units. To be settled in the game. The viewer draws the stacks as Area boxes
(288).

## 288 — The viewer's collision flags, revised against the game

Declared rules; each change follows something observed in the game.

- **The 0x1000 terrain faces are not walls.** In `L03D1` one stands where the
  real invisible wall is an object box (284) and the other stops nothing. So,
  at least there, they do not act as the invisible boundary walls of
  Ombelll's finding 15 and MODELFORMAT "Modus 0x10". 282 stands as a reading
  of the format; what the faces are for is open (triggers, loading planes?).
  They have their own flag, 0x1000 faces.
- **Invisible walls = hard walls with nothing drawn.** The heightmap's `0x7F`
  edges (Ombelll's finding 116) with no visible near-vertical face, of the
  terrain or of a placed object in its starting pose, passing within ±2
  sub-cells (80 units) of the edge at the panel's height. `L03D1`: 706 of
  2942 hard-wall panels; `L03A`: 56 of 114.
- **No collision, safe or trap.** From the centre of a no-collision face the
  fall meets either ground (safe, bright cyan) or first a zone that kills,
  hurts (action 0x48) or teleports (trap, faint dark cyan). The lava of
  `L03D1` is a trap over its death slab, except a strip at z 195–290 just
  outside the slab: a candidate for the safe spot on the lava known from the
  game. `L03D1`: 45 safe, 451 trap.
- **Fake walls withdrawn**: screenshots from the game showed the flag marking
  walls that clearly stop you.
- **Area boxes instead of the ceiling**: each heightmap stack drawn as a
  whole box, edges only (287: the top is a ceiling at most in places). Not
  verified.
- Hard walls are drawn as continuous panels (base 16 units under the lowest
  ground of the run, top 5 m over the highest); Ground is drawn 16 units over
  the heightmap, above the textures it matches.
- A viewer defect found on the way (per-model face stamp cached by `id()` of
  a face list whose id could be reused after it was freed: IndexError) is
  fixed; `check_walls.py` and `check_level_cache.py` rerun.
