# 5. Missing data

> **Build** — `null_report(df)` and `determinants(df)`: a count of the nulls in each column, and a test that finds the columns that decide whether a value is missing. A null that a column decides is a fact. A null that nothing decides is lost data.
>
> **Theory kept** — A missing value has a cause, and the right treatment depends on the cause. Most aggregations skip missing values. `groupby` drops rows with a missing key. `NaN` is not equal to `NaN`.
>
> **Source** — New. Library: [`pdbook/nulls.py`](../pdbook/nulls.py).
>
> **Run this first** — `uv run python -m examples.ch05_missing`, which is [`examples/ch05_missing.py`](../examples/ch05_missing.py). Exercises: [`exercises/05.md`](../exercises/05.md). Solutions: [`exercises/solutions/05.md`](../exercises/solutions/05.md).

## Three kinds of missing

[Chapter 1](01-series-and-dataframe.md) found 1,033 nulls in `duration_s`, 277 in `cell_id` and 4,474 in `codec`. The three columns look the same in `info()`. They are not the same problem:

- In these data, a call with the status `failed` never started. It has no duration. The value does not exist.
- A call that was not answered has no codec, because no media flowed. The value does not exist.
- A call that was answered over a cell has a cell. If the record has none, the record lost it. The value exists, and we do not know it.

The first two are facts about the call. The third is damage. A good analysis treats them differently. Fill the first two with a value only if the question needs it. Never fill the third with a guess without saying so.

## How pandas marks a missing value

| dtype | Marker | `x == x` |
|---|---|---|
| `float64` | `NaN` | `False` |
| `str` | `NaN` | `False` |
| `datetime64` | `NaT` | `False` |
| `Int64`, `boolean`, `string` | `<NA>` | `<NA>` |
| `object` | `None` or `NaN` | `False` |

The next block checks the table. For each dtype it makes a Series with one missing value, and prints the marker and the result of `x == x`:

```python
import numpy as np
import pandas as pd

cases = {
    "float64": pd.Series([np.nan]),
    "str": pd.Series([None], dtype="str"),
    "datetime64": pd.Series([pd.NaT]),
    "Int64": pd.Series([None], dtype="Int64"),
    "boolean": pd.Series([None], dtype="boolean"),
    "string": pd.Series([None], dtype="string"),
    "object": pd.Series([None], dtype=object),
}
for name, s in cases.items():
    print(f"{name:10s} {str(s.iloc[0]):5s} x == x: {str((s == s).iloc[0]):5s} isna: {s.isna().iloc[0]}")
```

```text
float64    nan   x == x: False isna: True
str        nan   x == x: False isna: True
datetime64 NaT   x == x: False isna: True
Int64      <NA>  x == x: <NA>  isna: True
boolean    <NA>  x == x: <NA>  isna: True
string     <NA>  x == x: <NA>  isna: True
object     None  x == x: False isna: True
```

`isna()` and `notna()` work on all of them. Use these two methods and never compare with `== np.nan`, because `NaN` is not equal to itself:

```python
import numpy as np
import pandas as pd

print(np.nan == np.nan)
print(pd.Series([np.nan, 1.0]).eq(np.nan).tolist())
print(pd.Series([np.nan, 1.0]).isna().tolist())
```

```text
False
[False, False]
[True, False]
```

The comparison with `NaN` is `False` for every row, including the row that holds `NaN`. `isna()` is the reliable test.

## Count them, then ask why

The two functions in `pdbook/nulls.py` answer two questions. `null_report` counts. `determinants` tests whether another column decides the null. Run them on the call records:

```python
from pdbook.io import load_calls
from pdbook.nulls import determinants, null_report

calls = load_calls()
print(null_report(calls))
print(determinants(calls))
```

```text
            nulls   share
duration_s   1033  0.0516
cell_id       277  0.0138
codec        4474  0.2237
{'duration_s': ['status'], 'cell_id': [], 'codec': ['status']}
```

The result for `duration_s` and `codec` is `['status']`. The result for `cell_id` is an empty list. Look at the idea behind the function. A column `by` decides a column `col` when, in each group of `by`, the nulls of `col` are all or none. You can see it by hand:

```python
from pdbook.io import load_calls

calls = load_calls()
share = calls.groupby("status")[["duration_s", "codec", "cell_id"]].agg(lambda s: s.isna().mean())
print(share.round(3).to_string())
```

```text
          duration_s  codec  cell_id
status                              
answered         0.0    0.0    0.014
busy             0.0    1.0    0.014
failed           1.0    1.0    0.015
noanswer         0.0    1.0    0.014
```

In the `duration_s` column the share is 0 for three statuses and 1 for `failed`. In `codec` it is 0 for `answered` and 1 for the other three. The `cell_id` column has the same small share, about 1.4%, in each status.

`determinants` finds only exact relations. A weaker relation is invisible to it, and `groupby` shows it. Look at the share of lost cells for each codec:

```python
from pdbook.io import load_calls

calls = load_calls()
lost = calls["cell_id"].isna()
print((100 * lost.groupby(calls["codec"]).mean()).round(2).to_dict())
```

```text
{'AMR-NB': 2.09, 'AMR-WB': 1.61, 'EVS': 0.48}
```

The share is 0.48% for `EVS` and 2.09% for `AMR-NB`. A value that is lost "at random" does not do this. The cause is in the process that made the data. The generator chooses the codec from the technology of the cell. A call without a cell gets the choice for a 4G cell, where `EVS` is rare. A real table has the same kind of cause.

A step in the pipeline reads a field, and a missing field takes a default branch. The lesson has two parts. A null that no column decides can still be associated with a column. And the association points at the step that you must read.

## Aggregations skip nulls

Most reductions (`mean`, `sum`, `std`, `count`, `min`, `max`) skip missing values. `size` and `len` do not, because they count rows:

```python
from pdbook.io import load_calls

duration = load_calls()["duration_s"]
print(len(duration), duration.count())
print(round(duration.mean(), 2))
print(duration.mean(skipna=False))
print(round(duration.fillna(0).mean(), 2))
```

```text
20000 18967
108.73
nan
103.12
```

Three different means from one column. The skipping mean is 108.73. It divides by 18,967, the count of non-null values. The mean with `skipna=False` is `NaN`, because one unknown makes the whole mean unknown. The mean after `fillna(0)` is 103.12.

It divides by 20,000, and it treats the 1,033 failed calls as calls of length zero. None of the three is wrong. They answer different questions: "the mean duration of calls that have a duration", "the mean is unknown", and "the mean duration if a failed call counts as zero". Write the question in a comment next to the line.

## Fill, drop or keep

`fillna` replaces missing values. `dropna` removes rows. Before you use either, say what you lose.

```python
from pdbook.io import load_calls

calls = load_calls()
print(len(calls.dropna()))
print(len(calls.dropna(subset=["cell_id"])))
print(len(calls.dropna(how="all")))
print(len(calls.dropna(thresh=9)))
```

```text
15314
19723
20000
15314
```

`dropna()` with no arguments drops every row that has at least one null. Here it removes 4,686 rows, 23% of the table. Of these, 4,474 have a null `codec`, which means that the call was not answered. The other 212 are answered calls with a lost `cell_id`. The table that remains holds only answered calls.

The third call (`how="all"`) drops nothing, because no row is null in every column. The fourth call (`thresh=9`) keeps rows with at least 9 non-null values. The table has 9 columns, so it is the same as the first call. A report on "all calls" computed from it is a report on answered calls. Use `subset=` to name the columns whose nulls matter for your question.

## Group keys that are missing

`groupby` drops the rows whose key is missing, without a message:

```python
from pdbook.io import load_calls

calls = load_calls()
default = calls.groupby("cell_id")["call_id"].count()
keep = calls.groupby("cell_id", dropna=False)["call_id"].count()
print(int(default.sum()), int(keep.sum()), len(calls))
print(keep[keep.index.isna()].to_dict())
```

```text
19723 20000 20000
{nan: 277}
```

The default total is 19,723, and 277 calls are not in the report. With `dropna=False`, the missing key becomes one group and the total is 20,000. A report that adds up to less than the table is one of the most common silent errors in pandas. Check `sum()` of the groups against `len()` of the table.

## Time series: gaps

In a time series a missing value is often a missing row. The table `kpi.csv` has one row for each cell and each 5 minutes, and some rows are not in the file. Put the series on a full grid to see the gaps:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi()
cell = kpi[kpi["cell_id"] == "BRU-004"].drop_duplicates("ts").set_index("ts")["prb_util_pct"]
grid = pd.date_range(cell.index.min(), cell.index.max(), freq="5min")
full = cell.reindex(grid)
print(len(cell), len(full), int(full.isna().sum()))

gap = full.isna()
run_id = (gap != gap.shift()).cumsum()
longest = gap.groupby(run_id).sum().max()
print("longest gap:", int(longest), "steps =", int(longest) * 5, "minutes")
```

```text
822 864 42
longest gap: 24 steps = 120 minutes
```

The cell has 42 missing steps. The longest gap is 24 steps, which is two hours: the outage of the cell. Three tools fill a gap, and each makes a claim:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi()
cell = kpi[kpi["cell_id"] == "BRU-004"].drop_duplicates("ts").set_index("ts")["prb_util_pct"]
full = cell.reindex(pd.date_range(cell.index.min(), cell.index.max(), freq="5min"))

print("missing before     :", int(full.isna().sum()))
print("ffill(limit=3)     :", int(full.ffill(limit=3).isna().sum()))
print("interpolate(limit=3):", int(full.interpolate(limit=3).isna().sum()))
print("interpolate()      :", int(full.interpolate().isna().sum()))
```

```text
missing before     : 42
ffill(limit=3)     : 21
interpolate(limit=3): 21
interpolate()      : 0
```

`ffill` repeats the last value: "the load did not change". `interpolate` draws a line between the two ends: "the load changed steadily".

Both are claims about a period in which you have no data. Use `limit` to fill short gaps (one lost sample) and to leave long gaps (an outage) visible. The last line fills all 42 steps, including the two-hour outage with a straight line. The result looks like a measurement, and it is not one.

## Three-valued logic

The nullable dtypes follow the rules of SQL. An unknown value in a condition gives an unknown result, unless the other side decides the result:

```python
import pandas as pd

a = pd.array([True, False, None], dtype="boolean")
print((a | True).tolist())
print((a & False).tolist())
print((a | pd.NA).tolist())
```

```text
[True, True, True]
[False, False, False]
[True, <NA>, <NA>]
```

"Unknown or true" is true, because one side is enough. "Unknown and false" is false. "Unknown or unknown" is unknown. A mask that contains `<NA>` cannot select rows, so you must decide with `fillna(False)` or `fillna(True)`, and the choice is part of your question.

## How it works

A missing value needs a place in memory. A `float64` array has one: `NaN` is a special bit pattern of the IEEE 754 standard. By the rules of the standard it is not equal to any number, itself included. An integer array has no such pattern, because every bit pattern of an `int64` is a number.

This is why a column of whole numbers that gets a null becomes `float64`. The nullable types (`Int64`, `boolean`) solve it in another way: they keep the values in an array and add a second array of booleans, the mask, that says which positions are missing.

All of this is visible with a few lines:

```python
import numpy as np
import pandas as pd

s = pd.Series([1.0, np.nan, 3.0])
print((s != s).tolist(), s.isna().tolist())
print(np.array([1, 2, 3]).dtype, np.array([1, np.nan, 3]).dtype)

whole = pd.array([1, 2, 3], dtype="int64")
nullable = pd.array([1, None, 3], dtype="Int64")
print(nullable.isna().tolist(), nullable.to_numpy(dtype="float64", na_value=np.nan).tolist())
print(whole.nbytes, nullable.nbytes)
```

```text
[False, True, False] [False, True, False]
int64 float64
[False, True, False] [1.0, nan, 3.0]
24 27
```

The first line shows the test that `isna` uses for floats: a value that is not equal to itself is missing. The second line shows the upcast: one `nan` makes the NumPy array `float64`. The last line shows the price of the mask: 3 values need 24 bytes as `int64`, and 27 bytes as `Int64`, which is one more byte for each value.

- **Invariant.** A missing value is a property of a position: a special float, or a bit in a mask.
- **Failure.** A comparison with `==` does not find the missing values. The float is not equal to itself, and the mask gives `<NA>`.
- **Cost.** The nullable type needs one byte more for each value, and each result must combine with the mask.

## Reference

```python
import pandas as pd

from pdbook.nulls import determinants, null_report
from pdbook.sigs import show_signature

show_signature(pd.DataFrame.isna)
show_signature(pd.Series.fillna, ["value", "limit"])
show_signature(pd.DataFrame.dropna, ["axis", "how", "thresh", "subset"])
show_signature(pd.DataFrame.groupby, ["by", "dropna", "observed"])
show_signature(pd.Series.mean, ["skipna"])
show_signature(pd.Series.interpolate, ["method", "limit"])
show_signature(pd.Series.ffill, ["limit"])
show_signature(null_report)
show_signature(determinants)
```

```text
DataFrame.isna(
    self
)
NDFrame.fillna(
    value: 'Hashable | Mapping | Series | DataFrame'
    limit: 'int | None' = None
)  # 3 more parameters
DataFrame.dropna(
    axis: 'Axis' = 0
    how: 'AnyAll | lib.NoDefault' = <no_default>
    thresh: 'int | lib.NoDefault' = <no_default>
    subset: 'IndexLabel | AnyArrayLike | None' = None
)  # 3 more parameters
DataFrame.groupby(
    by=None
    observed: 'bool' = True
    dropna: 'bool' = True
)  # 5 more parameters
Series.mean(
    skipna: 'bool' = True
)  # 4 more parameters
NDFrame.interpolate(
    method: 'InterpolateOptions' = 'linear'
    limit: 'int | None' = None
)  # 6 more parameters
NDFrame.ffill(
    limit: 'None | int' = None
)  # 4 more parameters
null_report(
    df: 'pd.DataFrame'
)
determinants(
    df: 'pd.DataFrame'
    max_levels: 'int' = 12
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `isna()` | — | a boolean table: `True` where a value is missing | — |
| `fillna(value)` | required | the value to put in place of a missing value | `fillna(0)` on `duration_s` moves the mean from 108.73 to 103.12 |
| `fillna(limit=...)` | `None` | the largest number of values to fill in a row | — |
| `dropna(how=...)` | `any` when not set | `any` drops a row with one null, `all` drops a row with only nulls | `dropna()` removes 4,686 of 20,000 rows |
| `dropna(subset=...)` | `None` | look only at these columns | `subset=["cell_id"]` removes 277 rows |
| `dropna(thresh=...)` | not set | keep rows with at least this many values | `thresh=9` on 9 columns is the same as `how="any"` |
| `groupby(dropna=...)` | `True` | `False` keeps a group for the missing key | `True` loses 277 calls: totals of 19,723 against 20,000 |
| `groupby(observed=...)` | `True` | for category keys, show only the groups that occur | `False` gives a row for an empty category |
| `mean(skipna=...)` | `True` | `False` gives `NaN` when any value is missing | the mean of `duration_s` is `NaN` |
| `interpolate(method=..., limit=...)` | `'linear'`, `None` | fill a gap along the index | no `limit`: all 42 missing steps filled, the 2-hour outage included. `limit=3` leaves 21 |
| `ffill(limit=...)` | `None` | repeat the last value | `limit=3` leaves 21 of 42 |
| `null_report(df)` | required | nulls and their share, for each column that has any | — |
| `determinants(df, max_levels=12)` | `12` | for each column with nulls, the columns that decide it | finds exact relations only, not weaker ones |

`null_report` returns a DataFrame. `determinants` returns a dict of column name to a list of column names.

## What you have now

- You ask why a value is missing, and you test the answer with `determinants`.
- You know that the mean, the sum and the count skip nulls, and that `fillna(0)` changes the mean.
- You know that `dropna()` without `subset` can remove a quarter of a table.
- You check that group totals add up to the table, and you use `dropna=False` when a missing key matters.
- You fill gaps in time series with a limit.

The next chapter cleans the text and dates of a table that is damaged in many more ways.

Next: [Chapter 6, Text and date cleanup](06-text-and-date-cleanup.md).
