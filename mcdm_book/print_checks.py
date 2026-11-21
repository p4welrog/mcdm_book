"""Zgodność wyników pakietu z drukiem dla przykładów z książki (panel „Wynik pakietu a druk” na stronie).

Źródła: sekcja „Zgodność z książką” w README, komentarze testów i errata transkrypcji
(`materialy/errata.md`, wpisy z dopiskiem „pakiet”). Wartości liczbowe są sprawdzane w testach.

Każdy wpis: status (ok — zgodny z drukiem; approx — zgodny z zastrzeżeniami: zaokrąglenia, konwencja,
dane uzupełnione; diff — część wyników w druku nie wynika z danych), summary (jedno zdanie),
points — lista (rodzaj, tekst), rodzaj: ok | diff | conv | info, oraz errata — kotwica sekcji erraty
w transkrypcji (bez prefiksu fragmentu).
"""
from typing import Any, Dict, List, Optional

_CD = "h-Przyklady-CD-do-rozdz-{}"
_ZB = "h-Zbiory-CD-do-rozdz-{}"
_BOOK = {
    2: "h-Rozdzial-2-Metody-addytywne", 3: "h-Rozdzial-3-Metoda-AHP-i-pokrewne",
    7: "h-Rozdzial-7-Wykorzystanie-punktow-referencyjnych", 9: "h-Rozdzial-9-Ocena-projektow-w-RPO",
    10: "h-Rozdzial-10-Interaktywny-wybor-projektow-w-firmi", 11: "h-Rozdzial-11-Wybor-systemu-klasy-ERP",
    12: "h-Rozdzial-12-Selekcja-akcji-do-portfela", 13: "h-Rozdzial-13-Ranking-centrow-handlowych",
    14: "h-Rozdzial-14-Analiza-negocjacyjna", 15: "h-Rozdzial-15-Premiowy-system-motywacji-do-pracy",
    16: "h-Rozdzial-16-Renowacja-zabytkow",
}

STATUS = {"ok": "zgodny z drukiem", "approx": "zgodny z zastrzeżeniami", "diff": "rozbieżności z drukiem"}


def _e(status: str, summary: str, *points, errata: Optional[str] = None) -> Dict[str, Any]:
    return {"status": status, "summary": summary, "points": [list(p) for p in points], "errata": errata}


CHECKS: Dict[str, Dict[str, Any]] = {
    # --- rozdz. 2
    "P2.1": _e("diff", "Wartości p zgodne z drukiem; uszeregowanie w druku zawiera błąd.",
               ("ok", "p = 0,43; 0,34; 0,71; 0,30; 0,45 (normalizacja min-max, wzór 2.3)."),
               ("diff", "W uszeregowaniu w druku a5 występuje dwukrotnie — na 5. pozycji powinien być a4.")),
    "P2.2": _e("ok", "Sumy punktów zgodne z drukiem.", ("ok", "Sumy 43; 34; 71; 30; 45.")),
    "P2.3": _e("ok", "Oceny FSAW zgodne z drukiem.",
               ("ok", "Wagi rozmyte (0; 0,1; 0,5), (0,1; 0,3; 0,4), (0,4; 0,6; 0,7), defuzyfikacja CoA: 0,73; 0,68; 0,95; 0,44; 0,74.")),
    "P2.7": _e("diff", "Kolumna u_i2 tablicy 2 w druku niezgodna z tekstem przykładu.",
               ("diff", "Druk: u_i2 = 0; 20; 0; 100, tekst: u12 = u32 = 100, u42 = 0. Oceny końcowe w druku liczone z błędnych wartości."),
               ("conv", "Pakiet: funkcja wartości odcinkowo-liniowa (60 → 37,5), U = 38,2; 25,6; 63,4; 63,4. Errata (parabola MNK): 38,2; 24,9; 63,4; 63,4 — różnica dla a2 wynika z wyboru funkcji wartości."),
               ("info", "Druk bierze u_i3 raz z punktów, raz z paraboli — żadna pojedyncza interpolacja tego nie odtwarza.")),
    "P2.11": _e("diff", "Waga ROC trzeciego kryterium w druku błędna.",
                ("diff", "w3(ROC) w druku 0,28, poprawnie 11/18 ≈ 0,61."),
                ("ok", "U = 29,011; 52,778; 59,056; 72,222 (druk w P2.12: 59,26 dla a3 — z niezaokrąglonych pośrednich).")),
    # --- rozdz. 3
    "P3.4": _e("ok", "AHP (metoda Saaty'ego) zgodny z drukiem.",
               ("ok", "c̄ = 0,088; 0,669; 0,243 (γ = 0,006); c = 0,263; 0,130; 0,058; 0,166; 0,094; 0,289."),
               ("ok", "Ranking a6, a1, a4, a2, a5, a3 — także z wektorem własnym.")),
    "P3.7": _e("diff", "Wektory cząstkowe zgodne z drukiem, wektor końcowy w druku nie wynika z danych.",
               ("ok", "c̄ = 0,101; 0,643; 0,255 oraz c1, c2, c3 zgodne z drukiem."),
               ("diff", "c w druku (0,349; …) nieodtwarzalny; pakiet (agregacja geometryczna 3.31): 0,372; 0,077; 0,036; 0,218; 0,057; 0,240. Ranking a1, a6, a4, a2, a5, a3 zgodny."),
               ("diff", "Tablica 5 (f2) nieantysymetryczna, tablice 6–7 zamienione — przyjęto f2 z tabl. 5, f3 z tabl. 6."),
               ("conv", "γ = ln √2 także dla wariantów, jak w przykładzie (wzór 3.28 przewiduje ln 2).")),
    "P3.10": _e("diff", "Rozmyty AHP zgodny z tablicą 1 poza jednym przedziałem.",
                ("ok", "ω1*(α) = 0,714 … 0,75 i λ* = 1,429 … 1 zgodne z tabl. 1; ω = 0,741; 0,259."),
                ("diff", "Dla α = 0,8 przedział w druku [2,2; 3,4], poprawnie [2,6; 3,2].")),
    "P3.12": _e("ok", "ANP odtworzony dokładnie.",
                ("ok", "Supermacierz ważona (tabl. 8), granica (tabl. 17) i priorytety 0,8084; 0,1916 zgodne."),
                ("info", "Kolumna f4 normalizowana (suma 0,75) — pakiet zgłasza to w uwagach.")),
    "P3.13": _e("approx", "BOCR odtworzony przy wagach aspektów odtworzonych z rysunku.",
                ("info", "Dane sieci w druku niepełne — przykład korzysta z priorytetów podsieci „Ideals” z rys. 10–13."),
                ("ok", "Formuła (3.50) odtwarza rys. 15 dokładnie."),
                ("conv", "Wag b, o, c, r brak w druku; odtworzone z rys. 14: ≈ 0,536; 0,267; 0,125; 0,072 — z nimi formuła (3.53) odtwarza rys. 14.")),
    "P3.14": _e("diff", "Analiza Changa zgodna z drukiem, priorytety końcowe nie.",
                ("ok", "Stopnie V z tabl. 6 dokładnie."),
                ("diff", "Priorytety z danych 0,8285; 0,1715, druk (tabl. 7) 0,8230; 0,1769; ranking zgodny."),
                ("conv", "Komponent, ze względu na który porównujemy, dostaje stopień 1 (3.58) — niezerowa przekątna V to cecha metody.")),
    # --- rozdz. 4
    "P4.2": _e("ok", "Skala MACBETH zgodna z drukiem.",
               ("ok", "Skala podstawowa 7; 3; 2; 0 → 100; 42,86; 28,57; 0."),
               ("info", "Bez elementu odniesienia najmniej ważne kryterium dostaje wagę 0 (cecha (4.13)–(4.16)).")),
    "P4.3": _e("approx", "Skale i wagi zgodne z M-MACBETH; dwa kryteria z gotowych ocen.",
               ("ok", "Skale jakości i ciężaru oraz wagi 17 : 10 : 13 : 2 (/42) dokładnie."),
               ("info", "Macierzy ocen dla „przekątnej” i „koloru” brak w druku — oceny wzięte z rys. 16 (macierz koloru z rys. 11 jest niespójna)."),
               ("conv", "Ocena Samsunga 248,65, w programie 248,64 (wagi zaokrąglone).")),
    "P4.5": _e("ok", "Porównanie wektorów JOS zgodne z drukiem.", ("ok", "JOS(Wojciech) = (1,1,1,1,2,3) ≤ JOS(Katarzyna) = (1,1,1,1,3,4).")),
    "P4.6": _e("ok", "ZAPROS odtworzony dokładnie.", ("ok", "JOS (tabl. 6), wektory (tabl. 7), relacje (tabl. 8) i graf (rys. 1); najlepsi a1, a4.")),
    "P4.7": _e("ok", "ZAPROS III zgodny z drukiem.", ("ok", "JSCV z trzech JSQV jak w druku; Kazimierz ≻ Zofia, Karolina ≻ Marek.")),
    "P4.8": _e("approx", "ZAPROS III odtworzony dokładnie; jedna relacja tylko z przechodniości.",
               ("ok", "JSQV (tabl. 3–5), JSCV (tabl. 6), FIQ (tabl. 7), rangi (tabl. 8) i graf."),
               ("info", "K9 ≻ K4 wynika tylko z przechodniości (K9 ≻ K1 ≻ K2 ≻ K4) — bezpośrednio nieporównywalne; tekst tego nie zaznacza.")),
    # --- rozdz. 5
    "P5.10": _e("diff", "Relacja i poziomy zgodne z drukiem; jedna wartość zgodności i graf od dołu nie.",
                ("diff", "c(a9, a7) w tabl. 6: 0,50, z danych 0,08 (tak też program w P5.12)."),
                ("ok", "Relacja S i poziomy rys. 1 dokładnie."),
                ("info", "d(a6, a9) = 3 (druk 0) — bez wpływu na wynik."),
                ("diff", "Rys. 2 (od najsłabszych): pakiet stawia a7 o poziom niżej niż a8; w druku razem na szczycie.")),
    "P5.11": _e("ok", "ELECTRE Iv zgodny z programem.", ("ok", "Relacja (tabl. 14, rys. 11) i poziomy {a7, a8}, {a1, a2, a4, a6}, {a5, a9}, {a3}.")),
    "P5.12": _e("ok", "ELECTRE Is zgodny z programem.", ("ok", "Relacja i poziomy jak w P5.11.")),
    "P5.13": _e("approx", "ELECTRE III zgodny z drukiem (różnica zaokrągleń).",
                ("ok", "σ (tabl. 13), destylacje i ranking a6 | a4 | a1, a5 | a2 | a3 (tabl. 26)."),
                ("conv", "c(a4, a5) = 0,665 (druk 0,66, a σ = 0,67).")),
    "P5.14": _e("approx", "Klasy i ranking zgodne z programem ELECTRE III.",
                ("ok", "Destylacje (5 i 4 klasy) i ranking a6 | a4 | a1, a5 | a3 | a2."),
                ("info", "Oceny a2 = (4, 8, 5, 2) — inne niż w P5.13. σ programu (rys. 12) wyglądają na zaokrąglone — nieporównywalne co do wartości.")),
    "P5.15": _e("diff", "Kategorie i σ zgodne z programem; ręczne obliczenia w druku z błędami.",
                ("ok", "a1 dobre, a3 słabe, pozostałe średnie (obie procedury); σ jak w programie (P5.17)."),
                ("diff", "Błędy obliczeń ręcznych: φ3(a4, b1), p3 = 3 w d3 i in. (errata).")),
    "P5.16": _e("diff", "Kategorie zgodne z programem; ręczne obliczenia w druku z błędami.",
                ("ok", "Kategorie jak w P5.15."),
                ("diff", "σ(a4, b2) = 0 w druku (P5.15: 0,54), progi v = 7, wniosek „a1 → C1” zamiast C3 (errata).")),
    "P5.19": _e("approx", "Zgodny z arkuszem P5.19; P5.18 pomija TSD.",
                ("ok", "Dominacje (TSD F13, F33, F43 nad F23; TISD2 F13 nad F43), c_E, c_N i sumy (rys. 4, 6, 7) dokładnie."),
                ("diff", "Tabl. 6 przykładu 5.18 pomija TSD, stąd inne Φ3 niż w P5.19."),
                ("ok", "s = 0,75 z parą niejasną (a5, a3): łuki a2→a1, a5→a1, a5→a2, a5→a3 (rys. 9).")),
    "P5.20": _e("diff", "ELECTRE III z dominacjami zgodny poza jedną wartością w druku.",
                ("ok", "c (tabl. 12), destylacje i ranking a4 | a5 | a1, a3 | a2."),
                ("diff", "σ(a3, a2) w tabl. 17: 0,0070, poprawnie 0,0700.")),
    # --- rozdz. 6
    "P6.2": _e("approx", "Przepływy i poziomy zgodne; obliczenia w druku na innych danych niż tabl. 1.",
               ("info", "Druk używa f1(a4) = 9,5 i f2(a6) = 1,5 (tabl. 1: 9 i 1) — indeksy π i przepływy są w obu wersjach identyczne."),
               ("ok", "φ⁺, φ⁻ i poziomy a5 | a2, a3 | a6, a7 | a1 | a4 (rys. 1) dokładnie; R: a2–a3, a6–a7.")),
    "P6.4": _e("ok", "PROMETHEE II zgodny z drukiem.", ("ok", "φ = −0,25; 0,2; −0,1; 0,25; −0,1.")),
    "P6.5": _e("ok", "Zgodny z Decision Lab.", ("ok", "φ⁺, φ⁻ do 4 miejsc; φ = 0,2179; −0,2089; 0,0841; −0,0931.")),
    "P6.7": _e("diff", "Druk liczy wskaźniki niezgodności odwrotnie niż wzór (6.20).",
               ("ok", "Indeksy zgodności c (tabl. 6) zgodne."),
               ("diff", "Tablice 7–9: d_k z f_k(aⁱ) − f_k(aʲ), odwrotnie niż (6.20); stąd σ(a2, a5) = 0,6, σ(a3, a5) = 0,15 i ranking a2, a3, a1/a4, a5."),
               ("info", "Wg (6.20): φ = −0,2; −0,3; −0,5; 0,2; 0,8, ranking a5, a4, a1, a2, a3. Wynik z druku daje opcja „Niezgodność: jak w przykładach 6.7 i 6.10”.")),
    "P6.8": _e("approx", "EXPROM zgodny z drukiem (zaokrąglenia).",
               ("ok", "TP i φ = −0,263; −0,486; 0,426; 0,323 (druk do 0,01); EXPROM I: a3 R a4.")),
    "P6.10": _e("diff", "Jak w P6.7: wskaźniki niezgodności odwrotnie niż wzór (6.20).",
                ("diff", "Druk: transponowane d, π = 0, ω = σ."),
                ("info", "Wg (6.20): φ = −0,2815; −0,3237; −0,5938; 0,2815; 0,9174, ranking a5, a4, a1, a2, a3. Wynik z druku daje opcja „Niezgodność: jak w przykładach 6.7 i 6.10”.")),
    "P6.11": _e("approx", "Przepływy dokładnie; tablica dominacji w druku z drobnymi błędami.",
                ("ok", "c (tabl. 12), σ (tabl. 17) i φ = −0,6457; −0,3739; −0,5205; 1,9259; −0,3858 dokładnie."),
                ("diff", "Tabl. 5: F11 nad F31 to SSD, nie FSD (tekst na s. 3 poprawnie); tabl. 7 wykazuje TISD2 spoza klasy DARA — nieużytą w obliczeniach.")),
    "P6.12": _e("ok", "Przepływy z porządkowymi i prawie dominacjami dokładnie.",
                ("ok", "φ = −1,003; 1,343; −0,092; 0,034; 0,137; −1,450; −2,635; 3,666 (OFSD, OSSD, OAFSD(0,333), OASSD(0,2))."),
                ("info", "Bez prawie dominacji a4 = 0,229, a8 = 3,471.")),
    "P6.14": _e("approx", "Przepływy dokładnie; tablica 24 w druku niespójna.",
                ("ok", "π (tabl. 23) i φ = −0,8012; −0,6239; −0,7614; 3,1632; −0,9767 dokładnie."),
                ("diff", "Tabl. 24: cztery wartości ω niezgodne z tabl. 17 i 23 i z dalszymi obliczeniami.")),
    "P6.16": _e("approx", "Przepływy zgodne do ±0,002; ranking zgodny.",
                ("ok", "OAFSD(0,2), OASSD(0,125); a2 4,660 (druk 4,661), a4 −3,249 (druk −3,251).")),
    # --- rozdz. 7
    "P7.1": _e("diff", "Wartości S zgodne; ranking w druku niezgodny z S.",
               ("ok", "S = 0,46; 0,53; 0,50; 0,35; 0,50; 0,46; 0,49; 0,52; 0,38."),
               ("diff", "Ranking w druku nie odpowiada malejącym S (poprawnie a2, a8, a3/a5, a7, a1/a6, a9, a4).")),
    "P7.3": _e("approx", "Rozmyty TOPSIS zgodny z tolerancją ok. 0,004.",
               ("ok", "S = 0,498; 0,452; 0,497; 0,323; 0,484; 0,391; 0,523; 0,608; 0,361."),
               ("conv", "Druk liczy z zaokrąglonych wartości pośrednich.")),
    "P7.4": _e("diff", "VIKOR zgodny co do wartości; rankingi R i S w druku zamienione.",
               ("ok", "S, R, Q zgodne; rozwiązanie kompromisowe a3 (W1, W2 spełnione)."),
               ("diff", "Rankingi według R i S zamienione (krok 4)."),
               ("conv", "Krok 6 w książce niekompletny — pakiet stosuje regułę Opricovica i Tzenga (2004).")),
    "P7.5": _e("diff", "DEMATEL zgodny; dwa elementy macierzy T w druku błędne.",
               ("ok", "r i c dokładnie."),
               ("diff", "T(3,3) = 3,1431 i T(4,4) = 2,3517 (w macierzy T w druku 3,1331 i 2,2517; tablice 4–5 poprawne).")),
    "P7.6": _e("approx", "Hybryda DEMATEL–ANP–VIKOR zgodna (zaokrąglenia); wniosek w druku niepełny.",
               ("ok", "T_D, T_f, W, wagi graniczne i S/R/Q (tabl. 5–11) zgodne; ranking a8, a10, a6, a9, a7, a11, a12, a5, a4, a3, a2, a1."),
               ("conv", "Q(a11) = 0,462 (druk 0,463)."),
               ("diff", "Krok 6: W1 i W2 niespełnione — rozwiązaniem kompromisowym jest para a8, a10, nie sam a8. Tabl. 16.5 (rozdz. 16) ma inny ranking.")),
    "P7.7": _e("diff", "Obliczenia w druku na danych z rys. 1, nie z tabl. 1; test weta niezgodny z (7.46).",
               ("info", "Przykład w pakiecie przyjmuje dane z rys. 1 (a1 = (1,5), a2 = (3,5), a3 = (4,3), a4 = (5,2))."),
               ("diff", "Test niekonfliktowości zawsze na ocenach wariantu (I⁻); wg (7.43)/(7.46) wszystkie warianty w B1. Druk odtwarza opcja „Test weta: jak w przykładach 7.7–7.12”.")),
    "P7.8": _e("approx", "Zgodny dla s = 0,4; dla s ∈ [0,5; 0,75) druk wymaga innej oceny.",
               ("ok", "D⁺, D⁻, kategorie i rankingi dla s = 0,4."),
               ("diff", "Nieporównywalność a6 przy s ∈ [0,5; 0,75) wymaga f₂(a6) = 6 (tabl. 1: 3); pakiet: a6 w B3.")),
    "P7.10": _e("approx", "Zmodyfikowane zbiory D i Z zgodne z rysunkami.", ("info", "Test weta jak w P7.7 (opcja „Test weta: jak w przykładach 7.7–7.12”).")),
    "P7.11": _e("approx", "Zmodyfikowane zbiory D i Z zgodne z rysunkami.", ("info", "Test weta jak w P7.7 (opcja „Test weta: jak w przykładach 7.7–7.12”).")),
    "P7.12": _e("approx", "a1 w kategorii B2′, jak w druku.", ("info", "Test weta jak w P7.7 (opcja „Test weta: jak w przykładach 7.7–7.12”).")),
    "P7.13": _e("diff", "Wagi, μ, ω i d_N zgodne; d_S w tabl. 11 niespójne z tabl. 9.",
                ("ok", "Wagi 0,378; 0,270; 0,351, μ = 196; 140; 182, ω = 0,863, d_N (tabl. 11)."),
                ("diff", "d_S pakietu = relacje tabl. 9 (0,9; 0,7; 0,7; −0,65; …); tabl. 11 niespójna z tabl. 9 dla a4–a6 i a8–a10 (nie tylko zamienione nagłówki).")),
    "P7.15": _e("diff", "Kategorie S zgodne; kategorie N dwóch wariantów nie wynikają z danych.",
                ("ok", "Kategorie S jak w tabl. 2."),
                ("diff", "a4, a6: pakiet N1, druk N2; stąd a6 w B1 (druk: bez kategorii).")),
    "P7.16": _e("approx", "BIPOLAR z dominacjami zgodny do ±0,001.", ("ok", "d_S, d_N; ranking a8, a2, a4, a5, a3, a1, a6, a7.")),
    # --- część II
    "R9.2": _e("approx", "Model Gershona odtworzony dokładnie; liczba usuniętych kryteriów w druku niespójna.",
               ("ok", "L1 = 11,6; 29,2; 15,8; 9,8; 16; 13,625; 14,125; EXPROM II pierwsza, ELECTRE III ostatnia."),
               ("diff", "Druk: „10 kryteriów usuniętych”, wymienia 9 — dziesiątym jest f9 (bez wpływu na wynik).")),
    "R9.3": _e("ok", "Procedura Tecle'a odtworzona dokładnie.", ("ok", "L1 = 95,33; 197,94; 119,01; 92,85; 123,83; 110,90; 112,45.")),
    "R9.5": _e("approx", "Kolejność zgodna z tabl. 9.6; Φ różne o ≤ 0,003.",
               ("conv", "σ i ω w R9.5 zaokrąglone; pakiet liczy wg (6.20)."),
               ("info", "Kolumna „Minimum” tabl. 9.4 nie wchodzi do obliczeń — tekst tego nie mówi.")),
    "R9.5E": _e("approx", "Kolejność zgodna z tabl. 9.6; Φ różne o ≤ 0,003.", ("conv", "σ i ω w R9.5 zaokrąglone; pakiet liczy wg (6.20).")),
    "R9.7I": _e("diff", "Punkty ważone różnią się od ocen łącznych druku dla 11 projektów.",
                ("diff", "Niezgodne projekty 1, 2, 9, 13, 23, 31, 38, 39, 40, 48, 54; oceny spoza skali 0–4 (a9 f15, a23 f14, a38 f12)."),
                ("info", "Mierniki R9.11 z pozycji R9.10 odtwarzają się dokładnie.")),
    "R9.7II": _e("diff", "Punkty ważone różnią się od ocen łącznych druku dla 6 projektów.",
                 ("diff", "Niezgodne projekty 1, 8, 11, 15, 16, 36; w R9.8/R9.10 projekt 20 na 17. zamiast 18. pozycji."),
                 ("info", "Mierniki R9.11 z pozycji R9.10 odtwarzają się dokładnie.")),
    "R11": _e("approx", "ANP z supermacierzy R11.1 zgodny (zaokrąglenia).",
              ("ok", "R11.3 (17/17, ±0,00006); priorytety 0,3035; 0,4415; 0,2551 (druk 0,2550)."),
              ("info", "Tabl. 11.3, wiersz e15: trzy jedynki, których nie ma w R11.1 (kolumna UF).")),
    "R12": _e("diff", "Uporządkowanie R12.4 nie odtwarza się z danych R12.1–R12.2.",
              ("diff", "R12.4 dzieli liczby przewag przez 150 i 195, a zbiory R12.2 mają 149 i 194 elementy; zgodność przybliżona (ρ Spearmana 0,92 / 0,91)."),
              ("diff", "Progi weta w druku z decyli tabl. 12.3 (14,97; 1,40; …); z danych 14,77; 1,376; 0,063; 0,742; 0,473; 0,838; 0,044."),
              ("info", "τ z danych = 75, 76, 57, 72, 55, 85, 62; decyle tabl. 12.3–12.4 nieodtwarzalne żadną definicją kwantyla.")),
    "R13": _e("approx", "Ranking z s. 253 odtworzony przy regule dekompozycji.",
              ("ok", "Ranking Sarni Stok, Ogrody, Piast, King Cross Praga, graf liniowy."),
              ("diff", "Rys. 13.7, porównanie 2: 68 najemców zamiast 69 (z 69 trzy porównania to to samo pytanie)."),
              ("conv", "Książka nie podaje reguły wnioskowania UniComBOS — pakiet stosuje zasadę dekompozycji (Ashikhmin, Furems 2005).")),
    "R13.2": _e("approx", "Graf rys. 13.6 to stan po 8 z 39 porównań R13.2.",
                ("ok", "Po 8 porównaniach: Sarni Stok nad trzema pozostałymi (rys. 13.6)."),
                ("info", "Po wszystkich porównaniach także Ogrody ≻ King Cross Praga i Ogrody ≻ Piast; nierozstrzygnięta para King Cross Praga–Piast."),
                ("conv", "Reguła dekompozycji jak w R13.")),
    "R14": _e("approx", "Rozmyty TOPSIS z rozdz. 14 zgodny do 4 miejsc; wzór (7.10) w druku inny niż przykład.",
              ("ok", "S = 0,2706; 0,6507; 0,1656; 0,3391; 0,5145; 0,5376."),
              ("diff", "Normalizacja kosztowa: przykład i tabl. 14.4 liczą z min l, wzór (7.10) w druku — z min u (opcja „Kryteria kosztowe: min u” daje wersję wzoru)."),
              ("diff", "Tabl. 14.5: a6, f2 (0,28; …) zamiast (0,38; …); poziom rezerwacji f3 0,20 zamiast 0,02.")),
    "R15": _e("diff", "Oceny dwóch pracowników w tabl. 15.6 nie wynikają z danych.",
              ("diff", "a24 = −0,0065 (druk 0,1952, poz. 1), a42 = −0,0236 (druk 0,1574, poz. 4); pozostałe oceny wyższe o ok. 0,008."),
              ("diff", "Ósemka z danych: a37, a41, a2, a26, a8, a68, a67, a66 — teza o tej samej ósemce w obu rankingach nie wynika z danych.")),
    "R15A": _e("diff", "Tabl. 15.8 zgodna dla 48 ocen; trzy oceny nie wynikają z danych.",
               ("diff", "Nagłówki kolumn tabl. 15.7 zamienione (z zamianą ρ = 0,989, wg druku 0,70)."),
               ("diff", "a42 0,0261 (druk 0,0365), a24 0,0341 (0,0377), a39 0,0227 (0,0252); ósemka z a67 zamiast a8."),
               ("conv", "Różnice zaokrąglane do 0,01 przed odczytem klasy (luki między przedziałami tabl. 15.7).")),
    "R16": _e("diff", "Łuki zgodne z tabl. 16.2; ranking w druku z dwiema niespójnościami.",
              ("ok", "Liczby łuków 2/5/10/21/38 dla s = 0,94 … 0,72; poziomy jak s. 288–290."),
              ("diff", "s = 0,86: a5 na poziomie 3, nie 1 („sześć wariantów” — wymieniono siedem)."),
              ("info", "s = 0,72: ranking z druku tylko przy pominięciu łuków dwukierunkowych; rys. 16.2 bez łuku 8 → 7.")),
}

# kotwice erraty: domyślnie sekcja przykładów / zbiorów z CD albo rozdziału
for _id, _c in CHECKS.items():
    if _c["errata"]: continue
    if _id.startswith("P"):
        _c["errata"] = _CD.format(int(_id[1:].split(".")[0]))
    else:
        _ch = int("".join(ch for ch in _id[1:].split(".")[0] if ch.isdigit()))
        _c["errata"] = _BOOK.get(_ch) or _ZB.format(_ch)
CHECKS["R9.2"]["errata"] = CHECKS["R9.3"]["errata"] = _BOOK[9]
CHECKS["R9.7I"]["errata"] = CHECKS["R9.7II"]["errata"] = _ZB.format(9)


def get(example_id: str) -> Optional[Dict[str, Any]]:
    c = CHECKS.get(example_id)
    if c is None: return None
    return dict(c, id=example_id, status_label=STATUS[c["status"]])


def summary() -> List[Dict[str, Any]]:
    return [dict(get(k)) for k in CHECKS]
