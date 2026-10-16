#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anymaker_scan.py — разведка по чанкам сейва Anymaker.

Что делает: обходит ВСЕ .json внутри сейва (папка или ZIP — распаковывать не надо)
и собирает:

  * все названия предметов, запчастей, пропсов, NPC — с количествами и по источникам;
  * все поля, которые встречаются в файлах (схема) — чтобы найти то, что мы ещё не читаем;
  * частоту слов в названиях — чтобы придумать категории (еда / одежда / мебель / …);
  * группы по первому слову (wheel_*, battery_*, …);
  * по одному примеру объекта на каждое название;
  * список того, что не удалось распознать (definition_id вне диапазона).

Только стандартная библиотека, ничего ставить не надо. Python 3.7+

Как запускать:

    python3 anymaker_scan.py путь/к/папке_сейва
    python3 anymaker_scan.py путь/к/архиву.zip
    python3 anymaker_scan.py архив.zip -o куда_положить
    python3 anymaker_scan.py архив.zip --schema-files 200   # больше файлов в разбор схемы
    python3 anymaker_scan.py архив.zip --no-schema          # быстрее, без анализа полей

Результат — папка (по умолчанию ./anymaker_scan_out):
    report.txt      сводка, читать в первую очередь
    names.csv       название;сколько;и по каждому источнику отдельно
    groups.txt      группы по первому слову (wheel_* → 18 названий, 388 шт.)
    tokens.csv      частота отдельных слов в названиях
    schema.csv      все найденные поля и массивы со счётчиками
    samples.json    по одному «сырому» объекту на каждое название
    unresolved.txt  что не удалось распознать
"""

import argparse
import collections
import io
import json
import os
import re
import sys
import zipfile

# ------------------------------------------------------------------ категории
# Черновик: слова, по которым названия раскладываются по категориям.
# Правь как хочешь — это просто подсказка для чтения отчёта, на результат поиска
# в карте она не влияет. Совпадение ищется по подстроке в названии.
CATEGORIES = {
    "еда/питьё": ["food", "can_", "canned", "milk", "water", "bread", "meat", "fruit",
                  "apple", "banana", "potato", "corn", "rice", "bean", "soup", "cereal",
                  "candy", "chocolate", "chip", "soda", "beer", "wine", "coffee", "tea",
                  "salt", "sugar", "flour", "cook", "kitchen", "drink", "juice", "egg",
                  "fish", "cheese", "butter", "pasta", "sandwich", "burger", "pie"],
    "одежда": ["cloth", "shirt", "pant", "jacket", "coat", "boot", "shoe", "hat", "helmet",
               "glove", "sock", "vest", "dress", "uniform", "mask", "goggle", "bag",
               "backpack", "belt", "scarf", "hoodie", "jeans", "armor"],
    "мебель/интерьер": ["chair", "table", "bed", "sofa", "couch", "shelf", "cabinet",
                        "wardrobe", "desk", "lamp", "rug", "carpet", "curtain", "toilet",
                        "sink", "bath", "shower", "fridge", "oven", "stove", "counter",
                        "bench", "stool", "dresser", "nightstand", "mirror", "picture",
                        "plant", "vase", "clock"],
    "запчасти/машины": ["wheel", "tire", "battery", "engine", "motor", "brake", "suspension",
                        "shock", "spring", "radiator", "exhaust", "muffler", "gearbox",
                        "transmission", "clutch", "alternator", "starter", "spark", "fuel",
                        "tank", "pump", "filter", "belt", "hose", "cable", "wire", "light",
                        "headlight", "mirror", "door", "window", "windshield", "seat",
                        "steering", "bumper", "hood", "trunk", "fender", "chassis", "frame",
                        "junction", "mechanical", "electronic", "electric", "rotor", "piston",
                        "crankshaft", "camshaft", "valve", "gasket", "bearing", "axle",
                        "differential", "driveshaft", "turbo", "carburetor", "injector"],
    "инструменты": ["tool", "wrench", "hammer", "screwdriver", "pliers", "saw", "drill",
                    "axe", "shovel", "pickaxe", "crowbar", "knife", "machete", "sledge",
                    "jerrycan", "rope", "duct", "tape", "nail", "screw", "bolt", "nailgun"],
    "оружие/боеприпасы": ["gun", "rifle", "pistol", "shotgun", "ammo", "bullet", "cartridge",
                          "magazine", "shell", "grenade", "explosive", "bomb", "mine",
                          "bow", "arrow", "crossbow", "spear", "bat", "blade", "sword"],
    "медицина": ["med", "bandage", "pill", "antibiotic", "syringe", "vaccine", "herb",
                 "plant_med", "first_aid", "splint", "suture", "disinfect", "morphine"],
    "материалы/стройка": ["wood", "plank", "log", "metal", "steel", "iron", "scrap", "stone",
                          "brick", "concrete", "cement", "glass", "plastic", "cloth_mat",
                          "nail", "beam", "panel", "sheet", "pipe", "rod", "wire_mat",
                          "rope_mat", "tarp", "wall", "floor", "roof", "stair", "fence",
                          "gate", "post", "pillar", "column"],
    "электроника": ["circuit", "chip", "board", "sensor", "relay", "fuse", "diode", "led",
                    "screen", "display", "radio", "speaker", "antenna", "module", "cpu",
                    "transistor", "capacitor", "resistor", "switch", "button"],
    "химия/жидкости": ["chemical", "acid", "fuel_can", "oil", "gasoline", "diesel", "solvent",
                       "paint", "glue", "fertilizer", "pesticide", "bleach", "alcohol"],
    "книги/бумага": ["book", "magazine", "newspaper", "note", "paper", "map", "manual",
                     "blueprint", "document", "letter", "pen", "pencil"],
}

# названия-обёртки: сам предмет — это коробка/заготовка, а деталь лежит в component_def
WRAPPERS = {"vehicle_editor_add_component", "vehicle_editor_add_building_component"}

SOURCES = ["ground", "installed", "stored", "npc_inv", "prop", "actor", "vehicle",
           "entity", "dome", "pseudo", "other"]
# чем заменять объект, если имя вытащить не удалось
FALLBACK = {"prop": "<пропс>", "actor": "<NPC>", "entity": "<объект>", "dome": "<купол>"}


# ------------------------------------------------------------------ обход файлов
def iter_json(src):
    """Отдаёт (относительный путь, байты) для каждого .json внутри папки или ZIP."""
    if os.path.isdir(src):
        for dp, _, fs in os.walk(src):
            for f in sorted(fs):
                if f.lower().endswith(".json"):
                    p = os.path.join(dp, f)
                    try:
                        with open(p, "rb") as fh:
                            yield os.path.relpath(p, src).replace("\\", "/"), fh.read()
                    except Exception as e:
                        sys.stderr.write("  ! не прочитался %s: %s\n" % (p, e))
    elif os.path.isfile(src) and zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if n.lower().endswith(".json") and not n.endswith("/"):
                    try:
                        yield n, z.read(n)
                    except Exception as e:
                        sys.stderr.write("  ! не прочитался %s: %s\n" % (n, e))
    else:
        raise SystemExit("Не понял, что это: %s\nНужна папка с сейвом или ZIP-архив." % src)


def kind_of(rel):
    if re.search(r"dungeon_\d+_", rel):
        return "dungeon"
    if rel.endswith("scene.json"):
        return "scene"
    if rel.endswith("meta.json"):
        return "meta"
    if re.search(r"tile_\d+_\d+_", rel):
        return "tile"
    return "other"


# ------------------------------------------------------------------ распознавание имён
def res(defs, v):
    """Имя по definition_id: строка — как есть, число — индекс в definitions.components."""
    if isinstance(v, str):
        return v
    if isinstance(v, int) and defs is not None and 0 <= v < len(defs):
        return defs[v]
    return None


def item_name(it):
    """Имя предмета: если это коробка с запчастью — берём component_def, иначе _type."""
    if not isinstance(it, dict):
        return None, None
    cd = it.get("component_def")
    t = it.get("_type")
    if cd:
        return cd, t
    return t, None


# ------------------------------------------------------------------ главное
def main():
    ap = argparse.ArgumentParser(description="Разведка по чанкам сейва Anymaker.")
    ap.add_argument("src", help="папка с сейвом или ZIP-архив")
    ap.add_argument("-o", "--out", default="anymaker_scan_out", help="куда положить отчёт")
    ap.add_argument("--schema-files", type=int, default=60,
                    help="сколько файлов разбирать на схему (0 = все, по умолчанию 60)")
    ap.add_argument("--no-schema", action="store_true", help="не собирать схему полей")
    args = ap.parse_args()

    names = collections.defaultdict(collections.Counter)   # имя -> {источник: сколько}
    samples = {}                                           # имя -> сырой объект
    unresolved = collections.Counter()                     # "файл: id" -> сколько
    unresolved_ex = {}
    wrapped = collections.Counter()                        # обёртка -> деталь: сколько
    files_by_kind = collections.Counter()
    schema = collections.Counter()                         # путь -> сколько
    schema_kind = {}
    players = []
    n_files = n_bytes = 0

    # какие файлы пойдут в разбор схемы
    schema_budget = [args.schema_files] if not args.no_schema else [0]

    print("Читаю", args.src)
    for rel, raw in iter_json(args.src):
        n_files += 1
        n_bytes += len(raw)
        try:
            j = json.loads(raw.decode("utf-8"))
        except Exception as e:
            sys.stderr.write("  ! битый JSON %s: %s\n" % (rel, e))
            continue
        k = kind_of(rel)
        files_by_kind[k] += 1
        if n_files % 200 == 0:
            sys.stdout.write("\r  файлов: %d, названий: %d" % (n_files, len(names)))
            sys.stdout.flush()

        # ---- схема (на выборке файлов) ----
        if schema_budget[0] > 0 and (k in ("scene", "meta", "dungeon") or schema_budget[0] > 0):
            schema_budget[0] -= 1
            seen = collections.Counter()

            def walk(o, path, d=0):
                if d > 9:
                    return
                if isinstance(o, dict):
                    for kk, vv in o.items():
                        walk(vv, path + "." + kk, d + 1)
                elif isinstance(o, list):
                    seen[path + "[]"] += len(o)
                    for vv in o[:300]:
                        walk(vv, path + "[]", d + 1)
                else:
                    seen[path] += 1

            walk(j, "")
            for p, c in seen.items():
                schema[p] += c
                schema_kind.setdefault(p, "array" if p.endswith("[]") else "field")

        defs = (j.get("definitions") or {}).get("components") or []

        def note(nm, src, obj=None):
            if not nm:
                return
            names[nm][src] += 1
            if nm not in samples and obj is not None:
                samples[nm] = obj

        # ---- предметы на земле ----
        for el in (j.get("floor_items") or {}).get("items") or []:
            it = el.get("item") or {}
            nm, wrap = item_name(it)
            if wrap:
                wrapped[wrap + " -> " + str(nm)] += 1
            note(nm, "ground", it)
            for ch in it.get("children") or []:
                nm2, _w = item_name(ch.get("item") or {})
                note(nm2, "ground", ch.get("item"))

        # ---- техника/здания и всё, что на них ----
        for v in (j.get("vehicles") or {}).get("vehicles") or []:
            note("<техника/здание>", "vehicle", v)
            for g in v.get("grids") or []:
                for c in g.get("components") or []:
                    d = res(defs, c.get("def"))
                    if d is None and c.get("def") is not None:
                        unresolved[":".join((k, str(c.get("def"))))] += 1
                        unresolved_ex.setdefault(str(c.get("def")), c)
                    note(d, "installed", c)
                    for it in c.get("items") or []:
                        it = it.get("item") or it
                        nm, wrap = item_name(it)
                        if wrap:
                            wrapped[wrap + " -> " + str(nm)] += 1
                        note(nm, "stored", it)
                    ac = (c.get("element") or {}).get("acc")
                    if isinstance(ac, dict):
                        nm, _w = item_name(ac.get("item") or {})
                        note(nm, "stored", ac.get("item"))

        # ---- пропсы, NPC, объекты, купола ----
        for sec, key, src in (("props", "props", "prop"),
                              ("actors", "actors", "actor"),
                              ("entities", "entities", "entity"),
                              ("creative_domes", "domes", "dome")):
            for el in (j.get(sec) or {}).get(key) or []:
                v = el.get("definition_id")
                nm = res(defs, v)
                if nm is None and v is not None:
                    unresolved[":".join((k, str(v)))] += 1
                    unresolved_ex.setdefault(str(v), el)
                    nm = "<id %s>" % v
                elif nm is None and isinstance(el.get("type"), str):
                    nm = el["type"]          # у entities имя лежит в type: train_junction
                if nm is None:
                    nm = FALLBACK.get(src, "<объект>")
                note(nm, src, el)

        # ---- инвентарь NPC (сети) ----
        for a in (j.get("actors") or {}).get("actors") or []:
            inv = a.get("inventory") or {}
            for slot, val in inv.items():
                if not isinstance(val, dict):
                    continue
                nm, _w = item_name(val.get("item") or val)
                note(nm, "npc_inv", val)
                for ch in val.get("children") or []:
                    nm2, _w = item_name(ch.get("item") or {})
                    note(nm2, "npc_inv", ch.get("item"))

        # ---- псевдообъекты сцены (патрули, лагеря) ----
        if k == "scene":
            for o in (j.get("pseudo_objects") or {}).get("objects") or []:
                note(o.get("type") or "<псевдообъект>", "pseudo", o)

        # ---- игроки ----
        if k == "scene":
            for pe in ((j.get("peers") or {}).get("peers") or []):
                w = pe.get("world_pos")
                if w and len(w) >= 3:
                    players.append((pe.get("uid"), w[0], w[1], w[2]))

    print("\r  готово: файлов %d (%.1f МБ), названий %d" %
          (n_files, n_bytes / 1048576.0, len(names)))

    # ------------------------------------------------------------------ отчёт
    os.makedirs(args.out, exist_ok=True)
    tot = collections.Counter()
    for nm, c in names.items():
        for s, v in c.items():
            tot[s] += v

    # категории
    cat_hits = collections.defaultdict(lambda: [0, 0])   # категория -> [названий, штук]
    cat_of = {}
    for nm, c in names.items():
        l = nm.lower()
        for cat, words in CATEGORIES.items():
            if any(w in l for w in words):
                cat_of[nm] = cat
                cat_hits[cat][0] += 1
                cat_hits[cat][1] += sum(c.values())
                break

    # токены
    tok_names = collections.Counter()
    tok_items = collections.Counter()
    for nm, c in names.items():
        for t in re.split(r"[_\W]+", nm.lower()):
            if t:
                tok_names[t] += 1
                tok_items[t] += sum(c.values())

    L = []
    L.append("АНАЛИЗ СЕЙВА: %s" % args.src)
    L.append("=" * 78)
    L.append("")
    L.append("Файлов JSON: %d (%.1f МБ)   разных названий: %d" %
             (n_files, n_bytes / 1048576.0, len(names)))
    L.append("По типам файлов: " + ", ".join("%s %d" % (k, v) for k, v in files_by_kind.most_common()))
    L.append("")
    L.append("Объектов по источникам:")
    for s in SOURCES:
        if tot[s]:
            L.append("   %-12s %s" % (s, format(tot[s], ",")))
    L.append("   %-12s %s" % ("ИТОГО", format(sum(tot.values()), ",")))
    L.append("")
    if players:
        L.append("Игроки (scene.json → peers.peers):")
        for i, (uid, x, y, z) in enumerate(players, 1):
            L.append("   P%d  uid %s  мир X %.1f  Y %.1f  Z %.1f" % (i, uid, x, y, z))
        L.append("")
    L.append("Черновые категории (по ключевым словам, словарь в начале скрипта):")
    for cat, (n1, n2) in sorted(cat_hits.items(), key=lambda kv: -kv[1][1]):
        L.append("   %-20s названий %4d   штук %s" % (cat, n1, format(n2, ",")))
    rest = [nm for nm in names if nm not in cat_of]
    L.append("   %-20s названий %4d   штук %s" %
             ("без категории", len(rest), format(sum(sum(names[n].values()) for n in rest), ",")))
    L.append("")
    L.append("Топ-100 названий:")
    L.append("   %-42s %10s  %s" % ("название", "всего", "по источникам"))
    for nm, c in sorted(names.items(), key=lambda kv: -sum(kv[1].values()))[:100]:
        br = " ".join("%s:%d" % (s, v) for s, v in c.most_common())
        L.append("   %-42s %10s  %s" % (nm[:42], format(sum(c.values()), ","), br))
    L.append("")
    if wrapped:
        L.append("Предметы-обёртки (в _type коробка, деталь в component_def):")
        for w, n in wrapped.most_common(30):
            L.append("   %-70s %s" % (w, format(n, ",")))
        L.append("")

    # ---- запись файлов ----
    def W(name, text):
        with io.open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(text)

    W("report.txt", "\n".join(L) + "\n")

    rows = ["name;total;" + ";".join(SOURCES)]
    for nm, c in sorted(names.items(), key=lambda kv: -sum(kv[1].values())):
        rows.append(";".join([nm, str(sum(c.values()))] + [str(c.get(s, 0)) for s in SOURCES]))
    W("names.csv", "\n".join(rows) + "\n")

    rows = ["token;distinct_names;items"]
    for t, n in tok_names.most_common():
        if n > 1 or tok_items[t] > 3:
            rows.append("%s;%d;%d" % (t, n, tok_items[t]))
    W("tokens.csv", "\n".join(rows) + "\n")

    # группы по первому слову
    groups = collections.defaultdict(list)
    for nm, c in names.items():
        m = re.match(r"^([a-z]+)", nm.lower())
        groups[m.group(1) if m else "?"].append((nm, sum(c.values())))
    out = []
    for g, items in sorted(groups.items(), key=lambda kv: -sum(n for _, n in kv[1])):
        items.sort(key=lambda t: -t[1])
        out.append("%-22s названий %3d  штук %s" % (g, len(items), format(sum(n for _, n in items), ",")))
        for nm, n in items[:40]:
            out.append("      %-46s %s" % (nm, format(n, ",")))
        if len(items) > 40:
            out.append("      … и ещё %d" % (len(items) - 40))
    W("groups.txt", "\n".join(out) + "\n")

    if schema:
        rows = ["path;kind;count"]
        for p, c in schema.most_common():
            rows.append("%s;%s;%d" % (p, schema_kind.get(p, "?"), c))
        W("schema.csv", "\n".join(rows) + "\n")

    if unresolved:
        rows = ["id или файл:id;сколько;пример объекта (обрезано)"]
        for key, n in unresolved.most_common(200):
            ex = unresolved_ex.get(key.split(":")[-1], {})
            rows.append("%s;%d;%s" % (key, n, json.dumps(ex, ensure_ascii=False)[:300]))
        W("unresolved.txt", "\n".join(rows) + "\n")

    slim = {}
    for nm, obj in samples.items():
        try:
            s = json.dumps(obj, ensure_ascii=False)
        except Exception:
            s = str(obj)
        slim[nm] = s[:4000]
    with io.open(os.path.join(args.out, "samples.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)

    print("Отчёт в папке:", os.path.abspath(args.out))
    for f in ("report.txt", "names.csv", "groups.txt", "tokens.csv", "schema.csv",
              "samples.json", "unresolved.txt"):
        p = os.path.join(args.out, f)
        if os.path.exists(p):
            print("   %-16s %8d байт" % (f, os.path.getsize(p)))


if __name__ == "__main__":
    main()
