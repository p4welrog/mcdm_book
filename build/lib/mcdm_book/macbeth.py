"""MACBETH (rozdz. 4.1): skala z jakościowych ocen różnic atrakcyjności przez zadanie PL-MACBETH (4.13),
jednoznaczność (4.14)–(4.16), przeskalowanie 0–100, wagi i oceny końcowe (4.17).

Oceny różnic (macierz judgements, wiersz bardziej atrakcyjny niż kolumna):
  0 / "no"                — równie atrakcyjne (relacja I),
  1–6 albo nazwa kategorii — d₁ „bardzo mała” … d₆ „ekstremalna” (very weak … extreme),
  [s, t] albo "d2-d4"     — kategoria od d_s do d_t, "positive" = [1, 6] (różnica nieznana),
  null                    — brak oceny.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .additive import _result
from .lp import LPError, linprog_max
from .problem import Problem, ProblemError

CATEGORY_NAMES = {
    "very weak": 1, "v. weak": 1, "bardzo mała": 1, "bardzo mala": 1,
    "weak": 2, "mała": 2, "mala": 2,
    "moderate": 3, "umiarkowana": 3,
    "strong": 4, "duża": 4, "duza": 4,
    "very strong": 5, "v. strong": 5, "bardzo duża": 5, "bardzo duza": 5,
    "extreme": 6, "ekstremalna": 6,
}
LABELS = ["no", "very weak", "weak", "moderate", "strong", "very strong", "extreme"]
_HALF = 0.5


def parse_judgement(x: Any, where: str) -> Optional[Tuple[int, int]]:
    """None — brak oceny; (0, 0) — równie atrakcyjne; (s, t) — kategorie d_s … d_t."""
    if x is None or x == "" or x == "?":
        return None
    if isinstance(x, bool):
        raise ProblemError(f"{where}: nieprawidłowa ocena {x!r}")
    if isinstance(x, (int, float)):
        if x != int(x) or not 0 <= x <= 6:
            raise ProblemError(f"{where}: kategoria musi być liczbą całkowitą 0–6")
        return (int(x), int(x))
    if isinstance(x, (list, tuple)):
        if len(x) != 2:
            raise ProblemError(f"{where}: zakres kategorii zapisz jako [s, t]")
        s, t = (parse_judgement(v, where) for v in x)
        if s is None or t is None or s[0] == 0 or t[0] == 0 or s[0] > t[0]:
            raise ProblemError(f"{where}: zakres [s, t] wymaga 1 ≤ s ≤ t ≤ 6")
        return (s[0], t[0])
    s = str(x).strip().lower()
    if s in ("no", "i", "nie ma różnicy", "brak różnicy", "równe", "rowne", "0"):
        return (0, 0)
    if s in ("positive", "nie wiem", "dodatnia"):
        return (1, 6)
    if s in CATEGORY_NAMES:
        k = CATEGORY_NAMES[s]
        return (k, k)
    m = re.fullmatch(r"d?([1-6])\s*(?:-|–|do|to)\s*d?([1-6])", s)
    if m:
        return parse_judgement([int(m.group(1)), int(m.group(2))], where)
    m = re.fullmatch(r"d?([0-6])", s)
    if m:
        return parse_judgement(int(m.group(1)), where)
    raise ProblemError(f"{where}: nieznana ocena {x!r} (użyj 0–6, nazwy kategorii, [s, t] albo \"positive\")")


def _judgements(names: Sequence[str], M: Any, what: str) -> List[Tuple[int, int, int, int]]:
    """Lista (i, j, s, t): i bardziej atrakcyjny od j (s ≥ 1) albo i ~ j (s = t = 0)."""
    n = len(names)
    if not isinstance(M, list) or len(M) != n or any(not isinstance(r, list) or len(r) != n for r in M):
        raise ProblemError(f"{what}: macierz ocen musi mieć wymiar {n}×{n}")
    out, seen = [], {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            jd = parse_judgement(M[i][j], f"{what} [{names[i]}, {names[j]}]")
            if jd is None:
                continue
            key = (min(i, j), max(i, j))
            if key in seen:
                if jd == (0, 0) and seen[key][2:] == (0, 0):
                    continue
                raise ProblemError(f"{what}: para {names[key[0]]}, {names[key[1]]} oceniona dwukrotnie")
            seen[key] = (i, j) + jd
            out.append((i, j) + jd)
    return out


def _order(n: int, J: List[Tuple[int, int, int, int]], names, what) -> List[int]:
    """Porządek od najbardziej atrakcyjnego (sortowanie topologiczne relacji P ∪ I)."""
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i, j, s, _ in J:
        if s == 0:
            parent[find(i)] = find(j)
    better = {find(k): set() for k in range(n)}
    for i, j, s, _ in J:
        if s > 0:
            if find(i) == find(j):
                raise ProblemError(f"{what}: brak rankingu — {names[i]} jest jednocześnie równie atrakcyjny "
                                   f"i lepszy od {names[j]}")
            better[find(j)].add(find(i))
    order, done = [], set()
    groups = sorted(better, key=lambda g: min(k for k in range(n) if find(k) == g))
    while len(done) < len(groups):
        ready = [g for g in groups if g not in done and better[g] <= done]
        if not ready:
            raise ProblemError(f"{what}: brak rankingu — relacja „bardziej atrakcyjny” zawiera cykl")
        g = ready[0]
        done.add(g)
        order += [k for k in range(n) if find(k) == g]
    return order


def _constraints(n: int, J, fixed: Dict[int, float]):
    """Ograniczenia S_mac (4.13): zmienne v(x_0…x_{n−1}), d_1…d_6."""
    N = n + 6
    A_ub, b_ub, A_eq, b_eq = [], [], [], []
    D = lambda k: n + k - 1

    def row(**coef):
        r = [0.0] * N
        for k, v in coef.items():
            r[int(k[1:])] += v
        return r
    for i, j, s, t in J:
        if s == 0:
            r = [0.0] * N
            r[i], r[j] = 1.0, -1.0
            A_eq.append(r); b_eq.append(0.0)
            continue
        r = [0.0] * N                       # d_s + 0,5 ≤ v_i − v_j
        r[D(s)] += 1.0; r[i] -= 1.0; r[j] += 1.0
        A_ub.append(r); b_ub.append(-_HALF)
        if t <= 5:                          # v_i − v_j ≤ d_{t+1} − 0,5
            r = [0.0] * N
            r[i] += 1.0; r[j] -= 1.0; r[D(t + 1)] -= 1.0
            A_ub.append(r); b_ub.append(-_HALF)
    r = [0.0] * N
    r[D(1)] = 1.0
    A_eq.append(r); b_eq.append(0.5)       # d_1 = 0,5
    for k in range(2, 7):                   # d_{k−1} + 1 ≤ d_k
        r = [0.0] * N
        r[D(k - 1)] = 1.0; r[D(k)] = -1.0
        A_ub.append(r); b_ub.append(-1.0)
    for i, val in fixed.items():
        r = [0.0] * N
        r[i] = 1.0
        A_eq.append(r); b_eq.append(val)
    return N, A_ub, b_ub, A_eq, b_eq


def _solve(n, J, fixed, target, sense):
    N, A_ub, b_ub, A_eq, b_eq = _constraints(n, J, fixed)
    c = [0.0] * N
    c[target] = 1.0 if sense == "max" else -1.0
    x, val = linprog_max(c, A_ub, b_ub, A_eq, b_eq)
    return x, (val if sense == "max" else -val)


def _repair_hint(n, J, names, what) -> str:
    """Pojedyncze zmiany kategorii przywracające spójność (sugestia jak w M-MACBETH, bez zmian wielokrotnych)."""
    fixes = []
    for k, (i, j, s, t) in enumerate(J):
        if s == 0:
            continue
        best = None
        for s2 in range(1, 7):
            if s2 == s and t == s:
                continue
            try:
                _solve(n, J[:k] + [(i, j, s2, s2)] + J[k + 1:], {}, 0, "min")
            except LPError:
                continue
            d = abs(s2 - s) if s2 < s else abs(s2 - t)
            if best is None or d < best[0]:
                best = (d, s2)
        if best:
            old = LABELS[s] if s == t else f"{LABELS[s]}–{LABELS[t]}"
            fixes.append((best[0], f"{names[i]}–{names[j]}: {old} → {LABELS[best[1]]}"))
    if fixes:
        fixes.sort(key=lambda f: f[0])
        return " Spójność przywraca jedna ze zmian: " + "; ".join(f for _, f in fixes) + "."
    return ""


def scale(names: Sequence[str], M: Any, what: str = "macierz", upper: Any = None, lower: Any = None,
          notes: Optional[list] = None) -> Dict[str, Any]:
    """Podstawowa skala MACBETH (4.13)–(4.16) i jej przeskalowanie: upper → 100, lower → 0
    (domyślnie najbardziej i najmniej atrakcyjny element)."""
    names = [str(x) for x in names]
    n = len(names)
    if n < 2:
        raise ProblemError(f"{what}: potrzebne co najmniej 2 elementy")
    J = _judgements(names, M, what)
    order = _order(n, J, names, what)
    # numeracja zmiennych w kolejności atrakcyjności: x_1 = najlepszy
    pos = {k: r for r, k in enumerate(order)}
    Jo = [(pos[i], pos[j], s, t) for i, j, s, t in J]
    try:
        x, v1 = _solve(n, Jo, {}, 0, "min")                                    # PL-MACBETH (4.13)
    except LPError as e:
        if "sprzeczne" in str(e):
            raise ProblemError(f"{what}: niespójne oceny (brak skali spełniającej (4.9)–(4.11))."
                               + _repair_hint(n, Jo, [names[k] for k in order], what)) from None
        raise ProblemError(f"{what}: {e}") from None
    mu = {0: v1}
    ranges = []
    for r in range(1, n):                                                      # (4.14)–(4.16)
        try:
            _, hi = _solve(n, Jo, mu, r, "max")
        except LPError:
            raise ProblemError(f"{what}: element {names[order[r]]} nie jest powiązany ocenami z pozostałymi "
                               "(skala nieograniczona) — uzupełnij porównania") from None
        _, lo = _solve(n, Jo, mu, r, "min")
        mu[r] = (lo + hi) / 2
        ranges.append((names[order[r]], lo, hi))
    basic = [0.0] * n
    for r, k in enumerate(order):
        basic[k] = mu[r]

    def idx(ref, default):
        if ref is None:
            return default
        if isinstance(ref, int) and not isinstance(ref, bool) and 0 <= ref < n:
            return ref
        s = str(ref)
        if s not in names:
            raise ProblemError(f"{what}: nieznany poziom odniesienia {ref!r}")
        return names.index(s)
    iu, il = idx(upper, order[0]), idx(lower, order[-1])
    if basic[iu] - basic[il] <= 1e-12:
        raise ProblemError(f"{what}: poziom „górny” musi być bardziej atrakcyjny od „dolnego”")
    scaled = [100 * (b - basic[il]) / (basic[iu] - basic[il]) for b in basic]
    if notes is not None and any(hi - lo > 1e-9 for _, lo, hi in ranges):
        notes.append(f"{what}: rozwiązanie PL-MACBETH nie było jednoznaczne — przyjęto środki przedziałów (4.16).")
    return {"elements": names, "order": [names[k] for k in order], "basic": basic, "scale": scaled,
            "upper": names[iu], "lower": names[il],
            "judgements": [[names[i], names[j], s, t] for i, j, s, t in J]}


def _interp(x: float, xs: List[float], ys: List[float]) -> Tuple[float, bool]:
    pts = sorted(zip(xs, ys))
    xs, ys = [a for a, _ in pts], [b for _, b in pts]
    if len(set(xs)) != len(xs):
        raise ProblemError("Poziomy ilościowe muszą być różne")
    out = x < xs[0] or x > xs[-1]
    k = 0 if x <= xs[0] else (len(xs) - 2 if x >= xs[-1] else max(i for i in range(len(xs) - 1) if xs[i] <= x))
    x0, x1, y0, y1 = xs[k], xs[k + 1], ys[k], ys[k + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0), out


def macbeth(p: Problem) -> Dict[str, Any]:
    """MACBETH: kryteria z polem "macbeth" ({"levels"?, "judgements", "upper"?, "lower"?}) albo z gotowymi ocenami
    0–100 w values; wagi z "criteria_judgements" (opcjonalnie z dodatkowym elementem odniesienia — ostatni
    wiersz, np. [ all lower ]) albo z pól weight."""
    notes: list = []
    m, n = p.m, p.n
    partial = [[0.0] * n for _ in range(m)]
    scales: Dict[str, Any] = {}
    for k, c in enumerate(p.criteria):
        spec = c.extra.get("macbeth")
        if spec is None:
            for i in range(m):
                v = p.values[i][k]
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    raise ProblemError(f"Kryterium {c.name}: bez pola \"macbeth\" oceny {p.variants[i]} muszą być "
                                       "liczbami w skali MACBETH (0 = poziom dolny, 100 = górny)")
                partial[i][k] = float(v)
            continue
        if isinstance(spec, list):
            spec = {"judgements": spec}
        levels = spec.get("levels")
        direct = levels is None
        lv = p.variants if direct else levels
        sc = scale([str(x) for x in lv], spec.get("judgements"), f"Kryterium {c.name}",
                   spec.get("upper"), spec.get("lower"), notes)
        scales[c.name] = sc
        if direct:
            for i in range(m):
                partial[i][k] = sc["scale"][i]
            continue
        labels = [str(x) for x in levels]
        numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in levels)
        outside = []
        for i in range(m):
            v = p.values[i][k]
            if str(v) in labels and not (numeric and isinstance(v, (int, float))):
                partial[i][k] = sc["scale"][labels.index(str(v))]
            elif numeric and isinstance(v, (int, float)) and not isinstance(v, bool):
                partial[i][k], out = _interp(float(v), [float(x) for x in levels], sc["scale"])
                if out:
                    outside.append(p.variants[i])
            else:
                raise ProblemError(f"Kryterium {c.name}: ocena {v!r} wariantu {p.variants[i]} nie jest żadnym "
                                   f"z poziomów {labels}")
        if numeric:
            sc["interpolation"] = "odcinkowo liniowa"
        if outside:
            notes.append(f"Kryterium {c.name}: oceny {', '.join(outside)} poza zakresem poziomów — ekstrapolacja "
                         "liniowa z najbliższego odcinka.")
    cj = p.extra.get("criteria_judgements")
    if cj is not None:
        names = [c.name for c in p.criteria]
        ref = None
        if isinstance(cj, list) and len(cj) == n + 1:
            ref = str(p.extra.get("criteria_reference", "[ all lower ]"))
            names = names + [ref]
        ws = scale(names, cj, "Wagi kryteriów", None, ref if ref is not None else None, notes)
        raw = ws["scale"][:n]
        if any(x < -1e-9 for x in raw):
            raise ProblemError("Wagi kryteriów: element odniesienia musi być najmniej ważny")
        tot = sum(raw)
        if tot <= 0:
            raise ProblemError("Wagi kryteriów: wszystkie wagi zerowe")
        w = [x / tot for x in raw]
        if ref is None and min(raw) < 1e-9:
            notes.append("Wagi z porównań samych kryteriów: najmniej ważne kryterium dostaje wagę 0 (skala 0–100). "
                         "Dodaj element odniesienia (np. „[ all lower ]” — wszystkie kryteria na poziomie dolnym) "
                         "jako ostatni wiersz macierzy, jak w M-MACBETH.")
        scales["weights"] = ws
    else:
        w = p.weights(notes=notes)
    scores = [sum(w[k] * partial[i][k] for k in range(n)) for i in range(m)]
    return _result("macbeth", p, scores, "ocena końcowa p_i (4.17)",
                   {"weights": w, "partial_scores": partial, "scales": scales}, notes)


def macbeth_scale(p: Problem, upper: Any = None, lower: Any = None) -> Dict[str, Any]:
    """Skala MACBETH dla jednej macierzy: elementy = warianty, pole "judgements" (np. porównania kryteriów)."""
    notes: list = []
    sc = scale(p.variants, p.extra.get("judgements"), "Macierz ocen", upper, lower, notes)
    res = _result("macbeth_scale", p, sc["scale"], "skala MACBETH (górny = 100, dolny = 0)",
                  {"basic": sc["basic"], "order": sc["order"], "upper": sc["upper"], "lower": sc["lower"],
                   "judgements": sc["judgements"]}, notes)
    tot = sum(sc["scale"])
    if all(x >= -1e-9 for x in sc["scale"]) and tot > 0:
        res["steps"]["weights"] = [x / tot for x in sc["scale"]]
    return res
