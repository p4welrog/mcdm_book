"""Dyskretne rozkłady prawdopodobieństwa i ich parametry (odpowiednik M_Util.bas z MCDM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Iterable, Sequence

EPS = 1e-6  # tolerancja numeryczna (dEPS w VBA)


@dataclass(frozen=True)
class Distribution:
    """Rozkład dyskretny: wartości rosnąco, bez powtórzeń, z dodatnimi prawdopodobieństwami.

    Wejście może mieć powtórzone wartości (prawdopodobieństwa się sumują) i punkty o zerowym
    prawdopodobieństwie (np. wypełnienie zerami z plików .mcf) — są pomijane.
    """
    values: tuple
    probs: tuple
    raw: tuple = field(default=(), compare=False, repr=False)  # pary (v, p) jak na wejściu — dla vba_compat

    @classmethod
    def from_pairs(cls, values: Sequence[float], probs: Sequence[float], *, check_sum: bool = True,
                   keep_zero: bool = False) -> "Distribution":
        if len(values) != len(probs):
            raise ValueError("Niezgodna liczba wartości i prawdopodobieństw")
        acc: dict = {}
        for v, p in zip(values, probs):
            v, p = float(v), float(p)
            if p < 0:
                raise ValueError(f"Ujemne prawdopodobieństwo {p}")
            if p == 0 and not keep_zero:
                continue
            acc[v] = acc.get(v, 0.0) + p
        if check_sum and abs(sum(acc.values()) - 1.0) > EPS:
            raise ValueError(f"Prawdopodobieństwa sumują się do {sum(acc.values())}, a nie do 1")
        vs = tuple(sorted(acc))
        raw = tuple((float(v), float(p)) for v, p in zip(values, probs))
        while raw and raw[-1] == (0.0, 0.0):   # obcięcie wypełnienia jak i_MaxO w VBA
            raw = raw[:-1]
        return cls(vs, tuple(acc[v] for v in vs), raw)

    @classmethod
    def from_observations(cls, obs: Iterable[float]) -> "Distribution":
        """Rozkład empiryczny z obserwacji (jak „Obserwacje” w formatce MCDM)."""
        obs = [float(o) for o in obs]
        if not obs:
            raise ValueError("Brak obserwacji")
        return cls.from_pairs(obs, [1.0 / len(obs)] * len(obs))

    def __iter__(self):
        return iter(zip(self.values, self.probs))

    def __len__(self):
        return len(self.values)

    # ---- funkcje rozkładu ----
    def cdf(self, t: float) -> float:
        """F(t) = P(X <= t)."""
        return sum(p for v, p in self if v <= t)

    def survival(self, t: float) -> float:
        """P(X >= t)."""
        return sum(p for v, p in self if v >= t)

    # ---- parametry (numeracja jak w MCDM: 1..11) ----
    def mean(self) -> float:
        return sum(v * p for v, p in self)

    def std(self) -> float:
        m = self.mean()
        return sqrt(sum((v - m) ** 2 * p for v, p in self))

    def lower_semi_std(self, psi: float) -> float:
        """Dolne semiodchylenie standardowe od wartości psi."""
        return sqrt(sum((psi - v) ** 2 * p for v, p in self if v < psi))

    def upper_semi_std(self, psi: float) -> float:
        return sqrt(sum((v - psi) ** 2 * p for v, p in self if v > psi))

    def lower_semi_mad(self, psi: float) -> float:
        """Dolne semiodchylenie przeciętne od wartości psi."""
        return sum((psi - v) * p for v, p in self if v < psi)

    def upper_semi_mad(self, psi: float) -> float:
        return sum((v - psi) * p for v, p in self if v > psi)

    def prob_le(self, psi: float) -> float:
        return self.cdf(psi)

    def prob_ge(self, psi: float) -> float:
        return self.survival(psi)

    def quantile(self, q: float) -> float:
        """Kwantyl: najmniejsze x z F(x) >= q; przy F(x) == q dokładnie — średnia z x i następnej wartości."""
        c = 0.0
        for i, (v, p) in enumerate(self):
            c += p
            if abs(c - q) <= EPS and i + 1 < len(self):
                return (v + self.values[i + 1]) / 2
            if c >= q - EPS:
                return v
        return self.values[-1]

    def median(self) -> float:
        return self.quantile(0.5)


# Numeracja parametrów jak w klasie C_Kryterium (a_Parametry(1..11))
PARAMS = {
    1: ("Wart śr", "wartość oczekiwana", False),
    2: ("Odchyl st", "odchylenie standardowe", False),
    3: ("D semiodch st", "dolne semiodchylenie standardowe od wartości", True),
    4: ("G semiodch st", "górne semiodchylenie standardowe od wartości", True),
    5: ("D semiodch p", "dolne semiodchylenie przeciętne od wartości", True),
    6: ("G semiodch p", "górne semiodchylenie przeciętne od wartości", True),
    7: ("Pr{X <= Psi}", "prawdopodobieństwo uzyskania wartości nie wyższej niż", True),
    8: ("Pr{X >= Psi}", "prawdopodobieństwo uzyskania wartości nie niższej niż", True),
    9: ("Mediana", "mediana", False),
    10: ("I Kwrt", "pierwszy kwartyl", False),
    11: ("III Kwrt", "trzeci kwartyl", False),
}
LOCATION = (1, 9, 10, 11)   # im więcej, tym lepiej (dla kryterium maksymalizowanego)
DISPERSION = (2, 3, 4, 5, 6)  # im mniej, tym lepiej (niezależnie od kierunku kryterium)


def parameter(d: Distribution, p: int, psi: float | None = None, *, vba_compat: bool = False) -> float:
    """Wartość parametru nr p rozkładu d.

    vba_compat=True odtwarza zachowanie MCDM 1.00:
      * odchylenie standardowe liczone względem v_n·p_n ostatniego punktu zamiast średniej
        (literówka `dz` zamiast `d_z` w Oblicz_os),
      * mediana = środkowa *pozycja* na liście wartości wejściowych (bez wag, z punktami
        o zerowym prawdopodobieństwie, bez końcowego wypełnienia (0, 0)),
      * kwartyle zawsze = 1 (funkcje Oblicz_pk/Oblicz_tk niezaimplementowane).
    """
    if PARAMS[p][2] and psi is None:
        raise ValueError(f"Parametr {p} wymaga wartości psi")
    if p == 1:
        return d.mean()
    if p == 2:
        if vba_compat:
            raw = d.raw or tuple(d)
            z = raw[-1][0] * raw[-1][1]
            return sqrt(sum((v - z) ** 2 * q for v, q in raw))
        return d.std()
    if p == 3:
        return d.lower_semi_std(psi)
    if p == 4:
        return d.upper_semi_std(psi)
    if p == 5:
        return d.lower_semi_mad(psi)
    if p == 6:
        return d.upper_semi_mad(psi)
    if p == 7:
        return d.prob_le(psi)
    if p == 8:
        return d.prob_ge(psi)
    if p == 9:
        if vba_compat:
            vals = [v for v, _ in (d.raw or tuple(d))]
            n = len(vals)
            return (vals[n // 2 - 1] + vals[n // 2]) / 2 if n % 2 == 0 else vals[n // 2]
        return d.median()
    if p == 10:
        return 1.0 if vba_compat else d.quantile(0.25)
    if p == 11:
        return 1.0 if vba_compat else d.quantile(0.75)
    raise ValueError(f"Nieznany parametr {p}")


def better(p: int, maximize: bool) -> int:
    """+1 gdy dla parametru p większa wartość jest lepsza, -1 gdy mniejsza."""
    if p in LOCATION or p == 8:
        return 1 if maximize else -1
    if p == 7:
        return -1 if maximize else 1
    return -1  # miary rozproszenia
