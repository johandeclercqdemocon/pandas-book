"""List code samples that break the example rules, for a person to read.

    uv run python scripts/audit_examples.py [files...]

Rules, from the review of the first example of the NumPy book (see the skill `programming-book-depth`, 3b):
  chain     the sample builds data with `arange(...).reshape(...)`: the values equal their positions, so a reader
            cannot tell a value from a place
  dtype     the sample passes `dtype=`: check that the text next to it gives the reason, because a reader who
            types the obvious call gets other numbers
  early     the sample calls a function or a method before the `####` block that introduces it. The blocks of
            the whole book count, in chapter order, because a later chapter links back to an earlier block
  unsigned  the sample calls a `pd.*` function that has no `####` block in the book (information only)

A method call such as `df.merge(` matches the first block whose name ends in `.merge`, so a hit on a
method can name the wrong class: read it as a hint. It never fails. It is an audit.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FENCE = re.compile(r"```python\n(.*?)```", re.S)
FULL = re.compile(r"\b(pd\.[A-Za-z_][\w.]*)\(")
METHOD = re.compile(r"[\w\])]\.([a-z_]\w*)\(")
HEAD = re.compile(r"^#### `([A-Za-z_][\w.]*)`", re.M)


def chapters() -> list[pathlib.Path]:
    return sorted((ROOT / "chapters").glob("*.md"))


def files() -> list[pathlib.Path]:
    named = [pathlib.Path(a).resolve() for a in sys.argv[1:]]
    return named or chapters()


def blocks_of_book() -> dict[str, tuple[int, int]]:
    """name -> (chapter number, line) of its `####` block."""
    out = {}
    for k, p in enumerate(chapters()):
        text = p.read_text(encoding="utf-8")
        for m in HEAD.finditer(text):
            out.setdefault(m.group(1), (k, text[:m.start()].count("\n") + 1))
    return out


def main() -> None:
    intro = blocks_of_book()
    by_last = {}
    for name in intro:
        by_last.setdefault(name.rsplit(".", 1)[-1], []).append(name)
    order = {p.resolve(): k for k, p in enumerate(chapters())}
    hits = {"chain": 0, "dtype": 0, "early": 0, "unsigned": 0}
    for p in files():
        text = p.read_text(encoding="utf-8")
        here = order.get(p.resolve(), len(order))
        out = []
        for m in FENCE.finditer(text):
            code, line = m.group(1), text[:m.start()].count("\n") + 1
            if re.search(r"arange\([^)]*\)\s*\.reshape\(", code):
                out.append((line, "chain", "arange(...).reshape(...)")); hits["chain"] += 1
            for d in sorted(set(re.findall(r"dtype=[^,)\s]+", code))):
                out.append((line, "dtype", d)); hits["dtype"] += 1
            full = set(FULL.findall(code))
            called = {(n, n) for n in full}
            called |= {(f".{n}", min(by_last[n], key=intro.get)) for n in METHOD.findall(code)
                       if n in by_last and f"pd.{n}" not in full}
            for shown, name in sorted(called):
                if name not in intro:
                    if shown == name and p.parent.name == "chapters":
                        out.append((line, "unsigned", name)); hits["unsigned"] += 1
                    continue
                k, at = intro[name]
                if (k, at) > (here, line):
                    where = f"line {at}" if k == here else f"chapter {k + 1}"
                    out.append((line, "early", f"{shown} -> {name} (block in {where})")); hits["early"] += 1
        if out:
            print(p.relative_to(ROOT))
            for line, kind, what in out:
                print(f"  {line:5d}  {kind:9s} {what}")
    print("\n" + ", ".join(f"{k} {v}" for k, v in hits.items()))


if __name__ == "__main__":
    main()
