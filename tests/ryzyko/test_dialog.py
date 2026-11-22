import pytest

from mcdm_ryzyko.dialog import (
    PRZERWIJ, BlednaOdpowiedz, PytanieTakNie, PytanieWybor, Sesja, Wynik, odtworz, uruchom,
)


def _proc():
    n = 0
    while True:
        n += 1
        tak = yield PytanieTakNie(f"pytanie {n}")
        if tak:
            wybor = yield PytanieWybor("wybierz", opcje=("a", "b"))
            return Wynik("zaakceptowano", rozwiazanie=n, historia=[wybor])


def test_uruchom_z_odpowiedziami():
    w = uruchom(_proc(), [False, False, True, "b"])
    assert (w.status, w.rozwiazanie, w.historia) == ("zaakceptowano", 3, ["b"])


def test_brak_i_nadmiar_odpowiedzi():
    with pytest.raises(ValueError):
        uruchom(_proc(), [False])
    with pytest.raises(ValueError):
        uruchom(_proc(), [True, "a", True])


def test_bledna_odpowiedz_nie_zmienia_stanu():
    s = Sesja(_proc())
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz("tak")
    assert s.pytanie.tresc == "pytanie 1"
    s.odpowiedz(True)
    with pytest.raises(BlednaOdpowiedz):
        s.odpowiedz("c")
    s.odpowiedz("a")
    assert s.zakonczona and s.przebieg == [True, "a"]


def test_przerwanie():
    s = Sesja(_proc())
    s.odpowiedz(False)
    s.odpowiedz(PRZERWIJ)
    assert s.wynik.status == "przerwano"


def test_odtworzenie():
    s = odtworz(_proc(), [False, True])
    assert s.pytanie.tresc == "wybierz"
