# 24. Field guide

> **Build** — One page of lookups for the whole book: which idiom answers which question, which behavior is new in pandas 3.0, and which first-draft claims of this book the machine contradicted, each one reproduced by a block that runs.
>
> **Theory kept** — Most pandas errors are not syntax errors. They are a result that looks right. The defense is a habit: name the question, state what must add up, and test the result against a second computation.
>
> **Source** — The measurements of Chapters 1 to 23. Library: all of [`pdbook/`](../pdbook/).
>
> **Run this first** — `uv run python scripts/check_snippets.py`, which runs every block of the book. For this chapter alone: `uv run python -m examples.ch24_field_guide`, which is [`examples/ch24_field_guide.py`](../examples/ch24_field_guide.py). Exercises: [`exercises/24.md`](../exercises/24.md). Solutions: [`exercises/solutions/24.md`](../exercises/solutions/24.md).

## From question to idiom

| You want to | Use | Check that | Chapter |
|---|---|---|---|
| read a file with the right types | `read_csv(dtype=..., parse_dates=...)`, one loader function | identifiers are text, timestamps have a zone | [2](02-input-and-output.md) |
| keep a table small | `category`, small integers, `usecols` | `same_content` is `True` | [4](04-types-and-memory.md) |
| know why a value is missing | `null_report`, `determinants` | `groupby` totals add up to `len(df)` | [5](05-missing-data.md) |
| clean text and dates | `.str`, `to_datetime(format="mixed")` | the rejects are listed, not guessed | [6](06-text-and-date-cleanup.md) |
| add a rule as a column | `where`, `np.select`, `map` | no row loop, `isna().sum()` after a `map` | [7](07-new-columns.md) |
| one row for each key | `groupby(...).agg(name=(col, func))` | the sum of the groups equals the table | [8](08-group-by.md) |
| add columns from a lookup | `merge(how="left", validate="m:1")` | the row count did not change | [9](09-joins.md) |
| reshape | `pivot_table`, `melt`, `unstack` | the total of the cells equals the input | [10](10-pivot-and-melt.md) |
| a day or an hour in local time | `tz_convert`, then `dt` | the zone is in the label | [12](12-dates-and-resampling.md) |
| a moving statistic | `rolling("1h", closed="left")` | the count of samples is kept | [13](13-windows-shifts-gaps.md) |
| sessions, ranks, running totals | sort, mark, `cumsum` | the result does not depend on row order | [14](14-ranks-running-totals-sessions.md) |
| a readable pipeline | method chain, `pipe`, `require` | a shuffled input gives the same report | [16](16-method-chains-and-pipelines.md) |
| trust an input | rules, `validate`, `plant_faults` | the validator finds the planted counts | [17](17-data-validation.md) |
| speed | column operations, one `concat` | time on the real size, and check equality | [18](18-performance.md) |
| a file larger than memory | `usecols`, filters, `chunksize` | chunked equals whole | [19](19-data-larger-than-memory.md) |
| a database | `to_sql`, parameters, one query | the SQL report equals the pandas report | [20](20-sql-and-pandas.md) |
| nested JSON | `json_normalize`, `explode` | records in, rows out, in both directions | [22](22-json-and-nested-records.md) |
| features for a model | cutoff, past only, `assert_no_leak` | the future can change and the features do not | [23](23-features-and-evaluation.md) |

## What changed in pandas 3.0

This book ran every line on pandas 3.0.6. A change that the book only describes is in [Appendix A](../appendices/A-described-not-built.md).

| Behavior in 3.0 | Where it shows | Chapter |
|---|---|---|
| text columns have the dtype `str`, stored with Arrow | `calls["status"].dtype` is `str` | [1](01-series-and-dataframe.md), [4](04-types-and-memory.md) |
| timestamps parse to microseconds (`datetime64[us]`), nanoseconds only when the text needs them | `to_datetime` on three strings | [2](02-input-and-output.md) |
| copy-on-write: a derived object is a copy, chained assignment does nothing and warns | `ChainedAssignmentError` | [3](03-selection.md), [15](15-copy-on-write-and-traps.md) |
| `.str` methods on `str` return `False` for a missing value, a `bool` mask | `startswith` on `cell_id` | [3](03-selection.md) |
| `groupby(observed=True)` is the default for categories | an empty category has no row | [4](04-types-and-memory.md) |
| `to_json` warns about the default epoch dates with `Pandas4Warning` | `date_format="iso"` | [2](02-input-and-output.md) |
| the option `mode.copy_on_write` is deprecated: copy-on-write is always on | reading it warns | [15](15-copy-on-write-and-traps.md) |
| the first parameter of `Series.map` is named `func` | printed signature | [7](07-new-columns.md) |

## What went wrong while writing this book

A book that shows only its results is an advertisement. Each row below is a claim that I wrote down before I ran the code, and what the code printed. The block reproduces eight of them in one run, so that they stay true when the library changes:

```python
import io

import numpy as np
import pandas as pd

rows = []

calls = pd.read_csv("data/calls.csv")
rows.append(("ch1", "callee is text", f"callee is {calls['callee'].dtype}"))

try:
    pd.DataFrame({"k": [1, 2]}).merge(pd.DataFrame({"k": ["1", "2"]}), on="k")
except ValueError:
    rows.append(("ch2", "int and text keys match with no rows", "ValueError"))

try:
    pd.Series(["a"]) == "a" & pd.Series([1.0]) > 0
except Exception as error:
    rows.append(("ch3", "missing parentheses give ValueError", type(error).__name__))

missing = pd.Series(["BRU-001", None]).str.startswith("BRU")
rows.append(("ch3", "startswith keeps NaN for a missing value", f"{missing.dtype}, {missing.tolist()}"))

a = pd.DataFrame({"k": pd.Categorical(["x", "y"])})
b = pd.DataFrame({"k": pd.Categorical(["y", "z"])})
rows.append(("ch4", "concat of two categoricals is a category", pd.concat([a, b])["k"].dtype.name))

rows.append(("ch6", "two missing keys are not duplicates", str(pd.Series([None, None]).duplicated().tolist())))

try:
    pd.MultiIndex.from_tuples([(1, "a")]).isna()
except NotImplementedError:
    rows.append(("ch11", "MultiIndex has isna()", "NotImplementedError"))

x, y = pd.DataFrame({"v": [1.0]}), pd.DataFrame({"v": [1.0 + 1e-9]})
try:
    pd.testing.assert_frame_equal(x, y, rtol=0)
    rows.append(("ch17", "rtol=0 rejects a 1e-9 difference", "accepted"))
except AssertionError:
    rows.append(("ch17", "rtol=0 rejects a 1e-9 difference", "rejected"))

print("pandas", pd.__version__, "| numpy", np.__version__)
for chapter, claim, printed in rows:
    print(f"{chapter:5s} {claim:44s} -> {printed}")
```

```text
pandas 3.0.6 | numpy 2.5.4
ch1   callee is text                               -> callee is int64
ch2   int and text keys match with no rows         -> ValueError
ch3   missing parentheses give ValueError          -> TypeError
ch3   startswith keeps NaN for a missing value     -> bool, [True, False]
ch4   concat of two categoricals is a category     -> str
ch6   two missing keys are not duplicates          -> [False, True]
ch11  MultiIndex has isna()                        -> NotImplementedError
ch17  rtol=0 rejects a 1e-9 difference             -> accepted
```

Read each line as "I wrote the first half, and the machine printed the second". Eight lines in one run, and none of the eight was what I expected. The full list of the corrections that the book needed is longer, and it has the cause for each:

| Chapter | First draft said | The machine said | Cause |
|---|---|---|---|
| 5 | the lost cells are independent of everything | the loss rate is 0.48% for `EVS` and 2.09% for `AMR-NB` | the generator picks the codec from the cell, and a missing cell takes the 4G branch |
| 6 | `N/A` stays a string with `dtype=str` | `N/A` and the empty string are `NaN` after the read, only `-` stays text | the default list of missing markers applies to text columns |
| 6 | a bad regex raises `re.error` | `ArrowInvalid` | Arrow strings use another regular expression engine |
| 16 | a plan missing from the lookup stops the report | the report runs and the revenue is 3,681.87 instead of 4,245.09 | `groupby().sum()` skips `NaN` |
| 17 | `rtol=0` makes the comparison exact | a difference of 1e-9 passes | `atol=1e-8` is a second tolerance |
| 18 | a category column is faster in one step | the conversion costs more than one use saves | the conversion is in the timed function |
| 19 | the peak memory of a child is its own | it includes the parent at the fork | `ru_maxrss` is inherited; use `VmHWM` |
| 19 | the chunked count is an integer | `float64` when a caller is missing in a chunk | `add(fill_value=0)` upcasts |
| 19 | `17 13 MB` in a block | `21 16 MB` | the numbers were typed, not printed |
| 20 | this SQLite has no `CEIL` | it has `ceil` | the limit was assumed and never tried |
| 23 | shuffling the future finds a count leak | it passes | a shuffle keeps each caller's count |
| 23 | 450 tasks with 1 seed has a smaller standard error | 0.0302 against 0.0308: the same | the noise is in the runs, and three seeds cancel it |

The pattern is the same in every row. The error was in a sentence that I wrote before I ran something, or in a number that I carried from one run to another. The checks that the book ships catch each of them.

## How it works

This chapter has no new function. Its mechanism is a lookup. Each row of the first table names a chapter. The chapter must exist, and it must contain the function or the behavior that the row claims. The block checks the first part for every chapter link in this file:

```python
import pathlib
import re

root = pathlib.Path(".")
text = (root / "chapters" / "24-field-guide.md").read_text(encoding="utf-8")
links = sorted(set(re.findall(r"\]\((\d\d-[a-z0-9-]+\.md)\)", text)))
missing = [name for name in links if not (root / "chapters" / name).exists()]
print(len(links), missing)

numbers = sorted({int(n[:2]) for n in links})
print(numbers[0], numbers[-1], len(numbers))
```

```text
21 []
1 23 21
```

- **Invariant.** Every chapter in the tables exists, and the numbers cover Chapters 1 to 23 except those that have no row of their own.
- **Failure.** A renamed chapter file leaves a dead link. The checker of the book resolves every link and fails on it.
- **Cost.** Nothing at run time. The cost is the discipline of putting the check in the table and not in a comment.

## Reference

This chapter has no API of its own. The functions of the book are listed here, by module, from the code, so that you can find them by name:

```python
import importlib
import inspect
import pkgutil

import pdbook

for info in sorted(pkgutil.iter_modules(pdbook.__path__), key=lambda i: i.name):
    if info.name in {"datasets", "sigs"}:
        continue
    module = importlib.import_module(f"pdbook.{info.name}")
    names = [n for n, f in inspect.getmembers(module, inspect.isfunction)
             if f.__module__ == module.__name__ and not n.startswith("_")]
    print(f"pdbook.{info.name}: {', '.join(names)}")
```

```text
pdbook.bench: best_of, replicate, task_category, task_groupby_apply, task_iterrows, task_itertuples, task_mask_groupby
pdbook.chunked: make_big_csv, peak_rss_mb, talk_by_caller_chunked, talk_by_caller_whole
pdbook.clean: clean_contacts, e164, money, name_key
pdbook.enrich: enrich
pdbook.evals: compare_configs, load_runs
pdbook.features: assert_no_leak, leaky_features, past_features, target
pdbook.indexcheck: index_audit
pdbook.io: load_calls, load_cells, load_kpi, load_plans, load_subscribers
pdbook.kpi: hourly_kpi
pdbook.looks: first_look, headline
pdbook.nulls: determinants, null_report
pdbook.plots: plot_duration_hist, plot_hourly_calls, plot_kpi_spike, plot_traffic_grid
pdbook.rating: rate_apply, rate_loop, rate_vector
pdbook.report: monthly_report, require
pdbook.sessions: session_table, sessionize
pdbook.shrink: memory_report, same_content, shrink
pdbook.spikes: flag_spikes
pdbook.sqlbridge: build_database, monthly_report_sql
pdbook.summary: subscriber_summary
pdbook.traces: call_summary, events_table, read_traces
pdbook.traffic: to_long, to_wide, traffic_grid
pdbook.traps: live
pdbook.validate: assert_valid, call_rules, check_schema, plant_faults, validate
```

The helpers `pdbook.datasets` (the generator of the data) and `pdbook.sigs` (the signature printer) are left out of the list. The parameters of each function are in the Reference section of the chapter that builds it.

## What you have now

- You can find the idiom for a question, and the check that goes with it.
- You know which behaviors are new in pandas 3.0, and which of them this book ran.
- You have the list of what went wrong while this book was written, and the reason in each case.
- You have a method: write the claim, run it, and let the machine correct the sentence.

This is the last chapter. The appendices list what the book describes and does not run, and what Python already gives you.

Next: [Appendix A, Described, not built](../appendices/A-described-not-built.md).
