"""Dominacje porządkowe (tabl. 1.3-1.4) na przykładach 1.12-1.16."""

from fractions import Fraction

import pytest

from mcdm_ryzyko import Rozklad
from mcdm_ryzyko.dominacje import Relacja as R, porownaj_porzadkowo

SKALA_6 = [1, 2, 3, 4, 5, 6]
SKALA_11 = list(range(11))  # oceny liczbowe 0-10 (tablica 1 przykładów 1.14-1.16)


def _r(skala, prawd):
    return Rozklad(skala, prawd)


def test_przyklad_1_12_ofsd():
    F1 = _r(SKALA_6, ["0", "0,1", "0,2", "0,3", "0,3", "0,1"])
    F2 = _r(SKALA_6, ["0,1", "0,1", "0,3", "0,3", "0,2", "0"])
    assert porownaj_porzadkowo(F1, F2, SKALA_6).najsilniejsza_porzadkowa() is R.OFSD


def test_przyklad_1_13_ossd():
    # brak OFSD (s = 3: 0,6 > 0,5), OSSD spełnione (tablica 3)
    F1 = _r(SKALA_6, ["0", "0,2", "0,4", "0,2", "0,1", "0,1"])
    F2 = _r(SKALA_6, ["0,1", "0,1", "0,3", "0,3", "0,2", "0"])
    w = porownaj_porzadkowo(F1, F2, SKALA_6)
    assert R.OFSD not in w.definicje
    assert w.najsilniejsza_porzadkowa() is R.OSSD


ROZKLAD_1_14 = (
    ["0", "0", "0", "0,2", "0", "0,2", "0,2", "0", "0,2", "0", "0,2"],
    ["0", "0", "0", "0", "0,2", "0,4", "0,2", "0", "0", "0,2", "0"],
)


def test_przyklad_1_14_oafsd():
    # tablica 5: ‖F1 − F2‖ = 1,0, Σ_{S1} = 0,2 — zachodzi OAFSD(0,2)
    F1, F2 = (_r(SKALA_11, p) for p in ROZKLAD_1_14)
    w = porownaj_porzadkowo(F1, F2, SKALA_11)
    assert w.najsilniejsza_porzadkowa() is None
    assert w.eps_afsd == Fraction(1, 5)
    assert w.afsd(0.2)


def test_przyklad_1_15_oassd():
    # tablice 5-6: ‖F1 − F2‖ = 2,2; Σ_{S1} = 0,6 > 0,44 (brak OAFSD(0,2));
    # Σ_{S2} = 0,2 ≤ 0,275 i μ_1 = 3,6 ≥ μ_2 = 2,6 — zachodzi OASSD(0,125)
    F1 = _r(SKALA_11, ["0", "0", "0,8", "0", "0", "0", "0", "0", "0", "0", "0,2"])
    F2 = _r(SKALA_11, ["0", "0,4", "0", "0,2", "0,4", "0", "0", "0", "0", "0", "0"])
    w = porownaj_porzadkowo(F1, F2, SKALA_11)
    assert w.najsilniejsza_porzadkowa() is None
    assert w.eps_afsd == Fraction(6, 22)
    assert not w.afsd(0.2)
    assert w.eps_assd == Fraction(2, 22)
    assert w.assd(0.125)
    assert (w.mu_i, w.mu_j) == (Fraction(18, 5), Fraction(13, 5))


def test_przyklad_1_16_raport_stdom():
    # Przykład 1.16, rysunek 4 (raport StDom): OFSD i OSSD „Nie Zachodzi”,
    # OAFSD „Zachodzi ze stopniem: 0,2”.
    F1, F2 = (_r(SKALA_11, p) for p in ROZKLAD_1_14)
    w = porownaj_porzadkowo(F1, F2, SKALA_11)
    assert w.definicje == frozenset()
    assert w.eps_afsd == Fraction(1, 5)


def test_skala_niepelna_zmienia_wynik():
    # Pominięcie ocen o zerowym prawdopodobieństwie zmienia normę (przykład 1.15).
    F1 = _r([2, 10], ["0,8", "0,2"])
    F2 = _r([1, 3, 4], ["0,4", "0,2", "0,4"])
    pelna = porownaj_porzadkowo(F1, F2, SKALA_11)
    zawezona = porownaj_porzadkowo(F1, F2, [1, 2, 3, 4, 10])
    assert pelna.eps_afsd != zawezona.eps_afsd


def test_wartosc_spoza_skali():
    with pytest.raises(ValueError):
        porownaj_porzadkowo(_r([1, 7], ["1/2", "1/2"]), _r([1], [1]), SKALA_6)
