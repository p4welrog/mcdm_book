"""INSDECM (rozdz. 8.4) na przykładach 8.3, 8.4, rozdz. 10.5 i przypadkach niespójności."""

from fractions import Fraction

import pytest

from mcdm_ryzyko import Problem, Rozklad
from mcdm_ryzyko.dialog import BlednaOdpowiedz, Sesja, uruchom
from mcdm_ryzyko.dominacje import Relacja as R
from mcdm_ryzyko.dominacje.regula import RegulaDominacji
from mcdm_ryzyko.insdecm import (
    OSLAB, PODTRZYMAJ, ZAOSTRZ, Insdecm, PytanieAkceptacjaZmian, PytanieDaneWystarczajace,
    PytanieNiespojnosc, PytanieParametry, PytaniePesymistyczne, PytaniePropozycja,
    PytanieRozwiazanie, PytanieWarunek, Warunek, ZmianaPrezentacji, eps_niespojnosci,
    macierz_mozliwosci, prezentacja_rozkladow, propozycje_modyfikacji, zbior_niespojnosci,
)
from mcdm_ryzyko.parametry import Parametr, RodzajParametru as RP
from dane_testowe import rozdzial_10, wczytaj

MU = Parametr(RP.WARTOSC_OCZEKIWANA)
MIN = Parametr(RP.MINIMUM)


def P_ge(s):
    return Parametr(RP.P_NIE_MNIEJ, s)


def _pm(P, nd=2):
    return [(round(float(a), nd), round(float(b), nd)) for a, b in zip(P.pesymistyczne, P.optymistyczne)]


D81 = wczytaj("przyklad_8_1")
P81 = Problem(D81["kryteria"], D81["warianty"], D81["rozklady"])
REGULA_81 = RegulaDominacji.awersja()


# --- przykład 8.3 / 8.4 -----------------------------------------------------------

def test_przyklad_8_3_przebieg():
    s = Sesja(Insdecm(P81, REGULA_81).przebieg())
    assert isinstance(s.pytanie, PytanieParametry)
    s.odpowiedz({0: [MU, P_ge(6)]})  # pozostałe kryteria: wartość oczekiwana
    # iteracja 1, tablica 9
    assert isinstance(s.pytanie, PytanieDaneWystarczajace)
    assert _pm(s.pytanie.macierz) == [(2.86, 8.14), (0.00, 1.00), (1.86, 8.43), (2.29, 8.43), (4.29, 9.00)]
    s.odpowiedz(True)
    assert isinstance(s.pytanie, PytaniePesymistyczne)
    s.odpowiedz(False)
    assert isinstance(s.pytanie, PytanieWarunek)
    s.odpowiedz(Warunek(0, P_ge(6), Fraction(1, 2)))
    # krok 5-6: 𝒜^(2) = {a2, a3, a4, a5, a9}, tablica 10
    assert isinstance(s.pytanie, PytanieAkceptacjaZmian)
    assert s.pytanie.po.warianty == (1, 2, 3, 4, 8)
    assert _pm(s.pytanie.po) == [(6.29, 8.14), (0.57, 1.00), (3.00, 7.00), (2.29, 8.43), (4.29, 8.57)]
    s.odpowiedz(True)  # 𝒩^(1) = ∅ — od razu iteracja 2
    assert isinstance(s.pytanie, PytanieDaneWystarczajace) and s.pytanie.iteracja == 2
    s.odpowiedz(False)
    s.odpowiedz({1: [MU, P_ge(5)]})
    # tablica 11 (pesymistyczna P{f2 ≥ 5} = 2/7, w druku 0,57 — ROZBIEZNOSCI.md)
    assert _pm(s.pytanie.macierz) == [(6.29, 8.14), (3.00, 7.00), (0.29, 1.00), (2.29, 8.43), (4.29, 8.57)]
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz(Warunek(1, P_ge(5), Fraction(65, 100)))
    assert s.pytanie.po.warianty == (3, 4, 8)  # 𝒜^(3) = {a4, a5, a9}
    # tablica 12
    assert _pm(s.pytanie.po) == [(6.43, 8.14), (5.86, 7.00), (0.71, 1.00), (3.29, 7.86), (4.29, 8.00)]
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz({2: [MU, P_ge(7.5)]})
    # tablica 13
    assert _pm(s.pytanie.macierz) == [(6.43, 8.14), (5.86, 7.00), (3.29, 7.86), (0.00, 0.71), (4.29, 8.00)]
    s.odpowiedz(True)
    s.odpowiedz(True)
    # tablica 14: macierz R^(3)
    assert isinstance(s.pytanie, PytanieRozwiazanie)
    R3 = s.pytanie.macierz
    assert R3.warianty == (3, 4, 8)
    assert [[round(float(v), 2) for v in w] for w in R3.wiersze] == [
        [8.14, 6.57, 7.86, 0.71, 4.29], [6.71, 7.00, 3.29, 0.00, 8.00], [6.43, 5.86, 5.00, 0.00, 6.00]]
    s.odpowiedz(3)
    w = s.wynik
    assert (w.status, w.rozwiazanie, w.warianty) == ("zaakceptowano", 3, (3, 4, 8))
    assert [h.niespojnosci for h in w.historia] == [(), ()]
    assert len(w.warunki) == 2


def test_przyklad_8_4_raport_programu():
    # Przykład 8.4, rysunek 7: P(2) z pełną precyzją arkusza
    P2 = macierz_mozliwosci(P81, {0: [MU, P_ge(6)], 1: [MU], 2: [MU], 3: [MU]}, (1, 2, 3, 4, 8))
    assert [float(x) for x in P2.pesymistyczne] == pytest.approx([6.28571429, 0.57142857, 3, 2.28571429, 4.28571429], abs=1e-8)
    assert [float(x) for x in P2.optymistyczne] == pytest.approx([8.14285714, 1, 7, 8.42857143, 8.57142857], abs=1e-8)


# --- rozdz. 10.5 ---------------------------------------------------------------------

T10 = rozdzial_10()
P10 = Problem(T10["kryteria"], [f"a{i}" for i in range(1, 15)],
              [[T10["rozklady"][k][i] for k in T10["kryteria"]] for i in range(14)])
REGULA_10 = RegulaDominacji(relacje=(R.FSD, R.SSD), afsd=False)


def test_rozdzial_10_macierz_P1():
    # Tablica 10.8 (μ dla f1, f2 z dokładnością do różnic opisanych przy R10.5).
    P1 = macierz_mozliwosci(P10, {0: [MU, P_ge(485)], 1: [MU], 2: [MIN], 3: [MIN], 4: [MIN], 5: [MIN]}, range(14))
    pm = _pm(P1)
    assert pm[0] == pytest.approx((435.36, 494.95), abs=0.025)
    assert pm[2] == pytest.approx((-515.59, -297.17), abs=0.025)
    assert pm[3:] == [(-58.0, -24.0), (-46.0, -25.5), (-44.0, -13.0), (16.0, 43.5)]
    # P{ξ_i1 ≥ 485}: w druku 0,00 i 0,87; z R10.3 0,00 i 0,887 (ROZBIEZNOSCI.md)
    assert pm[1] == (0.0, 0.89)


def test_rozdzial_10_warunek_485_w_druku_nieodtwarzalny():
    # Warunek P{ξ_i1 ≥ 485} ≥ 0,7 według R10.3 spełniają tylko a4 i a9;
    # druk podaje 𝒜^(2) z 10 portfelami (ROZBIEZNOSCI.md).
    w = Warunek(0, P_ge(485), Fraction(7, 10))
    assert [i + 1 for i in range(14) if w.spelnia(P_ge(485).wartosc(P10.zorientowana(i, 0)))] == [4, 9]


def test_rozdzial_10_przebieg():
    # Pierwszy warunek zastąpiony przez P{ξ_i1 ≥ 470} ≥ 0,7, który daje 𝒜^(2) z druku
    # (ROZBIEZNOSCI.md); dalsze warunki — jak w rozdz. 10.5.
    par = {0: [MU, P_ge(485)], 1: [MU], 2: [MIN], 3: [MIN], 4: [MIN], 5: [MIN]}
    s = Sesja(Insdecm(P10, REGULA_10).przebieg())
    s.odpowiedz(par)
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz(Warunek(0, P_ge(470), Fraction(7, 10)))
    assert [i + 1 for i in s.pytanie.po.warianty] == [1, 3, 4, 5, 6, 8, 9, 10, 12, 14]
    # tablica 10.9 (bez kolumny P{ξ_i1 ≥ 485})
    pm = _pm(s.pytanie.po)
    assert pm[0] == pytest.approx((482.01, 494.95), abs=0.025)
    assert pm[2] == pytest.approx((-515.59, -333.60), abs=0.025)
    assert pm[3:] == [(-47.67, -24.0), (-45.67, -25.5), (-44.0, -18.0), (16.0, 43.5)]
    s.odpowiedz(True)  # brak niespójności (jak w druku)
    # iteracja 2: tablica 10.10
    s.odpowiedz(False)
    s.odpowiedz({0: [MU], 1: [MU, P_ge(-430)], 2: [MIN], 3: [MIN], 4: [MIN], 5: [MIN]})
    assert _pm(s.pytanie.macierz)[2] == (0.0, 1.0)
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz(Warunek(1, P_ge(-430), Fraction(6, 10)))
    assert [i + 1 for i in s.pytanie.po.warianty] == [1, 3, 6, 8, 10, 12]
    # tablica 10.11 (pesymistyczna P{ξ_i2 ≥ −430}: w druku 0,62, z R10.4 0,652 — ROZBIEZNOSCI.md)
    pm = _pm(s.pytanie.po)
    assert pm[0] == pytest.approx((483.63, 491.92), abs=0.025)
    assert pm[1] == pytest.approx((-428.20, -333.60), abs=0.025)
    assert pm[2] == (0.65, 1.0)
    assert pm[3:] == [(-45.5, -24.0), (-44.0, -25.5), (-44.0, -18.0), (16.0, 43.5)]
    s.odpowiedz(True)
    # iteracja 3: warunek P(ξ_i3 ≥ −30) = 1 i parametry bez P{ξ_i2 ≥ −430} (tablica 10.12)
    s.odpowiedz(False)
    s.odpowiedz({0: [MU], 1: [MU], 2: [MIN], 3: [MIN], 4: [MIN], 5: [MIN]})
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz(Warunek(2, P_ge(-30), 1))
    assert [i + 1 for i in s.pytanie.po.warianty] == [6, 8]
    pm = _pm(s.pytanie.po)
    assert pm[0] == pytest.approx((483.63, 488.79), abs=0.025)
    assert pm[1] == pytest.approx((-419.53, -345.37), abs=0.025)
    assert pm[2:] == [(-28.5, -24.0), (-39.0, -25.5), (-28.5, -18.0), (29.0, 39.5)]
    s.odpowiedz(True)
    # iteracja 4: wartości pesymistyczne satysfakcjonujące, tablica 10.13
    s.odpowiedz(True)
    s.odpowiedz(True)
    R4 = s.pytanie.macierz
    assert [[round(float(v), 2) for v in w][2:] for w in R4.wiersze] == [[-24.0, -39.0, -18.0, 29.0], [-28.5, -25.5, -28.5, 39.5]]
    s.odpowiedz(7)  # a8
    assert s.wynik.rozwiazanie == 7
    assert all(h.niespojnosci == () for h in s.wynik.historia)


# --- niespójności (kroki 7-12) -----------------------------------------------------

SIGMA = Parametr(RP.ODCHYLENIE_STD)  # niższe lepsze


def _do_niespojnosci(granica=1.2):
    s = Sesja(Insdecm(P81, REGULA_81).przebieg())
    s.odpowiedz({0: [MU, SIGMA]})
    s.odpowiedz(True)
    s.odpowiedz(False)
    s.odpowiedz(Warunek(0, SIGMA, granica))
    return s


def test_zbior_niespojnosci_i_eps():
    # σ(f1) ≤ 1,2 spełnia tylko a9; a2 i a4 dominują a9 (FSD), więc 𝒩 = {(a2, a9), (a4, a9)}
    assert zbior_niespojnosci(P81, REGULA_81, 0, range(10), [8]) == [(1, 8), (3, 8)]
    assert eps_niespojnosci(P81, 1, 8, 0) == 0
    # SSD (a3 nad a8 dla f1): 0 < ε < 1; FSD w drugą stronę — ε = 1
    assert 0 < eps_niespojnosci(P81, 2, 7, 0) < 1
    assert eps_niespojnosci(P81, 8, 1, 0) == 1


def test_podtrzymanie_usuwa_pary():
    s = _do_niespojnosci()
    assert s.pytanie.po.warianty == (8,)
    s.odpowiedz(True)
    q = s.pytanie
    assert isinstance(q, PytanieNiespojnosc)
    assert (q.prezentacja.i, q.prezentacja.j) == (1, 8)  # najniższe ε, potem numer
    assert q.pozostale == ((1, 8), (3, 8))
    # krok 10: ρ = 10 przedziałów na [min α, max β] = [5, 10], P(X ≥ s_r)
    assert q.prezentacja.punkty[0] == 5 and q.prezentacja.punkty[-1] == 10 and len(q.prezentacja.punkty) == 11
    s.odpowiedz(ZmianaPrezentacji(rho=5, dekumulanta=False))
    assert len(s.pytanie.prezentacja.punkty) == 6 and not s.pytanie.prezentacja.dekumulanta
    s.odpowiedz(PODTRZYMAJ)  # usuwa wszystkie pary z s = a9 — 𝒩 puste
    assert isinstance(s.pytanie, PytanieDaneWystarczajace) and s.pytanie.macierz.warianty == (8,)


def test_oslabienie_warunku():
    s = _do_niespojnosci()
    s.odpowiedz(True)
    s.odpowiedz(OSLAB)
    q = s.pytanie
    assert isinstance(q, PytaniePropozycja)
    sigma_a2 = SIGMA.wartosc(P81.zorientowana(1, 0))
    assert q.propozycje[0] == Warunek(0, SIGMA, sigma_a2)
    s.odpowiedz(0)  # krok 5 z nowym warunkiem
    assert isinstance(s.pytanie, PytanieAkceptacjaZmian)
    assert 1 in s.pytanie.po.warianty and 8 in s.pytanie.po.warianty


def test_zaostrzenie_bez_wykonalnej_propozycji():
    # Zaostrzenie σ < σ(a9) odrzuciłoby wszystkie warianty — propozycja jest pomijana;
    # odrzucenie wraca do kroku 2.
    s = _do_niespojnosci()
    s.odpowiedz(True)
    s.odpowiedz(ZAOSTRZ)
    assert s.pytanie.propozycje == ()
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz(0)
    s.odpowiedz(None)
    assert isinstance(s.pytanie, PytanieDaneWystarczajace) and s.pytanie.iteracja == 1


def test_propozycje_dla_prawdopodobienstwa():
    # f1, P(X ≥ 6) ≥ 0,5: a1 nie spełnia (1/7), a2 spełnia (1).
    war = Warunek(0, P_ge(6), Fraction(1, 2))
    osl = propozycje_modyfikacji(P81, war, 0, 1, oslabienie=True)
    assert osl[0] == Warunek(0, P_ge(6), Fraction(1, 7))
    assert osl[1] == Warunek(0, P_ge(3), Fraction(1, 2))  # P_1(X ≥ 3) = 4/7
    zao = propozycje_modyfikacji(P81, war, 0, 1, oslabienie=False)
    assert zao[0] == Warunek(0, P_ge(6), 1, ostry=True)
    assert zao[1] == Warunek(0, P_ge(10), Fraction(1, 2))  # P_2(X ≥ 10) = 2/7


def test_warunek_bez_wariantow_odrzucony():
    s = Sesja(Insdecm(P81, REGULA_81).przebieg())
    s.odpowiedz({})
    s.odpowiedz(True)
    s.odpowiedz(False)
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz(Warunek(0, MU, 100))


def test_prezentacja_8_12():
    F1 = Rozklad([0, 10], ["1/2", "1/2"])
    F2 = Rozklad([5], [1])
    pr = prezentacja_rozkladow(F1, F2, 2)
    assert pr.punkty == (0, 5, 10)
    assert pr.wartosci_i == (1, Fraction(1, 2), Fraction(1, 2))
    assert pr.wartosci_j == (1, 1, 0)
