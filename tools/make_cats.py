#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_cats.py — собирает из данных игры компактный справочник категорий.

На вход: папка data/ с файлами определений игры
  inventory_definitions.json, vehicle_component_definitions.json,
  prop_definitions.json, creature_definitions.json, zombie_definitions.json
На выход: cats.js — встраивается в save_map.html (метка /*__CATS__*/).

    python3 make_cats.py путь/к/data -o cats.js

Логика:
  * предметы и компоненты берут КАТЕГОРИИ САМОЙ ИГРЫ (поля category / class),
    которые сведены в 19 укрупнённых групп;
  * у пропов игра категорий не хранит — группа выводится по ключевым словам
    (fence → building, lamp → road, pallet → cargo, tree → nature…);
  * сверху добавляются человеческие названия (name) — чтобы в выдаче было
    «Canned Vegetables», а не food_canned_veg.
"""

import argparse
import collections
import json
import os

# категории игры → укрупнённая группа
GROUP = {
    "furniture": "furniture", "building": "building", "engine": "engine", "wheel": "wheel",
    "mechanical": "mech", "torque": "mech", "hydraulic": "mech", "connector": "mech",
    "gas": "fluid", "liquid": "fluid",
    "electric": "electric", "interface": "electric", "sensor": "electric", "data": "electric",
    "radio": "electric", "sound": "electric", "light": "electric",
    "control": "control", "aircraft": "control",
    "weapon": "weapon", "storage": "storage",
    "body": "clothing", "legs": "clothing", "feet": "clothing", "head": "clothing",
    "hands": "clothing", "eyes": "clothing", "neck": "clothing", "back": "clothing",
    "hat": "clothing", "body_over": "clothing", "accessory": "clothing", "clothing": "clothing",
    "food": "food", "drink": "food", "medical": "medical",
    "miscellaneous": "misc", "vehicle_editor": "misc", "paint": "misc", "tool": "misc",
}
AMMO = {"ammo_box", "mounted_ammo_can", "grenade_frag", "grenade", "ammo"}

# у пропов категории нет — определяем по слову в названии
PROPKW = [("fence", "building"), ("wall", "building"), ("floor", "building"), ("roof", "building"),
          ("sign", "road"), ("lamp", "road"), ("post", "road"), ("barrier", "road"),
          ("divider", "road"), ("rail", "road"), ("road", "road"), ("cone", "road"),
          ("bridge", "road"), ("train", "road"),
          ("pallet", "cargo"), ("container", "cargo"), ("crate", "cargo"), ("barrel", "cargo"),
          ("box", "cargo"), ("dumpster", "cargo"), ("bin", "cargo"), ("sack", "cargo"),
          ("tree", "nature"), ("bush", "nature"), ("rock", "nature"), ("grass", "nature"),
          ("log", "nature"), ("stump", "nature")]

# объекты мира, которых нет в данных игры (типы entities и прочее)
MANUAL = {
    "light": "electric", "train_junction": "road", "button": "electric",
    "button_elevator": "electric", "door": "building", "character": "npc",
    "survivor_patrol": "npc", "spawner": "other", "util_proximity": "other",
    # типы entities из данжей (в данных игры их нет)
    "light_controller": "electric", "door_controller": "electric",
    "button_keycard": "electric", "button_destruct": "electric",
    "sound": "electric", "shaft_elevator": "building",
    "shaft_diagonal_elevator": "building", "turbine_elevator": "building",
    "big_storage_elevator": "building", "poi_fuel_tank": "fluid",
}

# подписи групп: [по-английски, по-русски]
LABELS = [
    ("building", "Building parts", "Стройматериалы"),
    ("furniture", "Furniture", "Мебель"),
    ("engine", "Engine", "Двигатель"),
    ("wheel", "Wheels", "Колёса"),
    ("mech", "Mechanical", "Механика"),
    ("fluid", "Gas / liquid", "Газ и жидкость"),
    ("electric", "Electric", "Электрика"),
    ("control", "Controls", "Управление"),
    ("weapon", "Weapons", "Оружие"),
    ("ammo", "Ammo", "Патроны"),
    ("clothing", "Clothing", "Одежда"),
    ("food", "Food & drink", "Еда и питьё"),
    ("medical", "Medical", "Медицина"),
    ("storage", "Storage", "Хранение"),
    ("misc", "Misc", "Разное"),
    ("road", "Road & signs", "Дороги и знаки"),
    ("cargo", "Cargo & crates", "Грузы и тара"),
    ("nature", "Nature", "Природа"),
    ("prop", "World props", "Объекты мира"),
    ("npc", "Creatures & NPC", "Живое"),
    ("vehicle", "Vehicles / buildings", "Техника и здания"),
    ("entity", "Map objects", "Объекты карты"),
    ("unknown", "Unrecognised", "Не распознано"),
    ("other", "Other", "Прочее"),
]


def load(path, name):
    p = os.path.join(path, name)
    if not os.path.exists(p):
        return []
    j = json.load(open(p, encoding="utf-8"))
    return j["definitions"] if isinstance(j, dict) and "definitions" in j else j


# у предметов поле class точнее, чем category: колёса в игре помечены
# category=accessory (слот), а class=wheel — поэтому класс проверяем первым
CLASS2GROUP = {
    "wheel": "wheel", "rotor_blade": "control",
    "battery": "electric", "battery_cell": "electric", "fuse": "electric",
    "radio": "electric", "radio_large": "electric", "binoculars": "electric",
    "night_vision_goggles": "electric", "headlamp": "electric", "helmet_light": "electric",
    "strobe_light": "electric", "torch": "electric", "angle_flashlight": "electric",
    "air_filter": "mech", "oil_filter": "fluid",
    "jerry_can": "fluid", "water_container": "fluid", "oil_container": "fluid",
    "backpack": "storage",
    "cable_electric": "electric", "cable_data": "electric",
    "cable_liquid": "fluid", "cable_gas": "fluid", "cable_mechanical": "mech",
}


def inv_group(e):
    cl = (e.get("class") or "").lower()
    if cl in CLASS2GROUP:
        return CLASS2GROUP[cl]
    if cl.startswith("gun_magazine") or cl.startswith("ammo") or cl.startswith("mounted_ammo"):
        return "ammo"
    if cl in AMMO or "ammo" in cl or cl == "component_accessory":
        return "ammo"
    if cl in ("backpack", "container", "storage"):
        return "storage"
    if cl.startswith("food") or cl in ("drink_bottle", "canteen"):
        return "food"
    if cl in ("bandage", "suture_kit", "blood_bag", "medical", "pills", "splint",
              "first_aid_kit", "adrenaline_autoinjector"):
        return "medical"
    if cl == "clothing" or e.get("wearable") or "is_wearable" in (e.get("flags") or []):
        return "clothing"
    return GROUP.get(e.get("category"), "misc")


def comp_group(e):
    # мебель в игре помечена обоими флагами, настоящие стройдетали — только первым
    if e.get("is_building_furniture"):
        return "furniture"
    if e.get("is_building_component"):
        return "building"
    return GROUP.get(e.get("category"), GROUP.get(e.get("class"), "misc"))


def prop_group(n):
    l = n.lower()
    for kw, g in PROPKW:
        if kw in l:
            return g
    return "prop"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="папка data/ с определениями игры")
    ap.add_argument("-o", "--out", default="cats.js")
    args = ap.parse_args()

    M = {}
    for e in load(args.data, "inventory_definitions.json"):
        if e.get("id"):
            M[e["id"]] = (inv_group(e), e.get("name") or e["id"])
    for e in load(args.data, "vehicle_component_definitions.json"):
        if e.get("id"):
            M.setdefault(e["id"], (comp_group(e), e.get("name") or e["id"]))
    for e in load(args.data, "prop_definitions.json"):
        n = e.get("name")
        if n:
            M.setdefault(n, (prop_group(n), n))
    for fn in ("creature_definitions.json", "zombie_definitions.json"):
        for e in load(args.data, fn):
            if e.get("id"):
                M.setdefault(e["id"], ("npc", e.get("name") or e["id"]))
    for k, g in MANUAL.items():
        M.setdefault(k, (g, k))

    cnt = collections.Counter(g for g, _ in M.values())
    grp = '{\n' + ",\n".join('"%s":["%s","%s"]' % (g, en, ru) for g, en, ru in LABELS) + '\n}'
    # id -> [группа, человеческое имя]; имя не пишем, если оно совпадает с id
    items = []
    for k in sorted(M):
        g, nm = M[k]
        items.append('"%s":["%s"%s]' % (k, g, "" if nm == k else ',"%s"' % nm.replace('"', "'")))
    cats = "{" + ",".join(items) + "}"

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("/* категории собраны make_cats.py из данных игры: %d id */\n" % len(M))
        f.write("const GRP=%s;\n" % grp)
        f.write("const CATS=%s;\n" % cats)

    print("id в справочнике: %d" % len(M))
    print("по группам: " + ", ".join("%s %d" % (g, n) for g, n in cnt.most_common()))
    print("записано %s (%d байт)" % (args.out, os.path.getsize(args.out)))


if __name__ == "__main__":
    main()
