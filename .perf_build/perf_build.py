"""
Build fuer "Multiplayer Performance Update RRR".

Der entities-Ordner dieses Mods wird NICHT von Hand gepflegt, sondern gebaut:
  frische Basis-Datei (RRR, sonst Vanilla)  +  unsere Werte aus perf_rules.json  =  entities/<datei>

Nach einem Spiel- oder RRR-Update einfach neu bauen - RRR-Aenderungen kommen automatisch mit,
unsere Performance-Werte bleiben erhalten.

Aufruf:
  python perf_build.py            -> Vorschau (aendert nichts), zeigt was passieren wuerde
  python perf_build.py --write    -> entities neu bauen (veraltete Overrides werden entfernt)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
ENTITIES = os.path.join(MOD, "entities")
RULES = os.path.join(HERE, "perf_rules.json")
RRR = r"C:\Users\Avija\AppData\Local\sins2\mods\modio\5762\mods\4317372\entities"
VANILLA = r"G:\Game Management\Steam\steamapps\common\Sins2\entities"


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    text = re.sub(r",\s*([}\]])", r"\1", text)  # Sins-Dateien haben teils Trailing Commas
    return json.loads(text)


def save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def base_path(name):
    for d in (RRR, VANILLA):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


TOKEN = re.compile(r"([^.\[\]]+)|\[([^\]]*)\]")


def parse(path):
    """'a.b[2].c[action_value_id=x]' -> ['a','b',2,'c',('action_value_id','x')]"""
    out = []
    for key, idx in TOKEN.findall(path):
        if key:
            out.append(key)
        elif "=" in idx:
            k, v = idx.split("=", 1)
            out.append((k, v))
        else:
            out.append(int(idx))
    return out


def step(obj, tok):
    if isinstance(tok, int):
        return obj[tok] if isinstance(obj, list) and tok < len(obj) else None
    if isinstance(tok, tuple):
        if not isinstance(obj, list):
            return None
        for item in obj:
            if isinstance(item, dict) and str(item.get(tok[0])) == tok[1]:
                return item
        return None
    return obj.get(tok) if isinstance(obj, dict) else None


def set_value(data, path, value):
    """Setzt den Wert. Rueckgabe: 'changed' | 'same' | 'missing'"""
    toks = parse(path)
    obj = data
    for tok in toks[:-1]:
        obj = step(obj, tok)
        if obj is None:
            return "missing"
    last = toks[-1]
    if isinstance(last, int):
        if not isinstance(obj, list) or last >= len(obj):
            return "missing"
        if obj[last] == value:
            return "same"
        obj[last] = value
        return "changed"
    if not isinstance(obj, dict):
        return "missing"
    if obj.get(last) == value:
        return "same"
    obj[last] = value  # neue Schluessel (z.B. player_ai) werden angelegt
    return "changed"


def get_value(data, path):
    obj = data
    for tok in parse(path):
        obj = step(obj, tok)
        if obj is None:
            return None
    return obj


def main():
    write = "--write" in sys.argv
    rules = load(RULES)
    targets = {}  # dateiname -> [(pfad, wert, quelle)]

    for g in rules.get("global", []):
        names = set(os.listdir(VANILLA)) | set(os.listdir(RRR))
        for n in sorted(names):
            if not n.endswith(g["ext"]):
                continue
            try:
                data = load(base_path(n))
            except Exception:
                continue
            if get_value(data, g["path"]) is not None:
                targets.setdefault(n, []).append((g["path"], g["value"], g["name"]))

    for n, vals in rules["files"].items():
        for p, v in vals.items():
            targets.setdefault(n, []).append((p, v, "perf_rules"))

    report = {"built": 0, "unchanged_vs_base": [], "missing": [], "no_base": []}
    built = {}
    for n, items in sorted(targets.items()):
        bp = base_path(n)
        if not bp:
            report["no_base"].append(n)
            continue
        data = load(bp)
        changed = 0
        for p, v, src in items:
            r = set_value(data, p, v)
            if r == "missing":
                report["missing"].append(f"{n} : {p}")
            elif r == "changed":
                changed += 1
        if changed == 0:
            report["unchanged_vs_base"].append(n)  # Basis hat unsere Werte schon -> kein Override noetig
            continue
        built[n] = data

    existing = {f for f in os.listdir(ENTITIES) if os.path.isfile(os.path.join(ENTITIES, f))}
    remove = sorted(existing - set(built))
    new = sorted(set(built) - existing)

    print(f"Basis: RRR  {RRR}")
    print(f"       Van  {VANILLA}")
    print(f"Override-Dateien nach Build: {len(built)}  (vorher {len(existing)})")
    print(f"  neu hinzugekommen: {len(new)}")
    print(f"  entfernt (Basis reicht / veraltet): {len(remove)}")
    if report["unchanged_vs_base"]:
        print(f"  Regeln ohne Wirkung (Basis hat die Werte schon): {len(report['unchanged_vs_base'])}")
        for n in report["unchanged_vs_base"]:
            print(f"     = {n}")
    if report["missing"]:
        print(f"  WARNUNG - Pfad in neuer Basis nicht gefunden ({len(report['missing'])}):")
        for m in report["missing"]:
            print(f"     ! {m}")
    if report["no_base"]:
        print(f"  WARNUNG - Datei gibt es weder in RRR noch Vanilla ({len(report['no_base'])}):")
        for m in report["no_base"]:
            print(f"     ! {m}")

    if not write:
        print("\nVorschau - nichts geaendert. Mit --write bauen.")
        return

    for n, data in built.items():
        save(os.path.join(ENTITIES, n), data)
    for n in remove:
        os.remove(os.path.join(ENTITIES, n))
    print(f"\nGebaut: {len(built)} Dateien geschrieben, {len(remove)} entfernt.")


if __name__ == "__main__":
    main()
