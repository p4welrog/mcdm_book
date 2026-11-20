# Wielokryterialne wspomaganie decyzji — metody z książki

Implementacje metod z książki „Wielokryterialne wspomaganie decyzji. Metody i zastosowania” (red. T. Trzaskalik, PWE 2014) oraz strona `index.html`, która uruchamia je w przeglądarce przez [Pyodide](https://pyodide.org).

| Pakiet | Zawartość |
|---|---|
| `mcdm_book` | metody addytywne (rozdz. 2: SAW, scoring, FSAW, SMART, SMARTER), AHP i metody pokrewne (rozdz. 3.1–3.5: AHP, REMBRANDT, rozmyty AHP Mikhailova, ANP z syntezą BOCR, rozmyta ANP Changa), metody punktów referencyjnych (rozdz. 7.1–7.3: TOPSIS, rozmyty TOPSIS, VIKOR), programowanie kompromisowe i dobór metody (rozdz. 9.3); interfejs JSON |
| `mcdm_cd` | port programów z płyty CD (K. Targiel): StDom 1.09b (dominacje stochastyczne) i MCDM 1.00 (STEM-DPR, INSDECM) |

## Interfejs JSON (`mcdm_book`)

```bash
python -m mcdm_book methods                 # lista metod, wymaganych danych i opcji
python -m mcdm_book example                 # przykłady z książki
python -m mcdm_book example P7.4 > z.json
python -m mcdm_book run z.json              # wynik w JSON
python -m mcdm_book run z.json --method topsis --option metric=1
```

Zadanie:

```json
{"method": "topsis", "options": {"metric": 2},
 "problem": {"variants": ["a1", "a2"],
             "criteria": [{"name": "cena", "direction": "min", "weight": 0.6},
                          {"name": "jakość", "direction": "max", "weight": 0.4}],
             "values": [[120, 7], [100, 5]]}}
```

Oceny rozmyte zapisuje się jako trójki `[l, m, u]`. Pola kryteriów zależne od metody: `weight`, `fuzzy_weight` (FSAW), `swing` i `scale` (SMART), `rank` (SMARTER), `max_points` (scoring).

Metody z rozdz. 3 przyjmują macierze porównań w polach zadania: `criteria_comparisons` (n×n) i `comparisons` (`{"nazwa kryterium": macierz m×m}`). Elementy macierzy mogą być liczbami, napisami typu `"1/7"` albo trójkami `[l, m, u]` (rozmyty AHP). Puste pola (`null`) są uzupełniane odwrotnością elementu symetrycznego, a w REMBRANDT wartością −δ. Kryterium bez macierzy w AHP dostaje wektor skali z ocen liczbowych w `values`. Model Mikhailova rozwiązuje wbudowany solver programowania liniowego (`mcdm_book/lp.py`), więc strona nie musi ładować scipy.

PROMETHEE i EXPROM (rozdz. 6): pola kryteriów `type` (1–6, tabl. 6.1), `q`, `p`, `s`, `v` (weto), `L` (EXPROM); metody `promethee_i` (ranking częściowy z relacjami P, I, R), `promethee_ii`, `promethee_ii_veto`, `exprom` (opcja `ranking`: complete | partial), `exprom_veto` oraz stochastyczne `promethee_ii_sd`, `exprom_ii_sd` — ocena to rozkład `{"values": [...], "probs": [...]}` albo obserwacje `{"obs": [...]}`, progi liczbą albo `[α, β]` (α + β·μ), opcje `risk` (DARA | INARA) i `dominances` (np. `["FSD", "SSD", "AFSD:0.333", "ASSD:0.2"]`); dominacje liczy `mcdm_cd`.

ANP (`anp`, `fuzzy_anp`) opisuje sieć polami zadania: `clusters` (komponenty kryteriów; warianty tworzą osobny komponent `variants_cluster`), `influences` (`{"element": [elementy, na które wpływa]}`) albo `dependency_matrix` (0/1, jak w przykładzie 3.11), `comparisons` (`{"element": {"komponent": macierz}}` — porównania elementów, na które element wpływa; zamiast macierzy można podać wektor wag) oraz `cluster_comparisons` (`{"komponent": {"clusters": [...], "matrix": ...}}`) albo gotową macierz wag komponentów `cluster_weights`. Supermacierz graniczna to granica potęg (3.49), a gdy sieć ma cykl i potęgi nie są zbieżne — granica Cesàro (3.48), liczona jako granica potęg ((I + Ω̄)/2). Struktura BOCR: pole `subnets` z sieciami (lub gotowymi priorytetami `priorities`) dla kluczy B, O, C, R, wagi `bocr_weights` i opcja `formula` (3.50)–(3.53). Przykład P3.12 pokazuje pełny zapis sieci.

Wynik każdej metody ma te same pola: `scores` (wartości i kierunek: im więcej/mniej, tym lepiej), `ranks` (z remisami), `ranking`, `best`, `steps` (wyniki pośrednie metody) i `notes` (uwagi, m.in. przyjęte konwencje).

W Pythonie: `from mcdm_book import run; run({...})`.

### Dobór metody

`{"method": "select_method", "profile": {...}}` zwraca ranking metod pakietu dla profilu problemu. Profil opisuje rodzaje ocen, zależności między kryteriami (`interdependence` — wtedy zostają tylko metody ANP), informację o preferencjach, którą decydent potrafi podać, wymaganą postać wyniku, stosunek do kompensacji, znajomość poziomów aspiracji, znaczenie wyjaśnienia wyniku oraz wiedzę i czas decydenta. Listę pól pokazuje `python -m mcdm_book methods`.

Procedura naśladuje model Gershona (rozdz. 9.3): cechy wykluczające (np. rodzaj danych) eliminują metody, a pozostałe są oceniane w skali 0–10 z wagami wynikającymi z profilu. Kolejność ustala odległość L1 od rozwiązania idealnego według wzoru (9.1). Ta sama odległość jest dostępna jako zwykła metoda `compromise`; odtwarza ona wyniki zbiorów R9.2 (model Gershona) i R9.3 (procedura Tecle'a).

Oceny SAW, SMART i TOPSIS opierają się na zbiorze R9.2. Oceny pozostałych metod są moje i można je nadpisać opcją `scores`.

## Zgodność z książką

Testy (`pytest`) odtwarzają przykłady z płyty: P2.1–P2.3, P2.5, P2.7, P2.11, P3.3, P3.4, P3.7, P3.10, P3.12–P3.14, P6.2–P6.16, P7.1, P7.3, P7.4, R9.2, R9.3, tablice 2.1–2.2 i rozmyty TOPSIS z rozdz. 14 (oceny ofert 0,2706; 0,6507; 0,1656; 0,3391; 0,5145; 0,5376).

Tam, gdzie książka zawiera błąd albo jest niejednoznaczna, pakiet przyjmuje wersję poprawną i to opisuje:
- **Normalizacja kosztowa:** liczona jako (max − f)/(max − min). Wzory (2.4) i (2.9) w druku są tożsame z (2.3) i (2.8).
- **Funkcja wartości SMART:** interpolacja odcinkowo-liniowa przez punkty bisekcji albo parabola MNK. Parabolę stosuje Excel w przykładach 2.5 i 2.7.
- **Rozmyty TOPSIS:** kryteria kosztowe są normalizowane przez min l, jak w rozdz. 14. Wzór (7.10) z druku jest dostępny jako opcja `cost_norm="min_u"`.
- **AHP:** λmax w metodzie Saaty'ego liczę z (Aω)ᵢ/ωᵢ, jak w przykładzie 3.3. Wzór (3.19) w druku ma ωᵀA. Domyślną metodą jest wektor własny, a metodę Saaty'ego i metodę potęgową z ε wybiera się opcją. Wartość r dla m > 10 pochodzi z Saaty (1980), spoza tablicy 3.1.
- **REMBRANDT:** domyślnie γ = ln √2 dla kryteriów i ln 2 dla wariantów, jak w (3.28). Przykład 3.7 liczy warianty z ln √2. Wektor końcowy jest agregowany geometrycznie (3.31), bo wartości z druku nie dają się odtworzyć.
- **ANP:** kolumny supermacierzy ważonej, które nie sumują się do 1, są normalizowane (jak w przykładzie 3.12). Rozmyta ANP dopisuje stopień 1 komponentowi, ze względu na który porównujemy (3.58), więc przekątna macierzy wag komponentów jest niezerowa (tabl. 6 przykładu 3.14). Gdy kolumny supermacierzy granicznej się różnią (np. hierarchia z pętlami `sinks="loop"`), wektor skali pochodzi z kolumn elementów źródłowych albo z kolumny wskazanej opcją `read_from`. Synteza BOCR domyślnie używa priorytetów „idealnych” (podzielonych przez największy), jak Super Decisions; tak odtwarza się rys. 15 przykładu 3.13.
- **PROMETHEE II / EXPROM II z wetem:** wskaźniki niezgodności wg wzoru (6.20) — d_k(aⁱ, aʲ) rośnie z przewagą aʲ nad aⁱ. Przykłady 6.7 i 6.10 liczą je odwrotnie (z f(aⁱ) − f(aʲ)); ich wynik odtwarza opcja `veto_direction="example"`. Przepływy z σ i ω są sumami (bez dzielenia przez m − 1), jak we wzorach (6.23), (6.38); opcja `divide`.
- **VIKOR:** reguła wyboru rozwiązania kompromisowego jest wzięta z Opricovic i Tzeng (2004), bo w książce wyliczenie przypadków jest niekompletne. Warunek W2 domyślnie wymaga, by a′ był najlepszy w rankingach S i R (jak w książce).

Rozbieżności w przykładach (P2.1, P2.7, P2.11, P3.14, P6.7, P6.10, P7.1, P7.4) opisano w komentarzach testów.

`mcdm_cd` sprawdzono z raportami StDom z przykładów 5.19, 6.13 i 6.15 oraz z przebiegami przykładów 8.2 i 8.4.

## Strona

`index.html` to jeden plik, który można otworzyć w przeglądarce albo opublikować przez GitHub Pages (Settings → Pages → Deploy from a branch → `main`, `/ (root)`). Przy pierwszym otwarciu potrzebny jest internet, bo Pyodide 0.26.4 jest ładowany z `cdn.jsdelivr.net`. Pliki wczytane przez użytkownika nie opuszczają przeglądarki.

Test strony w przeglądarce: `python tests/e2e_browser.py`. Skrypt sprawdza przykłady z książki we wszystkich zakładkach, edytor AHP, dobór metody i dialogi STEM-DPR oraz INSDECM. Wymaga Playwright; opcje i sposób uruchomienia bez dostępu do CDN opisuje nagłówek skryptu.

Plik buduje skrypt `python web/build.py`: łączy szablon `web/template.html`, kod łączący stronę z pakietami (`web/web.py`), źródła obu pakietów, pliki .mcf z płyty oraz bibliotekę [xlrd](https://github.com/python-excel/xlrd) 2.0.1 (licencja BSD, `web/vendor/`). Po każdej zmianie w pakietach trzeba go uruchomić ponownie.
