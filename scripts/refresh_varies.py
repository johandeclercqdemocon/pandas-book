"""Replace the body of every ```text block that starts with `# output varies` by a real run.

    python3 scripts/refresh_varies.py [files...]

The block above it is executed once, and its stdout is written under the marker. This is the only
sanctioned way to put a timing into the book: a number in such a block was printed by a run, never
typed. Blocks that build very large files (make_big_csv, peak_rss_mb) are skipped unless named.
Prose that quotes a number from a block must be checked after a refresh: run audit_numbers.py.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VAR = re.compile(r"(```python\n((?:(?!```)[\s\S])*)```\s*```text\n# output varies\n)((?:(?!```)[\s\S])*)```")


def main() -> None:
    named = [pathlib.Path(a).resolve() for a in sys.argv[1:] if not a.startswith("--")]
    files = named or sorted([*(ROOT / "chapters").glob("*.md"), *(ROOT / "exercises" / "solutions").glob("*.md")])
    for p in files:
        text = p.read_text(encoding="utf-8")

        def sub(m):
            src = m.group(2)
            if ("make_big_csv" in src or "peak_rss" in src) and not named:
                return m.group(0)
            r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=ROOT,
                               env={"PYTHONPATH": str(ROOT), "PATH": ""})
            if r.returncode:
                raise SystemExit(f"{p}: block failed:\n{r.stderr[-400:]}")
            return m.group(1) + r.stdout.strip() + "\n```"

        new = VAR.sub(sub, text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            print("refreshed", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
