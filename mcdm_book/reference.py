"""Metody wykorzystujące punkty referencyjne (rozdz. 7.1–7.3): TOPSIS, rozmyty TOPSIS, VIKOR."""
from __future__ import annotations

from math import sqrt
from typing import Any, Dict, List, Optional, Sequence

from .additive import _result
from .fuzzy import TFN, distance
from .problem import Problem, ProblemError, crisp, crisp_matrix, ranking, ranks


# ---------------------------------------------------------------------------
# TOPSIS (7.1)
# ---------------------------------------------------------------------------

def topsis(p: Problem, metric: float = 2) -> Dict[str, Any]:
    """TOPSIS: normalizacja wektorowa, macierz ważona (7.1), rozwiązania idealne (7.2)–(7.3),
    odległości w metryce Minkowskiego rzędu `metric` (7.4)–(7.5), S_j = d⁻/(d⁺ + d⁻) (7.6)."""
    notes: list = []
    w = p.weights(notes=notes)
    X = crisp_matrix(p)
    if metric < 1:
        raise ProblemError("Rząd metryki p musi być ≥ 1")
    N = [[0.0] * p.n for _ in range(p.m)]
    for k in range(p.n):
        norm = sqrt(sum(X[i][k] ** 2 for i in range(p.m)))
        if norm == 0:
            notes.append(f"Kryterium {p.criteria[k].name}: wszystkie oceny równe 0 — kolumna znormalizowana do 0.")
        for i in range(p.m):
            N[i][k] = X[i][k] / norm if norm else 0.0
    V = [[w[k] * N[i][k] for k in range(p.n)] for i in range(p.m)]
    col = lambda k: [V[i][k] for i in range(p.m)]
    vplus = [max(col(k)) if c.maximize else min(col(k)) for k, c in enumerate(p.criteria)]
    vminus = [min(col(k)) if c.maximize else max(col(k)) for k, c in enumerate(p.criteria)]

    def dist(row, ref):
        if metric == float("inf"):
            return max(abs(a - b) for a, b in zip(row, ref))
        return sum(abs(a - b) ** metric for a, b in zip(row, ref)) ** (1 / metric)

    dp = [dist(V[i], vplus) for i in range(p.m)]
    dm = [dist(V[i], vminus) for i in range(p.m)]
    S = []
    for i in range(p.m):
        s = dp[i] + dm[i]
        S.append(dm[i] / s if s > 0 else 0.0)
    return _result("topsis", p, S, "S_j (bliskość względna rozwiązania idealnego)",
                   {"weights": w, "normalized": N, "weighted": V, "ideal": vplus, "anti_ideal": vminus,
                    "d_plus": dp, "d_minus": dm, "metric": metric}, notes)


# ---------------------------------------------------------------------------
# Rozmyty TOPSIS (7.2)
# ---------------------------------------------------------------------------

COST_NORMS = {
    "min_l": "kryteria kosztowe: (min l / u, min l / m, min l / l) — jak w rozdz. 14 i u Chena (2000)",
    "min_u": "kryteria kosztowe: (min u / u, min u / m, min u / l) — wzór (7.10) w brzmieniu z druku",
}


def fuzzy_topsis(p: Problem, cost_norm: str = "min_l", reference: Optional[Dict[str, Sequence]] = None) -> Dict[str, Any]:
    """Rozmyty TOPSIS: oceny [l, m, u] > 0; normalizacja (7.9)–(7.10), macierz ważona (7.11),
    rozwiązania idealne po składowych (7.12)–(7.13), odległość wierzchołkowa, S_j (7.16).

    reference = {"ideal": [...], "anti_ideal": [...]} — własne punkty odniesienia (np. poziomy aspiracji
    i rezerwacji, rozdz. 14), oceny jak w wierszu macierzy; biorą udział w normalizacji."""
    notes: list = []
    w = p.weights(notes=notes)
    if cost_norm not in COST_NORMS:
        raise ProblemError(f"cost_norm: {', '.join(COST_NORMS)}")
    rows = [[TFN.of(v, f"{p.variants[i]}/{p.criteria[k].name}") for k, v in enumerate(row)]
            for i, row in enumerate(p.values)]
    refs = {}
    if reference:
        for key in ("ideal", "anti_ideal"):
            if key not in reference:
                raise ProblemError("reference wymaga obu pól: \"ideal\" i \"anti_ideal\"")
            r = reference[key]
            if len(r) != p.n:
                raise ProblemError(f"reference.{key}: {len(r)} ocen, a kryteriów jest {p.n}")
            refs[key] = [TFN.of(v, f"{key}/{p.criteria[k].name}") for k, v in enumerate(r)]
    allrows = rows + [refs[k] for k in ("ideal", "anti_ideal") if k in refs]
    for row in allrows:
        for t in row:
            if t.l < 0:
                raise ProblemError("Rozmyty TOPSIS wymaga ocen nieujemnych")
    Z_all = []
    for k, c in enumerate(p.criteria):
        colk = [r[k] for r in allrows]
        if c.maximize:
            mu = max(t.u for t in colk)
            Z_all.append([TFN(t.l / mu, t.m / mu, t.u / mu) for t in colk])
        else:
            base = min(t.l for t in colk) if cost_norm == "min_l" else min(t.u for t in colk)
            if any(t.l <= 0 for t in colk):
                raise ProblemError(f"Kryterium kosztowe {c.name}: normalizacja wymaga l > 0")
            Z_all.append([TFN(base / t.u, base / t.m, base / t.l) for t in colk])
    nrows = len(allrows)
    Z = [[Z_all[k][i] for k in range(p.n)] for i in range(nrows)]
    Vall = [[Z[i][k].scale(w[k]) for k in range(p.n)] for i in range(nrows)]
    V = Vall[:p.m]
    if refs:
        vplus, vminus = Vall[p.m], Vall[p.m + 1]
        notes.append("Rozwiązania idealne zadane przez użytkownika (np. poziomy aspiracji i rezerwacji).")
    else:
        vplus = [TFN(max(V[i][k].l for i in range(p.m)), max(V[i][k].m for i in range(p.m)),
                     max(V[i][k].u for i in range(p.m))) for k in range(p.n)]
        vminus = [TFN(min(V[i][k].l for i in range(p.m)), min(V[i][k].m for i in range(p.m)),
                      min(V[i][k].u for i in range(p.m))) for k in range(p.n)]
    dpk = [[distance(V[i][k], vplus[k]) for k in range(p.n)] for i in range(p.m)]
    dmk = [[distance(V[i][k], vminus[k]) for k in range(p.n)] for i in range(p.m)]
    dp = [sum(r) for r in dpk]
    dm = [sum(r) for r in dmk]
    S = [dm[i] / (dp[i] + dm[i]) if dp[i] + dm[i] > 0 else 0.0 for i in range(p.m)]
    L = lambda M: [[t.as_list() for t in row] for row in M]
    return _result("fuzzy_topsis", p, S, "S_j (bliskość względna rozwiązania idealnego)",
                   {"weights": w, "cost_norm": cost_norm, "normalized": L(Z[:p.m]), "weighted": L(V),
                    "ideal": [t.as_list() for t in vplus], "anti_ideal": [t.as_list() for t in vminus],
                    "d_plus_by_criterion": dpk, "d_minus_by_criterion": dmk, "d_plus": dp, "d_minus": dm}, notes)


# ---------------------------------------------------------------------------
# VIKOR (7.3)
# ---------------------------------------------------------------------------

def vikor(p: Problem, q: float = 0.5, ideal: Optional[Sequence[float]] = None,
          anti_ideal: Optional[Sequence[float]] = None, w2: str = "both") -> Dict[str, Any]:
    """VIKOR: S_i (7.19), R_i (7.20), Q_i (7.22); rankingi rosnąco; warunki W1 (7.23) i W2; rozwiązanie
    kompromisowe według Opricovic, Tzeng (2004). ideal/anti_ideal — własne f* i f_* (domyślnie najlepsze
    i najgorsze oceny wariantów, (7.17)–(7.18), z uwzględnieniem kierunku kryterium).
    w2 = "both": a' najlepszy w rankingu S i R (jak w książce); "either": w S lub R (Opricovic, Tzeng)."""
    notes: list = []
    if not 0 <= q <= 1:
        raise ProblemError("Współczynnik q musi należeć do [0; 1]")
    if p.m < 2:
        raise ProblemError("VIKOR wymaga co najmniej 2 wariantów")
    w = p.weights(notes=notes)
    X = crisp_matrix(p)
    fstar = [float(x) for x in ideal] if ideal is not None else \
        [max(r[k] for r in X) if c.maximize else min(r[k] for r in X) for k, c in enumerate(p.criteria)]
    fmin = [float(x) for x in anti_ideal] if anti_ideal is not None else \
        [min(r[k] for r in X) if c.maximize else max(r[k] for r in X) for k, c in enumerate(p.criteria)]
    if len(fstar) != p.n or len(fmin) != p.n:
        raise ProblemError("ideal i anti_ideal muszą mieć po jednej wartości na kryterium")
    r = [[0.0] * p.n for _ in range(p.m)]
    for k in range(p.n):
        span = abs(fstar[k] - fmin[k])
        if span == 0:
            notes.append(f"Kryterium {p.criteria[k].name}: f* = f_* — odległości przyjęto równe 0.")
        for i in range(p.m):
            r[i][k] = abs(fstar[k] - X[i][k]) / span if span else 0.0
    S = [sum(w[k] * r[i][k] for k in range(p.n)) for i in range(p.m)]
    R = [max(w[k] * r[i][k] for k in range(p.n)) for i in range(p.m)]
    Ss, Sm, Rs, Rm = min(S), max(S), min(R), max(R)
    Q = [(q * (S[i] - Ss) / (Sm - Ss) if Sm > Ss else 0.0) + ((1 - q) * (R[i] - Rs) / (Rm - Rs) if Rm > Rs else 0.0)
         for i in range(p.m)]
    tol = 1e-12
    order_Q = sorted(range(p.m), key=lambda i: (Q[i], i))
    a1, a2 = order_Q[0], order_Q[1]
    DQ = 1 / (p.m - 1)
    W1 = Q[a2] - Q[a1] >= DQ - tol
    best_S = S[a1] <= Ss + tol
    best_R = R[a1] <= Rs + tol
    if w2 not in ("both", "either"):
        raise ProblemError("w2: \"both\" albo \"either\"")
    W2 = (best_S and best_R) if w2 == "both" else (best_S or best_R)
    if W1 and W2:
        comp, rule = [a1], "W1 i W2 spełnione: rozwiązaniem kompromisowym jest a′."
    elif not W1:
        comp = [i for i in order_Q if Q[i] - Q[a1] < DQ - tol]
        rule = ("W1 niespełniony: rozwiązania kompromisowe a′, …, a⁽ᴹ⁾ — wszystkie warianty z Q − Q(a′) < DQ "
                "(Opricovic, Tzeng 2004).")
    else:
        comp, rule = [a1, a2], "Spełniony tylko W1 (W2 nie): rozwiązania kompromisowe a′ i a″ (Opricovic, Tzeng 2004)."
    notes.append("Reguła wyboru w kroku 6 według Opricovic, Tzeng (2004); w książce wyliczenie przypadków jest "
                 "niekompletne (brak przypadku „tylko W1”).")
    res = _result("vikor", p, Q, "Q_i (im mniej, tym lepiej)", {}, notes, descending=False)
    res["best"] = [p.variants[i] for i in comp]
    res["steps"] = {"weights": w, "f_star": fstar, "f_minus": fmin, "r": r, "S": S, "R": R, "Q": Q, "q": q,
                    "ranking_S": ranking(p.variants, S, descending=False),
                    "ranking_R": ranking(p.variants, R, descending=False),
                    "ranking_Q": [p.variants[i] for i in order_Q],
                    "DQ": DQ, "W1": W1, "W2": W2, "w2_rule": w2, "compromise_rule": rule,
                    "ranks_S": ranks(S, descending=False), "ranks_R": ranks(R, descending=False)}
    return res
