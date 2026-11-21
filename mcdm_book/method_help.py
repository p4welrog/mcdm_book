"""Krótka pomoc do metod (panel „Jak używać” na stronie): kiedy stosować, jak czytać wynik, na co uważać.

Tekst własny, oparty na implementacji pakietu i jego konwencjach (README, sekcja „Zgodność z książką”);
dokładne wzory i przykłady — w podanym rozdziale książki. Nazwy opcji jak w interfejsie strony.
"""
from typing import Any, Dict, List, Optional


def _h(use: str, result: str, *tips: str) -> Dict[str, Any]:
    return {"use": use, "result": result, "tips": list(tips)}


_DISTR = "Ocena wariantu to rozkład: „wartość:prawdopodobieństwo …” albo lista obserwacji (rozkład empiryczny)."
_RISK = ("Opcja „Decydent” wybiera dominacje stochastyczne: awersja do ryzyka — FSD, SSD, TSD; skłonność do ryzyka — FSD, SISD, TISD; "
         "pole „Uznawane dominacje” nadpisuje ten wybór, także prawie dominacjami (np. AFSD:0,333).")

HELP: Dict[str, Dict[str, Any]] = {
    # --- rozdz. 2
    "saw": _h("Szybki ranking, gdy słabą ocenę na jednym kryterium można w pełni zrekompensować dobrą na innym.",
              "Ocena p wariantu (0–1) to suma ważona znormalizowanych ocen; im większa, tym lepiej.",
              "Wynik zależy od sposobu normalizacji — przy porównaniu z innym źródłem sprawdź, jaką przyjęto.",
              "Wagi, które nie sumują się do 1, są normalizowane (informacja w uwagach).",
              "Kryterium o tej samej ocenie u wszystkich wariantów nie różnicuje wyniku."),
    "scoring": _h("Decydent sam przyznaje punkty wariantom na każdym kryterium.",
                  "Suma punktów (z wagami — ważona suma bez normalizacji wag); im większa, tym lepiej.",
                  "Skale punktów na kryteriach powinny być porównywalne — inaczej kryterium o szerszej skali dominuje wynik."),
    "fsaw": _h("Jak SAW, gdy wagi kryteriów znane są tylko w przybliżeniu (minimum, najbardziej prawdopodobna, maksimum).",
               "Ocena rozmyta zamieniona na liczbę metodą środka ciężkości; im większa, tym lepiej.",
               "Szerokie przedziały wag oznaczają dużą niepewność — przy bliskich ocenach sprawdź, czy zmiana wag nie odwraca kolejności."),
    "smart": _h("Gdy oceny trzeba najpierw przełożyć na użyteczność 0–100 (liniowo, bezpośrednio albo przez funkcję wartości), a wagi ustala się metodą rozpiętości (swing).",
                "Użyteczność U (0–100) jako suma ważona użyteczności cząstkowych; im większa, tym lepiej.",
                "Funkcja wartości z punktów jest odcinkowo-liniowa; poza przedziałem [najgorsza; najlepsza] wartości są ekstrapolowane bez obcinania (uwaga w wyniku).",
                "Wagi swing: najważniejsza rozpiętość dostaje 100, pozostałe — ile są warte w porównaniu z nią."),
    "smarter": _h("Jak SMART, gdy decydent umie podać tylko kolejność ważności kryteriów.",
                  "Użyteczność U jak w SMART, z wagami ROC wyliczonymi z rang.",
                  "Ranga 1 = najważniejsze kryterium; wagi ROC mocno faworyzują pierwsze miejsca."),
    # --- rozdz. 3
    "ahp": _h("Gdy oceny powstają z porównań parami (skala 1–9) kryteriów i wariantów.",
              "Wektor priorytetów wariantów (suma 1); współczynnik zgodności γ powyżej 0,1 to sygnał, by przejrzeć porównania.",
              "Wystarczy wypełnić górny trójkąt macierzy — odwrotności uzupełniają się same.",
              "Domyślnie wektor własny; metoda Saaty'ego, potęgowa i średnie geometryczne dają nieco inne liczby.",
              "Kryterium bez macierzy dostaje wektor skali z ocen liczbowych; przy wielu wariantach macierz można zbudować z różnic ocen."),
    "rembrandt": _h("Wersja AHP ze skalą logarytmiczną (oceny δ od −8 do 8), odporna na odwracanie rang po dodaniu wariantu.",
                    "Priorytety wariantów z agregacji geometrycznej, znormalizowane; im większe, tym lepiej.",
                    "Macierz powinna być antysymetryczna (δ i −δ); jeśli nie jest, pakiet liczy na danych i zgłasza to w uwagach."),
    "fuzzy_ahp": _h("Gdy porównania parami są niepewne i podawane jako trójki [l, m, u] (lub słownie, skalą Changa).",
                    "Ostre wagi z programowania liniowego; λ mierzy, na ile wagi spełniają porównania (λ < 0 — porównania niespójne).",
                    "Wynik łączy kilka poziomów α — wyższe poziomy ważą więcej."),
    "anp": _h("Gdy kryteria (i warianty) wpływają na siebie nawzajem, a hierarchia AHP tego nie oddaje.",
              "Priorytety wariantów z granicy supermacierzy ważonej (suma 1); w wynikach pośrednich supermacierze.",
              "Zależność czyta się „wiersz wpływa na kolumnę”; porównuje się elementy, na które dany element wpływa.",
              "Kolumny, które po ważeniu nie sumują się do 1, są normalizowane (uwaga z listą); przy cyklu granica to średnia Cesàro.",
              "BOCR: osobne podsieci korzyści, szans, kosztów i ryzyka łączone wybraną formułą."),
    "fuzzy_anp": _h("Jak ANP, gdy porównania komponentów są niepewne (trójki [l, m, u]).",
                    "Priorytety wariantów jak w ANP; wagi komponentów z rozszerzonej analizy Changa.",
                    "Komponent, ze względu na który porównujemy, dostaje stopień 1 — niezerowa przekątna to cecha metody, nie błąd."),
    # --- rozdz. 4
    "macbeth": _h("Gdy decydent ocenia słownie różnice atrakcyjności (od „bardzo mała” do „ekstremalna”), a nie liczby.",
                  "Skale kryteriów 0–100 (między poziomami „dobry” i „neutralny”) i wagi; ocena łączna — im większa, tym lepiej.",
                  "Przy niespójnych ocenach pakiet wskazuje najmniejszą zmianę kategorii, która przywraca spójność — potraktuj ją jako pytanie do decydenta.",
                  "Wagi wymagają elementu odniesienia „wszystko na poziomie neutralnym”; bez niego najmniej ważne kryterium dostaje wagę 0."),
    "macbeth_scale": _h("Budowa jednej skali MACBETH z jednej macierzy ocen różnic atrakcyjności.",
                        "Wartości elementów na skali 0–100 między wskazanymi poziomami.",
                        "Każdą parę oceniaj raz: wiersz bardziej atrakcyjny od kolumny."),
    "zapros": _h("Metoda werbalna: oceny słowne, a decydent porównuje tylko sytuacje różniące się jedną oceną.",
                 "Porządek częściowy (graf); pary nieporównywalne są normalnym wynikiem, nie błędem.",
                 "Skale kryteriów podaje się od najlepszej oceny; wspólna skala porządkowa (JOS) łączy oceny wszystkich kryteriów."),
    "zapros_iii": _h("Jak ZAPROS, gdy decydent porządkuje wariacje ocen parami kryteriów (JSQV) albo od razu wszystkie (JSCV).",
                     "Porządek częściowy i rangi; przy remisach decyduje FIQ (suma rang względem ideału).",
                     "Wariacje zapisuje się „A1>A2” — od najmniej do najbardziej dotkliwej."),
    "unicombos": _h("Gdy decydent woli porównywać konkretne zestawy ocen na dwóch–trzech kryteriach niż ustalać wagi.",
                    "Porządek częściowy wariantów; dla par nieporównywalnych strona podsuwa pytania — odpowiedź dopisuje porównanie i liczy ponownie.",
                    "Sprzeczne odpowiedzi pakiet zgłasza błędem; pytania o trzy kryteria warto zadać kilka razy w innej kolejności.",
                    "Książka nie podaje reguły wnioskowania — pakiet stosuje zasadę dekompozycji (Ashikhmin, Furems 2005)."),
    # --- rozdz. 5
    "electre_i": _h("Wybór najlepszych wariantów, gdy kompensacja ma być ograniczona, a duża przewaga na jednym kryterium może zablokować przewyższanie (weto).",
                    "Graf przewyższania i poziomy; najlepsze są warianty nieprzewyższane.",
                    "Wyższy próg zgodności s = mniej łuków i mniej rozstrzygnięć; zacznij od wysokiego i obniżaj."),
    "electre_iv": _h("ELECTRE I z progami weta osobno dla kryteriów.",
                     "Graf przewyższania i poziomy jak w ELECTRE I.",
                     "Progi podaje się liczbą albo [α, β], co oznacza α·f + β."),
    "electre_is": _h("ELECTRE I z pseudokryteriami: progi równoważności q, preferencji p i weta v.",
                     "Graf przewyższania i poziomy jak w ELECTRE I.",
                     "Bez progu p przyjmuje się p = q."),
    "electre_iii": _h("Ranking z progami q, p, v, gdy ważna jest wiarygodność przewyższania, a nie tylko jego fakt.",
                      "Dwa porządki z destylacji (zstępującej i wstępującej) i ranking końcowy, w którym mogą zostać pary nieporównywalne (R).",
                      "Progi [α, β] oznaczają α·f + β — odwrotnie niż w PROMETHEE (α + β·μ).",
                      "Pary nieporównywalne przekaż decydentowi; nie wymuszaj kolejności."),
    "electre_tri": _h("Przydział wariantów do uporządkowanych kategorii (np. słabe / średnie / dobre) zamiast rankingu.",
                      "Kategoria każdego wariantu według procedury pesymistycznej i optymistycznej.",
                      "Profile graniczne podaje się od najniższego; ustal je jako „typowy wariant na granicy kategorii”.",
                      "Różne kategorie w obu procedurach oznaczają wariant nieporównywalny z profilem."),
    "electre_i_sd": _h("ELECTRE I, gdy oceny są niepewne i opisane rozkładami.", "Graf przewyższania; pary niejasne zgłaszane w uwagach.",
                       _DISTR, _RISK, "Pary niejasne rozstrzygnij z decydentem; można je włączyć do relacji opcją."),
    "electre_iii_sd": _h("ELECTRE III, gdy oceny są niepewne i opisane rozkładami.", "Destylacje i ranking końcowy jak w ELECTRE III.",
                         _DISTR, _RISK, "Progi [α, β] liczone od wartości oczekiwanej: α·μ + β."),
    # --- rozdz. 6
    "promethee_i": _h("Porównanie parami z ograniczoną kompensacją, gdy wystarczy porządek częściowy.",
                      "Przepływy dodatni φ⁺ i ujemny φ⁻; gdy wskazują przeciwne kierunki, warianty są nieporównywalne (R).",
                      "Typ kryterium (1–6) i progi q, p, s podaje się w jednostkach kryterium.",
                      "Poziomy rankingu w wyniku pochodzą z diagramu Hassego relacji P."),
    "promethee_ii": _h("Jak PROMETHEE I, gdy potrzebny jest pełny ranking.",
                       "Przepływ netto φ = φ⁺ − φ⁻; im większy, tym lepiej.",
                       "Typ kryterium decyduje, jak różnica ocen przekłada się na preferencję — dobierz go z decydentem."),
    "promethee_ii_veto": _h("PROMETHEE II, gdy bardzo słaba ocena na jednym kryterium ma osłabiać lub wykluczać przewagę (weto).",
                            "Przepływ netto ze wskaźnikami wiarygodności σ.",
                            "Opcja „Niezgodność: jak w przykładach 6.7 i 6.10” odtwarza druk; domyślnie pakiet liczy zgodnie ze wzorem (6.20)."),
    "exprom": _h("PROMETHEE z dwoma poziomami preferencji: słabą i silną (granica L).",
                 "Przepływy EXPROM I (porządek częściowy) i EXPROM II (netto, pełny ranking).",
                 "Bez L granica zależy od typu kryterium: 0, q, p albo s (przy typie 6 z uwagą w wyniku)."),
    "exprom_veto": _h("EXPROM II z progami weta.", "Przepływ netto ze wskaźnikami wiarygodności.",
                      "Opcja „Niezgodność” działa jak w PROMETHEE II z wetem."),
    "promethee_ii_sd": _h("PROMETHEE II z wetem, gdy oceny są niepewne i opisane rozkładami.", "Przepływ netto; w wynikach pośrednich wykryte dominacje.",
                          _DISTR, _RISK, "Progi [α, β] oznaczają α + β·μ (od wartości oczekiwanej wariantu)."),
    "exprom_ii_sd": _h("EXPROM II z wetem, gdy oceny są niepewne i opisane rozkładami.", "Przepływ netto jak w EXPROM II.", _DISTR, _RISK),
    # --- rozdz. 7
    "topsis": _h("Ranking według bliskości do rozwiązania idealnego i oddalenia od antyidealnego.",
                 "Odległość względna S (0–1); im większa, tym lepiej.",
                 "Kierunek kryteriów (max/min) wyznacza punkt idealny — sprawdź go przy kryteriach kosztowych."),
    "fuzzy_topsis": _h("TOPSIS dla ocen niepewnych podanych jako trójki [l, m, u].",
                       "Odległość względna S; im większa, tym lepiej.",
                       "Normalizacja kryteriów kosztowych: domyślnie z min l (jak w przykładzie z rozdz. 14), opcja „Kryteria kosztowe: min u” — wersja wzoru (7.10) z druku.",
                       "Poziomy aspiracji i rezerwacji można podać jako punkty odniesienia."),
    "vikor": _h("Szukanie rozwiązania kompromisowego między użytecznością grupy (S) a największym żalem (R).",
                "S, R i Q — im mniejsze, tym lepiej; rozwiązanie kompromisowe z warunkami W1 (wyraźna przewaga) i W2 (stabilność).",
                "Gdy W1 lub W2 nie jest spełniony, wynikiem jest zbiór kompromisowy, a nie jeden wariant.",
                "Parametr q to waga „strategii większości” (domyślnie 0,5)."),
    "dematel": _h("Analiza, które elementy (np. grupy kryteriów) są przyczynami, a które skutkami.",
                  "r + c — znaczenie elementu, r − c — relacja (> 0 przyczyna, < 0 skutek); metoda nie porządkuje wariantów.",
                  "Oceny wpływu 0–4 czyta się „wiersz wpływa na kolumnę”; kilka macierzy ekspertów jest uśrednianych."),
    "hybrid": _h("Gdy wagi kryteriów mają wynikać z zależności między nimi (DEMATEL i ANP), a ranking z VIKOR.",
                 "Wagi z granicy supermacierzy i ranking VIKOR (S, R, Q).",
                 "Próg α odcina słabe wpływy; wagi wyznacza metoda — nie podaje się ich ręcznie."),
    "bipolar": _h("Gdy warianty ocenia się względem wzorców: przykładów „dobrych” (sukces) i „złych” (porażka).",
                  "Kategorie S, N i B oraz ranking; warianty bez kategorii (nieporównywalne ze wzorcami) są poza rankingiem.",
                  "Opcja „Test weta: jak w przykładach 7.7–7.12” odtwarza druk; domyślnie test według wzorów (7.43) i (7.46).",
                  "Przy wielu wzorcach wagi i weta można wyznaczyć z decyli (interpolacja liniowa — inne definicje kwantyla dają nieco inne wagi)."),
    "bipolar_sd": _h("BIPOLAR, gdy oceny i wzorce są rozkładami.", "Stopnie d_S, d_N i ich średnia jako ranking; kategorie według znaku.", _DISTR, _RISK),
    # --- część II
    "compromise": _h("Odległość od wartości idealnych z warunkami obowiązkowymi (np. ocena ofert z wymogami formalnymi).",
                     "Odległość L1 (wzór 9.1); im mniejsza, tym lepiej; warianty niespełniające kryteriów obowiązkowych odpadają.",
                     "Kryteria obowiązkowe zaznacza się w wierszu „obowiązkowe”; nie mają wag."),
    "agreement": _h("Porównanie dwóch uszeregowań tych samych wariantów (np. ocen dwóch ekspertów).",
                    "Wskaźniki zgodności pozycji, uszeregowania i ocen (w %); niskie wartości wskazują projekty do uzgodnienia.",
                    "Pozycje z remisami podaje się wprost (pozycja 1 = najlepsza)."),
}


def get(method: str) -> Optional[Dict[str, Any]]:
    return HELP.get(method)


def methods() -> List[str]:
    return list(HELP)
