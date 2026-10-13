"""Print the real signature of a function, with the defaults taken from the installed code."""
from __future__ import annotations

import inspect
from typing import Callable


def show_signature(obj: Callable, params: list[str] | None = None) -> None:
    """Print `qualname(` then one line for each parameter in `params` (all when None).

    The names, kinds and defaults come from `inspect.signature`, so they cannot drift from the
    installed library. When `params` selects a subset, the count of the others is printed.
    """
    sig = inspect.signature(obj)
    chosen = [p for n, p in sig.parameters.items() if params is None or n in params]
    missing = [n for n in (params or []) if n not in sig.parameters]
    if missing:
        raise KeyError(f"{obj.__qualname__} has no parameter {missing}")
    print(f"{obj.__qualname__}(")
    for p in chosen:
        print(f"    {p}")
    rest = len(sig.parameters) - len(chosen)
    print(")" if rest == 0 else f")  # {rest} more parameters")
