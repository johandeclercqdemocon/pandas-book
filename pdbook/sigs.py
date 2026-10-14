"""Print the real signature of a function, with the defaults taken from the installed code.

The chapters print each signature in a `#### name` block. `signature_text` makes that text, and the checker
compares the block with it, so a signature in the book cannot drift from the installed library.
"""
from __future__ import annotations

import importlib
import inspect
from typing import Callable

ROOTS = {"pd": "pandas", "np": "numpy", "plt": "matplotlib.pyplot", "matplotlib": "matplotlib",
         "pdbook": "pdbook", "examples": "examples", "sqlite3": "sqlite3"}


def resolve(path: str):
    """Turn a dotted name such as `pd.DataFrame.merge` or `pdbook.io.load_calls` into the object.

    The longest prefix that imports as a module is the module. The rest are attributes. An accessor such as
    `pd.Series.str` resolves to its class, so `pd.Series.str.replace` is the method of that class.
    """
    root, *rest = path.split(".")
    if root not in ROOTS:
        raise ValueError(f"{path}: the first name must be one of {sorted(ROOTS)}")
    parts = ROOTS[root].split(".") + rest
    for k in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:k]))
        except ImportError:
            continue
        for attr in parts[k:]:
            obj = getattr(obj, attr)
        return obj
    raise ImportError(path)


def _plain(p: inspect.Parameter) -> str:
    """One parameter as the caller writes it: no annotation, and the default in its repr."""
    stars = {p.VAR_POSITIONAL: "*", p.VAR_KEYWORD: "**"}.get(p.kind, "")
    return stars + p.name + ("" if p.default is p.empty else f"={p.default!r}")


def signature_text(obj: Callable, name: str) -> str:
    """`name(` then one parameter for each line, with the `/` and `*` markers, then `)`.

    The annotations are left out: the parameter table of the chapter says what each parameter takes.
    """
    sig = inspect.signature(obj)
    lines, kinds = [], [p.kind for p in sig.parameters.values()]
    for i, p in enumerate(sig.parameters.values()):
        if p.kind is p.KEYWORD_ONLY and (i == 0 or kinds[i - 1] not in (p.KEYWORD_ONLY, p.VAR_POSITIONAL)):
            lines.append("*")
        lines.append(_plain(p))
        if p.kind is p.POSITIONAL_ONLY and (i + 1 == len(kinds) or kinds[i + 1] is not p.POSITIONAL_ONLY):
            lines.append("/")
    if not lines:
        return f"{name}()"
    return f"{name}(\n" + "".join(f"    {line},\n" for line in lines) + ")"


def parameters(obj: Callable) -> list[tuple[str, str | None]]:
    """(name, default) for each parameter that a caller can pass. The default is its repr, None if required.

    `self` is left out. A `*args` or `**kwargs` parameter keeps its stars and has the default "—".
    """
    out = []
    for p in inspect.signature(obj).parameters.values():
        if p.name == "self":
            continue
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            out.append(("*" if p.kind is p.VAR_POSITIONAL else "**") + p.name)
            out[-1] = (out[-1], "—")
        else:
            out.append((p.name, None if p.default is p.empty else repr(p.default)))
    return out


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
