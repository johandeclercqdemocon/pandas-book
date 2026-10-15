# 3. Selection

> **Build** — `ops_questions(calls)`: five questions that an operations team asks of the call records, each answered by one selection, with the answers as a dict.
>
> **Theory kept** — `.loc` selects by label, and its slice includes the end. `.iloc` selects by position, and its slice excludes the end. A boolean mask selects the rows where it is `True`. Combine masks with `&`, `|` and `~`, and put each comparison in parentheses.
>
> **Source** — New.
>
> **Run this first** — `uv run python -m examples.ch03_selection`, which is [`examples/ch03_selection.py`](../examples/ch03_selection.py). Exercises: [`exercises/03.md`](../exercises/03.md). Solutions: [`exercises/solutions/03.md`](../exercises/solutions/03.md).

## Four tools, one question each

| You have | You want | Use |
|---|---|---|
| column names | some columns | `df["a"]` or `df[["a", "b"]]` |
| row labels | some rows | `df.loc[labels]` |
| row positions | some rows | `df.iloc[positions]` |
| a condition | the rows that match | `df[mask]` or `df.query("...")` |

Learn `.loc` and `.iloc` first, because they are explicit. The bare `df[...]` does different things for different arguments, and that is a source of errors.

## Columns

A string gives a Series. A list of strings gives a DataFrame, in the order of the list:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
print(type(calls["status"]).__name__)
print(calls[["status", "duration_s"]].head(3).to_string())
```

```text
Series
     status  duration_s
0  answered        24.0
1      busy         0.0
2  answered       174.0
```

pandas also lets you write `calls.status`. Do not use it in code that you keep. It fails for a column name with a space. It returns a method, not a column, when the name is also a method name. A DataFrame has a method `count`, so `df.count` is never a column called `count`.

## Rows by label and by position

Use a small table with text labels, so that labels and positions are different things:

```python
import pandas as pd

d = pd.DataFrame({"v": [10, 20, 30, 40]}, index=["a", "b", "c", "d"])
print(d.loc["a":"c"]["v"].tolist())
print(d.iloc[0:2]["v"].tolist())
print(d.loc["b", "v"], d.iloc[1, 0])
print(d[0:2]["v"].tolist(), d["a":"b"]["v"].tolist())
```

```text
[10, 20, 30]
[10, 20]
20 20
[10, 20] [10, 20]
```

The slice `"a":"c"` has three rows, and `0:2` has two. A label slice includes both ends, because the end label has no "next label" that you could stop before. A position slice follows the Python rule and excludes the end.

The last line shows the bare forms. `d[0:2]` is a position slice, and `d["a":"b"]` is a label slice. The same brackets have two meanings. Avoid both forms.

An integer index makes the difference more dangerous. Here the labels are the numbers 3, 2, 1, 0:

```python
import pandas as pd

d = pd.DataFrame({"v": [10, 20, 30, 40]}, index=[3, 2, 1, 0])
print(d.loc[0:1]["v"].tolist())
print(d.iloc[0:1]["v"].tolist())
print(d.loc[0, "v"], d.iloc[0, 0])

shuffled = pd.DataFrame({"v": [10, 20, 30, 40]}, index=[2, 0, 3, 1])
print(shuffled.loc[0:1].index.tolist())
```

```text
[]
[10]
40 10
[0, 3, 1]
```

The label slice `0:1` is empty. Label 0 is in the last row and label 1 is in the third row. The slice runs from position 3 back to position 2, and that range has no rows.

A label slice on an index that is not sorted is not an error. It returns an empty result or the wrong rows. On the index 2, 0, 3, 1 the slice `0:1` returns the labels 0, 3 and 1, and label 3 is outside the range. Sort the index first with `sort_index()`, or select with a list of labels. Also note that `d.loc[0]` and `d.iloc[0]` are different rows.

#### `pd.DataFrame.sort_index`

```text
pd.DataFrame.sort_index(
    self,
    *,
    axis=0,
    level=None,
    ascending=True,
    inplace=False,
    kind='quicksort',
    na_position='last',
    sort_remaining=True,
    ignore_index=False,
    key=None,
)
```

The method returns the table with its rows, or its columns, in the order of their labels.

The table under `pd.DataFrame.sort_index` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Rows by condition

A comparison on a column gives a boolean Series. That Series is a mask. Use it inside the brackets:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
mask = calls["duration_s"] > 600
print(mask.dtype, int(mask.sum()))
print(calls[mask].shape)
print(calls.loc[mask, ["call_id", "duration_s"]].head(3).to_string())
```

```text
bool 351
(351, 9)
    call_id  duration_s
75       83       971.0
82       90       713.0
86       94       883.0
```

The sum of a boolean Series is a count, because `True` is 1. The mean is a share. These two idioms replace most loops.

To combine masks, use `&` for and, `|` for or and `~` for not. Put each comparison in parentheses, because `&` binds more tightly than `>` and `==`. Do not use the Python words `and` and `or`:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
try:
    calls[calls["status"] == "answered" and calls["duration_s"] > 600]
except ValueError as error:
    print("ValueError:", str(error)[:42])

try:
    calls[calls["status"] == "answered" & calls["duration_s"] > 600]
except TypeError as error:
    print("TypeError:", str(error)[:42])

both = (calls["status"] == "answered") & (calls["duration_s"] > 600)
either = (calls["status"] == "answered") | (calls["duration_s"] > 600)
print(int(both.sum()), int(either.sum()))
```

```text
ValueError: The truth value of a Series is ambiguous. 
TypeError: Cannot perform 'rand_' with a dtyped [floa
351 15526
```

Python `and` asks for one truth value for a whole column, and pandas refuses to give one. Without the parentheses you get a different error. In `calls["status"] == "answered" & calls["duration_s"] > 600`, the `&` binds first and combines the text `"answered"` with a number column. The error is a `TypeError`.

Three helpers make masks readable: `isin` for membership, `between` for a range and `isna` for missing values:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
print(int(calls["codec"].isin(["EVS", "AMR-WB"]).sum()))
print(int(calls["duration_s"].between(60, 120).sum()))
print(int(calls["cell_id"].isna().sum()))
```

```text
12183
4226
277
```

#### `pd.Series.isin`

```text
pd.Series.isin(
    self,
    values,
)
```

The method returns a boolean Series: `True` where the value is in `values`.

The table under `pd.Series.isin` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pd.Series.between`

```text
pd.Series.between(
    self,
    left,
    right,
    inclusive='both',
)
```

The method returns a boolean Series: `True` where `left <= value <= right`.

The table under `pd.Series.between` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Missing values in a mask

A comparison with a missing value is not `True`. The rows with a missing value are not selected, and you get no message:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
longer = calls["duration_s"] > 0
shorter_or_equal = calls["duration_s"] <= 0
print(int(longer.sum()), int(shorter_or_equal.sum()), len(calls))
print(int(calls["duration_s"].isna().sum()))
```

```text
15526 3441 20000
1033
```

The two masks are opposites, and the counts do not add up to 20,000. The difference is 1,033, the number of nulls. A condition and its opposite do not cover the table when the column has nulls. When you need "not longer than zero", write `~longer` and check what you get.

The text methods in pandas 3.0 behave in a new way here. On the `str` dtype, `calls["cell_id"].str.startswith("BRU")` returns `False` for a missing value. On the `object` dtype, it returns a missing value. The `object` dtype was the default for text in pandas 2.x. A mask with a missing value is an error. Check both:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
bru = calls["cell_id"].str.startswith("BRU")
print(bru.dtype, int(calls["cell_id"].isna().sum()), int(bru.isna().sum()))

old_style = calls["cell_id"].astype(object).str.startswith("BRU")
print(old_style.dtype, int(old_style.isna().sum()))
try:
    calls[old_style]
except ValueError as error:
    print("ValueError:", str(error)[:41])
```

```text
bool 277 0
object 277
ValueError: Cannot mask with non-boolean array contai
```

The first result has the dtype `bool`, and no value is missing, although 277 cells are. The second result has the dtype `object` with 277 missing values, and it cannot be a mask. Be aware that, on the `str` dtype, a missing cell counts as "not Brussels". If you need a three-way answer (yes, no, unknown), keep `isna()` in the condition.

## query

`query` takes the condition as a string. It reads well when there are many conditions:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
limit = 600
result = calls.query("status == 'answered' and duration_s > @limit and cell_id.str.startswith('BRU')")
print(result.shape)
```

```text
(136, 9)
```

Inside a `query` string, `and` and `or` are correct, and `@name` reads a Python variable. The cost is that an editor does not check the string, and a typo in a column name is a runtime error. Use `query` when it is shorter and clearer. Use masks when you build a condition from parts in a function.

#### `pd.DataFrame.query`

```text
pd.DataFrame.query(
    self,
    expr,
    *,
    parser='pandas',
    engine=None,
    local_dict=None,
    global_dict=None,
    resolvers=None,
    level=0,
    inplace=False,
)
```

The method returns the rows where the condition in the string is true.

The table under `pd.DataFrame.query` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Set values with .loc

To change values, select the rows and the column in one `.loc`. Two steps do not work in pandas 3.0:

```python
import warnings

import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
mask = calls["status"] == "noanswer"

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    calls[mask]["duration_s"] = -1
print(caught[0].category.__name__)
print(int((calls["duration_s"] == -1).sum()))

calls.loc[mask, "duration_s"] = -1
print(int((calls["duration_s"] == -1).sum()))
```

```text
ChainedAssignmentError
0
2013
```

The first form selects a copy with `calls[mask]`, then sets a value in the copy. The copy is thrown away, and the table does not change. pandas 3.0 tells you with a `ChainedAssignmentError`, and the table does not change. The second form, with one `.loc`, changes the table. [Chapter 15](15-copy-on-write-and-traps.md) explains the rule behind this.

## Build: ops_questions

An operations team asks five questions. Each one is a mask, a count and a name. A function that returns a dict is easy to test and easy to print:

```python
import pandas as pd

from pdbook.io import load_calls


def ops_questions(calls: pd.DataFrame) -> dict[str, int]:
    answered = calls["status"] == "answered"
    return {
        "answered, over 10 min, Brussels cell":
            int((answered & (calls["duration_s"] > 600) & calls["cell_id"].str.startswith("BRU")).sum()),
        "answered, no cell recorded":
            int((answered & calls["cell_id"].isna()).sum()),
        "failed while roaming":
            int((calls["roaming"] & (calls["status"] == "failed")).sum()),
        "wideband or EVS codec":
            int(calls["codec"].isin(["EVS", "AMR-WB"]).sum()),
        "started on 10 September (UTC)":
            int(calls["start"].between(pd.Timestamp("2026-09-10", tz="UTC"),
                                       pd.Timestamp("2026-09-11", tz="UTC"), inclusive="left").sum()),
    }


for name, n in ops_questions(load_calls()).items():
    print(f"{n:>7,d}  {name}")
```

```text
    136  answered, over 10 min, Brussels cell
    212  answered, no cell recorded
     31  failed while roaming
 12,183  wideband or EVS codec
    782  started on 10 September (UTC)
```

#### `examples.ch03_selection.ops_questions`

```text
examples.ch03_selection.ops_questions(
    calls,
)
```

The function returns a dict of question to count.

The table under `examples.ch03_selection.ops_questions` in the Reference section of this chapter gives each parameter and what goes wrong with it.

Read the second line. 212 calls were answered, so media flowed, and the record has no cell. This is a data-quality fact, and it needs a decision: [Chapter 5](05-missing-data.md) treats it. Read the last line. The range uses `inclusive="left"`, so a call at exactly midnight on 11 September belongs to 11 September.

## How it works

Every selection ends as one of two operations on arrays: take the rows at some integer positions, or keep the rows where a boolean array is true. `.loc` with a label first turns the label into a position with the index, and then it takes. `.iloc` skips the first step. A mask is a boolean array of the length of the table, and `df[mask]` takes the positions where it is true.

The label-to-position step is a lookup in a hash table that the `Index` builds the first time that you ask. You can see the step with `get_loc`:

```python
import numpy as np
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().set_index("call_id")
position = calls.index.get_loc(7)
print(type(position).__name__, position)
print(calls.loc[7].equals(calls.iloc[position]))

mask = (calls["status"] == "answered") & (calls["duration_s"] > 600)
positions = np.flatnonzero(mask.to_numpy())
print(len(positions), calls[mask].equals(calls.iloc[positions]))

duplicated = pd.Index([5, 7, 7, 9])
unsorted = pd.Index([7, 5, 7, 9])
print(type(duplicated.get_loc(7)).__name__, type(unsorted.get_loc(7)).__name__)
```

```text
int 19000
True
351 True
slice ndarray
```

Call 7 is at position 19,000. It is one of the 1,000 late records at the end of the file, which [Chapter 12](12-dates-and-resampling.md) uses. `loc` and `iloc` give the same row. The mask gives 351 positions, and taking them gives the same table as `df[mask]`. The last line shows three return types of `get_loc`. A unique label gives an integer.

Equal labels next to each other give a slice. Equal labels that are apart give a boolean mask. This is why a non-unique index changes the type of what `loc` returns.

- **Invariant.** A selection is a set of integer positions.
- **Failure.** A label slice on an unsorted index takes everything between the positions of its two end labels.
- **Cost.** The hash table is built once for each index. A boolean mask costs one pass over its column.

The three return types of `get_loc` have three costs. A unique index answers from its hash table. A sorted index with repeated labels finds the first and the last copy with a binary search, and returns a slice. An unsorted index with repeated labels cannot do either: it compares every label and returns a mask. The next block times one lookup in each kind of index of one million labels:

```python
import timeit

import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
n = 1_000_000
kinds = {
    "unique": pd.Index(rng.permutation(n)),
    "sorted, repeated": pd.Index(np.sort(rng.integers(0, n // 2, n))),
    "unsorted, repeated": pd.Index(rng.integers(0, n // 2, n)),
}
times = {}
for name, index in kinds.items():
    key = int(index[12345])
    index.get_loc(key)
    times[name] = min(timeit.repeat(lambda: index.get_loc(key), number=100, repeat=3)) / 100
    print(f"{name:19s} {type(index.get_loc(key)).__name__:8s} {times[name] * 1e6:9.1f} us")
assert times["unsorted, repeated"] > 50 * times["unique"]
```

```text
# output varies
unique              int            0.4 us
sorted, repeated    slice          2.4 us
unsorted, repeated  ndarray      478.7 us
```

The unique index answers in less than a microsecond. The unsorted index with repeated labels reads all one million labels for each lookup. It is more than 50 times slower, and the assertion checks this. This is a reason to keep a key unique, or at least sorted, before a loop of `.loc` lookups. [Chapter 11](11-index-and-multiindex.md) measures the cost of the first lookup, which builds the table.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.sort_index` | Rows by label and by position | the rows in the order of their labels; a label slice needs it |
| `pd.Series.isin` | Rows by condition | a mask: the value is in a list |
| `pd.Series.between` | Rows by condition | a mask: the value is in a range, both ends included by default |
| `pd.DataFrame.query` | query | the rows where a condition in a string is true |
| `examples.ch03_selection.ops_questions` | Build: ops_questions | five counts for an operations team, as a dict |

`.loc` and `.iloc` are indexers, not functions, so they have no signature. `.loc[a:b]` includes `b`. `.iloc[a:b]` excludes it.

### Parameters

##### `pd.DataFrame.sort_index`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `axis` | `0` | `0` sorts the rows, `1` sorts the columns | — |
| `level` | `None` | for a MultiIndex, the level or levels to sort on ([Chapter 11](11-index-and-multiindex.md)) | — |
| `ascending` | `True` | the direction. A list gives one direction for each level | without the sort, the slice `0:1` on the index 2, 0, 3, 1 returns the labels 0, 3 and 1 |
| `inplace` | `False` | with `True`, change the table and return `None` | `df = df.sort_index(inplace=True)` sets `df` to `None` |
| `kind` | `'quicksort'` | the sort algorithm. Only `'mergesort'` and `'stable'` keep the order of equal labels | — |
| `na_position` | `'last'` | where a missing label goes: `'last'` or `'first'` | — |
| `sort_remaining` | `True` | after a sort on one level of a MultiIndex, also sort on the other levels | with `False`, the rows with equal labels at the sorted level keep their old order |
| `ignore_index` | `False` | with `True`, the result gets the labels 0, 1, 2 and so on | the sorted labels are lost |
| `key` | `None` | a function that changes the labels before the sort. It receives the whole `Index`, not one label | `key=str.lower` raises `TypeError`. Write `key=lambda i: i.str.lower()` |

##### `pd.Series.isin`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `values` | required | a list, a set, a Series or an array of the values to look for | a single string raises `TypeError`. Write `["EVS"]`, not `"EVS"`. A missing value in the list matches the missing values: `isin([np.nan])` finds the 4,474 rows with no codec, but `== np.nan` never matches |

##### `pd.Series.between`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `left` | required | the lower bound | — |
| `right` | required | the upper bound | `between(120, 60)` gives no row, and no error |
| `inclusive` | `'both'` | which bounds belong to the range: `'both'`, `'neither'`, `'left'` or `'right'` | 4,226 calls with `between(60, 120)`, and 4,179 with `inclusive="left"`. `inclusive=True` raises `ValueError` |

##### `pd.DataFrame.query`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `expr` | required | the condition as a string. `and`, `or` and `@name` work inside it | a typo in a column name raises `UndefinedVariableError` when it runs |
| `parser` | `'pandas'` | the grammar of the string. `'pandas'` gives `&` and `|` the low priority of `and` and `or` | with `parser="python"`, `"a > 1 & b < 2"` raises `NotImplementedError`, because `&` binds first |
| `engine` | `None` | the evaluator: `'numexpr'` or `'python'`. `None` uses `numexpr` if it is installed | `engine="numexpr"` raises `ImportError` here, because `numexpr` is not installed |
| `local_dict` | `None` | the variables for `@name`. With `None`, the local variables of the caller | — |
| `global_dict` | `None` | the global variables for `@name`. With `None`, the globals of the caller | — |
| `resolvers` | `None` | more objects in which to look up names | — |
| `level` | `0` | how many frames up the call stack to look for `@name` variables | — |
| `inplace` | `False` | with `True`, change the table and return `None` | — |

##### `examples.ch03_selection.ops_questions`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records, with the types that `load_calls` gives | a `start` column of text, not timestamps, makes the last question raise `TypeError` |


## What you have now

- You select columns with a string or a list, and rows with `.loc`, `.iloc` or a mask.
- You know that a label slice includes its end, and that a label slice on an unsorted index is a trap.
- You combine masks with `&`, `|`, `~` and parentheses.
- You know that missing values fall out of both a condition and its opposite.
- You set values with one `.loc`, never with two brackets.

The next chapter looks at the types of the columns that you selected, and at their memory.

Next: [Chapter 4, Types and memory](04-types-and-memory.md).
