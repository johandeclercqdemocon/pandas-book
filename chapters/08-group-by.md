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

#### `pd.DataFrame.groupby`

```text
pd.DataFrame.groupby(
    self,
    by=None,
    level=None,
    *,
    as_index=True,
    sort=True,
    group_keys=True,
    observed=True,
    dropna=True,
)
```

The method returns a `DataFrameGroupBy` object. Nothing is computed until you call a method on it, such as `size`, `sum`, `agg` or `transform`. The Series method has the same parameters.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `by` | `None` | the key: a column name, a list of names, a Series, an array of the same length, a dict or a function of the index labels | a Series key aligns on the index, not on the position: a key with the labels 1 and 2 puts row 0 in no group. A name that is not a column raises `KeyError` |
| `level` | `None` | group by a level of a MultiIndex, by number or name ([Chapter 11](11-index-and-multiindex.md)) | — |
| `as_index` | `True` | `True` makes the keys the index of the result. `False` keeps them as columns | `as_index=False` on a Series groupby raises `TypeError` |
| `sort` | `True` | sort the result by the keys. `False` keeps the order in which each key first appears | — |
| `group_keys` | `True` | for `apply` with a result of the same shape as the group: add the keys as an index level | with `True`, the index of the result becomes `(key, label)` pairs and does not fit back on the table |
| `observed` | `True` | for a `category` key: `True` shows only the categories that occur. pandas 3.0 changed the default from `False` | a category with no rows has no row in the report: 4 groups and not 5 for the five categories of [Chapter 4](04-types-and-memory.md) |
| `dropna` | `True` | drop the rows whose key is missing | `True` loses 277 calls: totals of 19,723 against 20,000 ([Chapter 5](05-missing-data.md)) |

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

#### `pd.core.groupby.DataFrameGroupBy.agg`

```text
pd.core.groupby.DataFrameGroupBy.agg(
    self,
    func=None,
    *args,
    engine=None,
    engine_kwargs=None,
    **kwargs,
)
```

The method returns one row for each group, with one column for each aggregation. `aggregate` is the same method.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | `None` | a name such as `"mean"`, a function, a list of them, or a dict of column to function. `None` when you use named aggregation | a lambda runs in Python for each group: `agg(lambda s: s.mean())` was 66 times slower than `agg("mean")` over 600 callers |
| `*args` | — | more positional arguments for a function in `func` | — |
| `engine` | `None` | `'cython'` or `'numba'` for a function. `None` means `'cython'` | `engine="numba"` raises `ModuleNotFoundError` here |
| `engine_kwargs` | `None` | options for the `numba` engine | — |
| `**kwargs` | — | named aggregation: `name=("column", "function")`, one output column for each keyword. With a `func`, more keyword arguments for it | a column that does not exist raises `KeyError`. A keyword that the function does not take raises `TypeError` |

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

#### `pd.core.groupby.DataFrameGroupBy.transform`

```text
pd.core.groupby.DataFrameGroupBy.transform(
    self,
    func,
    *args,
    engine=None,
    engine_kwargs=None,
    **kwargs,
)
```

The method returns a result with the index of the original table: one value for each row, computed from its group.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | required | a name such as `"sum"`, or a function of one group. One value for each group is spread over the rows of the group | a function that returns fewer rows than the group gets `NaN` for the other rows, with no error |
| `*args` | — | more positional arguments for `func` | — |
| `engine` | `None` | `'cython'` or `'numba'` for a function | — |
| `engine_kwargs` | `None` | options for the `numba` engine | — |
| `**kwargs` | — | more keyword arguments for `func` | — |

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
filter 56.1 ms, mask 3.9 ms, ratio 15x
```

56 subscribers have 60 calls or more, and they make 7,058 of the 20,000 calls. The second form uses `transform("size")` and a mask. It gives the same rows. It is faster, because the lambda of `filter` runs once for each of the 600 groups in Python, and `transform("size")` runs once in compiled code. The block prints the times of one run. The assertion fails if the mask form is not at least 3 times faster on your machine.

#### `pd.core.groupby.DataFrameGroupBy.filter`

```text
pd.core.groupby.DataFrameGroupBy.filter(
    self,
    func,
    dropna=True,
    *args,
    **kwargs,
)
```

The method returns the rows of the groups for which `func` returns `True`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | required | a function of one group that returns one `True` or `False` | a function that returns a number or a Series raises `TypeError`. More than 3 times slower than a mask from `transform("size")` (asserted) |
| `dropna` | `True` | `False` keeps the rows of the failing groups, with `NaN` in every column | — |
| `*args` | — | more positional arguments for `func`. They come after `dropna` | `filter(f, 1)` gives the `1` to `dropna`, not to `f`. Pass the argument by name |
| `**kwargs` | — | more keyword arguments for `func` | — |

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

`pd.Grouper` does the same with a frequency instead of `dt.date`. It keeps the timestamp, with its zone, as the key:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
by_utc = calls.groupby(pd.Grouper(key="start", freq="D")).size()
local = calls.assign(start=calls["start"].dt.tz_convert("Europe/Brussels"))
by_local = local.groupby(pd.Grouper(key="start", freq="D")).size()
print(len(by_utc), by_utc.index[0])
print(len(by_local), by_local.index[0])
print(int(by_utc.sum()), int(by_local.sum()))
```

```text
31 2026-08-31 00:00:00+00:00
30 2026-09-01 00:00:00+02:00
20000 20000
```

The keys are the starts of the days, in the zone of the column. The two reports have the same total and different days.

#### `pd.Grouper`

```text
pd.Grouper(
    *args,
    **kwargs,
)
```

The class describes a group key for `groupby`. With `freq`, it groups timestamps into periods, and it becomes a `TimeGrouper`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `*args` | — | positional arguments. The first one is taken as `key` | — |
| `**kwargs` | — | `key` (the column), `level`, `freq` (such as `"D"` or `"1h"`), `sort` and `dropna`. With `freq`, also `closed`, `label`, `origin`, `offset` and `convention`, as for `resample` ([Chapter 12](12-dates-and-resampling.md)) | `freq` on a column of text raises `TypeError`. With `freq="D"`, `origin` and `offset` do nothing and give a `RuntimeWarning`. `axis` raises `TypeError` in pandas 3.0 |

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

#### `pdbook.summary.subscriber_summary`

```text
pdbook.summary.subscriber_summary(
    calls,
    subs,
)
```

The function returns one row for each subscriber in `subs`, with zeros for a subscriber who made no call.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | a call whose caller is not in `subs` is in no row, with no message. The check `summary["calls"].sum() == len(calls)` finds it |
| `subs` | required | the subscribers, with `subscriber_id`, `plan` and `city` | — |

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

The next block tests both claims. A missing key gets the code -1 from `pd.factorize`, so it is in no group. Then it times a grouped sum on two million rows: once with a `str` key, which pandas must factorize, and once with a `category` key, which has its codes:

```python
import timeit

import numpy as np
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
codes, keys = pd.factorize(calls["cell_id"])
print(int((codes == -1).sum()), "rows with code -1,", int(calls["cell_id"].isna().sum()), "missing keys")

big = pd.concat([calls] * 100, ignore_index=True)
as_str = big["cell_id"]
as_cat = as_str.astype("category")
duration = big["duration_s"]


def best(f):
    return min(timeit.repeat(f, number=1, repeat=5))


t_str = best(lambda: duration.groupby(as_str).sum())
t_cat = best(lambda: duration.groupby(as_cat).sum())
t_factorize = best(lambda: pd.factorize(as_str))
same = np.allclose(duration.groupby(as_str).sum().to_numpy(), duration.groupby(as_cat).sum().to_numpy())
assert same and t_str / t_cat > 1.3
print(f"str key       {t_str * 1e3:6.0f} ms")
print(f"category key  {t_cat * 1e3:6.0f} ms")
print(f"factorize     {t_factorize * 1e3:6.0f} ms")
```

```text
# output varies
277 rows with code -1, 277 missing keys
str key           88 ms
category key      37 ms
factorize         58 ms
```

The 277 missing cells have the code -1, which is no group. The two sums are equal, and the `category` key is faster, which is what the assertion checks. The difference is about the time of `factorize` alone: a `str` key pays for its codes on each `groupby`. A key that you group by many times is a good candidate for `category`.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.groupby` | Split, apply, combine | a lazy grouping by keys; a missing key and an empty category are dropped by default |
| `pd.core.groupby.DataFrameGroupBy.agg` | agg and named aggregation | one row for each group |
| `pd.core.groupby.DataFrameGroupBy.transform` | transform: values that fit back into the table | one value for each original row, from its group |
| `pd.core.groupby.DataFrameGroupBy.filter` | filter: keep or drop whole groups | the rows of the groups that pass a test |
| `pd.Grouper` | Keys that are not in the table | a time key with a frequency, in the zone of the column |
| `pdbook.summary.subscriber_summary` | Build: subscriber_summary | one row for each subscriber, zeros for no calls |

## What you have now

- You pick `agg`, `transform` or `filter` from the shape of the result you want.
- You write named aggregations, and you use boolean columns as counters.
- You check that the groups add up to the table.
- You know that a group key can be a Series that is not a column, and that the zone of a timestamp decides the day.
- You have a summary table with one row for each subscriber.

The next chapter joins this summary with other tables, and shows how a join can silently multiply rows.

Next: [Chapter 9, Joins](09-joins.md).
