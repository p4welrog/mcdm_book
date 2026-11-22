# mcdm_book — metody z książki Trzaskalika (repozytorium publiczne)

Pakiety Pythona `mcdm_book` (metody wielokryterialne, interfejs JSON) i `mcdm_cd` (port algorytmów programów StDom i MCDM 1.00 z płyty CD oraz ATO-DPR według rozdz. 8.5) oraz strona `index.html` (Pyodide), publikowana przez GitHub Pages z gałęzi `main`, katalog główny. Opis interfejsu i zgodności z książką: `README.md`.

**Repozytorium jest publiczne, a książka (PWE 2014) i płyta CD są chronione prawem autorskim.** Nie przepisuj tu zdań z książki ani z przykładów z CD: do kodu, testów, README, `method_help.py`, `print_checks.py` i komentarzy wolno brać dane liczbowe, nazwy metod, kryteriów i wariantów, numery wzorów i tablic oraz krótkie terminy; opisy pisze się własnymi słowami. Transkrypcja jest w osobnym, prywatnym repozytorium `p4welrog/mcdm_book_tekst` (klon obok tego, `../mcdm_book_tekst`); stamtąd przychodzi tylko `web/book_anchors.json` (same identyfikatory kotwic).

## Polecenia

```bash
pip install -e ".[test,mcf]"      # pytest i xlrd (część testów czyta arkusze .xls/.mcf)
pytest -q
python web/build.py               # składa index.html i web/app_examples.json; po każdej zmianie w pakietach lub web/
python tests/e2e_browser.py       # test strony w Playwright (opcje bez CDN w nagłówku skryptu)
python -m mcdm_book methods | example [ID] | run zadanie.json
```

`index.html` i `web/app_examples.json` są w repozytorium (Pages serwuje `index.html` z `main`), więc commit zmian w pakietach zawiera też przebudowany `index.html`. CI (`.github/workflows/testy.yml`) uruchamia `pytest` i sprawdza, czy `index.html` i `web/app_examples.json` odpowiadają źródłom.

## `mcdm_cd`: port do zastąpienia

Obecny `mcdm_cd` (poza `ato_dpr.py`) powstał na podstawie kodu VBA programów K. Targiela i zostanie zastąpiony implementacją napisaną od nowa (clean room) według książki, poza tym repozytorium. Nie rozwijaj go i nie kopiuj z niego kodu do `mcdm_book`. Nowej implementacji nie pisze się w sesji, która widziała ten kod.

## Konwencje

- Wynik każdej metody: `scores`, `ranks`, `ranking`, `best`, `steps`, `notes`. Przyjęte interpretacje i odstępstwa od druku idą do `notes`, a nie są ukrywane.
- Domyślnie pakiet liczy według wzorów z książki (z poprawkami z erraty). Gdy przykład w druku liczy inaczej, wariant z druku jest opcją (np. `veto_direction="example"`, `veto_test="example"`, `cost_norm="min_u"`, `relations=("FSD", "SSD")`).
- Nowy przykład z książki: wpis w `mcdm_book/examples.py`, test, wpis w `mcdm_book/print_checks.py` (test kompletności to wymusza). Nowa metoda: wpis w `METHOD_PROFILES` w `mcdm_book/selection.py` (dobór metody) i w `mcdm_book/method_help.py` (test kompletności).
- Rozbieżności wyniku z drukiem dokumentuje się w README („Zgodność z książką”) i w `print_checks.py`; pełna errata jest w repozytorium transkrypcji.
- Bez zależności spoza biblioteki standardowej w pakietach (strona działa w Pyodide bez scipy; programowanie liniowe: `mcdm_book/lp.py`). `xlrd` tylko do wczytywania plików z płyty.
