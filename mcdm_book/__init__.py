"""Metody wielokryterialnego wspomagania decyzji z książki „Wielokryterialne wspomaganie decyzji.
Metody i zastosowania” (red. T. Trzaskalik, PWE 2014). Interfejs: api.run({"method", "problem", "options"})."""
from .api import METHODS, methods, run, run_safe
from .problem import Problem, ProblemError

__version__ = "0.1.0"
