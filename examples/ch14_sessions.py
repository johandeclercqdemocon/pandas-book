"""Chapter 14: group calls into sessions and check the result."""
import pandas as pd

from pdbook.io import load_calls
from pdbook.sessions import session_table, sessionize

calls = load_calls()
print(f"{'gap':>6s} {'sessions':>9s} {'longest':>8s}")
for gap in ("1min", "5min", "30min", "2h", "1D"):
    t = session_table(sessionize(calls, gap))
    assert int(t["calls"].sum()) == len(calls)
    print(f"{gap:>6s} {len(t):>9,d} {int(t['calls'].max()):>8d}")

shuffled = calls.sample(frac=1, random_state=3)
assert sessionize(shuffled).equals(sessionize(calls))
print("same result for a shuffled input: True")
