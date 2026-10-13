# 4. Types and memory

> **Build** — `shrink(df)`: a function that gives every column the smallest dtype that holds its values, plus a report of the bytes saved and a test that the content did not change.
>
> **Theory kept** — A dtype fixes how many bytes each value takes and what operations mean. `category` stores each distinct text once and each row as a small integer code. An integer dtype that is too small wraps around without an error.
>
> **Source** — New. Library: [`pdbook/shrink.py`](../pdbook/shrink.py).
>
> **Run this first** — `uv run python -m examples.ch04_types_memory`, which is [`examples/ch04_types_memory.py`](../examples/ch04_types_memory.py). Exercises: [`exercises/04.md`](../exercises/04.md). Solutions: [`exercises/solutions/04.md`](../exercises/solutions/04.md).

## The dtypes you meet

| dtype | Holds | Missing value | Bytes per value |
|---|---|---|---|
| `int64`, `int32`, `int16`, `int8` | whole numbers | not possible | 8, 4, 2, 1 |
| `float64` | decimals | `NaN` | 8 |
| `bool` | `True` or `False` | not possible | 1 |
| `str` | text | `NaN` | varies |
| `category` | text or numbers from a fixed set | `NaN` | 1, 2 or more |
| `datetime64[us, UTC]` | a point in time | `NaT` | 8 |
| `Int64`, `Int16`, `boolean` | whole numbers or booleans that can be missing | `<NA>` | 1 more than the plain type |
| `object` | any Python object | anything | 8 for the pointer, plus the object |

The column "missing value" is the reason that types matter beyond memory. An integer column cannot hold a missing value, so one null changes the column to `float64`. [Chapter 5](05-missing-data.md) uses this.

## Text: str, object and category

In pandas 3.0, a column of text read from a file has the dtype `str`. pandas stores it with the pyarrow library, in a compact form. In pandas 2.x the same column had the dtype `object`, with one Python string for each row. Measure the three representations of three columns:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
print(calls["status"].dtype.storage)
print(f"{'column':8s} {'str':>9s} {'object':>9s} {'category':>9s}")
for col in ["status", "codec", "cell_id", "caller"]:
    s = calls[col]
    print(f"{col:8s} {s.memory_usage(deep=True):>9,d} "
          f"{s.astype(object).memory_usage(deep=True):>9,d} "
          f"{s.astype('category').memory_usage(deep=True):>9,d}")
```

```text
pyarrow
column         str    object  category
status     312,354 1,132,354    20,191
codec      241,415   982,857    20,172
cell_id    304,193 1,169,484    20,316
caller     260,132 1,080,132    48,007
```

For `status` the `object` form needs 1,132,354 bytes and the `str` form 312,354 bytes: about a quarter. The `category` form needs 20,191 bytes, because it holds the four words once and a one-byte code for each of 20,000 rows. A column with few distinct values is a very good candidate.

A category is two arrays: the list of categories and an array of integer codes.

```python
import pandas as pd

from pdbook.io import load_calls

status = load_calls()["status"].astype("category")
print(status.cat.categories.tolist())
print(status.cat.codes.dtype, status.cat.codes.head(4).tolist())
print(status.head(4).tolist())
```

```text
['answered', 'busy', 'failed', 'noanswer']
int8 [0, 1, 0, 0]
['answered', 'busy', 'answered', 'answered']
```

Comparison and grouping work on the codes, so a category column is also faster for these operations ([Chapter 18](18-performance.md) measures it). Three properties of the category dtype surprise people:

```python
import pandas as pd

from pdbook.io import load_calls

status = load_calls()["status"].astype("category")
try:
    status.iloc[0] = "weird"
except TypeError as error:
    print("TypeError:", str(error)[:58])

levels = pd.CategoricalDtype(["answered", "busy", "failed", "noanswer", "other"])
typed = load_calls().assign(status=lambda d: d["status"].astype(levels))
print(typed.groupby("status")["call_id"].count().to_dict())
print(typed.groupby("status", observed=False)["call_id"].count().to_dict())

rank = pd.Series(pd.Categorical(["low", "high", "mid"],
                                categories=["low", "mid", "high"], ordered=True))
print(rank.sort_values().tolist(), (rank > "low").tolist())
```

```text
TypeError: Cannot setitem on a Categorical with a new category (weird
{'answered': 15526, 'busy': 1428, 'failed': 1033, 'noanswer': 2013}
{'answered': 15526, 'busy': 1428, 'failed': 1033, 'noanswer': 2013, 'other': 0}
['low', 'mid', 'high'] [False, True, True]
```

First, a new value that is not in the categories raises an error. You must add the category first. Second, `groupby` on a category column returns only the categories that occur in pandas 3.0 (`observed=True` is the new default). Write `observed=False` when you want a row for the empty category, for example in a report that has a fixed layout. Third, an ordered category sorts and compares by the order that you gave, not by the alphabet.

## Integers: small types and silent wrap

A column of whole numbers needs only as many bytes as its largest value. `call_id` goes up to 20,000, so `int16` (range ±32,767) holds it in 2 bytes instead of 8. `pd.to_numeric(..., downcast="integer")` picks the smallest type that fits:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

ids = load_calls()["call_id"]
small = pd.to_numeric(ids, downcast="integer")
print(ids.dtype, "->", small.dtype)
print(ids.memory_usage(), "->", small.memory_usage())
print(np.iinfo("int16").min, np.iinfo("int16").max)
```

```text
int64 -> int16
160132 -> 40132
-32768 32767
```

The risk is that a type that is too small does not fail. The value wraps around, in the same way as a counter in a telephone exchange that goes from 255 back to 0:

```python
import pandas as pd

print(pd.Series([300]).astype("int8").tolist())

s = pd.Series([100, 100], dtype="int8")
print((s + s).tolist())
print(s.sum(), s.sum().__class__.__name__)

try:
    s + 1000
except OverflowError as error:
    print("OverflowError:", str(error))
```

```text
[44]
[-56, -56]
200 int64
OverflowError: Python integer 1000 out of bounds for int8
```

There are four different results:

- The conversion of 300 to `int8` gives 44, with no error. The value is 300 minus 256.
- The sum of two `int8` columns gives −56, with no error. The value 200 does not fit, and the result wraps.
- The `sum()` method gives 200, because it adds in `int64`.
- A Python scalar that is out of range raises an error.

The silent cases are the dangerous ones. Narrow an integer column only when you know the range of the data. Test the range with `min()` and `max()` before you convert. The function `to_numeric(downcast=...)` does this check for you.

## Missing integers: the nullable types

A column of whole numbers with one null becomes `float64`. For a count of seconds, that is the wrong type: 24 becomes `24.0`. The nullable integer dtypes (capital `I`) keep integers and mark missing values as `<NA>`:

```python
import pandas as pd

from pdbook.io import load_calls

duration = load_calls()["duration_s"]
whole = duration.astype("Int16")
print(duration.dtype, "->", whole.dtype)
print(duration.memory_usage(), "->", whole.memory_usage())
print(whole.head(3).tolist(), whole.isna().sum())
print(duration.sum() == whole.sum())

values = pd.Series([1, None, 3], dtype="Int64")
print((values == 1).tolist())
try:
    bool(pd.NA)
except TypeError as error:
    print("TypeError:", error)
```

```text
float64 -> Int16
160132 -> 60132
[24, 0, 174] 1033
True
[True, <NA>, False]
TypeError: boolean value of NA is ambiguous
```

The `Int16` column keeps the same sum. The comparison `values == 1` gives `<NA>` for the missing value, because "is nothing equal to 1?" has no answer. That is the logic of SQL, and it differs from NumPy, where `NaN == 1` is `False`. A missing value in an `if` is an error, so pandas does not let you take a decision on something you do not know. Chapter 5 uses this.

## Build: shrink

`shrink` is a loop over the columns with three rules from this chapter. It does three things that a careful person does by hand, and it does them without the typing errors:

```python
import pandas as pd

from pdbook.io import load_calls


def shrink(df: pd.DataFrame, max_unique_share: float = 0.5, float_to_int: bool = False) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if isinstance(s.dtype, pd.StringDtype) or s.dtype == object:
            if len(s) and s.nunique() / len(s) <= max_unique_share:
                out[col] = s.astype("category")
        elif pd.api.types.is_bool_dtype(s):
            continue
        elif pd.api.types.is_integer_dtype(s) and not isinstance(s.dtype, pd.api.extensions.ExtensionDtype):
            out[col] = pd.to_numeric(s, downcast="integer")
        elif float_to_int and pd.api.types.is_float_dtype(s):
            whole = s.dropna()
            if len(whole) and (whole == whole.round()).all():
                small = pd.to_numeric(whole.astype("int64"), downcast="integer").dtype
                out[col] = s.astype(str(small).capitalize())
    return out


calls = load_calls()
small = shrink(calls, float_to_int=True)
before = calls.memory_usage(deep=True).sum()
after = small.memory_usage(deep=True).sum()
print(f"{before:,d} -> {after:,d} bytes ({after / before:.0%})")
print(small.dtypes.astype(str).to_dict())
```

```text
2,017,698 -> 788,290 bytes (39%)
{'call_id': 'int16', 'start': 'datetime64[us, UTC]', 'caller': 'category', 'callee': 'str', 'duration_s': 'Int16', 'status': 'category', 'cell_id': 'category', 'codec': 'category', 'roaming': 'bool'}
```

The table uses 39% of its memory after the change. The columns `callee` and `start` stay as they were. `callee` has 14,617 distinct values in 20,000 rows, which is more than the limit of 50% in `max_unique_share`. `shrink` leaves it as text.

The next section measures what a category saves here. The module [`pdbook/shrink.py`](../pdbook/shrink.py) also holds `memory_report` and `same_content`. The second one is the test: it casts the small table back to the original dtypes and compares it with the original.

```python
from pdbook.io import load_calls
from pdbook.shrink import memory_report, same_content, shrink

calls = load_calls()
small = shrink(calls, float_to_int=True)
print(same_content(calls, small))
print(memory_report(calls, small)[["before", "after"]].to_string())
```

```text
True
                         before                after
call_id                   int64                int16
start       datetime64[us, UTC]  datetime64[us, UTC]
caller                      str             category
callee                      str                  str
duration_s              float64                Int16
status                      str             category
cell_id                     str             category
codec                       str             category
roaming                    bool                 bool
```

`same_content` returns `True`. The two tables say the same, and one needs less than half the memory. Write this test every time you shrink a table.

## When not to shrink

Do not shrink a table that is small. The saving is in the order of megabytes, and the cost is a type that surprises the next person. Do not narrow integers that you add or multiply in the same dtype, because the sum wraps.

A category column with nearly as many categories as rows saves little. The column `callee` has 14,617 distinct values in 20,000 rows:

```python
import pandas as pd

from pdbook.io import load_calls

callee = load_calls()["callee"]
as_category = callee.astype("category")
print(callee.memory_usage(deep=True), as_category.memory_usage(deep=True))
print(len(as_category.cat.categories))
```

```text
400132 334300
14617
```

The saving is 16%, against 94% for `status`. The list of categories holds nearly every string anyway.

Two category columns that have different categories do not stay categories when you combine them:

```python
import pandas as pd

a = pd.DataFrame({"k": pd.Categorical(["x", "y"])})
b = pd.DataFrame({"k": pd.Categorical(["y", "z"])})
same = pd.DataFrame({"k": pd.Categorical(["y", "x"])})
print(pd.concat([a, b])["k"].dtype)
print(pd.concat([a, same])["k"].dtype)
print(a.merge(b, on="k")["k"].dtype)
```

```text
str
category
str
```

The first line is `str`, and the memory gain is gone. The second line has the same categories on both sides, and the result is still `category`. When you plan to combine tables, give both sides one `CategoricalDtype` object ([Chapter 9](09-joins.md)).

## How it works

A dtype fixes how many bytes each value takes and how the bytes are read. An `int16` column is an array of 2-byte numbers: 20,000 values need 40,000 bytes, and a value that does not fit in 16 bits wraps around. A `category` column is two arrays.

The first array holds each distinct value once, the *categories*. The second holds one small integer code for each row, and the code is the position of the value in the first array. Comparison and grouping work on the codes, and the text is only looked up when you display it.

The memory of a category column is the memory of its codes plus the memory of its categories. You can check this against `memory_usage`:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

status = load_calls()["status"].astype("category")
codes = status.cat.codes.to_numpy()
categories = status.cat.categories

print(codes.dtype, codes.nbytes)
print(categories.tolist(), int(categories.memory_usage(deep=True)))
print(codes.nbytes + int(categories.memory_usage(deep=True)), int(status.memory_usage(index=False, deep=True)))

print({name: np.dtype(name).itemsize for name in ["int8", "int16", "int32", "int64", "float64", "bool"]})
print(np.array_equal(status.cat.categories[codes].to_numpy(dtype=object), status.to_numpy(dtype=object)))
```

```text
int8 20000
['answered', 'busy', 'failed', 'noanswer'] 59
20059 20059
{'int8': 1, 'int16': 2, 'int32': 4, 'int64': 8, 'float64': 8, 'bool': 1}
True
```

The codes are `int8`, one byte for each of 20,000 rows. The four categories cost 59 bytes. The sum is 20,059 bytes, and it equals the memory of the column without its index. (The 20,191 of the first table in this chapter also counts the 132 bytes of the index.) The last line shows that indexing the categories with the codes gives back every original value. The `itemsize` line is the table of the chapter: the bytes of each fixed-size type.

- **Invariant.** The bytes of a column are the rows times the itemsize, plus any variable part (the text, the categories).
- **Failure.** A dtype that is too small wraps around without an error.
- **Cost.** A category needs a lookup of codes when you display or join. A column with nearly as many categories as rows saves little.

## Reference

```python
import pandas as pd

from pdbook.shrink import memory_report, same_content, shrink
from pdbook.sigs import show_signature

show_signature(pd.to_numeric, ["errors", "downcast"])
show_signature(pd.Series.astype, ["dtype", "errors"])
show_signature(pd.DataFrame.memory_usage, ["index", "deep"])
show_signature(pd.CategoricalDtype, ["categories", "ordered"])
show_signature(shrink)
show_signature(memory_report)
show_signature(same_content)
```

```text
to_numeric(
    errors: 'DateTimeErrorChoices' = 'raise'
    downcast: "Literal['integer', 'signed', 'unsigned', 'float'] | None" = None
)  # 2 more parameters
NDFrame.astype(
    dtype
    errors: 'IgnoreRaise' = 'raise'
)  # 2 more parameters
DataFrame.memory_usage(
    index: 'bool' = True
    deep: 'bool' = False
)  # 1 more parameters
CategoricalDtype(
    categories=None
    ordered: 'Ordered' = False
)
shrink(
    df: 'pd.DataFrame'
    max_unique_share: 'float' = 0.5
    float_to_int: 'bool' = False
)
memory_report(
    before: 'pd.DataFrame'
    after: 'pd.DataFrame'
)
same_content(
    before: 'pd.DataFrame'
    after: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `to_numeric(errors=...)` | `'raise'` | what to do with text that is not a number: raise, or `'coerce'` to `NaN` | — |
| `to_numeric(downcast=...)` | `None` | `'integer'` picks the smallest integer type that holds every value | — (`call_id`: 160,132 → 40,132 bytes) |
| `astype(dtype)` | required | convert to this type | `astype("int8")` on 300 gives 44, with no error |
| `astype(errors=...)` | `'raise'` | what to do when a value does not convert; the printed type allows `'raise'` and `'ignore'` | — |
| `memory_usage(deep=...)` | `False` | `True` counts the bytes of the text itself | — |
| `memory_usage(index=...)` | `True` | include the index | 132 bytes for a `RangeIndex` of 20,000 rows |
| `CategoricalDtype(categories=...)` | `None` | the allowed values, in order | a value outside the list raises `TypeError` on assignment |
| `CategoricalDtype(ordered=...)` | `False` | `True` makes comparison and sorting follow the order | — |
| `shrink(df, max_unique_share=...)` | `0.5` | the largest share of distinct values for a text column to become `category` | `callee` (73% distinct) stays `str` |
| `shrink(df, float_to_int=...)` | `False` | `True` turns whole-number floats into a nullable integer | `duration_s`: 160,132 → 60,132 bytes |
| `memory_report(before, after)` | required | bytes for each column, before and after | — |
| `same_content(before, after)` | required | `True` when `after`, cast back, equals `before` | — |

`shrink` returns a new DataFrame and does not change its argument.

## What you have now

- You know what each dtype costs and what it cannot hold.
- You use `str` for text, `category` for text with few distinct values and the nullable types for integers with nulls.
- You know that a small integer type wraps without an error.
- You have a function that shrinks a table and a test that proves the content is the same.

The next chapter takes the missing values that this chapter only marked, and decides what to do with them.

Next: [Chapter 5, Missing data](05-missing-data.md).
