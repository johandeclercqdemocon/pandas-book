# 16. Method chains and pipelines

> **Build** — `monthly_report(calls, subs, cells, plans)`: the report of calls, answer rate, billed minutes and revenue for each plan and city, written as one chain with two checks inside it, and three tests that prove it: the total agrees with an independent computation, the result does not depend on the row order, and a planted fault stops it.
>
> **Theory kept** — A method chain is a pipeline of steps that each take a table and return a table, with no mutation. `assign` makes columns, `pipe` runs your own function, and a check is a step that returns its input or raises an error.
>
> **Source** — New. Library: [`pdbook/report.py`](../pdbook/report.py).
>
> **Run this first** — `uv run python -m examples.ch16_chain`, which is [`examples/ch16_chain.py`](../examples/ch16_chain.py). Exercises: [`exercises/16.md`](../exercises/16.md). Solutions: [`exercises/solutions/16.md`](../exercises/solutions/16.md).

## Why a chain

Compare two ways to write the same three steps:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()

# step by step, with a name for each state
df = calls[calls["status"] == "answered"]
df = df.assign(minutes=df["duration_s"] / 60)
by_codec = df.groupby("codec").agg(calls=("call_id", "size"), minutes=("minutes", "sum"))
print(by_codec.round(1).to_dict("index")["EVS"])

# the same, as one chain
by_codec2 = (
    calls
    .query("status == 'answered'")
    .assign(minutes=lambda d: d["duration_s"] / 60)
    .groupby("codec")
    .agg(calls=("call_id", "size"), minutes=("minutes", "sum"))
)
pd.testing.assert_frame_equal(by_codec, by_codec2)
print("equal")
```

```text
{'calls': 4791, 'minutes': 10564.6}
equal
```

The results are equal. The chain has three properties that the first form does not have:

- **Nothing is assigned twice.** The variable `df` in the first form means two different things. A cell that you run twice in a notebook gives a different result the second time. The chain has one name at the start and one at the end.
- **Each step reads as a verb.** A person who reads from the top knows the order of the work without searching for the assignments.
- **There is no state to leave behind.** A step cannot change the input table, and the input is as it was after the chain.

## The pieces

The methods that give you a chain are the ones that return a new object:

| Step | Method |
|---|---|
| keep rows | `query`, `loc[mask]`, `drop_duplicates`, `head` |
| make columns | `assign`, `rename`, `astype`, `where` |
| change shape | `groupby(...).agg`, `pivot_table`, `melt`, `merge` |
| order | `sort_values`, `reset_index`, `set_axis` |
| your own step | `pipe` |

`assign` takes a function when the column depends on the table as it is at that point of the chain. The lambda receives that table. The arguments of one `assign` are evaluated from left to right, so a later one can use an earlier one:

```python
import pandas as pd

from pdbook.io import load_calls

result = (
    load_calls()
    .assign(
        minutes=lambda d: d["duration_s"] / 60,
        long=lambda d: d["minutes"] > 10,
    )
    .query("long")
    .shape
)
print(result)
```

```text
(351, 11)
```

## pipe: your own steps

`pipe` calls a function with the table as the first argument, and passes on what it returns. This puts a function of yours in the chain, and lets you put a check or a print in it:

```python
import pandas as pd

from pdbook.io import load_calls


def tap(df, label):
    print(f"{label:12s} {df.shape}")
    return df


def require(df, test, message):
    if not test(df):
        raise ValueError(message)
    return df


out = (
    load_calls()
    .pipe(tap, "loaded")
    .query("status == 'answered'")
    .pipe(tap, "answered")
    .pipe(require, lambda d: d["duration_s"].notna().all(), "an answered call has no duration")
    .groupby("caller")
    .size()
    .pipe(tap, "per caller")
)
print(int(out.sum()))
```

```text
loaded       (20000, 9)
answered     (15526, 9)
per caller   (600,)
15526
```

`tap` prints the shape and returns the table, so it does not change the result. `require` is a check inside the chain: when the test is false the chain stops with the message, and when it is true the table goes on. The shapes show where rows were lost:

20,000 loaded, 15,526 answered, and 600 callers. The check says that an answered call always has a duration. That is a fact about the data, and you want to be told when it is false.

#### `pd.DataFrame.pipe`

```text
pd.DataFrame.pipe(
    self,
    func,
    *args,
    **kwargs,
)
```

The method calls `func(df, *args, **kwargs)` and returns what `func` returns.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `func` | required | a function whose first argument is the table. A tuple `(function, "name")` passes the table as the keyword `name` instead | a `func` that returns `None` ends the chain: the next step fails on `None`, far from the cause. With a tuple, a keyword of the same name raises `ValueError` |
| `*args` | — | more positional arguments for `func` | — |
| `**kwargs` | — | more keyword arguments for `func` | — |

The same chain with a planted fault stops at the check:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls
from pdbook.report import require

calls = load_calls()
broken = calls.copy()
broken.loc[broken["status"] == "answered", "duration_s"] = np.nan

try:
    broken.query("status == 'answered'").pipe(
        require, lambda d: d["duration_s"].notna().all(), "an answered call has no duration")
except ValueError as error:
    print("ValueError:", error)
```

```text
ValueError: an answered call has no duration
```

#### `pdbook.report.require`

```text
pdbook.report.require(
    df,
    test,
    message,
)
```

The function is a step for `pipe`. It returns `df` unchanged when `test(df)` is true, and raises `ValueError(message)` when it is false.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the table that the chain passes | — |
| `test` | required | a function of the table that returns one `True` or `False` | a test that returns a Series raises `ValueError: The truth value of a Series is ambiguous`. End it with `.all()` or `.any()` |
| `message` | required | the text of the error | — |

## When a chain is too long

A chain of 15 steps is hard to debug: you cannot print the middle. Three habits keep a chain useful:

1. **Cut it at a meaning.** Give a name to the table at the point where it means something, for example `enriched`. Start a second chain from it.
2. **Put the cut in a function.** A function with a name and a docstring is a unit that you can test. A chain inside a function is easy to read.
3. **Debug by cutting from the end.** Put `.pipe(tap, "here")` after a step, or delete steps from the end until the output is what you expect.

## Build: monthly_report

The report is one function with one chain. It takes the four tables and enriches the calls ([Chapter 9](09-joins.md)). It adds the answered flag and the billed minutes ([Chapter 7](07-new-columns.md)). It groups by plan and home city ([Chapter 8](08-group-by.md)). Last, it checks that the groups add up to the calls:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
from pdbook.report import monthly_report

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
report = monthly_report(calls, subs, cells, plans)
print(report.shape)
print(report.head(5).to_string(index=False))
print(report.groupby("plan")[["calls", "revenue_eur"]].sum().round(2).to_dict("index"))
print(plans.set_index("plan")["rate_per_min_eur"].to_dict())
```

```text
(20, 7)
 plan home_city  calls  answered  billed_min  revenue_eur  answer_rate
basic   Antwerp   1083       854        2463        246.3        0.789
basic  Brussels   3073      2353        6156        615.6        0.766
basic     Ghent   1306      1007        2754        275.4        0.771
basic    Leuven    276       212         567         56.7        0.768
basic     Liège    926       727        2057        205.7        0.785
{'basic': {'calls': 6664, 'revenue_eur': 1399.7}, 'business': {'calls': 2290, 'revenue_eur': 193.72}, 'plus': {'calls': 4475, 'revenue_eur': 563.22}, 'prepaid': {'calls': 6571, 'revenue_eur': 2088.45}}
{'prepaid': 0.15, 'basic': 0.1, 'plus': 0.06, 'business': 0.04}
```

The report has 20 rows: 4 plans and 5 cities. The `prepaid` plan makes the most revenue, 2,088.45 euros, although it is not the largest in calls. Its price per minute is the highest, 0.15 euros. The `business` plan has 2,290 calls and makes 193.72 euros.

#### `pdbook.report.monthly_report`

```text
pdbook.report.monthly_report(
    calls,
    subs,
    cells,
    plans,
)
```

The function returns one row for each plan and home city: `calls`, `answered`, `billed_min`, `revenue_eur` and `answer_rate`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records. `call_id` must be unique | a repeated `call_id` raises `ValueError` |
| `subs` | required | the subscribers | — |
| `cells` | required | the cells | — |
| `plans` | required | the plans with their price per minute | a plan missing from `plans` gives revenue 3,681.87 against 4,245.09: the 20 rows are all there, and no error unless you add a check |

The last step of the chain in `monthly_report` is `sort_values`, so the rows come out in the order of plan and city.

#### `pd.DataFrame.sort_values`

```text
pd.DataFrame.sort_values(
    self,
    by,
    *,
    axis=0,
    ascending=True,
    inplace=False,
    kind='quicksort',
    na_position='last',
    ignore_index=False,
    key=None,
)
```

The method returns the rows in the order of the values of one or more columns.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `by` | required | a column name or a list of names | a name that is not a column raises `KeyError` |
| `axis` | `0` | `0` sorts the rows. `1` sorts the columns by the values of a row | — |
| `ascending` | `True` | the direction, or a list with one direction for each name in `by` | a list of another length than `by` raises `ValueError` |
| `inplace` | `False` | with `True`, change the table and return `None` | `inplace=True` in a chain returns `None` and breaks it |
| `kind` | `'quicksort'` | the algorithm. `'stable'` and `'mergesort'` keep the order of equal values. Only used for one sort column | with a list in `by`, `kind` is ignored and the sort is always stable |
| `na_position` | `'last'` | where the missing values go: `'last'` or `'first'` | — |
| `ignore_index` | `False` | with `True`, the result gets the labels 0, 1, 2 and so on | — |
| `key` | `None` | a function that changes the column before the sort. It receives the whole Series | `key=str.lower` raises `TypeError`. Write `key=lambda s: s.str.lower()` |

Three tests prove the function. They are independent of each other:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
from pdbook.rating import rate_vector
from pdbook.report import monthly_report

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
report = monthly_report(calls, subs, cells, plans)

independent = float(rate_vector(calls, subs, plans).sum())
print(round(float(report["revenue_eur"].sum()), 2), round(independent, 2))
print(bool(np.isclose(report["revenue_eur"].sum(), independent)))

shuffled = monthly_report(calls.sample(frac=1, random_state=1), subs, cells, plans)
pd.testing.assert_frame_equal(report, shuffled)
print("order independent")

duplicated = pd.concat([calls, calls.head(1)], ignore_index=True)
try:
    monthly_report(duplicated, subs, cells, plans)
except ValueError as error:
    print("ValueError:", error)
```

```text
4245.09 4245.09
True
order independent
ValueError: call_id is not unique
```

The first test compares the revenue of the chain with the revenue of `rate_vector` from Chapter 7. They are two different computations of the same number, and they agree. The second test shuffles the rows and gets the same report. The third plants a repeated call, and the check inside the chain stops it.

## How it works

Each method in a chain is a function from a table to a new table. The step `pipe(f, *args)` is only `f(df, *args)` written as a method, so that your function can stand in the chain with the others. A chain is therefore a composition of functions, read from the top. Nothing in it assigns to a name, and the input table is not changed.

You can check the three claims:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.report import require

calls = load_calls()
snapshot = calls.copy()


def add_minutes(df, scale):
    return df.assign(minutes=df["duration_s"] / scale)


by_pipe = calls.pipe(add_minutes, 60)
by_call = add_minutes(calls, 60)
print(by_pipe.equals(by_call))

result = (
    calls
    .query("status == 'answered'")
    .assign(minutes=lambda d: d["duration_s"] / 60)
    .pipe(require, lambda d: d["minutes"].notna().all(), "a minute is missing")
)
print(result is calls, result.shape, calls.shape)
print(calls.equals(snapshot), "minutes" in calls.columns)
```

```text
True
False (15526, 10) (20000, 9)
True False
```

`pipe` and the plain call give the same table. The chain returns a new object of a smaller shape. `calls` is still the same 20,000 rows, and it is equal to the copy that was made before. The column `minutes` exists only in the result.

- **Invariant.** A step takes a table and returns a table, and it leaves its input as it was.
- **Failure.** A step that assigns to its argument or returns `None`, such as a method with `inplace=True`, breaks the chain.
- **Cost.** A copy for each step that changes data. Copy-on-write keeps this cheap: columns that a step does not touch are shared, not copied.

The next block tests the cost line on seven steps. Each step runs on the call records, and NumPy says whether two untouched columns of the result still share memory with the input:

```python
import numpy as np

from pdbook.io import load_calls

calls = load_calls()
steps = {
    "assign": lambda d: d.assign(minutes=d["duration_s"] / 60),
    "rename": lambda d: d.rename(columns={"codec": "voice_codec"}),
    "astype": lambda d: d.astype({"roaming": "int8"}),
    "reset_index": lambda d: d.reset_index(drop=True),
    "query": lambda d: d.query("status == 'answered'"),
    "sort_values": lambda d: d.sort_values("start"),
    "head": lambda d: d.head(100),
}
for name, step in steps.items():
    out = step(calls)
    shared = [bool(np.shares_memory(calls[c].to_numpy(), out[c].to_numpy())) for c in ["call_id", "duration_s"]]
    print(f"{name:12s} shares call_id and duration_s: {shared}")
```

```text
assign       shares call_id and duration_s: [True, True]
rename       shares call_id and duration_s: [True, True]
astype       shares call_id and duration_s: [True, True]
reset_index  shares call_id and duration_s: [True, True]
query        shares call_id and duration_s: [False, False]
sort_values  shares call_id and duration_s: [False, False]
head         shares call_id and duration_s: [False, False]
```

The first four steps keep the rows, and the result shares the columns that the step did not change: a new column, a new name or a new type for one column costs no copy of the others. The last three steps choose or reorder rows, and each column of the result is a new array. A chain of steps of the first kind is almost free. Put a `query` early in a chain, so that the copies of the later steps are small.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.pipe` | pipe: your own steps | `func(df, ...)` written as a step of the chain |
| `pd.DataFrame.assign` | The pieces ([Chapter 7](07-new-columns.md) has the block) | new columns; functions see the earlier ones |
| `pd.DataFrame.query` | The pieces ([Chapter 3](03-selection.md) has the block) | the rows where a condition in a string is true |
| `pdbook.report.require` | pipe: your own steps | a check as a step: the table, or `ValueError` |
| `pdbook.report.monthly_report` | Build: monthly_report | one row for each plan and home city |
| `pd.DataFrame.sort_values` | Build: monthly_report | the rows in the order of column values |

## What you have now

- You write a transformation as a chain with one name at the start and one at the end.
- You use `assign` with lambdas, `pipe` for your own steps, and `require` for checks.
- You cut a long chain at a meaning, and put the cut in a named function.
- You test a report against an independent computation, against a shuffled input and against a planted fault.

The next chapter takes the checks out of the chain and makes them a validation layer for the data.

Next: [Chapter 17, Data validation](17-data-validation.md).
