"""Build "Pandas at Work" as one PDF, with page numbers.

Markdown -> HTML -> PDF, rendered by headless Chrome. No LaTeX, no pandoc, and
no system packages beyond a browser that is already installed.

Chrome is driven over the DevTools protocol rather than with `--print-to-pdf`,
for one reason: the footer. The command-line flag gives you either Chrome's own
footer — today's date, the page title and the `file://` URL of a temporary file,
none of which belong in a book — or, with `--no-pdf-header-footer`, no footer at
all. `Page.printToPDF` accepts a footer template, so the footer can carry the
page number and nothing else.

That also makes a numbered table of contents possible, and a numbered contents
needs two passes: print once to find out which page each section landed on, put
those numbers in the contents, print again. Adding the numbers can make the
contents one line longer and push everything after it down a page, so the
numbers are measured again and the pass repeats until what was printed matches
where things actually are.

Images are inlined as data URIs rather than linked, so the HTML is a single
self-contained file and the PDF cannot come out with missing figures because a
relative path resolved differently.

    uv run --with markdown --with websockets python scripts/build_pdf.py

The book itself has no dependencies; typesetting it is a separate job, so these two packages are
not in pyproject.toml.
"""

from __future__ import annotations

import base64
import contextlib
import json
import mimetypes
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import markdown
import websockets.sync.client

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts"

# A4, and the margins the text is set in. These used to live in an `@page`
# rule; the printer owns them now, because the footer is drawn in the bottom
# margin and Chrome has to know how much of it to reserve.
PAPER = {"paperWidth": 8.27, "paperHeight": 11.69,
         "marginTop": 0.71, "marginBottom": 0.79,
         "marginLeft": 0.63, "marginRight": 0.63}

FOOTER = ('<div style="width:100%;font:9px Helvetica,Arial,sans-serif;color:#888;'
          'text-align:center"><span class="pageNumber"></span></div>')

CSS = """
body { font-family: "Charter", "Georgia", serif; font-size: 10.5pt; line-height: 1.5;
       color: #1a1a1a; max-width: none; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 .3em; line-height: 1.2; }
h2 { font-size: 14pt; margin: 1.6em 0 .4em; border-bottom: 1px solid #ddd;
     padding-bottom: .15em; }
h3 { font-size: 11.5pt; margin: 1.3em 0 .3em; }
h4 { font-size: 10.5pt; margin: 1.1em 0 .25em; color: #333; }
h1, h2, h3, h4 { font-family: "Helvetica Neue", Arial, sans-serif; page-break-after: avoid; }
p, li { orphans: 2; widows: 2; }
code, pre { font-family: "DejaVu Sans Mono", Menlo, monospace; font-size: 8.6pt; }
code { background: #f4f4f4; padding: .1em .3em; border-radius: 2px; }
pre { background: #f7f7f7; border: 1px solid #e3e3e3; border-left: 3px solid #999;
      padding: .6em .8em; overflow-x: auto; white-space: pre-wrap;
      word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { margin: 1em 0; padding: .4em 1em; border-left: 3px solid #bbb;
             background: #fafafa; page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 9pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #ddd; padding: .35em .5em; text-align: left; }
th { background: #f0f0f0; }
img { max-width: 100%; page-break-inside: avoid; }
a { color: #14417a; text-decoration: none; }
.chapter { page-break-before: always; }
.toc { page-break-after: always; }
.toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc li { margin: .15em 0; padding-right: .2em; }
.toc li.group { margin-top: .9em; font-family: "Helvetica Neue", Arial, sans-serif;
                font-size: 10pt; }
.toc .pg { float: right; color: #666; font-variant-numeric: tabular-nums;
           font-family: "Helvetica Neue", Arial, sans-serif; font-size: 9pt; }
.cover { text-align: center; padding-top: 22vh; page-break-after: always; }
.cover h1 { font-size: 30pt; border: none; }
.cover .sub { font-size: 12pt; color: #555; margin-top: .8em; }
.cover .meta { font-size: 9.5pt; color: #777; margin-top: 3em; }
"""

EXTENSIONS = ["extra", "tables", "fenced_code", "sane_lists", "toc"]


def inline_images(html: str, base: pathlib.Path) -> str:
    """Replace <img src="..."> with data URIs so the file stands alone."""
    def swap(match: re.Match) -> str:
        src = match.group(1)
        if src.startswith(("http:", "https:", "data:")):
            return match.group(0)
        path = (base / src).resolve()
        if not path.exists():
            print(f"  ! missing image, dropped: {src}")
            return ""
        kind = mimetypes.guess_type(path)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'<img src="data:{kind};base64,{data}"'

    return re.sub(r'<img src="([^"]+)"', swap, html)


def strip_local_links(html: str) -> str:
    """Turn cross-file links into plain text.

    A PDF has no `../chapters/09-...md` to follow, and a link that silently goes
    nowhere is worse than no link. Anchors within the document are left alone.
    """
    return re.sub(r'<a href="(?!#)[^"]*\.md[^"]*">(.*?)</a>', r"\1", html,
                  flags=re.DOTALL)


def anchor_of(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def render(path: pathlib.Path, klass: str = "chapter") -> tuple[str, str]:
    """One markdown file to an HTML section, plus its title."""
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.*)$", text, re.M)
    title = title_match.group(1).strip() if title_match else path.stem

    html = markdown.markdown(text, extensions=EXTENSIONS)
    html = inline_images(html, path.parent)
    html = strip_local_links(html)
    return f'<section class="{klass}" id="{anchor_of(title)}">{html}</section>', title


def collect() -> tuple[list[str], list[tuple[str, str]]]:
    """Every section's HTML, and the contents as (title, anchor) pairs.

    A title starting with __GROUP__ is a heading inside the contents, not a
    section of the book.
    """
    parts: list[str] = []
    toc: list[tuple[str, str]] = []

    sources: list[tuple[str, list[pathlib.Path]]] = [
        ("Chapters", sorted((ROOT / "chapters").glob("*.md"))),
        ("Appendices", sorted((ROOT / "appendices").glob("*.md"))),
        ("Exercises", sorted((ROOT / "exercises").glob("[0-9]*.md"))),
        ("Worked solutions", sorted((ROOT / "exercises" / "solutions").glob("[0-9]*.md"))),
    ]

    for group, paths in sources:
        toc.append((f"__GROUP__{group}", ""))
        for path in paths:
            section, title = render(path)
            toc.append((title, anchor_of(title)))
            parts.append(section)

    return parts, toc


def build_html(parts: list[str], toc: list[tuple[str, str]],
               pages: dict[str, int]) -> str:
    """The whole book as one HTML file, with whatever page numbers are known."""
    lines = []
    for title, anchor in toc:
        if title.startswith("__GROUP__"):
            lines.append(f'<li class="group"><strong>{title[9:]}</strong></li>')
        else:
            number = pages.get(anchor)
            tag = f'<span class="pg">{number}</span>' if number else ""
            lines.append(f'<li>{tag}<a href="#{anchor}">{title}</a></li>')

    chapters = len(list((ROOT / "chapters").glob("*.md")))
    words = sum(len(p.read_text(encoding="utf-8").split())
                for p in (ROOT / "chapters").glob("*.md"))

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Pandas at Work</title><style>{CSS}</style></head><body>
<div class="cover">
  <h1>Pandas at Work</h1>
  <div class="sub">A practical book on pandas 3.0, with one data set of call records</div>
  <div class="meta">{chapters} chapters &middot; {words:,} words<br>
  Code that ships with the book printed every number in it.</div>
</div>
<section class="toc"><h1>Contents</h1><ul>{''.join(lines)}</ul></section>
{''.join(parts)}
</body></html>"""


class Chrome:
    """Just enough of the DevTools protocol to print one page to PDF."""

    def __init__(self, stack: contextlib.ExitStack) -> None:
        self.profile = pathlib.Path(tempfile.mkdtemp(prefix="pd-book-chrome-"))
        stack.callback(shutil.rmtree, self.profile, ignore_errors=True)
        self.proc = subprocess.Popen(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--remote-debugging-port=0", f"--user-data-dir={self.profile}",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stack.callback(self.close)

        port_file = self.profile / "DevToolsActivePort"
        deadline = time.monotonic() + 30
        while not port_file.exists():
            if time.monotonic() > deadline:
                raise SystemExit("chrome never opened a debugging port")
            time.sleep(0.05)
        port = port_file.read_text().splitlines()[0]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version") as r:
            endpoint = json.load(r)["webSocketDebuggerUrl"]
        self.ws = stack.enter_context(
            websockets.sync.client.connect(endpoint, max_size=None,
                                           open_timeout=30))
        self.next_id = 0

    def call(self, method: str, params: dict | None = None,
             session: str | None = None) -> dict:
        self.next_id += 1
        message = {"id": self.next_id, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        self.ws.send(json.dumps(message))
        while True:
            reply = json.loads(self.ws.recv(timeout=600))
            if reply.get("id") == self.next_id:
                if "error" in reply:
                    raise SystemExit(f"{method} failed: {reply['error']}")
                return reply["result"]

    def print_to_pdf(self, page: pathlib.Path, pdf: pathlib.Path) -> None:
        target = self.call("Target.createTarget", {"url": page.as_uri()})
        session = self.call("Target.attachToTarget",
                            {"targetId": target["targetId"], "flatten": True})
        session = session["sessionId"]
        self.call("Page.enable", session=session)
        # A 400-page document of inlined images is not laid out the instant the
        # load event fires, and printing early silently truncates it.
        time.sleep(5)
        result = self.call("Page.printToPDF", {
            "printBackground": True,
            "displayHeaderFooter": True,
            "headerTemplate": "<div></div>",
            "footerTemplate": FOOTER,
            **PAPER,
        }, session=session)
        pdf.write_bytes(base64.b64decode(result["data"]))
        self.call("Target.closeTarget", {"targetId": target["targetId"]})

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.proc.terminate()
            self.proc.wait(timeout=20)


def flat(text: str) -> str:
    return " ".join(text.split()).lower()


def page_texts(pdf: pathlib.Path) -> list[str]:
    """The text of each page, flattened. Index 0 is page 1."""
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    pages = out.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return [flat(p) for p in pages]


def locate(toc: list[tuple[str, str]], pages: list[str]) -> dict[str, int]:
    """Which page each section starts on.

    Titles are matched in document order from a moving cursor, so a chapter
    title quoted inside a later chapter cannot claim the entry. The contents
    pages are skipped first — they list every title, and would otherwise match
    all of them.
    """
    titles = [(anchor, flat(title)) for title, anchor in toc
              if not title.startswith("__GROUP__")]
    known = [t for _, t in titles]

    start = 0
    for i, text in enumerate(pages):
        if sum(1 for t in known if t in text) >= 3:
            start = i + 1
        elif start:
            break

    found: dict[str, int] = {}
    cursor = start
    for anchor, title in titles:
        for i in range(cursor, len(pages)):
            if title and title in pages[i]:
                found[anchor] = i + 1
                cursor = i
                break
    return found


def main() -> None:
    parts, toc = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    page = OUT / "pandas-book.html"
    pdf = OUT / "pandas-book.pdf"

    sections = sum(1 for title, _ in toc if not title.startswith("__GROUP__"))
    numbers: dict[str, int] = {}

    with contextlib.ExitStack() as stack:
        chrome = Chrome(stack)
        for attempt in range(1, 5):
            page.write_text(build_html(parts, toc, numbers), encoding="utf-8")
            chrome.print_to_pdf(page, pdf)
            if not pdf.exists():
                raise SystemExit("chrome produced no PDF")
            pages = page_texts(pdf)
            measured = locate(toc, pages)
            print(f"pass {attempt}: {len(pages)} pages, "
                  f"{len(measured)}/{sections} sections located")
            if measured == numbers:
                break
            numbers = measured
        else:
            print("! contents page numbers did not settle after 4 passes; "
                  "they may be a page out", file=sys.stderr)

    missing = [title for title, anchor in toc
               if not title.startswith("__GROUP__") and anchor not in numbers]
    for title in missing:
        print(f"  ! no page number for: {title}")

    print(f"wrote {page} ({page.stat().st_size / 1e6:.1f} MB)")
    print(f"wrote {pdf} ({pdf.stat().st_size / 1e6:.1f} MB, {len(pages)} pages)")


if __name__ == "__main__":
    main()
