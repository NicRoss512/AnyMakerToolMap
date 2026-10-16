#!/usr/bin/env python3
"""Extract every object position from an Anymaker save folder (…/saves/<name>/tiles).

Writes a .npz with columns: x, z, y, tile_x, tile_y, layer, kind, section, def_name
"""
import json
import os
import re
import sys

import numpy as np

SECTIONS = [("vehicles", "vehicles"), ("actors", "actors"), ("floor_items", "items"),
            ("props", "props"), ("entities", "entities"), ("creative_domes", "domes"),
            ("ropes", "ropes")]

ROADISH = ("sign_", "bollard", "lamp_post", "metal_divider", "road_post", "barrier_",
           "construction_barrel", "safety_rail", "concrete_construction_block",
           "guard", "kerb", "curb", "traffic", "road", "street")


def scan(tiles_dir):
    rows = []
    for fn in sorted(os.listdir(tiles_dir)):
        m = re.match(r"tile_(\d+)_(\d+)_(\d+)(?:_(.+))?\.json$", fn)
        if not m:
            continue
        tx, ty, layer, kind = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "base"
        try:
            j = json.load(open(os.path.join(tiles_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        defs = j.get("definitions", {}).get("components", [])
        for sec, key in SECTIONS:
            lst = j.get(sec, {}).get(key)
            if not isinstance(lst, list):
                continue
            for el in lst:
                if not isinstance(el, dict):
                    continue
                tr = el.get("transform")
                if not (isinstance(tr, dict) and isinstance(tr.get("t"), list) and len(tr["t"]) == 3):
                    continue
                d = el.get("definition_id")
                name = defs[d] if isinstance(d, int) and d < len(defs) else str(d)
                x, y, z = tr["t"]
                rows.append((x, z, y, tx, ty, layer, kind, sec, name))
    n = len(rows)
    out = {
        "x": np.array([r[0] for r in rows]),
        "z": np.array([r[1] for r in rows]),
        "y": np.array([r[2] for r in rows]),
        "tile_x": np.array([r[3] for r in rows], dtype=np.int32),
        "tile_y": np.array([r[4] for r in rows], dtype=np.int32),
        "layer": np.array([r[5] for r in rows], dtype=np.int32),
        "kind": np.array([r[6] for r in rows]),
        "section": np.array([r[7] for r in rows]),
        "def_name": np.array([r[8] for r in rows]),
    }
    return out


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "points.npz"
    d = scan(src)
    np.savez_compressed(dst, **d)
    print(f"{len(d['x'])} points -> {dst}")
    road = np.array([any(k in n for k in ROADISH) for n in d["def_name"]])
    print("road-ish props:", road.sum())
    print("X %.1f..%.1f  Z %.1f..%.1f" % (d["x"].min(), d["x"].max(), d["z"].min(), d["z"].max()))
