# 15. Copy-on-Write and traps

> **Build** — A catalog of ten traps, each as a pair of functions (the code that people write and the code that they meant), with a test that all ten still give a wrong answer without an error in the installed pandas.
>
> **Theory kept** — In pandas 3.0, every object that you derive from another object behaves as a copy. A change to one never changes another. Chained assignment does nothing and warns. A function that assigns a column to its argument still changes the caller's table, because there is only one object.
>
> **Source** — New. Library: [`pdbook/traps.py`](../pdbook/traps.py).
>
> **Run this first** — `uv run python -m examples.ch15_traps`, which is [`examples/ch15_traps.py`](../examples/ch15_traps.py). Exercises: [`exercises/15.md`](../exercises/15.md). Solutions: [`exercises/solutions/15.md`](../exercises/solutions/15.md).

## The rule in pandas 3.0

Before 3.0, a selection from a DataFrame was sometimes a view of the original data and sometimes a copy. The rule depended on internals. A write could change the original, or not, and `SettingWithCopyWarning` guessed which. pandas 3.0 replaces this with one rule, copy-on-write:

> Any DataFrame or Series that you get from another one behaves as a separate copy. A write to it never changes the other.

pandas does not copy the data at once. It shares the memory and copies at the first write. You do not see the mechanism. You see the rule:

```python
import pandas as pd

a = pd.DataFrame({"x": [10, 20, 30], "y": [1, 2, 3]})

col = a["x"]
col.iloc[0] = -1
sub = a[["x"]]
sub.iloc[0, 0] = -2
print("after writes to derived objects:", a["x"].tolist())

same = a
same["x"] = 0
print("after a write to a second name :", a["x"].tolist())
```

```text
after writes to derived objects: [10, 20, 30]
after a write to a second name : [0, 0, 0]
```

The writes to `col` and `sub` did not change `a`. The write through `same` did, because `same = a` does not make a new object. It gives a second name to the same object. Assignment of a name never copies. Use `a.copy()` when you want a separate object.

## Chained assignment

`df[mask]["x"] = value` has two steps. The first, `df[mask]`, makes a derived object. The second writes to it. Under the rule, the write goes to a copy that is thrown away:

```python
import warnings

import pandas as pd

df = pd.DataFrame({"x": [1, 2, 3]})
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    df[df["x"] > 1]["x"] = 0
    df["x"][0] = 99
print(df["x"].tolist(), sorted({w.category.__name__ for w in caught}))

df.loc[df["x"] > 1, "x"] = 0
print(df["x"].tolist())
```

```text
[1, 2, 3] ['ChainedAssignmentError']
[1, 0, 0]
```

Both chained forms warn with `ChainedAssignmentError` and change nothing. The `.loc` form with a mask and a column in one call changes the table. The same rule makes `inplace=True` on a column useless:

```python
import warnings

import pandas as pd

df = pd.DataFrame({"a": [1.0, None, 3.0]})
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    df["a"].fillna(0, inplace=True)
print(df["a"].tolist(), caught[0].category.__name__)

df["a"] = df["a"].fillna(0)
print(df["a"].tolist())
```

```text
[1.0, nan, 3.0] ChainedAssignmentError
[1.0, 0.0, 3.0]
```

`df["a"]` is a derived object. `fillna(inplace=True)` fills that object and not the table. The form `df["a"] = df["a"].fillna(0)` is clear and changes the table. Prefer it, and write `inplace=True` nowhere.

## A function that changes its argument

Copy-on-write protects against a hidden link between two objects. It does not protect against an assignment to the object itself. A function that assigns a column to its argument changes the table of the caller:

```python
import pandas as pd


def add_minutes_bad(df):
    df["minutes"] = df["duration_s"] / 60
    return df


def add_minutes_good(df):
    return df.assign(minutes=df["duration_s"] / 60)


calls = pd.DataFrame({"duration_s": [60, 90]})
add_minutes_good(calls)
print(calls.columns.tolist())
add_minutes_bad(calls)
print(calls.columns.tolist())
```

```text
['duration_s']
['duration_s', 'minutes']
```

The good function leaves the table of the caller as it was. The bad one adds a column to it. The caller has no sign of this in the code. A second call to a function that expects the column to be absent can fail or give a different result. Write functions that return a new table. Use `assign`, or begin with `df = df.copy()`.

## Arrays from pandas

`to_numpy()` gives the NumPy array of a column. Under copy-on-write that array is read-only, because a write to it changes the table without going through pandas:

```python
import pandas as pd

s = pd.Series([1, 2, 3])
arr = s.to_numpy()
print(arr.flags.writeable)
try:
    arr[0] = 5
except ValueError as error:
    print("ValueError:", str(error))

own = s.to_numpy(copy=True)
own[0] = 5
print(own.tolist(), s.tolist())
```

```text
False
ValueError: assignment destination is read-only
[5, 2, 3] [1, 2, 3]
```

Ask for `copy=True` when you need an array that you can write to.

## The other traps

Copy-on-write fixes one class of surprise. The others are in the data, and the earlier chapters showed each one. The module [`pdbook/traps.py`](../pdbook/traps.py) holds ten of them as pairs of functions, on small data, so that you can run them and see them:

```python
from pdbook.traps import TRAPS, live

for i, trap in enumerate(TRAPS, 1):
    print(f"{i:>2d} ch{trap.chapter:<3d} {str(trap.naive()):<14.14s} {str(trap.correct()):<14.14s} {trap.name}")
print(all(live(t) for t in TRAPS))
```

```text
 1 ch1   [4, 4, 4]      [2, 4, 6]      a Series adds by label, not by position
 2 ch2   [477123456]    ['0477123456'] read_csv turns a phone number into an integer
 3 ch5   4              6              groupby drops rows with a missing key
 4 ch3   2              3              a condition and its opposite miss the nulls
 5 ch3   [1, 2, 3]      [1, 0, 0]      chained assignment changes nothing
 6 ch3   [10, 20, 30]   [10, 20]       a label slice includes its end
 7 ch9   150            90             a duplicate in a lookup table multiplies rows
 8 ch4   [-56, -56]     [200, 200]     a small integer type wraps around
 9 ch15  False          True           0.1 + 0.2 is not 0.3
10 ch5   3.0            2.25           mean skips nulls
True
```

Each row is a result that looks right and is not. The first value is what the usual code gives, and the second is what a person meant. The list is also a test: `live` is `True` when the two differ. If a later version of pandas fixes a trap, the example module stops, and the book needs a change. The traps in the list are:

1. Arithmetic matches by label, so two Series in different orders give a different sum from two lists ([Chapter 1](01-series-and-dataframe.md)).
2. `read_csv` reads a phone number as an integer and loses the leading zero ([Chapter 2](02-input-and-output.md)).
3. `groupby` drops rows with a missing key ([Chapter 5](05-missing-data.md)).
4. A condition and its opposite both skip the nulls ([Chapter 3](03-selection.md)).
5. Chained assignment changes nothing ([Chapter 3](03-selection.md)).
6. A label slice includes its end ([Chapter 3](03-selection.md)).
7. A duplicate key in a lookup table multiplies rows ([Chapter 9](09-joins.md)).
8. A small integer type wraps around ([Chapter 4](04-types-and-memory.md)).
9. `0.1 + 0.2 == 0.3` is `False`, in pandas as in any language with binary floating point numbers.
10. `mean` skips nulls, so "the mean" is the mean of the known values ([Chapter 5](05-missing-data.md)).

The ninth is new in this chapter. A float comparison with `==` is a trap in every column of `float64`. Use `np.isclose` or `abs(a - b) < tolerance`, and use integers (cents, not euros) for money.

## Build: how to use the catalog

A catalog of known traps is also a review checklist. Before a pipeline goes to production, go through the ten lines and for each ask: does my code have this shape? Examples:

a `merge` without `validate`, a `groupby` without a total check, a `read_csv` without `dtype`. Another example is a `.loc` slice on an index that you did not sort. Each answer is a line of code that you add or a test that you write. The chapters named in the list give the form of the test.

You can also make a trap that is yours. When a wrong result reaches a report, write the small pair of functions before you fix the pipeline. The pair is a test that the fix works, and it is a line in the catalog of the team.

## How it works

Copy-on-write does not copy at once. A derived object, such as `df[["x"]]`, points at the same memory as its parent. Only when you write to one of the two does pandas make a private copy for the object that you write to. Until that moment the two share one array, and this is why a selection is cheap. The rule that a write never reaches another object is kept by the copy that happens at the write.

NumPy can tell whether two arrays share memory:

```python
import warnings

import numpy as np
import pandas as pd

df = pd.DataFrame({"x": np.arange(5), "y": np.arange(5) * 10})
sub = df[["x"]]
print(np.shares_memory(df["x"].to_numpy(), sub["x"].to_numpy()))

sub.iloc[0, 0] = -1
print(np.shares_memory(df["x"].to_numpy(), sub["x"].to_numpy()))
print(df["x"].tolist(), sub["x"].tolist())

view = df["y"].to_numpy()
print(view.flags.writeable)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    value = pd.options.mode.copy_on_write
print(value, caught[0].category.__name__)
```

```text
True
False
[0, 1, 2, 3, 4] [-1, 1, 2, 3, 4]
False
True Pandas4Warning
```

Before the write, the two objects share memory. After `sub.iloc[0, 0] = -1`, they do not, `sub` has its own array with the change, and `df` is as it was. The array from `to_numpy()` is read-only, so a write through it cannot change the table in a way that skips the rule. The last line reads the old option `mode.copy_on_write`. It is `True`, and reading it warns with `Pandas4Warning`: in pandas 3.0 copy-on-write is always on and the option has no effect.

- **Invariant.** A write to one object never changes another object. A read of one object never sees a write to the other.
- **Failure.** A name is not an object: `b = a` makes a second name. A function that assigns to its argument changes the caller's object.
- **Cost.** A selection costs no copy. The first write costs one copy of the array that you write to, not of the whole table.

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.traps import Trap, live

show_signature(pd.DataFrame.copy, ["deep"])
show_signature(pd.Series.to_numpy, ["dtype", "copy", "na_value"])
show_signature(pd.DataFrame.assign)
show_signature(pd.DataFrame.fillna, ["value", "inplace"])
show_signature(Trap)
show_signature(live)
```

```text
NDFrame.copy(
    deep: 'bool' = True
)  # 1 more parameters
IndexOpsMixin.to_numpy(
    dtype: 'npt.DTypeLike | None' = None
    copy: 'bool' = False
    na_value: 'object' = <no_default>
)  # 2 more parameters
DataFrame.assign(
    self
    **kwargs
)
NDFrame.fillna(
    value: 'Hashable | Mapping | Series | DataFrame'
    inplace: 'bool' = False
)  # 3 more parameters
Trap(
    name: 'str'
    chapter: 'int'
    naive: 'Callable[[], Any]'
    correct: 'Callable[[], Any]'
)
live(
    trap: 'Trap'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `copy(deep=...)` | `True` | a separate object | `b = a` is not a copy: a write through `b` changes `a` |
| `to_numpy(copy=...)` | `False` | the NumPy array of a column | the array is read-only: a write raises `ValueError`; ask for `copy=True` to write |
| `to_numpy(dtype=..., na_value=...)` | `None`, not set | the type of the array, and what a missing value becomes | — |
| `assign(**kwargs)` | — | a new table with the columns added | — |
| `fillna(value, inplace=...)` | required, `False` | fill missing values | `df["a"].fillna(0, inplace=True)` warns with `ChainedAssignmentError` and changes nothing |
| `Trap(name, chapter, naive, correct)` | required | a trap as two functions of no arguments | — |
| `live(trap)` | required | `True` when the two functions give different results | all 10 traps are live in this version |

`copy` returns a new object that has its own data.

## What you have now

- You know the copy-on-write rule and what it does not cover.
- You write `df.loc[mask, column] = value`, and `df[column] = df[column].fillna(...)`, and never `inplace=True`.
- You write functions that return a new table.
- You have ten named traps, each with a test, and a method to add one.

The next chapter puts the steps of a pipeline into one readable chain.

Next: [Chapter 16, Method chains and pipelines](16-method-chains-and-pipelines.md).
