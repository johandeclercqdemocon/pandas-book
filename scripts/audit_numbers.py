"""List the numbers in the prose that no output of the book contains.

    python3 scripts/audit_numbers.py [files...]

A number in the text that appears in no ```text output block, and in no code block, is one of:
derived (check the arithmetic), copied wrong (fix it) or invented (delete it). The script
cannot tell which, so it lists them for a person to read. It never fails: it is an audit.

Ignored: years 2018 to 2027, clock times, numbers of 1 or 2 digits without a decimal point,
numbers inside links, and chapter numbers.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NUMBER = re.compile(r"(?<![\w.#/-])\d[\d,]*(?:\.\d+)?(?![\w-]*\()")
FENCE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def norm(token: str) -> str:
    t = token.replace(",", "")
    return t.rstrip(".")


def numbers_in(text: str) -> set[str]:
    return {norm(m.group(0)) for m in NUMBER.finditer(text)}


def md_files() -> list[pathlib.Path]:
    out = [ROOT / "README.md"] if (ROOT / "README.md").exists() else []
    for d in ("chapters", "appendices", "exercises", "exercises/solutions"):
        out += sorted((ROOT / d).glob("*.md"))
    return out


def known_numbers(files: list[pathlib.Path]) -> set[str]:
    known: set[str] = set()
    for p in files:
        for lang, body in FENCE.findall(p.read_text(encoding="utf-8")):
            known |= numbers_in(body)
    for p in (ROOT / "data").glob("*.csv"):
        pass
    return known


def prose_of(text: str) -> list[tuple[int, str]]:
    stripped = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    stripped = re.sub(r"\]\([^)]*\)", "]", stripped)          # links
    stripped = re.sub(r"^>.*$", "", stripped, flags=re.MULTILINE) if False else stripped
    return list(enumerate(stripped.splitlines(), 1))


def main() -> int:
    files = md_files()
    known = known_numbers(files)
    targets = [pathlib.Path(a).resolve() for a in sys.argv[1:]] or files
    total, unknown_total = 0, 0
    for p in targets:
        report = []
        for lineno, line in prose_of(p.read_text(encoding="utf-8")):
            line = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", line)             # clock times
            line = re.sub(r"\b[Cc]hapters? \d+(?:\s*(?:to|and|-)\s*\d+)?", "", line)
            line = re.sub(r"\b\d+\.\s", "", line)                                  # list numbers
            for m in NUMBER.finditer(line):
                n = norm(m.group(0))
                digits = n.replace(".", "")
                if re.fullmatch(r"20(1[89]|2[0-7])", n):
                    continue
                if "." not in n and len(digits) < 3:
                    continue
                total += 1
                if n not in known:
                    report.append((lineno, n, line.strip()[:110]))
        unknown_total += len(report)
        if report:
            print(f"\n{p.relative_to(ROOT)}  ({len(report)})")
            for lineno, n, ctx in report:
                print(f"  {lineno:>4}  {n:<12} {ctx}")
    print(f"\n{total} numbers in the prose, {unknown_total} not found in any output or code block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
