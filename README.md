# Wielokryterialne wspomaganie decyzji — metody z książki

Implementacje metod z książki „Wielokryterialne wspomaganie decyzji. Metody i zastosowania” (red. T. Trzaskalik, PWE 2014) oraz strona `index.html`, która uruchamia je w przeglądarce przez [Pyodide](https://pyodide.org).

| Pakiet | Zawartość |
|---|---|
| `mcdm_book` | metody addytywne (rozdz. 2: SAW, scoring, FSAW, SMART, SMARTER) i metody punktów referencyjnych (rozdz. 7.1–7.3: TOPSIS, rozmyty TOPSIS, VIKOR); interfejs JSON |
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

Wynik każdej metody ma te same pola: `scores` (wartości i kierunek: im więcej/mniej, tym lepiej), `ranks` (z remisami), `ranking`, `best`, `steps` (wyniki pośrednie metody) i `notes` (uwagi, m.in. przyjęte konwencje).

W Pythonie: `from mcdm_book import run; run({...})`.

## Zgodność z książką

Testy (`pytest`) odtwarzają przykłady z płyty: P2.1–P2.3, P2.5, P2.7, P2.11, P7.1, P7.3, P7.4, tablice 2.1–2.2 i rozmyty TOPSIS z rozdz. 14 (oceny ofert 0,2706; 0,6507; 0,1656; 0,3391; 0,5145; 0,5376).

Tam, gdzie książka zawiera błąd albo jest niejednoznaczna, pakiet przyjmuje wersję poprawną i to opisuje:
- **Normalizacja kosztowa:** liczona jako (max − f)/(max − min). Wzory (2.4) i (2.9) w druku są tożsame z (2.3) i (2.8).
- **Funkcja wartości SMART:** interpolacja odcinkowo-liniowa przez punkty bisekcji albo parabola MNK. Parabolę stosuje Excel w przykładach 2.5 i 2.7.
- **Rozmyty TOPSIS:** kryteria kosztowe są normalizowane przez min l, jak w rozdz. 14. Wzór (7.10) z druku jest dostępny jako opcja `cost_norm="min_u"`.
- **VIKOR:** reguła wyboru rozwiązania kompromisowego jest wzięta z Opricovic i Tzeng (2004), bo w książce wyliczenie przypadków jest niekompletne. Warunek W2 domyślnie wymaga, by a′ był najlepszy w rankingach S i R (jak w książce).

Rozbieżności w przykładach (P2.1, P2.7, P2.11, P7.1, P7.4) opisano w komentarzach testów.

`mcdm_cd` sprawdzono z raportami StDom z przykładów 5.19, 6.13 i 6.15 oraz z przebiegami przykładów 8.2 i 8.4.

## Strona

`index.html` to jeden plik, który można otworzyć w przeglądarce albo opublikować przez GitHub Pages (Settings → Pages → Deploy from a branch → `main`, `/ (root)`). Przy pierwszym otwarciu potrzebny jest internet, bo Pyodide 0.26.4 jest ładowany z `cdn.jsdelivr.net`. Pliki wczytane przez użytkownika nie opuszczają przeglądarki.

Plik buduje skrypt `python web/build.py`: łączy szablon `web/template.html`, kod łączący stronę z pakietami (`web/web.py`), źródła obu pakietów, pliki .mcf z płyty oraz bibliotekę [xlrd](https://github.com/python-excel/xlrd) 2.0.1 (licencja BSD, `web/vendor/`). Po każdej zmianie w pakietach trzeba go uruchomić ponownie.
