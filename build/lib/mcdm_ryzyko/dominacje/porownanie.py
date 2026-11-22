"""Porównanie pary rozkładów względem relacji z tabl. 1.1 i 1.2."""

from __future__ import annotations

from ..rozklad import Rozklad
from .kardynalne import TOLERANCJA, relacje_kardynalne
from .prawie import stopnie_naruszenia
from .relacje import WynikPorownania


def porownaj(Fi: Rozklad, Fj: Rozklad, tolerancja: float = TOLERANCJA) -> WynikPorownania:
    """Porównuje F_i z F_j: relacje z tabl. 1.1 oraz stopnie ε_1, ε_2 z tabl. 1.2.

    >>> from mcdm_ryzyko import Rozklad
    >>> from mcdm_ryzyko.dominacje import Postawa
    >>> F1 = Rozklad([1, 3, 4], ["1/4", "1/2", "1/4"])   # przykład 1.2
    >>> F2 = Rozklad([1, 2, 3], ["1/2", "1/4", "1/4"])
    >>> porownaj(F1, F2).najsilniejsza(Postawa.AWERSJA)
    <Relacja.FSD: 'FSD'>
    """
    e1, e2 = stopnie_naruszenia(Fi, Fj, tolerancja)
    return WynikPorownania(
        definicje=relacje_kardynalne(Fi, Fj, tolerancja),
        mu_i=Fi.wartosc_oczekiwana(),
        mu_j=Fj.wartosc_oczekiwana(),
        eps_afsd=e1,
        eps_assd=e2,
        tolerancja=tolerancja,
    )
