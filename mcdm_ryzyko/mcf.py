"""Odczyt plików ``.mcf`` programu MCDM 1.00.

Plik ``.mcf`` jest skoroszytem Excela 97 z jednym arkuszem „Dane”. Układ
ustalony na podstawie plików z płyty (``dane/przyklad_8_1.mcf``,
``dane/Przyklad_1.mcf``) i instrukcji MCDM (rozdz. 2):

* wiersz 2: liczba kryteriów n, liczba wariantów m,
* wiersz 4: nazwy kryteriów (kolumny B…), wiersz 5: kierunki
  (0 — minimalizowane, 1 — maksymalizowane),
* wiersz 7: nazwy wariantów,
* od wiersza 9: dla każdego wariantu wiersz z jego nazwą, następnie dla
  każdego kryterium wiersz wartości (w kolumnie A nazwa kryterium) i wiersz
  prawdopodobieństw; bloki rozdzielone pustym wierszem.

Rozkłady bywają dopełnione parami (0; 0); pary o zerowym prawdopodobieństwie
są pomijane (DECYZJE.md). Moduł ``xlrd`` jest potrzebny tylko w
:func:`wczytaj_mcf`; :func:`parsuj_wiersze` działa na zwykłej liście wierszy.
"""

from __future__ import annotations

from typing import List, Sequence, Union

from .problem import Kryterium, Problem
from .rozklad import Rozklad


class BladFormatuMcf(ValueError):
    """Zawartość arkusza nie odpowiada formatowi ``.mcf``."""


def _pusta(x) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")


def _liczba(x, gdzie: str):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise BladFormatuMcf(f"{gdzie}: oczekiwano liczby, jest {x!r}")
    return int(x) if float(x).is_integer() else x


def parsuj_wiersze(wiersze: Sequence[Sequence]) -> Problem:
    """Tworzy :class:`Problem` z zawartości arkusza „Dane” (lista wierszy komórek)."""
    w = [list(r) for r in wiersze]

    def komorka(r, c):
        return w[r][c] if r < len(w) and c < len(w[r]) else ""

    try:
        n = int(_liczba(komorka(1, 0), "A2"))
        m = int(_liczba(komorka(1, 1), "B2"))
    except BladFormatuMcf as e:
        raise BladFormatuMcf(f"nagłówek: {e}") from None
    nazwy_kr = [str(komorka(3, 1 + k)).strip() for k in range(n)]
    kierunki = [_liczba(komorka(4, 1 + k), f"wiersz 5, kolumna {k + 2}") for k in range(n)]
    if any(d not in (0, 1) for d in kierunki):
        raise BladFormatuMcf("kierunki kryteriów muszą być równe 0 lub 1")
    kryteria = [Kryterium(nazwa, maksymalizowane=bool(d)) for nazwa, d in zip(nazwy_kr, kierunki)]
    warianty = [str(komorka(6, 1 + i)).strip() for i in range(m)]

    r = 8
    oceny: List[List[Rozklad]] = []
    for i in range(m):
        while r < len(w) and all(_pusta(x) for x in w[r]):
            r += 1
        if str(komorka(r, 0)).strip() != warianty[i]:
            raise BladFormatuMcf(f"wiersz {r + 1}: oczekiwano bloku wariantu {warianty[i]!r}")
        r += 1
        wiersz_ocen = []
        for k in range(n):
            if str(komorka(r, 0)).strip() != nazwy_kr[k]:
                raise BladFormatuMcf(
                    f"wiersz {r + 1}: oczekiwano wartości kryterium {nazwy_kr[k]!r} dla {warianty[i]!r}"
                )
            wartosci, prawd = [], []
            for c in range(1, max(len(w[r]), len(w[r + 1]) if r + 1 < len(w) else 0)):
                x, p = komorka(r, c), komorka(r + 1, c)
                if _pusta(x) and _pusta(p):
                    continue
                if _pusta(x) or _pusta(p):
                    raise BladFormatuMcf(f"wiersze {r + 1}-{r + 2}, kolumna {c + 1}: brak wartości albo prawdopodobieństwa")
                wartosci.append(_liczba(x, f"wiersz {r + 1}"))
                prawd.append(_liczba(p, f"wiersz {r + 2}"))
            try:
                wiersz_ocen.append(Rozklad(wartosci, prawd))
            except ValueError as e:
                raise BladFormatuMcf(f"{warianty[i]}, {nazwy_kr[k]}: {e}") from None
            r += 2
        oceny.append(wiersz_ocen)
    return Problem(kryteria, warianty, oceny)


def wczytaj_mcf(zrodlo: Union[str, bytes, "object"]) -> Problem:
    """Wczytuje plik ``.mcf`` (ścieżka albo zawartość ``bytes``, np. w Pyodide).

    Wymaga opcjonalnej zależności ``xlrd`` (``pip install mcdm_ryzyko[mcf]``).
    """
    try:
        import xlrd  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError("odczyt .mcf wymaga pakietu xlrd: pip install xlrd") from e
    if isinstance(zrodlo, (bytes, bytearray)):
        ksiazka = xlrd.open_workbook(file_contents=bytes(zrodlo))
    else:
        ksiazka = xlrd.open_workbook(str(zrodlo))
    arkusz = ksiazka.sheet_by_index(0)
    wiersze = [arkusz.row_values(r) for r in range(arkusz.nrows)]
    return parsuj_wiersze(wiersze)
