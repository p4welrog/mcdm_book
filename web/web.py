"""Most między stroną (JavaScript) a pakietami mcdm_ryzyko i mcdm_book w Pyodide. Wejście i wyjście: JSON.

Zakładki „Zadanie”, „StDom”, STEM-DPR, INSDECM i ATO-DPR korzystają z `mcdm_ryzyko` (rozkłady, dominacje
stochastyczne, rozdz. 1.3 i 8.3–8.4) oraz `mcdm_book.ato_dpr` (rozdz. 8.5). Procedury są generatorami pytań;
tu prowadzi je `mcdm_ryzyko.Sesja`, a pytania są tłumaczone na rodzaje obsługiwane przez stronę.
"""
from __future__ import annotations

import json
import math

from mcdm_ryzyko import (OSLAB, PODTRZYMAJ, PRZERWIJ, ZAOSTRZ, BlednaOdpowiedz, Insdecm, Parametr, Postawa, Prog,
                         RegulaDominacji, Relacja, RodzajParametru as RP, Rozklad, Sesja, StemDpr, Warunek,
                         porownaj, porownaj_porzadkowo, wczytaj_mcf)
from mcdm_ryzyko import insdecm as ins
from mcdm_ryzyko import stem_dpr as stem

from mcdm_book import ato_dpr as ato
from mcdm_book.ryzyko import EXAMPLES, example as ryzyko_example

S = {"problem": None, "method": None, "sesja": None, "kind": None, "pending": None, "iter": 0}


def _f(x):
    """Liczba do JSON (NaN → None)."""
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def _out(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _fmt(x) -> str:
    return f"{float(x):g}".replace(".", ",")


# ---------------------------------------------------------------------------
# Dane
# ---------------------------------------------------------------------------

def _summary(p, source: str) -> dict:
    return {"comment": "", "source": source, "criteria": [k.nazwa for k in p.kryteria],
            "maximize": [k.maksymalizowane for k in p.kryteria], "variants": list(p.warianty), "warnings": [],
            "n": p.m, "m": p.n}


def examples() -> str:
    return _out([{"id": k, "label": v} for k, v in EXAMPLES.items()])


def load_example(name: str) -> str:
    if name not in EXAMPLES:
        raise ValueError(f"Nieznany przykład {name}")
    S["problem"] = ryzyko_example(name)
    source = {"przyklad_8_5": "przykład 8.5", "rozdz_10": "rozdz. 10 (R10.3–R10.5)"}.get(name, f"{name}.mcf")
    return _out(_summary(S["problem"], source))


def load_bytes(data, filename: str) -> str:
    S["problem"] = wczytaj_mcf(bytes(data))
    return _out(_summary(S["problem"], filename))


def distributions(k: int) -> str:
    p = S["problem"]
    vals = sorted({v for i in range(p.m) for v in p.ocena(i, k).wartosci})
    rows = []
    for v in vals:
        rows.append([_f(v)] + [_f(dict(p.ocena(i, k).pary()).get(v, 0)) for i in range(p.m)])
    return _out({"criterion": p.kryteria[k].nazwa, "variants": list(p.warianty), "rows": rows,
                 "means": [_f(p.ocena(i, k).wartosc_oczekiwana()) for i in range(p.m)]})


def variant_dist(i: int, k: int) -> str:
    d = S["problem"].ocena(i, k)
    return _out({"values": [_f(x) for x in d.wartosci], "probs": [_f(x) for x in d.prawdopodobienstwa]})


def dominance_matrix(k: int) -> str:
    """Dominacje dla kryterium k (wiersz nad kolumną): FSD, SSD, TSD (awersja do ryzyka) albo AFSD(ε) dla ε < 0,5."""
    p = S["problem"]
    regula = RegulaDominacji.awersja()
    rows = []
    for i in range(p.m):
        row = []
        for j in range(p.m):
            if i == j:
                row.append("")
                continue
            w = p.porownanie(i, j, k)
            r = regula.relacja(w)
            if r is not None:
                row.append(r.value)
            elif w.eps_afsd is not None and w.eps_afsd < 0.5 - p.tolerancja:
                row.append(f"AFSD({float(w.eps_afsd):.2f})".replace(".", ","))
            else:
                row.append("")
        rows.append(row)
    return _out({"criterion": p.kryteria[k].nazwa, "variants": list(p.warianty), "rows": rows})


# ---------------------------------------------------------------------------
# StDom — dwa rozkłady
# ---------------------------------------------------------------------------

def stdom(xv, xp, yv, yp, ordinal: bool, risk: str, almost: bool, almost_second: bool) -> str:
    """Czy X dominuje Y: relacje z tabl. 1.1 (zwykłe) albo 1.3 (porządkowe), stopnie ε z tabl. 1.2 / 1.4."""
    xv, xp, yv, yp = list(xv), list(xp), list(yv), list(yp)
    x, y = Rozklad(xv, xp), Rozklad(yv, yp)
    rows, holds = [], {}
    if ordinal:
        skala = sorted(set(xv) | set(yv))
        w = porownaj_porzadkowo(x, y, skala)
        names = [Relacja.OFSD, Relacja.OSSD]
    else:
        w = porownaj(x, y)
        names = list((Postawa.AWERSJA if risk == "DARA" else Postawa.SKLONNOSC).relacje)
        holds = {r.value: r in w.definicje for r in (Relacja.FSD, Relacja.SSD, Relacja.TSD,
                                                     Relacja.SISD, Relacja.TISD1, Relacja.TISD2)}
    if x == y:
        rows.append(["—", "rozkłady identyczne"])
    else:
        for r in names:
            rows.append([r.value, "zachodzi" if r in w.definicje else "nie zachodzi"])
        eps = []
        if almost:
            eps.append(("OAFSD" if ordinal else "AFSD", w.eps_afsd))
        if almost_second or (almost and not ordinal and risk == "DARA"):
            eps.append(("OASSD" if ordinal else "ASSD", w.eps_assd))
        for name, e in eps:
            rows.append([name, "—" if e is None else f"stopień naruszenia ε = {float(e):.4f}".replace(".", ",")])
    grid = sorted(set(x.wartosci) | set(y.wartosci))
    return _out({"rows": rows, "holds": holds, "grid": [_f(t) for t in grid],
                 "cdf_x": [_f(x.dystrybuanta(t)) for t in grid], "cdf_y": [_f(y.dystrybuanta(t)) for t in grid],
                 "mean_x": _f(x.wartosc_oczekiwana()), "mean_y": _f(y.wartosc_oczekiwana())})


# ---------------------------------------------------------------------------
# Dialogi STEM-DPR, INSDECM i ATO-DPR
# ---------------------------------------------------------------------------

# Parametry rozkładu w INSDECM: kod → (rodzaj, nazwa, czy wymaga ψ).
PARAMS = {
    1: (RP.WARTOSC_OCZEKIWANA, "Wartość oczekiwana", False),
    2: (RP.ODCHYLENIE_STD, "Odchylenie standardowe", False),
    3: (RP.SEMIODCHYLENIE_STD_DOLNE, "Dolne semiodchylenie standardowe (od wartości oczekiwanej)", False),
    4: (RP.SEMIODCHYLENIE_PRZECIETNE_DOLNE, "Dolne semiodchylenie przeciętne (od wartości oczekiwanej)", False),
    5: (RP.P_NIE_WIECEJ, "Pr{X ≤ ψ}", True),
    6: (RP.P_NIE_MNIEJ, "Pr{X ≥ ψ}", True),
    7: (RP.MEDIANA, "Mediana", False),
    8: (RP.KWARTYL_DOLNY, "Pierwszy kwartyl", False),
    9: (RP.KWARTYL_GORNY, "Trzeci kwartyl", False),
    10: (RP.KWANTYL, "Kwantyl rzędu ψ", True),
    11: (RP.DOMINANTA, "Dominanta", False),
    12: (RP.MINIMUM, "Najgorsza wartość (minimum)", False),
    13: (RP.MAKSIMUM, "Najlepsza wartość (maksimum)", False),
}
_KOD = {v[0]: k for k, v in PARAMS.items()}


def _param(code: int, psi) -> Parametr:
    rodzaj, _, needs = PARAMS[code]
    return Parametr(rodzaj, float(psi) if needs else None)


def _plabel(par: Parametr) -> str:
    if par.rodzaj is RP.P_NIE_MNIEJ:
        return f"Pr{{X ≥ {_fmt(par.prog)}}}"
    if par.rodzaj is RP.P_NIE_WIECEJ:
        return f"Pr{{X ≤ {_fmt(par.prog)}}}"
    if par.rodzaj is RP.KWANTYL:
        return f"kwantyl rzędu {_fmt(par.prog)}"
    return PARAMS[_KOD[par.rodzaj]][1]


def _orig(k: int, x):
    """Wartość z orientacji „więcej = lepiej” w jednostkach kryterium."""
    return _f(S["problem"].kryteria[k].z_orientacji(x))


def _stem_it(st) -> dict:
    p = S["problem"]
    return {"number": st.iteracja, "trial": p.warianty[st.proba],
            "rows": [[p.kryteria[k].nazwa, _orig(k, st.mu_proby[k]), _f(st.d_proby[k]), _orig(k, st.idealny[k]),
                      k in st.aktywne, "max" if p.kryteria[k].maksymalizowane else "min"] for k in range(p.n)],
            "active_variants": [p.warianty[i] for i in st.warianty]}


def _pmatrix(P) -> dict:
    if P is None:
        return None
    p = S["problem"]
    return {"cols": [[p.kryteria[k].nazwa, _plabel(par)] for k, par in P.kolumny],
            "pessimistic": [_f(v) for v in P.pesymistyczne], "optimistic": [_f(v) for v in P.optymistyczne]}


def _ato_it(it) -> dict:
    p = S["problem"]
    return {"number": it.number, "trial": p.warianty[it.trial],
            "rows": [[p.kryteria[k].nazwa, _f(it.means[k]), _f(it.ideal[k]),
                      "max" if p.kryteria[k].maksymalizowane else "min"] for k in range(p.n)],
            "active_variants": [p.warianty[i] for i in it.active_variants]}


def _ato_steps(it) -> dict:
    p = S["problem"]
    V = lambda xs: [p.warianty[i] for i in xs]
    return {"number": it.number, "order": [p.kryteria[k].nazwa for k in it.order or []],
            "candidates": V(it.candidates or []), "relaxed": it.relaxed, "arbitrary": it.arbitrary,
            "steps": [{"rule": st.rule, "criteria": [p.kryteria[k].nazwa for k in st.criteria], "before": V(st.before),
                       "removed": [[p.warianty[i], [[p.warianty[j], t] for j, t in by]] for i, by in st.removed.items()],
                       "after": V(st.after)} for st in it.steps]}


def _ins_criteria(P) -> list:
    """Kryteria i parametry do pytania o dodatkowy warunek (indeks parametru w obrębie kryterium)."""
    p = S["problem"]
    crits = []
    for k in range(p.n):
        opts = [{"p": idx, "label": _plabel(par), "pessimistic": _f(pes), "higher_better": par.wyzsze_lepsze}
                for idx, ((kk, par), pes) in enumerate((c, v) for c, v in zip(P.kolumny, P.pesymistyczne) if c[0] == k)]
        if opts:
            crits.append({"k": k, "name": p.kryteria[k].nazwa, "params": opts})
    return crits


def _question() -> dict:
    """Bieżące pytanie sesji (albo pytanie pomocnicze mostu) w postaci dla strony."""
    p = S["problem"]
    pend = S["pending"]
    if pend is not None:                                # pytania mostu rozbijające jedno pytanie procedury
        return pend["view"]
    q = S["sesja"].pytanie
    kind = S["kind"]
    if kind == "ato":
        it = q.iteracja
        if isinstance(q, ato.PytanieSatysfakcjaAto):
            out = {"kind": "satisfied", "it": _ato_it(it)}
            if it.number == 1:
                out["first_d"] = [[p.warianty[j]] + [_f(x) for x in S["method"].first_d[j]] for j in range(p.m)]
                out["criteria"] = [k.nazwa for k in p.kryteria]
            else:
                out["prev"] = _ato_steps(S["method"].history[-2])
            return out
        if isinstance(q, ato.PytanieKolejnosc):
            return {"kind": "order", "it": _ato_it(it), "criteria": [k.nazwa for k in p.kryteria]}
        return {"kind": "relax", "it": _ato_it(it), "criterion": p.kryteria[q.k].nazwa}
    if kind == "stem":
        if isinstance(q, stem.PytanieSatysfakcja):
            return {"kind": "satisfied", "it": _stem_it(q.stan)}
        if isinstance(q, stem.PytanieKryteriumSatysfakcjonujace):
            return {"kind": "some_criterion_satisfactory", "it": _stem_it(q.stan)}
        if isinstance(q, stem.PytanieProg):            # najpierw kryterium, potem próg (dwa pytania strony)
            view = {"kind": "choose_criterion", "it": _stem_it(q.stan),
                    "candidates": [[k, p.kryteria[k].nazwa] for k in range(p.n)]}
            S["pending"] = {"kind": "choose_criterion", "view": view, "stan": q.stan}
            return view
        raise TypeError(type(q))
    # INSDECM
    if isinstance(q, ins.PytanieParametry):
        biezace = q.biezace or {}
        S["pending"] = {"kind": "parameters", "k": 0, "answers": {}, "biezace": biezace}
        return _ins_params_view()
    if isinstance(q, ins.PytanieDaneWystarczajace):
        S["iter"] = q.iteracja
        log = ["Zmieniono parametry"] if S.get("changed") else []
        S["changed"] = False
        return {"kind": "parameters_sufficient",
                "it": {"number": q.iteracja, "active": [p.warianty[i] for i in q.macierz.warianty],
                       "P": _pmatrix(q.macierz), "P_next": None, "log": log}}
    if isinstance(q, ins.PytaniePesymistyczne):
        return {"kind": "pessimistic_satisfactory", "it": {"number": q.iteracja, "P": _pmatrix(q.macierz)}}
    if isinstance(q, ins.PytanieWarunek):
        return {"kind": "condition", "criteria": _ins_criteria(q.macierz)}
    if isinstance(q, ins.PytanieAkceptacjaZmian):
        return {"kind": "accept_changes", "it": {"number": S["iter"], "P_next": _pmatrix(q.po)},
                "condition": q.warunek.opis(p.kryteria[q.warunek.k].nazwa)}
    if isinstance(q, ins.PytanieNiespojnosc):
        pr = q.prezentacja
        return {"kind": "inconsistency_action",
                "inc": {"i": p.warianty[pr.i], "j": p.warianty[pr.j], "eps": _f(q.eps),
                        "criterion": p.kryteria[pr.k].nazwa,
                        "points": [_f(x) for x in pr.punkty], "pi": [_f(x) for x in pr.wartosci_i],
                        "pj": [_f(x) for x in pr.wartosci_j]}}
    if isinstance(q, ins.PytaniePropozycja):
        return {"kind": "accept_proposal", "weaken": q.oslabienie,
                "proposals": [w.opis(p.kryteria[w.k].nazwa).replace(".", ",") for w in q.propozycje]}
    if isinstance(q, ins.PytanieRozwiazanie):
        R = q.macierz
        return {"kind": "accept_solution",
                "R": {"iteration": S["iter"], "cols": [[p.kryteria[k].nazwa, _plabel(par)] for k, par in R.kolumny],
                      "rows": [[p.warianty[i]] + [_f(v) for v in row] for i, row in zip(R.warianty, R.wiersze)]},
                "variants": [[i, p.warianty[i]] for i in R.warianty]}
    raise TypeError(type(q))


def _ins_params_view() -> dict:
    p = S["problem"]
    pend = S["pending"]
    k = pend["k"]
    cur = {}
    for par in pend["biezace"].get(k, ()):
        cur[str(_KOD[par.rodzaj])] = _f(par.prog)
    view = {"kind": "parameters", "k": k, "criterion": p.kryteria[k].nazwa, "current": cur,
            "params": [[c, name, needs] for c, (_, name, needs) in PARAMS.items() if c != 1]}
    pend["view"] = view
    return view


def _result(r) -> dict:
    p = S["problem"]
    status = {"zaakceptowano": "final", "brak_rozwiazania": "impossible", "przerwano": "cancelled",
              "final": "final", "impossible": "impossible", "cancelled": "cancelled"}[r.status]
    if S["kind"] == "ato":
        sol = getattr(r, "solution", None)
        its = getattr(r, "iterations", [])
        return {"done": True, "status": status, "solution": None if sol is None else p.warianty[sol],
                "prev": _ato_steps(its[-2]) if len(its) > 1 and its[-2].order else None}
    sol = r.rozwiazanie
    if S["kind"] == "stem":
        return {"done": True, "status": status, "solution": None if sol is None else p.warianty[sol]}
    return {"done": True, "status": status, "solutions": [] if sol is None else [p.warianty[sol]]}


def _next(answer=None, *, first=False, error=None) -> str:
    s = S["sesja"]
    if not first:
        try:
            s.odpowiedz(answer)
        except BlednaOdpowiedz as e:
            error = str(e)
    if s.zakonczona:
        return _out(_result(s.wynik))
    out = _question()
    if error:
        out = dict(out, error=error)
    return _out(out)


def start(kind: str, options: str = "{}") -> str:
    p = S["problem"]
    o = json.loads(options or "{}")
    if kind == "ato":
        m = ato.AtoDPR(p, risk=o.get("risk", "DARA"), dominances=o.get("dominances"),
                       almost=bool(o.get("almost", True)), tradeoff_rules=o.get("tradeoff_rules", ["FSD"]))
        gen = m.dialog()
    elif kind == "stem":
        rel = [r.strip() for r in (o.get("relations") or ["FSD", "SSD", "TSD", "AFSD"]) if r.strip()]
        regula = RegulaDominacji.awersja(relacje=tuple(Relacja[r] for r in rel if r != "AFSD"), afsd="AFSD" in rel)
        m = StemDpr(p, regula, pytaj_o_informacje=False)
        gen = m.przebieg()
    elif kind == "insdecm":
        m = Insdecm(p, RegulaDominacji.awersja())
        gen = m.przebieg()
    else:
        raise ValueError(kind)
    S.update(method=m, kind=kind, pending=None, iter=0, changed=False)
    S["sesja"] = Sesja(gen)
    return _next(first=True)


def answer(payload: str) -> str:
    """payload: JSON {"kind": ..., "value": ...}; wartość przekształcana do typu oczekiwanego przez procedurę.
    null przy pytaniach tak/nie, warunku, porządku kryteriów i wyborze kryterium oznacza „Anuluj”."""
    a = json.loads(payload)
    kind, v = a["kind"], a.get("value")
    pend = S["pending"]
    p = S["problem"]
    if pend is not None and kind == "choose_criterion":
        if v is None:
            S["pending"] = None
            return _next(PRZERWIJ)
        k = int(v)
        st = pend["stan"]
        view = {"kind": "threshold", "it": _stem_it(st), "k": k, "criterion": p.kryteria[k].nazwa,
                "maximize": p.kryteria[k].maksymalizowane, "default": _orig(k, st.idealny[k])}
        S["pending"] = {"kind": "threshold", "view": view, "k": k, "stan": st}
        return _out(view)
    if pend is not None and kind == "threshold":
        k = pend["k"]
        S["pending"] = None
        out = json.loads(_next(Prog(k, p.kryteria[k].zorientuj(float(v)))))
        if out.get("error") and not out.get("done"):        # zły próg: wróć do pytania o próg tego kryterium
            S["pending"] = pend
            out = dict(pend["view"], error=out["error"])
        return _out(out)
    if pend is not None and kind == "parameters":
        lst = [Parametr(RP.WARTOSC_OCZEKIWANA)] + [_param(int(c), psi) for c, psi in sorted((v or {}).items(), key=lambda t: int(t[0]))]
        pend["answers"][pend["k"]] = lst
        if pend["k"] + 1 < p.n:
            pend["k"] += 1
            return _out(_ins_params_view())
        S["pending"] = None
        S["changed"] = bool(pend["biezace"])
        return _next(pend["answers"])
    if kind in ("satisfied", "some_criterion_satisfactory", "parameters_sufficient", "pessimistic_satisfactory",
                "accept_changes", "relax"):
        return _next(PRZERWIJ if v is None else bool(v))
    if kind == "order":
        return _next(PRZERWIJ if v is None else [int(x) for x in v])
    if kind == "condition":
        if v is None:
            return _next(PRZERWIJ)
        k, idx, granica = int(v[0]), int(v[1]), float(v[2])
        q = S["sesja"].pytanie
        par = [par for kk, par in q.macierz.kolumny if kk == k][idx]
        return _next(Warunek(k, par, granica))
    if kind == "inconsistency_action":
        return _next({0: PODTRZYMAJ, 1: OSLAB, 2: ZAOSTRZ}[int(v)])
    if kind in ("accept_proposal", "accept_solution"):
        return _next(None if v is None else int(v))
    raise ValueError(f"Nieoczekiwana odpowiedź {kind!r}")


# ---------------------------------------------------------------------------
# Metody z rozdz. 2 i 7 (pakiet mcdm_book)
# ---------------------------------------------------------------------------

def book_methods() -> str:
    from mcdm_book import api as book_api
    return _out(book_api.methods())


def book_examples() -> str:
    from mcdm_book import examples as book_ex
    return _out(book_ex.listing())


def book_example(name: str) -> str:
    from mcdm_book import examples as book_ex
    return _out(book_ex.get(name))


def book_method_help(name: str) -> str:
    from mcdm_book import method_help
    return _out(method_help.get(name))


def book_print_check(name: str) -> str:
    from mcdm_book import print_checks
    return _out(print_checks.get(name))


def book_run(payload: str) -> str:
    from mcdm_book import api as book_api
    try:
        return _out(book_api.run_safe(json.loads(payload)))
    except Exception as e:  # noqa: BLE001 — błąd programu zwracamy stronie
        return _out({"error": f"{type(e).__name__}: {e}"})


def book_matrix_check(payload: str) -> str:
    """Bieżąca kontrola jednej macierzy porównań (edytor AHP / REMBRANDT)."""
    from mcdm_book import ahp as book_ahp
    from mcdm_book.problem import ProblemError
    a = json.loads(payload)
    notes: list = []
    try:
        M, kind = a["matrix"], a["kind"]
        n = len(M)
        if kind == "rembrandt":
            D = book_ahp.delta_matrix(M, n, "Macierz", notes)
            g = float(a.get("gamma", 0.6931471805599453))
            r = book_ahp._rembrandt_vector(D, g)
            return _out({"w": r["w"], "notes": notes})
        A = book_ahp.reciprocal_matrix(M, n, "Macierz", notes)
        pr = book_ahp.priority_vector(A, a.get("method", "eigen"))
        cons = book_ahp.consistency(pr["lambda_max"], n)
        return _out({"w": pr["w"], "lambda_max": pr["lambda_max"], "gamma": cons["gamma"],
                     "consistent": cons["consistent"], "notes": notes})
    except (ProblemError, ValueError, ZeroDivisionError) as e:
        return _out({"error": str(e)})
