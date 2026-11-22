"""Dominacje stochastyczne dla kryteriów kardynalnych (tabl. 1.1).

Porównujemy rozkład F_i z rozkładem F_j na wspólnym przedziale [a, b],
gdzie a i b to najmniejsza i największa wartość z sumy nośników. Niech
z_0 < … < z_n będą wszystkimi wartościami obu rozkładów. Wtedy:

* η⁽¹⁾(x) = F_i(x) − F_j(x) jest stała na [z_t, z_{t+1}) (wzór 1.21),
* η⁽²⁾(x) = ∫_a^x η⁽¹⁾ i η⁽³⁾(x) = ∫_a^x η⁽²⁾ (wzory 1.22, 1.23),
* η̄⁽¹⁾(x) = F̄_i(x) − F̄_j(x), gdzie F̄(x) = P(X ≥ x), jest stała na
  (z_t, z_{t+1}] (wzór 1.24),
* η̄⁽²⁾(x) = ∫_x^b η̄⁽¹⁾ (SISD, 1.24), η̄⁽³⁾ = ∫_a^x η̄⁽²⁾ (TISD1, 1.25)
  albo η̄⁽³⁾ = ∫_x^b η̄⁽²⁾ (TISD2, 1.26).

Każda definicja wymaga ponadto, by rozkłady były różne (∃x: F_i(x) ≠ F_j(x)).
Wartości punktowe w węzłach nie wpływają na całki, więc stałość „na odcinku
domkniętym z lewej albo z prawej” nie ma znaczenia dla warunków ≤ 0 i ≥ 0
poza samą η⁽¹⁾, dla której sprawdzamy wartości na wszystkich odcinkach.

Wszystkie porównania z zerem odbywają się z tolerancją (domyślnie 1e-6,
dokładność porównań programu StDom, instrukcja rozdz. 3.6).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rozklad import Rozklad
from .funkcje import FunkcjaOdcinkowa
from .relacje import Relacja

TOLERANCJA = 1e-6


@dataclass(frozen=True)
class FunkcjeEta:
    """Funkcje η z tabl. 1.1 dla pary (F_i, F_j) na wspólnej siatce wartości."""

    wezly: tuple
    eta1: FunkcjaOdcinkowa
    eta2: FunkcjaOdcinkowa
    eta3: FunkcjaOdcinkowa
    eta1_bar: FunkcjaOdcinkowa
    eta2_bar: FunkcjaOdcinkowa
    eta3_bar_tisd1: FunkcjaOdcinkowa
    eta3_bar_tisd2: FunkcjaOdcinkowa


def funkcje_eta(Fi: Rozklad, Fj: Rozklad) -> FunkcjeEta:
    """Wyznacza funkcje η⁽¹⁾…η⁽³⁾ i η̄⁽¹⁾…η̄⁽³⁾ dla F_i względem F_j."""
    z = Fi.nosnik_wspolny(Fj)
    roznice = [Fi.dystrybuanta(z[t]) - Fj.dystrybuanta(z[t]) for t in range(len(z) - 1)]
    eta1 = FunkcjaOdcinkowa.schodkowa(z, roznice)
    eta2 = eta1.calka_od_lewej()
    eta3 = eta2.calka_od_lewej()
    # Na (z_t, z_{t+1}] mamy F̄(x) = 1 − F(z_t), więc η̄⁽¹⁾ = −η⁽¹⁾ na tym odcinku.
    eta1_bar = FunkcjaOdcinkowa.schodkowa(z, [-d for d in roznice])
    eta2_bar = eta1_bar.calka_od_prawej()
    return FunkcjeEta(
        wezly=z,
        eta1=eta1,
        eta2=eta2,
        eta3=eta3,
        eta1_bar=eta1_bar,
        eta2_bar=eta2_bar,
        eta3_bar_tisd1=eta2_bar.calka_od_lewej(),
        eta3_bar_tisd2=eta2_bar.calka_od_prawej(),
    )


def _rozne(e: FunkcjeEta, tol: float) -> bool:
    return any(abs(c0) > tol for c0, _, _ in e.eta1.wsp)


def relacje_kardynalne(Fi: Rozklad, Fj: Rozklad, tolerancja: float = TOLERANCJA) -> frozenset:
    """Zbiór relacji z tabl. 1.1, których definicje spełnia F_i względem F_j.

    Warunek μ_i ≥ μ_j z twierdzeń 1.6, 1.8, 1.9 nie jest tu sprawdzany
    (zob. :meth:`WynikPorownania.zachodzi`).
    """
    e = funkcje_eta(Fi, Fj)
    if not _rozne(e, tolerancja):
        return frozenset()
    tol = tolerancja
    wynik = set()
    if e.eta1.maksimum() <= tol:
        wynik.add(Relacja.FSD)
    if e.eta2.maksimum() <= tol:
        wynik.add(Relacja.SSD)
    if e.eta3.maksimum() <= tol:
        wynik.add(Relacja.TSD)
    if e.eta2_bar.minimum() >= -tol:
        wynik.add(Relacja.SISD)
    if e.eta3_bar_tisd1.minimum() >= -tol:
        wynik.add(Relacja.TISD1)
    if e.eta3_bar_tisd2.minimum() >= -tol:
        wynik.add(Relacja.TISD2)
    return frozenset(wynik)
