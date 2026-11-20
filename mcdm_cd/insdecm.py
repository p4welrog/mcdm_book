"""Metoda INSDECM (odpowiednik M_INSDECM.bas i M_Util_Insdecm.bas z MCDM 1.00).

Dialog z decydentem przez obiekt z metodami (protokół `InsdecmDecisionMaker`); scenariusze
testowe — `ScriptedInsdecmDM`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

from .distribution import LOCATION, PARAMS, better, parameter
from .dominance import DARA, afsd_mcdm, stochastic_dominance
from .mcf import Problem
from .dialog import Ask, drive

KEEP, WEAKEN, TIGHTEN = 0, 1, 2   # reakcja na niespójność (formatka „Wybór akcji”)


@dataclass
class PMatrix:
    """Macierz możliwości: dla każdego (kryterium, parametr) para (pesymistyczna, optymistyczna)."""
    columns: List[Tuple[int, int, Optional[float]]]      # (k, p, psi)
    pessimistic: List[float]
    optimistic: List[float]

    def as_dict(self):
        return {(k, p): (pe, op) for (k, p, _), pe, op in zip(self.columns, self.pessimistic, self.optimistic)}


@dataclass
class Condition:
    k: int
    p: int
    value: float
    psi: Optional[float] = None


@dataclass
class Inconsistency:
    i: int        # wariant odrzucony, który dominuje (FSD/SSD/TSD) …
    j: int        # … wariant pozostawiony
    eps: float    # stopień AFSD (wariant MCDM)


@dataclass
class InsdecmIteration:
    number: int
    active: List[int]
    P: PMatrix
    condition: Optional[Condition] = None
    P_next: Optional[PMatrix] = None
    inconsistencies: List[Inconsistency] = field(default_factory=list)
    log: List[str] = field(default_factory=list)


class InsdecmDecisionMaker(Protocol):
    def parameters(self, s: "Insdecm", k: int, current: Dict[int, Optional[float]]) -> Dict[int, Optional[float]]:
        """Parametry prezentowane dla kryterium k: {nr parametru: psi lub None}; 1 jest zawsze."""

    def parameters_sufficient(self, s: "Insdecm", it: InsdecmIteration) -> Optional[bool]: ...

    def pessimistic_satisfactory(self, s: "Insdecm", it: InsdecmIteration) -> Optional[bool]: ...

    def condition(self, s: "Insdecm", it: InsdecmIteration) -> Optional[Tuple[int, int, float]]:
        """(kryterium, parametr, wartość progowa) albo None = Anuluj."""

    def accept_changes(self, s: "Insdecm", it: InsdecmIteration) -> Optional[bool]: ...

    def inconsistency_action(self, s: "Insdecm", it: InsdecmIteration, inc: Inconsistency) -> int:
        """KEEP / WEAKEN / TIGHTEN."""

    def accept_proposal(self, s: "Insdecm", it: InsdecmIteration, proposal: dict) -> Optional[str]:
        """Akceptacja propozycji zmiany progu: None = odrzucenie; dla parametrów 7/8 'value' albo
        'value_other' (dwie opcje formatki), dla pozostałych 'value'."""

    def accept_solution(self, s: "Insdecm", R: Dict[int, Dict[Tuple[int, int], float]]) -> bool: ...


@dataclass
class InsdecmResult:
    status: str                       # "final" | "cancelled"
    solutions: List[int]
    iterations: List[InsdecmIteration] = field(default_factory=list)
    R: Dict[int, Dict[Tuple[int, int], float]] = field(default_factory=dict)


class Insdecm:
    def __init__(self, problem: Problem, *, vba_compat: bool = False, orient_min: bool = True):
        """vba_compat: parametry jak w MCDM 1.00 (zob. distribution.parameter);
        orient_min=False — dominacje na surowych wartościach także dla kryteriów minimalizowanych."""
        self.p = problem
        self.vba = vba_compat
        self.orient_min = orient_min
        n, m = problem.n, problem.m
        self.params: List[Dict[int, Optional[float]]] = [{1: None} for _ in range(m)]
        self.active = [True] * n      # War_aktywny
        self.active1 = [True] * n     # War_aktywny_1 (zbiór w kolejnej iteracji)
        self.iteration = 0

    # --- obliczenia ---
    def _dist(self, i, k):
        return self.p.oriented(i, k) if self.orient_min else self.p.dist[i][k]

    def value(self, i: int, k: int, p: int, psi: Optional[float] = None) -> float:
        if psi is None:
            psi = self.params[k].get(p)
        return parameter(self.p.dist[i][k], p, psi, vba_compat=self.vba)

    def p_matrix(self, which: Sequence[bool]) -> PMatrix:
        cols, pes, opt = [], [], []
        idx = [i for i in range(self.p.n) if which[i]]
        for k in range(self.p.m):
            for p in sorted(self.params[k]):
                psi = self.params[k][p]
                vals = [self.value(i, k, p) for i in idx]
                b = better(p, self.p.maximize[k])
                cols.append((k, p, psi))
                if vals:
                    opt.append(max(vals) if b > 0 else min(vals))
                    pes.append(min(vals) if b > 0 else max(vals))
                else:
                    opt.append(float("nan"))
                    pes.append(float("nan"))
        return PMatrix(cols, pes, opt)

    def _ok(self, i: int, c: Condition, *, strict: bool) -> bool:
        """Czy wariant i spełnia warunek c (w kierunku „lepiej”)."""
        v = self.value(i, c.k, c.p)
        b = better(c.p, self.p.maximize[c.k])
        if not strict:
            return v >= c.value if b > 0 else v <= c.value
        # Dostosowanie_wariantow: nierówności ostre poza parametrami 7/8
        if c.p in (7, 8):
            return v >= c.value if b > 0 else v <= c.value
        return v > c.value if b > 0 else v < c.value

    def reduce(self, c: Condition) -> None:
        for i in range(self.p.n):
            if self.active[i] and not self._ok(i, c, strict=False):
                self.active1[i] = False

    def adjust(self, c: Condition) -> None:
        for i in range(self.p.n):
            if self.active[i]:
                self.active1[i] = self._ok(i, c, strict=True)

    def inconsistencies(self, k: int) -> List[Inconsistency]:
        out = []
        for i in range(self.p.n):
            if not (self.active[i] and not self.active1[i]):
                continue
            for j in range(self.p.n):
                if not self.active1[j]:
                    continue
                x, y = self._dist(i, k), self._dist(j, k)
                code = stochastic_dominance(x, y, DARA).code
                if 0 < code < 127:
                    out.append(Inconsistency(i, j, afsd_mcdm(x, y)))
        return out

    def proposal(self, action: int, c: Condition, inc: Inconsistency) -> dict:
        """Propozycja nowego progu (formatka „Osłabienie/Zaostrzenie warunku”).
        Osłabienie: wartość parametru wariantu odrzuconego i; zaostrzenie: wariantu j."""
        a, b = (inc.i, inc.j) if action == WEAKEN else (inc.j, inc.i)
        psi = self.params[c.k].get(c.p)
        if c.p in (7, 8):
            return {"action": action, "value": self.value(a, c.k, c.p, psi),
                    "value_other": self.value(b, c.k, c.p, psi), "psi": psi}
        return {"action": action, "value": self.value(a, c.k, c.p, psi), "psi": psi}

    def R(self) -> Dict[int, Dict[Tuple[int, int], float]]:
        return {i: {(k, p): self.value(i, k, p) for k in range(self.p.m) for p in sorted(self.params[k])}
                for i in range(self.p.n) if self.active[i]}

    # --- dialog ---
    def _choose_params(self):
        for k in range(self.p.m):
            ch = dict((yield Ask("parameters", (k, dict(self.params[k])))))
            ch[1] = None
            for p, psi in ch.items():
                if PARAMS[p][2] and psi is None:
                    raise ValueError(f"Parametr {p} wymaga psi")
            self.params[k] = ch

    def run(self, dm: InsdecmDecisionMaker, max_iter: int = 100) -> InsdecmResult:
        """Przebieg dialogu z decydentem `dm` (wywołania blokujące)."""
        return drive(self.dialog(max_iter), lambda q: getattr(dm, q.kind)(self, *q.args))

    def dialog(self, max_iter: int = 100):
        """Dialog jako generator pytań `Ask` (zob. StemDPR.dialog)."""
        its: List[InsdecmIteration] = []
        yield from self._choose_params()
        while True:
            cancelled = False
            while True:   # iteracje
                self.iteration += 1
                if self.iteration > max_iter:
                    raise RuntimeError("Przekroczono max_iter")
                self.active1 = list(self.active)
                it = InsdecmIteration(self.iteration, [i for i in range(self.p.n) if self.active[i]],
                                      self.p_matrix(self.active))
                its.append(it)
                while True:
                    a = (yield Ask("parameters_sufficient", (it,)))
                    if a is None:
                        cancelled = True
                        break
                    if a:
                        break
                    yield from self._choose_params()
                    it.log.append("Zmieniono prezentowane parametry rozkładu")
                    it.P = self.p_matrix(self.active)
                if cancelled:
                    break
                a = (yield Ask("pessimistic_satisfactory", (it,)))
                if a is None:
                    cancelled = True
                    break
                if a:
                    it.log.append("Zaakceptowano wartości pesymistyczne")
                    break
                cond = (yield Ask("condition", (it,)))
                if cond is None:
                    cancelled = True
                    break
                k, p, v = cond
                if p not in self.params[k]:
                    raise ValueError(f"Parametr {p} nie jest prezentowany dla kryterium {k}")
                c = Condition(k, p, v, self.params[k][p])
                it.condition = c
                self.reduce(c)
                it.P_next = self.p_matrix(self.active1)
                a = (yield Ask("accept_changes", (it,)))
                if a is None:
                    cancelled = True
                    break
                if not a:
                    self.active1 = list(self.active)
                    continue
                N = self.inconsistencies(k)
                it.inconsistencies = list(N)
                action = KEEP
                while N:
                    m = min(x.eps for x in N)
                    inc = [x for x in N if x.eps <= m][-1]
                    action = (yield Ask("inconsistency_action", (it, inc)))
                    if action == KEEP:
                        N = [x for x in N if x.i != inc.i]
                        N = [x for x in N if x.j != inc.j]
                        it.log.append("Podtrzymano warunek")
                    else:
                        it.log.append("Osłabiono warunek" if action == WEAKEN else "Zaostrzono warunek")
                        prop = self.proposal(action, c, inc)
                        choice = (yield Ask("accept_proposal", (it, prop)))
                        if choice:
                            c = Condition(k, p, prop[choice], c.psi)
                            it.condition = c
                            self.adjust(c)
                            it.P_next = self.p_matrix(self.active1)
                        else:
                            self.active1 = list(self.active)
                        N = []
                for i in range(self.p.n):
                    if self.active[i]:
                        self.active[i] = self.active1[i]
            if cancelled:
                return InsdecmResult("cancelled", [], its, self.R())
            R = self.R()
            if (yield Ask("accept_solution", (R,))):
                return InsdecmResult("final", list(R), its, R)
            yield from self._choose_params()


class ScriptedInsdecmDM:
    """Decydent ze scenariusza. `script` — lista iteracji, każda to słownik:
      params: {kryterium: {p: psi}} — zmiana parametrów przed iteracją (opcjonalnie),
      condition: (kryterium, p, wartość) albo None = akceptacja wartości pesymistycznych,
      accept: bool (domyślnie True), action: KEEP/WEAKEN/TIGHTEN (domyślnie KEEP),
      proposal: 'value' / 'value_other' / None (domyślnie 'value').
    `initial` — parametry początkowe {kryterium: {p: psi}}. Kryteria mogą być nazwami."""

    def __init__(self, initial=None, script=(), accept_final=True):
        self.initial = initial or {}
        self.script = list(script)
        self.accept_final = accept_final
        self.pending = None
        self.step = -1

    def _k(self, s, k):
        return s.p.criteria.index(k) if isinstance(k, str) else k

    def _cur(self):
        return self.script[self.step] if 0 <= self.step < len(self.script) else {}

    def parameters(self, s, k, current):
        src = self.initial if self.pending is None else self.pending
        for kk, v in src.items():
            if self._k(s, kk) == k:
                return dict(v)
        return {}

    def parameters_sufficient(self, s, it):
        self.step = it.number - 1
        if "params" in self._cur() and self.pending is None:
            self.pending = self._cur()["params"]
            return False
        self.pending = None
        return True

    def pessimistic_satisfactory(self, s, it):
        return self._cur().get("condition") is None

    def condition(self, s, it):
        k, p, v = self._cur()["condition"]
        return self._k(s, k), p, v

    def accept_changes(self, s, it):
        return self._cur().get("accept", True)

    def inconsistency_action(self, s, it, inc):
        return self._cur().get("action", KEEP)

    def accept_proposal(self, s, it, prop):
        return self._cur().get("proposal", "value")

    def accept_solution(self, s, R):
        return self.accept_final
