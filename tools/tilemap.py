#!/usr/bin/env python3
"""
Anymaker: tile index  <->  world coordinate conversion  (derived from a real save,
verified on 37 341 objects: 99.98 % fall inside the rhombus of their own tile).

THE WORLD GRID
--------------
The world is tiled by RHOMBI with side 512 (a hexagonal / "rhombille" lattice,
60°/120° corners).  Tile names are  tile_<tx>_<ty>_<layer>_<kind>.json

    Z = TZ * (ty + b)                     TZ = 512 * sqrt(3) / 2 = 443.4050067
    X = 512*tx + 256*ty + 512*a + 256*b   a,b in [0,1)  (a = along X, b = along the slant)

so tile (tx,ty) is the rhombus with the corners

    A = ( 512*tx + 256*ty      ,  TZ*ty       )
    B = ( 512*tx + 256*ty + 512,  TZ*ty       )
    C = ( 512*tx + 256*ty + 256,  TZ*(ty+1)   )
    D = ( 512*tx + 256*ty + 768,  TZ*(ty+1)   )

width 512 in X, height 443.405 in Z, X-shear 256 per row, diagonal 512.
Centre = A + (384, 221.7025).  Area = 512 * 443.405 = 227 023 world units².

Inverse:
    b = Z/TZ - ty        ty = floor(Z / TZ)
    a = (X - 256*Z/TZ)/512 - tx        tx = floor( (X - 256*Z/TZ) / 512 )

USAGE
-----
  python3 tilemap.py tile 104 117              # corners + centre of a tile
  python3 tilemap.py world 85000 52000         # which tile is this?
  python3 tilemap.py list <save>/tiles         # every tile file with its world box
  python3 tilemap.py mapcfg                    # print the constants
"""
import math
import os
import re
import sys

TILE_SIDE = 512.0
TZ = TILE_SIDE * math.sqrt(3) / 2.0     # 443.4050067…
SHEAR = TILE_SIDE / 2.0                 # 256


def tile_corners(tx, ty):
    """(X, Z) of the 4 corners A, B, D, C of tile (tx, ty)."""
    ax = TILE_SIDE * tx + SHEAR * ty
    az = TZ * ty
    return [(ax, az), (ax + TILE_SIDE, az),
            (ax + TILE_SIDE + SHEAR, az + TZ), (ax + SHEAR, az + TZ)]


def tile_center(tx, ty):
    ax = TILE_SIDE * tx + SHEAR * ty
    return (ax + TILE_SIDE / 2 + SHEAR / 2, TZ * (ty + 0.5))


def world_to_tile(x, z):
    """-> (tx, ty, a, b) with a,b the position inside the rhombus."""
    b = z / TZ
    ty = math.floor(b)
    b -= ty
    u = (x - SHEAR * z / TZ) / TILE_SIDE
    tx = math.floor(u)
    a = u - tx
    return int(tx), int(ty), a, b


def tile_files(tiles_dir):
    out = []
    for fn in sorted(os.listdir(tiles_dir)):
        m = re.match(r"tile_(\d+)_(\d+)_(\d+)(?:_(.+))?\.json$", fn)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        m.group(4) or "base", fn))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit()
    if a[0] == "tile":
        tx, ty = int(a[1]), int(a[2])
        c = tile_corners(tx, ty)
        cx, cz = tile_center(tx, ty)
        print("tile_%d_%d" % (tx, ty))
        for name, p in zip("ABDC", c):
            print("  %s  X %12.1f   Z %12.1f" % (name, p[0], p[1]))
        print("  centre  X %10.1f  Z %10.1f" % (cx, cz))
    elif a[0] == "world":
        x, z = float(a[1]), float(a[2])
        tx, ty, al, be = world_to_tile(x, z)
        print("tile_%d_%d   a=%.4f b=%.4f" % (tx, ty, al, be))
        print("  tile centre: X %.1f  Z %.1f" % tile_center(tx, ty))
    elif a[0] == "list":
        rows = tile_files(a[1])
        print("%-34s %-5s %-6s %12s %12s" % ("file", "tx", "ty", "centre X", "centre Z"))
        seen = set()
        for tx, ty, layer, kind, fn in rows:
            if (tx, ty) in seen:
                continue
            seen.add((tx, ty))
            cx, cz = tile_center(tx, ty)
            print("%-34s %-5d %-6d %12.1f %12.1f" % (fn, tx, ty, cx, cz))
        print("%d tile files, %d distinct tiles" % (len(rows), len(seen)))
    elif a[0] == "mapcfg":
        print("tile side   = 512")
        print("row height  = 512*sqrt(3)/2 = %.7f" % TZ)
        print("x shear/row = 256")
        print("tile area   = %.0f world units^2" % (TILE_SIDE * TZ))
