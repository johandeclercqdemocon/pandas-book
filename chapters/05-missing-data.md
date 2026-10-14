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

#### `pd.DataFrame.isna`

```text
pd.DataFrame.isna(
    self,
)
```

The method returns a table of the same shape, with `True` where a value is missing. It takes no parameters. The Series method is the same, and `notna` is its opposite. The sum of the result is the count of missing values in each column.

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

#### `pdbook.nulls.null_report`

```text
pdbook.nulls.null_report(
    df,
)
```

The function returns one row for each column that has a missing value: the count and the share.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | any DataFrame | a table with no missing value gives an empty table, not an error |

#### `pdbook.nulls.determinants`

```text
pdbook.nulls.determinants(
    df,
    max_levels=12,
)
```

The function returns, for each column with nulls, the columns of few distinct values that decide whether it is null.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | any DataFrame | it finds exact relations only, not weaker ones |
| `max_levels` | `12` | the largest number of distinct values for a column to be a candidate | with `max_levels=3`, `status` (4 values) is not tested, and every list is empty |

The method `groupby`, in the next block, has its signature and parameters in [Chapter 8](08-group-by.md), the chapter about groups.

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

#### `pd.Series.mean`

```text
pd.Series.mean(
    self,
    *,
    axis=0,
    skipna=True,
    numeric_only=False,
    **kwargs,
)
```

The method returns the mean of the values. The DataFrame method returns one mean for each column.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `axis` | `0` | not used for a Series. For a DataFrame, `0` gives a mean for each column and `1` for each row | — |
| `skipna` | `True` | skip the missing values. `False` gives `NaN` when any value is missing | the mean of `duration_s` is `NaN` with `skipna=False` |
| `numeric_only` | `False` | for a DataFrame, use only the number and boolean columns | `calls.mean()` raises `TypeError` on the text columns. `numeric_only=True` gives the means of `call_id`, `duration_s` and `roaming` |
| `**kwargs` | — | accepted for compatibility with NumPy. pandas does not use them | a name that pandas does not know raises `TypeError` |

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

#### `pd.DataFrame.dropna`

```text
pd.DataFrame.dropna(
    self,
    *,
    axis=0,
    how=<no_default>,
    thresh=<no_default>,
    subset=None,
    inplace=False,
    ignore_index=False,
)
```

The method returns the table without the rows, or the columns, that have missing values.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `axis` | `0` | `0` drops rows, `1` drops columns | `axis=1` drops `duration_s`, `cell_id` and `codec`: 3 of 9 columns |
| `how` | `<no_default>` | `'any'` drops a row with one null, `'all'` drops a row with only nulls. Not set means `'any'` | `dropna()` removes 4,686 of 20,000 rows |
| `thresh` | `<no_default>` | keep the rows with at least this many values | `thresh=9` on 9 columns is the same as `how="any"`. `how` and `thresh` together raise `TypeError` |
| `subset` | `None` | look only at these columns | `subset=["cell_id"]` removes 277 rows. A name that is not a column raises `KeyError` |
| `inplace` | `False` | with `True`, change the table and return `None` | — |
| `ignore_index` | `False` | with `True`, the result gets the labels 0, 1, 2 and so on | with `False`, the labels have holes: 0, 2, 3 |

#### `pd.Series.fillna`

```text
pd.Series.fillna(
    self,
    value,
    *,
    axis=None,
    inplace=False,
    limit=None,
)
```

The method returns the Series with each missing value replaced by `value`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `value` | required | the value to put in place of a missing value, or a dict of label to value | `fillna(0)` on `duration_s` moves the mean from 108.73 to 103.12. A string on a `float64` column makes it `object`, with no error. A list raises `TypeError` |
| `axis` | `None` | not used for a Series | — |
| `inplace` | `False` | with `True`, change the Series and return `None` | — |
| `limit` | `None` | the largest number of values to fill, counted along the whole Series | `limit=2` fills the first two missing values of the Series, not two in each gap. For a limit in each gap, use `ffill` or `interpolate` |

In pandas 3.0, `fillna` has no `method` argument. `fillna(method="ffill")` raises `TypeError`, and the method `ffill` below does that work.

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

#### `pd.Series.interpolate`

```text
pd.Series.interpolate(
    self,
    method='linear',
    *,
    axis=0,
    limit=None,
    inplace=False,
    limit_direction=None,
    limit_area=None,
    **kwargs,
)
```

The method fills the missing values with values on a line between the known values around them.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `method` | `'linear'` | how to compute the new values. `'linear'` treats the rows as equally spaced. `'index'` and `'time'` use the index | `'linear'` ignores the index: on the labels 0, 1, 2, 10 with values 1, gap, gap, 4 it gives 2 and 3. `method="index"` gives 1.3 and 1.6 |
| `axis` | `0` | not used for a Series | — |
| `limit` | `None` | the largest number of missing values in a row to fill | no `limit`: all 42 missing steps filled, the 2-hour outage included. `limit=3` leaves 21 |
| `inplace` | `False` | with `True`, change the Series and return `None` | — |
| `limit_direction` | `None` | `'forward'`, `'backward'` or `'both'`: the side from which to count `limit`. `None` means `'forward'` for `'linear'` | the default also fills after the last known value, by copying it: `[nan, 1, nan, nan, nan, 5, nan]` ends with 5.0. The first `nan` stays |
| `limit_area` | `None` | `'inside'` fills only the gaps between two known values. `'outside'` fills only the ends | `'inside'` leaves both ends as `nan` |
| `**kwargs` | — | more arguments for SciPy methods, such as `order` for `'polynomial'` | `method="polynomial"` needs SciPy, which this book does not install: `ImportError` |

#### `pd.Series.ffill`

```text
pd.Series.ffill(
    self,
    *,
    axis=None,
    inplace=False,
    limit=None,
    limit_area=None,
)
```

The method fills each missing value with the last known value before it.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `axis` | `None` | not used for a Series | — |
| `inplace` | `False` | with `True`, change the Series and return `None` | — |
| `limit` | `None` | the largest number of missing values in a row to fill | `limit=3` leaves 21 of 42 |
| `limit_area` | `None` | `'inside'` fills only between two known values. `'outside'` fills only after the last one | with the default, the gap after the last known value is filled too. A value that is no longer reported continues forever |

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

The logic of the nullable `boolean` type is a rule with three values, the logic of Kleene. Put false, unknown and true on a line as 0, 0.5 and 1. Then "or" is the larger of two values, and "and" is the smaller. The next block applies the rule to all nine pairs and compares it with pandas:

```python
import itertools

import pandas as pd

values = [True, False, None]
rank = {False: 0.0, None: 0.5, True: 1.0}
back = {0.0: False, 0.5: None, 1.0: True}

left, right = zip(*itertools.product(values, values))
a = pd.array(list(left), dtype="boolean")
b = pd.array(list(right), dtype="boolean")


def as_python(arr):
    return [None if v is pd.NA else bool(v) for v in arr]


rule_or = [back[max(rank[x], rank[y])] for x, y in zip(left, right)]
rule_and = [back[min(rank[x], rank[y])] for x, y in zip(left, right)]
print(as_python(a | b) == rule_or, as_python(a & b) == rule_and)
for x, y, o, n in zip(left, right, as_python(a | b), as_python(a & b)):
    print(f"{str(x):5s} {str(y):5s}  or {str(o):5s}  and {n}")

print(pd.Series([True, None], dtype="boolean").any(),
      pd.Series([False, None], dtype="boolean").any(),
      pd.Series([False, None], dtype="boolean").any(skipna=False))
```

```text
True True
True  True   or True   and True
True  False  or True   and False
True  None   or True   and None
False True   or True   and False
False False  or False  and False
False None   or None   and False
None  True   or True   and None
None  False  or None   and False
None  None   or None   and None
True False <NA>
```

The rule of the smaller and the larger value gives all nine results of pandas. An unknown value decides nothing when the other side is enough: "true or unknown" is true, and "false and unknown" is false. The last line shows the same logic in a reduction.

With `skipna=False`, "is any value true" over `[False, <NA>]` is `<NA>`: the unknown value can be true. The default skips the unknown value and says `False`.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.isna` | How pandas marks a missing value | a boolean table: `True` where a value is missing |
| `pdbook.nulls.null_report` | Count them, then ask why | count and share of nulls, for each column that has any |
| `pdbook.nulls.determinants` | Count them, then ask why | the columns that decide exactly whether a column is null |
| `pd.DataFrame.groupby` | Count them, then ask why ([Chapter 8](08-group-by.md) has the block) | groups of rows by the values of keys; a missing key is dropped by default |
| `pd.Series.mean` | Aggregations skip nulls | the mean of the values that are not missing |
| `pd.DataFrame.dropna` | Fill, drop or keep | the table without the rows that have nulls |
| `pd.Series.fillna` | Fill, drop or keep | each missing value replaced by one value |
| `pd.Series.interpolate` | Time series: gaps | a line through each gap, with an optional limit |
| `pd.Series.ffill` | Time series: gaps | the last known value repeated into each gap |

## What you have now

- You ask why a value is missing, and you test the answer with `determinants`.
- You know that the mean, the sum and the count skip nulls, and that `fillna(0)` changes the mean.
- You know that `dropna()` without `subset` can remove a quarter of a table.
- You check that group totals add up to the table, and you use `dropna=False` when a missing key matters.
- You fill gaps in time series with a limit.

The next chapter cleans the text and dates of a table that is damaged in many more ways.

Next: [Chapter 6, Text and date cleanup](06-text-and-date-cleanup.md).
