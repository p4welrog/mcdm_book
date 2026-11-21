"""Metody addytywne (rozdz. 2): SAW, metoda scoringowa, FSAW, SMART, SMARTER."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from . import weights as W
from .fuzzy import TFN, tfn_sum
from .problem import Problem, ProblemError, crisp, crisp_matrix, ranking, ranks

# ---------------------------------------------------------------------------
# Normalizacja ocen (krok 1 metody SAW)
# ---------------------------------------------------------------------------

NORMALIZATIONS = {
    "ratio": "ilorazowa: f/max dla kryteriów zyskowych (2.1), min/f dla kosztowych (2.2); wymaga ocen dodatnich",
    "minmax": "unitaryzacja: (f − min)/(max − min) dla zyskowych (2.3), (max − f)/(max − min) dla kosztowych",
}


def normalize_column(col: Sequence[float], maximize: bool, how: str, name: str, notes: list) -> List[float]:
    lo, hi = min(col), max(col)
    if how == "ratio":
        if maximize:
            if lo < 0:
                raise ProblemError(f"Kryterium {name}: normalizacja ilorazowa wymaga ocen nieujemnych")
            if hi == 0:
                notes.append(f"Kryterium {name}: wszystkie oceny równe 0 — przyjęto r = 0.")
                return [0.0] * len(col)
            return [v / hi for v in col]
        if lo <= 0:
            raise ProblemError(f"Kryterium {name}: normalizacja ilorazowa kryterium kosztowego wymaga ocen dodatnich")
        return [lo / v for v in col]
    if how == "minmax":
        if hi == lo:
            notes.append(f"Kryterium {name}: wszystkie warianty mają tę samą ocenę — przyjęto r = 1 (kryterium nie różnicuje).")
            return [1.0] * len(col)
        if maximize:
            return [(v - lo) / (hi - lo) for v in col]
        return [(hi - v) / (hi - lo) for v in col]
    raise ProblemError(f"Nieznana normalizacja {how!r}; dostępne: {', '.join(NORMALIZATIONS)}")


def normalized_matrix(p: Problem, how: str, notes: list) -> List[List[float]]:
    X = crisp_matrix(p)
    cols = [normalize_column([r[k] for r in X], p.criteria[k].maximize, how, p.criteria[k].name, notes)
            for k in range(p.n)]
    return [[cols[k][i] for k in range(p.n)] for i in range(p.m)]


def _result(method: str, p: Problem, scores: List[float], label: str, steps: Dict[str, Any], notes: list,
            descending: bool = True) -> Dict[str, Any]:
    rk = ranks(scores, descending=descending)
    order = ranking(p.variants, scores, descending=descending)
    best = [v for v, r in zip(p.variants, rk) if r == 1]
    return {"method": method, "variants": p.variants, "criteria": [c.name for c in p.criteria],
            "scores": {"label": label, "values": scores, "better": "higher" if descending else "lower"},
            "ranks": rk, "ranking": order, "best": best, "steps": steps, "notes": notes}


# ---------------------------------------------------------------------------
# SAW (2.1)
# ---------------------------------------------------------------------------

def saw(p: Problem, normalization: str = "minmax") -> Dict[str, Any]:
    """Metoda sumy ważonej: p_i = Σ w_k r_ik (2.5)."""
    notes: list = []
    w = p.weights(notes=notes)
    R = normalized_matrix(p, normalization, notes)
    scores = [sum(wk * r for wk, r in zip(w, row)) for row in R]
    return _result("saw", p, scores, "p_i (użyteczność)",
                   {"normalization": normalization, "weights": w, "normalized": R}, notes)


# ---------------------------------------------------------------------------
# Metoda scoringowa (2.1)
# ---------------------------------------------------------------------------

def scoring(p: Problem) -> Dict[str, Any]:
    """Oceny w macierzy to punkty p_i^k przyznane przez decydenta; opcjonalnie criteria[k].max_points = P_k."""
    notes: list = []
    X = crisp_matrix(p)
    caps = [c.extra.get("max_points") for c in p.criteria]
    for k, cap in enumerate(caps):
        if cap is None:
            continue
        for i in range(p.m):
            if not (0 <= X[i][k] <= float(cap)):
                raise ProblemError(f"{p.variants[i]}/{p.criteria[k].name}: {X[i][k]:g} punktów poza zakresem 0–{cap}")
    if all(c is not None for c in caps):
        notes.append(f"Pula punktów P = {sum(float(c) for c in caps):g}.")
    w = [c.weight for c in p.criteria]
    if all(x is not None for x in w):
        scores = [sum(float(wk) * x for wk, x in zip(w, row)) for row in X]
        notes.append("Punkty ważone wagami kryteriów (bez normalizacji wag), jak ocena projektu w rozdz. 9.5.")
        return _result("scoring", p, scores, "ważona suma punktów", {"points": X, "max_points": caps, "weights": w}, notes)
    scores = [sum(row) for row in X]
    return _result("scoring", p, scores, "suma punktów", {"points": X, "max_points": caps}, notes)


# ---------------------------------------------------------------------------
# FSAW (2.2)
# ---------------------------------------------------------------------------

def fsaw(p: Problem, normalization: str = "ratio") -> Dict[str, Any]:
    """Rozmyta suma ważona: wagi trójkątne criteria[k].fuzzy_weight = [a, m, c]; defuzyfikacja CoA."""
    notes: list = []
    fw = []
    for c in p.criteria:
        if "fuzzy_weight" not in c.extra:
            raise ProblemError(f"Kryterium {c.name}: brak wagi rozmytej (pole \"fuzzy_weight\": [min, najlepsza, max])")
        fw.append(TFN.of(c.extra["fuzzy_weight"], f"Waga rozmyta {c.name}"))
    sm = sum(t.m for t in fw)
    if abs(sm - 1) > 1e-6:
        notes.append(f"Suma najodpowiedniejszych wartości wag m_k wynosi {sm:g} (metoda zakłada 1).")
    R = normalized_matrix(p, normalization, notes)
    fuzzy = [tfn_sum(t.scale(r) for t, r in zip(fw, row)) for row in R]
    scores = [t.coa() for t in fuzzy]
    return _result("fsaw", p, scores, "p_i^CoA (użyteczność zdefuzyfikowana)",
                   {"normalization": normalization, "fuzzy_weights": [t.as_list() for t in fw], "normalized": R,
                    "fuzzy_scores": [t.as_list() for t in fuzzy]}, notes)


# ---------------------------------------------------------------------------
# SMART / SMARTER (2.3–2.4)
# ---------------------------------------------------------------------------

def _solve3(A, b):
    """Rozwiązanie układu 3×3 (eliminacja Gaussa z wyborem elementu głównego)."""
    M = [list(A[i]) + [b[i]] for i in range(3)]
    for c in range(3):
        piv = max(range(c, 3), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            raise ProblemError("Funkcja wartości: punkty nie wyznaczają paraboli (za mało różnych wartości)")
        M[c], M[piv] = M[piv], M[c]
        for r in range(3):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][3] / M[i][i] for i in range(3)]


def quadratic_fit(points: Sequence[Sequence[float]]) -> List[float]:
    """Parabola MNK y = a x² + b x + c (jak linia trendu wielomianowa st. 2 w Excelu, przykłady 2.5, 2.7)."""
    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    S = lambda e: sum(x ** e for x in xs)
    T = lambda e: sum(y * x ** e for x, y in zip(xs, ys))
    a, b, c = _solve3([[S(4), S(3), S(2)], [S(3), S(2), S(1)], [S(2), S(1), len(xs)]], [T(2), T(1), T(0)])
    return [a, b, c]


def value_function(points: Sequence[Sequence[float]], x: float, interpolation: str = "piecewise",
                   name: str = "") -> float:
    """Ocena 0–100 z funkcji wartości zadanej punktami (x, ocena), np. z metody równego podziału (bisekcji)."""
    pts = sorted((float(a), float(b)) for a, b in points)
    if len(pts) < 2:
        raise ProblemError(f"Kryterium {name}: funkcja wartości wymaga co najmniej 2 punktów")
    if interpolation == "quadratic":
        a, b, c = quadratic_fit(pts)
        return a * x * x + b * x + c
    if interpolation != "piecewise":
        raise ProblemError("Interpolacja funkcji wartości: \"piecewise\" albo \"quadratic\"")
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


SCALES = {
    "linear": "liniowa funkcja wartości między najgorszą (0) a najlepszą (100) wartością; domyślnie min i max z danych (2.8–2.9)",
    "direct": "ocena bezpośrednia: w macierzy są już oceny 0–100 nadane przez decydenta",
    "value_function": "funkcja wartości zadana punktami [[x, ocena], ...] (np. bisekcja), interpolacja \"piecewise\" lub \"quadratic\"",
}


def scores_0_100(p: Problem, notes: list, *, allowed=("linear", "direct", "value_function")) -> (List[List[float]], list):
    """Macierz ocen u_ik w skali 0–100 według criteria[k].scale."""
    U = [[0.0] * p.n for _ in range(p.m)]
    used = []
    for k, c in enumerate(p.criteria):
        sc = c.extra.get("scale") or {"type": "linear"}
        if isinstance(sc, str):
            sc = {"type": sc}
        t = sc.get("type", "linear")
        if t not in allowed:
            raise ProblemError(f"Kryterium {c.name}: sposób oceny {t!r} niedostępny w tej metodzie ({', '.join(allowed)})")
        col = [crisp(v, f"{p.variants[i]}/{c.name}") for i, v in enumerate(p.column(k))]
        if t == "direct":
            for i, v in enumerate(col):
                if not (0 <= v <= 100):
                    raise ProblemError(f"{p.variants[i]}/{c.name}: ocena bezpośrednia {v:g} spoza skali 0–100")
            u = col
            used.append({"criterion": c.name, "type": t})
        elif t == "linear":
            worst = sc.get("worst", min(col) if c.maximize else max(col))
            best = sc.get("best", max(col) if c.maximize else min(col))
            worst, best = float(worst), float(best)
            if best == worst:
                notes.append(f"Kryterium {c.name}: najlepsza i najgorsza wartość są równe — przyjęto ocenę 100.")
                u = [100.0] * p.m
            else:
                u = [(v - worst) / (best - worst) * 100 for v in col]
                if any(x < -1e-9 or x > 100 + 1e-9 for x in u):
                    notes.append(f"Kryterium {c.name}: część ocen wypada poza skalę 0–100 (wartości spoza przedziału [{worst:g}; {best:g}]).")
            used.append({"criterion": c.name, "type": t, "worst": worst, "best": best})
        else:
            pts = sc.get("points")
            if not pts:
                raise ProblemError(f"Kryterium {c.name}: funkcja wartości wymaga punktów \"points\"")
            interp = sc.get("interpolation", "piecewise")
            u = [value_function(pts, v, interp, c.name) for v in col]
            info = {"criterion": c.name, "type": t, "points": pts, "interpolation": interp}
            if interp == "quadratic":
                info["coefficients"] = quadratic_fit(pts)
            used.append(info)
        for i in range(p.m):
            U[i][k] = u[i]
    return U, used


def _smart_weights(p: Problem, how: Optional[str], default: str, notes: list) -> (List[float], str):
    have = {"swing": all("swing" in c.extra for c in p.criteria),
            "given": all(c.weight is not None for c in p.criteria),
            "rank": all("rank" in c.extra for c in p.criteria)}
    if how in (None, "auto"):
        order = [("swing", "swing"), ("given", "given"), ("roc", "rank")] if default == "swing" else \
                [(default, "rank"), ("given", "given"), ("swing", "swing")]
        how = next((h for h, key in order if have[key]), None)
        if how is None:
            raise ProblemError("Brak danych do wag: podaj \"swing\" (punkty 0–100), \"weight\" albo \"rank\" dla każdego kryterium")
    if how == "swing":
        if not have["swing"]:
            raise ProblemError("Wagi rozpiętości wymagają pola \"swing\" (0–100) dla każdego kryterium")
        return W.swing([float(c.extra["swing"]) for c in p.criteria]), how
    if how == "given":
        return p.weights(notes=notes), how
    if how in ("roc", "rank_sum"):
        if not have["rank"]:
            raise ProblemError("Wagi z rang wymagają pola \"rank\" (1 = najważniejsze) dla każdego kryterium")
        return W.from_ranks([int(c.extra["rank"]) for c in p.criteria], how), how
    raise ProblemError("Wagi: \"swing\", \"given\", \"roc\" albo \"rank_sum\"")


def smart(p: Problem, weights: Optional[str] = None) -> Dict[str, Any]:
    """SMART: oceny 0–100 (criteria[k].scale) i wagi rozpiętości; U(a^i) = Σ w_k u_ik (2.10)."""
    notes: list = []
    U, scales = scores_0_100(p, notes)
    w, how = _smart_weights(p, weights, "swing", notes)
    scores = [sum(wk * u for wk, u in zip(w, row)) for row in U]
    return _result("smart", p, scores, "U(a^i) (użyteczność globalna)",
                   {"scales": scales, "weights_method": how, "weights": w, "scores_0_100": U}, notes)


def smarter(p: Problem, weights: Optional[str] = None) -> Dict[str, Any]:
    """SMARTER: liniowe funkcje wartości (lub ocena bezpośrednia) i wagi z rang — ROC (2.11) albo suma rang (2.12)."""
    notes: list = []
    U, scales = scores_0_100(p, notes, allowed=("linear", "direct"))
    w, how = _smart_weights(p, weights, "roc", notes)
    scores = [sum(wk * u for wk, u in zip(w, row)) for row in U]
    return _result("smarter", p, scores, "U(a^i) (użyteczność globalna)",
                   {"scales": scales, "weights_method": how, "weights": w, "scores_0_100": U}, notes)
