"""Dominacje stochastyczne (odpowiednik M_Stoch_Dominacje.bas ze StDom i M_Dominacje.bas z MCDM).

Konwencja jak w programach z płyty: X dominuje Y (X jest „lepszy”), gdy dystrybuanta X leży
nie wyżej niż dystrybuanta Y (FSD), odpowiednio dla całek (SSD, TSD). Dla skłonności do ryzyka
(INARA) badane są dominacje odwrotne SISD, TISD1, TISD2 na funkcjach przeżycia P(X >= t).

Kody wyniku (bajt zwracany przez `Dominacje` w VBA):
  128 — rozkłady identyczne,
  DARA: 7 FSD, 6 SSD, 4 TSD, 0 brak;
  INARA: 57 FSD, 56 SISD, 16 TISD1, 32 TISD2, 0 brak.
Bity: 1 FSD, 2 SSD, 4 TSD, 8 SISD, 16 TISD1, 32 TISD2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .distribution import EPS, Distribution

DARA, INARA = "DARA", "INARA"   # awersja do ryzyka / skłonność do ryzyka

BIT = {"FSD": 1, "SSD": 2, "TSD": 4, "SISD": 8, "TISD1": 16, "TISD2": 32}
IDENTICAL = 128


def _grid(x: Distribution, y: Distribution) -> List[float]:
    return sorted(set(x.values) | set(y.values))


def _insert_zero_crossings(xs: List[float], hs: List[float]) -> Tuple[List[float], List[float]]:
    """Wstawia punkty, w których funkcja kawałkami liniowa (xs, hs) zmienia znak."""
    ox, oh = [xs[0]], [hs[0]]
    for i in range(1, len(xs)):
        a, b = hs[i - 1], hs[i]
        if (a > 0 and b < 0) or (a < 0 and b > 0):
            ox.append(xs[i - 1] + a / (a - b) * (xs[i] - xs[i - 1]))
            oh.append(0.0)
        ox.append(xs[i])
        oh.append(b)
    return ox, oh


def _trapz_left(xs, hs):
    out = [0.0]
    for i in range(1, len(xs)):
        out.append(out[-1] + 0.5 * (hs[i] + hs[i - 1]) * (xs[i] - xs[i - 1]))
    return out


def _trapz_right(xs, hs):
    out = [0.0] * len(xs)
    for i in range(len(xs) - 2, -1, -1):
        out[i] = out[i + 1] + 0.5 * (hs[i] + hs[i + 1]) * (xs[i + 1] - xs[i])
    return out


@dataclass
class DominanceResult:
    code: int                      # kod jak w VBA (z kaskadą: zwracany jest pierwszy spełniony stopień)
    risk: str
    holds: dict = field(default_factory=dict)   # każdy warunek sprawdzony niezależnie
    grid: List[float] = field(default_factory=list)
    cdf_x: List[float] = field(default_factory=list)
    cdf_y: List[float] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return self.code == IDENTICAL

    def flag(self, name: str) -> bool:
        """Czy dominacja `name` jest zgłaszana w raporcie StDom (bit w kodzie)."""
        return self.code != IDENTICAL and bool(self.code & BIT[name])

    def strongest(self) -> Optional[str]:
        for n in ("FSD", "SSD", "TSD", "SISD", "TISD1", "TISD2"):
            if self.flag(n):
                return n
        return None


def stochastic_dominance(x: Distribution, y: Distribution, risk: str = DARA, *,
                         tsd_mean_condition: bool = False) -> DominanceResult:
    """Bada, czy X dominuje Y.

    tsd_mean_condition=True dodaje do TSD warunek E[X] >= E[Y] (definicja Whitmore'a);
    programy z płyty go nie sprawdzają (całki tylko do największej wartości siatki).
    """
    g = _grid(x, y)
    fx = [x.cdf(t) for t in g]
    fy = [y.cdf(t) for t in g]
    h1 = [a - b for a, b in zip(fx, fy)]
    res = DominanceResult(0, risk, {}, g, fx, fy)
    if all(abs(h) <= 1e-12 for h in h1):
        res.code = IDENTICAL
        return res

    fsd = all(h <= EPS for h in h1)
    res.holds["FSD"] = fsd

    if risk == DARA:
        # H2(x_i) = ∫_{x_1}^{x_i} (F_X - F_Y)
        h2 = [0.0]
        for i in range(1, len(g)):
            h2.append(h2[-1] + h1[i - 1] * (g[i] - g[i - 1]))
        ssd = all(h <= EPS for h in h2)
        xs, hs = _insert_zero_crossings(g, h2)
        h3 = _trapz_left(xs, hs)
        tsd = all(h <= EPS for h in h3)
        if tsd_mean_condition:
            tsd = tsd and x.mean() >= y.mean() - EPS
        res.holds.update(SSD=ssd, TSD=tsd)
        res.code = 7 if fsd else 6 if ssd else 4 if tsd else 0
        return res

    if risk != INARA:
        raise ValueError("risk musi być DARA albo INARA")
    sx = [x.survival(t) for t in g]
    sy = [y.survival(t) for t in g]
    # H2'(x_i) = ∫_{x_i}^{x_n} (S_X - S_Y); na (x_{i}, x_{i+1}] S(t) = S(x_{i+1})
    n = len(g)
    h2r = [0.0] * n
    for i in range(n - 2, -1, -1):
        h2r[i] = h2r[i + 1] + (sx[i + 1] - sy[i + 1]) * (g[i + 1] - g[i])
    sisd = all(h >= -EPS for h in h2r)
    xs, hs = _insert_zero_crossings(g, h2r)
    tisd1 = all(h >= -EPS for h in _trapz_left(xs, hs))
    tisd2 = all(h >= -EPS for h in _trapz_right(xs, hs))
    res.holds.update(SISD=sisd, TISD1=tisd1, TISD2=tisd2)
    res.code = 57 if fsd else 56 if sisd else 16 if tisd1 else 32 if tisd2 else 0
    return res


def afsd(x: Distribution, y: Distribution) -> Optional[float]:
    """Stopień ε prawie pierwszej dominacji (AFSD, Leshno–Levy) X nad Y.

    ε = ∫_{F_X > F_Y} (F_X - F_Y) / ∫ |F_X - F_Y|; None dla rozkładów identycznych (VBA: -1).
    Zależność zachodzi „ze stopniem ε”, gdy 0 <= ε <= 0,5 (tak raportuje StDom).
    """
    g = _grid(x, y)
    num = den = 0.0
    for i in range(len(g) - 1):
        h = x.cdf(g[i]) - y.cdf(g[i])
        dx = g[i + 1] - g[i]
        den += abs(h) * dx
        if h > EPS:
            num += h * dx
    if den == 0:
        return None
    return num / den


def afsd_mcdm(x: Distribution, y: Distribution) -> float:
    """Wariant z MCDM (M_Dominacje.AFSD): ε, gdy ε < 0,5, w przeciwnym razie 0; 0 także dla identycznych."""
    e = afsd(x, y)
    if e is None or e >= 0.5:
        return 0.0
    return e


def assd(x: Distribution, y: Distribution) -> Optional[float]:
    """Stopień ε prawie drugiej dominacji (ASSD) X nad Y, wg StDom 1.09b.

    Liczony tylko gdy E[X] >= E[Y]: ε = Σ_{i: H2(x_{i+1}) > 0} H1(x_i)Δx_i / Σ |H1(x_i)|Δx_i,
    gdzie H1 = F_X - F_Y, H2 = ∫H1. None, gdy E[X] < E[Y] lub rozkłady identyczne (VBA: -1).
    """
    g = _grid(x, y)
    if x.mean() < y.mean():
        return None
    num = den = 0.0
    h2 = 0.0
    nonzero = False
    for i in range(len(g) - 1):
        h1 = x.cdf(g[i]) - y.cdf(g[i])
        dx = g[i + 1] - g[i]
        h2 += h1 * dx
        den += abs(h1) * dx
        nonzero = nonzero or h1 != 0
        if h2 > EPS:
            num += h1 * dx
    if not nonzero or den <= 0:
        return None
    return num / den


# ---------------------------------------------------------------------------
# Raport StDom (kaskada wierszy jak w Wyniki / Wyniki_O)
# ---------------------------------------------------------------------------

def stdom_report(x: Distribution, y: Distribution, risk: str = DARA, *, almost: bool = False,
                 almost_second: bool = False, ordinal: bool = False,
                 vba_param_quirk: bool = True, cascade: bool = True) -> List[Tuple[str, object]]:
    """Wiersze raportu StDom: lista (etykieta, wynik), wynik: True/False albo stopień ε (float).

    ordinal=True — „Porządkowe dominacje stochastyczne” (OFSD, OSSD, OAFSD, OASSD; zawsze DARA).
    cascade=False — układ raportów wklejonych do arkuszy przykładów 5.19, 6.13, 6.15 (starsza wersja
    StDom): wypisane wszystkie dominacje dla danego stosunku do ryzyka, także wynikające z silniejszej
    (FSD ⇒ SSD ⇒ TSD; FSD ⇒ SISD ⇒ TISD1, TISD2), bez wierszy AFSD.
    vba_param_quirk=True odtwarza błąd StDom: obliczenia DARA są wybierane tylko dla Param == 7,
    więc zaznaczenie AFSD (Param = 263) lub OAFSD/OASSD przełącza obliczenia na INARA.
    """
    if ordinal:
        risk = DARA
    param = (7 if risk == DARA else 57) | (256 if almost or almost_second else 0) \
        | (512 if ordinal and almost_second else 0)
    calc_risk = DARA if risk == DARA and (param == 7 or not vba_param_quirk) else INARA
    r = stochastic_dominance(x, y, calc_risk)
    if r.identical:
        return [("IDENTICAL", True)]
    eps1 = afsd(x, y) if param & 256 else None
    eps2 = assd(x, y) if param & 512 else None
    pre = "O" if ordinal else ""
    out: List[Tuple[str, object]] = []
    if not cascade:
        names = ("FSD", "SSD", "TSD") if calc_risk == DARA else ("FSD", "SISD", "TISD1", "TISD2")
        return [(n, r.flag(n)) for n in names]

    def almost_line(name, e, upper):
        ok = e is not None and e >= 0 and (upper is None or e <= upper)
        out.append((pre + name, e if ok else False))

    if not param & 1:
        return out
    out.append((pre + "FSD", r.flag("FSD")))
    if r.flag("FSD"):
        return out
    if param & 2:
        out.append((pre + "SSD", r.flag("SSD")))
        if not r.flag("SSD"):
            if ordinal:
                if param & 256:
                    almost_line("AFSD", eps1, 0.5)
                if param & 512:
                    almost_line("ASSD", eps2, None)
                return out
            if param & 4:
                out.append(("TSD", r.flag("TSD")))
                if not r.flag("TSD") and param & 256:
                    almost_line("AFSD", eps1, 0.5)
    if ordinal:
        return out
    if param & 8:
        out.append(("SISD", r.flag("SISD")))
        if not r.flag("SISD") and param & 16:
            out.append(("TISD1", r.flag("TISD1")))
            if not r.flag("TISD1") and param & 32:
                out.append(("TISD2", r.flag("TISD2")))
                if not r.flag("TISD2") and param & 256:
                    almost_line("AFSD", eps1, 0.5)
    return out
