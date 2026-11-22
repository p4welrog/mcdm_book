"""Rozdz. 10, zbiór R10.5: wartości oczekiwane i relacje FSD/SSD dla 14 portfeli."""

import pytest

from mcdm_ryzyko.dominacje import Relacja as R, porownaj
from dane_testowe import rozdzial_10

DANE = rozdzial_10()
KRYTERIA = DANE["kryteria"]

#: Pary, w których wynik według definicji różni się od R10.5 (ROZBIEZNOSCI.md):
#: (kryterium, i, j) -> (w druku, według definicji). W każdym przypadku
#: odpowiednia funkcja η dotyka zera (max η⁽¹⁾ = 0 lub max η⁽²⁾ = 0).
ROZBIEZNE = {
    ("f1", 3, 8): ("SSD", "FSD"),
    ("f1", 12, 3): ("SSD", "FSD"),
    ("f1", 14, 5): ("SSD", "FSD"),
    ("f2", 14, 9): ("X", "SSD"),
}


def _najsilniejsza_fsd_ssd(w):
    # Rozdz. 10.4: w analizie uwzględniono tylko FSD i SSD.
    return "FSD" if w.zachodzi(R.FSD) else "SSD" if w.zachodzi(R.SSD) else "X"


@pytest.mark.parametrize("k", KRYTERIA)
def test_wartosci_oczekiwane_R10_5(k):
    # R10.5, kolumna μ_ik. Dla f1, f2 druk podaje średnie z symulacji
    # (przed pogrupowaniem do liczb całkowitych) — różnice do 0,02;
    # dla f3-f6 tylko zaokrąglenie (μ_44 = −26,5556 wydrukowano jako −26,55).
    tol = 0.025 if k in ("f1", "f2") else 0.006
    policzone = [float(r.wartosc_oczekiwana()) for r in DANE["rozklady"][k]]
    assert policzone == pytest.approx(DANE["mu_R10_5"][k], abs=tol)


@pytest.mark.parametrize("k", KRYTERIA)
def test_relacje_R10_5(k):
    roz = DANE["rozklady"][k]
    druk = DANE["relacje_R10_5"][k]
    for i in range(14):
        for j in range(14):
            if i == j:
                continue
            oczekiwana = druk[i][j]
            klucz = (k, i + 1, j + 1)
            if klucz in ROZBIEZNE:
                assert ROZBIEZNE[klucz][0] == oczekiwana
                oczekiwana = ROZBIEZNE[klucz][1]
            assert _najsilniejsza_fsd_ssd(porownaj(roz[i], roz[j])) == oczekiwana, klucz
