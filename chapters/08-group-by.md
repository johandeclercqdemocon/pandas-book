# 8. Group by

> **Build** — `subscriber_summary(calls, subs)`: a table with one row for each subscriber (calls, answered, failed, talk time, cells used, first and last call), and four checks that its totals match the call table.
>
> **Theory kept** — `groupby` splits the rows by a key, applies a function to each group and combines the results. `agg` returns one row for each group. `transform` returns one value for each original row. `filter` keeps or drops whole groups. The totals of the groups must add up to the table.
>
> **Source** — New. Library: [`pdbook/summary.py`](../pdbook/summary.py).
>
> **Run this first** — `uv run python -m examples.ch08_group_by`, which is [`examples/ch08_group_by.py`](../examples/ch08_group_by.py). Exercises: [`exercises/08.md`](../exercises/08.md). Solutions: [`exercises/solutions/08.md`](../exercises/solutions/08.md).

## Split, apply, combine

A `groupby` does three things. It splits the table into groups, one for each distinct key. It applies a function to each group. It combines the results into one object. Take six rows:

```python
import pandas as pd

mini = pd.DataFrame({
    "caller": ["A", "B", "A", "C", "B", "A"],
    "status": ["answered", "failed", "answered", "busy", "answered", "failed"],
    "duration_s": [60, None, 120, 0, 30, None],
})
g = mini.groupby("caller")
print(g.size().to_dict())
print(g["duration_s"].sum().to_dict())
print(g["duration_s"].transform("sum").tolist())
```

```text
{'A': 3, 'B': 2, 'C': 1}
{'A': 180.0, 'B': 30.0, 'C': 0.0}
[180.0, 30.0, 180.0, 0.0, 30.0, 180.0]
```

`size` and `sum` have one value for each caller: A, B and C. `transform("sum")` has one value for each of the six rows, and each row carries the sum of its own group. The index of the `transform` result is the index of `mini`, so it fits back into the table as a column.

The three operations answer different questions:

| Operation | Rows in the result | Question |
|---|---|---|
| `agg` | one for each group | "How many calls did each subscriber make?" |
| `transform` | one for each original row | "What share of the subscriber's calls is this call?" |
| `filter` | the rows of the groups that pass | "Show the calls of subscribers with more than 60 calls." |

## agg and named aggregation

With `agg` you give names to the outputs. The form `name=("column", "function")` is the clearest, and it uses the fast built-in path for functions given as strings:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
flagged = calls.assign(answered=calls["status"].eq("answered"))
by_status = flagged.groupby("status").agg(
    rows=("call_id", "size"),
    with_duration=("duration_s", "count"),
    mean_s=("duration_s", "mean"),
    longest_s=("duration_s", "max"),
)
print(by_status.round(1).to_string())
```

```text
           rows  with_duration  mean_s  longest_s
status                                           
answered  15526          15526   132.8     3836.0
busy       1428           1428     0.0        0.0
failed     1033              0     NaN        NaN
noanswer   2013           2013     0.0        0.0
```

The second column is `count`, the number of non-null values. The first is `size`, the number of rows. They differ for `failed`: 1,033 rows and no duration.

`mean` and `max` of an empty group are `NaN`. When you want "how many rows", use `size`. When you want "how many have a value", use `count`.

A boolean column is a counter. `sum` counts the `True` values and `mean` gives the share:

```python
import pandas as pd

from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()
plan = calls["caller"].map(dict(zip(subs["subscriber_id"], subs["plan"]))).rename("plan")
answered = calls["status"].eq("answered")
rate = answered.groupby(plan).agg(["sum", "size", "mean"]).round(3)
print(rate.to_string())
```

```text
           sum  size   mean
plan                       
basic     5153  6664  0.773
business  1763  2290  0.770
plus      3497  4475  0.781
prepaid   5113  6571  0.778
```

This is a Series grouped by another Series. The key `plan` is not a column of `calls`. A key can be any Series that has the same index, or an array of the same length. The four rates are between 0.77 and 0.79: the plan does not change the chance that a call is answered.

## Several keys

Give a list of keys. The result has one index level for each key, which [Chapter 11](11-index-and-multiindex.md) explains. Use `as_index=False` when you want the keys as ordinary columns:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
table = calls.groupby(["status", "roaming"], as_index=False).agg(rows=("call_id", "size"))
print(table.to_string(index=False))
```

```text
  status  roaming  rows
answered    False 15081
answered     True   445
    busy    False  1382
    busy     True    46
  failed    False  1002
  failed     True    31
noanswer    False  1972
noanswer     True    41
```

## transform: values that fit back into the table

A statistic of the group, next to each row, lets you compare a row with its group. Here is the share of each subscriber's talk time that each call makes up, and a flag for calls much longer than the subscriber's average:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
answered = calls[calls["status"] == "answered"].copy()
by_caller = answered.groupby("caller")["duration_s"]
answered["share"] = answered["duration_s"] / by_caller.transform("sum")
answered["vs_mean"] = answered["duration_s"] / by_caller.transform("mean")

print(round(float(answered.groupby("caller")["share"].sum().min()), 6),
      round(float(answered.groupby("caller")["share"].sum().max()), 6))
print(int((answered["vs_mean"] > 3).sum()), "calls are more than 3 times the mean of their caller")
```

```text
1.0 1.0
867 calls are more than 3 times the mean of their caller
```

The first line is a check. The shares of each subscriber add up to 1, so the minimum and the maximum of the sums are both 1. The same result without `transform` needs an `agg`, then a `merge` back to the table, and a risk of a wrong key. `transform` does it in one line, with the index preserved.

## filter: keep or drop whole groups

`filter` takes a function that returns one boolean for each group. The rows of the groups that return `True` stay:

```python
import time

import pandas as pd

from pdbook.io import load_calls

calls = load_calls()


def best_of(fn, repeat=5):
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        best = min(best, time.perf_counter() - t0)
    return best, result


t_filter, heavy = best_of(lambda: calls.groupby("caller").filter(lambda g: len(g) >= 60))
size = calls.groupby("caller")["call_id"].transform("size")
t_mask, same = best_of(lambda: calls[calls.groupby("caller")["call_id"].transform("size") >= 60])

print(len(heavy), heavy["caller"].nunique())
print(heavy.index.equals(same.index))
print(f"filter {t_filter * 1000:.1f} ms, mask {t_mask * 1000:.1f} ms, ratio {t_filter / t_mask:.0f}x")
assert t_filter / t_mask > 3
```

```text
# output varies
7058 56
True
filter 50.5 ms, mask 2.8 ms, ratio 18x
```

56 subscribers have 60 calls or more, and they make 7,058 of the 20,000 calls. The second form uses `transform("size")` and a mask. It gives the same rows. It is faster, because the lambda of `filter` runs once for each of the 600 groups in Python, and `transform("size")` runs once in compiled code. The block prints the times of one run. The assertion fails if the mask form is not at least 3 times faster on your machine.

## Keys that are not in the table

Group by a day or an hour of a timestamp column with `dt` or with `pd.Grouper`. The zone of the timestamp decides which calls belong to a day:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
utc_day = calls.groupby(calls["start"].dt.date).size()
local = calls["start"].dt.tz_convert("Europe/Brussels")
local_day = calls.groupby(local.dt.date).size()

print(len(utc_day), len(local_day))
print(utc_day.index[0], int(utc_day.iloc[0]), "|", local_day.index[0], int(local_day.iloc[0]))
print(int((utc_day.reindex(local_day.index).fillna(0).astype(int) != local_day).sum()), "days differ")
print(local_day.index.min(), local_day.index.max())
```

```text
31 30
2026-08-31 7 | 2026-09-01 728
26 days differ
2026-09-01 2026-09-30
```

The call records are in UTC. In UTC the month has 31 days, because the first calls of 1 September (local time) fall on 31 August in UTC. In local time it has the 30 days of September. The counts of the days that exist in both are different for most of the days, because a local day starts at 22:00 UTC. A daily report must say which zone it uses. [Chapter 12](12-dates-and-resampling.md) treats time zones.

## Totals must add up

Every report from a `groupby` has one check: the groups must add up to the table. You saw the ways that it fails. A missing key drops the group ([Chapter 5](05-missing-data.md)).

A `category` key with `observed=True` hides the empty groups ([Chapter 4](04-types-and-memory.md)). A `filter` or a `merge` before the `groupby` drops rows. Add the check as a line of code, so that it runs every time:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
by_cell = calls.groupby("cell_id").size()
print(int(by_cell.sum()), len(calls), int(by_cell.sum()) == len(calls))

by_cell = calls.groupby("cell_id", dropna=False).size()
print(int(by_cell.sum()), len(calls), int(by_cell.sum()) == len(calls))
```

```text
19723 20000 False
20000 20000 True
```

## Build: subscriber_summary

The summary has one row for each subscriber, and subscribers without calls stay in it. A `groupby` alone drops them. The function starts from the subscriber table and joins the aggregates on, so every subscriber is a row:

```python
import pandas as pd

from pdbook.io import load_calls, load_subscribers
from pdbook.summary import subscriber_summary

calls, subs = load_calls(), load_subscribers()
summary = subscriber_summary(calls, subs)
print(summary.shape)
print(summary.drop(columns=["first_call", "last_call"]).head(4).to_string(index=False))
print(summary["calls"].describe().round(1).to_dict())
```

```text
(600, 11)
subscriber_id    plan     city  calls  answered  failed  talk_min  cells  answer_rate
        S0001 prepaid Brussels     11         8       1      10.0      5        0.727
        S0002   basic   Leuven     14         9       2      16.1      2        0.643
        S0003 prepaid  Antwerp     27        18       3      33.8      5        0.667
        S0004 prepaid  Antwerp     11         9       1      14.5      5        0.818
{'count': 600.0, 'mean': 33.3, 'std': 44.2, 'min': 6.0, '25%': 17.0, '50%': 22.0, '75%': 33.0, 'max': 628.0}
```

The distribution of calls is very uneven. The median subscriber makes 22 calls and the maximum is 628. A mean of 33.3 calls for each subscriber describes nobody. Report the median and the percentiles for such a column.

Now the four checks. They run in the example module as well:

```python
import pandas as pd

from pdbook.io import load_calls, load_subscribers
from pdbook.summary import subscriber_summary

calls, subs = load_calls(), load_subscribers()
summary = subscriber_summary(calls, subs)
print(len(summary) == len(subs), bool(summary["subscriber_id"].is_unique))
print(int(summary["calls"].sum()) == len(calls))
print(int(summary["answered"].sum()) == int((calls["status"] == "answered").sum()))
print(round(float(summary["talk_min"].sum()), 1), round(float(calls["duration_s"].fillna(0).sum() / 60), 1))
```

```text
True True
True
True
34372.0 34372.5
```

The talk time differs by 0.5 minutes, from 34,372.0 to 34,372.5. The function rounds the minutes of each subscriber to one decimal, and 600 roundings add up to a small difference. A check must allow for the rounding that you put in. The test in the example module allows 0.05 minutes for each subscriber. Round for display, not in the table that you add up.

## How it works

A `groupby` does not move rows into groups. It turns the key column into an array of small integer codes, one for each row, and a list of the distinct keys. A reduction then runs once over the data with the codes as the group number. This is the `factorize` step, and `pd.factorize` shows it. The reduction `sum` for each group is what `np.bincount` does with weights.

You can rebuild a grouped sum from the two parts, and see that `transform` is the same reduction followed by a take:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
duration = calls["duration_s"].fillna(0).to_numpy()

codes, keys = pd.factorize(calls["caller"])
print(codes[:5].tolist(), len(keys), codes.dtype)

sums = np.bincount(codes, weights=duration)
by_hand = pd.Series(sums, index=keys).sort_index()
by_pandas = calls.groupby("caller")["duration_s"].sum().sort_index()
print(bool(np.allclose(by_hand.to_numpy(), by_pandas.to_numpy())))

as_column = sums[codes]
print(bool(np.allclose(as_column, calls.groupby("caller")["duration_s"].transform("sum").fillna(0).to_numpy())))
```

```text
[0, 1, 2, 3, 4] 600 int64
True
True
```

The codes are small integers (`int64` here, from 0 to 599), and there are 600 keys. The hand-made sum equals the sum of `groupby`. The `transform` is `sums[codes]`. The reduced array, indexed by the codes, puts each group value back on its rows. This is why the result has the index of the original table.

- **Invariant.** The groups are the distinct keys. A missing key has no code, so it is dropped unless `dropna=False`.
- **Failure.** The missing key of [Chapter 5](05-missing-data.md): the rows with no code are in no group.
- **Cost.** One pass to factorize the key, and one pass for each reduction. A key that is already a `category` has its codes, so the first pass is free.

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.summary import subscriber_summary

show_signature(pd.DataFrame.groupby, ["by", "as_index", "sort", "dropna", "observed"])
show_signature(pd.core.groupby.DataFrameGroupBy.agg, ["func"])
show_signature(pd.core.groupby.DataFrameGroupBy.transform, ["func"])
show_signature(pd.core.groupby.DataFrameGroupBy.filter, ["func", "dropna"])
show_signature(pd.Grouper)
show_signature(subscriber_summary)
```

```text
DataFrame.groupby(
    by=None
    as_index: 'bool' = True
    sort: 'bool' = True
    observed: 'bool' = True
    dropna: 'bool' = True
)  # 3 more parameters
DataFrameGroupBy.aggregate(
    func=None
)  # 5 more parameters
DataFrameGroupBy.transform(
    func
)  # 5 more parameters
DataFrameGroupBy.filter(
    func
    dropna: 'bool' = True
)  # 3 more parameters
Grouper(
    *args
    **kwargs
)
subscriber_summary(
    calls: 'pd.DataFrame'
    subs: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `groupby(by)` | `None` | the column, list of columns or Series that defines the groups | a key that is a Series must have the index of the table |
| `groupby(as_index=...)` | `True` | `False` keeps the keys as columns | — |
| `groupby(sort=...)` | `True` | sort the groups by key | — |
| `groupby(observed=...)` | `True` | category keys: only the groups that occur | — |
| `groupby(dropna=...)` | `True` | `False` keeps the missing key as a group | 277 calls missing from the report when `True` |
| `agg(func)` | `None` | a name or function, or `name=("column", "function")` | a lambda is slower than a built-in name |
| `transform(func)` | required | a result with one value for each original row | — |
| `filter(func, dropna=...)` | required, `True` | keep the groups for which `func` is `True` | more than 3 times slower than a mask from `transform("size")` (asserted) |
| `Grouper(key=..., freq=...)` | — | a time key, for example `key="start", freq="D"` | the zone of the column decides the day |
| `subscriber_summary(calls, subs)` | required | one row for each subscriber, zeros for no calls | — |

`agg` returns one row for each group. `transform` returns the index of the table. `subscriber_summary` returns a DataFrame with 600 rows.

## What you have now

- You pick `agg`, `transform` or `filter` from the shape of the result you want.
- You write named aggregations, and you use boolean columns as counters.
- You check that the groups add up to the table.
- You know that a group key can be a Series that is not a column, and that the zone of a timestamp decides the day.
- You have a summary table with one row for each subscriber.

The next chapter joins this summary with other tables, and shows how a join can silently multiply rows.

Next: [Chapter 9, Joins](09-joins.md).
