"""Klasa Problem i odczyt plików .mcf z płyty (mcdm_book/data)."""

from pathlib import Path

import pytest

from mcdm_ryzyko import Kryterium, Problem, Rozklad
from mcdm_ryzyko.dominacje import Postawa, Relacja as R
from mcdm_ryzyko.mcf import BladFormatuMcf, parsuj_wiersze
from dane_testowe import wczytaj

DANE = Path(__file__).resolve().parents[2] / "mcdm_book" / "data"
xlrd = pytest.importorskip("xlrd")


def test_przyklad_8_1_mcf_zgodny_z_tablicami():
    # przyklad_8_1.mcf a tablice 1-4 przykładu 8.1 (dane/przyklad_8_1.json)
    from mcdm_ryzyko import wczytaj_mcf

    problem = wczytaj_mcf(DANE / "przyklad_8_1.mcf")
    assert problem.warianty == tuple(f"a{i}" for i in range(1, 11))
    assert [k.nazwa for k in problem.kryteria] == ["X1", "X2", "X3", "X4"]
    assert all(k.maksymalizowane for k in problem.kryteria)
    wzorzec = wczytaj("przyklad_8_1")["rozklady"]
    for i in range(10):
        for k in range(4):
            r, w = problem.ocena(i, k), wzorzec[i][k]
            assert r.wartosci == w.wartosci
            assert [float(p) for p in r.prawdopodobienstwa] == pytest.approx([float(p) for p in w.prawdopodobienstwa])


def test_przyklad_1_mcf_z_bajtow():
    from mcdm_ryzyko import wczytaj_mcf

    problem = wczytaj_mcf((DANE / "Przyklad_1.mcf").read_bytes())
    assert (problem.m, problem.n) == (20, 3)
    # rozkład a1/X1 w pliku: wartości 25…45 dopełnione zerami (0; 0); zerowe pomijane
    assert problem.ocena(0, 0).pary() == [(30, 0.4), (35, 0.4), (40, 0.2)]


def test_parser_bledny_blok():
    wiersze = [["Dane"], [1, 1], [""], ["", "X"], ["", 1], [""], ["", "a1"], [""], ["a2"]]
    with pytest.raises(BladFormatuMcf):
        parsuj_wiersze(wiersze)


def test_parser_kryterium_minimalizowane():
    wiersze = [["Dane"], [1, 1], [""], ["", "X"], ["", 0], [""], ["", "a1"], [""],
               ["a1"], ["X", 1, 2], ["", 0.5, 0.5]]
    p = parsuj_wiersze(wiersze)
    assert not p.kryteria[0].maksymalizowane
    assert p.zorientowana(0, 0).wartosci == (-2, -1)


def test_problem_orientacja_i_porownania():
    # Przykład 1.6: kryterium minimalizowane, po zmianie znaku F_1 SISD F_2
    p = Problem([Kryterium("f", maksymalizowane=False)], ["a1", "a2"],
                [[Rozklad([0, 3], ["0,2", "0,8"])], [Rozklad([2, 4], ["0,6", "0,4"])]])
    assert p.porownanie(0, 1, 0).najsilniejsza(Postawa.SKLONNOSC) is R.SISD
    assert p.porownanie(0, 1, 0) is p.porownanie(0, 1, 0)


def test_problem_porzadkowy():
    # Przykład 1.12 jako kryterium porządkowe
    skala = (1, 2, 3, 4, 5, 6)
    p = Problem([Kryterium("ocena", skala=skala)], ["a1", "a2"],
                [[Rozklad(skala, ["0", "0,1", "0,2", "0,3", "0,3", "0,1"])],
                 [Rozklad(skala, ["0,1", "0,1", "0,3", "0,3", "0,2", "0"])]])
    assert p.porownanie(0, 1, 0).najsilniejsza_porzadkowa() is R.OFSD
