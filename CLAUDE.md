# mcdm_book — metody z książki Trzaskalika (repozytorium publiczne)

Pakiety Pythona `mcdm_book` (metody wielokryterialne, interfejs JSON, ATO-DPR) i `mcdm_ryzyko` (dominacje stochastyczne, STEM-DPR, INSDECM) oraz strona `index.html` (Pyodide), publikowana przez GitHub Pages z gałęzi `main`, katalog główny. Opis interfejsu i zgodności z książką: `README.md`.

**Repozytorium jest publiczne, a książka (PWE 2014) i płyta CD są chronione prawem autorskim.** Nie przepisuj tu zdań z książki ani z przykładów z CD: do kodu, testów, README, `method_help.py`, `print_checks.py` i komentarzy wolno brać dane liczbowe, nazwy metod, kryteriów i wariantów, numery wzorów i tablic oraz krótkie terminy; opisy pisze się własnymi słowami. Transkrypcja jest w osobnym, prywatnym repozytorium `p4welrog/mcdm_book_tekst` (klon obok tego, `../mcdm_book_tekst`); stamtąd przychodzi tylko `web/book_anchors.json` (same identyfikatory kotwic).

## Polecenia

```bash
pip install -e ".[test,mcf]"      # pytest i xlrd (pliki .mcf z płyty)
pytest -q                         # razem z tests/ryzyko; doctesty: pytest -q --doctest-modules mcdm_ryzyko
python web/build.py               # składa index.html i web/app_examples.json; po każdej zmianie w pakietach lub web/
python tests/e2e_browser.py       # test strony w Playwright (opcje bez CDN w nagłówku skryptu)
python -m mcdm_book methods | example [ID] | run zadanie.json
```

`index.html` i `web/app_examples.json` są w repozytorium (Pages serwuje `index.html` z `main`), więc commit zmian w pakietach zawiera też przebudowany `index.html`. CI (`.github/workflows/testy.yml`) uruchamia `pytest` i sprawdza, czy `index.html` i `web/app_examples.json` odpowiadają źródłom.

## `mcdm_ryzyko`: clean room

`mcdm_ryzyko/` (dominacje stochastyczne, STEM-DPR, INSDECM) powstał metodą clean room w repozytorium `p4welrog/mcdm_ryzyko` (zarchiwizowane, stan 7175e13) i od 22.11.2026 rozwija się tutaj; testy są w `tests/ryzyko/`. Dawny `mcdm_cd` był portem kodu VBA programów z płyty; usunięto go razem z historią i nie wolno go odtwarzać ani jego opcji zgodności z programami.

Przy zmianach w `mcdm_ryzyko/`:
- **Wolno korzystać** z książki i przykładów z płyty (`../mcdm_book_tekst/rozdzialy`, `przyklady_cd`), instrukcji użytkownika programów (`../mcdm_book_tekst/materialy/pk_mcdm_instrukcja.md`, `pk_stdom_instrukcja.md`), plików danych (`mcdm_book/data`) i literatury naukowej, z podaniem źródła w kodzie.
- **Nie wolno korzystać** z kodu VBA programów, ich dokumentacji technicznej (klasy, procedury, zmienne), dawnego portu i opisów jego zgodności z programami. Te materiały są w prywatnym `p4welrog/mcdm_archiwum`; nie podłączaj go do sesji i nie szukaj w sieci kodu tych programów ani ich portów.
- Zmiany algorytmów robi sesja, która nie miała styczności z tymi materiałami. Integracja (`mcdm_book/ryzyko.py`, `mcdm_book/ato_dpr.py`, `web/web.py`, testy wywołań) tego nie wymaga.
- Każda decyzja interpretacyjna (książka niejednoznaczna albo sprzeczna) idzie do `mcdm_ryzyko/DECYZJE.md` z miejscem w książce i uzasadnieniem; wynik niezgodny z drukiem albo raportem programu — do `mcdm_ryzyko/ROZBIEZNOSCI.md`. Opcja odtwarzająca druk tylko wtedy, gdy uzasadnia ją tekst książki lub instrukcji.
- Testy podają miejsce źródła wartości oczekiwanej; dane testowe to same liczby (JSON), bez tekstu z książki i płyty.

## Skill

`.claude/skills/wspomaganie-decyzji-wielokryterialnych/SKILL.md` to skill prowadzący decydenta z użyciem pakietów (instalacja z tego repozytorium). Po zmianie API, nazw metod albo opcji popraw go w tym samym commicie i sprawdź jego fragmenty kodu. Kopia na koncie claude.ai aktualizuje się osobno.

## Konwencje

- Wynik każdej metody: `scores`, `ranks`, `ranking`, `best`, `steps`, `notes`. Przyjęte interpretacje i odstępstwa od druku idą do `notes`, a nie są ukrywane.
- Domyślnie pakiet liczy według wzorów z książki (z poprawkami z erraty). Gdy przykład w druku liczy inaczej, wariant z druku jest opcją (np. `veto_direction="example"`, `veto_test="example"`, `cost_norm="min_u"`, `relations=("FSD", "SSD")`).
- Nowy przykład z książki: wpis w `mcdm_book/examples.py`, test, wpis w `mcdm_book/print_checks.py` (test kompletności to wymusza). Nowa metoda: wpis w `METHOD_PROFILES` w `mcdm_book/selection.py` (dobór metody) i w `mcdm_book/method_help.py` (test kompletności).
- Rozbieżności wyniku z drukiem dokumentuje się w README („Zgodność z książką”) i w `print_checks.py`; pełna errata jest w repozytorium transkrypcji.
- Bez zależności spoza biblioteki standardowej w pakietach (strona działa w Pyodide bez scipy; programowanie liniowe: `mcdm_book/lp.py`). `xlrd` tylko do wczytywania plików z płyty.
