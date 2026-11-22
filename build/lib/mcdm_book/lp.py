"""Mały solver programowania liniowego (dwufazowa metoda sympleks, reguła Blanda) — bez zależności,
żeby działał także w przeglądarce (Pyodide) bez ładowania scipy. Przeznaczony do małych zadań
(np. model Mikhailova w rozmytym AHP)."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

EPS = 1e-10


class LPError(ValueError):
    pass


def _pivot(T: List[List[float]], basis: List[int], r: int, c: int) -> None:
    pv = T[r][c]
    T[r] = [x / pv for x in T[r]]
    for i in range(len(T)):
        if i != r and abs(T[i][c]) > 0:
            f = T[i][c]
            row = T[r]
            T[i] = [a - f * b for a, b in zip(T[i], row)]
    basis[r] = c


def _simplex(T: List[List[float]], basis: List[int], ncols: int, allowed: Sequence[bool]) -> None:
    """Maksymalizacja; ostatni wiersz T to wiersz celu w postaci (−c, wartość). Reguła Blanda."""
    m = len(T) - 1
    for _ in range(10000):
        col = next((j for j in range(ncols) if allowed[j] and T[m][j] < -EPS), None)
        if col is None:
            return
        best, row = None, None
        for i in range(m):
            if T[i][col] > EPS:
                ratio = T[i][-1] / T[i][col]
                if best is None or ratio < best - EPS or (abs(ratio - best) <= EPS and basis[i] < basis[row]):
                    best, row = ratio, i
        if row is None:
            raise LPError("Zadanie programowania liniowego jest nieograniczone")
        _pivot(T, basis, row, col)
    raise LPError("Przekroczono limit iteracji metody sympleks")


def linprog_max(c: Sequence[float], A_ub: Sequence[Sequence[float]] = (), b_ub: Sequence[float] = (),
                A_eq: Sequence[Sequence[float]] = (), b_eq: Sequence[float] = ()) -> Tuple[List[float], float]:
    """max cᵀx przy A_ub x ≤ b_ub, A_eq x = b_eq, x ≥ 0. Zwraca (x, wartość celu)."""
    n = len(c)
    rows: List[Tuple[List[float], float, str]] = []
    for a, b in zip(A_ub, b_ub):
        rows.append((list(map(float, a)), float(b), "le"))
    for a, b in zip(A_eq, b_eq):
        rows.append((list(map(float, a)), float(b), "eq"))
    # prawe strony nieujemne
    norm = []
    for a, b, kind in rows:
        if b < 0:
            a, b = [-x for x in a], -b
            kind = {"le": "ge", "eq": "eq"}[kind]
        norm.append((a, b, kind))
    m = len(norm)
    n_slack = sum(1 for _, _, k in norm if k in ("le", "ge"))
    n_art = sum(1 for _, _, k in norm if k in ("ge", "eq"))
    N = n + n_slack + n_art
    T: List[List[float]] = []
    basis: List[int] = []
    s_idx, a_idx = n, n + n_slack
    art_cols = []
    for a, b, kind in norm:
        row = a + [0.0] * (n_slack + n_art) + [b]
        if kind == "le":
            row[s_idx] = 1.0
            basis.append(s_idx)
            s_idx += 1
        elif kind == "ge":
            row[s_idx] = -1.0
            s_idx += 1
            row[a_idx] = 1.0
            basis.append(a_idx)
            art_cols.append(a_idx)
            a_idx += 1
        else:
            row[a_idx] = 1.0
            basis.append(a_idx)
            art_cols.append(a_idx)
            a_idx += 1
        T.append(row)
    # faza I: max −Σ sztucznych
    if art_cols:
        obj = [0.0] * (N + 1)
        for j in art_cols:
            obj[j] = 1.0
        for i in range(m):
            if basis[i] in art_cols:
                obj = [o - t for o, t in zip(obj, T[i])]
        T.append(obj)
        _simplex(T, basis, N, [True] * N)
        if T[m][-1] < -1e-8:
            raise LPError("Zadanie programowania liniowego jest sprzeczne")
        T.pop()
        # wyprowadzenie sztucznych z bazy (zdegenerowane)
        for i in range(m):
            if basis[i] in art_cols:
                col = next((j for j in range(n + n_slack) if abs(T[i][j]) > EPS), None)
                if col is not None:
                    _pivot(T, basis, i, col)
    allowed = [j < n + n_slack for j in range(N)]
    obj = [-float(x) for x in c] + [0.0] * (N - n) + [0.0]
    for i in range(m):
        if basis[i] < n and abs(obj[basis[i]]) > 0:
            f = obj[basis[i]]
            obj = [o - f * t for o, t in zip(obj, T[i])]
    T.append(obj)
    _simplex(T, basis, N, allowed)
    x = [0.0] * N
    for i in range(m):
        x[basis[i]] = T[i][-1]
    return x[:n], T[m][-1]
