# MCDM 1.00 i StDom 1.09b w przeglądarce

Jednoplikowa strona `index.html` z obliczeniami programów z płyty CD do książki „Wielokryterialne wspomaganie decyzji. Metody i zastosowania” (red. T. Trzaskalik). Programy MCDM 1.00 i StDom 1.09b są autorstwa K. Targiela; strona uruchamia ich port do Pythona (pakiet `mcdm_cd`) w przeglądarce przez [Pyodide](https://pyodide.org).

## Zakładki

- **Dane**: przykłady z płyty (`przyklad_8_1.mcf` — przykłady 8.1–8.4, `Przyklad_1.mcf`) albo własny plik .mcf; rozkłady ocen i wartości oczekiwane.
- **Wykryte dominacje**: macierze FSD/SSD/TSD/AFSD dla kryteriów (arkusz „Wykryte dominacje” programu MCDM).
- **Dominacje stochastyczne (StDom)**: zwykłe i porządkowe dominacje dla dwóch rozkładów, raport i wykres dystrybuant.
- **STEM-DPR** i **INSDECM**: dialog z decydentem jak w programie MCDM.

Wyniki sprawdzono z przebiegami przykładów 8.2 (STEM-DPR → a3) i 8.4 (INSDECM → a4, a5, a9).

## Uruchomienie

Wystarczy otworzyć `index.html` w przeglądarce albo opublikować repozytorium przez GitHub Pages (Settings → Pages → Deploy from a branch → `main`, `/ (root)`). Przy pierwszym otwarciu potrzebny jest internet: Pyodide 0.26.4 jest ładowany z `cdn.jsdelivr.net`. Wczytane pliki .mcf nie opuszczają przeglądarki.

Plik zawiera wbudowane źródła pakietu `mcdm_cd` (bez modułu widżetów), pliki .mcf z płyty oraz bibliotekę [xlrd](https://github.com/python-excel/xlrd) 2.0.1 (licencja BSD, tekst licencji dołączony w pliku) do odczytu plików .mcf.
