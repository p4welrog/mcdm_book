"""Funkcje odcinkowo wielomianowe (stopnia ≤ 2) na siatce punktów.

Dla rozkładów dyskretnych funkcja η⁽¹⁾ z tabl. 1.1 jest schodkowa, jej całka
η⁽²⁾ odcinkowo liniowa, a całka z η⁽²⁾ — η⁽³⁾ — odcinkowo kwadratowa.
Reprezentujemy je dokładnie: na każdym odcinku [z_t, z_{t+1}] jako
c0 + c1·s + c2·s², gdzie s = x − z_t. Dzięki temu warunki „dla każdego
x ∈ [a, b]” sprawdzamy bez próbkowania: wystarczą końce odcinków i ewentualny
wierzchołek paraboli wewnątrz odcinka.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Sequence

_POL = Fraction(1, 2)


class FunkcjaOdcinkowa:
    """Funkcja ciągła na odcinkach siatki ``wezly`` (poza stopniem 0).

    :param wezly: rosnący ciąg z_0 < … < z_n (n ≥ 1) albo jeden punkt (n = 0).
    :param wspolczynniki: dla każdego z n odcinków krotka (c0, c1, c2).
    """

    __slots__ = ("wezly", "wsp")

    def __init__(self, wezly: Sequence, wspolczynniki: Sequence[tuple]):
        if len(wspolczynniki) != max(len(wezly) - 1, 0):
            raise ValueError("liczba odcinków musi być o jeden mniejsza od liczby węzłów")
        self.wezly = tuple(wezly)
        self.wsp = tuple(tuple(c) + (0,) * (3 - len(c)) for c in wspolczynniki)

    @classmethod
    def schodkowa(cls, wezly: Sequence, wartosci: Sequence) -> "FunkcjaOdcinkowa":
        """Funkcja stała na każdym odcinku (wartości dla kolejnych odcinków)."""
        return cls(wezly, [(v, 0, 0) for v in wartosci])

    def _h(self, t: int):
        return self.wezly[t + 1] - self.wezly[t]

    def calka_od_lewej(self) -> "FunkcjaOdcinkowa":
        """G(x) = ∫_a^x f(y) dy, a = z_0 (stopień f co najwyżej 1)."""
        nowe = []
        G = 0
        for t, (c0, c1, c2) in enumerate(self.wsp):
            if c2:
                raise ValueError("całkowanie funkcji kwadratowej nie jest potrzebne")
            nowe.append((G, c0, c1 * _POL))
            h = self._h(t)
            G = G + c0 * h + c1 * h * h * _POL
        return FunkcjaOdcinkowa(self.wezly, nowe)

    def calka_od_prawej(self) -> "FunkcjaOdcinkowa":
        """R(x) = ∫_x^b f(y) dy, b = z_n (stopień f co najwyżej 1)."""
        nowe = []
        R = 0
        for t in range(len(self.wsp) - 1, -1, -1):
            c0, c1, c2 = self.wsp[t]
            if c2:
                raise ValueError("całkowanie funkcji kwadratowej nie jest potrzebne")
            h = self._h(t)
            # ∫_s^h (c0 + c1·u) du = c0·h + c1·h²/2 − c0·s − c1·s²/2
            stala = R + c0 * h + c1 * h * h * _POL
            nowe.append((stala, -c0, -c1 * _POL))
            R = stala
        nowe.reverse()
        return FunkcjaOdcinkowa(self.wezly, nowe)

    def wartosc_w_wezle(self, t: int):
        """Wartość w węźle z_t (dla funkcji ciągłych; z_n — granica lewostronna)."""
        if t < len(self.wsp):
            return self.wsp[t][0]
        c0, c1, c2 = self.wsp[-1]
        h = self._h(t - 1)
        return c0 + c1 * h + c2 * h * h

    def wartosc(self, x):
        """Wartość w punkcie ``x`` ∈ [z_0, z_n] (na odcinku prawostronnie domkniętym z lewej)."""
        if not self.wsp:
            raise ValueError("funkcja określona w jednym punkcie")
        if x < self.wezly[0] or x > self.wezly[-1]:
            raise ValueError("punkt poza dziedziną")
        t = 0
        while t + 1 < len(self.wsp) and x >= self.wezly[t + 1]:
            t += 1
        c0, c1, c2 = self.wsp[t]
        s = x - self.wezly[t]
        return c0 + c1 * s + c2 * s * s

    def _kandydaci(self, t: int):
        c0, c1, c2 = self.wsp[t]
        h = self._h(t)
        yield c0
        yield c0 + c1 * h + c2 * h * h
        if c2:
            s = -c1 * _POL / c2
            if 0 < s < h:
                yield c0 + c1 * s + c2 * s * s

    def maksimum(self):
        """Największa wartość na [z_0, z_n] (dla funkcji schodkowej: z wartości odcinków)."""
        return max(v for t in range(len(self.wsp)) for v in self._kandydaci(t))

    def minimum(self):
        """Najmniejsza wartość na [z_0, z_n]."""
        return min(v for t in range(len(self.wsp)) for v in self._kandydaci(t))

    def przesun(self, stala) -> "FunkcjaOdcinkowa":
        """f(x) + stała."""
        return FunkcjaOdcinkowa(self.wezly, [(c0 + stala, c1, c2) for c0, c1, c2 in self.wsp])
