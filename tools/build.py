#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка save_map.html из _template2.html:
    /*__JSZIP__*/  ->  jszip.min.js
    /*__CATS__*/   ->  cats.js  (категории, собранные make_cats.py из данных игры)

Запуск:
    python3 tools/build.py            # результат — save_map.html в корне репозитория
    python3 tools/build.py мой.html   # или куда скажете

Править надо _template2.html, а не готовый save_map.html.
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)

# по умолчанию кладём готовый файл в корень репозитория (рядом с worldmap.png)
out = sys.argv[1] if len(sys.argv) > 1 else None
if out is None:
    out = os.path.join(parent, "save_map.html") if os.path.isdir(parent) \
        else os.path.join(here, "save_map.html")

tpl = open(os.path.join(here, "_template2.html"), encoding="utf-8").read()
for token, fn in (("/*__JSZIP__*/", "jszip.min.js"), ("/*__CATS__*/", "cats.js")):
    assert token in tpl, "в шаблоне нет метки " + token
    tpl = tpl.replace(token, open(os.path.join(here, fn), encoding="utf-8").read())

open(out, "w", encoding="utf-8").write(tpl)
print("собран", out, "(", len(tpl), "байт )")
