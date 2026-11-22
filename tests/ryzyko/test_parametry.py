from fractions import Fraction

import pytest

from mcdm_ryzyko import Parametr, RodzajParametru as R
from dane_testowe import wczytaj

DANE = wczytaj("przyklad_8_1")
ROZKLADY = DANE["rozklady"]
WSZYSTKIE = range(10)


def _kolumna(param, k, indeksy):
    return [param.wartosc(ROZKLADY[i][k]) for i in indeksy]


def _indeksy(numery):
    return [n - 1 for n in numery]


def test_kierunki_domyslne():
    assert Parametr(R.WARTOSC_OCZEKIWANA).wyzsze_lepsze is True
    assert Parametr(R.ODCHYLENIE_STD).wyzsze_lepsze is False
    assert Parametr(R.P_NIE_WIECEJ, 3).wyzsze_lepsze is False


def test_gorne_semiodchylenie_wymaga_kierunku():
    with pytest.raises(ValueError):
        Parametr(R.SEMIODCHYLENIE_STD_GORNE)
    assert Parametr(R.SEMIODCHYLENIE_STD_GORNE, wyzsze_lepsze=True).wyzsze_lepsze is True


def test_prawdopodobienstwo_wymaga_progu():
    with pytest.raises(ValueError):
        Parametr(R.P_NIE_MNIEJ)


def test_macierz_mozliwosci_P1_przyklad_8_3():
    # Przykład 8.3, tablica 9 (i przykład 8.4, rysunek 2): wartości
    # pesymistyczne i optymistyczne μ_ik oraz P{f_i1 ≥ 6} w zbiorze A^(1).
    mu = Parametr(R.WARTOSC_OCZEKIWANA)
    p6 = Parametr(R.P_NIE_MNIEJ, 6)
    kol = _kolumna(p6, 0, WSZYSTKIE)
    assert (p6.pesymistyczna(kol), p6.optymistyczna(kol)) == (0, 1)
    pes = [round(float(mu.pesymistyczna(_kolumna(mu, k, WSZYSTKIE))), 2) for k in range(4)]
    opt = [round(float(mu.optymistyczna(_kolumna(mu, k, WSZYSTKIE))), 2) for k in range(4)]
    assert pes == [2.86, 1.86, 2.29, 4.29]
    assert opt == [8.14, 8.43, 8.43, 9.00]


def test_warunek_P_f1_ge_6_przyklad_8_3():
    # Przykład 8.3, iteracja 1, krok 5: warunek P{f_i1 ≥ 6} ≥ 0,5 spełniają
    # a2, a3, a4, a5, a9; tablica 10: pesymistyczna wartość P = 0,57 (4/7).
    p6 = Parametr(R.P_NIE_MNIEJ, 6)
    spelnia = [i + 1 for i in WSZYSTKIE if p6.wartosc(ROZKLADY[i][0]) >= Fraction(1, 2)]
    assert spelnia == [2, 3, 4, 5, 9]
    assert p6.pesymistyczna(_kolumna(p6, 0, _indeksy(spelnia))) == Fraction(4, 7)


def test_warunek_P_f2_ge_5_przyklad_8_3_i_8_4():
    # Przykład 8.4, rysunek 10: pesymistyczna wartość P{X2 ≥ 5} w zbiorze
    # {a2, a3, a4, a5, a9} wynosi 0,28571429 (= 2/7). W tablicy 11 przykładu
    # 8.3 wydrukowano 0,57 (ROZBIEZNOSCI.md).
    p5 = Parametr(R.P_NIE_MNIEJ, 5)
    a2 = _indeksy([2, 3, 4, 5, 9])
    assert p5.pesymistyczna(_kolumna(p5, 1, a2)) == Fraction(2, 7)
    # Krok 5 iteracji 2: warunek P{f_i2 ≥ 5} ≥ 0,65 daje A^(3) = {a4, a5, a9}.
    a3 = [i + 1 for i in a2 if p5.wartosc(ROZKLADY[i][1]) >= Fraction(65, 100)]
    assert a3 == [4, 5, 9]
    # Tablica 12: pesymistyczna P{f_i2 ≥ 5} w A^(3) = 0,71.
    assert round(float(p5.pesymistyczna(_kolumna(p5, 1, _indeksy(a3)))), 2) == 0.71


def test_macierz_rozwiazan_R3_przyklad_8_3():
    # Przykład 8.3, tablica 14 (i przykład 8.4, rysunek 18): macierz R^(3).
    mu = Parametr(R.WARTOSC_OCZEKIWANA)
    p75 = Parametr(R.P_NIE_MNIEJ, 7.5)
    oczekiwane = {
        4: [8.14, 6.57, 7.86, 0.71, 4.29],
        5: [6.71, 7.00, 3.29, 0.00, 8.00],
        9: [6.43, 5.86, 5.00, 0.00, 6.00],
    }
    for n, wiersz in oczekiwane.items():
        r = ROZKLADY[n - 1]
        policzone = [mu.wartosc(r[0]), mu.wartosc(r[1]), mu.wartosc(r[2]), p75.wartosc(r[2]), mu.wartosc(r[3])]
        assert [round(float(v), 2) for v in policzone] == wiersz
