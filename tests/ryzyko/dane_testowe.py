"""Wczytywanie danych testowych z ``tests/dane/`` (same liczby z płyty CD)."""

from __future__ import annotations

import json
from pathlib import Path

from mcdm_ryzyko import Rozklad

KATALOG = Path(__file__).parent / "dane"


def wczytaj(nazwa: str) -> dict:
    """Zwraca słownik z pliku JSON, z polem ``rozklady[i][k]`` (wariant, kryterium)."""
    dane = json.loads((KATALOG / f"{nazwa}.json").read_text(encoding="utf-8"))
    dane["rozklady"] = [
        [Rozklad(o["wartosci"], o["prawdopodobienstwa"]) for o in wariant]
        for wariant in dane["oceny"]
    ]
    return dane


def rozdzial_10() -> dict:
    """Dane z rozdz. 10: ``rozklady[k][i]`` dla kryterium k ∈ f1…f6, portfela i.

    f1, f2 — zbiory R10.3, R10.4 (f2 już pomnożone przez −1); f3…f6 —
    rozkłady ocen ekspertów z tabl. 10.4 według zasad z rozdz. 10.3
    (średnia ocen projektów w portfelu dla każdego eksperta, eksperci
    równoprawdopodobni; ryzyka f3…f5 pomnożone przez −1 jak w tabl. 10.5).
    """
    from fractions import Fraction

    dane = json.loads((KATALOG / "rozdzial_10.json").read_text(encoding="utf-8"))
    rozklady = {k: [Rozklad(o["wartosci"], o["prawdopodobienstwa"]) for o in dane[k]] for k in ("f1", "f2")}
    for k, oceny in dane["eksperci"].items():
        lista = []
        for portfel in dane["portfele"]:
            srednie = [Fraction(sum(e[p - 1] for p in portfel), len(portfel)) for e in oceny]
            r = Rozklad.z_obserwacji(srednie)
            lista.append(r.odwrocony() if k in dane["minimalizowane_wsrod_ekspertow"] else r)
        rozklady[k] = lista
    dane["rozklady"] = rozklady
    return dane
