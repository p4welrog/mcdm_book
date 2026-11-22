"""Metody PROMETHEE i EXPROM (rozdz. 6).

Pola kryteriów (oprócz name, direction, weight):
  "type": 1–6     typ uogólnionego kryterium (tabl. 6.1; domyślnie 1),
  "q", "p", "s"   próg równoważności, próg preferencji, parametr kryterium gaussowskiego,
  "v"             próg weta (metody z progami weta),
  "L"             granica obszaru silnej preferencji w EXPROM (domyślnie wg typu, wzór 6.29).
Kryteria minimalizowane są odwracane (−f), więc wzory dotyczą kryteriów maksymalizowanych.

Wersje stochastyczne (6.6–6.7): każda ocena to rozkład {"values": [...], "probs": [...]} albo
{"obs": [...]}; progi mogą zależeć od wartości oczekiwanej: liczba albo [α, β] → α + β·μ_ik.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from .additive import _result
from .problem import Problem, ProblemError, crisp_matrix

TYPES = {1: "kryterium prawdziwe (6.4)", 2: "quasi-kryterium, q (6.5)", 3: "liniowa preferencja, p (6.6)",
         4: "kryterium poziomowe, q i p (6.7)", 5: "pseudo-kryterium, q i p (6.8)", 6: "gaussowskie, s (6.9)"}
VETO_DIRECTIONS = {"formula": "d_k(aⁱ, aʲ) z f_k(aʲ) − f_k(aⁱ), wzór (6.20)",
                   "example": "d_k z f_k(aⁱ) − f_k(aʲ), jak w przykładach 6.7 i 6.10 (wynik niezgodny z (6.20))"}
RISKS = {"DARA": "awersja do ryzyka: FSD, SSD, TSD", "INARA": "skłonność do ryzyka: FSD, SISD, TISD1, TISD2"}
_TOL = 1e-9


# ---------------------------------------------------------------------------
# Uogólnione kryteria (tabl. 6.1)
# ---------------------------------------------------------------------------

def _num(c, key, required=False, default=None):
    v = c.extra.get(key, default)
    if v is None:
        if required:
            raise ProblemError(f"Kryterium {c.name}: brak parametru {key!r}")
        return None
    try:
        return float(str(v).replace(",", ".")) if not isinstance(v, (int, float)) else float(v)
    except ValueError:
        raise ProblemError(f"Kryterium {c.name}: niepoprawna wartość {key} = {v!r}")


def preference_function(c) -> Dict[str, Any]:
    """Parametry uogólnionego kryterium i funkcja G(d)."""
    t = c.extra.get("type", 1)
    try:
        t = int(t)
    except (TypeError, ValueError):
        raise ProblemError(f"Kryterium {c.name}: typ uogólnionego kryterium 1–6, jest {t!r}")
    if t not in TYPES:
        raise ProblemError(f"Kryterium {c.name}: typ uogólnionego kryterium 1–6, jest {t}")
    q = _num(c, "q", t in (2, 4, 5), 0.0 if t not in (2, 4, 5) else None)
    p = _num(c, "p", t in (3, 4, 5))
    s = _num(c, "s", t == 6)
    if t in (4, 5) and not p > q:
        raise ProblemError(f"Kryterium {c.name}: wymagane p > q (p = {p}, q = {q})")
    if t == 3 and not p > 0:
        raise ProblemError(f"Kryterium {c.name}: wymagane p > 0")
    if t == 6 and not s > 0:
        raise ProblemError(f"Kryterium {c.name}: wymagane s > 0")
    if q is not None and q < 0:
        raise ProblemError(f"Kryterium {c.name}: próg q nie może być ujemny")

    def G(d: float) -> float:
        if t == 1:
            return 1.0 if d > 0 else 0.0
        if t == 2:
            return 1.0 if d > q else 0.0
        if t == 3:
            return 0.0 if d <= 0 else (d / p if d <= p else 1.0)
        if t == 4:
            return 0.0 if d <= q else (0.5 if d <= p else 1.0)
        if t == 5:
            return 0.0 if d <= q else ((d - q) / (p - q) if d <= p else 1.0)
        return 0.0 if d <= 0 else 1.0 - math.exp(-d * d / (2 * s * s))

    L = _num(c, "L")
    if L is None:
        L = {1: 0.0, 2: q, 3: p, 4: p, 5: p, 6: s}[t]
    return {"type": t, "q": q if t in (2, 4, 5) else None, "p": p if t in (3, 4, 5) else None,
            "s": s if t == 6 else None, "L": L, "G": G}


def _oriented(p: Problem) -> List[List[float]]:
    X = crisp_matrix(p)
    return [[x if c.maximize else -x for x, c in zip(row, p.criteria)] for row in X]


def _flows(M: List[List[float]], divide: bool) -> Dict[str, List[float]]:
    m = len(M)
    k = (m - 1) if divide and m > 1 else 1
    fp = [sum(M[i][j] for j in range(m) if j != i) / k for i in range(m)]
    fm = [sum(M[j][i] for j in range(m) if j != i) / k for i in range(m)]
    return {"phi_plus": fp, "phi_minus": fm, "phi": [a - b for a, b in zip(fp, fm)]}


def partial_order(fp: Sequence[float], fm: Sequence[float], tol: float = _TOL) -> Dict[str, Any]:
    """Relacje PROMETHEE I (6.14): P, I, R; poziomy częściowego rankingu jak w przykładzie 6.2."""
    m = len(fp)
    rel = [[""] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            dp, dm = fp[i] - fp[j], fm[i] - fm[j]
            gp, ep, lp = dp > tol, abs(dp) <= tol, dp < -tol
            gm, em, lm = dm > tol, abs(dm) <= tol, dm < -tol
            if ep and em:
                rel[i][j] = "I"
            elif (gp and lm) or (ep and lm) or (gp and em):
                rel[i][j] = "P"
            elif (gp and gm) or (lp and lm):
                rel[i][j] = "R"
    left, level, levels = set(range(m)), 1, [0] * m
    while left:
        top = [i for i in left if not any(rel[j][i] == "P" for j in left if j != i)]
        for i in top:
            levels[i] = level
        left -= set(top)
        level += 1
    # krawędzie diagramu Hassego relacji P
    P = [[rel[i][j] == "P" for j in range(m)] for i in range(m)]
    edges = [(i, j) for i in range(m) for j in range(m)
             if P[i][j] and not any(P[i][k] and P[k][j] for k in range(m) if k not in (i, j))]
    return {"relations": rel, "levels": levels, "hasse": edges}


def _partial_result(method: str, p: Problem, fl: Dict[str, List[float]], steps: Dict[str, Any], notes: list):
    po = partial_order(fl["phi_plus"], fl["phi_minus"])
    lv = po["levels"]
    res = _result(method, p, fl["phi"], "przepływ netto φ (pomocniczo; ranking częściowy wg φ⁺ i φ⁻)", steps, notes)
    res["ranks"] = lv
    res["ranking"] = [p.variants[i] for i in sorted(range(p.m), key=lambda i: (lv[i], -fl["phi"][i], i))]
    res["best"] = [v for v, r in zip(p.variants, lv) if r == 1]
    steps["relations"] = po["relations"]
    steps["hasse"] = [[p.variants[i], p.variants[j]] for i, j in po["hasse"]]
    inc = [f"{p.variants[i]} R {p.variants[j]}" for i in range(p.m) for j in range(i + 1, p.m)
           if po["relations"][i][j] == "R"]
    if inc:
        notes.append("Nieporównywalne pary (R): " + ", ".join(inc) + ".")
    return res


# ---------------------------------------------------------------------------
# PROMETHEE I i II (6.2)
# ---------------------------------------------------------------------------

def _pi_matrix(p: Problem, X, notes):
    w = p.weights(notes=notes)
    fns = [preference_function(c) for c in p.criteria]
    m, n = p.m, p.n
    Gk = [[[fns[k]["G"](X[i][k] - X[j][k]) if i != j else 0.0 for j in range(m)] for i in range(m)] for k in range(n)]
    pi = [[sum(w[k] * Gk[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]     # (6.10)
    params = [{kk: v for kk, v in f.items() if kk != "G"} for f in fns]
    return w, params, Gk, pi


def promethee_i(p: Problem, divide: bool = True) -> Dict[str, Any]:
    """PROMETHEE I: indeksy π (6.10), przepływy φ⁺, φ⁻ (6.12)–(6.13), ranking częściowy (6.14)."""
    notes: list = []
    X = _oriented(p)
    w, params, Gk, pi = _pi_matrix(p, X, notes)
    fl = _flows(pi, divide)
    return _partial_result("promethee_i", p, fl, {"weights": w, "criteria_params": params, "G": Gk, "pi": pi, **fl},
                           notes)


def promethee_ii(p: Problem, divide: bool = True) -> Dict[str, Any]:
    """PROMETHEE II: przepływ netto φ = φ⁺ − φ⁻ (6.15), ranking całkowity (6.16)."""
    notes: list = []
    X = _oriented(p)
    w, params, Gk, pi = _pi_matrix(p, X, notes)
    fl = _flows(pi, divide)
    return _result("promethee_ii", p, fl["phi"], "przepływ netto φ", {"weights": w, "criteria_params": params,
                                                                        "G": Gk, "pi": pi, **fl}, notes)


# ---------------------------------------------------------------------------
# Zgodność, niezgodność, wiarygodność (6.18)–(6.22)
# ---------------------------------------------------------------------------

def _thresholds(p: Problem, need_v: bool):
    out = []
    for c in p.criteria:
        q = _num(c, "q", default=0.0)
        pp = _num(c, "p", required=True)
        v = _num(c, "v", required=need_v)
        if pp < q:
            raise ProblemError(f"Kryterium {c.name}: wymagane p ≥ q")
        if v is not None and v <= pp:
            raise ProblemError(f"Kryterium {c.name}: wymagane v > p")
        out.append((q, pp, v))
    return out


def _phi(d, q, pp):
    if d > pp:
        return 1.0
    if d > q:
        return (d - q) / (pp - q)
    return 0.0


def _disc(d, pp, v):
    if v is None:
        return 0.0
    if d > v:
        return 1.0
    if d > pp:
        return (d - pp) / (v - pp)
    return 0.0


def credibility(c: float, d: Sequence[float]) -> float:
    """σ = c Π_{k ∈ D} (1 − d_k)/(1 − c), D = {k: d_k > c} (6.21)–(6.22)."""
    s = c
    for dk in d:
        if dk > c + _TOL:
            s *= (1 - dk) / (1 - c)
    return s


def _veto_core(p: Problem, X, notes, veto_direction):
    if veto_direction not in VETO_DIRECTIONS:
        raise ProblemError(f"veto_direction: {', '.join(VETO_DIRECTIONS)}")
    w = p.weights(notes=notes)
    th = _thresholds(p, True)
    m, n = p.m, p.n
    phik = [[[_phi(X[i][k] - X[j][k], th[k][0], th[k][1]) if i != j else 0.0 for j in range(m)] for i in range(m)]
            for k in range(n)]
    C = [[sum(w[k] * phik[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]           # (6.18)
    sgn = 1 if veto_direction == "formula" else -1
    D = [[[_disc(sgn * (X[j][k] - X[i][k]), th[k][1], th[k][2]) if i != j else 0.0 for j in range(m)]
          for i in range(m)] for k in range(n)]                                                       # (6.20)
    S = [[credibility(C[i][j], [D[k][i][j] for k in range(n)]) if i != j else 0.0 for j in range(m)]
         for i in range(m)]
    Dsets = [[[p.criteria[k].name for k in range(n) if D[k][i][j] > C[i][j] + _TOL] for j in range(m)]
             for i in range(m)]
    if veto_direction == "example":
        notes.append("Wskaźniki niezgodności liczone jak w przykładach 6.7 i 6.10 (d_k z f_k(aⁱ) − f_k(aʲ)); "
                     "wzór (6.20) używa f_k(aʲ) − f_k(aⁱ).")
    return w, th, phik, C, D, S, Dsets


def promethee_ii_veto(p: Problem, veto_direction: str = "formula", divide: bool = False) -> Dict[str, Any]:
    """PROMETHEE II z progami weta (6.3): c (6.18)–(6.19), d_k (6.20), σ (6.21)–(6.22), przepływy z σ
    (6.23)–(6.24, bez dzielenia przez m − 1), ranking wg φ."""
    notes: list = []
    X = _oriented(p)
    w, th, phik, C, D, S, Ds = _veto_core(p, X, notes, veto_direction)
    fl = _flows(S, divide)
    return _result("promethee_ii_veto", p, fl["phi"], "przepływ netto φ (z wiarygodności σ)",
                   {"weights": w, "thresholds": [{"q": q, "p": pp, "v": v} for q, pp, v in th], "phi_k": phik,
                    "concordance": C, "discordance": D, "D_sets": Ds, "credibility": S, **fl}, notes)


# ---------------------------------------------------------------------------
# EXPROM (6.4) i EXPROM II z progami weta (6.5)
# ---------------------------------------------------------------------------

def exprom(p: Problem, ranking: str = "complete", divide: bool = True) -> Dict[str, Any]:
    """EXPROM: WP = π (6.27), SP (6.28)–(6.30), TP = min{1; WP + SP} (6.31), przepływy (6.32)–(6.33);
    ranking = complete (EXPROM II, wg φ) albo partial (EXPROM I, jak PROMETHEE I)."""
    if ranking not in ("complete", "partial"):
        raise ProblemError("ranking: complete albo partial")
    notes: list = []
    X = _oriented(p)
    w, params, Gk, WP = _pi_matrix(p, X, notes)
    m, n = p.m, p.n
    best = [max(r[k] for r in X) for k in range(n)]
    worst = [min(r[k] for r in X) for k in range(n)]
    SPk = []
    for k in range(n):
        dm, L = best[k] - worst[k], params[k]["L"]
        if dm - L <= 0:
            notes.append(f"Kryterium {p.criteria[k].name}: dm_k − L_k ≤ 0 — ścisłe indeksy preferencji równe 0.")
            SPk.append([[0.0] * m for _ in range(m)])
            continue
        SPk.append([[max(0.0, (X[i][k] - X[j][k] - L) / (dm - L)) if i != j else 0.0 for j in range(m)]
                    for i in range(m)])                                                              # (6.29)
    if any(f["type"] == 6 and p.criteria[k].extra.get("L") is None for k, f in enumerate(params)):
        notes.append("Kryterium gaussowskie: przyjęto L_k = s_k (książka nie określa L_k dla typu 6; pole \"L\").")
    SP = [[sum(w[k] * SPk[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]            # (6.28)
    TP = [[min(1.0, WP[i][j] + SP[i][j]) if i != j else 0.0 for j in range(m)] for i in range(m)]     # (6.31)
    fl = _flows(TP, divide)
    steps = {"weights": w, "criteria_params": params, "ideal": best, "anti_ideal": worst, "G": Gk, "WP": WP,
             "SP_k": SPk, "SP": SP, "TP": TP, **fl}
    if ranking == "partial":
        return _partial_result("exprom", p, fl, steps, notes)
    return _result("exprom", p, fl["phi"], "przepływ netto φ (EXPROM II)", steps, notes)


def exprom_veto(p: Problem, veto_direction: str = "formula", divide: bool = False) -> Dict[str, Any]:
    """EXPROM II z progami weta (6.5): σ jak w PROMETHEE II z wetem, π = ν Σ w_k π_k (6.34)–(6.36),
    ω = min{1; σ + π} (6.37), przepływy (6.38)–(6.39)."""
    notes: list = []
    X = _oriented(p)
    w, th, phik, C, D, S, Ds = _veto_core(p, X, notes, veto_direction)
    m, n = p.m, p.n
    best = [max(r[k] for r in X) for k in range(n)]
    worst = [min(r[k] for r in X) for k in range(n)]
    nu = [[1 if i == j or not Ds[i][j] else 0 for j in range(m)] for i in range(m)]                 # (6.35)
    PIk = []
    for k in range(n):
        den = best[k] - worst[k] - th[k][1]
        PIk.append([[(X[i][k] - X[j][k] - th[k][1]) / den if i != j and phik[k][i][j] >= 1 and den > 0 else 0.0
                     for j in range(m)] for i in range(m)])                                          # (6.36)
    PI = [[nu[i][j] * sum(w[k] * PIk[k][i][j] for k in range(n)) if i != j else 0.0 for j in range(m)]
          for i in range(m)]                                                                         # (6.34)
    Om = [[min(1.0, S[i][j] + PI[i][j]) if i != j else 0.0 for j in range(m)] for i in range(m)]     # (6.37)
    fl = _flows(Om, divide)
    return _result("exprom_veto", p, fl["phi"], "przepływ netto φ (z ω = min{1; σ + π})",
                   {"weights": w, "thresholds": [{"q": q, "p": pp, "v": v} for q, pp, v in th], "phi_k": phik,
                    "concordance": C, "discordance": D, "D_sets": Ds, "credibility": S, "nu": nu, "pi_k": PIk,
                    "pi": PI, "omega": Om, "ideal": best, "anti_ideal": worst, **fl}, notes)


# ---------------------------------------------------------------------------
# Wersje stochastyczne (6.6, 6.7)
# ---------------------------------------------------------------------------

from .ryzyko import rozklad as _distribution, dominance_test as _dominance_test, srednia as _mean  # noqa: E402


def _threshold_fn(c, key, required) -> Optional[Callable[[float], float]]:
    v = c.extra.get(key)
    if v is None:
        if required:
            raise ProblemError(f"Kryterium {c.name}: brak progu {key!r}")
        return None
    if isinstance(v, (list, tuple)):
        if len(v) != 2:
            raise ProblemError(f"Kryterium {c.name}: próg {key} jako liczba albo [α, β]")
        a, b = float(v[0]), float(v[1])
        return lambda mu: a + b * mu
    x = float(v)
    return lambda mu: x


def _stochastic_core(p: Problem, risk, dominances, notes):
    w = p.weights(notes=notes)
    m, n = p.m, p.n
    F = [[_distribution(p.values[i][k], f"{p.variants[i]}, {p.criteria[k].name}") for k in range(n)]
         for i in range(m)]
    for k, c in enumerate(p.criteria):
        if not c.maximize:
            for i in range(m):
                F[i][k] = F[i][k].odwrocony()
    mu = [[_mean(F[i][k]) for k in range(n)] for i in range(m)]
    allowed, test = _dominance_test(risk, dominances)
    SD = [[[test(F[i][k], F[j][k]) if i != j else None for j in range(m)] for i in range(m)] for k in range(n)]
    qf = [_threshold_fn(c, "q", False) for c in p.criteria]
    pf = [_threshold_fn(c, "p", True) for c in p.criteria]
    vf = [_threshold_fn(c, "v", True) for c in p.criteria]
    phik = [[[0.0] * m for _ in range(m)] for _ in range(n)]
    D = [[[0.0] * m for _ in range(m)] for _ in range(n)]
    for k in range(n):
        for i in range(m):
            for j in range(m):
                if i == j:
                    continue
                mi, mj = mu[i][k], mu[j][k]
                pk, vk = pf[k](mi), vf[k](mi)
                if SD[k][i][j]:
                    if qf[k] is None:                                                                 # (6.41)
                        phik[k][i][j] = 1.0 if mi >= mj + pk else ((mi - mj) / pk if mi > mj else 0.0)
                    else:                                                                             # (6.48)
                        qk = qf[k](mi)
                        phik[k][i][j] = 1.0 if mi > mj + pk else ((mi - mj - qk) / (pk - qk) if mi > mj + qk else 0.0)
                if SD[k][j][i]:                                                                       # (6.42)
                    D[k][i][j] = 1.0 if mj > mi + vk else ((mj - mi - pk) / (vk - pk) if mj > mi + pk else 0.0)
    C = [[sum(w[k] * phik[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    S = [[credibility(C[i][j], [D[k][i][j] for k in range(n)]) if i != j else 0.0 for j in range(m)]
         for i in range(m)]
    Ds = [[[p.criteria[k].name for k in range(n) if D[k][i][j] > C[i][j] + _TOL] for j in range(m)] for i in range(m)]
    notes.append(f"Dominacje zgodne z funkcją użyteczności decydenta: {', '.join(allowed)}.")
    return w, mu, SD, phik, C, D, S, Ds, pf


def promethee_ii_sd(p: Problem, risk: str = "DARA", dominances: Optional[List[str]] = None,
                    divide: bool = False) -> Dict[str, Any]:
    """PROMETHEE II z progami weta i dominacjami stochastycznymi (6.6): φ_k (6.41) lub z q (6.48),
    d_k (6.42), σ (6.43)–(6.44), przepływy (6.45)–(6.46)."""
    notes: list = []
    w, mu, SD, phik, C, D, S, Ds, _ = _stochastic_core(p, risk, dominances, notes)
    fl = _flows(S, divide)
    return _result("promethee_ii_sd", p, fl["phi"], "przepływ netto φ (z wiarygodności σ)",
                   {"weights": w, "means": mu, "dominance": SD, "phi_k": phik, "concordance": C, "discordance": D,
                    "D_sets": Ds, "credibility": S, **fl}, notes)


def exprom_ii_sd(p: Problem, risk: str = "DARA", dominances: Optional[List[str]] = None,
                 divide: bool = False) -> Dict[str, Any]:
    """EXPROM II z progami weta i dominacjami stochastycznymi (6.7): c z (6.47)–(6.48), d_k (6.42), σ,
    π = ν Σ w_k π_k (6.49)–(6.53), ω = min{1; σ + π} (6.54), przepływy (6.55)–(6.56)."""
    notes: list = []
    w, mu, SD, phik, C, D, S, Ds, pf = _stochastic_core(p, risk, dominances, notes)
    m, n = p.m, p.n
    hi = [max(mu[i][k] for i in range(m)) for k in range(n)]
    lo = [min(mu[i][k] for i in range(m)) for k in range(n)]
    nu = [[1 if i == j or not Ds[i][j] else 0 for j in range(m)] for i in range(m)]
    PIk = []
    for k in range(n):
        rows = []
        for i in range(m):
            row = []
            for j in range(m):
                pk = pf[k](mu[i][k])
                den = (hi[k] - lo[k]) - pk
                row.append(((mu[i][k] - mu[j][k]) - pk) / den if i != j and phik[k][i][j] >= 1 and den > 0 else 0.0)
            rows.append(row)
        PIk.append(rows)                                                                              # (6.51)
    PI = [[nu[i][j] * sum(w[k] * PIk[k][i][j] for k in range(n)) if i != j else 0.0 for j in range(m)]
          for i in range(m)]
    Om = [[min(1.0, S[i][j] + PI[i][j]) if i != j else 0.0 for j in range(m)] for i in range(m)]
    fl = _flows(Om, divide)
    return _result("exprom_ii_sd", p, fl["phi"], "przepływ netto φ (z ω = min{1; σ + π})",
                   {"weights": w, "means": mu, "mu_max": hi, "mu_min": lo, "dominance": SD, "phi_k": phik,
                    "concordance": C, "discordance": D, "D_sets": Ds, "credibility": S, "nu": nu, "pi_k": PIk,
                    "pi": PI, "omega": Om, **fl}, notes)
