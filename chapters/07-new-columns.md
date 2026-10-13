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
loop 0.583s  apply 0.169s  vector 0.0089s
loop/vector 65x  apply/vector 19x
total bill 4,245.09
```

The block prints the times of one run. The assertion at the end of the block checks the order of magnitude: the loop must be more than 10 times slower than the column form, and `apply` more than 3 times slower. The ratios depend on the machine and on the load at that moment, and they depend on the number of rows. The first exercise measures how.

The bill is the same in all three: 4,245.09 euros over 15,526 billed calls. The `assert_series_equal` lines prove it, and so you can use the fast form with the same trust.

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

## Reference

```python
import numpy as np
import pandas as pd

from pdbook.rating import rate_apply, rate_loop, rate_vector
from pdbook.sigs import show_signature

show_signature(pd.DataFrame.assign)
show_signature(pd.Series.where, ["cond", "other"])
show_signature(pd.Series.mask, ["cond", "other"])
show_signature(np.select, ["condlist", "choicelist", "default"])
show_signature(pd.cut, ["x", "bins", "labels", "right"])
show_signature(pd.Series.map, ["func", "na_action"])
show_signature(pd.DataFrame.apply, ["func", "axis"])
show_signature(rate_vector)
show_signature(rate_apply)
show_signature(rate_loop)
```

```text
DataFrame.assign(
    self
    **kwargs
)
NDFrame.where(
    cond
    other=<no_default>
)  # 4 more parameters
NDFrame.mask(
    cond
    other=<no_default>
)  # 4 more parameters
select(
    condlist
    choicelist
    default=0
)
cut(
    x
    bins
    right: 'bool' = True
    labels=None
)  # 5 more parameters
Series.map(
    func: 'Callable | Mapping | Series | None' = None
    na_action: "Literal['ignore'] | None" = None
)  # 3 more parameters
DataFrame.apply(
    func: 'AggFuncType'
    axis: 'Axis' = 0
)  # 8 more parameters
rate_vector(
    calls: 'pd.DataFrame'
    subs: 'pd.DataFrame'
    plans: 'pd.DataFrame'
)
rate_apply(
    calls: 'pd.DataFrame'
    subs: 'pd.DataFrame'
    plans: 'pd.DataFrame'
)
rate_loop(
    calls: 'pd.DataFrame'
    subs: 'pd.DataFrame'
    plans: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `assign(**kwargs)` | — | each keyword is a new column; a function gets the table at that point | — |
| `where(cond, other=...)` | not set | keep the values where `cond` is `True`; elsewhere put `other` or `NaN` | `where(d > 0)` makes 4,474 values `NaN` |
| `mask(cond, other=...)` | not set | the opposite of `where` | — |
| `np.select(condlist, choicelist, default=...)` | `0` | the first true condition decides | `isna` must come first, because `NaN < 30` is `False` |
| `pd.cut(x, bins, right=..., labels=...)` | `True`, `None` | numbers into labelled ranges, `(a, b]` for `right=True` | nulls stay `NaN` |
| `map(func, na_action=...)` | `None`, `None` | a dict or a function for each value | a key not in the dict gives `NaN`: 1,033 for `failed` |
| `apply(func, axis=...)` | required, `0` | `axis=1` calls `func` once for each row | 20,000 calls, and more than 10 times slower than the column form (asserted) |
| `rate_vector(calls, subs, plans)` | required | the bill for each call, from whole columns | — |
| `rate_apply(calls, subs, plans)` | required | the same bill with `apply(axis=1)` | — |
| `rate_loop(calls, subs, plans)` | required | the same bill with `iterrows` | — |

The three `rate_` functions return a Series named `cost_eur` with the index of `calls`, and they give equal results.

## What you have now

- You add columns with `[...]` and `assign`, and you know that a Series assigns by index.
- You make conditional columns with `where`, `np.select`, `pd.cut` and `map`, and you check the nulls after each one.
- You write a rule as a column expression, and you can show that a loop gives the same answer.
- You know the measured cost of `iterrows` and `apply`, and when `apply` is the right tool.

The next chapter turns the bill and the calls into a report with one row per subscriber.

Next: [Chapter 8, Group by](08-group-by.md).
