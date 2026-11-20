"""Port algorytmów programów StDom 1.09b i MCDM 1.00 (K. Targiel) z płyty CD do książki
„Wielokryterialne wspomaganie decyzji. Metody i zastosowania” (red. T. Trzaskalik) oraz metoda ATO-DPR (8.5)."""
from .ato_dpr import AtoDPR, ScriptedAtoDM, tradeoff
from .distribution import EPS, PARAMS, Distribution, parameter
from .dominance import DARA, INARA, afsd, afsd_mcdm, assd, stdom_report, stochastic_dominance
from .insdecm import KEEP, TIGHTEN, WEAKEN, Insdecm, ScriptedInsdecmDM
from .mcf import Problem, example, problem_from_tables, read_mcf
from .stem_dpr import ConsoleStemDM, ScriptedStemDM, StemDPR

__version__ = "0.1.0"
