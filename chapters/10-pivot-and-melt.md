# 10. Pivot and melt

> **Build** — `traffic_grid(calls)`: a 7 by 24 table of the calls in each weekday and local hour, with `to_long` and `to_wide` that convert it to one row for each cell and back, and a test that the round trip changes nothing.
>
> **Theory kept** — A long table has one row for each observation. A wide table has one row for each entity and one column for each variable. Long is the form for `groupby`, for plots and for models. Wide is the form for the eye. `pivot_table` aggregates, `pivot` does not, and `melt` reverses.
>
> **Source** — New. Library: [`pdbook/traffic.py`](../pdbook/traffic.py).
>
> **Run this first** — `uv run python -m examples.ch10_pivot`, which is [`examples/ch10_pivot.py`](../examples/ch10_pivot.py). Exercises: [`exercises/10.md`](../exercises/10.md). Solutions: [`exercises/solutions/10.md`](../exercises/solutions/10.md).

## Long and wide

The call records are long: one row for each call. A traffic report is wide: one row for each weekday, one column for each hour. The same numbers are in both. Which form you need depends on the next step:

| You want to | Form |
|---|---|
| group, filter, join, fit a model | long |
| plot several series against one axis | long (or wide for `df.plot`) |
| read the numbers, compare columns | wide |
| write a report for a person | wide |

Most work is in long form, and a report ends in wide form. `pivot_table` goes from long to wide. `melt` goes from wide to long.

## pivot_table: aggregate and spread

A `pivot_table` needs three things: which column gives the rows, which gives the columns, and what to put in the cells.

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
local = calls["start"].dt.tz_convert("Europe/Brussels")
frame = pd.DataFrame({"weekday": local.dt.dayofweek, "hour": local.dt.hour, "status": calls["status"],
                      "duration_s": calls["duration_s"]})

counts = frame.assign(n=1).pivot_table(index="weekday", columns="hour", values="n",
                                       aggfunc="sum", fill_value=0)
print(counts.shape, int(counts.to_numpy().sum()))

mean_duration = frame.pivot_table(index="weekday", columns="status", values="duration_s")
print(mean_duration.round(1).loc[0].to_dict())
```

```text
(7, 24) 20000
{'answered': 143.0, 'busy': 0.0, 'noanswer': 0.0}
```

The first table has 7 rows and 24 columns, and its cells add up to 20,000. The default `aggfunc` is `mean`, and the second table uses it: the mean duration for each weekday and status. The printed row is Monday. The `NaN` for `failed` is not in the printed dict, because `failed` has no durations, so pandas dropped the column `failed` from the result. With `dropna=True`, the default, pandas drops a column that is all `NaN`.

Three arguments change the table:

- `aggfunc` takes a string, a function or a list. A list gives one block of columns for each function.
- `fill_value` replaces `NaN` for a combination that does not exist. Use `0` for counts.
- `margins=True` adds a row and a column `All` with the totals.

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
local = calls["start"].dt.tz_convert("Europe/Brussels")
frame = pd.DataFrame({"weekday": local.dt.dayofweek, "status": calls["status"], "call_id": calls["call_id"]})

t = frame.pivot_table(index="weekday", columns="status", values="call_id", aggfunc="count", margins=True)
print(t.loc["All"].to_dict())
print(t.loc[5].to_dict())
```

```text
{'answered': 15526, 'busy': 1428, 'failed': 1033, 'noanswer': 2013, 'All': 20000}
{'answered': 1360, 'busy': 129, 'failed': 81, 'noanswer': 175, 'All': 1745}
```

The row `All` gives the total of each status and the total of the table. A check: the last value is 20,000.

## crosstab: counts and shares

`pd.crosstab` is a `pivot_table` for counts of two columns. It has `normalize`, which turns counts into shares:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
share = pd.crosstab(calls["status"], calls["roaming"], normalize="columns").round(3)
print(share.to_dict())

n = int(calls["roaming"].sum())
p = float(share.loc["answered", True])
print(n, round(100 * (p * (1 - p) / n) ** 0.5, 1))
```

```text
{False: {'answered': 0.776, 'busy': 0.071, 'failed': 0.052, 'noanswer': 0.101}, True: {'answered': 0.79, 'busy': 0.082, 'failed': 0.055, 'noanswer': 0.073}}
563 1.7
```

Each column adds up to 1. Of the roaming calls, 79.0% are answered, against 77.6% of the other calls. The last line gives the number of roaming calls, 563, and the standard error of the share of 0.790 for that many calls: 1.7 points. The difference of 1.4 points is smaller than one standard error. This table does not show that roaming changes the chance of an answer.

## pivot: reshape without aggregating

`pivot` has no `aggfunc`. It assumes that each pair of row key and column key occurs once. When a pair occurs twice, there is no rule to choose, and it raises an error:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
local = calls["start"].dt.tz_convert("Europe/Brussels")
frame = pd.DataFrame({"weekday": local.dt.dayofweek, "hour": local.dt.hour, "call_id": calls["call_id"]})
try:
    frame.pivot(index="weekday", columns="hour", values="call_id")
except ValueError as error:
    print("ValueError:", error)
```

```text
ValueError: Index contains duplicate entries, cannot reshape
```

That error is useful. It says that the data are not in the shape that you assumed. Use `pivot` when you know the key is unique, so that a duplicate is a surprise, and use `pivot_table` when you want an aggregate.

## melt: wide to long

`melt` takes the columns of a wide table and stacks them into one column of values, with a second column for the old column names:

```python
import pandas as pd

wide = pd.DataFrame({"cell": ["A", "B"], "mon": [5, 7], "tue": [6, 9]})
long = wide.melt(id_vars="cell", var_name="day", value_name="calls")
print(long.to_dict("list"))
print(long.groupby("day")["calls"].sum().to_dict())
```

```text
{'cell': ['A', 'B', 'A', 'B'], 'day': ['mon', 'mon', 'tue', 'tue'], 'calls': [5, 7, 6, 9]}
{'mon': 12, 'tue': 15}
```

`id_vars` are the columns that stay. The other columns go into `day` and `calls`. After the `melt` the data work with `groupby`, and with a plotting library that wants one column of values and one column of groups.

There is a trap in the column names that come from a wide table of numbers. The new column holds the old labels, and the dtype can be `object`, even when the labels are integers:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.traffic import traffic_grid

grid = traffic_grid(load_calls())
long = grid.reset_index().melt(id_vars="weekday", var_name="hour", value_name="calls")
print(long["hour"].dtype)
print(long["hour"].astype("int64").dtype)
```

```text
object
int64
```

The `reset_index` put the text `weekday` and the integer hours in one set of column labels, so the labels became `object`. A later join with a table that has integer hours finds no match. Convert the column to the type that you want, immediately after the `melt`.

## stack and unstack

`unstack` moves an index level into the columns, and `stack` does the reverse. They work on an index, and they are the tool after a `groupby` with two keys:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
by = calls.groupby(["roaming", "status"]).size()
print(type(by.index).__name__, by.shape)
print(by.unstack().to_string())
print(by.unstack(level="roaming").shape)
```

```text
MultiIndex (8,)
status   answered  busy  failed  noanswer
roaming                                  
False       15081  1382    1002      1972
True          445    46      31        41
(4, 2)
```

A `groupby` with two keys gives a Series with a two-level index. `unstack` moves the last level to the columns, and `unstack(level="roaming")` moves the other one. [Chapter 11](11-index-and-multiindex.md) explains the index.

## Build: the traffic grid

`traffic_grid` makes the 7 by 24 table. It converts the zone first, because a call at 23:30 UTC is already the next day in Belgium. It reindexes to all 7 weekdays and 24 hours with zeros, so a missing combination is a 0 and the shape never changes:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.traffic import to_long, to_wide, traffic_grid

calls = load_calls()
grid = traffic_grid(calls)
long = to_long(grid)
print(grid.shape, int(grid.to_numpy().sum()) == len(calls))
print(long.shape, long.dtypes.astype(str).to_dict())

pd.testing.assert_frame_equal(to_wide(long), grid)
print("round trip equal")

busy = long.sort_values("calls", ascending=False).head(3)
print(busy.to_dict("records"))
print(grid.sum(axis=1).to_dict())
```

```text
(7, 24) True
(168, 3) {'weekday': 'str', 'hour': 'int64', 'calls': 'int64'}
round trip equal
[{'weekday': 'Tue', 'hour': 9, 'calls': 300}, {'weekday': 'Wed', 'hour': 19, 'calls': 288}, {'weekday': 'Wed', 'hour': 10, 'calls': 278}]
{'Mon': 2925, 'Tue': 3698, 'Wed': 3836, 'Thu': 3021, 'Fri': 3057, 'Sat': 1745, 'Sun': 1718}
```

The busiest cell is Tuesday at 09:00 with 300 calls. Wednesday at 19:00 follows with 288, and Wednesday at 10:00 with 278. Wednesday is the busiest day with 3,836 calls, and the weekend days have 1,745 and 1,718, which is about half. A person reads the grid with the eye, and a program reads the long form. The functions convert between them without loss, and the `assert_frame_equal` shows it.

## How it works

A `pivot_table` is a `groupby` followed by an `unstack`. The `groupby` reduces the table to one row for each pair of row key and column key. The `unstack` then moves the last index level into the columns. `melt` is the reverse: it moves the columns back into rows. The two directions are `unstack` and `stack` on the index, and `pivot_table` and `melt` are the names that work on columns.

You can build the traffic grid of this chapter in two lines and compare it with `traffic_grid`:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.traffic import to_long, traffic_grid

calls = load_calls()
local = calls["start"].dt.tz_convert("Europe/Brussels")
by_pair = calls.groupby([local.dt.dayofweek, local.dt.hour]).size()
print(type(by_pair.index).__name__, by_pair.shape)

grid = by_pair.unstack(fill_value=0)
reference = traffic_grid(calls)
print(grid.shape, bool((grid.to_numpy() == reference.to_numpy()).all()))

back = reference.stack()
print(back.shape, int(back.sum()), len(to_long(reference)))
```

```text
MultiIndex (168,)
(7, 24) True
(168,) 20000 168
```

The `groupby` gives a Series with a two-level index, one entry for each pair that occurs. The `unstack` makes the 7 by 24 grid, and the values are the same as `traffic_grid`. The `stack` of the grid gives 168 values, one for each cell, that add up to 20,000, and `to_long` has the same 168 rows.

- **Invariant.** A pivot table has one cell for each pair of keys, and it holds an aggregate of every row with that pair.
- **Failure.** A pair that occurs twice in `pivot` has no rule to follow, and it raises an error. In `pivot_table`, it is silently aggregated.
- **Cost.** The `groupby` pass plus a copy into the 2-D array. A wide result with many empty cells holds `NaN` or 0 for each one.

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.traffic import to_long, to_wide, traffic_grid

show_signature(pd.DataFrame.pivot_table, ["values", "index", "columns", "aggfunc", "fill_value", "margins", "dropna"])
show_signature(pd.DataFrame.pivot, ["columns", "index", "values"])
show_signature(pd.crosstab, ["index", "columns", "normalize"])
show_signature(pd.DataFrame.melt, ["id_vars", "value_vars", "var_name", "value_name"])
show_signature(pd.Series.unstack, ["level", "fill_value"])
show_signature(traffic_grid)
show_signature(to_long)
show_signature(to_wide)
```

```text
DataFrame.pivot_table(
    values=None
    index=None
    columns=None
    aggfunc: 'AggFuncType' = 'mean'
    fill_value=None
    margins: 'bool' = False
    dropna: 'bool' = True
)  # 5 more parameters
DataFrame.pivot(
    columns
    index=<no_default>
    values=<no_default>
)  # 1 more parameters
crosstab(
    index
    columns
    normalize: "bool | Literal[0, 1, 'all', 'index', 'columns']" = False
)  # 7 more parameters
DataFrame.melt(
    id_vars=None
    value_vars=None
    var_name=None
    value_name: 'Hashable' = 'value'
)  # 3 more parameters
Series.unstack(
    level: 'IndexLabel' = -1
    fill_value: 'Hashable | None' = None
)  # 2 more parameters
traffic_grid(
    calls: 'pd.DataFrame'
    tz: 'str' = 'Europe/Brussels'
)
to_long(
    grid: 'pd.DataFrame'
)
to_wide(
    long: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `pivot_table(values, index, columns)` | `None` | the cell, the row key and the column key | — |
| `pivot_table(aggfunc=...)` | `'mean'` | how to combine the rows of one cell | a duplicate row is added in silence: total 20,016 and not 20,000 |
| `pivot_table(fill_value=...)` | `None` | the value for a cell with no rows | — |
| `pivot_table(margins=...)` | `False` | `True` adds a row and a column `All` | — |
| `pivot_table(dropna=...)` | `True` | drop a column that is all `NaN` | the status `failed` disappears from a table of mean durations |
| `pivot(columns, index, values)` | `index`, `values`: not set | reshape with no aggregation | a pair that occurs twice raises `ValueError` |
| `crosstab(index, columns)` | required | counts of two columns | — |
| `crosstab(normalize=...)` | `False` | `"columns"` makes each column add up to 1 | — |
| `melt(id_vars, value_vars)` | `None` | the columns to keep and the columns to stack | — |
| `melt(var_name, value_name)` | `None`, `'value'` | names of the two new columns | `hour` comes back as `object`; convert it |
| `unstack(level, fill_value)` | `-1`, `None` | move an index level to the columns | a pair that does not occur is `NaN` |
| `traffic_grid(calls, tz=...)` | required, `'Europe/Brussels'` | the 7 by 24 table of calls | the grid in UTC differs in 164 of 168 cells |
| `to_wide(long)` | required | back to the grid | a repeated row raises `ValueError` |

`traffic_grid` returns a DataFrame indexed by weekday names with the columns 0 to 23. `to_long` returns 168 rows.

## What you have now

- You choose long or wide from the next step.
- You use `pivot_table` to aggregate, `pivot` to reshape a unique key, `crosstab` for counts and shares.
- You use `melt` to go back, and you fix the type of the new column at once.
- You use `stack` and `unstack` after a `groupby` with two keys.
- You have a traffic grid and a test that the round trip is exact.

The next chapter looks at the object that `unstack` and `groupby` left on the rows: the index.

Next: [Chapter 11, The index and MultiIndex](11-index-and-multiindex.md).
