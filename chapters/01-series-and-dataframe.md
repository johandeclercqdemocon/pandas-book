# 1. Series and DataFrame

> **Build** — `first_look(df)`: a function that tells you, for any table, what each column holds, how much is missing and how much memory the table uses.
>
> **Theory kept** — A Series is values plus an index. A DataFrame is a set of Series that share one index. The index is a set of labels, not a position.
>
> **Source** — New. Data: [`data/calls.csv`](../data/calls.csv), made by [`pdbook/datasets.py`](../pdbook/datasets.py).
>
> **Run this first** — `uv run python -m examples.ch01_first_look`, which is [`examples/ch01_first_look.py`](../examples/ch01_first_look.py). Exercises: [`exercises/01.md`](../exercises/01.md). Solutions: [`exercises/solutions/01.md`](../exercises/solutions/01.md).

## What pandas is for

pandas holds a table in memory and gives each row and each column a label. You use it when the data fit in memory and the question is about rows and columns: how many calls failed, which cell has the longest calls, what changed between Monday and Tuesday.

Underneath, pandas stores each column as an array (NumPy or Arrow). Operations on a column run in compiled code, not in a Python loop. This is the reason pandas is fast enough for millions of rows. It is also the reason you must learn to write operations on whole columns. Chapter 7 measures the difference.

This book uses pandas 3.0. Most tutorials on the web describe pandas 1.x or 2.x. Where 3.0 behaves differently, the text says so and shows the output. [Chapter 24](24-field-guide.md) lists, in one table, the differences that this book ran.

## The Series: values and labels

A Series is a one-dimensional array with a label for each value. It has four parts: the values, the index, a name, and a dtype (the type of every value).

```python
import pandas as pd

fee = pd.Series([12.5, 24.0, 45.0],
                index=["basic", "plus", "business"],
                name="monthly_fee_eur")
print(fee)
print(fee.dtype)
print(list(fee.index))
print(fee.to_numpy())
```

```text
basic       12.5
plus        24.0
business    45.0
Name: monthly_fee_eur, dtype: float64
float64
['basic', 'plus', 'business']
[12.5 24.  45. ]
```

The values are a plain NumPy array. The index holds the labels. You can read a value by its label or by its position:

```python
import pandas as pd

fee = pd.Series([12.5, 24.0, 45.0], index=["basic", "plus", "business"])
print(fee["plus"])
print(fee.iloc[1])
```

```text
24.0
24.0
```

Use `.loc` for labels and `.iloc` for positions. [Chapter 3](03-selection.md) explains both. For now, remember one fact: the label is part of the data, and it does not change when you reorder the Series.

## The index takes part in arithmetic

NumPy arrays add by position. A Series adds by label. This is the first difference that surprises people, and it is the source of many silent errors.

```python
import pandas as pd

a = pd.Series([1, 2, 3], index=["x", "y", "z"])
b = pd.Series([10, 20, 30], index=["y", "z", "w"])
print(a + b)
```

```text
w     NaN
x     NaN
y    12.0
z    23.0
dtype: float64
```

Only `y` and `z` appear in both Series, so only those two labels get a sum. The labels `x` and `w` appear in one Series only, and the result for them is `NaN` (not a number, the marker for a missing value). Notice also that the dtype changed from integer to `float64`, because an integer array has no place to store `NaN`. [Chapter 5](05-missing-data.md) returns to this.

Alignment is a feature. When you divide one column by another from a different table, pandas matches the right rows without a join in your code. It is also a trap, and [Chapter 15](15-copy-on-write-and-traps.md) lists the ways it fails.

## The DataFrame: Series that share an index

A DataFrame is a table. Each column is a Series. All the columns share one index, which labels the rows. Each column has its own dtype.

```python
import pandas as pd

plans = pd.DataFrame({
    "monthly_fee_eur": [0.0, 12.5, 24.0, 45.0],
    "included_minutes": [0, 100, 500, 2000],
}, index=["prepaid", "basic", "plus", "business"])
print(plans)
print(plans.dtypes)
print(type(plans["included_minutes"]).__name__)
print(type(plans[["included_minutes"]]).__name__)
```

```text
          monthly_fee_eur  included_minutes
prepaid               0.0                 0
basic                12.5               100
plus                 24.0               500
business             45.0              2000
monthly_fee_eur     float64
included_minutes      int64
dtype: object
Series
DataFrame
```

One pair of square brackets with a string gives a Series. Two pairs (a list of names) give a DataFrame. This difference matters: many methods exist on both, but they return different shapes.

## Read the call records

The file `data/calls.csv` holds 20,000 call detail records for September 2026. One row is one call attempt.

```python
import pandas as pd

calls = pd.read_csv("data/calls.csv")
print(calls.shape)
print(calls.index)
print(calls.head(3).to_string())
```

```text
(20000, 9)
RangeIndex(start=0, stop=20000, step=1)
   call_id                 start caller       callee  duration_s    status  cell_id codec  roaming
0        1  2026-08-31T22:13:30Z  S0125  32434086075        24.0  answered  BRU-003   EVS    False
1        2  2026-08-31T22:15:27Z  S0108  32491633063         0.0      busy  GHE-001   NaN    False
2        3  2026-08-31T22:51:30Z  S0414  32447458698       174.0  answered  BRU-003   EVS    False
```

`shape` is a tuple of rows and columns. The index is a `RangeIndex` that pandas made: 0, 1, 2 and so on. The file has no index column, so pandas labels the rows by position.

The `info` method gives the dtypes and the number of non-null values for each column in one view:

```python
import pandas as pd

calls = pd.read_csv("data/calls.csv")
calls.info()
```

```text
<class 'pandas.DataFrame'>
RangeIndex: 20000 entries, 0 to 19999
Data columns (total 9 columns):
 #   Column      Non-Null Count  Dtype  
---  ------      --------------  -----  
 0   call_id     20000 non-null  int64  
 1   start       20000 non-null  str    
 2   caller      20000 non-null  str    
 3   callee      20000 non-null  int64  
 4   duration_s  18967 non-null  float64
 5   status      20000 non-null  str    
 6   cell_id     19723 non-null  str    
 7   codec       15526 non-null  str    
 8   roaming     20000 non-null  bool   
dtypes: bool(1), float64(1), int64(2), str(5)
memory usage: 2.1 MB
```

Look at the column `callee`. The file holds phone numbers such as `+32434086075`. pandas read them as integers, because a plus sign at the start is a valid sign for a number. A phone number is an identifier, not a quantity, so integers are the wrong type. The sum of two phone numbers is not useful in the real world. [Chapter 2](02-input-and-output.md) shows how to prevent this.

Look also at the text columns. In pandas 3.0 they have the dtype `str`. In pandas 2.x they had the dtype `object`, which stored Python string objects. The new dtype is faster and uses less memory. [Chapter 4](04-types-and-memory.md) measures both.

## Build: first_look

The standard `info` output is for the eye. It does not return a value that you can test, save or compare. `first_look` returns a DataFrame with one row per column.

```python
import pandas as pd


def first_look(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: dtype, null count, distinct count, first value."""
    return pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "nulls": df.isna().sum(),
        "unique": df.nunique(),
        "first": df.iloc[0].astype(str),
    })


calls = pd.read_csv("data/calls.csv")
print(first_look(calls))
```

```text
              dtype  nulls  unique                 first
call_id       int64      0   20000                     1
start           str      0   19881  2026-08-31T22:13:30Z
caller          str      0     600                 S0125
callee        int64      0   14617           32434086075
duration_s  float64   1033     858                  24.0
status          str      0       4              answered
cell_id         str    277      12               BRU-003
codec           str   4474       3                   EVS
roaming        bool      0       2                 False
```

The function builds a DataFrame from a dict of four Series. Each Series has the column names of `df` as its index. Because the indexes are equal, pandas aligns them without any extra code. This is the alignment from the previous section, and here it saves code.

The table tells you five things at once:

1. `call_id` has 20,000 distinct values in 20,000 rows. It is a key.
2. `caller` has 600 distinct values. It repeats, so it identifies a subscriber, not a call.
3. `duration_s` has 1,033 nulls and the dtype `float64`. An integer column cannot hold nulls, so a count of seconds became a float.
4. `cell_id` and `codec` have nulls. They do not have the same cause: the next chapters find out why.
5. `status` has 4 distinct values. A column with few distinct values is a candidate for the `category` dtype ([Chapter 4](04-types-and-memory.md)).

The module in `pdbook/looks.py` holds this function and `headline`, which returns one line with the row count and the memory:

```python
import pandas as pd

from pdbook.looks import headline

print(headline(pd.read_csv("data/calls.csv")))
```

```text
20,000 rows x 9 columns, 2.2 MB
```

The memory figure is the deep figure: it counts the bytes of the strings, not only of the pointers to them. Use `memory_usage(deep=True)` whenever you compare two representations of the same table.

## How it works

A Series is two objects held together: a NumPy array of values and an `Index` object that holds the labels. A DataFrame is an ordered set of such arrays. Each column is its own array with its own dtype, and all columns share one `Index` for the rows. There is no single block of memory with rows in it, so a column operation reads one contiguous array.

Arithmetic between two Series has three steps. First, pandas builds the union of the two indexes. Second, it reindexes each Series to that union, and a label that the Series lacks becomes `NaN`. Third, it adds the two arrays by position. The alignment of [this chapter](#the-index-takes-part-in-arithmetic) is steps one and two. You can do the three steps yourself and compare:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

a = pd.Series([1, 2, 3], index=["x", "y", "z"])
b = pd.Series([10, 20, 30], index=["y", "z", "w"])

labels = a.index.union(b.index)
by_hand = a.reindex(labels).to_numpy() + b.reindex(labels).to_numpy()
print(labels.tolist())
print(by_hand.tolist())
print(bool(np.array_equal((a + b).to_numpy(), by_hand, equal_nan=True)))
print(type(a.index).__name__, type(a.to_numpy()).__name__)

calls = load_calls()
print({name: type(calls[name].to_numpy()).__name__ for name in ["call_id", "status"]})
print(calls["call_id"].to_numpy().dtype, calls["duration_s"].to_numpy().dtype)
```

```text
['w', 'x', 'y', 'z']
[nan, nan, 12.0, 23.0]
True
Index ndarray
{'call_id': 'ndarray', 'status': 'ndarray'}
int64 float64
```

The union of the labels is sorted: `w`, `x`, `y`, `z`. The hand-made sum has `nan` at `w` and `x`, because each of those labels is in only one Series. The third line is `True`:

`a + b` has the same values, `NaN` included. The last lines show two things. The index and the values are separate objects. The columns of the table are separate arrays with different types.

- **Invariant.** The result of an operation on two Series has the union of their indexes as labels.
- **Failure.** A label on one side only gives `NaN`, and `int64` becomes `float64`.
- **Cost.** The reindex looks up each label and makes a new array. This is why arithmetic on two different indexes is slower than on two arrays.

## Reference

The signatures below are printed from the installed code, with the parameters that this chapter uses.

```python
import pandas as pd

from pdbook.looks import first_look, headline
from pdbook.sigs import show_signature

show_signature(pd.Series, ["data", "index", "dtype", "name"])
show_signature(pd.DataFrame, ["data", "index", "columns", "dtype"])
show_signature(pd.read_csv, ["filepath_or_buffer", "dtype", "nrows"])
show_signature(first_look)
show_signature(headline)
```

```text
Series(
    data=None
    index=None
    dtype: 'Dtype | None' = None
    name=None
)  # 1 more parameters
DataFrame(
    data=None
    index: 'Axes | None' = None
    columns: 'Axes | None' = None
    dtype: 'Dtype | None' = None
)  # 1 more parameters
read_csv(
    filepath_or_buffer: 'FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str]'
    dtype: 'DtypeArg | None' = None
    nrows: 'int | None' = None
)  # 41 more parameters
first_look(
    df: 'pd.DataFrame'
)
headline(
    df: 'pd.DataFrame'
)
```

The parameters that matter in this chapter:

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `Series(data=...)` | `None` | the values: a list, an array or a dict | a dict puts its keys in the index |
| `Series(index=...)` | `None` | the labels, which also drive alignment | labels on one side only give `NaN`, and `int64` becomes `float64` (this chapter) |
| `Series(dtype=...)` | `None` | forces the type of every value | — |
| `Series(name=...)` | `None` | the name, which becomes the column name | — |
| `DataFrame(data=..., index=..., columns=...)` | `None` | a dict of columns, or rows and column names | — |
| `read_csv(filepath_or_buffer)` | required | the file or buffer to read | — |
| `read_csv(nrows=...)` | `None` | read only the first n rows, to look at a large file | — |
| `first_look(df)` | required | one row for each column: dtype, nulls, distinct values, first value | — |
| `headline(df)` | required | one line: rows, columns and deep memory | — |

`first_look` returns a DataFrame indexed by column name. `headline` returns a string.

## What you have now

You can read a CSV file into a DataFrame, and you know that:

- Every column is a Series with its own dtype.
- The index labels the rows and takes part in arithmetic.
- One bracket pair gives a Series. A list gives a DataFrame.
- The dtype `float64` in a column of whole numbers means that nulls are present.

The next chapter reads and writes data in a controlled way. The phone numbers in `callee` need it.

Next: [Chapter 2, Input and output](02-input-and-output.md).
