"""Chapter 18: one task written five ways, timed, with a check that all five agree."""
import pandas as pd

from pdbook.bench import (best_of, replicate, task_category, task_groupby_apply, task_iterrows,
                          task_itertuples, task_mask_groupby)
from pdbook.io import load_calls

calls = replicate(load_calls(), 5)
rungs = [("iterrows loop", task_iterrows, 1), ("itertuples loop", task_itertuples, 1),
         ("groupby().apply", task_groupby_apply, 1), ("mask + groupby", task_mask_groupby, 5),
         ("category + mask + groupby", task_category, 5)]
seconds, results = {}, {}
for name, fn, repeat in rungs:
    seconds[name], results[name] = best_of(lambda fn=fn: fn(calls), repeat)

reference = results["mask + groupby"]
for name, result in results.items():
    pd.testing.assert_series_equal(result, reference, check_names=False)

print(f"{len(calls):,d} rows")
fast = seconds["mask + groupby"]
for name, s in seconds.items():
    print(f"{name:26s} {s:8.4f} s {s / fast:8.1f}x")
