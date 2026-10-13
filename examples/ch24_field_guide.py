"""Chapter 24: the first-draft claims of this book, reproduced. Run the blocks of chapters/24-field-guide.md."""
import re
import subprocess
import sys
import pathlib

text = pathlib.Path("chapters/24-field-guide.md").read_text(encoding="utf-8")
blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
for i, src in enumerate(blocks, 1):
    out = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
    status = "ok" if out.returncode == 0 else "FAILED"
    print(f"block {i}: {status}")
    if out.returncode:
        print(out.stderr[-300:])
        raise SystemExit(1)
