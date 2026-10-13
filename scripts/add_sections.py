"""Insert the How it works and Reference sections into a chapter, before "## What you have now".

    python3 scripts/add_sections.py chapters/01-series-and-dataframe.md how.md ref.md

Existing sections of the same name are replaced, so the script can be run again.
"""
import pathlib
import re
import sys

chapter, how, ref = (pathlib.Path(a) for a in sys.argv[1:4])
text = chapter.read_text(encoding="utf-8")
for heading in ("## How it works", "## Reference"):
    text = re.sub(rf"\n{re.escape(heading)}\n.*?(?=\n## )", "\n", text, flags=re.DOTALL)
block = "\n" + how.read_text(encoding="utf-8").strip() + "\n\n" + ref.read_text(encoding="utf-8").strip() + "\n"
marker = "\n## What you have now"
assert marker in text, "no 'What you have now' heading"
text = text.replace(marker, block + marker, 1)
chapter.write_text(text, encoding="utf-8")
print("updated", chapter)
