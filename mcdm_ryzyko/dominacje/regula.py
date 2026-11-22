"""Reguła SD_T: dominacja zgodna z przyjętym typem funkcji użyteczności.

W STEM-DPR (wzór 8.4) i INSDECM (wzór 8.8) SD_T oznacza dominację
stochastyczną zgodną z wiedzą o funkcji użyteczności decydenta (założenia
w rozdz. 8.2). Reguła określa, które relacje z tabl. 1.1 brać pod uwagę
i czy w STEM-DPR uwzględniać AFSD. Przykłady:

* ``RegulaDominacji.awersja()`` — FSD, SSD, TSD i AFSD (przykład 8.1),
* ``RegulaDominacji.sklonnosc()`` — FSD, SISD, TISD1, TISD2 i AFSD,
* ``RegulaDominacji(relacje=(Relacja.FSD, Relacja.SSD), afsd=False)`` —
  rozdz. 10.4 („uwzględniono relacje FSD oraz SSD”).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .relacje import Postawa, Relacja, WynikPorownania

#: Odpowiedniki porządkowe relacji kardynalnych (tabl. 1.3), używane, gdy
#: kryterium jest porządkowe (rozszerzenie poza rozdz. 8, DECYZJE.md).
_PORZADKOWE = {Relacja.FSD: Relacja.OFSD, Relacja.SSD: Relacja.OSSD}


@dataclass(frozen=True)
class RegulaDominacji:
    """Konfiguracja relacji SD_T.

    :param postawa: stosunek decydenta do ryzyka; wyznacza domyślny zbiór relacji.
    :param relacje: relacje uznawane za SD_T (domyślnie cała grupa ``postawa``).
    :param afsd: czy w STEM-DPR uwzględniać AFSD (wzór 8.4, drugi przypadek).
    :param warunek_sredniej: czy dla TSD/TISD1/TISD2 wymagać μ_i ≥ μ_j
        (tw. 1.6, 1.8, 1.9); domyślnie sama definicja (DECYZJE.md).
    """

    postawa: Postawa = Postawa.AWERSJA
    relacje: Optional[Tuple[Relacja, ...]] = None
    afsd: bool = True
    warunek_sredniej: bool = False

    @classmethod
    def awersja(cls, **kw) -> "RegulaDominacji":
        return cls(postawa=Postawa.AWERSJA, **kw)

    @classmethod
    def sklonnosc(cls, **kw) -> "RegulaDominacji":
        return cls(postawa=Postawa.SKLONNOSC, **kw)

    @property
    def lista_relacji(self) -> Tuple[Relacja, ...]:
        return tuple(self.relacje) if self.relacje is not None else self.postawa.relacje

    def dominuje(self, w: WynikPorownania) -> bool:
        """Czy F_i SD_T F_j dla wyniku porównania ``w``."""
        return self.relacja(w) is not None

    def relacja(self, w: WynikPorownania) -> Optional[Relacja]:
        """Najsilniejsza relacja z :attr:`lista_relacji`, która zachodzi, albo None."""
        for r in self.lista_relacji:
            if w.zachodzi(r, warunek_sredniej=self.warunek_sredniej):
                return r
            odp = _PORZADKOWE.get(r)
            if odp is not None and odp in w.definicje:
                return odp
        return None
