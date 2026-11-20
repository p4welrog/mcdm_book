"""Metody ELECTRE (rozdz. 5).

Pola kryteriów (oprócz name, direction, weight): progi "q" (równoważności), "p" (preferencji), "v" (weta) —
liczba albo [α, β], co oznacza próg α·f_k(aⁱ) + β zależny od oceny wariantu aⁱ (w wersjach stochastycznych
od wartości oczekiwanej μ_ik, wzór 5.39). Kryteria minimalizowane są odwracane (−f).

ELECTRE TRI: w zadaniu "profiles" — profile graniczne b¹ … b^(p−1) (od najniższego, wartości wg kryteriów),
opcjonalnie "categories" — nazwy p kategorii od najgorszej; progi q_k(bʰ), p_k(bʰ), v_k(bʰ) jak wyżej
(liczba albo [α, β] liczone od wartości profilu).

Uwaga: [α, β] = α·x + β jak we wzorze (5.39) i w programach ELECTRE z Politechniki Poznańskiej; w PROMETHEE
(rozdz. 6) pakiet przyjmuje [α, β] = α + β·μ.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .additive import _result
from .problem import Problem, ProblemError, crisp_matrix
from .promethee import _stochastic_core, credibility

_TOL = 1e-9


# ---------------------------------------------------------------------------
# Wspólne
# ---------------------------------------------------------------------------

def _oriented(p: Problem) -> List[List[float]]:
    X = crisp_matrix(p)
    return [[x if c.maximize else -x for x, c in zip(row, p.criteria)] for row in X]


def threshold(c, key: str, required: bool = False, default: Optional[float] = None) -> Optional[Callable[[float], float]]:
    """Próg jako funkcja oceny: liczba → stała; [α, β] → α·x + β (5.39)."""
    v = c.extra.get(key)
    if v is None:
        if required:
            raise ProblemError(f"Kryterium {c.name}: brak progu {key!r}")
        if default is None:
            return None
        return lambda x, d=default: d
    if isinstance(v, (list, tuple)):
        if len(v) != 2:
            raise ProblemError(f"Kryterium {c.name}: próg {key} — liczba albo [α, β] (α·f + β)")
        a, b = float(v[0]), float(v[1])
        return lambda x: a * x + b
    try:
        x0 = float(v)
    except (TypeError, ValueError):
        raise ProblemError(f"Kryterium {c.name}: niepoprawny próg {key} = {v!r}")
    if x0 < 0:
        raise ProblemError(f"Kryterium {c.name}: próg {key} nie może być ujemny")
    return lambda x: x0


def _levels(S: List[List[bool]], top_down: bool = True) -> Tuple[List[int], bool]:
    """Poziomy grafu przewyższania (5.2.4): od góry — kolejno warianty nieprzewyższane (ściśle) przez pozostałe;
    od dołu — kolejno warianty, które nie przewyższają ściśle pozostałych. Zwraca (poziomy, czy były cykle)."""
    m = len(S)
    left, level, out, cyc = set(range(m)), 1, [0] * m, False
    strict = [[S[i][j] and not S[j][i] for j in range(m)] for i in range(m)]
    while left:
        if top_down:
            cand = [i for i in left if not any(strict[j][i] for j in left if j != i)]
        else:
            cand = [i for i in left if not any(strict[i][j] for j in left if j != i)]
        if not cand:
            cand, cyc = list(left), True
        for i in cand:
            out[i] = level
        left -= set(cand)
        level += 1
    if not top_down:
        mx = max(out)
        out = [mx - x + 1 for x in out]
    return out, cyc


def _graph_result(method: str, p: Problem, S: List[List[bool]], steps: Dict[str, Any], notes: list):
    m = p.m
    top, cyc1 = _levels(S, True)
    bottom, cyc2 = _levels(S, False)
    if cyc1 or cyc2:
        notes.append("Graf przewyższania ma cykle — warianty w cyklu umieszczono na wspólnym poziomie "
                     "(książka zaleca grupowanie wierzchołków, 5.2.4).")
    res = _result(method, p, [float(x) for x in top], "poziom w grafie przewyższania (od najlepszych; mniej = lepiej)",
                  steps, notes, descending=False)
    res["best"] = [v for v, t in zip(p.variants, top) if t == 1]
    steps["outranking"] = [[1 if S[i][j] else 0 for j in range(m)] for i in range(m)]
    steps["edges"] = [[p.variants[i], p.variants[j]] for i in range(m) for j in range(m) if i != j and S[i][j]]
    steps["levels_top_down"] = top
    steps["levels_bottom_up"] = bottom
    inc = [f"{p.variants[i]} R {p.variants[j]}" for i in range(m) for j in range(i + 1, m) if not S[i][j] and not S[j][i]]
    if inc:
        notes.append("Pary nieporównywalne (brak przewyższania w obu kierunkach): " + ", ".join(inc) + ".")
    return res


def _check_s(s):
    if s is None:
        raise ProblemError("Podaj próg zgodności s (opcja s, zwykle 0,5–1)")
    s = float(s)
    if not 0 <= s <= 1:
        raise ProblemError("Próg zgodności s musi należeć do [0; 1]")
    return s


# ---------------------------------------------------------------------------
# ELECTRE I, Iv, Is (5.2)
# ---------------------------------------------------------------------------

def _concordance_true(p: Problem, X, w):
    m, n = p.m, p.n
    phik = [[[1.0 if X[i][k] >= X[j][k] else 0.0 for j in range(m)] for i in range(m)] for k in range(n)]   # (5.10)
    C = [[sum(w[k] * phik[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]                  # (5.9)
    return phik, C


def electre_i(p: Problem, s: Optional[float] = None, v: Optional[float] = None) -> Dict[str, Any]:
    """ELECTRE I: c (5.9)–(5.10), zbiór zgodności C_s (5.11), poziom niezgodności d (5.12), D_v (5.13),
    S = C_s \\ D_v (5.14), graf przewyższania. Jeden próg weta v dla wszystkich kryteriów (wspólna skala)."""
    notes: list = []
    s = _check_s(s)
    if v is None:
        raise ProblemError("ELECTRE I: podaj wspólny próg weta v (opcja v)")
    v = float(v)
    w = p.weights(notes=notes)
    X = _oriented(p)
    m, n = p.m, p.n
    phik, C = _concordance_true(p, X, w)
    Cs = [[i != j and C[i][j] >= s - _TOL for j in range(m)] for i in range(m)]
    d = [[max([X[j][k] - X[i][k] for k in range(n) if X[j][k] > X[i][k]] or [0.0]) if Cs[i][j] else None
          for j in range(m)] for i in range(m)]                                                                  # (5.12)
    Dv = [[Cs[i][j] and d[i][j] > v + _TOL for j in range(m)] for i in range(m)]
    S = [[Cs[i][j] and not Dv[i][j] for j in range(m)] for i in range(m)]
    return _graph_result("electre_i", p, S, {"weights": w, "s": s, "v": v, "phi_k": phik, "concordance": C,
                                             "concordance_set": [[int(x) for x in r] for r in Cs],
                                             "discordance_level": d,
                                             "discordance_set": [[int(x) for x in r] for r in Dv]}, notes)


def electre_iv(p: Problem, s: Optional[float] = None) -> Dict[str, Any]:
    """ELECTRE Iv: jak ELECTRE I, ale progi weta v_k dla kryteriów (5.15): weto, gdy f_k(aʲ) > f_k(aⁱ) + v_k."""
    notes: list = []
    s = _check_s(s)
    w = p.weights(notes=notes)
    X = _oriented(p)
    m, n = p.m, p.n
    vf = [threshold(c, "v") for c in p.criteria]
    if all(f is None for f in vf):
        notes.append("Żadne kryterium nie ma progu weta v — wynik jak ELECTRE I bez testu niezgodności.")
    phik, C = _concordance_true(p, X, w)
    Cs = [[i != j and C[i][j] >= s - _TOL for j in range(m)] for i in range(m)]
    Dk = [[[bool(Cs[i][j] and vf[k] is not None and X[j][k] > X[i][k] + vf[k](X[i][k]) + _TOL) for j in range(m)]
           for i in range(m)] for k in range(n)]
    Dv = [[any(Dk[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    S = [[Cs[i][j] and not Dv[i][j] for j in range(m)] for i in range(m)]
    return _graph_result("electre_iv", p, S, {"weights": w, "s": s, "phi_k": phik, "concordance": C,
                                              "concordance_set": [[int(x) for x in r] for r in Cs],
                                              "veto_k": [[[int(x) for x in r] for r in M] for M in Dk],
                                              "discordance_set": [[int(x) for x in r] for r in Dv]}, notes)


def _pseudo_phi(fi, fj, q, pp):
    """φ_k z progami q, p liczonymi dla aⁱ (5.17, 5.21)."""
    if fi + q >= fj:
        return 1.0
    if fj <= fi + pp and pp > q:
        return (fi + pp - fj) / (pp - q)
    return 0.0


def _pseudo_concordance(p: Problem, X, w, need_p: bool):
    m, n = p.m, p.n
    qf = [threshold(c, "q", default=0.0) for c in p.criteria]
    pf = [threshold(c, "p", required=need_p) or qf[k] for k, c in enumerate(p.criteria)]          # brak p → p = q
    for k, c in enumerate(p.criteria):
        for i in range(m):
            if pf[k](X[i][k]) < qf[k](X[i][k]) - _TOL:
                raise ProblemError(f"Kryterium {c.name}: wymagane q ≤ p (5.4)")
    phik = [[[_pseudo_phi(X[i][k], X[j][k], qf[k](X[i][k]), pf[k](X[i][k])) for j in range(m)] for i in range(m)]
            for k in range(n)]
    C = [[sum(w[k] * phik[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    return qf, pf, phik, C


def electre_is(p: Problem, s: Optional[float] = None) -> Dict[str, Any]:
    """ELECTRE Is: pseudokryteria — c (5.16)–(5.17); weto (5.18)–(5.19):
    f_k(aʲ) + q_k[f_k(aʲ)]·η_k > f_k(aⁱ) + v_k[f_k(aⁱ)], η_k = (1 − c − w_k)/(1 − s − w_k)."""
    notes: list = []
    s = _check_s(s)
    w = p.weights(notes=notes)
    X = _oriented(p)
    m, n = p.m, p.n
    qf, pf, phik, C = _pseudo_concordance(p, X, w, need_p=False)
    vf = [threshold(c, "v") for c in p.criteria]
    Cs = [[i != j and C[i][j] >= s - _TOL for j in range(m)] for i in range(m)]
    Dk = [[[False] * m for _ in range(m)] for _ in range(n)]
    for k in range(n):
        if vf[k] is None:
            continue
        den = 1 - s - w[k]
        if den <= 0:
            notes.append(f"Kryterium {p.criteria[k].name}: 1 − s − w_k ≤ 0 — η_k nieokreślone, przyjęto η_k = 0.")
        for i in range(m):
            for j in range(m):
                if not Cs[i][j]:
                    continue
                eta = (1 - C[i][j] - w[k]) / den if den > 0 else 0.0                                          # (5.19)
                Dk[k][i][j] = X[j][k] + qf[k](X[j][k]) * eta > X[i][k] + vf[k](X[i][k]) + _TOL                # (5.18)
    Dv = [[any(Dk[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    S = [[Cs[i][j] and not Dv[i][j] for j in range(m)] for i in range(m)]
    return _graph_result("electre_is", p, S, {"weights": w, "s": s, "phi_k": phik, "concordance": C,
                                              "concordance_set": [[int(x) for x in r] for r in Cs],
                                              "veto_k": [[[int(x) for x in r] for r in M] for M in Dk],
                                              "discordance_set": [[int(x) for x in r] for r in Dv]}, notes)


# ---------------------------------------------------------------------------
# ELECTRE III (5.3): wiarygodność i destylacje
# ---------------------------------------------------------------------------

def _discordance_iii(fi, fj, pp, v):
    """d_k (5.23)."""
    if v is None:
        return 0.0
    if fj > fi + v:
        return 1.0
    if fj <= fi + pp:
        return 0.0
    return (fj - fi - pp) / (v - pp)


def lambda_preference(S, i, j, lam, alpha, beta) -> bool:
    """aⁱ ≻^λ aʲ ⇔ σ(aⁱ, aʲ) − s[σ(aⁱ, aʲ)] > σ(aʲ, aⁱ) i σ(aⁱ, aʲ) > λ (5.24); s(x) = α·x + β."""
    sij = S[i][j]
    return sij > lam + _TOL and sij - (alpha * sij + beta) > S[j][i] + _TOL


def distillation(S: List[List[float]], descending: bool, alpha: float = -0.15, beta: float = 0.30
                 ) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
    """Destylacja zstępująca (descending) lub wstępująca (5.25)–(5.28). Zwraca klasy w kolejności
    wyznaczania (zstępująca: od najlepszej; wstępująca: od najgorszej) i ślad kroków."""
    m = len(S)
    A = list(range(m))
    classes, log = [], []
    while A:
        if len(A) == 1:
            classes.append(A[:])
            break
        lam = max(S[i][j] for i in A for j in A if i != j)                                                    # 3.2
        D = A[:]
        while True:
            thr = lam - (alpha * lam + beta)
            cand = [S[i][j] for i in D for j in D if i != j and S[i][j] < thr - _TOL]
            lam_n = max(cand) if cand else 0.0                                                               # (5.26)
            qv = {}
            for i in D:
                pw = sum(1 for j in D if j != i and lambda_preference(S, i, j, lam_n, alpha, beta))
                fw = sum(1 for j in D if j != i and lambda_preference(S, j, i, lam_n, alpha, beta))
                qv[i] = pw - fw                                                                              # (5.25)
            ext = max(qv.values()) if descending else min(qv.values())                                       # (5.27–5.28)
            Dn = [i for i in D if qv[i] == ext]
            log.append({"D": D[:], "lambda_prev": lam, "lambda": lam_n, "q": [qv[i] for i in D], "selected": Dn[:]})
            if len(Dn) == 1 or lam_n <= 0:
                break
            D, lam = Dn, lam_n
        classes.append(Dn)
        A = [i for i in A if i not in Dn]
    return classes, log


def final_ranking(r1: Sequence[int], r2: Sequence[int]) -> Tuple[List[List[str]], List[int]]:
    """Ranking końcowy z porządków Z1, Z2 (pozycje od góry): P, P⁻, I, R; poziomy od najlepszych."""
    m = len(r1)
    rel = [[""] * m for _ in range(m)]
    better = [[False] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            a, b = r1[i] - r1[j], r2[i] - r2[j]
            if a == 0 and b == 0:
                rel[i][j] = "I"
            elif (a <= 0 and b <= 0):
                rel[i][j], better[i][j] = "P", True
            elif a >= 0 and b >= 0:
                rel[i][j] = "P-"
            else:
                rel[i][j] = "R"
    left, lv, out = set(range(m)), 1, [0] * m
    while left:
        cand = [i for i in left if not any(better[j][i] for j in left if j != i)]
        for i in cand:
            out[i] = lv
        left -= set(cand)
        lv += 1
    return rel, out


def _iii_from_sigma(method, p, S, steps, notes, alpha, beta):
    m = p.m
    desc, log_d = distillation(S, True, alpha, beta)
    asc, log_a = distillation(S, False, alpha, beta)
    r1 = [0] * m
    for h, cl in enumerate(desc, 1):
        for i in cl:
            r1[i] = h
    r2 = [0] * m
    na = len(asc)
    for h, cl in enumerate(asc, 1):
        for i in cl:
            r2[i] = na - h + 1
    rel, lv = final_ranking(r1, r2)
    steps.update({"distillation_alpha": alpha, "distillation_beta": beta,
                  "descending_classes": [[p.variants[i] for i in cl] for cl in desc],
                  "ascending_classes": [[p.variants[i] for i in cl] for cl in reversed(asc)],
                  "descending_rank": r1, "ascending_rank": r2, "final_relations": rel,
                  "descending_log": log_d, "ascending_log": log_a})
    inc = [f"{p.variants[i]} R {p.variants[j]}" for i in range(m) for j in range(i + 1, m) if rel[i][j] == "R"]
    if inc:
        notes.append("Warianty nieporównywalne (porządki Z1 i Z2 sprzeczne): " + ", ".join(inc) + ".")
    res = _result(method, p, [float(x) for x in lv], "poziom w rankingu końcowym (mniej = lepiej)", steps, notes,
                  descending=False)
    return res


def electre_iii(p: Problem, alpha: float = -0.15, beta: float = 0.30) -> Dict[str, Any]:
    """ELECTRE III: c (5.20)–(5.21), d_k (5.23), σ (5.22), destylacja zstępująca i wstępująca z progiem
    dyskryminacji s(λ) = α·λ + β (domyślnie −0,15λ + 0,30), ranking końcowy (krok 4)."""
    notes: list = []
    w = p.weights(notes=notes)
    X = _oriented(p)
    m, n = p.m, p.n
    qf, pf, phik, C = _pseudo_concordance(p, X, w, need_p=True)
    vf = [threshold(c, "v") for c in p.criteria]
    for k, c in enumerate(p.criteria):
        if vf[k] is not None and any(vf[k](X[i][k]) <= pf[k](X[i][k]) for i in range(m)):
            raise ProblemError(f"Kryterium {c.name}: wymagane v > p")
    Dk = [[[_discordance_iii(X[i][k], X[j][k], pf[k](X[i][k]), vf[k](X[i][k]) if vf[k] else None) if i != j else 0.0
            for j in range(m)] for i in range(m)] for k in range(n)]
    S = [[credibility(C[i][j], [Dk[k][i][j] for k in range(n)]) if i != j else 1.0 for j in range(m)]
         for i in range(m)]
    Ds = [[[p.criteria[k].name for k in range(n) if Dk[k][i][j] > C[i][j] + _TOL] for j in range(m)] for i in range(m)]
    steps = {"weights": w, "phi_k": phik, "concordance": C, "discordance": Dk, "D_sets": Ds, "credibility": S}
    return _iii_from_sigma("electre_iii", p, S, steps, notes, float(alpha), float(beta))


# ---------------------------------------------------------------------------
# ELECTRE TRI (5.4)
# ---------------------------------------------------------------------------

def electre_tri(p: Problem, cut: float = 0.75, procedure: str = "both") -> Dict[str, Any]:
    """ELECTRE TRI: c(aⁱ, bʰ) (5.29)–(5.30), d_k (5.32), σ (5.31), przypisanie pesymistyczne
    (aⁱ S bʰ od najwyższego profilu) i optymistyczne (bʰ ≻ aⁱ od najniższego)."""
    if procedure not in ("pessimistic", "optimistic", "both"):
        raise ProblemError("procedure: pessimistic | optimistic | both")
    notes: list = []
    lam = float(cut)
    if not 0.5 <= lam <= 1:
        notes.append("Poziom cięcia λ poza zalecanym przedziałem [0,5; 1].")
    w = p.weights(notes=notes)
    X = _oriented(p)
    m, n = p.m, p.n
    prof = p.extra.get("profiles")
    if not prof or not isinstance(prof, list):
        raise ProblemError("ELECTRE TRI: podaj \"profiles\" — profile graniczne b¹…b^(p−1) (wartości wg kryteriów)")
    H = len(prof)
    B = []
    for h, b in enumerate(prof):
        if len(b) != n:
            raise ProblemError(f"Profil b{h + 1}: {n} wartości (po jednej na kryterium)")
        B.append([float(x) if c.maximize else -float(x) for x, c in zip(b, p.criteria)])
    for h in range(1, H):
        if any(B[h][k] < B[h - 1][k] - _TOL for k in range(n)):
            notes.append(f"Profil b{h + 1} nie dominuje profilu b{h} na wszystkich kryteriach.")
    cats = p.extra.get("categories") or [f"C{h}" for h in range(1, H + 2)]
    if len(cats) != H + 1:
        raise ProblemError(f"\"categories\": {H + 1} nazw kategorii (od najgorszej)")

    def thr(k, key, h):
        f = threshold(p.criteria[k], key, required=(key == "p"), default=0.0 if key == "q" else None)
        return None if f is None else f(B[h][k])

    T = [[(thr(k, "q", h), thr(k, "p", h), thr(k, "v", h)) for h in range(H)] for k in range(n)]

    def sig(x, y, k_thr):
        """σ(x, y) dla porównania x z y, progi profilu."""
        phik, dk = [], []
        for k in range(n):
            q, pp, v = k_thr[k]
            diff = y[k] - x[k]
            phik.append(1.0 if diff <= q + _TOL else ((x[k] + pp - y[k]) / (pp - q) if diff <= pp + _TOL and pp > q
                                                      else 0.0))                                             # (5.30)
            if v is None or diff < pp - _TOL:
                dk.append(0.0)
            elif diff >= v - _TOL:
                dk.append(1.0)
            else:
                dk.append((diff - pp) / (v - pp))                                                            # (5.32)
        c = sum(w[k] * phik[k] for k in range(n))
        return c, phik, dk, credibility(c, dk)

    ab, ba = [], []
    for i in range(m):
        r1, r2 = [], []
        for h in range(H):
            kt = [T[k][h] for k in range(n)]
            c1, ph1, d1, s1 = sig(X[i], B[h], kt)
            c2, ph2, d2, s2 = sig(B[h], X[i], kt)
            r1.append({"c": c1, "phi_k": ph1, "d_k": d1, "sigma": s1})
            r2.append({"c": c2, "phi_k": ph2, "d_k": d2, "sigma": s2})
        ab.append(r1)
        ba.append(r2)
    pess, opt = [], []
    for i in range(m):
        cat = 0
        for h in range(H - 1, -1, -1):
            if ab[i][h]["sigma"] >= lam - _TOL:
                cat = h + 1
                break
        pess.append(cat)
        cat = H
        for h in range(H):
            if ba[i][h]["sigma"] >= lam - _TOL and ab[i][h]["sigma"] < lam - _TOL:
                cat = h
                break
        opt.append(cat)
    use = opt if procedure == "optimistic" else pess
    if procedure == "both":
        diff = [p.variants[i] for i in range(m) if pess[i] != opt[i]]
        if diff:
            notes.append("Procedury pesymistyczna i optymistyczna przypisują różnie: " + ", ".join(diff)
                         + " (wynik główny: pesymistyczna).")
    steps = {"weights": w, "cut": lam, "profiles": prof, "categories": cats,
             "sigma_a_b": [[r["sigma"] for r in row] for row in ab], "sigma_b_a": [[r["sigma"] for r in row] for row in ba],
             "c_a_b": [[r["c"] for r in row] for row in ab], "c_b_a": [[r["c"] for r in row] for row in ba],
             "details_a_b": ab, "details_b_a": ba,
             "pessimistic": [cats[x] for x in pess], "optimistic": [cats[x] for x in opt]}
    res = _result("electre_tri", p, [float(x + 1) for x in use], "numer kategorii (więcej = lepiej)", steps, notes)
    res["categories"] = {v: cats[x] for v, x in zip(p.variants, use)}
    return res


# ---------------------------------------------------------------------------
# Wersje stochastyczne (5.5, 5.6)
# ---------------------------------------------------------------------------

def electre_i_sd(p: Problem, s: float = 1.0, risk: str = "DARA", dominances: Optional[List[str]] = None,
                 include_unclear: bool = False) -> Dict[str, Any]:
    """ELECTRE I z dominacjami stochastycznymi: wyraźna zgodność c_E (5.35)–(5.36), niewyraźna c_N (5.37)–(5.38)
    dla par z c_E < s w obu kierunkach; pary niejasne: c_E < s ≤ c_E + c_N (krok 4). include_unclear=True włącza
    je do relacji przewyższania (gdy decydent rozstrzygnie je na korzyść aⁱ)."""
    from .promethee import _dominance_test, _distribution
    from mcdm_cd import Distribution
    notes: list = []
    s = _check_s(s)
    w = p.weights(notes=notes)
    m, n = p.m, p.n
    F = [[_distribution(p.values[i][k], f"{p.variants[i]}, {p.criteria[k].name}") for k in range(n)] for i in range(m)]
    for k, c in enumerate(p.criteria):
        if not c.maximize:
            for i in range(m):
                d = F[i][k]
                F[i][k] = Distribution.from_pairs([-x for x in d.values], list(d.probs))
    allowed, test_t = _dominance_test(risk, dominances)
    other = "INARA" if risk == "DARA" else "DARA"
    _, test_any = _dominance_test(other, None)
    T = [[[test_t(F[i][k], F[j][k]) if i != j else None for j in range(m)] for i in range(m)] for k in range(n)]
    NT = [[[None if i == j or T[k][i][j] else test_any(F[i][k], F[j][k]) for j in range(m)] for i in range(m)]
          for k in range(n)]
    phiE = [[[1.0 if T[k][i][j] else 0.0 for j in range(m)] for i in range(m)] for k in range(n)]
    CE = [[sum(w[k] * phiE[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    phiN = [[[1.0 if i != j and ((NT[k][i][j] and not T[k][j][i]) or (NT[k][j][i] and not T[k][i][j])) else 0.0
              for j in range(m)] for i in range(m)] for k in range(n)]
    CN = [[sum(w[k] * phiN[k][i][j] for k in range(n)) for j in range(m)] for i in range(m)]
    unclear = [[i != j and CE[i][j] < s - _TOL and CE[j][i] < s - _TOL and CE[i][j] + CN[i][j] >= s - _TOL
                for j in range(m)] for i in range(m)]
    S = [[i != j and (CE[i][j] >= s - _TOL or (include_unclear and unclear[i][j])) for j in range(m)] for i in range(m)]
    unc = [f"({p.variants[i]}, {p.variants[j]})" for i in range(m) for j in range(m) if unclear[i][j]]
    if unc:
        notes.append("Pary niejasne (c_E < s ≤ c_E + c_N) — relację należy wyjaśnić z decydentem: " + ", ".join(unc)
                     + ("; włączone do relacji przewyższania." if include_unclear else "."))
    notes.append(f"Dominacje zgodne z funkcją użyteczności (SD_T): {', '.join(allowed)}; pozostałe wykryte "
                 f"dominacje traktowane jako SD_NT.")
    steps = {"weights": w, "s": s, "dominance_T": T, "dominance_NT": NT, "phi_E": phiE, "phi_N": phiN,
             "concordance_E": CE, "concordance_N": CN, "concordance_sum": [[a + b for a, b in zip(r1, r2)]
                                                                           for r1, r2 in zip(CE, CN)],
             "unclear": [[int(x) for x in r] for r in unclear]}
    return _graph_result("electre_i_sd", p, S, steps, notes)


def electre_iii_sd(p: Problem, risk: str = "DARA", dominances: Optional[List[str]] = None,
                   alpha: float = -0.15, beta: float = 0.30) -> Dict[str, Any]:
    """ELECTRE III z dominacjami stochastycznymi (5.6): c (5.44)–(5.45), d_k (5.48), σ (5.47)–(5.49) —
    jak w PROMETHEE II z dominacjami — i destylacje ELECTRE III."""
    notes: list = []
    q = Problem.from_dict(p.to_dict())
    for c in q.criteria:                       # (5.39) α·μ + β → konwencja PROMETHEE α' + β'·μ
        for key in ("q", "p", "v"):
            v = c.extra.get(key)
            if isinstance(v, (list, tuple)) and len(v) == 2:
                c.extra[key] = [v[1], v[0]]
    w, mu, SD, phik, C, D, S, Ds, _ = _stochastic_core(q, risk, dominances, notes)
    m = p.m
    S = [[S[i][j] if i != j else 1.0 for j in range(m)] for i in range(m)]
    steps = {"weights": w, "means": mu, "dominance": SD, "phi_k": phik, "concordance": C, "discordance": D,
             "D_sets": Ds, "credibility": S}
    return _iii_from_sigma("electre_iii_sd", p, S, steps, notes, float(alpha), float(beta))
