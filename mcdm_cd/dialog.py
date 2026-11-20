"""Wspólny mechanizm dialogu: metody interaktywne są generatorami pytań do decydenta."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generator, Tuple


@dataclass
class Ask:
    kind: str          # nazwa pytania = nazwa metody w protokole decydenta
    args: Tuple = ()


def drive(gen: Generator, answer: Callable[[Ask], Any]):
    """Prowadzi dialog do końca, odpowiadając funkcją `answer`; zwraca wynik metody."""
    try:
        q = next(gen)
        while True:
            q = gen.send(answer(q))
    except StopIteration as e:
        return e.value
