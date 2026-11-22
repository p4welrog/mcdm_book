---
name: "wspomaganie-decyzji-wielokryterialnych"
description: "Wybór, ranking lub sortowanie wariantów według wielu kryteriów metodami z książki Trzaskalika (SAW, SMART, AHP, ANP, MACBETH, ZAPROS, UniComBOS, ELECTRE, PROMETHEE, TOPSIS, VIKOR, BIPOLAR, ryzyko). Użyj, gdy ktoś waży opcje, ustala wagi kryteriów lub porównuje parami."
---

# Wielokryterialne wspomaganie decyzji

Prowadzisz decydenta od opisu problemu do uzasadnionej rekomendacji. Obliczenia wykonuje pakiet Pythona `mcdm_book` (metody z rozdz. 2–7 książki, także UniComBOS z rozdz. 4.2 i 13 „Wielokryterialne wspomaganie decyzji. Metody i zastosowania”, red. T. Trzaskalik, PWE 2014) oraz `mcdm_ryzyko` (dominacje stochastyczne, STEM-DPR i INSDECM z rozdz. 1.3 i 8.3–8.4); ATO-DPR z rozdz. 8.5 jest w `mcdm_book.ato_dpr`. Wyniki obu pakietów są sprawdzone na przykładach z książki. Nie licz ich w pamięci ani nie szacuj w prozie: każdą liczbę w odpowiedzi bierz z wyniku pakietu.

## Instalacja (raz na sesję)

```bash
pip install --break-system-packages -q "mcdm-book[mcf] @ git+https://github.com/p4welrog/mcdm_book"
python -m mcdm_book methods > /tmp/mcdm_methods.json   # metody, wymagane dane, opcje
```

Jeśli GitHub jest niedostępny, poproś użytkownika o dołączenie katalogu repozytorium (np. `Documents/Trzaskalik/mcdm_book`) i zainstaluj z niego: `pip install --break-system-packages -e <katalog>[mcf]`.

Przykłady z książki gotowe do uruchomienia: `python -m mcdm_book example` (lista), `python -m mcdm_book example P3.4`. Pokazują format danych każdej metody — zajrzyj do przykładu metody, zanim zbudujesz własne zadanie.

Te same metody działają w przeglądarce: https://p4welrog.github.io/mcdm_book/ (bez instalacji; edytor zadania, wyniki pośrednie, dialogi STEM-DPR, INSDECM i ATO-DPR). Adres `https://p4welrog.github.io/mcdm_book/?example=<id>` otwiera przykład z książki od razu policzony (`&run=0` — bez liczenia; `P8.1`–`P8.5` i `R10` otwierają zakładkę dialogu z danymi). Podaj ten link, gdy decydent chce sam zobaczyć metodę na przykładzie z książki albo dalej edytować zadanie — z tobą liczy pakiet, link jest uzupełnieniem, nie zastępstwem odpowiedzi.

## Przebieg

1. **Struktura problemu.** Ustal z użytkownikiem: cel, warianty (co najmniej 2), kryteria z kierunkiem (max — im więcej, tym lepiej; min — koszt) i rodzaj danych dla każdego kryterium: liczby, oceny jakościowe, przedziały lub oceny niepewne (trójki pesymistyczna–najbardziej prawdopodobna–optymistyczna), rozkłady prawdopodobieństwa (ryzyko). Brakujących ocen nie wymyślaj; zapytaj albo zaproponuj ocenę i poproś o potwierdzenie. Pytaj o kilka rzeczy naraz (np. o całą tabelę), nie o każdą komórkę osobno.
2. **Wybór metody** — procedurą `select_method` (sekcja „Dobór metody”), a nie z pamięci. Pokaż użytkownikowi dwie najlepsze metody z odległością L1 i odrzucone metody z powodem; zaproponuj pierwszą, drugą zachowaj do sprawdzenia odporności. Jeśli użytkownik chce innej metody, uszanuj to i powiedz, czym ryzykuje według profilu. Tablica „Wybór metody — uzasadnienie” służy do wyjaśnienia wyboru.
3. **Wagi i preferencje** — sposób zależny od metody (sekcja „Pozyskiwanie wag”).
4. **Obliczenia.** Zapisz zadanie do pliku JSON i uruchom `python -m mcdm_book run zadanie.json`. Błąd (`{"error": ...}`) to komunikat o danych — popraw dane albo dopytaj.
5. **Odporność wyniku.** Zanim zarekomendujesz, sprawdź stabilność (sekcja „Analiza wrażliwości”). Przy ważnych decyzjach policz też drugą, odmienną metodą (np. SAW i TOPSIS albo AHP i VIKOR) i porównaj rankingi.
6. **Rekomendacja.** Podaj ranking z wartościami, najlepszy wariant (albo zbiór, gdy są remisy lub VIKOR wskazuje kilka), kluczowe wyniki pośrednie, wnioski z analizy wrażliwości i wszystkie uwagi z pola `notes` wyniku. Wyjaśnij prostym językiem, dlaczego wygrał dany wariant (które kryteria i wagi o tym zadecydowały). Decyzja należy do użytkownika.

## Dobór metody

Zbierz profil problemu z rozmowy (dopytaj tylko o to, czego nie wiesz) i uruchom:

```bash
python -m mcdm_book run - <<'EOF'
{"method": "select_method",
 "profile": {"data": ["numeric", "qualitative"], "preferences": ["pairwise"], "output": "ranking",
             "compensation": "full", "reference_levels": false,
             "explain": "medium", "expertise": "low", "time": "medium"}}
EOF
```

JSON nie dopuszcza komentarzy — nie dopisuj ich w zadaniu. Pola profilu: `data` — rodzaje ocen (`numeric`, `qualitative`, `fuzzy`, `stochastic`); `preferences` — co decydent potrafi podać (`weights`, `swing`, `ranks`, `pairwise`, `fuzzy_weights`, `points`, `dialog`); `output` — `best`, `ranking`, `scores` albo `sort` (przypisanie do uporządkowanych kategorii, np. „słabe / średnie / dobre” — wtedy zostaje ELECTRE TRI); `compensation` — `full` albo `limited`; `reference_levels` — czy zna poziomy aspiracji i rezerwacji; `explain`, `expertise`, `time` — `low`, `medium` albo `high` (znaczenie wyjaśnienia wyniku innym, wiedza decydenta o metodach, jego czas); `interdependence` — `true`, gdy kryteria wpływają na siebie (wtedy zostają metody ANP i metoda hybrydowa).

Procedura naśladuje model Gershona (rozdz. 9.3): cechy obowiązkowe (rodzaj danych, wymagana postać wyniku) eliminują metody, pozostałe cechy są punktowane 0–10 z wagami z profilu, a ranking daje odległość L1 od rozwiązania idealnego (wzór 9.1). Wynik: `ranking` (od najlepszej), `scores.values` (L1, im mniej, tym lepiej), `elimination_reasons`, `titles`, `grade_sources`, `notes`. Oceny metod SAW, SMART i TOPSIS pochodzą ze zbioru R9.2, pozostałe są ocenami autora pakietu — powiedz to, gdy użytkownik pyta o podstawę wyboru; ekspert może je nadpisać opcją `"options": {"scores": {"vikor": {"transparency": 8}}}`. Gdy żadna metoda nie przechodzi (np. rozkłady prawdopodobieństwa i wymagany pełny ranking), powiedz, czego brakuje, i zaproponuj złagodzenie wymagań. Metoda `compromise` (ta sama odległość L1, kryteria z `"mandatory": true`) nadaje się też do zwykłych problemów decyzyjnych z wartościami idealnymi.

## Wybór metody — uzasadnienie

| Sytuacja | Metoda (`method`) | Rozdz. |
|---|---|---|
| Oceny liczbowe, wagi znane; chcesz najprostszej, przejrzystej metody | `saw` | 2.1 |
| Decydent rozdziela pulę punktów między kryteria i przyznaje punkty; także karta oceny z wagami kryteriów (ważona suma punktów, rozdz. 9.5) | `scoring` | 2.1 |
| Oceny liczbowe, wagi niepewne (min / najbardziej odpowiednia / max) | `fsaw` | 2.2 |
| Oceny różnego typu (liczby, oceny bezpośrednie 0–100, nieliniowa użyteczność); wagi z porównania rozpiętości | `smart` | 2.3 |
| Jak wyżej, ale decydent umie tylko uszeregować kryteria | `smarter` | 2.4 |
| Kryteria lub warianty trudno ocenić liczbą — porównania parami (skala 1–9) | `ahp` | 3.1 |
| Porównania parami, odporność na odwrócenie rankingu, agregacja geometryczna | `rembrandt` | 3.2 |
| Porównania parami nieprecyzyjne (trójki) | `fuzzy_ahp` | 3.3 |
| Kryteria zależą od siebie lub od wariantów (sprzężenia zwrotne); także struktura korzyści–szanse–koszty–ryzyko (BOCR) | `anp` | 3.4 |
| Jak wyżej, ale porównania komponentów nieprecyzyjne (skala Changa) | `fuzzy_anp` | 3.5 |
| Decydent woli słownie oceniać różnice atrakcyjności („mała”, „duża”…) niż podawać liczby; potrzebna skala kardynalna i kontrola spójności | `macbeth` (wagi: `macbeth_scale`) | 4.1 |
| Oceny słowne na krótkich skalach porządkowych, wielu wariantów, decydent odpowiada tylko na pytania porządkowe; wystarczy porządek częściowy | `zapros` | 4.2.2 |
| Jak wyżej, ale z porównaniem wariacji ocen dla par kryteriów i rangami (także „rozmytymi”) | `zapros_iii` | 4.2.3 |
| Niewiele wariantów, oceny liczbowe i słowne; decydent nie chce wag ani liczb, ale umie porównać dwa konkretne zestawy ocen na 1–3 kryteriach („to czy tamto?”); wynik z wyjaśnieniem, z jakich porównań wynika | `unicombos` | 4.2, 13 |
| Oceny liczbowe; wariant najbliższy ideałowi i najdalszy od antyideału | `topsis` | 7.1 |
| Oceny niepewne jako trójki; także punkty odniesienia (np. poziom aspiracji i rezerwacji w negocjacjach) | `fuzzy_topsis` | 7.2 |
| Potrzebny kompromis z kontrolą przewagi i stabilności rozwiązania | `vikor` | 7.3 |
| Które czynniki (grupy kryteriów) są przyczynami, a które skutkami — mapa wpływów bez rankingu wariantów | `dematel` | 7.4 |
| Kryteria w grupach wpływają na siebie, decydent umie ocenić siłę wpływu (0–4) zamiast porównywać parami; wagi z DEMATEL i ANP, ranking VIKOR | `hybrid` | 7.4 |
| Warianty ocenia się względem wzorców: przykładów „dobrych” (sukces) i „złych” (porażka); wynik to kategorie i ranking | `bipolar` | 7.5 |
| Jak wyżej, ale oceny i wzorce to rozkłady albo oceny kilku osób | `bipolar_sd` | 7.6 |
| Odległość od wartości idealnych z warunkami obowiązkowymi (np. ocena metod, ofert z wymogami formalnymi) | `compromise` | 9.3 |
| Wybór najlepszych wariantów bez pełnej kompensacji; wynik to graf przewyższania (warianty nieprzewyższane) | `electre_i` (wspólna skala, jeden próg weta) / `electre_iv` (weto dla każdego kryterium) / `electre_is` (progi q, p, v) | 5.2 |
| Porządkowanie z progami q, p, v; dopuszczalna nieporównywalność, ranking częściowy | `electre_iii` | 5.3 |
| Przypisanie wariantów do uporządkowanych kategorii wyznaczonych profilami granicznymi | `electre_tri` | 5.4 |
| Oceny to rozkłady prawdopodobieństwa; wybór (graf) albo porządkowanie częściowe | `electre_i_sd` / `electre_iii_sd` | 5.5–5.6 |
| Oceny liczbowe, różnice ocen mają znaczenie dopiero powyżej progów; dopuszczalna nieporzównywalność wariantów | `promethee_i` (ranking częściowy) / `promethee_ii` | 6.2 |
| Jak wyżej, ale duża przewaga w jednym kryterium ma blokować przewyższanie (weto) | `promethee_ii_veto` | 6.3 |
| Jak PROMETHEE, ale potrzebna skala kardynalna wyniku (siła silnej preferencji względem ideału) | `exprom` / `exprom_veto` | 6.4–6.5 |
| Oceny to rozkłady prawdopodobieństwa albo oceny kilku osób; potrzebny pełny ranking | `promethee_ii_sd` / `exprom_ii_sd` | 6.6–6.7 |
| Oceny to rozkłady prawdopodobieństwa (ryzyko); porównanie dwóch wariantów | dominacje stochastyczne (`mcdm_ryzyko.porownaj`) | 1.3 |
| Ryzyko, decydent woli dialog krok po kroku zamiast podawać wagi | STEM-DPR / INSDECM (`mcdm_ryzyko`) | 8.3–8.4 |
| Ryzyko, dialog; decydent umie powiedzieć, które oceny wariantu próbnego satysfakcjonują go najbardziej, a które najmniej (bez progów liczbowych) | ATO-DPR (`mcdm_book.ato_dpr.AtoDPR`) | 8.5 |

Metody addytywne (SAW, SMART) zakładają niezależność preferencyjną kryteriów i pełną kompensację (słaba ocena może być zrównoważona dobrą). Jeśli decydent mówi, że jakiegoś braku nic nie zrekompensuje, zaproponuj VIKOR (kontrola maksymalnej straty R), metodę z progami weta (ELECTRE, PROMETHEE II, EXPROM II) albo warunek eliminacyjny przed obliczeniami.

## Format zadania

```json
{"method": "topsis", "options": {"metric": 2},
 "problem": {"name": "Wybór dostawcy",
             "variants": ["A", "B", "C"],
             "criteria": [{"name": "cena", "direction": "min", "weight": 0.5},
                          {"name": "jakość", "direction": "max", "weight": 0.3},
                          {"name": "termin", "direction": "min", "weight": 0.2}],
             "values": [[120, 7, 14], [100, 5, 21], [135, 9, 10]]}}
```

- `values[i][k]` — ocena wariantu i według kryterium k; oceny rozmyte jako `[l, m, u]`.
- Pola kryteriów zależne od metody: `weight` (wagi; inne niż suma 1 są normalizowane z uwagą), `fuzzy_weight` (FSAW), `swing` (punkty 0–100, SMART), `rank` (1 = najważniejsze, SMARTER), `scale` (SMART: `{"type": "linear" | "direct" | "value_function", ...}`), `max_points` (scoring).
- Metody z rozdz. 3: `criteria_comparisons` (macierz n×n) i `comparisons` (`{"nazwa kryterium": macierz m×m}`) na poziomie `problem`; elementy liczbowe, napisy `"1/7"`, trójki `[l, m, u]`; `null` pod przekątną jest uzupełniany odwrotnością (w REMBRANDT: −δ). W AHP kryterium bez macierzy dostaje wektor skali z ocen w `values`; przy wielu wariantach (porównania ręczne niemożliwe) pole kryterium `difference_scale` — 8 górnych granic różnic ocen dla stopni 1–8 (powyżej — 9), opcjonalnie `difference_decimals` — buduje macierz z różnic ocen jak w rozdz. 15.5.4 (`example R15A`); granice ustal z decydentem jako „od jakiej różnicy przewaga jest niewielka, wyraźna…”.
- ANP (`anp`, `fuzzy_anp`): `clusters` (komponenty kryteriów; warianty tworzą komponent `variants_cluster`), `influences` (`{"element": [elementy, na które wpływa]}`) albo `dependency_matrix` (0/1), `comparisons` (`{"element": {"komponent": macierz porównań elementów, na które wpływa}}`), `cluster_comparisons` (`{"komponent": {"clusters": [...], "matrix": ...}}`) albo `cluster_weights`. BOCR: `subnets` (`{"B": sieć | {"priorities": [...]}, ...}`), `bocr_weights`, opcja `formula`. Wzór zapisu: `python -m mcdm_book example P3.12`.
- PROMETHEE i EXPROM: w kryteriach `type` (1–6: zwykłe; quasi z `q`; liniowe z `p`; poziomowe i pseudo z `q`, `p`; gaussowskie z `s`), w metodach z wetem progi `q`, `p`, `v`. Progi ustalaj w jednostkach kryterium: „od jakiej różnicy przestaje to być bez znaczenia” (q), „od jakiej różnicy przewaga jest zdecydowana” (p), „jaka różnica przekreśla wariant mimo innych zalet” (v). W wersjach stochastycznych ocena to `{"values": [...], "probs": [...]}` albo `{"obs": [...]}` (np. oceny kilku osób), opcje `risk` (DARA | INARA) i `dominances`. PROMETHEE I zwraca relacje P/I/R w `steps.relations` — nieporzównywalność (R) przekaż decydentowi, zamiast ją ukrywać. Macierz zależności ustalaj z decydentem jako listę „co wpływa na co” — to najtrudniejszy i najważniejszy krok.
- ELECTRE: progi `q`, `p`, `v` w kryteriach — liczba albo `[α, β]` oznaczające α·f + β (wzór 5.39; w PROMETHEE `[α, β]` to α + β·μ — nie myl). Opcje: `s` (próg zgodności, ELECTRE I/Iv/Is i I SD; w I SD zacznij od 1 i obniżaj, dopóki s > 0,5), `v` (wspólne weto w ELECTRE I), `alpha`, `beta` (s(λ) w destylacji ELECTRE III; domyślnie −0,15 i 0,30). ELECTRE I zwraca `steps.edges` i poziomy grafu, `best` = warianty nieprzewyższane. ELECTRE III zwraca klasy obu destylacji i `steps.final_relations` (P, P-, I, R) — nieporównywalne pary przekaż decydentowi. ELECTRE TRI: pole zadania `profiles` (profile graniczne od najniższego, wartości wg kryteriów) i `categories` (nazwy od najgorszej), opcje `cut` (λ, 0,5–1) i `procedure` (pessimistic | optimistic | both); wynik w `categories`. Profile ustalaj z decydentem jako „typowy wariant na granicy kategorii”. ELECTRE I SD wskazuje pary niejasne (c_E < s ≤ c_E + c_N) w `notes` — rozstrzygnij je z decydentem; opcja `include_unclear` włącza je do relacji. Wzory zapisu: `python -m mcdm_book example P5.13`, `P5.15`, `P5.19`.
- DEMATEL i metoda hybrydowa: `dematel` — elementy (np. grupy kryteriów) jako `variants`, `criteria` puste, pole `influence` z macierzą 0–4 „wiersz wpływa na kolumnę” (albo listą macierzy ekspertów — uśredniana); wynik r + c, a w `steps.relation` r − c (> 0 przyczyna, < 0 skutek). `hybrid` — kryteria z polem `cluster`, pola `cluster_influence` (grupy) i `criteria_influence` (kryteria), opcje `alpha`, `alpha_criteria` (odcięcie słabych wpływów), `ideal`, `anti_ideal`, `q`, `w2`; wagi wyznacza metoda (`steps.weights`). Wzory: `example P7.5`, `P7.6`.
- BIPOLAR: pola zadania `good` i `bad` (obiekty referencyjne — wiersze ocen jak `values`), w kryteriach `weight`, `q`, `v` (najmniejsza dopuszczalna ocena — weto). Opcje: `s` (próg zgodności), `weights` (given | deciles | objects — wagi z rozróżniania wzorców), `veto_decile`, `local_preference`, `position` (classic | counts — counts daje pełny ranking), `modify`, `b2_prime`. Kategorie S, N, B w `steps`; warianty bez kategorii (nieporównywalne ze wzorcami) mają `ranks` = null — przekaż to decydentowi. Wzorce ustalaj z decydentem jako rzeczywiste przykłady udanych i nieudanych wyborów. Gdy wzorców jest dużo (np. spółki-zwycięzcy i przegrani, rozdz. 12), nie pytaj o wagi: `"weights": "deciles"` wyznacza wagi z tego, jak dobrze decyle kryterium rozdzielają wzorce dobre i złe (τ, ρ — w `steps`), `"veto_decile": 3` bierze weto z 3. decyla wzorców dobrych, `"position": "counts"` daje pełny ranking z liczb przewag (7.81)–(7.82); decyle liczone interpolacją liniową (jak PERCENTYL w Excelu) — powiedz to, bo inne definicje kwantyla dają nieco inne wagi. Wzory: `example P7.8`, `P7.13`, `P7.16`, `R12`.
- MACBETH: w kryterium pole `macbeth` = {`levels` (poziomy jakościowe lub liczbowe; bez nich porównuje się warianty), `judgements` (macierz: wiersz bardziej atrakcyjny od kolumny; 0 = równie atrakcyjne, 1–6 albo "very weak" … "extreme" / "bardzo mała" … "ekstremalna", [s, t], "positive" gdy decydent nie umie ocenić), `upper`, `lower` (poziomy 100 i 0 — np. „dobry” i „neutralny”)}; kryterium bez `macbeth` ma gotowe oceny w tej skali. Wagi: `criteria_judgements` z dodatkowym ostatnim wierszem `[ all lower ]` (bez niego najmniej ważne kryterium dostaje wagę 0). Przy niespójnych ocenach błąd wskazuje zmianę kategorii, która przywraca spójność — przedstaw ją decydentowi jako pytanie, nie poprawiaj sam. Wzory: `example P4.3`, `P4.2`.
- ZAPROS: kryteria z polem `scale` (oceny od najlepszej, różne między kryteriami, np. A1, A2, A3), values = te oceny; `jos` (grupy ocen wg rang) albo `y_comparisons`. Pytaj: „Co wolisz: ocenę gorszą na kryterium k i najlepsze pozostałe, czy gorszą na l…?”. ZAPROS III: `jscv` (wariacje od najmniej dotkliwej, np. "C1>C2") albo `jsqv` dla par kryteriów. Wynik to porządek częściowy (`steps.relations`, `steps.edges`) — nieporównywalne pary przekaż decydentowi. Wzory: `example P4.6`, `P4.8`.
- UniComBOS: oceny liczbowe albo słowne; pole zadania `comparisons` — lista porównań `{"criteria": ["f2", "f5"], "first": [28.81, 29326], "second": [33.32, 6341], "answer": ">"}` (`>` pierwszy lepszy, `=` tak samo, `<` gorszy, `?` nie wiem); dla ocen słownych pole kryterium `order` (od najlepszej; grupa równoważnych jako lista), dla liczb porównania jednokryterialne wynikają z kierunku (opcja `auto_single`; gdy decydent uważa małe różnice za nieistotne — np. 2,50 ≈ 2,60 mln — dopisz porównanie `=`). Prowadź dialog: uruchom, pokaż porządek, a dla par nieporównywalnych zadaj pytania z `steps.suggested_questions` (dwa kryteria, gotowe zestawy ocen), dopisz odpowiedzi i licz ponownie; gdy pary dwukryterialne nie wystarczą, zapytaj o trzy kryteria, każde pytanie trzy razy w innej kolejności kryteriów (kontrola spójności — sprzeczność pakiet zgłasza błędem). Uzasadnienie relacji: `steps.explanation` (bloki kryteriów). Wzór: `example R13` (rozdz. 13), stan pośredni `R13.2`.
- Zgodność dwóch ekspertów (R9.6): `{"method": "agreement", "positions": [[...], [...]], "scores": [[...], [...]]}` — wskaźniki zgodności pozycji, uszeregowania i ocen punktowych; użyj, gdy kilku oceniających szereguje te same warianty i trzeba wskazać projekty do uzgodnienia (`position_differences`).

- Opcje metod: `python -m mcdm_book methods`; nadpisanie z wiersza poleceń: `--option q=0.3`, `--method saw`.

Wynik: `scores` (wartości i kierunek — `better: "higher"` albo `"lower"`, VIKOR: im mniej, tym lepiej), `ranks` (z remisami), `ranking`, `best`, `steps` (wyniki pośrednie), `notes` (uwagi — zawsze przekaż je użytkownikowi).

W Pythonie: `from mcdm_book import run; r = run({...})`.

## Pozyskiwanie wag

- **Bezpośrednio:** gdy decydent podaje wagi, sprawdź, czy rozumie je jako względną ważność, a nie „ważność w ogóle”; zawsze pokaż wagi po normalizacji.
- **Wagi rozpiętości (SMART):** zapytaj, którą zmianę z najgorszego na najlepszy poziom kryterium decydent wybrałby najpierw (to kryterium = 100), a potem ile warta jest analogiczna zmiana każdego kolejnego kryterium (0–100). Pytaj o zakres wartości w danych, nie o kryterium abstrakcyjnie.
- **Rangi (SMARTER):** tylko kolejność ważności; wagi ROC (domyślne) albo sumy rang (`"weights": "rank_sum"` — łagodniejsze, gdy kryteriów jest więcej niż 3).
- **Porównania parami (AHP):** pytaj o pary werbalnie („czy cena jest ważniejsza od jakości, a jeśli tak — niewiele, wyraźnie, znacznie czy zdecydowanie?”) i przekładaj na skalę 1–9 (3, 5, 7, 9; wartości parzyste przy wahaniu). Wystarczą pary nad przekątną. Po obliczeniu sprawdź zgodność: w `steps.matrices` każda macierz ma `gamma`; gdy γ > 0,1, pokaż decydentowi najbardziej sprzeczne porównanie (np. A > B i B > C, a C ≥ A) i poproś o korektę zamiast liczyć dalej. Dla m > 9 porównań robi się bardzo dużo — zaproponuj wtedy oceny liczbowe albo SMART.
- **Niepewne wagi lub oceny:** trójki (min, najbardziej prawdopodobna, max) → `fsaw`, `fuzzy_topsis`, `fuzzy_ahp`.

## Analiza wrażliwości

Ranking jest wiarygodny tylko wtedy, gdy nie zmienia się przy rozsądnych zmianach wag. Dla każdego kryterium zmień jego wagę o ±20% (pozostałe proporcjonalnie, suma 1) i uruchom metodę ponownie; podaj, przy jakich zmianach zmienia się zwycięzca. Szkic:

```python
import copy, json
from mcdm_book import run
req = json.load(open("zadanie.json"))
base = run(req)["best"]
for k, c in enumerate(req["problem"]["criteria"]):
    for f in (0.8, 1.2):
        r2 = copy.deepcopy(req); cr = r2["problem"]["criteria"]
        w = [x["weight"] for x in cr]; w[k] *= f; s = sum(w)
        for x, wi in zip(cr, w): x["weight"] = wi / s
        b = run(r2)["best"]
        if b != base: print(c["name"], f, "→", b)
```

Przy AHP zmieniaj wektor skali kryteriów: zamiast `criteria_comparisons` podaj `weight` dla kryteriów. Gdy dwa najlepsze warianty mają bardzo bliskie wyniki, powiedz to wprost — to sygnał, że decyzję rozstrzygają czynniki spoza modelu.

## Ryzyko: dominacje stochastyczne i metody interaktywne

Pakiet `mcdm_ryzyko` (instaluje się razem z `mcdm_book`; napisany według rozdz. 1.3 i 8.3–8.4, opis w `mcdm_ryzyko/README.md`, decyzje interpretacyjne w `DECYZJE.md`, różnice z drukiem w `ROZBIEZNOSCI.md`).

```python
from mcdm_ryzyko import Rozklad, porownaj, Relacja, Postawa
x = Rozklad([1, 2, 3], ["0,2", "0,5", "0,3"])     # wartości, prawdopodobieństwa (liczby albo napisy)
y = Rozklad([1, 2, 3], ["0,3", "0,4", "0,3"])
w = porownaj(x, y)                                 # x względem y
w.zachodzi(Relacja.FSD), w.najsilniejsza(Postawa.AWERSJA)
w.eps_afsd, w.eps_assd, w.afsd(0.2), w.assd(0.2)   # prawie dominacje (tabl. 1.2, wzory 1.29–1.30)
x.wartosc_oczekiwana(), x.kwantyl(0.25), x.p_nie_mniej(2)
```

Relacje: `FSD`, `SSD`, `TSD` (awersja do ryzyka), `SISD`, `TISD1`, `TISD2` (skłonność do ryzyka), prawie dominacje `AFSD`, `ASSD`; skala porządkowa: `porownaj_porzadkowo(F, G, skala)` (OFSD, OSSD, OAFSD, OASSD). Kryterium minimalizowane: `x.odwrocony()` albo `Kryterium(nazwa, maksymalizowane=False)`. Rozkład z obserwacji: `Rozklad.z_obserwacji([...])`.

Problem decyzyjny: `wczytaj_mcf("plik.mcf")` (plik programu MCDM z płyty) albo `Problem([Kryterium(...), ...], ["a1", ...], oceny)`, gdzie `oceny[i][k]` to `Rozklad` wariantu i względem kryterium k. Przykłady z książki: `mcdm_book.ryzyko.example("przyklad_8_1" | "przyklad_8_5" | "rozdz_10" | "Przyklad_1")`. Reguła dominacji, czyli które relacje się liczy: `RegulaDominacji.awersja()` (wzór 8.4: FSD, SSD i AFSD), `RegulaDominacji.awersja(relacje=(Relacja.FSD, Relacja.SSD), afsd=False)` (tak liczy rozdz. 10), `RegulaDominacji.sklonnosc()`. Powiedz decydentowi, którą regułę stosujesz.

STEM-DPR i INSDECM to dialogi: procedura zadaje pytanie, decydent odpowiada. Prowadź je w rozmowie, przechodząc dialog od nowa z listą dotychczasowych odpowiedzi:

```python
from mcdm_ryzyko import StemDpr, Insdecm, RegulaDominacji, Sesja, Prog, uruchom
from mcdm_book.ryzyko import example
problem = example("rozdz_10")
s = Sesja(StemDpr(problem, RegulaDominacji.awersja(), pytaj_o_informacje=False).przebieg())
for a in answers:          # odpowiedzi zebrane od użytkownika w kolejnych turach
    s.odpowiedz(a)
s.pytanie                  # bieżące pytanie (klasa Pytanie…, pola z danymi do pokazania), None po zakończeniu
s.wynik                    # po zakończeniu: status ("zaakceptowano" | "brak_rozwiazania" | "przerwano"), rozwiazanie (indeks wariantu)
```

Błędna odpowiedź zgłasza `BlednaOdpowiedz` z komunikatem dla decydenta; `PRZERWIJ` kończy dialog. Rodzaje pytań i oczekiwane odpowiedzi opisują docstringi klas `Pytanie…` w `mcdm_ryzyko.stem_dpr` i `mcdm_ryzyko.insdecm`.

- STEM-DPR (8.3): `PytanieSatysfakcja` (tak/nie), `PytanieKryteriumSatysfakcjonujace` (tak/nie), `PytanieProg` → `Prog(k, delta)`: o ile decydent zgadza się pogorszyć oczekiwaną ocenę kryterium k. Wzór: rozdz. 10 z regułą FSD i SSD bez AFSD, odpowiedzi `[False, True, Prog(3, -25), True]`.
- INSDECM (8.4): decydent wybiera parametry rozkładów (`Parametr(RodzajParametru.…)`: wartość oczekiwana, odchylenia i semiodchylenia, prawdopodobieństwa nieprzekroczenia lub przekroczenia progu, kwartyle, kwantyl, mediana, dominanta, minimum, maksimum) i stawia warunki `Warunek(k, parametr, granica)`. Przy silnej awersji do ryzyka pytaj o minimum („czego nie chcesz zobaczyć nawet w najgorszym razie?”); tak pracuje rozdz. 10. Niespójne warunki procedura pokazuje w `PytanieNiespojnosc`; odpowiedzi `PODTRZYMAJ`, `OSLAB`, `ZAOSTRZ`.
- ATO-DPR (8.5, `mcdm_book.ato_dpr.AtoDPR(problem, dominances=..., almost=..., tradeoff_rules=...)`): pytania `PytanieSatysfakcjaAto` (tak/nie), `PytanieKolejnosc` (nazwy kryteriów od najbardziej do najmniej satysfakcjonującej oceny; ostatnie jest do poprawy), `PytanieOgraniczenia` (gdy kryterium nie da się poprawić w bieżącym zbiorze: czy pominąć wcześniejsze ograniczenia). Generator `dialog()` prowadzi się `Sesja` jak wyżej; przebieg zawężania zbioru kandydatów jest w `AtoIteration.steps`, pokazuj go decydentowi jako uzasadnienie nowej propozycji. Wzór: `example("przyklad_8_5")`, `AtoDPR(p).run(ScriptedAtoDM([["X3", "X4", "X1", "X2"], ["X2", "X3", "X4", "X1"]]))` → a4.

## Zasady

- Wszystkie liczby w odpowiedzi pochodzą z wyniku pakietu; podawaj je z sensowną dokładnością (zwykle 3 cyfry znaczące).
- Pole `notes` przekazuj zawsze — zawiera przyjęte konwencje i miejsca, w których pakiet odchodzi od wzorów w druku (np. normalizacja kryteriów kosztowych, reguła VIKOR z Opricovic i Tzeng 2004).
- Gdy użytkownik odtwarza przykład z książki, porównuj z wydrukiem ostrożnie: w przykładach z płyty bywają błędy, a pakiet liczy według poprawnej wersji wzorów. Gotowe przypadki z części II: `R9.5`, `R9.5E`, `R9.7I`, `R9.7II`, `R11`, `R12`, `R13`, `R13.2`, `R15`, `R15A`, `R16` w `mcdm_book.examples.EXAMPLES`. Zgodność z drukiem dla każdego przykładu podaje `mcdm_book.print_checks.get("<id>")`: `status` (ok | approx | diff), `summary` i `points` — pary (ok | diff | conv | info, tekst) z zgodnymi wartościami, różnicami i ich przyczyną oraz nazwą opcji, która odtwarza druk (np. `veto_direction="example"` w P6.7). Gdy użytkownik pyta, czemu wynik różni się od książki, zacznij od tego wpisu i przekaż go własnymi słowami; nie wymyślaj przyczyn spoza niego. Ten sam opis pokazuje panel „Wynik pakietu a druk” na stronie (`?example=<id>`).
- Odwołując się do metody, podawaj rozdział książki, żeby decydent mógł doczytać.
- Przy decyzjach o dużej stawce (finanse, zdrowie, zatrudnienie) podkreśl, że model porządkuje rozumowanie, ale nie zastępuje oceny eksperta.