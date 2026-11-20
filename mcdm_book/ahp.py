"""Metoda AHP i metody pokrewne (rozdz. 3.1–3.3): AHP, REMBRANDT, rozmyty AHP w ujęciu Mikhailova.

Zadanie (oprócz pól wspólnych):
  "criteria_comparisons": macierz n×n porównań kryteriów,
  "comparisons": {"nazwa kryterium": macierz m×m porównań wariantów, ...}.
Kryterium bez macierzy porównań może mieć oceny liczbowe w "values" — wektor skali to wtedy oceny
znormalizowane do sumy 1 (dla kryteriów minimalizowanych: odwrotności ocen), jak w przykładzie 3.4.

Elementy macierzy: liczby, napisy "1/7", null (uzupełniane odwrotnością elementu symetrycznego).
REMBRANDT: oceny δ ∈ {−8, …, 8} (tabl. 3.3), null uzupełniane przez −δ.
Rozmyty AHP: trójki [l, m, u] (liczba x → (x, x, x)), null uzupełniane przez (1/u, 1/m, 1/l) (3.33).
"""
from __future__ import annotations

from fractions import Fraction
from math import exp, log, sqrt
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .additive import _result
from .fuzzy import TFN
from .lp import LPError, linprog_max
from .problem import Problem, ProblemError, crisp

# Tablica 3.1 (Saaty 1980); dla m = 11–15 wartości z tej samej pracy (spoza książki)
RANDOM_INDEX = {3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
                11: 1.51, 12: 1.48, 13: 1.56, 14: 1.57, 15: 1.59}

SAATY_SCALE = {1: "równoważne", 2: "wahanie: równoważność — niewielka przewaga", 3: "niewielka przewaga",
               4: "wahanie: niewielka — duża przewaga", 5: "duża przewaga",
               6: "wahanie: duża — istotnie większa przewaga", 7: "istotnie większa przewaga",
               8: "wahanie: istotnie większa — ogromna przewaga", 9: "ogromna przewaga"}
CHANG_SCALE = {"równoważne": (1, 1, 1), "umiarkowanie ważniejsze": (1, 3, 5), "silnie ważniejsze": (3, 5, 7),
               "bardzo silnie ważniejsze": (5, 7, 9), "ekstremalnie ważniejsze": (7, 9, 9)}

PRIORITY_METHODS = {
    "eigen": "wektor własny dla λmax (metoda potęgowa do zbieżności, tw. 3.4, 3.8)",
    "saaty": "metoda Saaty'ego: średnie wierszy macierzy znormalizowanej kolumnami (3.16)–(3.18)",
    "power": "metoda potęgowa z dokładnością eps (3.20)–(3.23); domyślnie eps = 0,001 jak w przykładzie 3.3",
    "geometric": "średnie geometryczne wierszy (metoda logarytmicznych najmniejszych kwadratów)",
}


# ---------------------------------------------------------------------------
# Macierze porównań
# ---------------------------------------------------------------------------

def _num(v: Any, where: str) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        try:
            return float(Fraction(s))
        except (ValueError, ZeroDivisionError):
            raise ProblemError(f"{where}: niepoprawna wartość {v!r}") from None
    return crisp(v, where)


def reciprocal_matrix(M: Sequence[Sequence[Any]], size: int, name: str, notes: list) -> List[List[float]]:
    """Macierz proporcjonalna (3.4): braki uzupełniane odwrotnościami; pełna macierz używana bez zmian
    (niezgodność z α_ij = 1/α_ji zgłaszana w uwagach)."""
    if len(M) != size or any(len(r) != size for r in M):
        raise ProblemError(f"{name}: macierz porównań musi mieć wymiar {size}×{size}")
    A = [[_num(M[i][j], f"{name} [{i + 1},{j + 1}]") for j in range(size)] for i in range(size)]
    for i in range(size):
        if A[i][i] is None:
            A[i][i] = 1.0
        for j in range(size):
            if A[i][j] is None:
                if A[j][i] is None:
                    raise ProblemError(f"{name}: brak porównania elementów {i + 1} i {j + 1}")
                A[i][j] = 1 / A[j][i]
            if A[i][j] <= 0:
                raise ProblemError(f"{name}: oceny porównań muszą być dodatnie")
    bad = [(i + 1, j + 1) for i in range(size) for j in range(i + 1, size) if abs(A[i][j] * A[j][i] - 1) > 1e-6]
    if any(abs(A[i][i] - 1) > 1e-9 for i in range(size)):
        notes.append(f"{name}: na przekątnej są wartości różne od 1.")
    if bad:
        notes.append(f"{name}: macierz nie jest proporcjonalna (α_ij ≠ 1/α_ji dla par {bad}); użyto jej bez zmian.")
    return A


def _matvec(A, w):
    return [sum(a * x for a, x in zip(row, w)) for row in A]


def priority_vector(A: List[List[float]], method: str = "eigen", eps: Optional[float] = None) -> Dict[str, Any]:
    """Wektor skali (sumujący się do 1) i λmax."""
    m = len(A)
    if method == "saaty":
        sig = [sum(A[i][j] for i in range(m)) for j in range(m)]
        B = [[A[i][j] / sig[j] for j in range(m)] for i in range(m)]
        w = [sum(B[i]) / m for i in range(m)]
        Aw = _matvec(A, w)
        lam = sum(Aw[i] / w[i] for i in range(m)) / m      # (3.19) z (A·ω)_i — zob. errata do s. 56
        return {"w": w, "lambda_max": lam, "column_sums": sig}
    if method == "geometric":
        g = [exp(sum(log(x) for x in row) / m) for row in A]
        s = sum(g)
        w = [x / s for x in g]
        Aw = _matvec(A, w)
        return {"w": w, "lambda_max": sum(Aw[i] / w[i] for i in range(m)) / m}
    if method in ("eigen", "power"):
        tol = eps if eps is not None else (1e-3 if method == "power" else 1e-12)
        w = [1 / m] * m
        lam, it = float(m), 0
        for it in range(1, 10001):
            z = _matvec(A, w)
            lam = sum(z)                                    # (3.22): Σ z_i → λmax, bo Σ w = 1
            new = [x / lam for x in z]
            diff = max(abs(a - b) for a, b in zip(new, w))
            w = new
            if diff < tol:
                break
        return {"w": w, "lambda_max": lam, "iterations": it, "eps": tol}
    raise ProblemError(f"Nieznana metoda wektora skali {method!r}; dostępne: {', '.join(PRIORITY_METHODS)}")


def consistency(lam: float, m: int, notes: Optional[list] = None, name: str = "") -> Dict[str, Any]:
    """Miara zgodności μ (3.13) i zmodyfikowana miara γ (3.14) z r z tabl. 3.1; zgodność, gdy γ ≤ 0,1."""
    if m <= 2:
        return {"mu": 0.0, "gamma": 0.0, "r": None, "consistent": True}
    mu = (lam - m) / (m - 1)
    r = RANDOM_INDEX.get(m)
    if r is None:
        r = RANDOM_INDEX[15]
        if notes is not None:
            notes.append(f"{name}: brak wartości r dla m = {m}; przyjęto r = {r}.")
    elif m > 10 and notes is not None:
        notes.append(f"{name}: r = {r} dla m = {m} spoza tablicy 3.1 (Saaty 1980).")
    gamma = mu / r
    if gamma > 0.1 and notes is not None:
        notes.append(f"{name}: γ = {gamma:.3f} > 0,1 — oceny niezgodne, zaleca się ponowne porównania parami.")
    return {"mu": mu, "gamma": gamma, "r": r, "consistent": gamma <= 0.1}


def _values_vector(p: Problem, k: int, notes: list) -> List[float]:
    c = p.criteria[k]
    col = [crisp(v, f"{p.variants[i]}/{c.name}") for i, v in enumerate(p.column(k))]
    if any(v <= 0 for v in col):
        raise ProblemError(f"Kryterium {c.name}: wektor skali z ocen wymaga ocen dodatnich")
    if not c.maximize:
        col = [1 / v for v in col]
        notes.append(f"Kryterium {c.name} (min): wektor skali z odwrotności ocen, znormalizowany do sumy 1.")
    s = sum(col)
    return [v / s for v in col]


def _comparisons(p: Problem) -> Tuple[Any, Dict[str, Any]]:
    cc = p.extra.get("criteria_comparisons")
    comp = p.extra.get("comparisons") or {}
    if not isinstance(comp, dict):
        raise ProblemError("\"comparisons\" musi być słownikiem {nazwa kryterium: macierz}")
    names = {c.name for c in p.criteria}
    unknown = set(comp) - names
    if unknown:
        raise ProblemError(f"\"comparisons\": nieznane kryteria {sorted(unknown)}")
    return cc, comp


# ---------------------------------------------------------------------------
# AHP (3.1)
# ---------------------------------------------------------------------------

def ahp(p: Problem, method: str = "eigen", eps: Optional[float] = None) -> Dict[str, Any]:
    """AHP: wektor skali kryteriów c̄ (3.24), wektory skali wariantów c_k (3.25), c = C c̄ (3.27).
    Bez "criteria_comparisons" używane są wagi kryteriów (weight)."""
    notes: list = []
    cc, comp = _comparisons(p)
    matrices = []
    if cc is not None:
        A = reciprocal_matrix(cc, p.n, "Porównania kryteriów", notes)
        pr = priority_vector(A, method, eps)
        cons = consistency(pr["lambda_max"], p.n, notes, "Porównania kryteriów")
        cbar = pr["w"]
        matrices.append({"name": "kryteria", "matrix": A, **pr, **cons})
    else:
        cbar = p.weights(notes=notes)
        notes.append("Brak macierzy porównań kryteriów — użyto podanych wag.")
    cols = []
    for k, c in enumerate(p.criteria):
        if c.name in comp:
            A = reciprocal_matrix(comp[c.name], p.m, f"Kryterium {c.name}", notes)
            pr = priority_vector(A, method, eps)
            cons = consistency(pr["lambda_max"], p.m, notes, f"Kryterium {c.name}")
            cols.append(pr["w"])
            matrices.append({"name": c.name, "matrix": A, **pr, **cons})
        else:
            cols.append(_values_vector(p, k, notes))
            matrices.append({"name": c.name, "from_values": True, "w": cols[-1]})
    C = [[cols[k][i] for k in range(p.n)] for i in range(p.m)]
    c = [sum(C[i][k] * cbar[k] for k in range(p.n)) for i in range(p.m)]
    return _result("ahp", p, c, "c (końcowy wektor skali)",
                   {"method": method, "criteria_weights": cbar, "C": C, "matrices": matrices}, notes)


# ---------------------------------------------------------------------------
# REMBRANDT (3.2)
# ---------------------------------------------------------------------------

def delta_matrix(M: Sequence[Sequence[Any]], size: int, name: str, notes: list) -> List[List[float]]:
    if len(M) != size or any(len(r) != size for r in M):
        raise ProblemError(f"{name}: macierz porównań musi mieć wymiar {size}×{size}")
    D = [[_num(M[i][j], f"{name} [{i + 1},{j + 1}]") for j in range(size)] for i in range(size)]
    diag = False
    for i in range(size):
        if D[i][i] not in (None, 0.0):
            diag = True
        D[i][i] = 0.0
        for j in range(size):
            if D[i][j] is None:
                if D[j][i] is None:
                    raise ProblemError(f"{name}: brak porównania elementów {i + 1} i {j + 1}")
                D[i][j] = -D[j][i]
    if diag:
        notes.append(f"{name}: na przekątnej przyjęto δ_ii = 0.")
    bad = [(i + 1, j + 1) for i in range(size) for j in range(i + 1, size) if abs(D[i][j] + D[j][i]) > 1e-9]
    if bad:
        notes.append(f"{name}: macierz nie jest antysymetryczna (δ_ij ≠ −δ_ji dla par {bad}); użyto jej bez zmian.")
    if any(abs(x) > 8 for row in D for x in row):
        notes.append(f"{name}: oceny δ spoza skali −8…8 (tabl. 3.3).")
    return D


def _rembrandt_vector(D: List[List[float]], gamma: float) -> Dict[str, Any]:
    z = len(D)
    R = [[exp(gamma * d) for d in row] for row in D]               # (3.28)
    v = [exp(gamma * sum(row) / z) for row in D]                   # (3.30), Π v = 1
    s = sum(v)
    return {"r": R, "v": v, "w": [x / s for x in v]}


def rembrandt(p: Problem, gamma_criteria: float = log(sqrt(2)), gamma_variants: float = log(2)) -> Dict[str, Any]:
    """REMBRANDT: oceny δ_ij (tabl. 3.3), r_ij = exp(γ δ_ij) (3.28), wektory skali ze średnich geometrycznych
    (3.30), wagi kryteriów normalizowane addytywnie, c_i = Π_k (c_k^i)^{c̄_k} (3.31), normalizacja do sumy 1."""
    notes: list = []
    cc, comp = _comparisons(p)
    steps: Dict[str, Any] = {"gamma_criteria": gamma_criteria, "gamma_variants": gamma_variants}
    if cc is not None:
        D = delta_matrix(cc, p.n, "Porównania kryteriów", notes)
        rc = _rembrandt_vector(D, gamma_criteria)
        cbar = rc["w"]
        steps["criteria"] = {"delta": D, **rc}
    else:
        cbar = p.weights(notes=notes)
        notes.append("Brak macierzy porównań kryteriów — użyto podanych wag.")
    cols, per = [], []
    for k, c in enumerate(p.criteria):
        if c.name not in comp:
            raise ProblemError(f"REMBRANDT: brak macierzy porównań wariantów dla kryterium {c.name}")
        D = delta_matrix(comp[c.name], p.m, f"Kryterium {c.name}", notes)
        rv = _rembrandt_vector(D, gamma_variants)
        cols.append(rv["w"])
        per.append({"name": c.name, "delta": D, **rv})
    C = [[cols[k][i] for k in range(p.n)] for i in range(p.m)]
    raw = [1.0] * p.m
    for i in range(p.m):
        for k in range(p.n):
            raw[i] *= C[i][k] ** cbar[k]
    s = sum(raw)
    c = [x / s for x in raw]
    steps.update(criteria_weights=cbar, C=C, matrices=per, product=raw)
    return _result("rembrandt", p, c, "c (wektor priorytetów, znormalizowany)", steps, notes)


# ---------------------------------------------------------------------------
# Rozmyty AHP w ujęciu Mikhailova (3.3)
# ---------------------------------------------------------------------------

def fuzzy_matrix(M: Sequence[Sequence[Any]], size: int, name: str, notes: list) -> List[List[TFN]]:
    if len(M) != size or any(len(r) != size for r in M):
        raise ProblemError(f"{name}: macierz porównań musi mieć wymiar {size}×{size}")
    F: List[List[Optional[TFN]]] = [[None] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            v = M[i][j]
            if v is None or v == "":
                continue
            if isinstance(v, str) and v.strip().lower() in CHANG_SCALE:
                F[i][j] = TFN(*map(float, CHANG_SCALE[v.strip().lower()]))
            elif isinstance(v, (list, tuple)):
                F[i][j] = TFN.of([_num(x, f"{name} [{i + 1},{j + 1}]") for x in v], f"{name} [{i + 1},{j + 1}]")
            else:
                x = _num(v, f"{name} [{i + 1},{j + 1}]")
                F[i][j] = TFN(x, x, x)
    for i in range(size):
        F[i][i] = TFN(1.0, 1.0, 1.0)
        for j in range(size):
            if F[i][j] is None:
                t = F[j][i]
                if t is None:
                    raise ProblemError(f"{name}: brak porównania elementów {i + 1} i {j + 1}")
                F[i][j] = TFN(1 / t.u, 1 / t.m, 1 / t.l)              # (3.33)
            if F[i][j].l <= 0:
                raise ProblemError(f"{name}: oceny porównań muszą być dodatnie")
    return F


def mikhailov(F: List[List[TFN]], alphas: Sequence[float], d: float) -> Dict[str, Any]:
    """Model (3.43) dla każdego α; wynik ważony α (3.44). Używane są porównania i < j."""
    m = len(F)
    if m == 1:
        return {"w": [1.0], "levels": [{"alpha": a, "w": [1.0], "lambda": 1.0, "R": [], "cuts": []} for a in alphas],
                "lambda_min": 1.0}
    per = []
    for a in alphas:
        rows, cut = [], []
        for i in range(m):
            for j in range(i + 1, m):
                lo = F[i][j].l + (F[i][j].m - F[i][j].l) * a            # (3.35)
                hi = F[i][j].u - (F[i][j].u - F[i][j].m) * a            # (3.36)
                r1 = [0.0] * m
                r1[i], r1[j] = 1.0, -hi                                  # ω_i − u ω_j ≲ 0
                r2 = [0.0] * m
                r2[i], r2[j] = -1.0, lo                                  # −ω_i + l ω_j ≲ 0
                rows += [r1, r2]
                cut.append({"pair": [i + 1, j + 1], "interval": [lo, hi]})
        # zmienne: ω_1..ω_m, λ⁺, λ⁻ (λ może być ujemne)
        A_ub = [r + [d, -d] for r in rows]
        b_ub = [d] * len(rows)
        A_eq = [[1.0] * m + [0.0, 0.0]]
        try:
            x, val = linprog_max([0.0] * m + [1.0, -1.0], A_ub, b_ub, A_eq, [1.0])
        except LPError as e:
            raise ProblemError(f"Model Mikhailova (α = {a:g}): {e}") from None
        per.append({"alpha": a, "w": x[:m], "lambda": x[m] - x[m + 1], "R": rows, "cuts": cut})
    sa = sum(alphas)
    if sa > 0:
        w = [sum(r["alpha"] * r["w"][i] for r in per) / sa for i in range(m)]
    else:
        w = [sum(r["w"][i] for r in per) / len(per) for i in range(m)]
    return {"w": w, "levels": per, "lambda_min": min(r["lambda"] for r in per)}


def fuzzy_ahp(p: Problem, alphas: Sequence[float] = (0, 0.2, 0.4, 0.6, 0.8, 1), d: float = 1.0) -> Dict[str, Any]:
    """Rozmyty AHP (Mikhailov): porównania [l, m, u], α-przekroje (3.34)–(3.36), model (3.43) dla każdego α,
    średnia ważona poziomami α (3.44); synteza c = C c̄ (3.27)."""
    notes: list = []
    alphas = [float(a) for a in alphas]
    if not alphas or any(not 0 <= a <= 1 for a in alphas):
        raise ProblemError("Poziomy α muszą należeć do [0; 1]")
    if d <= 0:
        raise ProblemError("Tolerancja d musi być dodatnia")
    cc, comp = _comparisons(p)
    mats = []
    if cc is not None:
        res = mikhailov(fuzzy_matrix(cc, p.n, "Porównania kryteriów", notes), alphas, d)
        cbar = res["w"]
        mats.append({"name": "kryteria", **res})
    else:
        cbar = p.weights(notes=notes)
        notes.append("Brak macierzy porównań kryteriów — użyto podanych wag.")
    cols = []
    for k, c in enumerate(p.criteria):
        if c.name in comp:
            res = mikhailov(fuzzy_matrix(comp[c.name], p.m, f"Kryterium {c.name}", notes), alphas, d)
            cols.append(res["w"])
            mats.append({"name": c.name, **res})
        else:
            cols.append(_values_vector(p, k, notes))
            mats.append({"name": c.name, "from_values": True, "w": cols[-1]})
    for mt in mats:
        if "lambda_min" in mt and mt["lambda_min"] < 0:
            notes.append(f"{mt['name']}: λ* < 0 — oceny całkowicie niezgodne na co najmniej jednym poziomie α.")
    C = [[cols[k][i] for k in range(p.n)] for i in range(p.m)]
    c = [sum(C[i][k] * cbar[k] for k in range(p.n)) for i in range(p.m)]
    return _result("fuzzy_ahp", p, c, "c (końcowy wektor skali)",
                   {"alphas": alphas, "d": d, "criteria_weights": cbar, "C": C, "matrices": mats}, notes)
