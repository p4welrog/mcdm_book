"""UniComBOS (Unit Comparison for the Best Object Selection; Ashikhmin, Furems 2005) — rozdz. 4.2 (przykład 4.9)
i rozdz. 13. Werbalna analiza decyzji: decydent porównuje „jednostki” — zestawienia ocen dla jednego, dwóch albo
trzech kryteriów (pozostałe oceny takie same), a relację między wariantami wyprowadza się z tych porównań.

Zadanie (oprócz pól wspólnych; oceny liczbowe albo słowne):
  "comparisons": lista porównań decydenta:
      {"criteria": ["f2", "f5"], "first": [28.81, 29326], "second": [33.32, 6341], "answer": ">"}
      answer: ">" | "=" | "<" | "?" (też "better", "equal", "worse", "unknown"),
  pole kryterium "order" (opcjonalnie): oceny od najbardziej preferowanej, grupa równoważnych jako lista
      (odpowiednik „Order estimates” w programie), np. ["średnia", "duża"] albo [4070659.81, [2596405.1, 2501592.72]].

Reguła wnioskowania (zasada dekompozycji UniComBOS): aⁱ ≽ aʲ, gdy kryteria, na których oceny się różnią, można
podzielić na rozłączne bloki (1–3 kryteria, dla których są porównania), tak by na każdym bloku jednostka aⁱ była
nie gorsza od jednostki aʲ; aⁱ ≻ aʲ, gdy na co najmniej jednym bloku ściśle lepsza. Relacje jednostek tego samego
zbioru kryteriów są domykane przechodnio (z dominacją po współrzędnych według porównań jednokryterialnych),
a relacja wariantów — przechodnio, jak w ZAPROS. Opcja "auto_single": porównania jednokryterialne, których nie
podano, wynikają z kierunku kryterium (direction) — wartość lepsza jest ściśle preferowana.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .problem import Problem, ProblemError
from .zapros import _pack, _partial_order

ANSWERS = {">": 1, "better": 1, "=": 0, "~": 0, "equal": 0, "<": -1, "worse": -1, "?": None, "unknown": None}


def _key(v: Any) -> Any:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return round(float(v), 9)
    if isinstance(v, str):
        s = v.strip()
        try:
            return round(float(s.replace(" ", "").replace(",", ".")), 9)
        except ValueError:
            return s
    raise ProblemError(f"UniComBOS: ocena {v!r} — liczba albo napis")


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v)


class _Units:
    """Relacje ≽ / ≻ między jednostkami jednego zbioru kryteriów (krotki ocen w kolejności kryteriów)."""

    def __init__(self):
        self.ge: Dict[Tuple, Dict[Tuple, bool]] = {}   # ge[u][v] = strict?

    def add(self, u, v, strict):
        self.ge.setdefault(u, {})
        self.ge.setdefault(v, {})
        if v in self.ge[u]:
            self.ge[u][v] = self.ge[u][v] or strict
        else:
            self.ge[u][v] = strict

    def close(self) -> List[Tuple]:
        nodes = list(self.ge)
        for k in nodes:
            for i in nodes:
                if k not in self.ge[i]:
                    continue
                s1 = self.ge[i][k]
                for j, s2 in list(self.ge[k].items()):
                    s = s1 or s2
                    if j not in self.ge[i] or (s and not self.ge[i][j]):
                        self.ge[i][j] = s if j not in self.ge[i] else (self.ge[i][j] or s)
        return [u for u in nodes if self.ge[u].get(u)]

    def rel(self, u, v) -> Optional[bool]:
        """True — u ≻ v, False — u ≽ v (nie ściśle), None — brak relacji ≽."""
        if u == v:
            return False
        return self.ge.get(u, {}).get(v)


def unicombos(p: Problem, auto_single: bool = True, max_block: int = 3) -> Dict[str, Any]:
    notes: List[str] = []
    n, m = p.n, p.m
    names = [c.name for c in p.criteria]
    idx = {c: k for k, c in enumerate(names)}
    X = [[_key(v) for v in row] for row in p.values]

    # --- porównania decydenta → odpowiedzi na zbiorach kryteriów (kolejność kryteriów jak w zadaniu)
    raw = p.extra.get("comparisons") or []
    if not isinstance(raw, list):
        raise ProblemError("UniComBOS: \"comparisons\" — lista porównań")
    answers: Dict[Tuple[int, ...], Dict[Tuple[Tuple, Tuple], List[Tuple[int, Optional[int]]]]] = {}
    for q, c in enumerate(raw):
        crit = c.get("criteria")
        if not isinstance(crit, list) or not crit or any(x not in idx for x in crit) or len(set(crit)) != len(crit):
            raise ProblemError(f"UniComBOS: porównanie {q + 1} — \"criteria\" spoza listy kryteriów")
        a, b = c.get("first"), c.get("second")
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(crit) or len(b) != len(crit):
            raise ProblemError(f"UniComBOS: porównanie {q + 1} — \"first\" i \"second\" muszą mieć {len(crit)} ocen")
        ans = c.get("answer")
        if ans not in ANSWERS:
            raise ProblemError(f"UniComBOS: porównanie {q + 1} — odpowiedź {ans!r} (dozwolone: > = < ?)")
        order = sorted(range(len(crit)), key=lambda t: idx[crit[t]])
        S = tuple(idx[crit[t]] for t in order)
        u = tuple(_key(a[t]) for t in order)
        v = tuple(_key(b[t]) for t in order)
        r = ANSWERS[ans]
        if u > v:                                         # postać kanoniczna pary (repetycje pytania)
            u, v, r = v, u, (None if r is None else -r)
        answers.setdefault(S, {}).setdefault((u, v), []).append((q + 1, r))

    # spójność odpowiedzi na to samo pytanie (program zadaje pytanie trzykrotne trzy razy, rys. 13.7)
    repeated = []
    for S, pairs in answers.items():
        for (u, v), lst in pairs.items():
            vals = {r for _, r in lst if r is not None}
            if len(vals) > 1:
                raise ProblemError("UniComBOS: niespójne odpowiedzi na to samo porównanie (pytania "
                                   + ", ".join(str(q) for q, _ in lst) + ") — należy je powtórzyć")
            if len(lst) > 1:
                repeated.append([q for q, _ in lst])
    if repeated:
        notes.append("Powtórzone pytania z identyczną odpowiedzią (kontrola spójności): "
                     + "; ".join(", ".join(map(str, g)) for g in repeated) + ".")

    # --- porównania jednokryterialne: z answers, pola "order", ewentualnie z kierunku
    single: List[_Units] = [_Units() for _ in range(n)]
    explicit_single = [set() for _ in range(n)]
    for k, c in enumerate(p.criteria):
        order = c.extra.get("order")
        if order is not None:
            groups = [[_key(x) for x in (g if isinstance(g, list) else [g])] for g in order]
            for gi, g in enumerate(groups):
                for x in g:
                    for y in g:
                        if x != y:
                            single[k].add((x,), (y,), False)
                    for h in groups[gi + 1:]:
                        for y in h:
                            single[k].add((x,), (y,), True)
                            explicit_single[k].add(frozenset((x, y)))
                for x, y in combinations(g, 2):
                    explicit_single[k].add(frozenset((x, y)))
        for (u, v), lst in answers.get((k,), {}).items():
            r = next((r for _, r in lst if r is not None), None)
            explicit_single[k].add(frozenset((u[0], v[0])))
            if r is None:
                continue
            if r >= 0:
                single[k].add(u, v, r > 0)
            if r <= 0:
                single[k].add(v, u, r < 0)
    auto_used = []
    for k, c in enumerate(p.criteria):
        vals = sorted({X[i][k] for i in range(m)}, key=str)
        for x, y in combinations(vals, 2):
            if frozenset((x, y)) in explicit_single[k] or single[k].rel((x,), (y,)) is not None \
                    or single[k].rel((y,), (x,)) is not None:
                continue
            if not auto_single:
                continue
            if not all(isinstance(t, float) for t in (x, y)):
                continue
            better, worse = (x, y) if (x > y) == c.maximize else (y, x)
            single[k].add((better,), (worse,), True)
            auto_used.append(names[k])
    if auto_used:
        notes.append("Porównania jednokryterialne z kierunku kryterium (auto_single): "
                     + ", ".join(sorted(set(auto_used), key=idx.get)) + ".")
    for k in range(n):
        cyc = single[k].close()
        if cyc:
            raise ProblemError(f"UniComBOS: sprzeczne porównania dla kryterium {names[k]}: "
                               + ", ".join(_fmt(u[0]) for u in cyc))

    def single_ge(k, x, y) -> Optional[bool]:
        return False if x == y else single[k].rel((x,), (y,))

    # --- jednostki wielokryterialne: odpowiedzi + dominacja po współrzędnych, domknięcie przechodnie
    blocks: Dict[Tuple[int, ...], _Units] = {}
    for S, pairs in answers.items():
        if len(S) == 1:
            continue
        if len(S) > max_block:
            raise ProblemError(f"UniComBOS: porównania obejmują najwyżej {max_block} kryteria")
        U = _Units()
        nodes = set()
        for (u, v), lst in pairs.items():
            r = next((r for _, r in lst if r is not None), None)
            nodes |= {u, v}
            if r is None:
                continue
            if r >= 0:
                U.add(u, v, r > 0)
            if r <= 0:
                U.add(v, u, r < 0)
        nodes |= {tuple(X[i][k] for k in S) for i in range(m)}
        for u in nodes:
            for v in nodes:
                if u == v:
                    continue
                rs = [single_ge(k, a, b) for k, a, b in zip(S, u, v)]
                if all(r is not None for r in rs):
                    U.add(u, v, any(rs))
        cyc = U.close()
        if cyc:
            raise ProblemError("UniComBOS: sprzeczność porównań dla kryteriów " + ", ".join(names[k] for k in S)
                               + " (cykl preferencji) — program UniComBOS prosi wtedy o ich zmianę")
        blocks[S] = U

    def unit_ge(S, u, v) -> Optional[bool]:
        if len(S) == 1:
            return single_ge(S[0], u[0], v[0])
        if u == v:
            return False
        return blocks[S].rel(u, v) if S in blocks else None

    candidates = sorted(blocks, key=len)

    def decompose(i, j) -> Optional[Tuple[bool, List[Tuple[int, ...]]]]:
        """Podział kryteriów, na których aⁱ ≠ aʲ, na bloki z aⁱ ≽ aʲ; preferuje podział ze ścisłą przewagą."""
        diff = tuple(k for k in range(n) if X[i][k] != X[j][k])
        best: List[Optional[Tuple[bool, List]]] = [None]

        def rec(left: Tuple[int, ...], parts, strict):
            if best[0] is not None and best[0][0]:
                return
            if not left:
                if best[0] is None or (strict and not best[0][0]):
                    best[0] = (strict, list(parts))
                return
            k0 = left[0]
            opts = [(k0,)] + [S for S in candidates if S[0] == k0 and set(S) <= set(left)]
            for S in opts:
                r = unit_ge(S, tuple(X[i][k] for k in S), tuple(X[j][k] for k in S))
                if r is None:
                    continue
                rec(tuple(k for k in left if k not in S), parts + [S], strict or r)

        rec(diff, [], False)
        return best[0]

    rel = [["I" if i == j else "R" for j in range(m)] for i in range(m)]
    explain: Dict[str, str] = {}
    for i in range(m):
        for j in range(m):
            if i == j:
                continue
            d = decompose(i, j)
            if d is None:
                continue
            strict, parts = d
            if strict:
                rel[i][j] = "P"
                explain[f"{p.variants[i]} ≻ {p.variants[j]}"] = " + ".join(
                    "(" + ", ".join(names[k] for k in S) + ")" for S in parts)
    for i in range(m):
        for j in range(m):
            if i != j and rel[i][j] == "P" and rel[j][i] == "P":
                raise ProblemError(f"UniComBOS: sprzeczne wnioski {p.variants[i]} ≻ {p.variants[j]} i odwrotnie")
            if i != j and rel[i][j] == "R" and decompose(i, j) is not None and decompose(j, i) is not None:
                rel[i][j] = "I"
    po = _partial_order(p.variants, rel, notes)

    # pytania, które mogą rozstrzygnąć pary nieporównywalne (jak „Compare uncompared”)
    suggestions = []
    for i, j in combinations(range(m), 2):
        if po["relations"][i][j] != "R":
            continue
        diff = [k for k in range(n) if X[i][k] != X[j][k]]
        for k, l in combinations(diff, 2):
            a = single_ge(k, X[i][k], X[j][k])
            b = single_ge(l, X[j][l], X[i][l])
            if a and b and unit_ge((k, l), (X[i][k], X[i][l]), (X[j][k], X[j][l])) is None \
                    and unit_ge((k, l), (X[j][k], X[j][l]), (X[i][k], X[i][l])) is None:
                suggestions.append({"variants": [p.variants[i], p.variants[j]], "criteria": [names[k], names[l]],
                                    "first": [p.values[i][k], p.values[i][l]],
                                    "second": [p.values[j][k], p.values[j][l]]})
    if suggestions:
        notes.append(f"Pary nieporównywalne: {len(suggestions)} pytań o dwa kryteria może je rozstrzygnąć "
                     "(steps.suggested_questions).")
    steps = {"explanation": explain, "suggested_questions": suggestions[:20],
             "comparisons_by_size": {str(s): sum(len(v) for S, v in answers.items() if len(S) == s)
                                     for s in sorted({len(S) for S in answers})}}
    return _pack("unicombos", p, po, steps, notes)
