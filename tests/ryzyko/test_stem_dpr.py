"""STEM-DPR (rozdz. 8.3) na przykładach 8.1, 8.2 i rozdz. 10.4."""

import pytest

from mcdm_ryzyko import Problem
from mcdm_ryzyko.dialog import PRZERWIJ, BlednaOdpowiedz, Sesja, uruchom
from mcdm_ryzyko.dominacje import Relacja as R
from mcdm_ryzyko.dominacje.regula import RegulaDominacji
from mcdm_ryzyko.parametry import Parametr, RodzajParametru
from mcdm_ryzyko.stem_dpr import (
    PytanieInformacje, PytanieKryteriumSatysfakcjonujace, PytanieProg, PytanieSatysfakcja,
    Prog, StemDpr, phi,
)
from dane_testowe import rozdzial_10, wczytaj

D81 = wczytaj("przyklad_8_1")
P81 = Problem(D81["kryteria"], D81["warianty"], D81["rozklady"])
# Tablice 5-8 przykładu 8.1 odpowiadają grupie relacji dla awersji do ryzyka (ROZBIEZNOSCI.md).
REGULA_81 = RegulaDominacji.awersja()

#: Druk zaokrągla ε do 0,01 przed obliczeniem φ (np. ε = 0,1429 → 0,14 → φ = 0,72
#: zamiast 0,714), stąd różnice do 0,01 w d (ROZBIEZNOSCI.md).
TOL_DRUKU = 0.011


def _f(x):
    return float(x)


def test_phi_przyklad_8_1_tablice_9_12():
    # Wybrane niecałkowite φ z tablic 9-12 (wiersz a^i, kolumna a^j).
    druk = {
        (0, 3, 1): 0.20, (0, 7, 0): 0.88, (0, 7, 6): 0.71, (0, 7, 9): 0.86, (0, 4, 8): 0.34,
        (1, 9, 3): 0.66, (1, 9, 4): 0.14, (1, 9, 5): 0.88, (1, 9, 8): 0.82,
        (2, 0, 8): 0.60, (2, 3, 5): 0.34, (2, 9, 4): 0.80,
        (3, 5, 9): 0.34, (3, 8, 0): 0.72,
    }
    for (k, i, j), v in druk.items():
        assert _f(phi(P81, REGULA_81, i, j, k)) == pytest.approx(v, abs=TOL_DRUKU), (k, i, j)
    # φ = 1 dla SD_T, np. a9 TSD a5 (f1) według samej definicji TSD
    assert phi(P81, REGULA_81, 8, 4, 0) == 1


def test_iteracja_1_przyklad_8_1_tablice_13_14():
    st = StemDpr(P81, REGULA_81).stan_iteracji(1, range(10), range(4))
    druk_13 = [
        [7.88, 0.00, 5.00, 7.72], [0.20, 8.00, 9.00, 1.00], [3.42, 7.00, 0.00, 2.00],
        [0.00, 3.66, 3.00, 9.00], [3.00, 2.14, 7.80, 3.00], [9.00, 5.88, 3.34, 4.00],
        [5.71, 1.00, 1.00, 6.00], [5.00, 9.00, 2.00, 0.00], [2.34, 4.82, 5.60, 7.00],
        [6.86, 3.00, 7.00, 4.34],
    ]
    for j in range(10):
        assert [_f(x) for x in st.d[j]] == pytest.approx(druk_13[j], abs=TOL_DRUKU), j
    assert st.proba == 6 and st.remis == (6,)  # a7
    # tablica 14
    assert [round(_f(x), 2) for x in st.mu_proby] == [5.00, 7.86, 8.14, 7.29]
    assert [round(_f(x), 2) for x in st.idealny] == [8.14, 8.43, 8.43, 9.00]


def test_iteracja_2_przyklad_8_1_tablice_15_19():
    st = StemDpr(P81, REGULA_81).stan_iteracji(2, [2, 3, 5, 6, 7], [0, 1, 3])
    druk_18 = {2: [1, 3, 1], 3: [0, 1, 4], 5: [4, 2, 2], 6: [2.71, 0, 3], 7: [2, 4, 0]}
    for j, d in druk_18.items():
        assert [_f(st.d[j][k]) for k in (0, 1, 3)] == pytest.approx(d, abs=TOL_DRUKU)
    # remis a3/a7 (3,00); druk wybiera a3 — wariant o niższym numerze
    assert st.remis == (2, 6) and st.proba == 2
    # tablica 19: d_3k^(2) = 1, 3, 0, 1 (także dla nieaktywnego f3)
    assert [_f(x) for x in st.d_proby] == [1, 3, 0, 1]
    assert [round(_f(x), 2) for x in st.mu_proby] == [6.29, 4.86, 8.43, 8.43]
    # wektor idealny według (8.1) w 𝒜^(2); druk podaje 8,43 dla f2 (ROZBIEZNOSCI.md)
    assert [round(_f(x), 2) for x in st.idealny] == [8.14, 7.86, 8.43, 9.00]


def test_dialog_przyklad_8_1():
    # Kroki 3-6 iteracji 1, kroki 3-4 iteracji 2. δ_3 = 6,00 daje 𝒜^(2) = {a3, a4, a6, a7, a8}.
    s = Sesja(StemDpr(P81, REGULA_81).przebieg())
    assert isinstance(s.pytanie, PytanieInformacje)
    s.odpowiedz(True)
    assert isinstance(s.pytanie, PytanieSatysfakcja)
    s.odpowiedz(False)
    assert isinstance(s.pytanie, PytanieKryteriumSatysfakcjonujace)
    s.odpowiedz(True)
    assert isinstance(s.pytanie, PytanieProg)
    s.odpowiedz(Prog(2, 6.0))
    assert s.pytanie.stan.warianty == (2, 3, 5, 6, 7)
    assert s.pytanie.stan.aktywne == (0, 1, 3)
    s.odpowiedz(True)
    s.odpowiedz(True)
    assert s.wynik.status == "zaakceptowano" and s.wynik.rozwiazanie == 2  # a3
    assert [h.proba for h in s.wynik.historia] == [6, 2]


def test_dialog_przyklad_8_2_program():
    # Przykład 8.2: program nie zadaje pytania z kroku 3; rysunki 1 i 5.
    w = uruchom(StemDpr(P81, REGULA_81, pytaj_o_informacje=False).przebieg(),
                [False, True, Prog(2, 6), True])
    assert w.rozwiazanie == 2
    it1, it2 = w.historia
    assert [_f(x) for x in it1.mu_proby] == pytest.approx([5, 7.857142857, 8.142857143, 7.285714286], abs=1e-9)
    assert [round(_f(x), 2) for x in it1.d_proby] == [5.71, 1.00, 1.00, 6.00]
    assert [_f(x) for x in it1.idealny] == pytest.approx([8.142857143, 8.428571429, 8.428571429, 9], abs=1e-9)
    # rysunek 5: kryterium aktywne X3 — Nie; warianty rozpatrywane a3, a4, a6, a7, a8
    assert it2.aktywne == (0, 1, 3)
    assert [P81.warianty[j] for j in it2.warianty] == ["a3", "a4", "a6", "a7", "a8"]
    assert [round(_f(x), 2) for x in it2.d_proby] == [1.00, 3.00, 0.00, 1.00]


def test_dodatkowe_parametry_krok_3():
    s = Sesja(StemDpr(P81, REGULA_81).przebieg())
    par = Parametr(RodzajParametru.ODCHYLENIE_STD)
    s.odpowiedz([(0, par)])
    assert isinstance(s.pytanie, PytanieInformacje)
    assert s.pytanie.stan.dodatkowe[(0, par)] == pytest.approx(P81.zorientowana(6, 0).odchylenie_std())


def test_brak_rozwiazania_i_przerwanie():
    w = uruchom(StemDpr(P81, REGULA_81, pytaj_o_informacje=False).przebieg(), [False, False])
    assert w.status == "brak_rozwiazania" and w.rozwiazanie is None
    w = uruchom(StemDpr(P81, REGULA_81).przebieg(), [True, PRZERWIJ])
    assert w.status == "przerwano"


def test_prog_bez_wariantow_odrzucony():
    s = Sesja(StemDpr(P81, REGULA_81, pytaj_o_informacje=False).przebieg())
    s.odpowiedz(False)
    s.odpowiedz(True)
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz(Prog(2, 100))
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz(Prog(7, 1))


def test_zbior_K_przywracany_gdy_pusty():
    odp = []
    for k in range(4):
        odp += [False, True, Prog(k, -1e9)]
    s = Sesja(StemDpr(P81, REGULA_81, pytaj_o_informacje=False).przebieg())
    for o in odp:
        s.odpowiedz(o)
    assert s.pytanie.stan.aktywne == (0, 1, 2, 3)


# --- rozdz. 10.4 --------------------------------------------------------------

T10 = rozdzial_10()
P10 = Problem(T10["kryteria"], [f"a{i}" for i in range(1, 15)],
              [[T10["rozklady"][k][i] for k in T10["kryteria"]] for i in range(14)])
REGULA_10 = RegulaDominacji(relacje=(R.FSD, R.SSD), afsd=False)  # rozdz. 10.4


def test_rozdzial_10_stem_dpr():
    w = uruchom(StemDpr(P10, REGULA_10, pytaj_o_informacje=False).przebieg(),
                [False, True, Prog(3, -25), True])
    assert w.status == "zaakceptowano" and w.rozwiazanie == 5  # a6
    it1, it2 = w.historia
    # tablica 10.6 (μ z rozkładów R10.3/R10.4 różnią się od druku do 0,02 — ROZBIEZNOSCI.md)
    assert it1.proba == 7  # a8
    assert [_f(x) for x in it1.mu_proby] == pytest.approx([483.63, -419.53, -24.00, -19.17, -16.67, 44.67], abs=0.025)
    assert [_f(x) for x in it1.idealny] == pytest.approx([494.95, -297.17, -17.33, -16.33, -12.33, 56.33], abs=0.025)
    # d_8k^(1): druk 6, 6, 1, 0, 5, 6; według R10.5 d_86 = 2 (ROZBIEZNOSCI.md)
    assert [_f(x) for x in it1.d_proby] == [6, 6, 1, 0, 5, 2]
    # 𝒜^(2) dla δ_4 = −25
    assert it2.warianty == (2, 5, 6, 7, 9, 11)
    assert it2.aktywne == (0, 1, 2, 4, 5)
    # tablica 10.7
    assert it2.proba == 5
    assert [_f(x) for x in it2.d_proby] == [1, 1, 0, 3, 1, 3]
    assert [_f(x) for x in it2.mu_proby] == pytest.approx([488.79, -345.37, -17.33, -21.33, -12.67, 35.33], abs=0.025)
    assert [_f(x) for x in it2.idealny] == pytest.approx([491.92, -297.17, -17.33, -16.33, -12.33, 56.33], abs=0.025)
