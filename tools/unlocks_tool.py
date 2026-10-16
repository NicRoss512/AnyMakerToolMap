#!/usr/bin/env python3
"""
Anymaker unlocks.txt <-> JSON  (decode / encode / re-key / merge)

HOW THE FILE WORKS
------------------
1) The game takes the plain JSON of your unlocks, e.g.
       {"unlocked_items":[{"definition_id":"food_water","pattern_index":12}, ...]}
2) XORs every byte with the ASCII bytes of YOUR SteamID64 (17 digits, e.g. 76561198000000000),
   repeating the key:  data[i] ^ key[i % 17]
   -> THIS is why a file copied from another account "does nothing": on a different
      SteamID the XOR un-mangles into garbage and the game just discards it.
3) Base32-encodes the result with the alphabet "abcdefghijklmnopqrstuvwxyz234567"
   and LSB-first bit packing (NOT standard RFC4648 base32 - python's base64.b32decode
   will give you the wrong bytes!).

So: moving unlocks between accounts = decode with OLD SteamID -> encode with NEW SteamID.

USAGE
-----
  python3 unlocks_tool.py decode  unlocks.txt          <SteamID64>  [out.json]
  python3 unlocks_tool.py encode  unlocks.json         <SteamID64>  [out.txt]
  python3 unlocks_tool.py rekey   unlocks.txt  <OLD_ID> <NEW_ID>    [out.txt]
  python3 unlocks_tool.py merge   a.txt <ID_A>  b.txt <ID_B>  <NEW_ID>  [out.txt]
  python3 unlocks_tool.py findkey unlocks.txt      # recover the unknown SteamID from a file
"""

import json
import sys

ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"


# ---------- custom base32 (LSB-first, exactly like crypt.js in AnyUnlocker) ----------
def b32_decode(s):
    bits = value = 0
    out = bytearray()
    for ch in s:
        idx = ALPHABET.find(ch)
        if idx < 0:
            continue
        value |= idx << bits
        bits += 5
        while bits >= 8:
            out.append(value & 255)
            value >>= 8
            bits -= 8
    return bytes(out)


def b32_encode(data):
    bits = value = 0
    out = []
    for b in data:
        value |= b << bits
        bits += 8
        while bits >= 5:
            out.append(ALPHABET[value & 31])
            value >>= 5
            bits -= 5
    if bits > 0:
        out.append(ALPHABET[value & 31])
    return "".join(out)


def xor_bytes(data, key):
    k = key.encode()
    return bytes(c ^ k[i % len(k)] for i, c in enumerate(data))


# ---------- public API ----------
def decode(text, steam_id):
    """unlocks.txt content -> JSON string"""
    return xor_bytes(b32_decode(text.strip()), steam_id).decode("utf-8")


def encode(json_text, steam_id):
    """JSON string -> unlocks.txt content"""
    return b32_encode(xor_bytes(json_text.encode("utf-8"), steam_id))


def find_key(text, known_prefix=b'{"unlocked_items":['):
    """Recover the SteamID a file was encrypted with (needs >= len+2 known plaintext bytes
       to confirm the period; the game's JSON always starts with known_prefix)."""
    raw = b32_decode(text.strip())
    k = bytes(a ^ b for a, b in zip(raw, known_prefix))
    for period in range(1, len(k)):
        if all(k[i] == k[i % period] for i in range(len(k))):
            return k[:period].decode("latin1")
    return k.decode("latin1")


def load(path, steam_id):
    return json.loads(decode(open(path, encoding="utf-8").read(), steam_id))


def dump(obj, steam_id, path=None):
    """Serialize the way the game does: compact separators, keys in insertion order."""
    text = json.dumps(obj, separators=(",", ":"))
    out = encode(text, steam_id)
    if path:
        open(path, "w", encoding="utf-8", newline="").write(out)
    return out


def merge(*jsons):
    """Union of several unlock lists, order preserved, duplicates removed."""
    seen, items = set(), []
    for j in jsons:
        for it in j.get("unlocked_items", []):
            key = json.dumps(it, sort_keys=True)
            if key not in seen:
                seen.add(key)
                items.append(it)
    return {"unlocked_items": items}


# ---------- CLI ----------
def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = a[0]

    if cmd == "decode":
        txt = decode(open(a[1], encoding="utf-8").read(), a[2])
        json.loads(txt)  # validate
        if len(a) > 3:
            open(a[3], "w", encoding="utf-8").write(txt)
            print(f"OK -> {a[3]}")
        else:
            print(txt)

    elif cmd == "encode":
        js = open(a[1], encoding="utf-8").read()
        json.loads(js)  # validate
        out = encode(js, a[2])
        if len(a) > 3:
            open(a[3], "w", encoding="utf-8", newline="").write(out)
            print(f"OK -> {a[3]}")
        else:
            print(out)

    elif cmd == "rekey":
        js = decode(open(a[1], encoding="utf-8").read(), a[2])
        json.loads(js)
        out = encode(js, a[3])
        open(a[4] if len(a) > 4 else "unlocks_rekeyed.txt", "w",
             encoding="utf-8", newline="").write(out)
        print(f"OK -> {a[4] if len(a) > 4 else 'unlocks_rekeyed.txt'}")

    elif cmd == "merge":
        objs = [load(a[1], a[2]), load(a[3], a[4])]
        out = encode(json.dumps(merge(*objs), separators=(",", ":")), a[5])
        open(a[6] if len(a) > 6 else "unlocks_merged.txt", "w",
             encoding="utf-8", newline="").write(out)
        print(f"OK -> {a[6] if len(a) > 6 else 'unlocks_merged.txt'}")

    elif cmd == "findkey":
        print(find_key(open(a[1], encoding="utf-8").read()))

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
