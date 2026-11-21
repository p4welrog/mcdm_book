"""Zadanie wielokryterialne w warunkach ryzyka i odczyt plików .mcf (MCDM 1.00).

Plik .mcf to skoroszyt Excela (BIFF8) z arkuszem „Dane”:
  A1 komentarz; A2 liczba kryteriów k, B2 liczba wariantów n;
  wiersz 4 od B: nazwy kryteriów, wiersz 5: 1 = maksymalizowane, 0 = minimalizowane;
  wiersz 7 od B: nazwy wariantów; od wiersza 10 dla każdego wariantu po k par wierszy
  (wartości, prawdopodobieństwa) w kolumnach B:K, a po nich jeden wiersz odstępu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

from .distribution import Distribution

MAX_POINTS = 10  # iMAX_DANE


@dataclass
class Problem:
    criteria: List[str]
    maximize: List[bool]
    variants: List[str]
    dist: List[List[Distribution]]          # dist[i][k] — wariant i, kryterium k
    comment: str = ""
    source: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.variants)

    @property
    def m(self) -> int:
        return len(self.criteria)

    def oriented(self, i: int, k: int) -> Distribution:
        """Rozkład w orientacji „więcej = lepiej” (dla kryteriów minimalizowanych wartości z minusem)."""
        d = self.dist[i][k]
        if self.maximize[k]:
            return d
        return Distribution.from_pairs([-v for v in d.values], d.probs)


def _num(v) -> float:
    if v in ("", None):
        return 0.0
    return float(v)


def example(name: str = "przyklad_8_1") -> Problem:
    """Plik .mcf z płyty dołączony do pakietu: "przyklad_8_1" (przykłady 8.1–8.4) albo "Przyklad_1";
    "rozdz_10" — 14 portfeli z rozdz. 10 (R10.3, R10.4, tabl. 10.2, 10.4);
    "przyklad_8_5" — dane przykładu 8.5 (jak 8.1, ale rozkłady kryterium f1 wariantów a6 i a8 zamienione)."""
    if name == "rozdz_10":
        import json
        d = json.loads((Path(__file__).parent / "data" / "rozdz_10.json").read_text(encoding="utf-8"))
        p = problem_from_tables(d["criteria"], [True] * len(d["criteria"]), d["variants"],
                                [[tuple(x) for x in row] for row in d["dist"]])
        p.comment = ("Rozdz. 10: 14 portfeli projektów; f1, f2 — R10.3–R10.4 (f2 ze znakiem minus), "
                     "f3–f6 — średnie ocen 3 ekspertów (tabl. 10.4, p = 1/3; f3–f5 ze znakiem minus)")
        return p
    if name == "przyklad_8_5":
        p = read_mcf(Path(__file__).parent / "data" / "przyklad_8_1.mcf")
        p.dist[5][0], p.dist[7][0] = p.dist[7][0], p.dist[5][0]
        p.comment = "Przykład 8.5 (ATO-DPR): dane przykładu 8.1 z zamienionymi rozkładami f1 wariantów a6 i a8"
        return p
    return read_mcf(Path(__file__).parent / "data" / f"{name}.mcf")


def read_mcf(path: "str | Path | bytes", *, check_sum: bool = False) -> Problem:
    """Wczytuje plik .mcf. Prawdopodobieństwa nie muszą sumować się do 1 (MCDM tego nie sprawdza);
    odchylenia trafiają do `Problem.warnings`."""
    import xlrd

    if isinstance(path, (bytes, bytearray)):
        book = xlrd.open_workbook(file_contents=bytes(path))
        path = "<bytes>"
    else:
        book = xlrd.open_workbook(str(path))
    sh = book.sheet_by_name("Dane")
    cell = lambda r, c: sh.cell_value(r - 1, c - 1) if r - 1 < sh.nrows and c - 1 < sh.ncols else ""
    k, n = int(_num(cell(2, 1))), int(_num(cell(2, 2)))
    crit = [str(cell(4, 2 + j)) for j in range(k)]
    maxi = [bool(int(_num(cell(5, 2 + j)))) for j in range(k)]
    var = [str(cell(7, 2 + j)) for j in range(n)]
    dist, warns = [], []
    row = 9
    for i in range(n):
        row += 1
        di = []
        for j in range(k):
            vals = [_num(cell(row, 2 + c)) for c in range(MAX_POINTS)]
            prs = [_num(cell(row + 1, 2 + c)) for c in range(MAX_POINTS)]
            s = sum(prs)
            if abs(s - 1) > 1e-6:
                warns.append(f"{var[i]}/{crit[j]}: suma prawdopodobieństw {s:.6g} (wiersz {row + 1})")
            di.append(Distribution.from_pairs(vals, prs, check_sum=check_sum))
            row += 2
        dist.append(di)
        row += 1
    return Problem(crit, maxi, var, dist, str(cell(1, 1)), str(path), warns)


def problem_from_tables(criteria: Sequence[str], maximize: Sequence[bool], variants: Sequence[str],
                        table: Sequence[Sequence[tuple]]) -> Problem:
    """table[i][k] = (wartości, prawdopodobieństwa)."""
    dist = [[Distribution.from_pairs(v, p) for v, p in row] for row in table]
    return Problem(list(criteria), list(maximize), list(variants), dist)
