# AnyMakerToolMap

**English** · [Русский](README_rus.md)

Repo: <https://github.com/NicRoss512/AnyMakerToolMap> · Site: <https://nicross512.github.io/AnyMakerToolMap/>

**Interactive map of your Anymaker save — and a part search across the whole world.**
A single HTML file: double-click it and everything runs inside the browser.
No internet needed, and your save never leaves your computer.

![AnyMakerToolMap — save map and part search](img/img1.png)

What it does:

- drop a ZIP of your save and search the entire world: `engine`, `battery`,
  `wheel`, `food_`, `keycard`… 600–1000 distinct names, half a million objects;
- shows every hit **on the map** with coordinates, the tile (`104_117`) and the
  grid square (`L 12`);
- **categories taken from the game's own data** (building parts, furniture,
  food, clothing, weapons, electrics…) — “only / except” chips cut the noise in
  one click;
- a separate **In dungeons** filter — underground stops getting in the way of
  your surface search;
- player positions (all of them in co-op), a vehicles layer, CSV export;

---

## Quick start

**Online (GitHub Pages):** <https://nicross512.github.io/AnyMakerToolMap/>

**Locally:**

1. Download `save_map.html` and `worldmap.png` **into the same folder**.
2. Zip up your save (how — below).
3. Drag the ZIP onto the right-hand area.
4. Type `engine` into the search box and tick the names you want.

---

## 1. Where the save lives and how to zip it

Saves are here:

```
%appdata%\Anymaker\saves\
```

(paste that into the address bar in Explorer). Inside you'll find one folder per
save, each containing `meta.json`, `scene.json`, `tiles/`,
`dungeons/`.

**How to zip it:**

- **Windows Explorer:** open `saves`, right-click the save folder →
  *Send to → Compressed (zipped) folder*.
- **7-Zip / WinRAR:** right-click → *Add to archive* → format **zip**.
- **Terminal:** `cd %appdata%\Anymaker\saves && tar -a -c -f save.zip save_dir`
  or `zip -r save.zip save_dir`.

Things that matter:

- it must be a **ZIP** (`.rar` and `.7z` are not supported);
- the archive must hold **the files themselves** (`meta.json`, `scene.json`,
  `tiles/*.json`, `dungeons/*.json`) — a folder inside is fine, the tool walks
  every `*.json` at any depth;
- no need to unpack it — the archive is read straight from browser memory
  (JSZip);
- a 100 MB save parses in roughly 10–30 seconds, with a progress indicator.

You don't have to rename the archive; if the browser is picky about the
extension, the tool has a file-picker button.

---

## 2. The map

`worldmap.png` is the map exported from the game (4096×4096; the map is not
procedural, it is the same for every world). Put it **next to
`save_map.html`** and it is picked up automatically. If the file isn't there,
the tool asks you to drop the PNG by hand.

The image is only used to draw the dots: search, coordinates, tiles, squares and
CSV export all work without it.

---

## 3. Search

The **Find** box matches a substring of the internal name or of the human name
from the game; separate several variants with commas (`wheel,tyre`). The
**Exclude** box throws out the junk: `barrel` + exclude `_a` leaves only
`barrel_b`.

Case doesn't matter. The result is a list of names with counts; ticking them
(«Select all» / «Top 20») turns them into dots on the map and into the hit list.

Real numbers from a test save: `engine` — 31 names, 1391 objects; `battery` —
591; `wheel` — 565; `food_` — 658; `keycard` — 8.

---

## 4. Categories

Under the search row sits a row of chips: one per group, with the object count
from your save. Clicking cycles three states: **“only this group” → “except this
group” → back to normal** (green / struck through / plain). Several can be on at
once.

Groups: building parts, furniture, engine, wheels, mechanics, gas and liquids,
electrics, controls, weapons, ammo, clothing, food and drink, medicine, storage,
misc, roads and signs, cargo and containers, nature, world objects, living,
vehicles and buildings.

They are **read out of the game's own files** (`*_definitions.json`), not made
up: items use the `class` field (it is more precise than `category` — wheels have
`class=wheel` but `category=accessory`), parts use the
`is_building_furniture` / `is_building_component` flags, and props are grouped
by name. Coverage on the test save is 100 % of names.

Why it matters: on a large save (511 k objects) **62 % of everything is building
parts** (`building_b_wall` alone is 142 thousand). One “except building parts”
chip turns a half-million-dot soup into ~196 thousand meaningful points.

The set of pressed chips is remembered in the browser.

---

## 5. Dungeons

The first chip in the row is **In dungeons**, with the same “only / except”
logic. It's a separate filter because a dungeon is a property of the point, not
of the item: the same name occurs both on the surface and underground. In the
test save **25 % of all objects sit inside three dungeons**, so “except
dungeons” is the fastest way to drop everything you can't walk to anyway.

![Part search: green dots are the hits on the map](img/img2.png)

---

## 6. What you see on the map

| colour | what it is |
|---|---|
| turquoise | every object in the save (the “All objects” layer, off by default) |
| green | hits for the current search |
| amber, labelled `P1`, `P2` | players |
| blue diamonds | save tiles |

Layers are switched in the **View** section. Wheel zooms, drag pans; when you
zoom in, every object in the frame is drawn (duplicate merging only kicks in
above ~80 thousand points in frame).

The **A-P / 00-15** grid: letters run vertically bottom-to-top, digits
horizontally left-to-right; bottom-left square is `A 00`, top-right is `P 15`.
The **Order** button flips it (in case the game does it the other way), and the
grid layer is off by default so it doesn't cover the map.

---

## 7. Navigation

- **Square** — jump to a square: `L 12`
- **Tile tx_ty** — jump to a tile: `104 117`
- **World X / Z** — jump to world coordinates: `80000 52000`

The **«☰»** button on the seam between the panel and the map hides the panel —
the map then fills the whole window.

---

## 8. Players

Positions come from `scene.json` → `peers.peers[]`. In single player there is
one entry (you), in co-op one per player. The “Players” layer is on by default:
an amber dot labelled `P1…` on the map, and a list in the panel with
coordinates, tile and square (click to fly there).

---

## 9. CSV export

The **CSV** button saves every current hit:

```
name;worldX;worldZ;worldY;tile;square;source;zone;category;display_name
food_cola;83987.7;53644.2;32.9;103_120;K 11;on the ground;surface;Food & drink;Cola
```

`source` is where the item came from (on the ground / on a vehicle / in a
container / in an NPC inventory), `zone` is the surface or `dungeon N`,
`display_name` is the human name from the game.

---

## How it works

- **The save** is a pile of JSON chunks: `tiles/tile_<tx>_<ty>_*.json` (the map
  is cut into 512×443 m diamonds), `dungeons/`, `scene.json`, `meta.json`.
- **Names** of items live in `item._type`, while parts sold as a “blank” keep
  theirs in **`component_def`**: `vehicle_editor_add_component` with
  `component_def: mechanical_junction_abs`. Without that field, searching
  `engine` found nothing at all (0 instead of 1391).
- **Categories** are built from the game files by `tools/make_cats.py`
  (details in the full documentation). The game files themselves are not part of
  this repository — that's the game's data, copy them from your own install.
- **Map calibration**: `px = (X − 74484.08) / 3.180124224`,
  `py = (58513.82 − Z) / 3.180124224` (4096×4096 px, 161 px per tile). Derived
  from 5 794 roadside objects: median distance to a road on the map is 0 pixels.
  The full calibration is in the documentation.
- **Nothing is uploaded**: JSZip reads the archive in browser memory, all the
  code sits inside one file, and there are no network requests at all.

---

## Tools in `tools/`

| file | what it does |
|---|---|
| `chunk_scan.py` | recon by chunk: walks every JSON in the save (folder or ZIP, standard library only) and dumps all names with counts, the field schema, word frequency, sample objects |
| `make_cats.py` | builds `cats.js` — the category lookup from the game's definition files |
| `cats.js` | 1161 ids → group + human name; inlined into `save_map.html` |
| `build.py` | build step: `python3 build.py` injects `jszip.min.js` and `cats.js` into `_template2.html` |
| `_template2.html` | the source of `save_map.html` (edit this one, not the built file) |
| `jszip.min.js` | JSZip 3.7.1 — inlined so the tool works offline |
| `mapref.py` | “world ↔ pixel ↔ square ↔ tile” conversions from the command line |
| `tilemap.py` | pure tile-grid geometry |
| `unlocks_tool.py` | `unlocks.txt` ↔ JSON (decode, re-encrypt for another account, merge) |
| `extract_points.py` | dump every object of the save into `points.npz` |
| `grid_table.csv` | all 256 map squares: pixels, world bounds, tiles inside |

Quick ones:

```bash
python3 tools/chunk_scan.py path/to/archive.zip        # what's in this save
python3 tools/mapref.py world 85000 52000              # what's at this world point
python3 tools/unlocks_tool.py decode unlocks.txt <SteamID64>
```

---

## Full documentation

`docs/README_FULL.md` — everything in one place: the `unlocks.txt` format, tile
grid geometry, map calibration, field-by-field chunk breakdown, how categories
are put together. It is in Russian; the English README is this file.

---

## Disclaimer

An unofficial fan tool, not affiliated with the developers of Anymaker. The game
is only read: the tool never modifies save files, and the save itself never
leaves your computer. The game's definition files are not part of this
repository — copy them from your own installation.
