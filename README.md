# Wielokryterialne wspomaganie decyzji — metody z książki

Implementacje metod z książki „Wielokryterialne wspomaganie decyzji. Metody i zastosowania” (red. T. Trzaskalik, PWE 2014) oraz strona `index.html`, która uruchamia je w przeglądarce przez [Pyodide](https://pyodide.org).

| Pakiet | Zawartość |
|---|---|
| `mcdm_book` | metody addytywne (rozdz. 2: SAW, scoring, FSAW, SMART, SMARTER), AHP i metody pokrewne (rozdz. 3.1–3.5: AHP, REMBRANDT, rozmyty AHP Mikhailova, ANP z syntezą BOCR, rozmyta ANP Changa), metody punktów referencyjnych (rozdz. 7.1–7.3: TOPSIS, rozmyty TOPSIS, VIKOR), programowanie kompromisowe i dobór metody (rozdz. 9.3); interfejs JSON |
| `mcdm_cd` | port programów z płyty CD (K. Targiel): StDom 1.09b (dominacje stochastyczne) i MCDM 1.00 (STEM-DPR, INSDECM) oraz ATO-DPR (8.5) |

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

MACBETH i metody werbalne (rozdz. 4):
- `macbeth` — kryterium z polem `macbeth`: `levels` (poziomy jakościowe albo liczbowe; liczby wariantów są interpolowane odcinkowo liniowo jak w M-MACBETH; bez `levels` porównuje się warianty), `judgements` (macierz ocen różnic atrakcyjności: wiersz lepszy od kolumny; 0 / `"no"` — równie atrakcyjne, 1–6 albo nazwy `"very weak"` … `"extreme"` / `"bardzo mała"` … `"ekstremalna"`, zakres `[s, t]`, `"positive"`), `upper`, `lower` (poziomy 100 i 0). Kryterium bez `macbeth` ma gotowe oceny w skali MACBETH. Wagi: pole zadania `criteria_judgements` (macierz kryteriów; wiersz n+1 to element odniesienia `[ all lower ]`) albo `weight`. Skala z zadania PL-MACBETH (4.13), jednoznaczność przez (4.14)–(4.16) (własny sympleks); przy niespójnych ocenach komunikat wskazuje pojedyncze zmiany kategorii, które przywracają spójność;
- `macbeth_scale` — skala jednej macierzy (np. wagi kryteriów, przykład 4.2);
- `zapros` — kryteria z polem `scale` (oceny od najlepszej), pole `jos` (grupy ocen wg rang) albo `y_comparisons` (macierz P/I porównań wektorów ze zbioru Y: najlepszy, potem kolejne gorsze oceny); wynik: porządek częściowy (`steps.relations`, `steps.edges`), ranga = poziom;
- `zapros_iii` — `jscv` (wariacje od najmniej dotkliwej, np. `"C1>C2"`) albo `jsqv` (łączone w JSCV) albo `qv_comparisons` (tablice porównań wariacji); FIQ, rangi i rangi „rozmyte” (`steps.rank_low`, `rank_high`). Relację preferencji domyka się przechodnio (jak w książce), dodane pary są w `notes`.

ELECTRE (rozdz. 5): pola kryteriów `q`, `p`, `v` — liczba albo `[α, β]` oznaczające α·f + β, jak we wzorze (5.39) i w programach ELECTRE z Politechniki Poznańskiej (w PROMETHEE `[α, β]` oznacza α + β·μ). Metody:
- `electre_i` (opcje `s` i wspólny próg weta `v`), `electre_iv` (progi weta kryteriów), `electre_is` (pseudokryteria q, p, v; brak p oznacza p = q) — wynik to graf przewyższania: `steps.edges`, poziomy `levels_top_down` i `levels_bottom_up`, `best` = warianty nieprzewyższane;
- `electre_iii` — wiarygodność σ, destylacje zstępująca i wstępująca z s(λ) = αλ + β (opcje `alpha`, `beta`; domyślnie −0,15 i 0,30), ranking końcowy z relacjami P, P⁻, I, R; wynik to poziom w rankingu końcowym;
- `electre_tri` — pole zadania `profiles` (profile graniczne od najniższego) i opcjonalnie `categories` (nazwy od najgorszej), opcje `cut` (λ) i `procedure` (pessimistic | optimistic | both); wynik `categories`;
- stochastyczne `electre_i_sd` (wyraźna i niewyraźna zgodność, pary niejasne; opcja `include_unclear`) i `electre_iii_sd` — oceny i opcje `risk`, `dominances` jak w PROMETHEE.

PROMETHEE i EXPROM (rozdz. 6): pola kryteriów `type` (1–6, tabl. 6.1), `q`, `p`, `s`, `v` (weto), `L` (EXPROM); metody `promethee_i` (ranking częściowy z relacjami P, I, R), `promethee_ii`, `promethee_ii_veto`, `exprom` (opcja `ranking`: complete | partial), `exprom_veto` oraz stochastyczne `promethee_ii_sd`, `exprom_ii_sd` — ocena to rozkład `{"values": [...], "probs": [...]}` albo obserwacje `{"obs": [...]}`, progi liczbą albo `[α, β]` (α + β·μ), opcje `risk` (DARA | INARA) i `dominances` (np. `["FSD", "SSD", "AFSD:0.333", "ASSD:0.2"]`); dominacje liczy `mcdm_cd`.

Rozdz. 7.4–7.6:
- `dematel` — elementy systemu jako warianty (`criteria` może być puste), pole `influence`: macierz ocen wpływu 0–4 (wiersz → kolumna) albo lista macierzy ekspertów (uśredniana); wynik r + c, w `steps` także r − c i macierz T;
- `hybrid` (DEMATEL–ANP–VIKOR) — kryteria z polem `cluster`, pola zadania `cluster_influence` i `criteria_influence`; opcje `alpha`, `alpha_criteria` (α-cięcie (7.30)), `limit` i opcje VIKOR (`q`, `ideal`, `anti_ideal`, `w2`); wagi kryteriów to średnie wierszy supermacierzy granicznej;
- `bipolar` — pola zadania `good`, `bad` (obiekty referencyjne, wiersze ocen), pola kryteriów `weight`, `q`, `v` (najmniejsza dopuszczalna ocena); opcje `s`, `weights` (given | deciles | objects), `veto_decile`, `local_preference`, `position` (classic | counts), `modify` (good | bad), `b2_prime`, `veto_test`; wynik: kategorie S, N, B w `steps`, ranking tylko wariantów z kategorią (pozostałe mają `ranks` = null);
- `bipolar_sd` — oceny i obiekty referencyjne jako rozkłady, progi `q`, `p`, `v` na wartościach oczekiwanych, opcje `risk`, `dominances`; wynik d_SN = (d_S + d_N)/2.

ANP (`anp`, `fuzzy_anp`) opisuje sieć polami zadania: `clusters` (komponenty kryteriów; warianty tworzą osobny komponent `variants_cluster`), `influences` (`{"element": [elementy, na które wpływa]}`) albo `dependency_matrix` (0/1, jak w przykładzie 3.11), `comparisons` (`{"element": {"komponent": macierz}}` — porównania elementów, na które element wpływa; zamiast macierzy można podać wektor wag) oraz `cluster_comparisons` (`{"komponent": {"clusters": [...], "matrix": ...}}`) albo gotową macierz wag komponentów `cluster_weights`. Supermacierz graniczna to granica potęg (3.49), a gdy sieć ma cykl i potęgi nie są zbieżne — granica Cesàro (3.48), liczona jako granica potęg ((I + Ω̄)/2). Struktura BOCR: pole `subnets` z sieciami (lub gotowymi priorytetami `priorities`) dla kluczy B, O, C, R, wagi `bocr_weights` i opcja `formula` (3.50)–(3.53). Przykład P3.12 pokazuje pełny zapis sieci.

Wynik każdej metody ma te same pola: `scores` (wartości i kierunek: im więcej/mniej, tym lepiej), `ranks` (z remisami), `ranking`, `best`, `steps` (wyniki pośrednie metody) i `notes` (uwagi, m.in. przyjęte konwencje).

W Pythonie: `from mcdm_book import run; run({...})`.

### Dobór metody

`{"method": "select_method", "profile": {...}}` zwraca ranking metod pakietu dla profilu problemu. Profil opisuje rodzaje ocen, zależności między kryteriami (`interdependence` — wtedy zostają tylko metody ANP), informację o preferencjach, którą decydent potrafi podać, wymaganą postać wyniku, stosunek do kompensacji, znajomość poziomów aspiracji, znaczenie wyjaśnienia wyniku oraz wiedzę i czas decydenta. Listę pól pokazuje `python -m mcdm_book methods`.

Procedura naśladuje model Gershona (rozdz. 9.3): cechy wykluczające (np. rodzaj danych) eliminują metody, a pozostałe są oceniane w skali 0–10 z wagami wynikającymi z profilu. Kolejność ustala odległość L1 od rozwiązania idealnego według wzoru (9.1). Ta sama odległość jest dostępna jako zwykła metoda `compromise`; odtwarza ona wyniki zbiorów R9.2 (model Gershona) i R9.3 (procedura Tecle'a).

Oceny SAW, SMART i TOPSIS opierają się na zbiorze R9.2, a ELECTRE III, PROMETHEE II, EXPROM II i BIPOLAR — częściowo. ELECTRE III (podobnie jak PROMETHEE I) nie daje pełnego rankingu (R9.2: „kompletny ranking” 0). Profil `output: "sort"` wybiera metody sortujące do kategorii (ELECTRE TRI). Oceny pozostałych metod są moje i można je nadpisać opcją `scores`.

## Zgodność z książką

Testy (`pytest`) odtwarzają przykłady z płyty: P2.1–P2.3, P2.5, P2.7, P2.11, P3.3, P3.4, P3.7, P3.10, P3.12–P3.14, P4.2, P4.3, P4.5–P4.8, P5.10–P5.16, P5.19, P5.20, P6.2–P6.16, P7.1, P7.3–P7.8, P7.12, P7.13, P7.15, P7.16, R9.2, R9.3, tablice 2.1–2.2, rozmyty TOPSIS z rozdz. 14 (oceny ofert 0,2706; 0,6507; 0,1656; 0,3391; 0,5145; 0,5376) oraz przypadki z części II (`tests/test_part2_cases.py`, przykłady `R9.5`, `R9.5E`, `R11`, `R15`, `R16` i `mcdm_cd.example("rozdz_10")`).

Tam, gdzie książka zawiera błąd albo jest niejednoznaczna, pakiet przyjmuje wersję poprawną i to opisuje:
- **Normalizacja kosztowa:** liczona jako (max − f)/(max − min). Wzory (2.4) i (2.9) w druku są tożsame z (2.3) i (2.8).
- **Funkcja wartości SMART:** interpolacja odcinkowo-liniowa przez punkty bisekcji albo parabola MNK. Parabolę stosuje Excel w przykładach 2.5 i 2.7.
- **Rozmyty TOPSIS:** kryteria kosztowe są normalizowane przez min l, jak w rozdz. 14. Wzór (7.10) z druku jest dostępny jako opcja `cost_norm="min_u"`.
- **AHP:** λmax w metodzie Saaty'ego liczę z (Aω)ᵢ/ωᵢ, jak w przykładzie 3.3. Wzór (3.19) w druku ma ωᵀA. Domyślną metodą jest wektor własny, a metodę Saaty'ego i metodę potęgową z ε wybiera się opcją. Wartość r dla m > 10 pochodzi z Saaty (1980), spoza tablicy 3.1.
- **REMBRANDT:** domyślnie γ = ln √2 dla kryteriów i ln 2 dla wariantów, jak w (3.28). Przykład 3.7 liczy warianty z ln √2. Wektor końcowy jest agregowany geometrycznie (3.31), bo wartości z druku nie dają się odtworzyć.
- **ANP:** kolumny supermacierzy ważonej, które nie sumują się do 1, są normalizowane (jak w przykładzie 3.12). Rozmyta ANP dopisuje stopień 1 komponentowi, ze względu na który porównujemy (3.58), więc przekątna macierzy wag komponentów jest niezerowa (tabl. 6 przykładu 3.14). Gdy kolumny supermacierzy granicznej się różnią (np. hierarchia z pętlami `sinks="loop"`), wektor skali pochodzi z kolumn elementów źródłowych albo z kolumny wskazanej opcją `read_from`. Synteza BOCR domyślnie używa priorytetów „idealnych” (podzielonych przez największy), jak Super Decisions; tak odtwarza się rys. 15 przykładu 3.13.
- **PROMETHEE II / EXPROM II z wetem:** wskaźniki niezgodności wg wzoru (6.20) — d_k(aⁱ, aʲ) rośnie z przewagą aʲ nad aⁱ. Przykłady 6.7 i 6.10 liczą je odwrotnie (z f(aⁱ) − f(aʲ)); ich wynik odtwarza opcja `veto_direction="example"`. Przepływy z σ i ω są sumami (bez dzielenia przez m − 1), jak we wzorach (6.23), (6.38); opcja `divide`.
- **ELECTRE:** progi i weto liczone od oceny wariantu aⁱ (pierwszego w parze). Warianty w cyklu grafu przewyższania trafiają na wspólny poziom. Przy budowie grafu od najsłabszych wariant trafia na najniższy możliwy poziom; w przykładzie 5.10 (rys. 2) książka stawia a7 razem z a8 na szczycie, pakiet — o poziom niżej. ELECTRE TRI liczy d_k = 1 już przy różnicy równej v (jak w przykładzie 5.15); jego σ zgadzają się z programem ELECTRE TRI (P5.17, rys. 8), a nie z ręcznymi obliczeniami P5.15–P5.16, które zawierają błędy. ELECTRE I z dominacjami uznaje TSD wykryte przez StDom; tak liczy arkusz P5.19, a tablica 6 przykładu 5.18 je pomija.
- **MACBETH:** przykład 4.3 odtwarzam z ocenami przekątnej i koloru wziętymi z tabeli wyników M-MACBETH (macierze tych kryteriów nie są podane); skale jakości wyświetlania i ciężaru oraz wagi wychodzą z (4.13)–(4.16) dokładnie jak w programie (ocena Samsunga 248,65; program 248,64 przy wagach zaokrąglonych do 4 miejsc). Bez elementu odniesienia najmniej ważne kryterium dostaje wagę 0 (przykład 4.2).
- **ZAPROS III:** przykład 4.8 odtworzony w całości (JSCV, FIQ, rangi, graf); bezpośrednie porównanie K9 i K4 daje nieporównywalność, preferencja wynika z przechodniości (K9 ≻ K1 ≻ K2 ≻ K4).
- **DEMATEL–ANP–VIKOR:** przykład 7.6 odtwarzam z ocenami z tablicy 16.1 i f* = 10, f₋ = 0 (tabl. 5, 7, 8, 10, 11 zgodne; Q(a11) = 0,462 wobec 0,463 w druku). Ranking hybrydowy w tabl. 16.5 rozdz. 16 (za Targiel i in. 2012) jest inny.
- **BIPOLAR:** przy c⁺ = c⁻ przyjmuję d⁺ = d⁻ = c⁺ + c⁼, jak w przykładzie 7.8 (wzór (7.49) w druku: c⁺ + c⁻). Test niekonfliktowości domyślnie wg (7.43) i (7.46); przykłady 7.7–7.12 zawsze sprawdzają oceny wariantu na kryteriach z I⁻ — opcja `veto_test="example"`. Obliczenia przykładu 7.7 odpowiadają danym z rys. 1 (i przykładu 7.9), nie tablicy 1. W przykładzie 7.13 d_N zgadza się z tablicą 11, a d_S — z relacjami tablicy 9 (tablica 11 jest z nimi niespójna dla a4–a6, a8–a10); w przykładzie 7.14 tablica 4 powtarza wyniki 7.13. W przykładzie 7.15 kategorie S zgadzają się z tablicą 2, a N — poza a4 i a6 (pakiet: N1). W przykładzie 7.8 dla s ∈ [0,5; 0,75) książka uznaje a6 za nieporównywalny, co wymaga f₂(a6) = 6 zamiast 3 z tablicy 1. Przykład 7.16 (z dominacjami) zgadza się co do d_S, d_N i rankingu.
- **VIKOR:** reguła wyboru rozwiązania kompromisowego jest wzięta z Opricovic i Tzeng (2004), bo w książce wyliczenie przypadków jest niekompletne. Warunek W2 domyślnie wymaga, by a′ był najlepszy w rankingach S i R (jak w książce).

Rozbieżności w przykładach (P2.1, P2.7, P2.11, P3.14, P5.10, P5.13, P5.15–P5.18, P5.20, P6.7, P6.10, P7.1, P7.4, P7.6–P7.15) opisano w komentarzach testów.

ATO-DPR (`mcdm_cd.AtoDPR`, dialog jak w STEM-DPR: `run(ScriptedAtoDM([...]))` albo generator `dialog()`): opcje `risk`, `dominances` (relacje SD_T; klasa U₂ z przykładu 8.5 to `("FSD", "SSD")`), `almost` (AFSD przy pierwszym wariancie próbnym; przykład 8.5 ją pomija), `tradeoff_rules` (dominacje rozkładów współczynników wymiany: wzór (8.19) — FSD, tekst kroku 7 i przykład 8.5 — FSD i SSD; w przykładzie 8.5 wynik jest ten sam). Rozkład współczynnika wymiany liczony dokładnie ze wszystkich kombinacji (8.15)–(8.16), M = 10 000. Przykład 8.5 (`mcdm_cd.example("przyklad_8_5")`) odtworzony w całości: współczynniki d (tabl. 9–13), relacje T (tabl. 17–19, 21), kolejne warianty próbne a6 → a1 → a4. Tablica 7 przykładu powtarza tablicę 6, a „idealny wektor” w tabl. 20 jest liczony dla całego zbioru, nie dla 𝒜⁽²⁾.

`mcdm_cd` sprawdzono z raportami StDom z przykładów 5.19, 6.13 i 6.15 oraz z przebiegami przykładów 8.2 i 8.4.

### Część II (rozdz. 9–16)

- **Rozdz. 9 (R9.5):** PROMETHEE II i EXPROM II z wetem dają kolejność tabl. 9.6; Φ różni się od druku najwyżej o 0,003 (R9.5 zaokrągla σ i ω do 3 miejsc). Kolumna „Minimum” tabl. 9.4 nie wchodzi do obliczeń.
- **Rozdz. 10:** dane `rozdz_10` — f1, f2 z rozkładów R10.3–R10.4, f3–f6 ze średnich ocen ekspertów (tabl. 10.4, p = 1/3, f3–f5 ze znakiem minus jak w R10.5). STEM-DPR odtwarza tabl. 10.6–10.7 tylko przy `relations=("FSD", "SSD")`: przykład nie liczy TSD ani składnika AFSD z (8.4); domyślne ustawienie (jak MCDM 1.00) daje d₈₁ = 6,89, wybór a8 bez zmian. W druku d₈₆ = 6 (wychodzi 2) i μ₆₂ = −345,53 (wychodzi −345,38). INSDECM: dodano parametry rozkładu 12 (minimum) i 13 (maksimum), którymi posługują się tabl. 10.8–10.13. Warunek P{ξᵢ₁ ≥ 485} ≥ 0,7 z s. 209 zostawia tylko a4 i a9 (dalej zbiór pusty); zbiór 𝒜⁽²⁾ z druku daje np. warunek μᵢ₁ ≥ 482 — od niego 𝒜⁽³⁾, 𝒜⁽⁴⁾ = {a6, a8} i P(4) zgadzają się z drukiem.
- **Rozdz. 11:** ANP z supermacierzy R11.1 i wag komponentów tabl. 11.8 odtwarza R11.3 i tabl. 11.13 (0,3035; 0,4415; 0,2551, w druku 0,2550).
- **Rozdz. 15:** PROMETHEE II (typ 5, progi z s. 275–276) na danych tabl. 15.4 nie odtwarza tabl. 15.6: a24 i a42 (w druku poz. 1 i 4) mają −0,0065 i −0,0236; pierwsza ósemka to a37, a41, a2, a26, a8, a68, a67, a66. Rankingu AHP z tabl. 15.8 nie odtwarzam (przekształcenie różnic tabl. 15.7 ma zamienione nagłówki i niejednoznaczne granice).
- **Rozdz. 16:** ELECTRE I bez weta (`v = 10`) daje grafy R16.2 (2, 5, 10, 21, 38 łuków) i rankingi z s. 288–290; reguła poziomów pomija łuki dwukierunkowe, tak odtwarza się tabl. 16.5 (kol. 1). Dla s = 0,86 a5 trafia na poziom 3, nie 1 (przewyższają go a4 i a10). Ranking hybrydowy: zob. DEMATEL–ANP–VIKOR wyżej.
- **Rozdz. 12, 13:** nieodtworzone — dane R12.1–R12.2 są tylko w arkuszach .xls płyty (brak ich w repozytorium), a rozdz. 13 używa programu UniComBOS (werbalna analiza decyzyjna), którego pakiet nie implementuje. Rozdz. 14 — zob. rozmyty TOPSIS.

## Strona

`index.html` to jeden plik, który można otworzyć w przeglądarce albo opublikować przez GitHub Pages (Settings → Pages → Deploy from a branch → `main`, `/ (root)`). Przy pierwszym otwarciu potrzebny jest internet, bo Pyodide 0.26.4 jest ładowany z `cdn.jsdelivr.net`. Pliki wczytane przez użytkownika nie opuszczają przeglądarki.

Test strony w przeglądarce: `python tests/e2e_browser.py`. Skrypt sprawdza przykłady z książki we wszystkich zakładkach, edytor AHP, dobór metody i dialogi STEM-DPR, INSDECM i ATO-DPR. Wymaga Playwright; opcje i sposób uruchomienia bez dostępu do CDN opisuje nagłówek skryptu.

Plik buduje skrypt `python web/build.py`: łączy szablon `web/template.html`, kod łączący stronę z pakietami (`web/web.py`), źródła obu pakietów, pliki .mcf z płyty oraz bibliotekę [xlrd](https://github.com/python-excel/xlrd) 2.0.1 (licencja BSD, `web/vendor/`). Po każdej zmianie w pakietach trzeba go uruchomić ponownie.
