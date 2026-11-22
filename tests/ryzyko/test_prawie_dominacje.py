"""Prawie dominacje AFSD i ASSD (tabl. 1.2)."""

from fractions import Fraction

import pytest

from mcdm_ryzyko import Rozklad
from mcdm_ryzyko.dominacje import Postawa, afsd, assd, porownaj, stopnie_naruszenia
from dane_testowe import wczytaj
from test_dominacje_kardynalne import _tablice_relacji_8_1


def test_przyklad_1_10_afsd():
    # Przykład 1.10: ∫_{S1} = 0,2, ‖F1 − F2‖ = 0,8, więc ε_1 = 0,25 i zachodzi AFSD(0,25).
    F1 = Rozklad([1, 3, 4, 5], ["0,20", "0,40", "0,20", "0,20"])
    F2 = Rozklad([2, 3, 4], ["0,40", "0,40", "0,20"])
    e1, _ = stopnie_naruszenia(F1, F2)
    assert e1 == Fraction(1, 4)
    assert afsd(F1, F2, 0.25)
    assert not afsd(F1, F2, 0.2)


def test_przyklad_1_11_assd():
    # Przykład 1.11: ‖F1 − F2‖ = 2,0; ∫_{S1} = 0,8 (ε_1 = 0,4, brak AFSD(0,25));
    # S_2 = (3, 4), ∫_{S2} = 0,4 (ε_2 = 0,2), μ_1 > μ_2 — zachodzi ASSD(0,25).
    F1 = Rozklad([2, 8], ["0,80", "0,20"])
    F2 = Rozklad([1, 4], ["0,40", "0,60"])
    w = porownaj(F1, F2)
    assert w.najsilniejsza(Postawa.AWERSJA) is None
    assert (w.eps_afsd, w.eps_assd) == (Fraction(2, 5), Fraction(1, 5))
    assert not w.afsd(0.25)
    assert w.assd(0.25)
    assert assd(F1, F2, 0.25)
    # μ_1 = 3,2, μ_2 = 2,8 (w druku 2,2 i 1,8 — ROZBIEZNOSCI.md)
    assert (w.mu_i, w.mu_j) == (Fraction(16, 5), Fraction(14, 5))


def test_fsd_daje_eps_zero():
    F1 = Rozklad([1, 3, 4], ["1/4", "1/2", "1/4"])
    F2 = Rozklad([1, 2, 3], ["1/2", "1/4", "1/4"])
    assert stopnie_naruszenia(F1, F2) == (0, 0)
    # ε dla odwrotnej kolejności: cała różnica jest naruszeniem
    assert stopnie_naruszenia(F2, F1)[0] == 1


def test_eps_spoza_przedzialu():
    F = Rozklad([1, 2], ["1/2", "1/2"])
    with pytest.raises(ValueError):
        afsd(F, F, 0.5)


def test_rozklady_identyczne():
    F = Rozklad([1, 2], ["1/2", "1/2"])
    assert stopnie_naruszenia(F, F) == (None, None)
    assert not porownaj(F, F).afsd(0.4)


def test_przyklad_8_1_wartosci_afsd():
    # Przykład 8.1, tablice 5-8: AFSD(ε) z minimalnym ε, podane tam, gdzie nie
    # zachodzi relacja SD (zaokrąglenie do 0,01).
    druk = {
        (0, 3, 1): 0.40, (0, 4, 2): 0.29, (0, 4, 8): 0.33, (0, 7, 0): 0.06, (0, 7, 6): 0.14, (0, 7, 9): 0.07,
        (1, 9, 3): 0.17, (1, 9, 4): 0.43, (1, 9, 5): 0.06, (1, 9, 8): 0.09,
        (2, 0, 8): 0.20, (2, 3, 5): 0.33, (2, 9, 4): 0.10,
        (3, 5, 9): 0.33, (3, 8, 0): 0.14,
    }
    rozklady = wczytaj("przyklad_8_1")["rozklady"]
    tablice = _tablice_relacji_8_1()
    assert {(k, i, j) for k, t in tablice.items() for i in range(10) for j in range(10) if t[i][j] == "AFSD"} == set(druk)
    for (k, i, j), eps in druk.items():
        assert round(float(porownaj(rozklady[i][k], rozklady[j][k]).eps_afsd), 2) == eps
