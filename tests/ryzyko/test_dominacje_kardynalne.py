"""Dominacje z tabl. 1.1 na przykładach z płyty CD do rozdz. 1 i 8."""

from fractions import Fraction

from mcdm_ryzyko import Rozklad
from mcdm_ryzyko.dominacje import Postawa, Relacja as R, funkcje_eta, porownaj
from dane_testowe import wczytaj


def _r(wartosci, prawd):
    return Rozklad(wartosci, prawd)


# --- przykłady 1.2-1.4: grupa dla awersji do ryzyka -------------------------

def test_przyklad_1_2_fsd():
    # Przykład 1.2: F_1 FSD F_2; tablica 2: η⁽¹⁾ = 0; −0,25; −0,5; −0,25
    F1 = _r([1, 2, 3, 4], ["0,25", "0", "0,50", "0,25"])
    F2 = _r([1, 2, 3, 4], ["0,50", "0,25", "0,25", "0"])
    e = funkcje_eta(F1, F2)
    assert [c[0] for c in e.eta1.wsp] == [Fraction(-1, 4), Fraction(-1, 2), Fraction(-1, 4)]
    w = porownaj(F1, F2)
    assert w.najsilniejsza(Postawa.AWERSJA) is R.FSD
    assert {R.FSD, R.SSD, R.TSD} <= w.definicje


def test_przyklad_1_3_ssd():
    # Przykład 1.3: η⁽¹⁾ > 0 na [3, 4), ale F_1 SSD F_2
    F1 = _r([1, 3, 4], ["0,25", "0,50", "0,25"])
    F2 = _r([1, 4], ["0,50", "0,50"])
    w = porownaj(F1, F2)
    assert not w.zachodzi(R.FSD)
    assert w.najsilniejsza(Postawa.AWERSJA) is R.SSD


def test_przyklad_1_4_tsd():
    # Przykład 1.4: nie FSD (η⁽¹⁾ > 0 na [4, 5)), nie SSD, ale F_1 TSD F_2
    F1 = _r([1, 2, 3, 4], ["0,23", "0,30", "0,23", "0,24"])
    F2 = _r([1, 2, 3, 5], ["0,34", "0,20", "0,23", "0,23"])
    w = porownaj(F1, F2)
    assert not w.zachodzi(R.FSD) and not w.zachodzi(R.SSD)
    assert w.najsilniejsza(Postawa.AWERSJA) is R.TSD
    # μ_1 = 2,48 < μ_2 = 2,58: przykład stosuje samą definicję (1.23),
    # warunku μ_i ≥ μ_j z tw. 1.6 nie sprawdza.
    assert not w.warunek_sredniej
    assert w.najsilniejsza(Postawa.AWERSJA, warunek_sredniej=True) is None


def test_przyklad_1_10_eta2_eta3():
    # Przykład 1.10, rysunki 2 i 5: wartości η⁽²⁾ i η⁽³⁾ w punktach; brak FSD/SSD/TSD
    F1 = _r([1, 3, 4, 5], ["0,20", "0,40", "0,20", "0,20"])
    F2 = _r([2, 3, 4], ["0,40", "0,40", "0,20"])
    e = funkcje_eta(F1, F2)
    assert [e.eta2.wartosc(x) for x in (1, 2, 3, 5)] == [0, Fraction(1, 5), 0, Fraction(-2, 5)]
    assert [e.eta3.wartosc(x) for x in (1, 2, 3, 4, 5)] == [0, Fraction(1, 10), Fraction(1, 5), Fraction(1, 10), Fraction(-1, 5)]
    assert porownaj(F1, F2).najsilniejsza(Postawa.AWERSJA) is None


# --- przykłady 1.6-1.8: grupa dla skłonności do ryzyka ----------------------
# Kryteria minimalizowane: rozkłady po zmianie znaku (tablica 2 każdego przykładu).

def test_przyklad_1_6_sisd():
    F1 = _r([0, 3], ["0,20", "0,80"]).odwrocony()
    F2 = _r([2, 4], ["0,60", "0,40"]).odwrocony()
    e = funkcje_eta(F1, F2)
    # rysunek 2: η̄⁽²⁾(−4) = 0,4; η̄⁽²⁾(−3) = 0; η̄⁽²⁾(−2) = 0,4; η̄⁽²⁾(0) = 0
    assert [e.eta2_bar.wartosc(x) for x in (-4, -3, -2, 0)] == [Fraction(2, 5), 0, Fraction(2, 5), 0]
    w = porownaj(F1, F2)
    assert not w.zachodzi(R.FSD)
    assert w.najsilniejsza(Postawa.SKLONNOSC) is R.SISD


def test_przyklad_1_7_tisd1():
    F1 = _r([2, 6], ["5/7", "2/7"]).odwrocony()
    F2 = _r([1, 4], ["1/7", "6/7"]).odwrocony()
    e = funkcje_eta(F1, F2)
    # rysunek 2: η̄⁽²⁾ w punktach −6, −4, −2, −1
    assert [e.eta2_bar.wartosc(x) for x in (-6, -4, -2, -1)] == [Fraction(3, 7), 1, Fraction(-1, 7), 0]
    # rysunek 3: η̄⁽³⁾ (TISD1) w punktach −5, −4, −3, −2, −1 (zaokrąglenia z druku)
    assert [round(float(e.eta3_bar_tisd1.wartosc(x)), 2) for x in (-5, -4, -3, -2, -1)] == [0.57, 1.43, 2.14, 2.29, 2.21]
    w = porownaj(F1, F2)
    assert not w.zachodzi(R.FSD) and not w.zachodzi(R.SISD)
    assert w.najsilniejsza(Postawa.SKLONNOSC) is R.TISD1


def test_przyklad_1_8_tisd2():
    F1 = _r([1, 2, 3, 6], ["0,30", "0,20", "0,30", "0,20"]).odwrocony()
    F2 = _r([1, 2, 3, 4], ["0,20", "0,30", "0,20", "0,30"]).odwrocony()
    w = porownaj(F1, F2)
    assert not w.zachodzi(R.FSD) and not w.zachodzi(R.SISD)
    assert w.zachodzi(R.TISD2)
    # μ_1 = −2,8 < μ_2 = −2,6: tw. 1.9 nie jest spełnione, przykład stosuje samą definicję (1.26).
    assert not w.zachodzi(R.TISD2, warunek_sredniej=True)


# --- przykład 1.9: macierz relacji (DARA) -----------------------------------

def test_przyklad_1_9_tablica_2():
    p = {
        1: ["0,60", "0,24", "0,10", "0,04", "0,02"],
        2: ["0,60", "0,20", "0,10", "0,05", "0,05"],
        3: ["0,70", "0,10", "0,10", "0,10", "0,00"],
        4: ["0,40", "0,15", "0,15", "0,15", "0,15"],
        5: ["0,50", "0,15", "0,15", "0,10", "0,10"],
    }
    F = {i: _r([0, 1, 2, 3, 4], pi) for i, pi in p.items()}
    oczekiwane = {(1, 3): R.SSD, (2, 1): R.FSD, (2, 3): R.FSD, (4, 1): R.FSD,
                  (4, 2): R.FSD, (4, 3): R.FSD, (4, 5): R.FSD, (5, 1): R.FSD,
                  (5, 2): R.FSD, (5, 3): R.FSD}
    for i in F:
        for j in F:
            if i != j:
                assert porownaj(F[i], F[j]).najsilniejsza(Postawa.AWERSJA) is oczekiwane.get((i, j)), (i, j)


# --- przykład 8.1: tablice 5-8 ----------------------------------------------

def _tablice_relacji_8_1():
    """Oczekiwane relacje z tablic 5-8 przykładu 8.1 (stałe przepisane z druku)."""
    T = {
        0: """
        . . . . . FSD . . . .
        FSD . FSD . FSD FSD FSD FSD FSD FSD
        FSD . . . . FSD FSD SSD . FSD
        FSD AFSD FSD . FSD FSD FSD FSD FSD FSD
        FSD . AFSD . . FSD FSD SSD AFSD FSD
        . . . . . . . . . .
        FSD . . . . FSD . . . FSD
        AFSD . . . . FSD AFSD . . AFSD
        FSD . SSD . TSD FSD FSD SSD . FSD
        SSD . . . . FSD . . . .""",
        1: """
        . FSD FSD FSD FSD FSD FSD FSD FSD FSD
        . . . . . . . FSD . .
        . FSD . . . . . FSD . .
        . FSD FSD . . FSD . FSD FSD .
        . FSD FSD SSD . FSD . FSD FSD TSD
        . FSD SSD . . . . FSD . .
        . FSD FSD FSD FSD FSD . FSD FSD SSD
        . . . . . . . . . .
        . FSD SSD . . SSD . FSD . .
        . FSD FSD AFSD AFSD AFSD . FSD AFSD .""",
        2: """
        . FSD . . FSD . . . AFSD SSD
        . . . . . . . . . .
        FSD FSD . SSD FSD SSD SSD FSD FSD FSD
        FSD FSD . . FSD AFSD . . FSD FSD
        . FSD . . . . . . . .
        FSD FSD . . FSD . . . FSD FSD
        FSD FSD . SSD FSD SSD . SSD FSD FSD
        FSD FSD . SSD FSD SSD . . FSD FSD
        . FSD . . FSD . . . . SSD
        . FSD . . AFSD . . . . .""",
        3: """
        . . . SSD . . . . . .
        FSD . SSD FSD FSD FSD FSD . FSD FSD
        FSD . . FSD FSD FSD FSD . FSD FSD
        . . . . . . . . . .
        FSD . . FSD . FSD FSD . FSD FSD
        FSD . . FSD . . SSD . FSD AFSD
        FSD . . FSD . . . . FSD .
        FSD FSD FSD FSD FSD FSD FSD . FSD FSD
        AFSD . . FSD . . . . . .
        FSD . . FSD . . SSD . FSD .""",
    }
    return {k: [w.split() for w in t.strip().splitlines()] for k, t in T.items()}


def test_przyklad_8_1_tablice_5_8_wedlug_definicji():
    # Przykład 8.1, tablice 5-8. Druk podaje relacje z grupy dla awersji do ryzyka
    # (FSD/SSD/TSD), choć treść mówi o funkcji INARA (ROZBIEZNOSCI.md), a TSD
    # według samej definicji (1.23). Komórki „AFSD” oznaczają brak relacji SD.
    rozklady = wczytaj("przyklad_8_1")["rozklady"]
    for k, tablica in _tablice_relacji_8_1().items():
        for i in range(10):
            for j in range(10):
                if i == j:
                    continue
                druk = tablica[i][j]
                oczekiwana = None if druk in (".", "AFSD") else R[druk]
                w = porownaj(rozklady[i][k], rozklady[j][k])
                assert w.najsilniejsza(Postawa.AWERSJA) is oczekiwana, (k, i, j)


def test_przyklad_8_1_tsd_bez_warunku_sredniej():
    # Dwie relacje TSD z tablic 5 i 6 nie spełniają warunku μ_i ≥ μ_j z tw. 1.6.
    rozklady = wczytaj("przyklad_8_1")["rozklady"]
    for k, i, j in [(0, 8, 4), (1, 4, 9)]:  # f1: a9→a5, f2: a5→a10
        w = porownaj(rozklady[i][k], rozklady[j][k])
        assert w.zachodzi(R.TSD)
        assert not w.warunek_sredniej
        assert w.najsilniejsza(Postawa.AWERSJA, warunek_sredniej=True) is None


def test_rozklady_identyczne_nie_dominuja():
    F = _r([1, 2], ["1/2", "1/2"])
    assert porownaj(F, F).definicje == frozenset()


def test_floaty_z_tolerancja():
    F1 = Rozklad([1, 2, 3], [0.1, 0.2, 0.7])
    F2 = Rozklad([1, 2, 3], [0.1 + 1e-9, 0.2, 0.7 - 1e-9])
    assert porownaj(F1, F2).definicje == frozenset()
