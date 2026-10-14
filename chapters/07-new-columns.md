# 7. New columns

> **Build** — `rate_vector(calls, subs, plans)`: a function that prices each call from three tables, written with whole-column operations, with a proof that a loop and an `apply` give the same bill and are slower by a measured factor.
>
> **Theory kept** — A column operation runs once in compiled code. A function that you pass to `apply` runs once for each row in Python. Write the rule as a column expression, and keep `apply` for the cases that have no column form.
>
> **Source** — New. Library: [`pdbook/rating.py`](../pdbook/rating.py).
>
> **Run this first** — `uv run python -m examples.ch07_new_columns`, which is [`examples/ch07_new_columns.py`](../examples/ch07_new_columns.py). Exercises: [`exercises/07.md`](../exercises/07.md). Solutions: [`exercises/solutions/07.md`](../exercises/solutions/07.md).

## Add a column

The plain form assigns to a new name. The `assign` method returns a new DataFrame and leaves the original as it was, so it fits in a chain ([Chapter 16](16-method-chains-and-pipelines.md)):

```python
import numpy as np

from pdbook.io import load_calls

calls = load_calls()
calls["minutes"] = np.ceil(calls["duration_s"] / 60)
with_hour = calls.assign(hour=lambda d: d["start"].dt.hour)
print(calls.columns.tolist()[-1], with_hour.columns.tolist()[-1])
print(calls.shape, with_hour.shape)
print("hour" in calls.columns)
```

```text
minutes hour
(20000, 10) (20000, 11)
False
```

`calls["minutes"] = ...` changed `calls`. `calls.assign(hour=...)` made a new table, and `calls` has no `hour` column. Both work on the whole column at once. The lambda in `assign` receives the table at that point of the chain. A later step can use a column that an earlier step made.

#### `pd.DataFrame.assign`

```text
pd.DataFrame.assign(
    self,
    **kwargs,
)
```

The method returns a new table with the new or changed columns. The table that you call it on does not change.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `**kwargs` | — | one keyword for each column: `name=value`. A value can be a constant, a Series, an array or a function of the table. The functions run in order, so `c=lambda d: d["b"] + 1` can use a `b` made one keyword earlier | a Series aligns on the index: a Series with the labels 1 and 2 on a table with the labels 0 and 1 gives `NaN` in row 0. A name with a space needs `**{"my col": ...}` |

## The index decides where values go

When you assign a Series, pandas aligns it to the index of the table. It does not use the order:

```python
import pandas as pd

from pdbook.io import load_calls

part = load_calls().head(5).copy()
part["z"] = pd.Series([10, 20, 30], index=[3, 4, 99])
print(part["z"].tolist())

part["w"] = [10, 20, 30, 40, 50]
print(part["w"].tolist())
try:
    part["v"] = [1, 2, 3]
except ValueError as error:
    print("ValueError:", str(error)[:50])
```

```text
[nan, nan, nan, 10.0, 20.0]
[10, 20, 30, 40, 50]
ValueError: Length of values (3) does not match length of inde
```

The first assignment puts 10 on index 3 and 20 on index 4. Index 99 does not exist, so its value is dropped, and the other three rows get `NaN`. A list does not align. It goes by position, and it must have the right length. When two tables have the same rows in a different order, a Series goes by label and a list goes by position. The two give different columns, and neither gives an error.

## Conditions

Four tools make a column from a condition. Use the first one that fits:

| Need | Tool |
|---|---|
| keep or replace on one condition | `where(cond, other)` or `mask(cond, other)` |
| several conditions, first match wins | `np.select(conditions, choices, default)` |
| numbers into labelled ranges | `pd.cut(x, bins, labels)` |
| a lookup of a value in a table | `Series.map(dict)` |

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

d = load_calls()["duration_s"]
status = load_calls()["status"]

only_positive = d.where(d > 0)
band = np.select(
    [d.isna(), d.eq(0), d.lt(30), d.lt(300)],
    ["none", "unanswered", "short", "normal"],
    default="long",
)
cut = pd.cut(d, [-0.5, 0.5, 29.5, 299.5, np.inf], labels=["unanswered", "short", "normal", "long"])
sign = status.map({"answered": 1, "busy": 0, "noanswer": 0})

print(int(only_positive.isna().sum()))
print(pd.Series(band).value_counts().to_dict())
print(cut.value_counts(dropna=False).to_dict())
print(int(sign.isna().sum()))
```

```text
4474
{'normal': 11578, 'unanswered': 3441, 'short': 2487, 'long': 1461, 'none': 1033}
{'normal': 11578, 'unanswered': 3441, 'short': 2487, 'long': 1461, nan: 1033}
1033
```

Read the results. `where(d > 0)` keeps the positive durations and makes 4,474 values `NaN`: the 3,441 zeros and the 1,033 nulls. `np.select` takes the first condition that is true, so the order of the conditions is part of the rule. Put `isna` first, because `NaN < 30` is `False` and the null falls to the default `long`.

`pd.cut` gives a category and leaves the nulls as `NaN`, and `np.select` gives text with a label of your choice for them. `map` with a dict gives `NaN` for a key that is not in the dict: `failed` is missing from the dict above, and 1,033 values are `NaN`. This is the correct behavior and a trap, so check `isna().sum()` after a `map`.

The block used five callables. Their signatures and parameters follow.

#### `pd.Series.where`

```text
pd.Series.where(
    self,
    cond,
    other=<no_default>,
    *,
    inplace=False,
    axis=None,
    level=None,
)
```

The method keeps each value where `cond` is `True` and replaces it where `cond` is `False`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `cond` | required | a boolean Series, an array of the same length, or a function of the Series | a Series with other labels aligns: a label that `cond` does not have counts as `False`. A list of the wrong length raises `ValueError` |
| `other` | `<no_default>` | the value for the rows where `cond` is `False`: a value, a Series or a function. Not set means `NaN` | without `other`, an `int64` Series becomes `float64`, because it must hold `NaN`. `where(d > 0)` makes 4,474 values `NaN` |
| `inplace` | `False` | with `True`, change the Series and return `None` | — |
| `axis` | `None` | for a DataFrame, the axis on which to align `cond` and `other`. Not used for a Series | — |
| `level` | `None` | for a MultiIndex, the level on which to align | — |

#### `pd.Series.mask`

```text
pd.Series.mask(
    self,
    cond,
    other=<no_default>,
    *,
    inplace=False,
    axis=None,
    level=None,
)
```

The method is the opposite of `where`: it replaces each value where `cond` is `True`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `cond` | required | the rows to replace | the same alignment as `where` |
| `other` | `<no_default>` | the new value. Not set means `NaN` | the same upcast to `float64` as `where` |
| `inplace` | `False` | with `True`, change the Series and return `None` | — |
| `axis` | `None` | for a DataFrame, the axis on which to align | — |
| `level` | `None` | for a MultiIndex, the level on which to align | — |

#### `np.select`

```text
np.select(
    condlist,
    choicelist,
    default=0,
)
```

The NumPy function returns an array with, for each row, the choice of the first condition that is true.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `condlist` | required | a list of boolean arrays or Series | `isna` must come first, because `NaN < 30` is `False` and the null would fall through to `default` |
| `choicelist` | required | a list of values or arrays, one for each condition | a list of another length raises `ValueError` |
| `default` | `0` | the value where no condition is true | with text choices, the default `0` raises `TypeError` on NumPy 2.5: give a text `default`. The result is a NumPy array, not a Series, and it has no index |

#### `pd.cut`

```text
pd.cut(
    x,
    bins,
    right=True,
    labels=None,
    retbins=False,
    precision=3,
    include_lowest=False,
    duplicates='raise',
    ordered=True,
)
```

The function puts each number in an interval and returns a category.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `x` | required | the numbers, one-dimensional | a value outside all the bins becomes `NaN`, with no message |
| `bins` | required | the edges of the intervals, or a number of intervals of equal width | edges `[0, 5, 10]` exclude 0: `(0, 5]` does not hold it, and 0 becomes `NaN` |
| `right` | `True` | `True` gives intervals `(a, b]`, `False` gives `[a, b)` | — |
| `labels` | `None` | the names of the intervals, one fewer than the edges. `False` gives the interval number | a list of the wrong length raises `ValueError` |
| `retbins` | `False` | `True` also returns the edges. Use it when `bins` is a number | the result is a tuple, not a Series |
| `precision` | `3` | the number of digits in the names of the intervals | the names are rounded and the bins are not. With `bins=[0.1216, 1.0556]` and `precision=1`, the interval is named `(0.1, 1.1]`, and 1.08 still becomes `NaN` |
| `include_lowest` | `False` | with `True`, the first interval holds its left edge | without it, the smallest edge is outside every interval |
| `duplicates` | `'raise'` | `'raise'` or `'drop'` for repeated edges | edges `[0, 5, 5, 10]` raise `ValueError`. `'drop'` makes two intervals |
| `ordered` | `True` | the category is ordered. `False` allows a label twice | `ordered=False` without `labels` raises `ValueError` |

#### `pd.Series.map`

```text
pd.Series.map(
    self,
    func=None,
    na_action=None,
    engine=None,
    **kwargs,
)
```

The method returns a new Series with each value replaced through a dict, a Series or a function.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | `None` | a dict, a Series or a function of one value | a key not in the dict gives `NaN`: 1,033 for `failed`. A `defaultdict` gives its default instead |
| `na_action` | `None` | `'ignore'` passes a missing value through and does not call the function on it | without it, the function receives `NaN`: `lambda v: v.upper()` raises `AttributeError` |
| `engine` | `None` | a compiler for the function, such as Numba. `None` runs Python | with a dict, any `engine` raises `ValueError` |
| `**kwargs` | — | more keyword arguments for the function | — |

## The three speeds

A bill needs a rule with a condition, a rounding, and a lookup in two tables. Only answered calls are billed. The billed time is the duration rounded up to whole minutes, with a minimum of one minute. The price per minute depends on the plan of the caller. Here are three ways to write it. All three are in [`pdbook/rating.py`](../pdbook/rating.py).

The loop is the way that a programmer writes it first:

```python
import math


def rate_loop(calls, subs, plans):
    plan_of = dict(zip(subs["subscriber_id"], subs["plan"]))
    rate_of = dict(zip(plans["plan"], plans["rate_per_min_eur"]))
    out = []
    for _, row in calls.iterrows():
        if row["status"] != "answered":
            out.append(0.0)
            continue
        minutes = max(1, math.ceil(row["duration_s"] / 60))
        out.append(round(minutes * rate_of[plan_of[row["caller"]]], 2))
    return out
```

The `apply` form is the same function body, handed to pandas. Pandas still calls it once for each row. The vectorized form states the rule for whole columns:

```python
import numpy as np


def rate_vector(calls, subs, plans):
    plan_of = dict(zip(subs["subscriber_id"], subs["plan"]))
    rate_of = dict(zip(plans["plan"], plans["rate_per_min_eur"]))
    rate = calls["caller"].map(plan_of).map(rate_of)
    minutes = np.maximum(1, np.ceil(calls["duration_s"] / 60))
    cost = (minutes * rate).where(calls["status"] == "answered", 0.0)
    return cost.round(2)
```

Now run all three, check that they agree, and time them. The assertion at the end is part of the chapter: it fails if the vectorized form is not at least ten times faster than the loop on your machine.

```python
import time

import pandas as pd

from pdbook.io import load_calls, load_plans, load_subscribers
from pdbook.rating import rate_apply, rate_loop, rate_vector

calls, subs, plans = load_calls(), load_subscribers(), load_plans()


def best_of(fn, repeat):
    best, result = float("inf"), None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn(calls, subs, plans)
        best = min(best, time.perf_counter() - t0)
    return best, result


t_loop, r_loop = best_of(rate_loop, 1)
t_apply, r_apply = best_of(rate_apply, 1)
t_vec, r_vec = best_of(rate_vector, 5)

pd.testing.assert_series_equal(r_loop, r_vec)
pd.testing.assert_series_equal(r_apply, r_vec)
print(f"loop {t_loop:.3f}s  apply {t_apply:.3f}s  vector {t_vec:.4f}s")
print(f"loop/vector {t_loop / t_vec:.0f}x  apply/vector {t_apply / t_vec:.0f}x")
print(f"total bill {r_vec.sum():,.2f}")
assert t_loop / t_vec > 10 and t_apply / t_vec > 3
```

```text
# output varies
loop 0.601s  apply 0.179s  vector 0.0090s
loop/vector 67x  apply/vector 20x
total bill 4,245.09
```

The block prints the times of one run. The assertion at the end of the block checks the order of magnitude: the loop must be more than 10 times slower than the column form, and `apply` more than 3 times slower. The ratios depend on the machine and on the load at that moment, and they depend on the number of rows. The first exercise measures how.

The bill is the same in all three: 4,245.09 euros over 15,526 billed calls. The `assert_series_equal` lines prove it, and so you can use the fast form with the same trust.

The three functions are in [`pdbook/rating.py`](../pdbook/rating.py). They take the same three tables and return the same Series.

#### `pdbook.rating.rate_vector`

```text
pdbook.rating.rate_vector(
    calls,
    subs,
    plans,
)
```

The function returns the cost of each call in euros, from whole columns.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | — |
| `subs` | required | the subscribers, with `subscriber_id` and `plan` | a caller that is not in `subs` gets the cost `NaN`, and the sum of the bill skips it with no message. Check `isna().sum()` |
| `plans` | required | the plans, with `plan` and `rate_per_min_eur` | — |

#### `pdbook.rating.rate_apply`

```text
pdbook.rating.rate_apply(
    calls,
    subs,
    plans,
)
```

The function returns the same bill with `apply(axis=1)`: one Python call for each row.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | — |
| `subs` | required | the subscribers | a caller that is not in `subs` raises `KeyError` |
| `plans` | required | the plans | — |

#### `pdbook.rating.rate_loop`

```text
pdbook.rating.rate_loop(
    calls,
    subs,
    plans,
)
```

The function returns the same bill with a loop over `iterrows`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | — |
| `subs` | required | the subscribers | a caller that is not in `subs` raises `KeyError` |
| `plans` | required | the plans | — |

## Why the loop is slow

`iterrows` builds a Series for every row. The block in the section on how it works prints its type. The dtype of such a row is the dtype that holds all the columns, which is `object` for a table with text. That Series is a new Python object.

The loop body then runs bytecode for each of 20,000 rows. `apply(axis=1)` does the same without the loop in your code. The vectorized form calls NumPy once, and NumPy loops in C over a contiguous array.

You can tell the difference by its shape. A vectorized operation names columns and never names a row. If you write `for` or `row[...]` over a table, ask first whether a column expression says the same.

## When apply is the right tool

Some work has no column form: a function from a library that takes one value, or a parser that reads a nested record. Then `apply` or `map` on one column is fine. It is fast enough when the column is small or when the function is the slow part:

```python
import pandas as pd

from pdbook.io import load_calls

caller = load_calls()["caller"]
number = caller.map(lambda s: int(s[1:]))
print(number.head(3).tolist(), number.dtype)
print(caller.str[1:].astype(int).equals(number))
```

```text
[125, 108, 414] int64
True
```

The second line shows that `.str[1:].astype(int)` gives the same result without a Python function. Try the column form first. When you must use `apply`, prefer `Series.map` or `Series.apply` over `DataFrame.apply(axis=1)`, because a column holds one type, and a row holds a mix.

#### `pd.DataFrame.apply`

```text
pd.DataFrame.apply(
    self,
    func,
    axis=0,
    raw=False,
    result_type=None,
    args=(),
    by_row='compat',
    engine=None,
    engine_kwargs=None,
    **kwargs,
)
```

The method calls `func` on each column, or with `axis=1` on each row, and combines the results.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | required | a function of a Series, a name such as `"sum"`, or a list of them | — |
| `axis` | `0` | `0` calls `func` on each column, `1` on each row | `axis=1` calls `func` 20,000 times, more than 10 times slower than the column form (asserted) |
| `raw` | `False` | `True` passes a NumPy array, not a Series, to `func` | with `True`, `func` cannot use names such as `row["a"]` |
| `result_type` | `None` | for `axis=1`: `'expand'` turns a list result into columns, `'reduce'` keeps one value, `'broadcast'` keeps the shape | without it, a list result stays a list in each cell |
| `args` | `()` | more positional arguments for `func` | — |
| `by_row` | `'compat'` | only for a list or dict of functions: `False` passes the whole column | — |
| `engine` | `None` | a compiler, such as Numba. `None` runs Python | `engine="numba"` raises `ImportError` here |
| `engine_kwargs` | `None` | options for the engine | — |
| `**kwargs` | — | more keyword arguments for `func` | — |

A row from `apply(axis=1)` is one Series, and a Series has one dtype. A row of the call records has the dtype `object`. A row with an `int64` and a `float64` column makes the integer a float. The function receives other types than the columns have.

## Build: the bill

`rate_vector` is the function to keep. The test that makes it trustworthy is the comparison with the loop on a sample. A loop is slow, so use a small sample, and use a loop that is easy to read:

```python
import pandas as pd

from pdbook.io import load_calls, load_plans, load_subscribers
from pdbook.rating import rate_loop, rate_vector

calls, subs, plans = load_calls(), load_subscribers(), load_plans()
sample = calls.sample(1000, random_state=0)
pd.testing.assert_series_equal(rate_loop(sample, subs, plans), rate_vector(sample, subs, plans))

bill = rate_vector(calls, subs, plans)
by_plan = bill.groupby(calls["caller"].map(dict(zip(subs["subscriber_id"], subs["plan"])))).sum().round(2)
print(by_plan.to_dict())
print(round(float(bill.sum()), 2))
```

```text
{'basic': 1399.7, 'business': 193.72, 'plus': 563.22, 'prepaid': 2088.45}
4245.09
```

The sample test uses the real rule on 1,000 random rows, and it passes. The bill by plan adds up to the total, which is the check that every call has a plan. A call whose caller is not in `subs` has a missing plan, and the group total is less than the full total.

## How it works

A column operation is one call into compiled code. NumPy takes the array, loops over it in C, and returns a new array. A function that you give to `apply(axis=1)` is different: pandas builds a Series for each row, calls your Python function once for each row, and collects the results. The cost of a Python call (a few hundred nanoseconds, plus the Series) is paid 20,000 times. The speed ratios of this chapter are the price of that call, repeated.

You can count the calls:

```python
import numpy as np

from pdbook.io import load_calls

calls = load_calls()
seen = {"row": 0, "column": 0}


def per_row(row):
    seen["row"] += 1
    seen["type"] = f"{type(row).__name__}, dtype {row.dtype}"
    return float(np.ceil(row["duration_s"] / 60)) if row["status"] == "answered" else 0.0


def per_column(duration_s):
    seen["column"] += 1
    return np.ceil(duration_s / 60)


by_row = calls.apply(per_row, axis=1)
by_column = per_column(calls["duration_s"])

print(len(calls), seen)
print(calls["duration_s"].to_numpy().flags["C_CONTIGUOUS"], calls["duration_s"].to_numpy().dtype)
answered = calls["status"] == "answered"
print(bool(np.array_equal(by_row[answered].to_numpy(), by_column[answered].to_numpy())))
```

```text
20000 {'row': 20000, 'column': 1, 'type': 'Series, dtype object'}
True float64
True
```

The row version called the function 20,000 times, one call for each row. The column version called it once, and the loop ran inside NumPy over a contiguous array of `float64`. The third line shows that the two give the same values for the answered calls. (The rows that are not answered differ on purpose in this example, because the row function returns 0 for them.)

- **Invariant.** A column operation calls the function once and loops in compiled code. `apply(axis=1)` calls it once for each row.
- **Failure.** A rule with `if` and `for` over rows. Rewrite it with `where`, `np.select` or `map`.
- **Cost.** The call count. 20,000 calls here, and the speed ratio of this chapter is the price of those calls.

`np.select` has a rule too: the first true condition wins. A chain of `np.where` calls gives the same result. Write it from the last condition back to the first, with `default` at the end. The next block builds the chain and compares it with `np.select` on the bands of this chapter:

```python
import numpy as np

from pdbook.io import load_calls

d = load_calls()["duration_s"]
conditions = [d.isna(), d.eq(0), d.lt(30), d.lt(300)]
choices = ["none", "unanswered", "short", "normal"]

chain = np.full(len(d), "long", dtype=object)
for cond, choice in reversed(list(zip(conditions, choices))):
    chain = np.where(cond, choice, chain)

selected = np.select(conditions, choices, default="long")
print(bool((chain == selected).all()))

swapped = np.select([d.lt(30), d.isna(), d.eq(0), d.lt(300)],
                    ["short", "none", "unanswered", "normal"], default="long")
print(int((swapped != selected).sum()), sorted(set(selected[swapped != selected].tolist())))
```

```text
True
3441 ['unanswered']
```

The chain and `np.select` agree on all 20,000 rows. The first condition is the last `np.where` to write, so it overwrites all the others. This is why the order of the conditions is part of the rule. The last line puts `lt(30)` first. The 3,441 zero durations are less than 30 too, so they become `short` and not `unanswered`. The nulls stay `none`, because `NaN < 30` is `False`.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.assign` | Add a column | a new table with new columns; functions see the earlier ones |
| `pd.Series.where` | Conditions | keep where the condition is true, else `other` or `NaN` |
| `pd.Series.mask` | Conditions | replace where the condition is true |
| `np.select` | Conditions | the choice of the first true condition, as a NumPy array |
| `pd.cut` | Conditions | numbers into labelled intervals, as a category |
| `pd.Series.map` | Conditions | each value through a dict, a Series or a function; unknown keys give `NaN` |
| `pd.DataFrame.apply` | When apply is the right tool | a function on each column, or with `axis=1` on each row |
| `pdbook.rating.rate_vector` | The three speeds | the bill from whole columns |
| `pdbook.rating.rate_apply` | The three speeds | the same bill with `apply(axis=1)` |
| `pdbook.rating.rate_loop` | The three speeds | the same bill with `iterrows` |

## What you have now

- You add columns with `[...]` and `assign`, and you know that a Series assigns by index.
- You make conditional columns with `where`, `np.select`, `pd.cut` and `map`, and you check the nulls after each one.
- You write a rule as a column expression, and you can show that a loop gives the same answer.
- You know the measured cost of `iterrows` and `apply`, and when `apply` is the right tool.

The next chapter turns the bill and the calls into a report with one row per subscriber.

Next: [Chapter 8, Group by](08-group-by.md).
