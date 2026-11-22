"""Relacje dominacji stochastycznej, postawy wobec ryzyka i wynik porównania.

Grupy relacji według rozdz. 1.3.1: dla decydenta z awersją do ryzyka
FSD, SSD, TSD; dla decydenta skłonnego do ryzyka FSD, SISD, TISD1, TISD2.
Dla relacji trzeciego stopnia twierdzenia 1.6, 1.8 i 1.9 wymagają
dodatkowo μ_i ≥ μ_j, aby wybór był zgodny z maksymalizacją oczekiwanej
użyteczności. Domyślnie sprawdzana jest sama definicja, tak jak w przykładach
z płyty (1.4, 1.8, 8.1); warunek średniej można włączyć (DECYZJE.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class Relacja(Enum):
    """Relacje z tabl. 1.1-1.4."""

    FSD = "FSD"
    SSD = "SSD"
    TSD = "TSD"
    SISD = "SISD"
    TISD1 = "TISD1"
    TISD2 = "TISD2"
    AFSD = "AFSD"
    ASSD = "ASSD"
    OFSD = "OFSD"
    OSSD = "OSSD"
    OAFSD = "OAFSD"
    OASSD = "OASSD"

    def __str__(self) -> str:
        return self.value


#: Relacje, dla których twierdzenia wymagają warunku μ_i ≥ μ_j.
WYMAGAJA_SREDNIEJ = frozenset({Relacja.TSD, Relacja.TISD1, Relacja.TISD2})


class Postawa(Enum):
    """Stosunek decydenta do ryzyka (rozdz. 1.2-1.3)."""

    AWERSJA = "awersja do ryzyka"
    SKLONNOSC = "skłonność do ryzyka"

    @property
    def relacje(self) -> Tuple[Relacja, ...]:
        """Relacje grupy od najsilniejszej (kolejność ścieżek obliczeń StDom, rozdz. 1.3)."""
        if self is Postawa.AWERSJA:
            return (Relacja.FSD, Relacja.SSD, Relacja.TSD)
        return (Relacja.FSD, Relacja.SISD, Relacja.TISD1, Relacja.TISD2)


@dataclass(frozen=True)
class WynikPorownania:
    """Wynik porównania rozkładu F_i z rozkładem F_j („F_i względem F_j”).

    :param definicje: relacje, których definicje (tabl. 1.1) są spełnione.
    :param mu_i: wartość oczekiwana F_i.
    :param mu_j: wartość oczekiwana F_j.
    :param eps_afsd: faktyczny stopień naruszenia FSD ε₁ (tabl. 1.2) lub None.
    :param eps_assd: faktyczny stopień naruszenia SSD ε₂ (tabl. 1.2) lub None.
    """

    definicje: frozenset
    mu_i: object
    mu_j: object
    eps_afsd: Optional[object] = None
    eps_assd: Optional[object] = None
    tolerancja: float = field(default=1e-6, compare=False)

    @property
    def warunek_sredniej(self) -> bool:
        """Czy μ_i ≥ μ_j (z tolerancją)."""
        return self.mu_i >= self.mu_j - self.tolerancja

    def zachodzi(self, relacja: Relacja, *, warunek_sredniej: bool = False) -> bool:
        """Czy zachodzi ``relacja``.

        Domyślnie sprawdzana jest sama definicja z tabl. 1.1. Przy
        ``warunek_sredniej=True`` dla TSD, TISD1, TISD2 wymagane jest też
        μ_i ≥ μ_j (tw. 1.6, 1.8, 1.9).
        """
        if relacja not in self.definicje:
            return False
        if warunek_sredniej and relacja in WYMAGAJA_SREDNIEJ:
            return self.warunek_sredniej
        return True

    def afsd(self, eps) -> bool:
        """Czy F_i AFSD(ε*) F_j dla ε* = ``eps`` (wzór 1.29: ε_1 ≤ ε*)."""
        return self.eps_afsd is not None and self.eps_afsd <= eps + self.tolerancja

    def assd(self, eps) -> bool:
        """Czy F_i ASSD(ε*) F_j (wzór 1.30: ε_2 ≤ ε* oraz μ_i ≥ μ_j)."""
        return (
            self.eps_assd is not None
            and self.eps_assd <= eps + self.tolerancja
            and self.warunek_sredniej
        )

    def najsilniejsza_porzadkowa(self) -> Optional[Relacja]:
        """OFSD, jeśli zachodzi, w przeciwnym razie OSSD albo None (tabl. 1.3)."""
        for r in (Relacja.OFSD, Relacja.OSSD):
            if r in self.definicje:
                return r
        return None

    def najsilniejsza(self, postawa: Postawa, *, warunek_sredniej: bool = False) -> Optional[Relacja]:
        """Pierwsza zachodząca relacja z grupy ``postawa`` albo None."""
        for r in postawa.relacje:
            if self.zachodzi(r, warunek_sredniej=warunek_sredniej):
                return r
        return None
