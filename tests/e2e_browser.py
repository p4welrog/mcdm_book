"""Test strony index.html w przeglądarce (Playwright): przykłady z książki we wszystkich zakładkach.

Uruchomienie (z katalogu repozytorium, po `python web/build.py`):

    pip install playwright && python -m playwright install chromium
    python tests/e2e_browser.py                         # Pyodide z cdn.jsdelivr.net
    python tests/e2e_browser.py --pyodide node_modules/pyodide --chrome /usr/bin/google-chrome

--pyodide KATALOG — lokalna kopia Pyodide 0.26.4 (np. `npm install pyodide@0.26.4`), gdy CDN jest niedostępny;
--chrome ŚCIEŻKA  — systemowa przeglądarka zamiast pobranej przez Playwright;
--shots KATALOG   — zrzuty ekranu kolejnych etapów.
Kod wyjścia 0, gdy wszystkie kontrole przeszły. Plik nie jest zbierany przez pytest (nazwa nie zaczyna się od test_).
"""
import argparse
import mimetypes
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
PAGE = "https://test.local/index.html"

failures = []


def check(cond, label, detail=""):
    print(("OK   " if cond else "FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(ROOT / "index.html"))
    ap.add_argument("--pyodide")
    ap.add_argument("--chrome")
    ap.add_argument("--shots")
    a = ap.parse_args()
    index = Path(a.index)
    pyo = Path(a.pyodide) if a.pyodide else None
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    def route(r):
        url = r.request.url
        if pyo and url.startswith(CDN):
            f = pyo / url[len(CDN):].split("?")[0]
            if f.exists():
                return r.fulfill(path=str(f), content_type=mimetypes.guess_type(str(f))[0] or "application/octet-stream")
            return r.fulfill(status=404, body="nf")
        if url.startswith("https://test.local/"):
            return r.fulfill(path=str(index), content_type="text/html; charset=utf-8")
        return r.continue_()

    def shot(name):
        if shots:
            page.screenshot(path=str(shots / f"{name}.png"), full_page=True)

    with sync_playwright() as p:
        kw = {"executable_path": a.chrome, "args": ["--no-sandbox"]} if a.chrome else {}
        browser = p.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.route("**/*", route)
        page.goto(PAGE)
        page.wait_for_selector("#loading", state="hidden", timeout=180000)
        check(page.locator("#dist-table tr").count() > 2, "ładowanie Pyodide i pakietów")

        # --- zakładka rankingu: przykłady z książki ---
        expected = {"P2.1": ("saw", "a3"), "P2.2": ("scoring", "a3"), "P2.3": ("fsaw", "a3"), "P2.7": ("smart", "a3, a4"),
                    "P2.11": ("smarter", "a4"), "P3.4": ("ahp", "a6"), "P3.7": ("rembrandt", "a1"),
                    "P3.10": ("fuzzy_ahp", "a1"), "P3.12": ("anp", "a1"), "P3.13": ("anp", "dostawca Y"),
                    "P3.14": ("fuzzy_anp", "a1"), "P4.2": ("macbeth_scale", "f1 cena lokalu"), "P4.3": ("macbeth", "Samsung Galaxy S3"),
                    "P4.5": ("zapros", "Wojciech"), "P4.6": ("zapros", "a1, a4"), "P4.8": ("zapros_iii", "K9"),
                    "P5.10": ("electre_i", "a7, a8"), "P5.11": ("electre_iv", "a7, a8"),
                    "P5.12": ("electre_is", "a7, a8"), "P5.13": ("electre_iii", "a6"), "P5.14": ("electre_iii", "a6"),
                    "P5.15": ("electre_tri", "a1"), "P5.16": ("electre_tri", "a1"), "P5.19": ("electre_i_sd", "a4, a5"),
                    "P5.20": ("electre_iii_sd", "a4"), "P6.2": ("promethee_i", "a5"), "P6.5": ("promethee_ii", "a1"),
                    "P6.7": ("promethee_ii_veto", "a5"), "P6.8": ("exprom", "a3"), "P6.10": ("exprom_veto", "a5"),
                    "P6.11": ("promethee_ii_sd", "a4"), "P6.12": ("promethee_ii_sd", "a8"),
                    "P6.14": ("exprom_ii_sd", "a4"), "P6.16": ("exprom_ii_sd", "a2"), "P7.1": ("topsis", "a2"), "P7.3": ("fuzzy_topsis", "a8"),
                    "P7.4": ("vikor", "a3"), "P7.5": ("dematel", "C3 wartości muzyczne"), "P7.6": ("hybrid", "a8, a10"),
                    "P7.7": ("bipolar", "a4"), "P7.8": ("bipolar", "a1, a3"), "P7.12": ("bipolar", "a4"),
                    "P7.13": ("bipolar", "a1"), "P7.16": ("bipolar_sd", "a8"), "R14": ("fuzzy_topsis", "a2"), "R9.2": ("compromise", "EXPROM II"),
                    "R13": ("unicombos", "Sarni Stok"), "R15A": ("ahp", "a24"), "R9.7I": ("scoring", "a6")}
        for ex, (meth, best) in expected.items():
            page.select_option("#bk-method", meth)
            page.select_option("#bk-example", ex)
            page.click("#bk-load")
            page.click("#bk-run")
            txt = page.locator("#bk-out .note.ok").inner_text()
            check(txt.endswith(best), f"{ex} ({meth})", txt)
            shot(f"rank_{ex}")

        # --- edytor AHP: bieżąca zgodność i autouzupełnianie odwrotności ---
        page.select_option("#bk-method", "ahp"); page.select_option("#bk-example", "P3.4"); page.click("#bk-load")
        page.select_option("#bk-options select[data-o=method]", "saaty")
        check("γ = 0,006" in page.locator("[data-check='cc']").inner_text(), "AHP: zgodność macierzy kryteriów na żywo")
        sel = "table[data-matrix='c:f1'] input[data-mi='0'][data-mj='5']"
        page.fill(sel, "1/9"); page.dispatch_event(sel, "input")
        check(page.input_value("table[data-matrix='c:f1'] input[data-mi='5'][data-mj='0']") == "9", "AHP: odwrotność")
        check("niezgodne" in page.locator("[data-check='c:f1']").inner_text(), "AHP: wykrycie niezgodności")

        # --- puste zadanie AHP ---
        page.select_option("#bk-example", ""); page.click("#bk-load")
        for tid, vals in (("cc", {(0, 1): "3"}), ("c:f1", {(0, 1): "5", (0, 2): "7", (1, 2): "3"}),
                          ("c:f2", {(0, 1): "1/3", (0, 2): "1/5", (1, 2): "1/2"})):
            for (i, j), v in vals.items():
                s = f"table[data-matrix='{tid}'] input[data-mi='{i}'][data-mj='{j}']"
                page.fill(s, v); page.dispatch_event(s, "input")
        page.click("#bk-run")
        check(page.locator("#bk-out .note.ok").inner_text().endswith("a1"), "AHP: zadanie wpisane od zera")

        # --- edytor ANP: sieć z przykładu 3.12 ---
        page.select_option("#bk-method", "anp"); page.select_option("#bk-example", "P3.12"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-dep]").count() == 30, "ANP: macierz zależności 6×6")
        check(page.input_value("table[data-matrix='cl:AT'] input[data-mi='1'][data-mj='0']") == "3",
              "ANP: odwrotność w porównaniach komponentów")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("0,8084" in out and "0,2129" in out, "ANP: supermacierz graniczna (tabl. 17–18)")
        page.uncheck("#bk-editor input[data-dep='a1'][data-to='f4']")
        check(page.locator("#bk-editor input[data-dep]").count() == 30, "ANP: przebudowa po zmianie zależności")
        page.click("#bk-run")
        out2 = page.locator("#bk-out .note.ok").inner_text()
        check(out2.startswith("Najlepszy") and "0,8084" not in page.locator("#bk-out").inner_text(),
              "ANP: zmiana zależności zmienia wynik", out2)
        sel = "table[data-matrix='el:f1|W'] input[data-mi='0'][data-mj='1']"
        page.fill(sel, "1/5"); page.dispatch_event(sel, "input")
        check(page.input_value("table[data-matrix='el:f1|W'] input[data-mi='1'][data-mj='0']") == "5",
              "ANP: odwrotność w porównaniach elementów")
        page.select_option("#bk-method", "fuzzy_anp"); page.select_option("#bk-example", "P3.14"); page.click("#bk-load")
        page.click("#bk-run")
        check("0,8285" in page.locator("#bk-out").inner_text(), "rozmyta ANP: wynik przykładu 3.14")
        shot("anp")

        # --- PROMETHEE / EXPROM: relacje, weto jak w druku, edycja rozkładu ---
        page.select_option("#bk-method", "promethee_i"); page.select_option("#bk-example", "P6.2"); page.click("#bk-load")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("Relacje PROMETHEE I" in out and "a5 → a2" in out, "PROMETHEE I: relacje i graf (przykład 6.2)")
        page.select_option("#bk-method", "promethee_ii_veto"); page.select_option("#bk-example", "P6.7"); page.click("#bk-load")
        page.select_option("#bk-options select[data-o=veto_direction]", "example"); page.click("#bk-run")
        check(page.locator("#bk-out .note.ok").inner_text().endswith("a2"), "PROMETHEE II z wetem: wariant z druku")
        page.wait_for_timeout(100)
        hrefs = page.eval_on_selector_all("main a.bk", "els => els.map(e => e.getAttribute('href').split('#')[1] + ' ← ' + e.textContent)")
        print("     odsyłacze:", "; ".join(hrefs[:12]))
        check(any(h.startswith("cd6-P6-7 ") for h in hrefs) and any(h.startswith("r6-") for h in hrefs),
              "odsyłacze do transkrypcji: przykład 6.7 i rozdz. 6", f"{len(hrefs)} linków")
        check(not page.locator("#bk-options a.bk, #bk-editor a.bk, table a.bk").count(), "odsyłacze: bez linków w polach i tablicach")
        page.click("nav button[data-tab=info]"); page.fill("#book-base", ""); page.click("#book-save")
        check(page.locator("main a.bk").count() == 0, "odsyłacze: pusty adres wyłącza linki")
        page.click("#book-reset")
        check(page.locator("main a.bk").count() == len(hrefs), "odsyłacze: przywrócenie adresu domyślnego")
        page.click("nav button[data-tab=rank]")
        page.select_option("#bk-method", "promethee_ii_sd"); page.select_option("#bk-example", "P6.11"); page.click("#bk-load")
        check(page.input_value("#bk-editor input[data-i='0'][data-k='0']").startswith("0:0,6"), "rozkład w komórce edytora")
        page.fill("#bk-editor input[data-i='0'][data-k='0']", "0:0,1 4:0,9"); page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("Dominacje stochastyczne" in out and "1,9259" not in out, "PROMETHEE II SD: edycja rozkładu zmienia wynik")
        shot("promethee")

        # --- ELECTRE: destylacje, profile TRI, pary niejasne ---
        page.select_option("#bk-method", "electre_iii"); page.select_option("#bk-example", "P5.13"); page.click("#bk-load")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("Destylacja zstępująca" in out and "4. a2, a3" in out and "3. a3" in out, "ELECTRE III: destylacje (przykład 5.13)")
        page.select_option("#bk-method", "electre_tri"); page.select_option("#bk-example", "P5.15"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-b]").count() == 8, "ELECTRE TRI: profile w edytorze")
        page.click("#bk-add-prof")
        check(page.locator("#bk-editor input[data-b]").count() == 12, "ELECTRE TRI: dodanie profilu")
        page.fill("#bk-editor input[data-b='2'][data-k='3']", "11"); page.fill("#bk-cats", "słabe | średnie | dobre | znakomite")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("znakomite" not in out.split("Wynik")[1].split("\n")[1] and "σ(a, b3)" in out, "ELECTRE TRI: trzeci profil i kategorie", out[:200])
        page.select_option("#bk-method", "electre_i_sd"); page.select_option("#bk-example", "P5.19"); page.click("#bk-load")
        page.select_option("#bk-options select[data-o=include_unclear]", "false"); page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("a5 → a3" not in out and "Pary niejasne" in out, "ELECTRE I SD: para niejasna tylko wskazana")
        shot("electre")

        # --- BIPOLAR i DEMATEL: obiekty referencyjne, macierze wpływu ---
        page.select_option("#bk-method", "bipolar"); page.select_option("#bk-example", "P7.12"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-ref]").count() == 10, "BIPOLAR: obiekty referencyjne w edytorze")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("B2′" in out and "Relacje wariantów" in out, "BIPOLAR: kategoria B2′ i relacje (przykład 7.12)")
        page.select_option("#bk-options select[data-o=b2_prime]", "false"); page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("brak" in out, "BIPOLAR: wariant bez kategorii bipolarnej")
        page.click("#bk-editor button[data-add-ref=bad]")
        check(page.locator("#bk-editor input[data-ref=bad]").count() == 6, "BIPOLAR: dodanie obiektu „złego”")
        page.select_option("#bk-method", "dematel"); page.select_option("#bk-example", "P7.5"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-mx=influence]").count() == 16, "DEMATEL: macierz wpływu w edytorze")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("przyczyna" in out and "skutek" in out, "DEMATEL: przyczyny i skutki")
        page.select_option("#bk-method", "hybrid"); page.select_option("#bk-example", "P7.6"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-mx=cluster_influence]").count() == 16
              and page.locator("#bk-editor input[data-mx=criteria_influence]").count() == 144, "Hybryda: macierze wpływu grup i kryteriów")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("Znormalizowana macierz T grup" in out and "Ranking Q: a8, a10" in out, "Hybryda: T grup i ranking VIKOR")
        shot("bipolar")

        # --- MACBETH i ZAPROS: macierze ocen werbalnych, JOS, JSQV ---
        page.select_option("#bk-method", "macbeth"); page.select_option("#bk-example", "P4.3"); page.click("#bk-load")
        check(page.locator("#bk-editor select[data-mm='__w']").count() == 20, "MACBETH: macierz wag z [ all lower ]")
        page.select_option("#bk-editor select[data-mm='c0'][data-r='0'][data-k='2']", "weak"); page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("niespójne oceny" in out and "Doskonała–Dobra: weak →" in out, "MACBETH: niespójne oceny i sugestia zmiany", out[:300])
        page.select_option("#bk-editor select[data-mm='c0'][data-r='0'][data-k='2']", "strong"); page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("248,6" in out and "122,2222" in out, "MACBETH: oceny końcowe i skala ciężaru (rys. 14, 16)")
        page.select_option("#bk-method", "zapros"); page.select_option("#bk-example", "P4.6"); page.click("#bk-load")
        check(page.locator("#bk-editor select[data-zy]").count() == 42, "ZAPROS: porównania wektorów Y w edytorze")
        page.select_option("#bk-editor select[data-zap-mode]", "jos"); page.fill("#zap-jos", "A1 B1 C1 | C2 | A2 | B2 | B3 | A3 C3")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("a1 → a2" in out and "(1, 2, 4)" in out, "ZAPROS: JOS wpisana ręcznie, graf porządku")
        page.select_option("#bk-method", "zapros_iii"); page.select_option("#bk-example", "P4.8"); page.click("#bk-load")
        page.click("#bk-editor button[data-zap-mode]")
        check("C1>C2, A1>A2" in page.locator("#zap-jscv").input_value(), "ZAPROS III: tablice wariacji → JSCV")
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("K9 → K1" in out and "1. (C1→C2)" in out, "ZAPROS III: rangi i JSCV (przykład 4.8)")
        shot("macbeth_zapros")

        # --- UniComBOS: porównania w edytorze, pytania z wyniku ---
        page.select_option("#bk-method", "unicombos"); page.select_option("#bk-example", "R13.2"); page.click("#bk-load")
        n0 = len(page.locator("#uni-comps").input_value().strip().split("\n"))
        check(n0 == 99, "UniComBOS: 99 porównań R13.1 (60) + R13.2 (39) w edytorze", str(n0))
        page.click("#bk-run")
        out = page.locator("#bk-out").inner_text()
        check("Sarni Stok → Ogrody" in out and "Pytania do porównań" in out, "UniComBOS: graf i pytania (R13.2)", out[:300])
        page.click("#bk-out [data-uni-q='0'][data-uni-a='<']")
        page.wait_for_timeout(300)
        n1 = len(page.locator("#uni-comps").input_value().strip().split("\n"))
        check(n1 == 100, "UniComBOS: odpowiedź na pytanie dopisuje porównanie", str(n1))
        page.select_option("#bk-method", "ahp"); page.select_option("#bk-example", "R15A"); page.click("#bk-load")
        check(page.locator("#bk-editor input[data-c='difference_scale']").count() == 3, "AHP: macierze z różnic ocen (rozdz. 15)")
        shot("unicombos_ahp15")

        # --- dobór metody ---
        page.click("#sel-box summary")
        page.check("input[name=sel-data][value=qualitative]")
        page.check("input[name=sel-pref][value=pairwise]")
        page.uncheck("input[name=sel-pref][value=weights]")
        page.click("#sel-run")
        first = page.locator("#sel-out tbody tr").first.inner_text()
        check("AHP" in first, "dobór metody: porównania parami → AHP", first.replace("\t", " | "))
        shot("select")
        page.locator("#sel-out [data-use]").first.click()
        check(page.input_value("#bk-method") == "ahp", "dobór metody: przycisk „Użyj”")
        page.click("#sel-box summary")
        page.check("#sel-dep"); page.click("#sel-run")
        first = page.locator("#sel-out tbody tr").first.inner_text()
        check("ANP" in first, "dobór metody: zależności między kryteriami → ANP", first.replace("\t", " | "))
        page.uncheck("#sel-dep")
        page.uncheck("input[name=sel-data][value=qualitative]"); page.check("input[name=sel-data][value=numeric]")
        page.select_option("#sel-output", "sort"); page.click("#sel-run")
        first = page.locator("#sel-out tbody tr").first.inner_text()
        check("ELECTRE TRI" in first, "dobór metody: sortowanie → ELECTRE TRI", first.replace("\t", " | "))
        page.select_option("#sel-output", "ranking"); page.click("#sel-box summary")

        # --- edycja zadania i błędne dane (TOPSIS) ---
        page.select_option("#bk-method", "topsis"); page.select_option("#bk-example", "P7.1"); page.click("#bk-load")
        page.fill("#bk-editor input[data-i='3'][data-k='2']", "20"); page.click("#bk-run")
        check(page.locator("#bk-out .note.ok").inner_text().endswith("a4"), "TOPSIS: zmiana oceny zmienia wynik")
        page.click("#bk-add-var"); page.click("#bk-run")
        check(page.locator("#bk-out table").first.locator("tbody tr").count() == 10, "TOPSIS: dodanie wariantu")
        page.fill("#bk-editor input[data-i='0'][data-k='0']", "abc"); page.click("#bk-run")
        check("Niepoprawna liczba" in page.locator("#bk-out .note.bad").inner_text(), "TOPSIS: komunikat o błędnych danych")

        # --- zakładki programów z płyty (mcdm_cd) ---
        page.click("nav button[data-tab=dom]")
        page.wait_for_selector("#dom-table table")
        row = page.locator("#dom-table tr").nth(2).locator("td").all_inner_texts()
        check(row[:4] == ["a2", "FSD", "", "FSD"], "wykryte dominacje (przykład 8.4)", str(row[:4]))

        page.click("nav button[data-tab=stdom]")
        page.check("#sd-afsd"); page.click("#sd-run")
        check("0,2500" in page.locator("#sd-report").inner_text(), "StDom: AFSD ε = 0,25 (przykład 1.10)")

        page.click("nav button[data-tab=stem]")
        page.click("#stem-start")

        def q(scope, text):
            page.locator(f"{scope} .question button", has_text=text).first.click()

        q("#stem-q", "Nie"); q("#stem-q", "Tak"); q("#stem-q", "X3")
        page.fill("#stem-thr", "6"); page.click("#stem-thr-ok"); q("#stem-q", "Tak")
        check(page.locator("#stem-log .note").last.inner_text().endswith("a3"), "STEM-DPR (przykład 8.2)")

        page.click("nav button[data-tab=insdecm]")
        page.click("#ins-start")

        def params(sel_):
            for pp, psi in sel_.items():
                page.check(f"#pp-{pp}")
                if psi is not None:
                    page.fill(f"#psi-{pp}", str(psi))
            page.click("#pp-ok")

        params({8: "6"}); params({}); params({}); params({})
        q("#ins-q", "Tak"); q("#ins-q", "Nie")
        page.select_option("#c-k", "0"); page.select_option("#c-p", "8"); page.fill("#c-v", "0,5"); page.click("#c-ok")
        q("#ins-q", "Tak"); q("#ins-q", "Nie")
        params({}); params({8: "5"}); params({}); params({})
        q("#ins-q", "Tak"); q("#ins-q", "Nie")
        page.select_option("#c-k", "1"); page.select_option("#c-p", "8"); page.fill("#c-v", "0,65"); page.click("#c-ok")
        q("#ins-q", "Tak"); q("#ins-q", "Nie")
        params({}); params({}); params({8: "7,5"}); params({})
        q("#ins-q", "Tak"); q("#ins-q", "Tak"); q("#ins-q", "Tak")
        check(page.locator("#ins-log .note").last.inner_text().endswith("a4, a5, a9"), "INSDECM (przykład 8.4)")
        shot("insdecm")

        page.click("nav button[data-tab=dane]")
        page.select_option("#example", "przyklad_8_5")
        page.wait_for_function("document.querySelector('#problem-info').innerText.includes('8.5')", timeout=15000)
        page.click("nav button[data-tab=ato]")
        page.click("#ato-book"); page.click("#ato-start")

        def order(names):
            crit = ["X1", "X2", "X3", "X4"]
            for pos, nm in enumerate(names):
                page.select_option(f"#ato-q select[data-ato-pos='{pos}']", str(crit.index(nm)))
            page.click("#ato-ord-ok")

        check("a6" in page.locator("#ato-log h4").last.inner_text(), "ATO-DPR: pierwszy wariant próbny a6 (tabl. 13)")
        q("#ato-q", "Nie"); order(["X3", "X4", "X1", "X2"])
        log = page.locator("#ato-log").inner_text()
        check("a1, a7" in log and "a1" in page.locator("#ato-log h4").last.inner_text(), "ATO-DPR: współczynniki wymiany → a1 (tabl. 17–19)")
        q("#ato-q", "Nie"); order(["X2", "X3", "X4", "X1"])
        q("#ato-q", "Tak")
        check(page.locator("#ato-log .note").last.inner_text().endswith("a4"), "ATO-DPR (przykład 8.5)")
        shot("ato_dpr")

        page.click("nav button[data-tab=dane]")
        page.select_option("#example", "Przyklad_1")
        check("20 wariantów" in page.locator("#problem-info").inner_text(), "odczyt Przyklad_1.mcf")
        page.set_input_files("#mcf-file", str(ROOT / "mcdm_cd" / "data" / "przyklad_8_1.mcf"))
        page.wait_for_function("document.querySelector('#problem-info').innerText.includes('przyklad_8_1')", timeout=15000)
        check("10 wariantów" in page.locator("#problem-info").inner_text(), "wczytanie pliku .mcf z dysku")

        check(not errors, "brak błędów JavaScript", "; ".join(errors))
        browser.close()

    print(f"\n{'Wszystkie kontrole przeszły.' if not failures else f'Nieudane: {len(failures)}'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
