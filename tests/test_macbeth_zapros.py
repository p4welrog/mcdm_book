import pytest

from mcdm_book import api, examples
from mcdm_book.macbeth import parse_judgement, scale
from mcdm_book.problem import ProblemError

N = None


def run(name, **opts):
    e = examples.get(name)
    return api.run({"method": e["method"], "problem": e["problem"], "options": {**e["options"], **opts}})


def r2(xs):
    return [round(x, 2) for x in xs]


def test_p4_3_macbeth():
    r = run("P4.3")
    st = r["steps"]
    assert r2(st["scales"]["Jakość wyświetlania"]["scale"]) == [150, 100, 50, 0, -66.67]           # rys. 13
    assert r2(st["scales"]["Ciężar"]["scale"]) == [122.22, 100, 66.67, 0, -66.67]                    # rys. 14
    assert [round(w, 4) for w in st["weights"]] == [0.3095, 0.2381, 0.4048, 0.0476]                # rys. 15 (17:10:13:2... /42)
    assert r2(r["scores"]["values"]) == [248.65, 85.05, 54.76, 45.24, -107.94]                    # rys. 16 (248,64)
    assert r2([row[3] for row in st["partial_scores"]]) == [46.67, 111.11, 0, 100, -66.67]
    assert r["ranking"][0] == "Samsung Galaxy S3"


def test_p4_2_weights_and_reference_note():
    r = run("P4.2")
    assert r2(r["scores"]["values"]) == [100, 42.86, 28.57, 0]
    assert r["steps"]["basic"] == pytest.approx([7, 3, 2, 0])


def test_macbeth_inconsistency_suggestion():
    M = [[0, "strong", "weak", "strong"], [N, 0, "strong", "strong"], [N, N, 0, "strong"], [N, N, N, 0]]
    with pytest.raises(ProblemError, match="Biały–Czarny: weak → strong"):
        scale(["Biały", "Srebrny", "Czarny", "Niebieski"], M, "Kolor")             # rys. 11–12


def test_macbeth_ordinal_cycle():
    with pytest.raises(ProblemError, match="brak rankingu"):
        scale(["x", "y", "z"], [[0, 0, 2], [N, 0, 0], [N, N, 0]], "m")            # przypis 32: xIy, yIz, xPz


def test_parse_judgement():
    assert parse_judgement("positive", "") == (1, 6)
    assert parse_judgement("d2-d4", "") == (2, 4)
    assert parse_judgement("bardzo duża", "") == (5, 5)
    assert parse_judgement(None, "") is None


def test_p4_5_zapros_two_candidates():
    r = run("P4.5")
    assert r["steps"]["jos_sorted"] == [[1, 1, 1, 1, 3, 4], [1, 1, 1, 1, 2, 3]]
    assert r["best"] == ["Wojciech"]


def test_p4_6_zapros():
    r = run("P4.6")
    st = r["steps"]
    assert st["jos"] == {"A1": 1, "B1": 1, "C1": 1, "C2": 2, "A2": 3, "B2": 4, "B3": 5, "A3": 6, "C3": 6}  # tabl. 6
    assert st["jos_sorted"] == [[1, 2, 4], [1, 3, 4], [1, 2, 6], [1, 1, 5], [1, 3, 6], [2, 4, 6]]       # tabl. 7
    assert r["best"] == ["a1", "a4"]
    assert {tuple(e) for e in st["edges"]} == {("a1", "a2"), ("a1", "a3"), ("a4", "a3"), ("a2", "a5"),
                                                ("a3", "a5"), ("a5", "a6")}                           # rys. 1
    assert st["relations"][1][2] == "R" and st["relations"][0][3] == "R"                              # tabl. 8


def test_p4_7_zapros_iii_pairs():
    r = run("P4.7")
    assert r["steps"]["jscv"] == ["C1>C2", "A1>A2", "B1>B2", "A1>A3", "B1>B3", "C1>C3", "A2>A3", "B2>B3", "C2>C3"]
    rel = r["steps"]["direct_relations"]
    assert rel[1][0] == "P" and rel[2][3] == "P"                       # Kazimierz ≻ Zofia, Karolina ≻ Marek


def test_p4_8_zapros_iii():
    r = run("P4.8")
    st = r["steps"]
    assert st["jscv"] == ["C1>C2", "A1>A2", "B1>B2", "A2>A3", "B2>B3", "C2>C3", "A1>A3", "B1>B3", "C1>C3"]  # tabl. 6
    assert st["FIQ"] == [4, 5, 8, 8, 11, 11, 10, 15, 3]                                                 # tabl. 7
    assert r["ranks"] == [2, 3, 4, 4, 5, 6, 5, 7, 1]                                                    # tabl. 8
    assert r["best"] == ["K9"]
    assert {tuple(e) for e in st["edges"]} == {("K9", "K1"), ("K1", "K2"), ("K2", "K3"), ("K2", "K4"), ("K3", "K5"),
                                                ("K3", "K7"), ("K4", "K5"), ("K4", "K7"), ("K7", "K6"), ("K6", "K8")}


def test_zapros_iii_jscv_direct_equals_merge():
    e = examples.get("P4.8")
    jscv = run("P4.8")["steps"]["jscv"]
    prob = {k: v for k, v in e["problem"].items() if k != "qv_comparisons"}
    r = api.run({"method": "zapros_iii", "problem": {**prob, "jscv": jscv}, "options": {}})
    assert r["ranks"] == [2, 3, 4, 4, 5, 6, 5, 7, 1]


def test_zapros_bad_grade():
    e = examples.get("P4.6")
    prob = {**e["problem"], "values": [["A9", "B1", "C1"]] + e["problem"]["values"][1:]}
    with pytest.raises(ProblemError, match="spoza skali"):
        api.run({"method": "zapros", "problem": prob, "options": {}})
