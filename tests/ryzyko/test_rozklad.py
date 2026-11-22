from fractions import Fraction

import pytest

from mcdm_ryzyko import Rozklad
from dane_testowe import wczytaj


# --- własności podstawowe ---------------------------------------------------

def test_porzadkowanie_scalanie_i_pomijanie_zer():
    r = Rozklad([3, 0, 1, 3], [0.25, 0, 0.5, 0.25])
    assert r.wartosci == (1, 3)
    assert r.prawdopodobienstwa == (0.5, 0.5)


def test_suma_prawdopodobienstw_musi_byc_jeden():
    with pytest.raises(ValueError):
        Rozklad([1, 2], [0.5, 0.4])


def test_dystrybuanta_i_dekumulanta():
    # Przykład 1.2 (płyta CD do rozdz. 1), tablice 1-2: F_1 i F_2
    f1 = Rozklad([1, 2, 3, 4], ["0,25", "0", "0,50", "0,25"])
    f2 = Rozklad([1, 2, 3, 4], ["0,50", "0,25", "0,25", "0"])
    assert [f1.dystrybuanta(x) for x in (0, 1, 2, 3, 4)] == [0, Fraction(1, 4), Fraction(1, 4), Fraction(3, 4), 1]
    assert [f2.dystrybuanta(x) for x in (0, 1, 2, 3, 4)] == [0, Fraction(1, 2), Fraction(3, 4), 1, 1]
    assert f1.dekumulanta(3) == Fraction(3, 4)
    assert f1.dekumulanta(1) == 1


def test_z_obserwacji_rozdzial_10():
    # Rozdz. 10.3, tabl. 10.5: oceny trzech ekspertów dla portfela a^1 względem f_3
    # (po zmianie znaku): −42, −19, −18, każda z prawdopodobieństwem 1/3.
    r = Rozklad.z_obserwacji([42, 19, 18]).odwrocony()
    assert r.pary() == [(-42, Fraction(1, 3)), (-19, Fraction(1, 3)), (-18, Fraction(1, 3))]
    assert r.minimum() == -42


def test_kwantyle_i_dominanta():
    r = Rozklad([1, 2, 3, 4], ["0,25", "0,25", "0,25", "0,25"])
    assert r.mediana() == 2
    assert r.kwartyl_dolny() == 1
    assert r.kwartyl_gorny() == 3
    assert r.kwantyl(1) == 4
    assert Rozklad([1, 2, 3], ["1/4", "1/2", "1/4"]).dominanta() == 2


def test_wariancja_i_semiodchylenia():
    r = Rozklad([0, 2, 4], ["1/4", "1/2", "1/4"])  # μ = 2
    assert r.wariancja() == 2
    assert r.semiodchylenie_std() == pytest.approx((Fraction(1, 4) * 4) ** 0.5)
    assert r.semiodchylenie_std(dolne=False) == pytest.approx(1.0)
    assert r.semiodchylenie_przecietne() == Fraction(1, 2)
    assert r.semiodchylenie_przecietne(3, dolne=False) == Fraction(1, 4)


# --- przykład 8.1 -----------------------------------------------------------

def test_wartosci_oczekiwane_przyklad_8_1():
    # Przykład 8.1 (płyta CD do rozdz. 8), wiersze μ_ik tablic 1-4
    dane = wczytaj("przyklad_8_1")
    for k in range(4):
        policzone = [float(dane["rozklady"][i][k].wartosc_oczekiwana()) for i in range(10)]
        assert [round(m, 2) for m in policzone] == dane["mu_w_druku"][k]


def test_wartosci_oczekiwane_w_raporcie_programu_przyklad_8_2():
    # Przykład 8.2, rysunek 1: raport STEM-DPR, kolumna „Średnia” dla a7
    # i kolumna „Wartość idealna” (pełna precyzja arkusza).
    r = wczytaj("przyklad_8_1")["rozklady"]
    assert [float(r[6][k].wartosc_oczekiwana()) for k in range(4)] == pytest.approx(
        [5, 7.857142857, 8.142857143, 7.285714286], abs=1e-9
    )
    idealne = [max(float(r[i][k].wartosc_oczekiwana()) for i in range(10)) for k in range(4)]
    assert idealne == pytest.approx([8.142857143, 8.428571429, 8.428571429, 9], abs=1e-9)
