"""Split paragraphs of more than 6 sentences, as STE rule 6.6 requires.

    python3 scripts/ste_split_paragraphs.py chapters/05-missing-data.md [more files]

Uses the sentence rule of the STE checker (a sentence ends at . ! ? or :). Only plain paragraphs
are touched: code fences, tables, lists, headings, quotes and the contract block are left alone.
A paragraph with n > 6 sentences becomes ceil(n / 5) paragraphs of near-equal length.
"""
import math
import pathlib
import re
import sys

SENT = re.compile(r"(?<=[.!?:])\s+")
SKIP = re.compile(r"^(#|\||- |\* |\d+\. |>|```|!\[)")


def split_text(text: str) -> tuple[str, int]:
    out, n_changed, fence, buf = [], 0, False, []

    def flush():
        nonlocal n_changed
        if not buf:
            return
        par = " ".join(l.strip() for l in buf)
        sents = SENT.split(par)
        if len(sents) > 6:
            parts = math.ceil(len(sents) / 5)
            size = math.ceil(len(sents) / parts)
            groups = [" ".join(sents[i:i + size]) for i in range(0, len(sents), size)]
            out.append("\n\n".join(groups))
            n_changed += 1
        else:
            out.extend(buf)
        buf.clear()

    for line in text.split("\n"):
        if line.startswith("```"):
            flush()
            fence = not fence
            out.append(line)
        elif fence or not line.strip() or SKIP.match(line):
            flush()
            out.append(line)
        else:
            buf.append(line)
    flush()
    return "\n".join(out), n_changed


if __name__ == "__main__":
    for name in sys.argv[1:]:
        p = pathlib.Path(name)
        new, n = split_text(p.read_text(encoding="utf-8"))
        if n:
            p.write_text(new, encoding="utf-8")
        print(f"{name}: {n} paragraph(s) split")
