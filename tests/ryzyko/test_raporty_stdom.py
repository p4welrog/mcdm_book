"""Raporty programu StDom z arkuszy przykładów 5.19, 6.13, 6.15 (płyta CD) i StDom_Przyklad1.

Rozkłady i werdykty wyjęto z arkuszy „Dominacje stoch-kryterium k” do
``dane/raporty_stdom.json`` (same liczby i werdykty, klucz: przykład i kryterium).

StDom porównuje rozkład X („dominujący”) z rozkładem Y na surowych wartościach
(instrukcja StDom, rozdz. 3.3); raporty dla awersji podają FSD, SSD, TSD, dla
skłonności FSD, SISD, TISD1, TISD2. Każdy werdykt „Zachodzi / Nie Zachodzi”
porównujemy z definicją z tabl. 1.1 (bez warunku średniej).
"""

import pytest

from mcdm_ryzyko import Rozklad
from mcdm_ryzyko.dominacje import Postawa, Relacja as R, porownaj
import json
from pathlib import Path

RAPORTY = json.loads((Path(__file__).parent / "dane" / "raporty_stdom.json").read_text(encoding="utf-8"))
PLIKI = ["P05_19", "P06_13", "P06_15"]


@pytest.mark.parametrize("plik", PLIKI)
@pytest.mark.parametrize("k", [1, 2, 3])
def test_raporty_stdom_w_arkuszach_przykladow(plik, k):
    arkusz = RAPORTY[f"{plik}_k{k}"]
    F = {int(i): Rozklad(*v) for i, v in arkusz["rozklady"].items()}
    raporty = arkusz["raporty"]
    assert len(raporty) >= 30
    for r in raporty:
        i, j, kk, werdykty = r["i"], r["j"], r["k"], r["werdykty"]
        assert kk == k
        w = porownaj(F[i], F[j])
        for rel, tekst in werdykty.items():
            assert tekst in ("Zachodzi", "Nie Zachodzi")
            assert w.zachodzi(R[rel]) == (tekst == "Zachodzi"), (plik, k, i, j, rel)


def test_stdom_przyklad1_wyniki():
    # StDom_Przyklad1.xls z płyty, arkusz „Wyniki”: X, Y z arkusza „Dane Przykłady” (przykład 1.10);
    # FSD, SSD, TSD — „Nie Zachodzi”; dystrybuanty X: 0,2 0,2 0,6 0,8 1; Y: 0 0,4 0,8 1 1.
    X = Rozklad([1, 2, 3, 4, 5], [0.2, 0.0, 0.4, 0.2, 0.2])
    Y = Rozklad([1, 2, 3, 4, 5], [0.0, 0.4, 0.4, 0.2, 0.0])
    assert [X.dystrybuanta(x) for x in range(1, 6)] == pytest.approx([0.2, 0.2, 0.6, 0.8, 1.0])
    assert [Y.dystrybuanta(x) for x in range(1, 6)] == pytest.approx([0.0, 0.4, 0.8, 1.0, 1.0])
    assert porownaj(X, Y).najsilniejsza(Postawa.AWERSJA) is None
