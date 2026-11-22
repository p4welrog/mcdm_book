"""Parametry rozkładów ocen pokazywane decydentowi w fazie dialogu.

Lista parametrów pochodzi z rozdz. 8.3 (s. 157: mediana, moda, odchylenie
standardowe, semiodchylenia, kwantyle), 8.4 (s. 161) oraz z formatki
„Parametry rozkładu” programu MCDM (instrukcja, rozdz. 4.2.1). Parametr
„najgorsza wartość” (min) używany jest w rozdz. 10.5 (tabl. 10.8).

Każdy parametr ma kierunek: czy decydent woli wartości wyższe (zbiór Q_1
w rozdz. 8.4) czy niższe (Q_2). Kierunek decyduje o tym, która wartość jest
w macierzy możliwości optymistyczna, a która pesymistyczna (wzory 8.6-8.7).
Parametry są liczone na rozkładzie już zorientowanym tak, że wyższe oceny
są lepsze (por. :meth:`Rozklad.odwrocony`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .rozklad import Liczba, Rozklad


class RodzajParametru(Enum):
    """Rodzaje parametrów rozkładu dostępne w dialogu."""

    WARTOSC_OCZEKIWANA = "wartość oczekiwana"
    ODCHYLENIE_STD = "odchylenie standardowe"
    SEMIODCHYLENIE_STD_DOLNE = "dolne semiodchylenie standardowe"
    SEMIODCHYLENIE_STD_GORNE = "górne semiodchylenie standardowe"
    SEMIODCHYLENIE_PRZECIETNE_DOLNE = "dolne semiodchylenie przeciętne"
    SEMIODCHYLENIE_PRZECIETNE_GORNE = "górne semiodchylenie przeciętne"
    P_NIE_WIECEJ = "prawdopodobieństwo wartości nie wyższej niż próg"
    P_NIE_MNIEJ = "prawdopodobieństwo wartości nie niższej niż próg"
    MEDIANA = "mediana"
    KWARTYL_DOLNY = "pierwszy kwartyl"
    KWARTYL_GORNY = "trzeci kwartyl"
    KWANTYL = "kwantyl"
    DOMINANTA = "dominanta"
    MINIMUM = "najgorsza wartość"
    MAKSIMUM = "najlepsza wartość"


#: Rodzaje, dla których wymagany jest próg (wartość zmiennej losowej).
_WYMAGA_PROGU = {RodzajParametru.P_NIE_WIECEJ, RodzajParametru.P_NIE_MNIEJ}

#: Rodzaje, dla których próg jest opcjonalnym punktem odniesienia (domyślnie μ).
_ODNIESIENIE = {
    RodzajParametru.SEMIODCHYLENIE_STD_DOLNE,
    RodzajParametru.SEMIODCHYLENIE_STD_GORNE,
    RodzajParametru.SEMIODCHYLENIE_PRZECIETNE_DOLNE,
    RodzajParametru.SEMIODCHYLENIE_PRZECIETNE_GORNE,
}

#: Domyślny kierunek: True — wyższe lepsze (Q_1), False — niższe lepsze (Q_2).
#: Dla górnych semiodchyleń kierunku nie ustalono; musi go podać decydent
#: (DECYZJE.md).
_DOMYSLNY_KIERUNEK: dict = {
    RodzajParametru.WARTOSC_OCZEKIWANA: True,
    RodzajParametru.ODCHYLENIE_STD: False,
    RodzajParametru.SEMIODCHYLENIE_STD_DOLNE: False,
    RodzajParametru.SEMIODCHYLENIE_PRZECIETNE_DOLNE: False,
    RodzajParametru.P_NIE_WIECEJ: False,
    RodzajParametru.P_NIE_MNIEJ: True,
    RodzajParametru.MEDIANA: True,
    RodzajParametru.KWARTYL_DOLNY: True,
    RodzajParametru.KWARTYL_GORNY: True,
    RodzajParametru.KWANTYL: True,
    RodzajParametru.DOMINANTA: True,
    RodzajParametru.MINIMUM: True,
    RodzajParametru.MAKSIMUM: True,
}


@dataclass(frozen=True)
class Parametr:
    """Parametr rozkładu ocen wybrany przez decydenta.

    :param rodzaj: rodzaj parametru.
    :param prog: próg ``s`` dla prawdopodobieństw P(X ≤ s), P(X ≥ s),
        punkt odniesienia dla semiodchyleń (``None`` — od wartości
        oczekiwanej) albo rząd kwantyla dla :attr:`RodzajParametru.KWANTYL`.
    :param wyzsze_lepsze: kierunek preferencji (True — zbiór Q_1, False — Q_2);
        ``None`` oznacza kierunek domyślny dla danego rodzaju.

    >>> Parametr(RodzajParametru.P_NIE_MNIEJ, 6).wyzsze_lepsze
    True
    """

    rodzaj: RodzajParametru
    prog: Optional[Liczba] = None
    wyzsze_lepsze: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.rodzaj in _WYMAGA_PROGU and self.prog is None:
            raise ValueError(f"parametr „{self.rodzaj.value}” wymaga progu")
        if self.rodzaj is RodzajParametru.KWANTYL and (self.prog is None or not 0 < self.prog <= 1):
            raise ValueError("kwantyl wymaga rzędu z przedziału (0, 1]")
        if self.wyzsze_lepsze is None:
            if self.rodzaj not in _DOMYSLNY_KIERUNEK:
                raise ValueError(
                    f"dla parametru „{self.rodzaj.value}” trzeba podać kierunek (wyzsze_lepsze)"
                )
            object.__setattr__(self, "wyzsze_lepsze", _DOMYSLNY_KIERUNEK[self.rodzaj])

    def wartosc(self, r: Rozklad) -> Liczba:
        """Wartość parametru dla rozkładu ``r``."""
        R = RodzajParametru
        k = self.rodzaj
        if k is R.WARTOSC_OCZEKIWANA:
            return r.wartosc_oczekiwana()
        if k is R.ODCHYLENIE_STD:
            return r.odchylenie_std()
        if k is R.SEMIODCHYLENIE_STD_DOLNE:
            return r.semiodchylenie_std(self.prog, dolne=True)
        if k is R.SEMIODCHYLENIE_STD_GORNE:
            return r.semiodchylenie_std(self.prog, dolne=False)
        if k is R.SEMIODCHYLENIE_PRZECIETNE_DOLNE:
            return r.semiodchylenie_przecietne(self.prog, dolne=True)
        if k is R.SEMIODCHYLENIE_PRZECIETNE_GORNE:
            return r.semiodchylenie_przecietne(self.prog, dolne=False)
        if k is R.P_NIE_WIECEJ:
            return r.p_nie_wiecej(self.prog)
        if k is R.P_NIE_MNIEJ:
            return r.p_nie_mniej(self.prog)
        if k is R.MEDIANA:
            return r.mediana()
        if k is R.KWARTYL_DOLNY:
            return r.kwartyl_dolny()
        if k is R.KWARTYL_GORNY:
            return r.kwartyl_gorny()
        if k is R.KWANTYL:
            return r.kwantyl(self.prog)
        if k is R.DOMINANTA:
            return r.dominanta()
        if k is R.MINIMUM:
            return r.minimum()
        if k is R.MAKSIMUM:
            return r.maksimum()
        raise AssertionError(k)  # pragma: no cover

    def lepszy(self, a: Liczba, b: Liczba) -> Liczba:
        """Lepsza z dwóch wartości parametru według jego kierunku."""
        return max(a, b) if self.wyzsze_lepsze else min(a, b)

    def optymistyczna(self, wartosci) -> Liczba:
        """Wartość optymistyczna z ciągu wartości parametru (wzór 8.6)."""
        w = list(wartosci)
        return max(w) if self.wyzsze_lepsze else min(w)

    def pesymistyczna(self, wartosci) -> Liczba:
        """Wartość pesymistyczna z ciągu wartości parametru (wzór 8.7)."""
        w = list(wartosci)
        return min(w) if self.wyzsze_lepsze else max(w)

    def opis(self) -> str:
        """Krótki opis do wyświetlenia, np. ``P(X ≥ 6)``."""
        R = RodzajParametru
        if self.rodzaj is R.P_NIE_MNIEJ:
            return f"P(X ≥ {self.prog})"
        if self.rodzaj is R.P_NIE_WIECEJ:
            return f"P(X ≤ {self.prog})"
        if self.rodzaj is R.KWANTYL:
            return f"kwantyl rzędu {self.prog}"
        if self.rodzaj in _ODNIESIENIE and self.prog is not None:
            return f"{self.rodzaj.value} od {self.prog}"
        return self.rodzaj.value
