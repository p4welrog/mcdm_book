"""Most strony (web/web.py) z mcdm_ryzyko i ATO-DPR: przebiegi dialogów z przykładów 8.2, 8.4, 8.5 i formatka StDom."""
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("xlrd")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
import web  # noqa: E402


def ans(kind, value):
    return json.loads(web.answer(json.dumps({"kind": kind, "value": value})))


def test_stem_example_8_2():
    """Przykład 8.2: Nie, Tak, X3, próg 6 → a3."""
    web.load_example("przyklad_8_1")
    q = json.loads(web.start("stem", json.dumps({"relations": ["FSD", "SSD", "TSD", "AFSD"]})))
    assert q["kind"] == "satisfied" and q["it"]["number"] == 1
    q = ans("satisfied", False)
    assert q["kind"] == "some_criterion_satisfactory"
    q = ans("some_criterion_satisfactory", True)
    assert q["kind"] == "choose_criterion" and len(q["candidates"]) == 4
    q = ans("choose_criterion", 2)
    assert q["kind"] == "threshold" and q["criterion"] == "X3"
    q = ans("threshold", 100)                                   # żaden wariant nie spełnia — pytanie zostaje
    assert q["kind"] == "threshold" and q["error"]
    q = ans("threshold", 6)
    assert q["kind"] == "satisfied" and q["it"]["number"] == 2
    r = ans("satisfied", True)
    assert r["done"] and r["status"] == "final" and r["solution"] == "a3"


def test_stem_cancel():
    web.load_example("przyklad_8_1")
    web.start("stem", "{}")
    r = ans("satisfied", None)
    assert r["done"] and r["status"] == "cancelled"


def _params(q, chosen):
    """Odpowiedzi na pytania o parametry dla kolejnych kryteriów; chosen: {nazwa kryterium: {kod: ψ}}."""
    while q["kind"] == "parameters":
        q = ans("parameters", chosen.get(q["criterion"], {}))
    return q


def test_insdecm_example_8_4():
    """Przykład 8.4: Pr{X1 ≥ 6} ≥ 0,5, potem Pr{X2 ≥ 5} ≥ 0,65 → macierz rozwiązań a4, a5, a9."""
    web.load_example("przyklad_8_1")
    q = json.loads(web.start("insdecm", "{}"))
    assert q["kind"] == "parameters" and q["criterion"] == "X1"
    q = _params(q, {"X1": {"6": 6}})
    assert q["kind"] == "parameters_sufficient"
    q = ans("parameters_sufficient", True)
    assert q["kind"] == "pessimistic_satisfactory"
    q = ans("pessimistic_satisfactory", False)
    assert q["kind"] == "condition"
    x1 = next(c for c in q["criteria"] if c["name"] == "X1")
    idx = next(p["p"] for p in x1["params"] if p["label"].startswith("Pr{X ≥"))
    q = ans("condition", [x1["k"], idx, 0.5])
    assert q["kind"] == "accept_changes"
    q = ans("accept_changes", True)
    while q["kind"] == "inconsistency_action":
        q = ans("inconsistency_action", 0)
    assert q["kind"] == "parameters_sufficient" and q["it"]["number"] == 2
    q = ans("parameters_sufficient", False)
    q = _params(q, {"X1": {"6": 6}, "X2": {"6": 5}})
    q = ans("parameters_sufficient", True)
    q = ans("pessimistic_satisfactory", False)
    x2 = next(c for c in q["criteria"] if c["name"] == "X2")
    idx = next(p["p"] for p in x2["params"] if p["label"].startswith("Pr{X ≥"))
    q = ans("condition", [x2["k"], idx, 0.65])
    q = ans("accept_changes", True)
    while q["kind"] == "inconsistency_action":
        q = ans("inconsistency_action", 0)
    q = ans("parameters_sufficient", True)
    q = ans("pessimistic_satisfactory", True)
    assert q["kind"] == "accept_solution"
    assert [v for _, v in q["variants"]] == ["a4", "a5", "a9"]
    r = ans("accept_solution", q["variants"][0][0])
    assert r["done"] and r["status"] == "final" and r["solutions"] == ["a4"]


def test_ato_example_8_5():
    web.load_example("przyklad_8_5")
    o = {"risk": "DARA", "dominances": ["FSD", "SSD"], "almost": False, "tradeoff_rules": ["FSD", "SSD"]}
    q = json.loads(web.start("ato", json.dumps(o)))
    assert q["kind"] == "satisfied" and q["it"]["trial"] == "a6" and q["first_d"]
    order = lambda names: [q["criteria"].index(n) for n in names]
    q = ans("satisfied", False)
    q = ans("order", order(["X3", "X4", "X1", "X2"]))
    assert q["kind"] == "satisfied" and q["it"]["trial"] == "a1" and q["prev"]["candidates"]
    q = ans("satisfied", False)
    q = ans("order", order(["X2", "X3", "X4", "X1"]))
    r = ans("satisfied", True)
    assert r["done"] and r["solution"] == "a4"


def test_stdom_example_1_10():
    r = json.loads(web.stdom([1, 2, 3, 4, 5], [0.2, 0, 0.4, 0.2, 0.2], [1, 2, 3, 4, 5], [0, 0.4, 0.4, 0.2, 0],
                             False, "DARA", True, False))
    rows = dict(r["rows"])
    assert rows["FSD"] == "nie zachodzi"
    assert rows["AFSD"].endswith("0,2500")                       # przykład 1.10: ε₁ = 0,25
    assert r["mean_x"] == pytest.approx(3.2) and r["mean_y"] == pytest.approx(2.8)


def test_dominance_matrix_and_distributions():
    web.load_example("przyklad_8_1")
    d = json.loads(web.dominance_matrix(0))
    assert len(d["rows"]) == 10 and all(len(r) == 10 for r in d["rows"])
    t = json.loads(web.distributions(0))
    assert len(t["means"]) == 10
