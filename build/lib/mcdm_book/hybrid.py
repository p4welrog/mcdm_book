"""DEMATEL i metoda hybrydowa DEMATEL–ANP–VIKOR (rozdz. 7.4).

DEMATEL: macierz ocen wpływu O (0–4; kilku ekspertów → średnia), X = sO (7.25)–(7.26),
T = X(I − X)⁻¹ (7.27), wskaźniki znaczenia r + c i relacji r − c.

Metoda hybrydowa: kryteria mają pole "cluster" (grupa kryteriów); zadanie zawiera:
  "cluster_influence"   — macierz wpływu grup (kolejność grup jak w "clusters" albo pierwszego wystąpienia),
  "criteria_influence"  — macierz wpływu kryteriów (kolejność kryteriów),
  opcjonalnie "clusters" — lista nazw grup.
T grup → α-cięcie i normalizacja wierszy (7.30)–(7.31) → T_D; T kryteriów → normalizacja wierszy → T_f;
Ω = T_fᵀ; Ω^α — blok (i, j) mnożony przez t^D_ij (7.32), kolumny normalizowane; Ω^lim (7.33) — wagi
kryteriów; ranking VIKOR (7.3).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .additive import _result
from .anp import limit_matrix
from .problem import Problem, ProblemError
from .reference import vikor

_TOL = 1e-12


def _num_matrix(M: Any, n: int, what: str) -> List[List[float]]:
    if not isinstance(M, list) or len(M) != n or any(not isinstance(r, list) or len(r) != n for r in M):
        raise ProblemError(f"{what}: oczekiwano macierzy {n}×{n}")
    out = []
    for r in M:
        row = []
        for x in r:
            if x is None or x == "x":
                row.append(None)
            else:
                try:
                    row.append(float(x))
                except (TypeError, ValueError):
                    raise ProblemError(f"{what}: niepoprawna wartość {x!r}")
        out.append(row)
    return out


def _average(O: Any, n: int, what: str, notes: list) -> List[List[float]]:
    """Macierz albo lista macierzy ekspertów → macierz średnich (krok 1). Brak przekątnej (None) → 0."""
    mats = O if (isinstance(O, list) and O and isinstance(O[0], list) and O[0] and isinstance(O[0][0], list)) else [O]
    Ms = [_num_matrix(M, n, what) for M in mats]
    avg = [[sum((M[i][j] or 0.0) for M in Ms) / len(Ms) for j in range(n)] for i in range(n)]
    if any(M[i][i] is None for M in Ms for i in range(n)):
        notes.append(f"{what}: brak ocen na przekątnej — przyjęto 0.")
    if len(Ms) > 1:
        notes.append(f"{what}: średnia ocen {len(Ms)} ekspertów.")
    return avg


def _inverse(A: List[List[float]]) -> List[List[float]]:
    n = len(A)
    M = [list(map(float, r)) + [1.0 if i == j else 0.0 for j in range(n)] for i, r in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-14:
            raise ProblemError("DEMATEL: macierz I − X jest osobliwa")
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        M[c] = [x / pv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [r[n:] for r in M]


def _mm(A, B):
    return [[sum(a * b for a, b in zip(r, col)) for col in zip(*B)] for r in A]


def dematel_matrices(O: List[List[float]]) -> Dict[str, Any]:
    """Kroki 2–4 metody DEMATEL dla macierzy średnich ocen O."""
    n = len(O)
    rs, cs = max(sum(r) for r in O), max(sum(c) for c in zip(*O))
    if rs <= 0 or cs <= 0:
        raise ProblemError("DEMATEL: macierz wpływu jest zerowa")
    s = min(1 / rs, 1 / cs)                                                                    # (7.26)
    X = [[s * x for x in r] for r in O]                                                        # (7.25)
    T = _mm(X, _inverse([[(1.0 if i == j else 0.0) - X[i][j] for j in range(n)] for i in range(n)]))  # (7.27)
    r = [sum(row) for row in T]
    c = [sum(col) for col in zip(*T)]
    return {"s": s, "X": X, "T": T, "r": r, "c": c, "prominence": [a + b for a, b in zip(r, c)],
            "relation": [a - b for a, b in zip(r, c)]}


def alpha_normalize(T: List[List[float]], alpha: float, notes: list, what: str) -> List[List[float]]:
    """α-cięcie (t < α → 0) i podział wierszy przez sumy d_i (7.30)–(7.31)."""
    Ta = [[x if x >= alpha else 0.0 for x in r] for r in T]
    out = []
    for i, r in enumerate(Ta):
        d = sum(r)
        if d <= _TOL:
            notes.append(f"{what}: wiersz {i + 1} po α-cięciu jest zerowy — pozostawiono zera.")
            out.append([0.0] * len(r))
        else:
            out.append([x / d for x in r])
    return out


def dematel(p: Problem) -> Dict[str, Any]:
    """DEMATEL (7.4): elementy systemu to „warianty” zadania, pole "influence" — macierz ocen wpływu
    (0–4; wiersz wpływa na kolumnę) albo lista macierzy kilku ekspertów. Wynik: wskaźnik znaczenia r + c
    (scores), wskaźnik relacji r − c w steps (dodatni — element przyczynowy, ujemny — wynikowy).
    Metoda nie wspomaga wyboru wariantu (przyp. 68) — służy do opisu zależności."""
    notes: list = []
    O = p.extra.get("influence")
    if O is None:
        raise ProblemError("DEMATEL: podaj \"influence\" — macierz ocen wpływu elementów (wiersz → kolumna)")
    O = _average(O, p.m, "influence", notes)
    D = dematel_matrices(O)
    cause = [v for v, x in zip(p.variants, D["relation"]) if x > 1e-12]
    notes.append("Elementy przyczynowe (r − c > 0): " + (", ".join(cause) or "brak") + "; pozostałe — wynikowe.")
    res = _result("dematel", p, D["prominence"], "wskaźnik znaczenia r + c", {"O": O, **D}, notes)
    return res


def hybrid(p: Problem, alpha: float = 0.0, alpha_criteria: float = 0.0, q: float = 0.5,
           ideal: Optional[Sequence[float]] = None, anti_ideal: Optional[Sequence[float]] = None,
           w2: str = "both", limit: str = "auto") -> Dict[str, Any]:
    """Metoda hybrydowa DEMATEL–ANP–VIKOR (7.4): wagi kryteriów z supermacierzy granicznej, ranking VIKOR."""
    notes: list = []
    n = p.n
    groups = [c.extra.get("cluster") for c in p.criteria]
    if any(g is None for g in groups):
        raise ProblemError("Metoda hybrydowa: każde kryterium musi mieć pole \"cluster\" (grupa kryteriów)")
    names = list(p.extra.get("clusters") or dict.fromkeys(groups))
    if set(names) != set(groups):
        raise ProblemError("\"clusters\" musi zawierać dokładnie grupy użyte w kryteriach")
    G = len(names)
    gi = [names.index(g) for g in groups]
    if p.extra.get("cluster_influence") is None or p.extra.get("criteria_influence") is None:
        raise ProblemError("Metoda hybrydowa: podaj \"cluster_influence\" (grupy) i \"criteria_influence\" (kryteria)")
    Oc = _average(p.extra["cluster_influence"], G, "cluster_influence", notes)
    Dc = dematel_matrices(Oc)
    TD = alpha_normalize(Dc["T"], alpha, notes, "T grup")                                     # (7.30)–(7.31)
    Of = _average(p.extra["criteria_influence"], n, "criteria_influence", notes)
    Df = dematel_matrices(Of)
    Tf = alpha_normalize(Df["T"], alpha_criteria, notes, "T kryteriów")
    Om = [list(col) for col in zip(*Tf)]                                                      # Ω = T_fᵀ
    W = [[TD[gi[i]][gi[j]] * Om[i][j] for j in range(n)] for i in range(n)]                    # (7.32)
    cs = [sum(W[i][j] for i in range(n)) for j in range(n)]
    for j in range(n):
        if cs[j] > _TOL:
            for i in range(n):
                W[i][j] /= cs[j]
    lim = limit_matrix(W, limit)                                                              # (7.33)
    L = lim["G"]
    wts = [sum(L[i][j] for j in range(n)) / n for i in range(n)]
    s = sum(wts)
    wts = [x / s for x in wts]
    q_p = Problem.from_dict({**p.to_dict(), "criteria": [
        {"name": c.name, "direction": c.direction, "weight": w} for c, w in zip(p.criteria, wts)]})
    res = vikor(q_p, q=q, ideal=ideal, anti_ideal=anti_ideal, w2=w2)
    res["method"] = "hybrid"
    res["notes"] = notes + [x for x in res["notes"] if not x.startswith("Wagi sumowały")]
    res["steps"].update({"clusters": names, "cluster_T": Dc["T"], "T_D": TD, "criteria_T": Df["T"], "T_f": Tf,
                         "weighted_supermatrix": W, "limit_supermatrix": L, "limit_mode": lim["mode"],
                         "weights": wts, "cluster_dematel": {k: Dc[k] for k in ("r", "c", "prominence", "relation")}})
    return res
