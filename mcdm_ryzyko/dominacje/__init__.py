"""Dominacje stochastyczne (rozdz. 1.3)."""

from .kardynalne import FunkcjeEta, funkcje_eta, relacje_kardynalne
from .porownanie import porownaj
from .porzadkowe import porownaj_porzadkowo
from .prawie import afsd, assd, stopnie_naruszenia
from .relacje import Postawa, Relacja, WynikPorownania

__all__ = [
    "FunkcjeEta",
    "Postawa",
    "Relacja",
    "WynikPorownania",
    "afsd",
    "assd",
    "funkcje_eta",
    "porownaj",
    "porownaj_porzadkowo",
    "relacje_kardynalne",
    "stopnie_naruszenia",
]
