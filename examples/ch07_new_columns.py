"""Chapter 7: price every call three ways and time each one."""
import time

import pandas as pd

from pdbook.io import load_calls, load_plans, load_subscribers
from pdbook.rating import rate_apply, rate_loop, rate_vector

calls, subs, plans = load_calls(), load_subscribers(), load_plans()
results, seconds = {}, {}
for name, fn, repeat in [("iterrows loop", rate_loop, 1), ("apply(axis=1)", rate_apply, 1), ("vectorized", rate_vector, 5)]:
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        results[name] = fn(calls, subs, plans)
        best = min(best, time.perf_counter() - t0)
    seconds[name] = best

reference = results["vectorized"]
for name, r in results.items():
    pd.testing.assert_series_equal(r, reference)
print(f"{'method':14s} {'seconds':>8s} {'x slower':>9s}")
for name, s in seconds.items():
    print(f"{name:14s} {s:>8.3f} {s / seconds['vectorized']:>8.0f}x")
print(f"\nall three equal; total bill {reference.sum():,.2f} EUR over {int((reference > 0).sum()):,d} billed calls")
