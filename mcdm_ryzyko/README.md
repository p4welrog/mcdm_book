# mcdm_ryzyko

Dominacje stochastyczne oraz interaktywne metody STEM-DPR i INSDECM dla
dyskretnych problemów decyzyjnych w warunkach ryzyka, według rozdz. 1.3
i 8.3–8.4 książki T. Trzaskalik (red.), *Wielokryterialne wspomaganie decyzji.
Metody i zastosowania*, PWE 2014. Czysty Python ≥ 3.10, bez zależności
(opcjonalnie `xlrd` do plików `.mcf`), działa w Pyodide.

Implementacja powstała wyłącznie na podstawie książki, instrukcji użytkownika
programów MCDM 1.00 i StDom 1.09b oraz opublikowanych wyników przykładów.
Decyzje interpretacyjne: [`DECYZJE.md`](DECYZJE.md); różnice z drukiem:
[`ROZBIEZNOSCI.md`](ROZBIEZNOSCI.md).

## Rozkłady i dominacje

```python
from mcdm_ryzyko import Rozklad, porownaj, Postawa, Relacja

F1 = Rozklad([2, 8], ["0,8", "0,2"])          # prawdopodobieństwa: liczby lub napisy
F2 = Rozklad([1, 4], ["0,4", "0,6"])
w = porownaj(F1, F2)                           # F1 względem F2
w.zachodzi(Relacja.SSD), w.najsilniejsza(Postawa.AWERSJA)
w.eps_afsd, w.eps_assd, w.assd(0.25)           # prawie dominacje (tabl. 1.2)
F1.wartosc_oczekiwana(), F1.p_nie_mniej(4), F1.kwantyl(0.25)
```

Kryterium minimalizowane: `Rozklad.odwrocony()` albo `Kryterium(..., maksymalizowane=False)`.
Skala porządkowa: `porownaj_porzadkowo(F, G, skala)` (OFSD, OSSD, OAFSD, OASSD).

## Metody interaktywne

Procedury są generatorami pytań. `Sesja` prowadzi dialog krok po kroku
(np. w przeglądarce), `uruchom` przechodzi go na odpowiedziach zapisanych z góry.

```python
from mcdm_ryzyko import wczytaj_mcf, StemDpr, RegulaDominacji, Sesja, Prog

problem = wczytaj_mcf("dane/przyklad_8_1.mcf")
sesja = Sesja(StemDpr(problem, RegulaDominacji.awersja()).przebieg())
sesja.pytanie            # PytanieInformacje ze stanem iteracji (μ, d, wektor idealny)
sesja.odpowiedz(True)    # → następne pytanie
...
sesja.wynik.rozwiazanie  # indeks wybranego wariantu
```

INSDECM: `Insdecm(problem, regula).przebieg()`, warunki `Warunek(k, Parametr(...), granica)`.

## Testy

```
pip install -e .[mcf,test]
pytest --doctest-modules mcdm_ryzyko tests
```

Każdy test podaje miejsce w książce lub na płycie, z którego pochodzi oczekiwana wartość.
