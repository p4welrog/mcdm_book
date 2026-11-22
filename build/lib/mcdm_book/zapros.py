"""Metody werbalne (rozdz. 4.2): ZAPROS (wspólna skala porządkowa JOS) i ZAPROS III (wariacje jakościowe,
JSQV → JSCV, formalny indeks jakości FIQ). Wynik: częściowy porządek wariantów i rangi (także „rozmyte”).

Kryteria mają pole "scale" — oceny od najlepszej do najgorszej (np. ["A1", "A2", "A3"]); values to te oceny.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .problem import Problem, ProblemError


def _scales(p: Problem) -> List[List[str]]:
    out = []
    for c in p.criteria:
        sc = c.extra.get("scale")
        if not isinstance(sc, list) or len(sc) < 2:
            raise ProblemError(f"Kryterium {c.name}: pole \"scale\" — lista ocen od najlepszej do najgorszej")
        out.append([str(x) for x in sc])
    allg = [g for sc in out for g in sc]
    if len(set(allg)) != len(allg):
        raise ProblemError("Oceny w skalach kryteriów muszą być różne (np. A1, A2, … dla f1; B1, B2, … dla f2)")
    for i, row in enumerate(p.values):
        for k, v in enumerate(row):
            if str(v) not in out[k]:
                raise ProblemError(f"Wariant {p.variants[i]}: ocena {v!r} spoza skali kryterium {p.criteria[k].name}")
    return out


def _grade_index(scales):
    return {g: (k, r) for k, sc in enumerate(scales) for r, g in enumerate(sc)}


# ---------------------------------------------------------------------------
# porządek częściowy, rangi
# ---------------------------------------------------------------------------

def _vector_compare(a: Sequence[float], b: Sequence[float]) -> str:
    """Porównanie posortowanych wektorów rang (mniej = lepiej): P (a lepszy), P- (b lepszy), I, R."""
    a, b = sorted(a), sorted(b)
    le = all(x <= y for x, y in zip(a, b))
    ge = all(x >= y for x, y in zip(a, b))
    if le and ge:
        return "I"
    if le:
        return "P"
    if ge:
        return "P-"
    return "R"


def _partial_order(names: List[str], rel: List[List[str]], notes: list) -> Dict[str, Any]:
    m = len(names)
    # klasy równoważności (I)
    cls = list(range(m))
    for i in range(m):
        for j in range(i + 1, m):
            if rel[i][j] == "I":
                a, b = cls[i], cls[j]
                cls = [a if x == b else x for x in cls]
    better = [[rel[i][j] == "P" for j in range(m)] for i in range(m)]
    # domknięcie przechodnie (jak w książce: aⁱ ≻ aʲ i aʲ ≻ aˡ ⇒ aⁱ ≻ aˡ)
    clos = [row[:] for row in better]
    for k in range(m):
        for i in range(m):
            if clos[i][k]:
                for j in range(m):
                    if clos[k][j]:
                        clos[i][j] = True
    added = [(names[i], names[j]) for i in range(m) for j in range(m) if clos[i][j] and not better[i][j]]
    cyc = [names[i] for i in range(m) if clos[i][i]]
    if cyc:
        raise ProblemError("Relacja preferencji między wariantami zawiera cykl: " + ", ".join(cyc))
    if added:
        notes.append("Z przechodniości dodano: " + ", ".join(f"{a} ≻ {b}" for a, b in added) + ".")
    # rangi: dolna = 1 + najdłuższy łańcuch dominujących; górna — rozmyta (Larichev 2001)
    order = []
    left = set(range(m))
    low = [0] * m
    while left:
        ready = [i for i in left if not any(clos[j][i] for j in left)]
        for i in ready:
            low[i] = 1 + max((low[j] for j in range(m) if clos[j][i]), default=0)
        left -= set(ready)
        order += ready
    high = []
    maxr = max(low)
    for i in range(m):
        dom = [low[j] for j in range(m) if clos[i][j]]
        high.append(min(dom) - 1 if dom else low[i])
    # krawędzie diagramu Hassego
    edges = [(names[i], names[j]) for i in range(m) for j in range(m)
             if clos[i][j] and not any(clos[i][k] and clos[k][j] for k in range(m))]
    full = [["I" if i == j or rel[i][j] == "I" else ("P" if clos[i][j] else ("P-" if clos[j][i] else "R"))
             for j in range(m)] for i in range(m)]
    return {"low": low, "high": high, "edges": edges, "relations": full, "levels": maxr}


def _pack(method: str, p: Problem, po: Dict[str, Any], steps: Dict[str, Any], notes: list,
          tiebreak: Optional[List[float]] = None) -> Dict[str, Any]:
    low, high = po["low"], po["high"]
    rk = low
    best = [v for v, r in zip(p.variants, rk) if r == 1]
    order = sorted(range(p.m), key=lambda i: (rk[i], high[i], tiebreak[i] if tiebreak else 0, i))
    fuzzy = [f"{p.variants[i]}: {low[i]}–{high[i]}" for i in range(p.m) if high[i] > low[i]]
    if fuzzy:
        notes.append("Rangi „rozmyte”: " + ", ".join(fuzzy) + ".")
    inc = sorted({tuple(sorted((p.variants[i], p.variants[j]))) for i in range(p.m) for j in range(p.m)
                  if po["relations"][i][j] == "R"})
    if inc:
        notes.append("Pary nieporównywalne: " + ", ".join(f"{a}–{b}" for a, b in inc) + ".")
    steps.update({"relations": po["relations"], "edges": [list(e) for e in po["edges"]],
                  "rank_low": low, "rank_high": high})
    return {"method": method, "variants": p.variants, "criteria": [c.name for c in p.criteria],
            "scores": {"label": "ranga w porządku częściowym (mniej = lepiej)",
                       "values": [float(x) for x in rk], "better": "lower"},
            "ranks": rk, "ranking": [p.variants[i] for i in order], "best": best, "steps": steps, "notes": notes}


# ---------------------------------------------------------------------------
# ZAPROS (4.2.2)
# ---------------------------------------------------------------------------

def _jos_from_relations(scales, Y: List[str], M: Any, notes: list) -> Dict[str, int]:
    """Rangi JOS z porównań wektorów ze zbioru Y (macierz P / I, wiersz względem kolumny)."""
    n = len(Y)
    if not isinstance(M, list) or len(M) != n or any(len(r) != n for r in M):
        raise ProblemError(f"y_comparisons: macierz {n}×{n} (kolejność: wektor najlepszy, potem kolejne oceny "
                           "gorsze od najlepszej wg kryteriów)")
    rel = [[None] * n for _ in range(n)]
    for i in range(n):
        rel[i][i] = "I"
        for j in range(n):
            if i == j or M[i][j] in (None, ""):
                continue
            x = str(M[i][j]).strip().upper()
            if x not in ("P", "I", "P-"):
                raise ProblemError(f"y_comparisons [{Y[i]}, {Y[j]}]: P, I albo P-")
            inv = {"P": "P-", "P-": "P", "I": "I"}[x]
            for a, b, r in ((i, j, x), (j, i, inv)):
                if rel[a][b] not in (None, r):
                    raise ProblemError(f"y_comparisons: sprzeczne oceny pary {Y[i]}, {Y[j]}")
                rel[a][b] = r
    miss = [f"{Y[i]}–{Y[j]}" for i in range(n) for j in range(i + 1, n) if rel[i][j] is None]
    if miss:
        raise ProblemError("y_comparisons: brak porównań " + ", ".join(miss) + " — JOS wymaga porządku zupełnego")
    for i in range(n):
        for j in range(n):
            for k in range(n):
                a, b = rel[i][j], rel[j][k]
                if a in ("P", "I") and b in ("P", "I") and (a == "P" or b == "P") and rel[i][k] != "P":
                    raise ProblemError(f"y_comparisons: naruszona przechodniość ({Y[i]}, {Y[j]}, {Y[k]})")
                if a == "I" and b == "I" and rel[i][k] != "I":
                    raise ProblemError(f"y_comparisons: naruszona przechodniość ({Y[i]}, {Y[j]}, {Y[k]})")
    rank = {}
    for i in range(n):
        above = {min(j2 for j2 in range(n) if rel[j][j2] == "I") for j in range(n) if rel[j][i] == "P"}
        rank[Y[i]] = 1 + len(above)
    return rank


def zapros(p: Problem) -> Dict[str, Any]:
    """ZAPROS: pole "jos" ({ocena: ranga} albo lista grup ocen od rangi 1) albo "y_comparisons" (macierz porównań
    wektorów ze zbioru Y (4.18): najlepszy, potem każda gorsza ocena przy pozostałych najlepszych)."""
    notes: list = []
    scales = _scales(p)
    best = [sc[0] for sc in scales]
    Y = ["+".join(best)] + [g for sc in scales for g in sc[1:]]
    if "jos" in p.extra:
        jos = p.extra["jos"]
        if isinstance(jos, list):
            jos = {str(g): r + 1 for r, grp in enumerate(jos) for g in (grp if isinstance(grp, list) else [grp])}
        jos = {str(k): int(v) for k, v in jos.items()}
        for g in best:
            jos.setdefault(g, 1)
    elif "y_comparisons" in p.extra:
        r = _jos_from_relations(scales, Y, p.extra["y_comparisons"], notes)
        jos = {g: r[Y[0]] for g in best}
        jos.update({g: r[g] for g in Y[1:]})
    else:
        raise ProblemError("ZAPROS: podaj \"jos\" (rangi ocen we wspólnej skali porządkowej) albo \"y_comparisons\"")
    missing = [g for sc in scales for g in sc if g not in jos]
    if missing:
        raise ProblemError("JOS: brak rang ocen " + ", ".join(missing))
    for k, sc in enumerate(scales):
        rs = [jos[g] for g in sc]
        if any(a >= b for a, b in zip(rs, rs[1:])):
            notes.append(f"Kryterium {p.criteria[k].name}: rangi JOS nie rosną wraz z pogarszaniem oceny "
                         f"({', '.join(f'{g} {jos[g]}' for g in sc)}).")
    vec = [[jos[str(v)] for v in row] for row in p.values]
    m = p.m
    rel = [[_vector_compare(vec[i], vec[j]) if i != j else "I" for j in range(m)] for i in range(m)]
    po = _partial_order(p.variants, rel, notes)
    steps = {"jos": jos, "Y": Y, "jos_vectors": vec, "jos_sorted": [sorted(v) for v in vec],
             "direct_relations": rel}
    return _pack("zapros", p, po, steps, notes)


# ---------------------------------------------------------------------------
# ZAPROS III (4.2.3)
# ---------------------------------------------------------------------------

def _qv(x: Any, gi) -> Tuple[str, str]:
    if isinstance(x, (list, tuple)) and len(x) == 2:
        a, b = str(x[0]), str(x[1])
    else:
        s = str(x).replace("→", ">").replace("->", ">").replace("(", "").replace(")", "")
        if ">" not in s:
            raise ProblemError(f"Wariacja jakościowa {x!r}: zapisz jako \"A1>A2\" albo [\"A1\", \"A2\"]")
        a, b = (t.strip() for t in s.split(">", 1))
    if a not in gi or b not in gi or gi[a][0] != gi[b][0] or gi[a][1] >= gi[b][1]:
        raise ProblemError(f"Wariacja jakościowa {a}→{b}: obie oceny z jednego kryterium, od lepszej do gorszej")
    return a, b


def _merge(chains: List[List[Tuple[str, str]]], allqv: List[Tuple[str, str]], notes: list) -> List[Tuple[str, str]]:
    """JSCV z JSQV: kolejno wariacja, której żadna pozostała nie poprzedza w żadnej JSQV."""
    before = {q: set() for q in allqv}
    for ch in chains:
        for i, q in enumerate(ch):
            before[q] |= set(ch[:i])
    out, done = [], set()
    while len(out) < len(allqv):
        ready = [q for q in allqv if q not in done and before[q] <= done]
        if not ready:
            raise ProblemError("JSQV są sprzeczne (cykl) — wyjaśnij z decydentem naruszenie przechodniości")
        if len(ready) > 1:
            notes.append("JSCV niejednoznaczna: " + ", ".join(f"({a}→{b})" for a, b in ready)
                         + " — przyjęto kolejność podania.")
        out.append(ready[0])
        done.add(ready[0])
    return out


def _qv_from_matrix(names: List[Tuple[str, str]], M: Any) -> List[Tuple[str, str]]:
    """JSQV z tablicy porównań wariacji (P w wierszu = wariacja z wiersza preferowana, tj. mniej dotkliwa)."""
    n = len(names)
    if not isinstance(M, list) or len(M) != n or any(len(r) != n for r in M):
        raise ProblemError(f"Tablica porównań wariacji: macierz {n}×{n}")
    beats = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i != j and str(M[i][j] or "").strip().upper() == "P":
                beats[j].add(i)
    out, done = [], set()
    while len(out) < n:
        ready = [i for i in range(n) if i not in done and beats[i] <= done]
        if len(ready) != 1:
            raise ProblemError("Tablica porównań wariacji nie wyznacza porządku liniowego")
        out.append(names[ready[0]])
        done.add(ready[0])
    return out


def zapros_iii(p: Problem) -> Dict[str, Any]:
    """ZAPROS III: pole "jscv" (wariacje od najmniej dotkliwej, np. ["C1>C2", "A1>A2", …]) albo "jsqv" (lista
    skal dla par kryteriów, łączona w JSCV), albo "qv_comparisons" (lista {"qv": [...], "matrix": P/I}).
    Porównanie wariantów rangami wariacji (Larichev 2001), FIQ względem wariantu idealnego, rangi jąder."""
    notes: list = []
    scales = _scales(p)
    gi = _grade_index(scales)
    allqv = [(sc[a], sc[b]) for sc in scales for a in range(len(sc)) for b in range(a + 1, len(sc))]
    if "jscv" in p.extra:
        jscv = [_qv(x, gi) for x in p.extra["jscv"]]
        steps_src = "jscv"
    else:
        chains = []
        if "jsqv" in p.extra:
            chains = [[_qv(x, gi) for x in ch] for ch in p.extra["jsqv"]]
        elif "qv_comparisons" in p.extra:
            for t in p.extra["qv_comparisons"]:
                chains.append(_qv_from_matrix([_qv(x, gi) for x in t["qv"]], t["matrix"]))
        else:
            raise ProblemError("ZAPROS III: podaj \"jscv\", \"jsqv\" albo \"qv_comparisons\"")
        present = {q for ch in chains for q in ch}
        jscv = _merge(chains, [q for q in allqv if q in present], notes)
        steps_src = "jsqv"
    if len(set(jscv)) != len(jscv):
        raise ProblemError("JSCV: wariacja powtórzona")
    missing = [f"({a}→{b})" for a, b in allqv if (a, b) not in jscv]
    if missing:
        raise ProblemError("JSCV: brak wariacji " + ", ".join(missing))
    qrank = {q: r + 1 for r, q in enumerate(jscv)}
    m, n = p.m, p.n
    vals = [[str(v) for v in row] for row in p.values]

    def pair_vectors(a, b):
        va, vb = [], []
        for k in range(n):
            x, y = a[k], b[k]
            if x == y:
                va.append(0); vb.append(0)
            elif gi[x][1] < gi[y][1]:
                va.append(0); vb.append(qrank[(x, y)])
            else:
                va.append(qrank[(y, x)]); vb.append(0)
        return va, vb
    rel = [["I"] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            if i != j:
                va, vb = pair_vectors(vals[i], vals[j])
                rel[i][j] = _vector_compare(va, vb)
    ideal = [sc[0] for sc in scales]
    fiq = [sum(pair_vectors(ideal, vals[i])[1]) for i in range(m)]
    po = _partial_order(p.variants, rel, notes)
    steps = {"jscv": [f"{a}>{b}" for a, b in jscv], "qv_ranks": {f"{a}>{b}": r for (a, b), r in qrank.items()},
             "source": steps_src, "FIQ": fiq, "direct_relations": rel}
    return _pack("zapros_iii", p, po, steps, notes, tiebreak=fiq)
