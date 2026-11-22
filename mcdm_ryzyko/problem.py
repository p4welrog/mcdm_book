"""Wielokryterialny problem decyzyjny w warunkach ryzyka (rozdz. 1.5.4, 8.2).

Problem to zbiór wariantów 𝒜 = {a^1, …, a^m}, zbiór kryteriów
ℱ = {f_1, …, f_n} i tablica decyzyjna, w której ocena wariantu a^i względem
kryterium f_k jest rozkładem :class:`Rozklad`. Oceny przechowujemy w
jednostkach oryginalnych; metody z rozdz. 8 zakładają, że wyższe wartości są
lepsze (8.2), więc porównania i parametry liczone są na rozkładach
zorientowanych — dla kryterium minimalizowanego ze zmienionym znakiem
(tabl. 10.5, przykłady 1.6-1.8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .dominacje import WynikPorownania, porownaj, porownaj_porzadkowo
from .dominacje.kardynalne import TOLERANCJA
from .rozklad import Liczba, Rozklad


@dataclass(frozen=True)
class Kryterium:
    """Kryterium oceny.

    :param nazwa: nazwa kryterium.
    :param maksymalizowane: True — wyższe oceny lepsze; False — niższe
        (pole „Min” w programie MCDM, instrukcja rozdz. 2.2-2.3).
    :param skala: dla kryterium porządkowego pełna, rosnąca lista ocen
        liczbowych skali (rozdz. 1.3.3); None — kryterium kardynalne.
    """

    nazwa: str
    maksymalizowane: bool = True
    skala: Optional[Tuple] = None

    @property
    def porzadkowe(self) -> bool:
        return self.skala is not None

    def zorientuj(self, wartosc: Liczba) -> Liczba:
        """Wartość w jednostkach „wyższe lepsze” (zmiana znaku dla kryterium min)."""
        return wartosc if self.maksymalizowane else -wartosc

    def z_orientacji(self, wartosc: Liczba) -> Liczba:
        """Odwrotność :meth:`zorientuj`."""
        return self.zorientuj(wartosc)


class Problem:
    """Tablica decyzyjna z rozkładami ocen i pamięcią porównań par wariantów.

    :param kryteria: lista :class:`Kryterium` (albo nazw — wtedy maksymalizowane).
    :param warianty: nazwy wariantów.
    :param oceny: ``oceny[i][k]`` — rozkład oceny wariantu i względem kryterium k,
        w jednostkach oryginalnych.
    :param tolerancja: tolerancja porównań w dominacjach (domyślnie 1e-6).
    """

    def __init__(
        self,
        kryteria: Sequence,
        warianty: Sequence[str],
        oceny: Sequence[Sequence[Rozklad]],
        tolerancja: float = TOLERANCJA,
    ):
        self.kryteria: Tuple[Kryterium, ...] = tuple(
            k if isinstance(k, Kryterium) else Kryterium(str(k)) for k in kryteria
        )
        self.warianty: Tuple[str, ...] = tuple(warianty)
        if len(oceny) != len(self.warianty):
            raise ValueError("liczba wierszy ocen musi być równa liczbie wariantów")
        for wiersz in oceny:
            if len(wiersz) != len(self.kryteria):
                raise ValueError("każdy wariant musi mieć ocenę względem każdego kryterium")
        self._oceny: Tuple[Tuple[Rozklad, ...], ...] = tuple(tuple(w) for w in oceny)
        self._zorientowane = tuple(
            tuple(r if kr.maksymalizowane else r.odwrocony() for r, kr in zip(w, self.kryteria))
            for w in self._oceny
        )
        self.tolerancja = tolerancja
        self._porownania: Dict[Tuple[int, int, int], WynikPorownania] = {}

    @property
    def m(self) -> int:
        """Liczba wariantów."""
        return len(self.warianty)

    @property
    def n(self) -> int:
        """Liczba kryteriów."""
        return len(self.kryteria)

    def ocena(self, i: int, k: int) -> Rozklad:
        """Rozkład oceny a^i względem f_k w jednostkach oryginalnych."""
        return self._oceny[i][k]

    def zorientowana(self, i: int, k: int) -> Rozklad:
        """Rozkład oceny a^i względem f_k w orientacji „wyższe lepsze”."""
        return self._zorientowane[i][k]

    def indeks_wariantu(self, nazwa: str) -> int:
        return self.warianty.index(nazwa)

    def indeks_kryterium(self, nazwa: str) -> int:
        return [k.nazwa for k in self.kryteria].index(nazwa)

    def porownanie(self, i: int, j: int, k: int) -> WynikPorownania:
        """Wynik porównania F_ik z F_jk (zorientowanych); zapamiętywany.

        Dla kryterium porządkowego używane są relacje z tabl. 1.3-1.4 na skali
        zorientowanej, dla kardynalnego — z tabl. 1.1-1.2.
        """
        klucz = (i, j, k)
        w = self._porownania.get(klucz)
        if w is None:
            kr = self.kryteria[k]
            Fi, Fj = self._zorientowane[i][k], self._zorientowane[j][k]
            if kr.porzadkowe:
                skala = sorted(kr.zorientuj(s) for s in kr.skala)
                w = porownaj_porzadkowo(Fi, Fj, skala, self.tolerancja)
            else:
                w = porownaj(Fi, Fj, self.tolerancja)
            self._porownania[klucz] = w
        return w

    def wartosci_oczekiwane(self) -> List[List[Liczba]]:
        """Macierz μ_ik (zorientowanych) — krok 2 fazy wstępnej STEM-DPR."""
        return [[r.wartosc_oczekiwana() for r in w] for w in self._zorientowane]

    def __repr__(self) -> str:
        return f"Problem(m={self.m}, n={self.n}, kryteria={[k.nazwa for k in self.kryteria]})"
