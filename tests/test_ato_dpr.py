import pytest

pytest.importorskip("xlrd")

from mcdm_cd import AtoDPR, ScriptedAtoDM, example, tradeoff

BOOK = dict(dominances=("FSD", "SSD"), almost=False, tradeoff_rules=("FSD", "SSD"))


def V(p, xs):
    return [p.variants[i] for i in xs]


@pytest.fixture
def p85():
    return example("przyklad_8_5")


def test_first_trial_table_13(p85):
    a = AtoDPR(p85, **BOOK)
    s, D = a.first_trial()
    assert p85.variants[s] == "a6"
    assert [max(r) for r in D] == [7, 9, 7, 9, 7, 5, 6, 9, 7, 7]                         # tabl. 13
    assert [r[0] for r in D] == [7, 0, 3, 0, 2, 5, 5, 9, 2, 6]                           # tabl. 9


def test_example_8_5_dialog(p85):
    a = AtoDPR(p85, **BOOK)
    r = a.run(ScriptedAtoDM([["X3", "X4", "X1", "X2"], ["X2", "X3", "X4", "X1"]]))
    assert r.status == "final" and p85.variants[r.solution] == "a4"
    it1, it2, it3 = r.iterations
    assert V(p85, it1.candidates) == ["a1", "a4", "a5", "a7", "a9", "a10"]
    st = it1.steps[0]                                                                    # tabl. 17
    assert {p85.variants[i]: sorted((p85.variants[j], t) for j, t in by) for i, by in st.removed.items()} == {
        "a4": [("a1", "SSD"), ("a7", "FSD")], "a5": [("a1", "FSD"), ("a4", "SSD"), ("a7", "FSD")],
        "a9": [("a1", "FSD"), ("a10", "SSD"), ("a4", "FSD"), ("a5", "SSD"), ("a7", "FSD")],
        "a10": [("a1", "FSD"), ("a4", "FSD"), ("a7", "FSD")]}
    assert V(p85, st.after) == ["a1", "a7"]
    assert [s.removed for s in it1.steps[1:3]] == [{}, {}]                               # tabl. 18–19
    assert it1.steps[3].rule == "rating" and V(p85, it1.steps[3].after) == ["a1"]
    assert p85.variants[it2.trial] == "a1"
    assert V(p85, it2.candidates) == ["a4", "a5", "a7", "a9", "a10"]
    assert V(p85, it2.steps[0].after) == ["a4"]                                           # tabl. 21
    assert [round(x, 2) for x in it3.ideal] == [8.14, 7.86, 8.14, 8.0]                    # tabl. 22


def test_formula_8_19_fsd_only_same_result(p85):
    a = AtoDPR(p85, dominances=("FSD", "SSD"), almost=False)
    r = a.run(ScriptedAtoDM([["X3", "X4", "X1", "X2"], ["X2", "X3", "X4", "X1"]]))
    assert p85.variants[r.solution] == "a4"


def test_tradeoff_distribution(p85):
    a = AtoDPR(p85, **BOOK)
    T = tradeoff(a, 5, 0, 1, 2)                                                           # T_{16}^{23} (tabl. 16)
    assert abs(sum(T.probs) - 1) < 1e-12
    d = dict(zip(T.values, T.probs))
    assert d[-10000.0] == pytest.approx(1 / 7 * 3 / 7)                                    # f2(a1) = 6 < f2(a6) ∈ {7, 8}
    assert d[0.0] == pytest.approx(2 / 7 * 2 / 7)                                         # f2(a1) = f2(a6) = 8
    assert d[5.0] == pytest.approx(56 / 7 ** 4)                                           # np. (8 − 3)/(4 − 3)
    assert d[3.0] > 0 and 10000.0 in d


def test_relax_when_no_candidates(p85):
    a = AtoDPR(p85, **BOOK)
    # a1 ma na X2 rozkład dominujący wszystkie pozostałe — poprawa X2 względem a1 jest niemożliwa
    r = a.run(ScriptedAtoDM([["X3", "X4", "X1", "X2"], ["X1", "X3", "X4", "X2"]], relax=True))
    assert r.status == "impossible" and p85.variants[r.iterations[-1].trial] == "a1"
