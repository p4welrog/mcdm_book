"""Wiersz poleceń.

python -m mcdm_book methods                      — lista metod i opcji (JSON)
python -m mcdm_book run ZADANIE.json             — {"method", "problem", "options"} → wynik (JSON)
python -m mcdm_book run ZADANIE.json --method topsis --option metric=1
python -m mcdm_book run -                        — zadanie ze standardowego wejścia
python -m mcdm_book example NAZWA                — przykład z książki (bez nazwy: lista)
"""
import json
import sys

from . import api, examples


def _load(path):
    return json.load(sys.stdin) if path == "-" else json.load(open(path, encoding="utf-8"))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "methods":
        out = api.methods()
    elif cmd == "example":
        out = examples.get(argv[1]) if len(argv) > 1 else examples.listing()
    elif cmd == "run" and len(argv) >= 2:
        req = _load(argv[1])
        if "problem" not in req and "variants" in req:
            req = {"problem": req}
        rest = argv[2:]
        while rest:
            flag = rest.pop(0)
            if flag == "--method":
                req["method"] = rest.pop(0)
            elif flag == "--option":
                k, v = rest.pop(0).split("=", 1)
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    pass
                req.setdefault("options", {})[k] = v
            else:
                print(f"Nieznany argument {flag}", file=sys.stderr)
                return 2
        out = api.run_safe(req)
    else:
        print(__doc__)
        return 2
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if isinstance(out, dict) and "error" in out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
