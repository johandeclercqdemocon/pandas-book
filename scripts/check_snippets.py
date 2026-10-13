"""Check that this book's links, code and claimed outputs still agree.

    python3 scripts/check_snippets.py            # check everything
    python3 scripts/check_snippets.py --fill     # write real output into `text` blocks marked "# fill"
    python3 scripts/check_snippets.py --refill chapters/16-hashing.md   # regenerate every checked output in a file

Checks, all mechanical and all zero-false-positive by design:

  links     every relative markdown link resolves to a file that exists
  contract  every chapter carries Build / Theory kept / Source / Run this first
  python    every ```python block -- in chapters, exercises AND solutions -- is executed, exit 0
            and writes nothing to stderr (a warning is a failure: a reader copies the block)
  output    every ```text block directly below a ```python block must equal the real output
  examples  every examples/*.py module named in a chapter runs and exits 0
  sections  every chapter has "## How it works" and "## Reference" (or says why not)

A reader copies a block and runs it, so the check is execution, not syntax. Blocks that are not
programs belong in a ```text, ```bash or ```json fence and are skipped. A ```text block that
starts with `# output varies` is skipped (timings). Never weaken this file to fit a snippet --
rewrite the snippet.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")
PY_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)
PAIRED = re.compile(r"(```python\n((?:(?!```)[\s\S])*)```\s*)```text\n((?:(?!```)[\s\S])*)```")
CONTRACT = ("> **Build**", "> **Theory kept**", "> **Source**", "> **Run this first**")
RUN_TIMEOUT = 600
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"[FAIL] {msg}")


def md_files() -> list[pathlib.Path]:
    return sorted(p for p in [ROOT / "README.md", *(ROOT / "chapters").glob("*.md"), *(ROOT / "appendices").glob("*.md"),
                   *(ROOT / "exercises").glob("*.md"), *(ROOT / "exercises" / "solutions").glob("*.md")] if p.exists())


def run(src: str):
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "snippet.py"
        f.write_text(src, encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONHASHSEED": "0"}
        return subprocess.run([sys.executable, str(f)], capture_output=True, text=True,
                              timeout=RUN_TIMEOUT, cwd=ROOT, env=env)


def check_links(files):
    n = 0
    for p in files:
        for t in LINK.findall(p.read_text(encoding="utf-8")):
            if t.startswith(("http://", "https://", "mailto:")):
                continue
            n += 1
            if not (p.parent / t).resolve().exists():
                fail(f"{p.relative_to(ROOT)} -> {t} does not exist")
    return n


def check_contracts():
    chs = sorted((ROOT / "chapters").glob("*.md"))
    for p in chs:
        text = p.read_text(encoding="utf-8")
        miss = [m for m in CONTRACT if m not in text]
        if miss:
            fail(f"{p.relative_to(ROOT)} missing {', '.join(miss)}")
    return len(chs)


def norm(t):
    return [l.rstrip() for l in t.rstrip().splitlines()]


_cache: dict[str, object] = {}


def run_cached(src: str):
    """Run each distinct snippet once, however many checks need its result."""
    if src not in _cache:
        try:
            _cache[src] = run(src)
        except subprocess.TimeoutExpired:
            _cache[src] = None
    return _cache[src]


def check_python_and_outputs(files):
    """Execute every ```python block once (in parallel); compare each paired ```text block with its stdout."""
    from concurrent.futures import ThreadPoolExecutor

    blocks, paired = [], {}
    for p in files:
        text = p.read_text(encoding="utf-8")
        for i, src in enumerate(PY_BLOCK.findall(text), 1):
            blocks.append((p, i, src))
        for j, m in enumerate(PAIRED.finditer(text), 1):
            paired[(p, m.group(2))] = (j, m.group(3))

    for p, i, src in blocks:
        try:
            ast.parse(src)
        except SyntaxError as e:
            fail(f"{p.relative_to(ROOT)} block {i} does not parse: {e}")

    unique = sorted({src for _, _, src in blocks})
    # A block that measures time must not share the CPU with other blocks: run it alone, after
    # the parallel batch. (Run in parallel, two timing blocks slow each other down and an
    # assertion on a ratio fails for a reason that is not in the book.)
    timing = [src for src in unique if any(k in src for k in ("perf_counter", "best_of(", "peak_rss_mb"))]
    others = [src for src in unique if src not in set(timing)]
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        list(pool.map(run_cached, others))
    for src in timing:
        run_cached(src)

    checked = 0
    for p, i, src in blocks:
        label = f"{p.relative_to(ROOT)} block {i}"
        d = _cache[src]
        if d is None:
            fail(f"{label} timed out after {RUN_TIMEOUT}s")
        elif d.returncode:
            fail(f"{label} failed: {(d.stderr.strip().splitlines() or ['?'])[-1]}")
        elif d.stderr.strip():
            fail(f"{label} wrote to stderr: {d.stderr.strip().splitlines()[0]}")
        elif (p, src) in paired:
            j, want = paired[(p, src)]
            if want.lstrip().startswith("# output varies"):
                continue
            checked += 1
            a, c = norm(d.stdout), norm(want)
            if a != c:
                for k, (g, w) in enumerate(zip(a, c), 1):
                    if g != w:
                        fail(f"{label} output line {k}:\n      claimed: {w}\n      actual:  {g}")
                        break
                else:
                    fail(f"{label} output: claimed {len(c)} lines, produced {len(a)}")
    return len(blocks), checked


def check_examples():
    mods = sorted(set(re.findall(r"python3? -m (examples\.[A-Za-z0-9_]+)",
                                 "".join(p.read_text(encoding="utf-8") for p in (ROOT / "chapters").glob("*.md")))))
    for m in mods:
        if not (ROOT / (m.replace(".", "/") + ".py")).exists():
            fail(f"{m} named in a chapter but file is missing")
            continue
        try:
            d = subprocess.run([sys.executable, "-m", m], capture_output=True, text=True, timeout=RUN_TIMEOUT,
                               cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)})
        except subprocess.TimeoutExpired:
            fail(f"{m} timed out")
            continue
        if d.returncode:
            fail(f"{m} exited {d.returncode}: {(d.stderr.strip().splitlines() or ['?'])[-1]}")
        elif d.stderr.strip():
            fail(f"{m} wrote to stderr: {d.stderr.strip().splitlines()[0]}")
    return len(mods)


def check_sections():
    """Every chapter has a How it works section and a Reference section. A chapter with no API
    (a field guide) must say "No API in this chapter" under the heading instead of omitting it."""
    chs = sorted((ROOT / "chapters").glob("*.md"))
    for p in chs:
        text = p.read_text(encoding="utf-8")
        for heading in ("## How it works", "## Reference"):
            if heading not in text:
                fail(f"{p.relative_to(ROOT)} has no '{heading}' section")
    return len(chs)


def fill(files, refill=False):
    """Write real stdout into ```text blocks: those marked "# fill", or (refill) every checked block."""
    from concurrent.futures import ThreadPoolExecutor

    body = r"[\s\S]*?" if refill else r"# fill\n"
    marker = re.compile(r"(```python\n((?:(?!```)[\s\S])*)```\s*```text\n)(?!# output varies)" + body + "```")
    todo = {m.group(2) for p in files for m in marker.finditer(p.read_text(encoding="utf-8"))}
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        list(pool.map(run_cached, sorted(todo)))
    for p in files:
        text = p.read_text(encoding="utf-8")

        def sub(m):
            d = run_cached(m.group(2))
            if d is None or d.returncode:
                raise SystemExit(f"{p}: snippet failed:\n{d.stderr if d else 'timeout'}")
            return m.group(1) + d.stdout.rstrip() + "\n```"

        new = marker.sub(sub, text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            print(f"filled {p.relative_to(ROOT)}")


def main():
    files = md_files()
    only = [pathlib.Path(a).resolve() for a in sys.argv[1:] if not a.startswith("--")]
    if only:
        files = [f for f in files if f.resolve() in only]
    if "--fill" in sys.argv or "--refill" in sys.argv:
        fill(files, refill="--refill" in sys.argv)
        return 0
    links, chs = check_links(files), check_contracts()
    (blocks, outs), mods = check_python_and_outputs(files), check_examples()
    secs = check_sections()
    print(f"[ OK ] {links} relative links resolve")
    print(f"[ OK ] {chs} chapters carry their contract")
    print(f"[ OK ] {blocks} python blocks run")
    print(f"[ OK ] {outs} claimed outputs match what the code prints")
    print(f"[ OK ] {mods} example modules run")
    print(f"[ OK ] {secs} chapters have How it works and Reference")
    if failures:
        print(f"\n{len(failures)} problem(s).")
        return 1
    print(f"\nAll checks passed across {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
