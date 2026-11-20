"""Most między stroną (JavaScript) a pakietem mcdm_cd w Pyodide. Wejście i wyjście: JSON."""
from __future__ import annotations

import json
import math
from pathlib import Path

from mcdm_cd.distribution import PARAMS, Distribution, better
from mcdm_cd.dominance import DARA, IDENTICAL, INARA, stdom_report, stochastic_dominance
from mcdm_cd.ato_dpr import AtoDPR
from mcdm_cd.insdecm import Insdecm
from mcdm_cd.mcf import Problem, example as mcf_example, read_mcf
from mcdm_cd.stem_dpr import StemDPR

DATA = Path(__file__).parent / "mcdm_cd" / "data"
EXAMPLES = {
    "przyklad_8_1": "przyklad_8_1.mcf — przykłady 8.1–8.4 (4 kryteria, 10 wariantów)",
    "Przyklad_1": "Przyklad_1.mcf — przykład STEM-DPR z instrukcji MCDM (3 kryteria, 20 wariantów)",
    "przyklad_8_5": "przykład 8.5 (ATO-DPR) — jak 8.1, z zamienionymi rozkładami f1 wariantów a6 i a8",
}

S = {"problem": None, "method": None, "gen": None, "kind": None}


def _f(x):
    """Liczba do JSON (NaN → None)."""
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def _out(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def param_label(p: int, psi) -> str:
    return _param_label(p, psi).replace(".", ",")


def _param_label(p: int, psi) -> str:
    if p == 7:
        return f"Pr{{X ≤ {psi:g}}}"
    if p == 8:
        return f"Pr{{X ≥ {psi:g}}}"
    if p in (3, 4, 5, 6):
        return f"{PARAMS[p][0]} ({psi:g})"
    return PARAMS[p][0]


# ---------------------------------------------------------------------------
# Dane
# ---------------------------------------------------------------------------

def _summary(p: Problem) -> dict:
    return {"comment": p.comment, "source": p.source, "criteria": p.criteria, "maximize": p.maximize,
            "variants": p.variants, "warnings": p.warnings, "n": p.n, "m": p.m}


def examples() -> str:
    return _out([{"id": k, "label": v} for k, v in EXAMPLES.items()])


def load_example(name: str) -> str:
    if name not in EXAMPLES:
        raise ValueError(f"Nieznany przykład {name}")
    p = mcf_example(name)
    p.source = f"{name}.mcf" if name != "przyklad_8_5" else "przykład 8.5"
    S["problem"] = p
    return _out(_summary(p))


def load_bytes(data, filename: str) -> str:
    p = read_mcf(bytes(data))
    p.source = filename
    S["problem"] = p
    return _out(_summary(p))


def distributions(k: int) -> str:
    p = S["problem"]
    vals = sorted({v for i in range(p.n) for v in p.dist[i][k].values})
    rows = []
    for v in vals:
        rows.append([v] + [dict(zip(p.dist[i][k].values, p.dist[i][k].probs)).get(v, 0.0) for i in range(p.n)])
    return _out({"criterion": p.criteria[k], "variants": p.variants, "rows": rows,
                 "means": [p.dist[i][k].mean() for i in range(p.n)]})


def variant_dist(i: int, k: int) -> str:
    d = S["problem"].dist[i][k]
    return _out({"values": list(d.values), "probs": list(d.probs)})


def dominance_matrix(k: int, orient_min: bool = True) -> str:
    """Arkusz „Wykryte dominacje” dla kryterium k: wiersz dominuje kolumnę."""
    s = StemDPR(S["problem"], orient_min=orient_min)
    lab = {7.0: "FSD", 6.0: "SSD", 4.0: "TSD", float(IDENTICAL): ""}
    rows = [[lab.get(x, f"AFSD({x:.2f})".replace(".", ",") if x else "") for x in s.dom[k][i]] for i in range(s.p.n)]
    return _out({"criterion": s.p.criteria[k], "variants": s.p.variants, "rows": rows})


# ---------------------------------------------------------------------------
# StDom — dwa rozkłady
# ---------------------------------------------------------------------------

def stdom(xv, xp, yv, yp, ordinal: bool, risk: str, almost: bool, almost_second: bool, quirk: bool) -> str:
    x = Distribution.from_pairs(list(xv), list(xp))
    y = Distribution.from_pairs(list(yv), list(yp))
    lines = stdom_report(x, y, risk, almost=almost, almost_second=almost_second and ordinal,
                         ordinal=ordinal, vba_param_quirk=quirk)
    r = stochastic_dominance(x, y, DARA if ordinal else risk)
    rows = []
    for name, v in lines:
        if name == "IDENTICAL":
            rows.append(["—", "rozkłady identyczne"])
        elif isinstance(v, bool):
            rows.append([name, "zachodzi" if v else "nie zachodzi"])
        else:
            rows.append([name, f"zachodzi ze stopniem ε = {v:.4f}".replace(".", ",")])
    g = r.grid
    return _out({"rows": rows, "holds": r.holds, "grid": g, "cdf_x": [x.cdf(t) for t in g],
                 "cdf_y": [y.cdf(t) for t in g], "mean_x": x.mean(), "mean_y": y.mean()})


# ---------------------------------------------------------------------------
# Dialogi STEM-DPR i INSDECM
# ---------------------------------------------------------------------------

def _stem_it(s: StemDPR, it) -> dict:
    p = s.p
    return {"number": it.number, "trial": p.variants[it.trial],
            "rows": [[p.criteria[k], _f(it.means[k]), _f(it.d[k]), _f(it.ideal[k]),
                      it.active_criteria[k], "max" if p.maximize[k] else "min"] for k in range(p.m)],
            "active_variants": [p.variants[i] for i in it.active_variants]}


def _pmatrix(s: Insdecm, P) -> dict:
    if P is None:
        return None
    return {"cols": [[s.p.criteria[k], param_label(p, psi)] for k, p, psi in P.columns],
            "pessimistic": [_f(v) for v in P.pessimistic], "optimistic": [_f(v) for v in P.optimistic]}


def _ins_it(s: Insdecm, it) -> dict:
    return {"number": it.number, "active": [s.p.variants[i] for i in it.active],
            "P": _pmatrix(s, it.P), "P_next": _pmatrix(s, it.P_next), "log": list(it.log)}


def _question(q) -> dict:
    s = S["method"]
    p = s.p
    a = q.args
    out = {"kind": q.kind}
    if S["kind"] == "ato":
        it = a[0]
        out["it"] = _ato_it(s, it)
        if q.kind == "satisfied" and it.number == 1:
            out["first_d"] = [[p.variants[j]] + [_f(x) for x in s.first_d[j]] for j in range(p.n)]
            out["criteria"] = p.criteria
        if q.kind == "satisfied" and it.number > 1:
            out["prev"] = _ato_steps(s, s.history[-2])
        if q.kind == "order":
            out["criteria"] = p.criteria
        if q.kind == "relax":
            out["criterion"] = p.criteria[a[1]]
        return out
    if S["kind"] == "stem":
        it = a[0]
        out["it"] = _stem_it(s, it)
        if q.kind == "choose_criterion":
            out["candidates"] = [[k, p.criteria[k]] for k in a[1]]
        elif q.kind == "threshold":
            k = a[1]
            out.update(k=k, criterion=p.criteria[k], maximize=p.maximize[k], default=_f(a[2]))
        return out
    # INSDECM
    if q.kind == "parameters":
        k, cur = a
        out.update(k=k, criterion=p.criteria[k], current={str(pp): psi for pp, psi in cur.items()},
                   params=[[pp, PARAMS[pp][1], PARAMS[pp][2]] for pp in range(2, 12)])
        return out
    if q.kind == "accept_solution":
        R = a[0]
        cols = None
        rows = []
        for i, row in R.items():
            keys = sorted(row)
            cols = cols or keys
            rows.append([p.variants[i]] + [_f(row[c]) for c in keys])
        out["R"] = {"iteration": s.iteration,
                    "cols": [[p.criteria[k], param_label(pp, s.params[k].get(pp))] for k, pp in (cols or [])],
                    "rows": rows}
        return out
    it = a[0]
    out["it"] = _ins_it(s, it)
    if q.kind == "condition":
        pes = {(k, pp): v for (k, pp, _), v in zip(it.P.columns, it.P.pessimistic)}
        crits = []
        for k in range(p.m):
            opts = []
            for pp, psi in sorted(s.params[k].items()):
                opts.append({"p": pp, "label": param_label(pp, psi), "pessimistic": _f(pes.get((k, pp))),
                             "higher_better": better(pp, p.maximize[k]) > 0})
            crits.append({"k": k, "name": p.criteria[k], "params": opts})
        out["criteria"] = crits
    elif q.kind == "inconsistency_action":
        inc = a[1]
        out["inc"] = {"i": p.variants[inc.i], "j": p.variants[inc.j], "eps": _f(inc.eps)}
    elif q.kind == "accept_proposal":
        prop = a[1]
        c = it.condition
        out["proposal"] = {"criterion": p.criteria[c.k], "param": param_label(c.p, prop["psi"]),
                           "action": prop["action"], "value": _f(prop["value"]),
                           "value_other": _f(prop.get("value_other"))}
    return out


def _ato_it(s: AtoDPR, it) -> dict:
    p = s.p
    return {"number": it.number, "trial": p.variants[it.trial],
            "rows": [[p.criteria[k], _f(it.means[k]), _f(it.ideal[k]), "max" if p.maximize[k] else "min"]
                     for k in range(p.m)],
            "active_variants": [p.variants[i] for i in it.active_variants]}


def _ato_steps(s: AtoDPR, it) -> dict:
    p = s.p
    V = lambda xs: [p.variants[i] for i in xs]
    return {"number": it.number, "order": [p.criteria[k] for k in it.order or []],
            "candidates": V(it.candidates or []), "relaxed": it.relaxed, "arbitrary": it.arbitrary,
            "steps": [{"rule": st.rule, "criteria": [p.criteria[k] for k in st.criteria], "before": V(st.before),
                       "removed": [[p.variants[i], [[p.variants[j], t] for j, t in by]] for i, by in st.removed.items()],
                       "after": V(st.after)} for st in it.steps]}


def _result(r) -> dict:
    s = S["method"]
    p = s.p
    if S["kind"] == "ato":
        return {"done": True, "status": r.status, "solution": None if r.solution is None else p.variants[r.solution],
                "prev": _ato_steps(s, r.iterations[-2]) if len(r.iterations) > 1 and r.iterations[-2].order else None}
    if S["kind"] == "stem":
        return {"done": True, "status": r.status,
                "solution": None if r.solution is None else p.variants[r.solution]}
    return {"done": True, "status": r.status, "solutions": [p.variants[i] for i in r.solutions]}


def _step(answer, first=False) -> str:
    try:
        q = next(S["gen"]) if first else S["gen"].send(answer)
    except StopIteration as e:
        S["gen"] = None
        return _out(_result(e.value))
    return _out(_question(q))


def start(kind: str, orient_min: bool = True, vba_compat: bool = False, options: str = "{}") -> str:
    p = S["problem"]
    if kind == "ato":
        o = json.loads(options or "{}")
        S["method"] = AtoDPR(p, risk=o.get("risk", DARA), dominances=o.get("dominances"),
                             almost=bool(o.get("almost", True)), tradeoff_rules=o.get("tradeoff_rules", ["FSD"]))
    elif kind == "stem":
        S["method"] = StemDPR(p, orient_min=orient_min)
    elif kind == "insdecm":
        S["method"] = Insdecm(p, orient_min=orient_min, vba_compat=vba_compat)
    else:
        raise ValueError(kind)
    S["kind"] = kind
    S["gen"] = S["method"].dialog()
    return _step(None, first=True)


def answer(payload: str) -> str:
    """payload: JSON {"kind": ..., "value": ...}; wartość przekształcana do typu oczekiwanego przez metodę."""
    a = json.loads(payload)
    kind, v = a["kind"], a.get("value")
    if kind == "parameters":
        v = {int(pp): (None if psi is None else float(psi)) for pp, psi in (v or {}).items()}
    elif kind == "condition" and v is not None:
        v = (int(v[0]), int(v[1]), float(v[2]))
    elif kind == "order" and v is not None:
        v = [int(k) for k in v]
    elif kind in ("choose_criterion",) and v is not None:
        v = int(v)
    elif kind == "threshold":
        v = float(v)
    elif kind == "inconsistency_action":
        v = int(v)
    return _step(v)


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
