"""Dialog z decydentem bez wątków i bez blokującego ``input()``.

Procedura interaktywna (STEM-DPR, INSDECM) jest generatorem: w każdym
kroku dialogu oddaje obiekt :class:`Pytanie` i czeka na odpowiedź przesłaną
przez ``send``; po zakończeniu zwraca wynik (``StopIteration.value``).
Zgodnie z rys. 8.1 faza dialogu i faza obliczeniowa przeplatają się, a cały
stan obliczeń jest w generatorze, więc:

* :class:`Sesja` prowadzi dialog krok po kroku (np. w przeglądarce przez
  Pyodide): ``sesja.pytanie`` → ``sesja.odpowiedz(x)`` → kolejne pytanie,
* :func:`uruchom` przechodzi cały dialog na odpowiedziach zapisanych z góry
  (testy, odtwarzanie przykładów z książki),
* :attr:`Sesja.przebieg` to lista przyjętych odpowiedzi; ponowne
  uruchomienie z tą listą (:func:`odtworz`) odtwarza sesję, bo obliczenia
  są deterministyczne.

Odpowiedź :data:`PRZERWIJ` odpowiada przyciskowi „Anuluj” w programie MCDM
(instrukcja, rozdz. 3-4) i kończy procedurę na dowolnym pytaniu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generator, Iterable, List, Optional, Sequence


class _Przerwij:
    __slots__ = ()

    def __repr__(self) -> str:
        return "PRZERWIJ"


#: Odpowiedź przerywająca procedurę („Anuluj”).
PRZERWIJ = _Przerwij()


class BlednaOdpowiedz(ValueError):
    """Odpowiedź nie pasuje do pytania; pytanie pozostaje aktywne."""


class ProceduraPrzerwana(Exception):
    """Zgłaszane w generatorze procedury po odpowiedzi :data:`PRZERWIJ`."""


@dataclass
class Pytanie:
    """Pytanie do decydenta.

    Podklasy określają rodzaj oczekiwanej odpowiedzi w :meth:`sprawdz`
    i niosą w polach dane potrzebne do wyświetlenia (stan iteracji).

    :param tresc: treść pytania do wyświetlenia.
    """

    tresc: str

    def sprawdz(self, odpowiedz: Any) -> Any:
        """Sprawdza i normalizuje odpowiedź; zgłasza :class:`BlednaOdpowiedz`."""
        return odpowiedz


@dataclass
class PytanieTakNie(Pytanie):
    """Pytanie z odpowiedzią Tak/Nie (``bool``)."""

    def sprawdz(self, odpowiedz: Any) -> bool:
        if not isinstance(odpowiedz, bool):
            raise BlednaOdpowiedz(f"oczekiwano True albo False, otrzymano {odpowiedz!r}")
        return odpowiedz


@dataclass
class PytanieWybor(Pytanie):
    """Wybór jednej z opcji (odpowiedź: element ``opcje``)."""

    opcje: Sequence = ()

    def sprawdz(self, odpowiedz: Any) -> Any:
        if odpowiedz not in self.opcje:
            raise BlednaOdpowiedz(f"odpowiedź {odpowiedz!r} spoza opcji {list(self.opcje)!r}")
        return odpowiedz


@dataclass
class Wynik:
    """Wspólna część wyniku procedury.

    :param status: ``"zaakceptowano"``, ``"brak_rozwiazania"`` albo ``"przerwano"``.
    :param rozwiazanie: indeks wybranego wariantu albo None.
    """

    status: str
    rozwiazanie: Optional[int] = None
    historia: List[Any] = field(default_factory=list)


Generator_ = Generator[Pytanie, Any, Wynik]


class Sesja:
    """Dialog prowadzony krok po kroku.

    >>> def proc():
    ...     a = yield PytanieTakNie("Czy rozwiązanie jest satysfakcjonujące?")
    ...     return Wynik("zaakceptowano" if a else "brak_rozwiazania")
    >>> s = Sesja(proc())
    >>> s.pytanie.tresc
    'Czy rozwiązanie jest satysfakcjonujące?'
    >>> s.odpowiedz(True) is None, s.wynik.status
    (True, 'zaakceptowano')
    """

    def __init__(self, generator: Generator_):
        self._gen = generator
        self.przebieg: List[Any] = []
        self.wynik: Optional[Wynik] = None
        self.pytanie: Optional[Pytanie] = None
        self._krok(lambda: next(self._gen))

    @property
    def zakonczona(self) -> bool:
        return self.wynik is not None

    def _krok(self, f: Callable[[], Pytanie]) -> None:
        try:
            self.pytanie = f()
        except StopIteration as e:
            self.pytanie = None
            self.wynik = e.value

    def odpowiedz(self, odpowiedz: Any) -> Optional[Pytanie]:
        """Przekazuje odpowiedź na bieżące pytanie; zwraca następne albo None.

        Błędna odpowiedź zgłasza :class:`BlednaOdpowiedz`, a pytanie pozostaje
        bez zmian (można odpowiedzieć ponownie).
        """
        if self.zakonczona:
            raise RuntimeError("procedura już się zakończyła")
        if odpowiedz is PRZERWIJ:
            self.przebieg.append(PRZERWIJ)
            try:
                self._gen.throw(ProceduraPrzerwana())
            except (ProceduraPrzerwana, StopIteration):
                pass
            finally:
                self._gen.close()
            self.pytanie = None
            self.wynik = Wynik("przerwano")
            return None
        znormalizowana = self.pytanie.sprawdz(odpowiedz)
        self.przebieg.append(znormalizowana)
        self._krok(lambda: self._gen.send(znormalizowana))
        return self.pytanie


def uruchom(generator: Generator_, odpowiedzi: Iterable[Any]) -> Wynik:
    """Przechodzi dialog na podanych odpowiedziach i zwraca wynik.

    Zgłasza ``ValueError``, gdy odpowiedzi zabraknie albo gdy zostaną
    niewykorzystane.
    """
    s = Sesja(generator)
    lista = list(odpowiedzi)
    for nr, odp in enumerate(lista):
        if s.zakonczona:
            raise ValueError(f"procedura zakończyła się po {nr} odpowiedziach, zostało {len(lista) - nr}")
        try:
            s.odpowiedz(odp)
        except BlednaOdpowiedz as e:
            raise ValueError(f"odpowiedź nr {nr + 1} ({odp!r}) na pytanie {s.pytanie.tresc!r}: {e}") from e
    if not s.zakonczona:
        raise ValueError(f"zabrakło odpowiedzi; oczekuje pytanie: {s.pytanie.tresc!r}")
    return s.wynik


def odtworz(generator: Generator_, przebieg: Iterable[Any]) -> Sesja:
    """Odtwarza sesję z listy odpowiedzi; zwraca sesję w stanie po ostatniej z nich."""
    s = Sesja(generator)
    for odp in przebieg:
        s.odpowiedz(odp)
    return s
