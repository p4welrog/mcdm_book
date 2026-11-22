"""Metoda ANP (rozdz. 3.4) i rozmyta metoda ANP w ujęciu Changa (rozdz. 3.5).

Zadanie (oprócz variants i criteria):
  "clusters": {"AS": ["f1", "f2"], "AT": ["f3", "f4"]}       # komponenty kryteriów (domyślnie jeden: "Kryteria")
  "variants_cluster": "W"                                     # nazwa komponentu wariantów (domyślnie "Warianty")
  "influences": {"f1": ["f3", "f4", "a1", "a2"], ...}         # macierz zależności jako listy: element → elementy,
                                                              #   na które wpływa (kolumna supermacierzy = element)
  albo "dependency_matrix": [[0, 1, ...], ...]                # 0/1, wiersze i kolumny: kryteria, potem warianty
                                                              #   (wiersz i wpływa na kolumnę j, jak w przykładzie 3.11)
  "comparisons": {"f1": {"W": [[1, 3], [null, 1]], "AT": [[1, 5], [null, 1]]}, ...}
                                                              # porównania elementów komponentu, na które wpływa
                                                              #   dany element (kolejność jak w komponencie);
                                                              #   zamiast macierzy można podać wektor wag [0.75, 0.25]
  "cluster_comparisons": {"AS": {"clusters": ["AT", "W"], "matrix": [[1, 5], [null, 1]]}, ...}
                                                              # porównania komponentów ze względu na komponent
                                                              #   (albo "weights": [...] zamiast "matrix")
  albo "cluster_weights": [[...]]                             # macierz wag komponentów V (N×N, kolumny = komponent,
                                                              #   ze względu na który porównujemy)

Gdy brak "influences" i "dependency_matrix", element wpływa na wszystkie elementy komponentów wymienionych
w jego "comparisons". Element, który na nic nie wpływa (ujście), daje kolumnę zerową.

Struktura złożona BOCR (3.4.4, wzory 3.50–3.53):
  "subnets": {"B": {...sieć jak wyżej z własnymi "criteria"... } | {"priorities": [...]}, "O": ..., "C": ..., "R": ...},
  "bocr_weights": {"B": b, "O": o, "C": c, "R": r}
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .additive import _result
from .ahp import CHANG_SCALE, PRIORITY_METHODS, _num, consistency, priority_vector, reciprocal_matrix
from .fuzzy import TFN
from .problem import Problem, ProblemError

LIMITS = {
    "auto": "potęgi Ω̄^(2^k) do zbieżności (3.49); gdy brak zbieżności (cykle) — granica Cesàro (3.48)",
    "power": "tylko potęgi (3.49); błąd, gdy brak zbieżności",
    "cesaro": "granica Cesàro (3.48), liczona jako lim ((I + Ω̄)/2)^k",
}
SINKS = {"zero": "kolumna ujścia pozostaje zerowa (książka)",
         "loop": "ujście dostaje pętlę ω_jj = 1 (konwencja Saaty'ego dla hierarchii)"}
FORMULAS = {"additive": "b·B + o·O − c·C − r·R (3.53); bez wag (3.52)",
            "multiplicative": "B·O / (C·R) (3.50)",
            "multiplicative_weighted": "(b·B)(o·O) / ((c·C)(r·R)) (3.51)"}
BOCR_KEYS = ("B", "O", "C", "R")
_TOL = 1e-10


# ---------------------------------------------------------------------------
# Rozszerzona analiza Changa (3.54)–(3.59)
# ---------------------------------------------------------------------------

def _tfn(v: Any, where: str) -> TFN:
    if isinstance(v, str) and v.strip().lower() in CHANG_SCALE:
        return TFN(*map(float, CHANG_SCALE[v.strip().lower()]))
    if isinstance(v, (list, tuple)):
        return TFN.of([_num(x, where) for x in v], where)
    x = _num(v, where)
    return TFN(x, x, x)


def _is_fuzzy(M: Any) -> bool:
    return isinstance(M, (list, tuple)) and any(
        isinstance(r, (list, tuple)) and any(isinstance(x, (list, tuple)) or
                                             (isinstance(x, str) and x.strip().lower() in CHANG_SCALE) for x in r)
        for r in M)


def fuzzy_reciprocal(M: Sequence[Sequence[Any]], size: int, name: str) -> List[List[TFN]]:
    """Macierz trójkątnych liczb rozmytych; braki (null) uzupełniane przez M̃_ij = M̃_ji^(−1)."""
    if len(M) != size or any(len(r) != size for r in M):
        raise ProblemError(f"{name}: macierz porównań musi mieć wymiar {size}×{size}")
    F: List[List[Optional[TFN]]] = [[None] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            if M[i][j] is not None and M[i][j] != "":
                F[i][j] = _tfn(M[i][j], f"{name} [{i + 1},{j + 1}]")
    for i in range(size):
        F[i][i] = TFN(1.0, 1.0, 1.0)
        for j in range(size):
            if F[i][j] is None:
                t = F[j][i]
                if t is None:
                    raise ProblemError(f"{name}: brak porównania elementów {i + 1} i {j + 1}")
                F[i][j] = TFN(1 / t.u, 1 / t.m, 1 / t.l)
            if F[i][j].l <= 0:
                raise ProblemError(f"{name}: oceny porównań muszą być dodatnie")
    return F


def possibility(a: TFN, b: TFN) -> float:
    """V(a ≥ b) dla trójkątnych liczb rozmytych (Chang 1996)."""
    if a.m >= b.m:
        return 1.0
    if b.l >= a.u:
        return 0.0
    return (b.l - a.u) / ((a.m - a.u) - (b.m - b.l))


def chang(F: List[List[TFN]], self_degree: bool = False) -> Dict[str, Any]:
    """Rozszerzona analiza Changa: M̃_i (3.54), M̃ (3.55), S̃_i (3.56), d(C_i) = min V(S̃_i ≥ S̃_j) (3.57);
    self_degree — dopisanie 1 dla komponentu, ze względu na który porównujemy (3.58); normalizacja (3.59)."""
    n = len(F)
    rows = [TFN(sum(x.l for x in r), sum(x.m for x in r), sum(x.u for x in r)) for r in F]
    tot = TFN(sum(r.l for r in rows), sum(r.m for r in rows), sum(r.u for r in rows))
    inv = TFN(1 / tot.u, 1 / tot.m, 1 / tot.l)
    S = [TFN(r.l * inv.l, r.m * inv.m, r.u * inv.u) for r in rows]
    d = [min([possibility(S[i], S[j]) for j in range(n) if j != i] or [1.0]) for i in range(n)]
    full = d + ([1.0] if self_degree else [])
    s = sum(full)
    if s <= 0:
        raise ProblemError("Analiza Changa: wszystkie stopnie możliwości równe 0")
    return {"row_sums": [r.as_list() for r in rows], "total": tot.as_list(), "total_inverse": inv.as_list(),
            "S": [x.as_list() for x in S], "d": full, "w": [x / s for x in full]}


# ---------------------------------------------------------------------------
# Sieć
# ---------------------------------------------------------------------------

class Network:
    def __init__(self, criteria: List[str], variants: List[str], data: Dict[str, Any], name: str, notes: list):
        self.name = name
        vc = str(data.get("variants_cluster", "Warianty"))
        clusters = data.get("clusters")
        if clusters is None:
            clusters = {"Kryteria": list(criteria)} if criteria else {}
        if not isinstance(clusters, dict):
            raise ProblemError(f"{name}\"clusters\" musi być słownikiem {{komponent: [elementy]}}")
        clusters = {str(k): [str(e) for e in v] for k, v in clusters.items()}
        if vc in clusters:
            if set(clusters[vc]) != set(variants):
                raise ProblemError(f"{name}komponent {vc!r} musi zawierać dokładnie warianty")
            clusters[vc] = list(variants)
        else:
            clusters[vc] = list(variants)
        listed = [e for k, v in clusters.items() if k != vc for e in v]
        if sorted(listed) != sorted(criteria) or len(set(listed)) != len(listed):
            raise ProblemError(f"{name}każde kryterium musi należeć do dokładnie jednego komponentu "
                               f"(kryteria: {', '.join(criteria)})")
        self.clusters = clusters
        self.cluster_names = list(clusters)
        self.elements = [e for c in self.cluster_names for e in clusters[c]]
        self.cluster_of = {e: c for c in self.cluster_names for e in clusters[c]}
        self.index = {e: i for i, e in enumerate(self.elements)}
        self.variants = list(variants)
        self.vc = vc
        self.data = data
        self.notes = notes
        self.influences = self._influences()

    def _influences(self) -> Dict[str, List[str]]:
        data, name = self.data, self.name
        order = [e for c in self.cluster_names if c != self.vc for e in self.clusters[c]] + self.variants
        if data.get("influences") is not None and data.get("dependency_matrix") is not None:
            raise ProblemError(f"{name}podaj \"influences\" albo \"dependency_matrix\", nie oba")
        out: Dict[str, List[str]] = {e: [] for e in self.elements}
        if data.get("dependency_matrix") is not None:
            D = data["dependency_matrix"]
            n = len(order)
            if len(D) != n or any(len(r) != n for r in D):
                raise ProblemError(f"{name}macierz zależności musi mieć wymiar {n}×{n} (kryteria, potem warianty)")
            for i, e in enumerate(order):
                out[e] = [order[j] for j in range(n) if D[i][j]]
        elif data.get("influences") is not None:
            inf = data["influences"]
            if not isinstance(inf, dict):
                raise ProblemError(f"{name}\"influences\" musi być słownikiem {{element: [elementy]}}")
            for e, lst in inf.items():
                if str(e) not in self.index:
                    raise ProblemError(f"{name}influences: nieznany element {e!r}")
                bad = [x for x in lst if str(x) not in self.index]
                if bad:
                    raise ProblemError(f"{name}influences[{e}]: nieznane elementy {bad}")
                out[str(e)] = [str(x) for x in lst]
        else:
            comp = data.get("comparisons") or {}
            for e, per in comp.items():
                if str(e) not in self.index or not isinstance(per, dict):
                    continue
                for c in per:
                    if c not in self.clusters:
                        raise ProblemError(f"{name}comparisons[{e}]: nieznany komponent {c!r}")
                    out[str(e)] += [x for x in self.clusters[c] if x != e]
            self.notes.append(f"{name}Brak macierzy zależności — przyjęto, że element wpływa na wszystkie elementy "
                              f"komponentów, które porównano ze względu na niego.")
        # porządek jak w komponentach
        return {e: [x for x in self.elements if x in set(v)] for e, v in out.items()}

    # --- supermacierz początkowa (krok 4) ---
    def initial_supermatrix(self, method: str, fuzzy_elements: bool) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        n = len(self.elements)
        Om = [[0.0] * n for _ in range(n)]
        comp = self.data.get("comparisons") or {}
        if not isinstance(comp, dict):
            raise ProblemError(f"{self.name}\"comparisons\" musi być słownikiem")
        for e in comp:
            if e not in self.index:
                raise ProblemError(f"{self.name}comparisons: nieznany element {e!r}")
        log = []
        for e in self.elements:
            j = self.index[e]
            per = comp.get(e) or {}
            for c in per:
                if c not in self.clusters:
                    raise ProblemError(f"{self.name}comparisons[{e}]: nieznany komponent {c!r}")
            for c in self.cluster_names:
                targets = [x for x in self.influences[e] if self.cluster_of[x] == c]
                given = per.get(c)
                if not targets:
                    if given is not None:
                        raise ProblemError(f"{self.name}comparisons[{e}][{c}]: element {e} nie wpływa na komponent {c} "
                                           f"(uzupełnij macierz zależności)")
                    continue
                where = f"{self.name}Porównania ze względu na {e} w komponencie {c}"
                entry: Dict[str, Any] = {"element": e, "cluster": c, "elements": targets}
                k = len(targets)
                if given is None:
                    w = [1.0 / k] * k
                    if k > 1:
                        self.notes.append(f"{where}: brak porównań — przyjęto równe wagi.")
                    entry["w"] = w
                elif isinstance(given, (list, tuple)) and given and not isinstance(given[0], (list, tuple)):
                    vals = [_num(x, where) for x in given]
                    if len(vals) != k or any(v is None or v < 0 for v in vals) or sum(vals) <= 0:
                        raise ProblemError(f"{where}: wektor wag musi mieć {k} nieujemnych składowych "
                                           f"({', '.join(targets)})")
                    s = sum(vals)
                    w = [v / s for v in vals]
                    entry["w"] = w
                    entry["given"] = True
                elif _is_fuzzy(given):
                    if not fuzzy_elements:
                        raise ProblemError(f"{where}: oceny rozmyte — użyj metody fuzzy_anp")
                    res = chang(fuzzy_reciprocal(given, k, where))
                    w = res["w"]
                    entry.update(chang=res, w=w)
                else:
                    A = reciprocal_matrix(given, k, where, self.notes)
                    pr = priority_vector(A, method)
                    cons = consistency(pr["lambda_max"], k, self.notes, where)
                    w = pr["w"]
                    entry.update(matrix=A, w=w, lambda_max=pr["lambda_max"], **cons)
                for x, wx in zip(targets, w):
                    Om[self.index[x]][j] = wx
                log.append(entry)
        return Om, log

    def block_nonzero(self, Om) -> List[List[bool]]:
        N = len(self.cluster_names)
        out = [[False] * N for _ in range(N)]
        for i, e in enumerate(self.elements):
            for j, f in enumerate(self.elements):
                if Om[i][j] > 0:
                    out[self.cluster_names.index(self.cluster_of[e])][self.cluster_names.index(self.cluster_of[f])] = True
        return out

    # --- macierz wag komponentów (krok 3) ---
    def cluster_weights(self, Om, method: str, fuzzy: bool) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        names = self.cluster_names
        N = len(names)
        nz = self.block_nonzero(Om)
        data, name = self.data, self.name
        if data.get("cluster_weights") is not None:
            V = data["cluster_weights"]
            if len(V) != N or any(len(r) != N for r in V):
                raise ProblemError(f"{name}macierz wag komponentów musi mieć wymiar {N}×{N} ({', '.join(names)})")
            return [[float(_num(x, f"{name}cluster_weights") or 0.0) for x in r] for r in V], []
        cc = data.get("cluster_comparisons") or {}
        if not isinstance(cc, dict):
            raise ProblemError(f"{name}\"cluster_comparisons\" musi być słownikiem")
        V = [[0.0] * N for _ in range(N)]
        log = []
        for c in cc:
            if c not in names:
                raise ProblemError(f"{name}cluster_comparisons: nieznany komponent {c!r}")
        for j, c in enumerate(names):
            spec = cc.get(c)
            where = f"{name}Porównania komponentów ze względu na {c}"
            if spec is None:
                active = [i for i in range(N) if nz[i][j]]
                for i in active:
                    V[i][j] = 1.0 / len(active)
                if len(active) > 1:
                    self.notes.append(f"{where}: brak porównań — przyjęto równe wagi komponentów "
                                      f"{', '.join(names[i] for i in active)}.")
                continue
            comp = [str(x) for x in spec.get("clusters", [])]
            bad = [x for x in comp if x not in names]
            if bad or not comp:
                raise ProblemError(f"{where}: podaj \"clusters\" — listę komponentów (nieznane: {bad})")
            k = len(comp)
            entry: Dict[str, Any] = {"cluster": c, "clusters": comp}
            if spec.get("weights") is not None:
                vals = [_num(x, where) for x in spec["weights"]]
                if len(vals) != k or any(v is None or v < 0 for v in vals) or sum(vals) <= 0:
                    raise ProblemError(f"{where}: wektor wag musi mieć {k} nieujemnych składowych")
                s = sum(vals)
                w, out_names = [v / s for v in vals], comp
            elif spec.get("matrix") is not None:
                M = spec["matrix"]
                if fuzzy:
                    self_deg = c not in comp
                    res = chang(fuzzy_reciprocal(M, k, where), self_degree=self_deg)
                    w = res["w"]
                    out_names = comp + ([c] if self_deg else [])
                    entry["chang"] = res
                    if self_deg:
                        entry["self_degree"] = True
                elif _is_fuzzy(M):
                    raise ProblemError(f"{where}: oceny rozmyte — użyj metody fuzzy_anp")
                else:
                    A = reciprocal_matrix(M, k, where, self.notes)
                    pr = priority_vector(A, method)
                    cons = consistency(pr["lambda_max"], k, self.notes, where)
                    w, out_names = pr["w"], comp
                    entry.update(matrix=A, lambda_max=pr["lambda_max"], **cons)
            else:
                raise ProblemError(f"{where}: podaj \"matrix\" albo \"weights\"")
            for x, wx in zip(out_names, w):
                V[names.index(x)][j] = wx
            entry["v"] = [V[i][j] for i in range(N)]
            log.append(entry)
        return V, log


# ---------------------------------------------------------------------------
# Supermacierz ważona i graniczna (kroki 5–6)
# ---------------------------------------------------------------------------

def _mm(A, B):
    n, k, m = len(A), len(B), len(B[0])
    Bt = [[B[r][c] for r in range(k)] for c in range(m)]
    return [[sum(a * b for a, b in zip(A[i], Bt[c])) for c in range(m)] for i in range(n)]


def _maxdiff(A, B):
    return max(abs(a - b) for ra, rb in zip(A, B) for a, b in zip(ra, rb))


def limit_matrix(W: List[List[float]], mode: str = "auto", tol: float = 1e-12, max_squarings: int = 60
                 ) -> Dict[str, Any]:
    """Supermacierz graniczna: lim Ω̄^k (3.49) przez kolejne kwadraty albo granica Cesàro (3.48).
    Granica potęg jest przyjęta, gdy Ω̄^(2^k) = Ω̄^(2^(k+1)) = Ω̄^(2^k + 1) (wyklucza cykle)."""
    if mode not in LIMITS:
        raise ProblemError(f"Nieznany sposób wyznaczania granicy {mode!r}; dostępne: {', '.join(LIMITS)}")
    n = len(W)
    if mode in ("auto", "power"):
        P, power = [r[:] for r in W], 1
        for _ in range(max_squarings):
            Q = _mm(P, P)
            power *= 2
            if _maxdiff(P, Q) < tol:
                if _maxdiff(_mm(Q, W), Q) < 1e-9:
                    return {"G": Q, "mode": "power", "power": power}
                break
            P = Q
        if mode == "power":
            raise ProblemError("Potęgi supermacierzy ważonej nie są zbieżne (cykl w sieci) — użyj limit = cesaro")
    L = [[(W[i][j] + (1.0 if i == j else 0.0)) / 2 for j in range(n)] for i in range(n)]
    P, power = L, 1
    for _ in range(max_squarings):
        Q = _mm(P, P)
        power *= 2
        if _maxdiff(P, Q) < tol:
            return {"G": Q, "mode": "cesaro", "power": power}
        P = Q
    raise ProblemError("Nie udało się wyznaczyć supermacierzy granicznej")


def _evaluate(net: Network, method: str, fuzzy: bool, limit: str, sinks: str, read_from: Optional[str]
              ) -> Dict[str, Any]:
    notes = net.notes
    Om, elog = net.initial_supermatrix(method, fuzzy)
    V, clog = net.cluster_weights(Om, method, fuzzy)
    n = len(net.elements)
    ci = [net.cluster_names.index(net.cluster_of[e]) for e in net.elements]
    Wraw = [[Om[i][j] * V[ci[i]][ci[j]] for j in range(n)] for i in range(n)]       # (3.45)–(3.46)
    sums = [sum(Wraw[i][j] for i in range(n)) for j in range(n)]
    W = [r[:] for r in Wraw]
    renorm, sink_cols = [], []
    for j in range(n):
        if sums[j] <= _TOL:
            sink_cols.append(net.elements[j])
            if sinks == "loop":
                W[j][j] = 1.0
            continue
        if abs(sums[j] - 1) > 1e-9:
            renorm.append({"element": net.elements[j], "sum": sums[j]})
            for i in range(n):
                W[i][j] /= sums[j]
    if renorm:
        notes.append(f"{net.name}Kolumny supermacierzy ważonej znormalizowano (suma ≠ 1): "
                     + ", ".join(f"{r['element']} ({r['sum']:.4f})" for r in renorm) + ".")
    if sink_cols:
        notes.append(f"{net.name}Elementy bez wpływu (kolumny zerowe): {', '.join(sink_cols)}"
                     + (" — dodano pętle ω_jj = 1." if sinks == "loop" else "."))
    lim = limit_matrix(W, limit)
    G = lim["G"]
    if lim["mode"] == "cesaro" and limit == "auto":
        notes.append(f"{net.name}Potęgi supermacierzy ważonej nie są zbieżne (cykl) — użyto granicy Cesàro (3.48).")
    # odczyt wektora skali
    colsum = [sum(G[i][j] for i in range(n)) for j in range(n)]
    live = [j for j in range(n) if colsum[j] > 1e-9]
    if not live:
        raise ProblemError(f"{net.name}Supermacierz graniczna jest zerowa — sieć nie ma cyklu ani pętli "
                           f"(dla hierarchii użyj sinks = loop)")
    identical = all(max(abs(G[i][j] - G[i][live[0]]) for i in range(n)) < 1e-6 for j in live)
    if read_from is not None:
        if read_from not in net.index:
            raise ProblemError(f"read_from: nieznany element {read_from!r}")
        cols = [net.index[read_from]]
        how = f"kolumna {read_from}"
    elif identical:
        cols, how = [live[0]], "kolumny identyczne"
    else:
        sources = [j for j in live if all(Wraw[j][k] == 0 for k in range(n))]
        cols = sources or live
        how = ("średnia kolumn elementów źródłowych: " if sources else "średnia kolumn niezerowych: ") + \
              ", ".join(net.elements[j] for j in cols)
        notes.append(f"{net.name}Kolumny supermacierzy granicznej nie są identyczne — wektor skali: {how}.")
    vec = [sum(G[i][j] / colsum[j] for j in cols) / len(cols) for i in range(n)]
    vi = [net.index[v] for v in net.variants]
    raw = [vec[i] for i in vi]
    s = sum(raw)
    if s <= _TOL:
        raise ProblemError(f"{net.name}Warianty mają zerowe priorytety graniczne — sprawdź zależności")
    normal = [x / s for x in raw]
    mx = max(raw)
    return {"elements": net.elements, "clusters": net.clusters, "influences": net.influences,
            "cluster_weights": V, "cluster_comparisons": clog, "element_comparisons": elog,
            "initial_supermatrix": Om, "weighted_unnormalized": Wraw, "weighted_supermatrix": W,
            "limit_supermatrix": G, "limit_mode": lim["mode"], "limit_power": lim["power"], "read": how,
            "priorities_all": dict(zip(net.elements, vec)), "raw": raw, "normal": normal,
            "ideal": [x / mx for x in raw]}


def _network(p: Problem, data: Dict[str, Any], criteria: List[str], name: str, notes: list) -> Network:
    return Network(criteria, p.variants, data, name, notes)


def _subnet_eval(p: Problem, key: str, sub: Any, method, fuzzy, limit, sinks, notes) -> Dict[str, Any]:
    if not isinstance(sub, dict):
        raise ProblemError(f"subnets.{key}: oczekiwano opisu sieci albo {{\"priorities\": [...]}}")
    if sub.get("priorities") is not None:
        vals = [_num(x, f"subnets.{key}.priorities") for x in sub["priorities"]]
        if len(vals) != p.m or any(v is None or v < 0 for v in vals) or max(vals) <= 0:
            raise ProblemError(f"subnets.{key}.priorities: {p.m} nieujemnych wartości (kolejność wariantów)")
        s, mx = sum(vals), max(vals)
        return {"given": True, "raw": vals, "normal": [v / s for v in vals], "ideal": [v / mx for v in vals]}
    crit = [str(c["name"] if isinstance(c, dict) else c) for c in sub.get("criteria", [])]
    net = _network(p, sub, crit, f"[{key}] ", notes)
    return _evaluate(net, method, fuzzy, limit, sinks, sub.get("read_from"))


def _run(p: Problem, fuzzy: bool, method: str, limit: str, sinks: str, read_from: Optional[str],
         formula: str, bocr_mode: str) -> Dict[str, Any]:
    notes: list = []
    tag = "fuzzy_anp" if fuzzy else "anp"
    if method not in PRIORITY_METHODS:
        raise ProblemError(f"Nieznana metoda wektora skali {method!r}; dostępne: {', '.join(PRIORITY_METHODS)}")
    if sinks not in SINKS:
        raise ProblemError(f"sinks: {', '.join(SINKS)}")
    subnets = p.extra.get("subnets")
    if subnets is None:
        net = _network(p, p.extra, [c.name for c in p.criteria], "", notes)
        res = _evaluate(net, method, fuzzy, limit, sinks, read_from)
        res["method"] = method
        return _result(tag, p, res["normal"], "priorytety wariantów (znormalizowane z supermacierzy granicznej)",
                       res, notes)
    # struktura złożona BOCR (krok 8)
    if not isinstance(subnets, dict) or not subnets:
        raise ProblemError("\"subnets\" musi być słownikiem {B|O|C|R: sieć}")
    bad = [k for k in subnets if k not in BOCR_KEYS]
    if bad:
        raise ProblemError(f"subnets: dozwolone klucze {', '.join(BOCR_KEYS)} (nieznane: {bad})")
    if formula not in FORMULAS:
        raise ProblemError(f"formula: {', '.join(FORMULAS)}")
    if bocr_mode not in ("ideal", "normal"):
        raise ProblemError("bocr_mode: ideal albo normal")
    per = {k: _subnet_eval(p, k, subnets[k], method, fuzzy, limit, sinks, notes) for k in BOCR_KEYS if k in subnets}
    wts = p.extra.get("bocr_weights")
    if wts is not None:
        bad = [k for k in wts if k not in per]
        if bad:
            raise ProblemError(f"bocr_weights: klucze bez podsieci {bad}")
        wts = {k: float(_num(wts.get(k, 0), f"bocr_weights.{k}") or 0.0) for k in per}
    vals = {k: per[k][bocr_mode] for k in per}
    out = []
    for i in range(p.m):
        if formula == "additive":
            w = wts or {k: 1.0 for k in per}
            pos = sum(w[k] * vals[k][i] for k in ("B", "O") if k in per)
            neg = sum(w[k] * vals[k][i] for k in ("C", "R") if k in per)
            out.append(pos - neg)
        else:
            w = wts if (formula == "multiplicative_weighted" and wts) else {k: 1.0 for k in per}
            num = 1.0
            den = 1.0
            for k in ("B", "O"):
                if k in per:
                    num *= w[k] * vals[k][i]
            for k in ("C", "R"):
                if k in per:
                    den *= w[k] * vals[k][i]
            if den <= 0:
                raise ProblemError(f"Formuła multiplikatywna: zerowy koszt lub ryzyko wariantu {p.variants[i]}")
            out.append(num / den)
    if formula == "additive" and wts is None:
        notes.append("Brak wag b, o, c, r — formuła addytywna (3.52) z wagami 1.")
    if formula == "multiplicative_weighted" and wts is None:
        notes.append("Brak wag b, o, c, r — formuła (3.51) sprowadza się do (3.50).")
    if formula == "multiplicative_weighted" and wts:
        notes.append("Wagi w formule (3.51) mnożą wszystkie oceny przez tę samą stałą — uszeregowanie jak w (3.50).")
    if formula == "multiplicative" and wts:
        notes.append("Formuła multiplikatywna (3.50) nie używa wag b, o, c, r.")
    if formula == "additive" and any(x < 0 for x in out):
        notes.append("Ujemne oceny syntetyczne: koszty i ryzyko przeważają korzyści i szanse.")
    mx = max(out)
    s = sum(out)
    steps = {"formula": formula, "bocr_mode": bocr_mode, "bocr_weights": wts, "subnets": per, "raw": out,
             "ideal": [x / mx for x in out] if mx > 0 else None, "normal": [x / s for x in out] if s > 0 else None}
    return _result(tag, p, out, f"ocena syntetyczna BOCR ({FORMULAS[formula]})", steps, notes)


def anp(p: Problem, method: str = "eigen", limit: str = "auto", sinks: str = "zero", read_from: Optional[str] = None,
        formula: str = "additive", bocr_mode: str = "ideal") -> Dict[str, Any]:
    """ANP (algorytm z 3.4.5): macierz wag komponentów V, supermacierz początkowa Ω, ważona Ω̄ = Ω * V
    (3.45)–(3.46) z normalizacją kolumn, graniczna G (3.48)–(3.49), wektor skali wariantów (krok 7);
    struktura BOCR — synteza (3.50)–(3.53) (krok 8)."""
    return _run(p, False, method, limit, sinks, read_from, formula, bocr_mode)


def fuzzy_anp(p: Problem, method: str = "eigen", limit: str = "auto", sinks: str = "zero",
              read_from: Optional[str] = None, formula: str = "additive", bocr_mode: str = "ideal") -> Dict[str, Any]:
    """Rozmyta ANP (3.5): porównania komponentów w skali Changa — rozszerzona analiza Changa (3.54)–(3.59)
    z jedynką dla komponentu, ze względu na który porównujemy; porównania elementów rozmyte (Chang) albo
    ostre (method); dalej jak w ANP."""
    return _run(p, True, method, limit, sinks, read_from, formula, bocr_mode)
