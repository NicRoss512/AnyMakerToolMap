#!/usr/bin/env python3
"""
Anymaker — привязка карты worldmap.png (4096×4096) к мировым координатам.

КАЛИБРОВКА (подобрана по 5 794 придорожным пропсам сейва: медианное
расстояние до дороги на карте = 0 пикселей, 90 % объектов ближе 16 px = 50 ед.)

    units_per_pixel = 512/161 = 3.18012422      -> ровно 161 пиксель на тайл по X
    origin  X = 74484.08   (мир X в левом крае картинки)
    origin  Z = 58513.82   (мир Z в ВЕРХНЕМ крае картинки)
    flip_Z  = True         (Z растёт вверх по картинке)

    px = (X - OX) / S          X = OX + px*S
    py = (OZ - Z) / S          Z = OZ - py*S

Квадраты карты: сетка 16×16, ячейка 256 px.
Столбцы — буквы A…P слева направо, строки — числа 00…15 снизу вверх.
Левый нижний квадрат = A 00.

Команды:
  python3 mapref.py world 85000 52000     что в этой точке мира
  python3 mapref.py pixel 2000 1500       что в этом пикселе карты
  python3 mapref.py grid  G 07            границы квадрата + тайлы в нём
  python3 mapref.py tile  104 117         где тайл на карте
  python3 mapref.py table                 вся таблица квадратов
  python3 mapref.py overlay               нарисовать тайлы сейва поверх карты
"""
import math
import os
import sys

# ------------------------------------------------------------------ constants
S = 512.0 / 161.0          # 3.1801242240 world units per image pixel
OX = 74484.08              # world X at image px = 0
OZ = 58513.82              # world Z at image py = 0 (top row)
FLIP_Z = True

IMG = 4096                 # map size, px
CELL = 256                 # grid cell, px
N = IMG // CELL            # 16
LETTERS = "ABCDEFGHIJKLMNOP"
# Порядок подписи клеток (см. save_map.html, переключатель «Порядок»):
#   SWAP=True  -> буквы A-P по ВЕРТИКАЛИ (снизу вверх), цифры 00-15 по горизонтали (слева направо)
#   SWAP=False -> буквы A-P по горизонтали (слева направо), цифры 00-15 по вертикали (снизу вверх)
# В обоих случаях левый нижний квадрат = A 00, правый верхний = P 15.
SWAP = True

TILE = 512.0
TZ = TILE * math.sqrt(3) / 2.0        # 443.4050067
SHEAR = TILE / 2.0                    # 256


# ------------------------------------------------------------------ transforms
def world_to_pixel(x, z):
    return ((x - OX) / S, (OZ - z) / S if FLIP_Z else (z - OZ) / S)


def pixel_to_world(px, py):
    return (OX + px * S, OZ - py * S if FLIP_Z else OZ + py * S)


def world_to_tile(x, z):
    b = z / TZ
    ty = math.floor(b)
    u = (x - SHEAR * z / TZ) / TILE
    tx = math.floor(u)
    return int(tx), int(ty), u - tx, b - ty


def tile_corners(tx, ty):
    ax = TILE * tx + SHEAR * ty
    az = TZ * ty
    return [(ax, az), (ax + TILE, az), (ax + TILE + SHEAR, az + TZ), (ax + SHEAR, az + TZ)]


def tile_center(tx, ty):
    return (TILE * tx + SHEAR * ty + TILE / 2 + SHEAR / 2, TZ * (ty + 0.5))


def grid_name(col, row):
    """Подпись клетки. col = столбец слева (0..15), row = ряд снизу (0..15)."""
    return (LETTERS[row], col) if SWAP else (LETTERS[col], row)


def grid_cols_rows(letter, num):
    """Обратно к подписи: -> (col, row)."""
    return (num, LETTERS.index(letter.upper())) if SWAP else (LETTERS.index(letter.upper()), num)


def pixel_to_grid(px, py):
    """-> (буква, число) или None вне картинки."""
    if not (0 <= px < IMG and 0 <= py < IMG):
        return None
    col = int(px // CELL)
    row = int((IMG - 1 - py) // CELL)          # 0 = bottom row
    if not (0 <= col < N and 0 <= row < N):
        return None
    return grid_name(col, row)


def grid_to_pixel(letter, row):
    """-> (x0, y0, x1, y1) pixel box of the cell (y grows downward)."""
    col, row = grid_cols_rows(letter, row)
    x0, x1 = col * CELL, (col + 1) * CELL
    y1 = IMG - row * CELL                       # bottom edge (larger py)
    y0 = y1 - CELL
    return x0, y0, x1, y1


def grid_box_world(letter, row):
    x0, y0, x1, y1 = grid_to_pixel(letter, row)
    wx0, wz0 = pixel_to_world(x0, y1)           # bottom-left  (py max)
    wx1, wz1 = pixel_to_world(x1, y0)           # top-right    (py min)
    return wx0, wz0, wx1, wz1


def tiles_in_pixel_box(x0, y0, x1, y1):
    """tile indices whose rhombus overlaps the pixel box."""
    out = set()
    cs = [pixel_to_world(x0, y1), pixel_to_world(x1, y1),
          pixel_to_world(x0, y0), pixel_to_world(x1, y0)]
    txs = [world_to_tile(c[0], c[1])[0] for c in cs]
    tys = [world_to_tile(c[0], c[1])[1] for c in cs]
    for tx in range(min(txs) - 1, max(txs) + 2):
        for ty in range(min(tys) - 1, max(tys) + 2):
            p = [world_to_pixel(*v) for v in tile_corners(tx, ty)]
            px_ = [q[0] for q in p]
            py_ = [q[1] for q in p]
            if max(px_) >= x0 and min(px_) <= x1 and max(py_) >= y0 and min(py_) <= y1:
                out.add((tx, ty))
    return sorted(out)


# ------------------------------------------------------------------ cli
def _fmt_tile(t):
    tx, ty, a, b = t
    return "тайл %d_%d  (a=%.3f b=%.3f)" % (tx, ty, a, b)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--across"]
    if "--across" in sys.argv:
        SWAP = False            # старый порядок: буквы по горизонтали
    if not a:
        print(__doc__)
        sys.exit()

    if a[0] == "world":
        x, z = float(a[1]), float(a[2])
        px, py = world_to_pixel(x, z)
        g = pixel_to_grid(px, py)
        print("мир  X %.1f  Z %.1f" % (x, z))
        print("пиксель карты  x %.1f  y %.1f" % (px, py))
        print("квадрат  %s %02d" % g if g else "квадрат  вне картинки")
        print(_fmt_tile(world_to_tile(x, z)))

    elif a[0] == "pixel":
        px, py = float(a[1]), float(a[2])
        x, z = pixel_to_world(px, py)
        g = pixel_to_grid(px, py)
        print("пиксель  x %.1f  y %.1f" % (px, py))
        print("мир  X %.1f  Z %.1f" % (x, z))
        print("квадрат  %s %02d" % g if g else "квадрат  вне картинки")
        print(_fmt_tile(world_to_tile(x, z)))

    elif a[0] == "grid":
        letter, row = a[1].upper(), int(a[2])
        wx0, wz0, wx1, wz1 = grid_box_world(letter, row)
        x0, y0, x1, y1 = grid_to_pixel(letter, row)
        print("квадрат %s %02d" % (letter, row))
        print("  пиксели  x %d…%d   y %d…%d" % (x0, x1, y0, y1))
        print("  мир      X %.0f…%.0f   Z %.0f…%.0f" % (wx0, wx1, wz0, wz1))
        print("  размер   %.0f × %.0f ед. мира (%.2f × %.2f тайла)"
              % (wx1 - wx0, wz1 - wz0, (wx1 - wx0) / TILE, (wz1 - wz0) / TZ))
        print("  тайлы:  " + " ".join("%d_%d" % t for t in tiles_in_pixel_box(x0, y0, x1, y1)))

    elif a[0] == "tile":
        tx, ty = int(a[1]), int(a[2])
        cx, cz = tile_center(tx, ty)
        px, py = world_to_pixel(cx, cz)
        g = pixel_to_grid(px, py)
        ps = [world_to_pixel(*v) for v in tile_corners(tx, ty)]
        print("тайл %d_%d" % (tx, ty))
        print("  центр мира  X %.1f  Z %.1f" % (cx, cz))
        print("  центр на карте  x %.1f  y %.1f" % (px, py))
        print("  квадрат  %s %02d" % g if g else "  вне картинки")
        print("  углы ромба на карте: " +
              " ".join("(%.0f,%.0f)" % (q[0], q[1]) for q in ps))

    elif a[0] == "table":
        print("%-6s %11s %11s %11s %11s   %s" %
              ("кв-т", "X нач", "X кон", "Z нач", "Z кон", "тайлы"))
        for row in range(N - 1, -1, -1):
            for col in range(N):
                L, num = grid_name(col, row)
                wx0, wz0, wx1, wz1 = grid_box_world(L, num)
                x0, y0, x1, y1 = grid_to_pixel(L, num)
                tl = tiles_in_pixel_box(x0, y0, x1, y1)
                print("%-6s %11.0f %11.0f %11.0f %11.0f   %s" %
                      ("%s %02d" % (L, row), wx0, wx1, wz0, wz1,
                       " ".join("%d_%d" % t for t in tl)))

    elif a[0] == "overlay":
        from PIL import Image
        import json
        import re
        tiles_dir = a[1] if len(a) > 1 else "save/tiles"
        out = a[2] if len(a) > 2 else "overlay.png"
        im = Image.open("worldmap.png").convert("RGB")
        # draw with PIL: rhombi + grid + labels
        from PIL import ImageDraw
        dr = ImageDraw.Draw(im, "RGBA")
        for tx, ty in sorted({(int(m.group(1)), int(m.group(2)))
                              for m in (re.match(r"tile_(\d+)_(\d+)_", f)
                                        for f in os.listdir(tiles_dir)) if m}):
            pts = [tuple(world_to_pixel(*v)) for v in tile_corners(tx, ty)]
            dr.polygon(pts, fill=(78, 163, 255, 40), outline=(78, 163, 255, 220))
            c = world_to_pixel(*tile_center(tx, ty))
            dr.text((c[0] - 18, c[1] - 5), "%d_%d" % (tx, ty), fill=(255, 255, 255, 230))
        for i in range(N + 1):
            dr.line([(i * CELL, 0), (i * CELL, IMG)], fill=(255, 255, 255, 60))
            dr.line([(0, i * CELL), (IMG, i * CELL)], fill=(255, 255, 255, 60))
        for col in range(N):
            for row in range(N):
                L, num = grid_name(col, row)
                x0, y0, _, _ = grid_to_pixel(L, num)
                dr.text((x0 + 8, y0 + 8), "%s %02d" % (L, num),
                        fill=(255, 255, 0, 200))
        im.save(out)
        print("saved", out, im.size)
