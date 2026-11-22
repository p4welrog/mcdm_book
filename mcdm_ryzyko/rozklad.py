"""Dyskretny rozkład prawdopodobieństwa oceny wariantu względem kryterium.

W książce ocena wariantu a^i względem kryterium f_k jest zmienną losową
o skończonej liczbie wartości (rozdz. 1.5.4, założenia w 8.2). Klasa
:class:`Rozklad` przechowuje taki rozkład w postaci uporządkowanej
i udostępnia wielkości, z których korzystają dominacje stochastyczne
(dystrybuanta F i dekumulanta F̄ z tabl. 1.1) oraz parametry pokazywane
decydentowi w dialogu (rozdz. 8.3 krok 3, 8.4, instrukcja MCDM, rozdz. 4.2.1).

Obliczenia są prowadzone w typie liczb podanych na wejściu: dla ``int``
i ``fractions.Fraction`` wyniki (poza pierwiastkami) są dokładne.
"""

from __future__ import annotations

import math
from collections import Counter
from fractions import Fraction
from numbers import Real
from typing import Iterable, Sequence, Union

Liczba = Union[int, float, Fraction]

#: Dopuszczalne odchylenie sumy prawdopodobieństw od 1. Programy z płyty
#: sprawdzają, czy prawdopodobieństwa sumują się do jedynki (instrukcja
#: MCDM, rozdz. 2.3; instrukcja StDom, rozdz. 3.3), a StDom porównuje liczby
#: z dokładnością 1e-6 (rozdz. 3.6).
TOLERANCJA_SUMY = 1e-6


def _na_liczbe(x: object) -> Liczba:
    """Zamienia napis w rodzaju ``"3/7"`` lub ``"0,25"`` na liczbę."""
    if isinstance(x, str):
        return Fraction(x.strip().replace(",", "."))
    if isinstance(x, bool) or not isinstance(x, Real):
        raise TypeError(f"oczekiwano liczby, otrzymano {x!r}")
    return x  # type: ignore[return-value]


class Rozklad:
    """Rozkład dyskretny: rosnący ciąg wartości i ich prawdopodobieństwa.

    Przy tworzeniu wartości są sortowane, powtórzenia scalane (prawdopodobieństwa
    sumowane), a wartości o zerowym prawdopodobieństwie pomijane, bo nie należą
    do nośnika rozkładu (por. DECYZJE.md, wpis o plikach ``.mcf``).

    >>> r = Rozklad([3, 1, 2], ["1/4", "1/2", "1/4"])
    >>> r.wartosci, r.wartosc_oczekiwana()
    ((1, 2, 3), Fraction(7, 4))
    """

    __slots__ = ("_x", "_p")

    def __init__(self, wartosci: Iterable[object], prawdopodobienstwa: Iterable[object]):
        xs = [_na_liczbe(v) for v in wartosci]
        ps = [_na_liczbe(p) for p in prawdopodobienstwa]
        if len(xs) != len(ps):
            raise ValueError("liczba wartości i prawdopodobieństw musi być taka sama")
        if any(p < 0 for p in ps):
            raise ValueError("prawdopodobieństwa nie mogą być ujemne")
        suma = sum(ps)
        if abs(suma - 1) > TOLERANCJA_SUMY:
            raise ValueError(f"prawdopodobieństwa sumują się do {suma}, a nie do 1")
        scalone: dict = {}
        for x, p in zip(xs, ps):
            if p != 0:
                scalone[x] = scalone.get(x, 0) + p
        if not scalone:
            raise ValueError("rozkład musi mieć co najmniej jedną wartość")
        klucze = sorted(scalone)
        self._x: tuple = tuple(klucze)
        self._p: tuple = tuple(scalone[k] for k in klucze)

    # --- konstruktory -------------------------------------------------------

    @classmethod
    def z_obserwacji(cls, obserwacje: Iterable[object]) -> "Rozklad":
        """Rozkład empiryczny: każda obserwacja ma prawdopodobieństwo 1/n.

        Odpowiada wprowadzaniu ocen jako obserwacji w programie MCDM
        (instrukcja, rozdz. 2.2) oraz konstrukcji rozkładów z ocen ekspertów
        w rozdz. 10.3 (każdy ekspert ma taką samą wagę).
        """
        xs = [_na_liczbe(v) for v in obserwacje]
        if not xs:
            raise ValueError("brak obserwacji")
        licznik = Counter(xs)
        n = len(xs)
        return cls(list(licznik), [Fraction(c, n) for c in licznik.values()])

    @classmethod
    def pewny(cls, wartosc: object) -> "Rozklad":
        """Rozkład jednopunktowy (ocena deterministyczna)."""
        return cls([wartosc], [1])

    # --- dane podstawowe ----------------------------------------------------

    @property
    def wartosci(self) -> tuple:
        """Wartości nośnika w kolejności rosnącej."""
        return self._x

    @property
    def prawdopodobienstwa(self) -> tuple:
        """Prawdopodobieństwa odpowiadające :attr:`wartosci`."""
        return self._p

    def pary(self) -> list:
        """Lista par (wartość, prawdopodobieństwo)."""
        return list(zip(self._x, self._p))

    def __len__(self) -> int:
        return len(self._x)

    def __eq__(self, inny: object) -> bool:
        if not isinstance(inny, Rozklad):
            return NotImplemented
        return self._x == inny._x and self._p == inny._p

    def __hash__(self) -> int:
        return hash((self._x, self._p))

    def __repr__(self) -> str:
        pary = ", ".join(f"{x}: {p}" for x, p in self.pary())
        return f"Rozklad({{{pary}}})"

    # --- prawdopodobieństwa progowe ----------------------------------------

    def dystrybuanta(self, x: Liczba) -> Liczba:
        """F(x) = P(X ≤ x) (tabl. 1.1, oznaczenia)."""
        return sum((p for v, p in zip(self._x, self._p) if v <= x), 0)

    def dekumulanta(self, x: Liczba) -> Liczba:
        """F̄(x) = P(X ≥ x), dekumulacyjna dystrybuanta (tabl. 1.1)."""
        return sum((p for v, p in zip(self._x, self._p) if v >= x), 0)

    def p_nie_wiecej(self, x: Liczba) -> Liczba:
        """Prawdopodobieństwo uzyskania wartości nie wyższej niż ``x``."""
        return self.dystrybuanta(x)

    def p_nie_mniej(self, x: Liczba) -> Liczba:
        """Prawdopodobieństwo uzyskania wartości nie niższej niż ``x``."""
        return self.dekumulanta(x)

    # --- położenie -------------------------------------------------------

    def wartosc_oczekiwana(self) -> Liczba:
        """μ = Σ x·p."""
        return sum((x * p for x, p in zip(self._x, self._p)), 0)

    def minimum(self) -> Liczba:
        """Najmniejsza wartość nośnika (dla kryterium maksymalizowanego: najgorsza)."""
        return self._x[0]

    def maksimum(self) -> Liczba:
        """Największa wartość nośnika."""
        return self._x[-1]

    def kwantyl(self, q: Liczba) -> Liczba:
        """Kwantyl rzędu ``q`` ∈ (0, 1]: najmniejsze x, dla którego F(x) ≥ q.

        Książka nie podaje definicji kwantyla rozkładu dyskretnego; przyjęto
        uogólnioną odwrotność dystrybuanty (DECYZJE.md).
        """
        if not 0 < q <= 1:
            raise ValueError("rząd kwantyla musi należeć do przedziału (0, 1]")
        skumulowane: Liczba = 0
        for x, p in zip(self._x, self._p):
            skumulowane += p
            if skumulowane >= q - 1e-12:
                return x
        return self._x[-1]

    def mediana(self) -> Liczba:
        """Kwantyl rzędu 1/2 (patrz :meth:`kwantyl`)."""
        return self.kwantyl(Fraction(1, 2))

    def kwartyl_dolny(self) -> Liczba:
        """Kwantyl rzędu 1/4."""
        return self.kwantyl(Fraction(1, 4))

    def kwartyl_gorny(self) -> Liczba:
        """Kwantyl rzędu 3/4."""
        return self.kwantyl(Fraction(3, 4))

    def dominanty(self) -> tuple:
        """Wszystkie wartości o największym prawdopodobieństwie, rosnąco."""
        pmax = max(self._p)
        return tuple(x for x, p in zip(self._x, self._p) if p == pmax)

    def dominanta(self) -> Liczba:
        """Najmniejsza z dominant (moda); por. :meth:`dominanty`."""
        return self.dominanty()[0]

    # --- rozproszenie ------------------------------------------------------

    def wariancja(self) -> Liczba:
        """σ² = Σ p·(x − μ)²."""
        mu = self.wartosc_oczekiwana()
        return sum((p * (x - mu) ** 2 for x, p in zip(self._x, self._p)), 0)

    def odchylenie_std(self) -> float:
        """σ, pierwiastek z wariancji."""
        return math.sqrt(self.wariancja())

    def _odniesienie(self, odniesienie: Liczba | None) -> Liczba:
        return self.wartosc_oczekiwana() if odniesienie is None else odniesienie

    def semiodchylenie_std(self, odniesienie: Liczba | None = None, *, dolne: bool = True) -> float:
        """Semiodchylenie standardowe od wartości ``odniesienie`` (domyślnie od μ).

        Dolne: √Σ_{x<t} p·(t − x)², górne: √Σ_{x>t} p·(x − t)².
        Wzór według literatury (semiwariancja Markowitza); książka wymienia
        tylko nazwę parametru (rozdz. 8.4, s. 161), zob. DECYZJE.md.
        """
        t = self._odniesienie(odniesienie)
        if dolne:
            s = sum((p * (t - x) ** 2 for x, p in zip(self._x, self._p) if x < t), 0)
        else:
            s = sum((p * (x - t) ** 2 for x, p in zip(self._x, self._p) if x > t), 0)
        return math.sqrt(s)

    def semiodchylenie_przecietne(self, odniesienie: Liczba | None = None, *, dolne: bool = True) -> Liczba:
        """Semiodchylenie przeciętne od wartości ``odniesienie`` (domyślnie od μ).

        Dolne: Σ_{x<t} p·(t − x), górne: Σ_{x>t} p·(x − t) (DECYZJE.md).
        """
        t = self._odniesienie(odniesienie)
        if dolne:
            return sum((p * (t - x) for x, p in zip(self._x, self._p) if x < t), 0)
        return sum((p * (x - t) for x, p in zip(self._x, self._p) if x > t), 0)

    # --- przekształcenia -----------------------------------------------------

    def odwrocony(self) -> "Rozklad":
        """Rozkład zmiennej −X.

        Kryterium minimalizowane sprowadza się do maksymalizowanego przez
        zmianę znaku ocen, tak jak w tabl. 10.5 (rozdz. 10.3).
        """
        return Rozklad([-x for x in self._x], self._p)

    def nosnik_wspolny(self, *inne: "Rozklad") -> tuple:
        """Posortowana suma nośników tego i innych rozkładów."""
        zbior = set(self._x)
        for r in inne:
            zbior.update(r._x)
        return tuple(sorted(zbior))


def rozklad(pary: Sequence[tuple]) -> Rozklad:
    """Skrót: ``rozklad([(1, "1/2"), (3, "1/2")])``."""
    return Rozklad([x for x, _ in pary], [p for _, p in pary])
