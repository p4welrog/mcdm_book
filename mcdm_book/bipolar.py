"""Metoda BIPOLAR (rozdz. 7.5–7.6).

Zadanie: oceny wariantów w "values"; bipolarny system referencyjny w polach "good" (obiekty „dobre” D)
i "bad" (obiekty „złe” Z) — wiersze ocen jak w "values"; opcjonalnie "good_names", "bad_names".
Kryteria: "weight", próg równoważności "q", próg weta "v" — najmniejsza dopuszczalna ocena (7.43), (7.46)
(nie różnica ocen); w wersji stochastycznej także próg preferencji "p". Kryterium min → oceny odwracane.

bipolar     — metoda klasyczna (7.5.1–7.5.3) z modyfikacjami 7.5.4–7.5.5,
bipolar_sd  — metoda z dominacjami stochastycznymi (7.6).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .problem import Problem, ProblemError, crisp

_TOL = 1e-9


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------

def _ref(p: Problem, key: str, label: str, conv: Callable[[Any, str], Any]) -> Tuple[List[str], List[List[Any]]]:
    rows = p.extra.get(key)
    if not rows or not isinstance(rows, list):
        raise ProblemError(f"BIPOLAR: podaj \"{key}\" — oceny obiektów {label} (wiersze jak w values)")
    names = p.extra.get(key + "_names") or [f"{'d' if key == 'good' else 'z'}{i + 1}" for i in range(len(rows))]
    if len(names) != len(rows):
        raise ProblemError(f"\"{key}_names\": {len(rows)} nazw")
    out = []
    for name, r in zip(names, rows):
        if not isinstance(r, list) or len(r) != p.n:
            raise ProblemError(f"Obiekt {name}: {p.n} ocen (po jednej na kryterium)")
        out.append([conv(x, f"{name}, {c.name}") for x, c in zip(r, p.criteria)])
    return [str(x) for x in names], out


def _oriented_rows(p: Problem, rows: List[List[float]]) -> List[List[float]]:
    return [[x if c.maximize else -x for x, c in zip(r, p.criteria)] for r in rows]


def _num(c, key) -> Optional[float]:
    v = c.extra.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ProblemError(f"Kryterium {c.name}: niepoprawny próg {key} = {v!r}")


def percentile(xs: Sequence[float], p: float) -> float:
    """Kwantyl z interpolacją liniową (jak PERCENTYL w Excelu) — decyle w przykładzie 7.13."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    h = p * (len(s) - 1)
    lo = int(h)
    if lo >= len(s) - 1:
        return s[-1]
    return s[lo] + (h - lo) * (s[lo + 1] - s[lo])


def deciles(xs: Sequence[float]) -> List[float]:
    return [percentile(xs, q / 10) for q in range(11)]


def fraction(x: float, dec: Sequence[float]) -> int:
    """ζ (7.76): numer frakcji rozkładu decylowego, do której należy x (0–10)."""
    if x < dec[0] - _TOL:
        return 0
    if x >= dec[10] - _TOL:
        return 10
    for l in range(1, 11):
        if dec[l - 1] - _TOL <= x < dec[l] - _TOL:
            return l
    return 10


def _competition(keys: List[Optional[float]], descending: bool) -> List[Optional[int]]:
    """Rangi z remisami (1, 1, 3) dla wariantów z kluczem; None — wariant pominięty."""
    out = []
    for k in keys:
        if k is None:
            out.append(None)
            continue
        better = sum(1 for t in keys if t is not None and ((t - k > _TOL) if descending else (k - t > _TOL)))
        out.append(better + 1)
    return out


def _pack(method: str, p: Problem, level: List[Optional[int]], label: str, steps: Dict[str, Any],
          notes: list, values: Optional[List[Optional[float]]] = None) -> Dict[str, Any]:
    order = sorted([i for i in range(p.m) if level[i] is not None], key=lambda i: (level[i], i))
    return {"method": method, "variants": p.variants, "criteria": [c.name for c in p.criteria],
            "scores": {"label": label, "values": values if values is not None else level,
                       "better": "higher" if values is not None else "lower"},
            "ranks": level, "ranking": [p.variants[i] for i in order],
            "best": [p.variants[i] for i in range(p.m) if level[i] == 1], "steps": steps, "notes": notes}


def _rel(dp: float, dm: float, s: float) -> str:
    """Relacja (7.51) z punktu widzenia pary (aⁱ, rʲ): L (aⁱ L rʲ), L- (rʲ L aⁱ), I, R."""
    if dp > s + _TOL and dm <= _TOL:
        return "L"
    if dp <= _TOL and dm > s + _TOL:
        return "L-"
    if dp > s + _TOL and dm > s + _TOL:
        return "I"
    return "R"


# ---------------------------------------------------------------------------
# BIPOLAR klasyczny
# ---------------------------------------------------------------------------

def bipolar(p: Problem, s: float = 0.5, weights: str = "given", veto_decile: Optional[int] = None,
            local_preference: bool = False, position: str = "classic", modify: Optional[str] = None,
            b2_prime: bool = False, veto_test: str = "formula") -> Dict[str, Any]:
    """BIPOLAR: c⁺, c⁻, c⁼ (7.35)–(7.40), wskaźniki przewyższania d⁺, d⁻ (7.43)–(7.50), relacje L, I, R (7.51),
    pozycja d_S, d_N (7.52)–(7.53), mono- i BIPOLAR-sorting/ranking (7.54)–(7.63).
    Modyfikacje: modify = good | bad (7.66)–(7.69), b2_prime — kategoria B2′ (7.70)–(7.74);
    weights = given | deciles (7.83), (7.85) | objects (μ_k z obiektów D jak w przykładzie 7.13);
    veto_decile = q → v_k = δ^D_qk (7.87); local_preference — funkcje h_k (7.76)–(7.80);
    position = classic | counts (7.81)–(7.82).
    veto_test = formula: test niekonfliktowości (7.43) dla aⁱ ≻ rʲ i (7.46) — oceny rʲ na kryteriach z I⁺ —
    dla rʲ ≻ aⁱ; example: zawsze oceny aⁱ na kryteriach z I⁻ (jak w przykładach 7.7–7.12)."""
    notes: list = []
    if weights not in ("given", "deciles", "objects"):
        raise ProblemError("weights: given | deciles | objects")
    if veto_test not in ("formula", "example"):
        raise ProblemError("veto_test: formula | example")
    if position not in ("classic", "counts"):
        raise ProblemError("position: classic | counts")
    if modify not in (None, "", "none", "good", "bad"):
        raise ProblemError("modify: good | bad")
    s = float(s)
    if not 0 <= s <= 1:
        raise ProblemError("Próg zgodności s musi należeć do [0; 1]")
    m, n = p.m, p.n
    conv = lambda x, w: crisp(x, w)
    A = _oriented_rows(p, [[conv(x, f"{v}, {c.name}") for x, c in zip(r, p.criteria)] for v, r in zip(p.variants, p.values)])
    dn, D = _ref(p, "good", "„dobrych”", conv)
    zn, Z = _ref(p, "bad", "„złych”", conv)
    D, Z = _oriented_rows(p, D), _oriented_rows(p, Z)
    # warunek (7.34) i modyfikacje systemu referencyjnego
    viol = [(dn[a], zn[b]) for a in range(len(D)) for b in range(len(Z)) if any(D[a][k] < Z[b][k] for k in range(n))]
    if viol:
        notes.append("Warunek (7.34) nie jest spełniony: " + ", ".join(f"{a} nie dominuje {b}" for a, b in viol[:6])
                     + (" …" if len(viol) > 6 else "") + ".")
    if modify == "good":                                                                      # (7.66)–(7.67)
        zs = [max(z[k] for z in Z) for k in range(n)]
        D = [[max(d[k], zs[k]) for k in range(n)] for d in D]
        notes.append("Zmodyfikowano obiekty „dobre” wzorem (7.67).")
    elif modify == "bad":                                                                     # (7.68)–(7.69)
        ds = [min(d[k] for d in D) for k in range(n)]
        Z = [[min(z[k], ds[k]) for k in range(n)] for z in Z]
        notes.append("Zmodyfikowano obiekty „złe” wzorem (7.69).")
    decD = [deciles([d[k] for d in D]) for k in range(n)]
    decZ = [deciles([z[k] for z in Z]) for k in range(n)]
    # wagi
    mu = omega = None
    if weights == "given":
        w = p.weights(notes=notes)
    else:
        if weights == "deciles":                                                              # (7.83)
            mu = [float(sum(fraction(decD[k][qq], decZ[k]) for qq in range(1, 11))) for k in range(n)]
            omega = sum(mu) / (100 * n)                                                       # (7.86)
        else:
            mu = [float(sum(fraction(d[k], decZ[k]) for d in D)) for k in range(n)]
            omega = sum(mu) / (10 * len(D) * n)
        tot = sum(mu)
        if tot <= 0:
            raise ProblemError("Wszystkie μ_k = 0 — kryteria nie różnicują zbiorów referencyjnych")
        w = [x / tot for x in mu]                                                             # (7.85)
        weak = [p.criteria[k].name for k in range(n) if mu[k] <= (55 if weights == "deciles" else 5.5 * len(D))]
        notes.append(f"Wagi z rozkładów decylowych ({'decyle D' if weights == 'deciles' else 'obiekty D'}): "
                     + ", ".join(f"{c.name} {x:.3f}" for c, x in zip(p.criteria, w)) + f"; ω = {omega:.3f}.")
        if weak:
            notes.append("Kryteria słabo różnicujące zbiory referencyjne (μ_k ≤ 55): " + ", ".join(weak)
                         + " — rozważ ich usunięcie.")
    q = [(_num(c, "q") or 0.0) for c in p.criteria]
    if veto_decile is not None:                                                               # (7.87)
        vq = int(veto_decile)
        if not 0 <= vq <= 10:
            raise ProblemError("veto_decile: 0–10")
        v = [decD[k][vq] for k in range(n)]
        notes.append(f"Progi weta = {vq}. decyl obiektów „dobrych”: " + ", ".join(f"{x:g}" for x in v) + ".")
    else:
        v = []
        for c in p.criteria:
            x = _num(c, "v")
            v.append(None if x is None else (x if c.maximize else -x))
    h = [[fraction(A[i][k], decZ[k]) / 10 if local_preference else 1.0 for k in range(n)] for i in range(m)]  # (7.77)
    R = D + Z
    rn = dn + zn
    nd = len(D)
    Cp, Cm, Ce, Dp, Dm, Rel = ([[0.0] * len(R) for _ in range(m)] for _ in range(6))
    for i in range(m):
        for j, r in enumerate(R):
            fp = [1.0 if A[i][k] - r[k] > q[k] + _TOL else 0.0 for k in range(n)]           # (7.38)
            fm = [1.0 if r[k] - A[i][k] > q[k] + _TOL else 0.0 for k in range(n)]           # (7.39)
            fe = [1.0 if abs(r[k] - A[i][k]) <= q[k] + _TOL else 0.0 for k in range(n)]     # (7.40)
            cp = sum(w[k] * h[i][k] * fp[k] for k in range(n))
            cm = sum(w[k] * h[i][k] * fm[k] for k in range(n))
            ce = sum(w[k] * h[i][k] * fe[k] for k in range(n))
            t_a = all(v[k] is None or A[i][k] > v[k] for k in range(n) if fm[k])            # (7.43)
            t_r = t_a if veto_test == "example" else \
                all(v[k] is None or r[k] > v[k] for k in range(n) if fp[k])                  # (7.46)
            if cp > cm + _TOL:
                dp, dm = (cp + ce, 0.0) if t_a else (0.0, 0.0)                               # (7.44)–(7.45)
            elif cm > cp + _TOL:
                dp, dm = (0.0, cm + ce) if t_r else (0.0, 0.0)                               # (7.47)–(7.48)
            else:
                dp = dm = (cp + ce) if (t_a and t_r) else 0.0                                # (7.49)–(7.50)
            Cp[i][j], Cm[i][j], Ce[i][j], Dp[i][j], Dm[i][j] = cp, cm, ce, dp, dm
            Rel[i][j] = _rel(dp, dm, s)
    steps: Dict[str, Any] = {"veto_test": veto_test, "weights": w, "reference_names": rn, "good": [d for d in D], "bad": [z for z in Z],
                             "q": q, "v": v, "s": s, "c_plus": Cp, "c_minus": Cm, "c_eq": Ce,
                             "d_plus": Dp, "d_minus": Dm, "relations": Rel}
    if mu is not None:
        steps.update({"mu": mu, "omega": omega})
    if local_preference:
        steps["local_preference"] = h
        steps["deciles_bad"] = decZ
    steps["deciles_good"] = decD
    if veto_test == "example":
        notes.append("Test niekonfliktowości jak w przykładach 7.7–7.12: oceny wariantu na kryteriach z I⁻ "
                     "(także gdy rʲ przeważa nad aⁱ; wzór (7.46) sprawdza oceny rʲ na kryteriach z I⁺).")
    notes.append("Dla c⁺ = c⁻ przyjęto d⁺ = d⁻ = c⁺ + c⁼ (jak w przykładzie 7.8; wzór (7.49) w druku: c⁺ + c⁻).")
    if position == "counts":
        return _counts_result("bipolar", p, Rel, nd, rn, steps, notes)
    return _classic_result(p, Dp, Dm, Rel, nd, rn, b2_prime, steps, notes)


def _classic_result(p, Dp, Dm, Rel, nd, rn, b2_prime, steps, notes):
    m = p.m
    S_cat, S_val, N_cat, N_val = [], [], [], []
    for i in range(m):
        dD = range(nd)
        up = [j for j in dD if Rel[i][j] in ("L", "I")]
        down = [j for j in dD if Rel[i][j] == "L-"]
        if up:                                                                                # (7.52)
            S_cat.append("S1"); S_val.append(max(Dp[i][j] for j in up))
        elif down:
            S_cat.append("S2"); S_val.append(min(Dm[i][j] for j in down))
        else:
            S_cat.append("S3"); S_val.append(0.0)
        zZ = range(nd, len(rn))
        bad = [j for j in zZ if Rel[i][j] in ("L-", "I")]
        good = [j for j in zZ if Rel[i][j] == "L"]
        if bad:                                                                               # (7.53)
            N_cat.append("N2"); N_val.append(max(Dm[i][j] for j in bad))
        elif good:
            N_cat.append("N1"); N_val.append(min(Dp[i][j] for j in good))
        else:
            N_cat.append("N3"); N_val.append(0.0)
    if any(S_val[i] <= _TOL and S_cat[i] != "S3" for i in range(m)) or \
            any(N_val[i] <= _TOL and N_cat[i] != "N3" for i in range(m)):
        notes.append("Część wariantów ma d_S lub d_N równe 0 mimo relacji z obiektami — traktowane jak nieporównywalne.")
        for i in range(m):
            if S_val[i] <= _TOL:
                S_cat[i] = "S3"
            if N_val[i] <= _TOL:
                N_cat[i] = "N3"

    def mono(cat, val, first, second):                                                         # (7.54)–(7.57)
        keys = []
        for c, x in zip(cat, val):
            keys.append(None if c not in (first, second) else (2 + x if c == first else 1 - x))
        return _competition(keys, True)
    monoS = mono(S_cat, S_val, "S1", "S2")
    monoN = mono(N_cat, N_val, "N1", "N2")
    B_cat, keys = [], []
    for i in range(m):
        sc, nc, ds, dn_ = S_cat[i], N_cat[i], S_val[i], N_val[i]
        if sc == "S1" and nc == "N1":
            B_cat.append("B1"); keys.append(10 + ds + dn_)                                      # (7.58)–(7.59)
        elif sc == "S2" and nc == "N1":
            B_cat.append("B2"); keys.append(5 + (1 - ds + dn_))                                  # (7.60)–(7.61)
        elif sc == "S1" and nc == "N2" and b2_prime:
            B_cat.append("B2′"); keys.append(5 + (1 + ds - dn_))                                 # (7.70)–(7.74)
        elif sc == "S2" and nc == "N2":
            B_cat.append("B3"); keys.append(-(ds + dn_))                                         # (7.62)–(7.63)
        else:
            B_cat.append(None); keys.append(None)
    level = _competition(keys, True)
    inc = [p.variants[i] for i in range(m) if B_cat[i] is None]
    if inc:
        both = [p.variants[i] for i in range(m) if S_cat[i] == "S1" and N_cat[i] == "N2" and not b2_prime]
        notes.append("Warianty bez kategorii bipolarnej (nieporównywalne): " + ", ".join(inc) + "."
                     + (f" Warianty lepsze od „dobrych” i gorsze od „złych” ({', '.join(both)}) — zob. opcje "
                        "b2_prime albo modify (7.5.4)." if both else ""))
    steps.update({"S_category": S_cat, "d_S": S_val, "N_category": N_cat, "d_N": N_val, "mono_rank_S": monoS,
                  "mono_rank_N": monoN, "B_category": B_cat, "position": "classic"})
    return _pack("bipolar", p, level, "pozycja w BIPOLAR-rankingu (mniej = lepiej)", steps, notes)


def _counts_result(method, p, Rel, nd, rn, steps, notes):
    m = p.m
    nz = len(rn) - nd
    dS = [(sum(1 for j in range(nd) if Rel[i][j] == "L") - sum(1 for j in range(nd) if Rel[i][j] == "L-")) / nd
          for i in range(m)]                                                                   # (7.81)–(7.82)
    dN = [(sum(1 for j in range(nd, nd + nz) if Rel[i][j] == "L")
           - sum(1 for j in range(nd, nd + nz) if Rel[i][j] == "L-")) / nz for i in range(m)]
    return _signed_result(method, p, dS, dN, steps, notes, "counts")


def _signed_result(method, p, dS, dN, steps, notes, position):
    sign = lambda x, a, b, c: a if x > _TOL else (c if x < -_TOL else b)
    dSN = [(a + b) / 2 for a, b in zip(dS, dN)]                                                # (7.97)
    steps.update({"d_S": dS, "d_N": dN, "d_SN": dSN,
                  "S_category": [sign(x, "S1", "S2", "S3") for x in dS],
                  "N_category": [sign(x, "N1", "N2", "N3") for x in dN],
                  "B_category": [sign(x, "B1", "B2", "B3") for x in dSN],
                  "mono_rank_S": _competition(dS, True), "mono_rank_N": _competition(dN, True),
                  "position": position})
    level = _competition(dSN, True)
    res = _pack(method, p, level, "d_SN = (d_S + d_N)/2", steps, notes, values=dSN)
    return res


# ---------------------------------------------------------------------------
# BIPOLAR z dominacjami stochastycznymi (7.6)
# ---------------------------------------------------------------------------

def bipolar_sd(p: Problem, risk: str = "DARA", dominances: Optional[List[str]] = None) -> Dict[str, Any]:
    """BIPOLAR z dominacjami stochastycznymi: φ⁺, φ⁻ (7.89)–(7.90) z progami q, p dla wartości oczekiwanych,
    test zgodności c⁺ > c⁻ i niekonfliktowości μ_k ≥ v_k, d⁺ = c⁺ − c⁻ (7.93), d⁻ = c⁻ − c⁺ (7.94),
    d_S, d_N (7.95)–(7.96), d_SN (7.97); kategorie S, N, B wg znaku."""
    from mcdm_cd import Distribution
    from .promethee import _distribution, _dominance_test
    notes: list = []
    w = p.weights(notes=notes)
    m, n = p.m, p.n

    def dist(x, where):
        d = _distribution(x, where)
        return d

    A = [[dist(x, f"{v}, {c.name}") for x, c in zip(r, p.criteria)] for v, r in zip(p.variants, p.values)]
    dn, D = _ref(p, "good", "„dobrych”", dist)
    zn, Z = _ref(p, "bad", "„złych”", dist)

    def orient(rows):
        out = []
        for r in rows:
            out.append([d if c.maximize else Distribution.from_pairs([-x for x in d.values], list(d.probs))
                        for d, c in zip(r, p.criteria)])
        return out
    A, D, Z = orient(A), orient(D), orient(Z)
    R = D + Z
    rn = dn + zn
    nd = len(D)
    q = [(_num(c, "q") or 0.0) for c in p.criteria]
    pp = []
    for c, qk in zip(p.criteria, q):
        x = _num(c, "p")
        if x is None:
            raise ProblemError(f"Kryterium {c.name}: brak progu preferencji p")
        if x <= qk:
            raise ProblemError(f"Kryterium {c.name}: wymagane p > q")
        pp.append(x)
    v = []
    for c in p.criteria:
        x = _num(c, "v")
        v.append(None if x is None else (x if c.maximize else -x))
    allowed, test = _dominance_test(risk, dominances)
    muA = [[d.mean() for d in r] for r in A]
    muR = [[d.mean() for d in r] for r in R]

    def phi(sd, diff, k):                                                                      # (7.89)–(7.90)
        if not sd or diff <= q[k] + _TOL:
            return 0.0
        if diff > pp[k] + _TOL:
            return 1.0
        return (diff - q[k]) / (pp[k] - q[k])
    SDa = [[[test(A[i][k], R[j][k]) for k in range(n)] for j in range(len(R))] for i in range(m)]
    SDr = [[[test(R[j][k], A[i][k]) for k in range(n)] for j in range(len(R))] for i in range(m)]
    Cp, Cm, Dp, Dm = ([[0.0] * len(R) for _ in range(m)] for _ in range(4))
    Pp = [[[0.0] * n for _ in R] for _ in range(m)]
    Pm = [[[0.0] * n for _ in R] for _ in range(m)]
    for i in range(m):
        for j in range(len(R)):
            fp = [phi(SDa[i][j][k], muA[i][k] - muR[j][k], k) for k in range(n)]
            fm = [phi(SDr[i][j][k], muR[j][k] - muA[i][k], k) for k in range(n)]
            Pp[i][j], Pm[i][j] = fp, fm
            cp = sum(w[k] * fp[k] for k in range(n))
            cm = sum(w[k] * fm[k] for k in range(n))
            Cp[i][j], Cm[i][j] = cp, cm
            if cp > cm + _TOL and all(v[k] is None or muA[i][k] >= v[k] - _TOL for k in range(n) if fm[k] > 0):
                Dp[i][j] = cp - cm                                                             # (7.93)
            elif cm > cp + _TOL and all(v[k] is None or muR[j][k] >= v[k] - _TOL for k in range(n) if fp[k] > 0):
                Dm[i][j] = cm - cp                                                             # (7.94)
    dS = [sum(Dp[i][j] - Dm[i][j] for j in range(nd)) / nd for i in range(m)]                 # (7.95)
    dN = [sum(Dp[i][j] - Dm[i][j] for j in range(nd, len(R))) / (len(R) - nd) for i in range(m)]  # (7.96)
    notes.append(f"Dominacje zgodne z funkcją użyteczności decydenta: {', '.join(allowed)}.")
    steps = {"weights": w, "reference_names": rn, "means": muA, "reference_means": muR,
             "dominance_a_r": SDa, "dominance_r_a": SDr, "phi_plus": Pp, "phi_minus": Pm,
             "c_plus": Cp, "c_minus": Cm, "d_plus": Dp, "d_minus": Dm, "q": q, "p": pp, "v": v}
    return _signed_result("bipolar_sd", p, dS, dN, steps, notes, "stochastic")
