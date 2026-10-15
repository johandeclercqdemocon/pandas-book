# 11. The index and MultiIndex

> **Build** — `index_audit(df)`: a function that states what the index of a table promises (unique, sorted, named, typed, no missing labels), so that you check it before you rely on it.
>
> **Theory kept** — The index is a set of row labels. It gives fast lookup, it drives alignment, and it is the key of a join on the index. It does not have to be unique, and it does not have to be sorted, and a lot of code assumes both. A MultiIndex is an index with several levels.
>
> **Source** — New. Library: [`pdbook/indexcheck.py`](../pdbook/indexcheck.py).
>
> **Run this first** — `uv run python -m examples.ch11_index`, which is [`examples/ch11_index.py`](../examples/ch11_index.py). Exercises: [`exercises/11.md`](../exercises/11.md). Solutions: [`exercises/solutions/11.md`](../exercises/solutions/11.md).

## What the index is for

Three jobs belong to the index:

1. **Lookup.** `df.loc[label]` finds a row by a hash of the label, without a scan of the column.
2. **Alignment.** An operation between two objects matches the rows by label ([Chapter 1](01-series-and-dataframe.md)).
3. **Time.** A `DatetimeIndex` gives time-based slicing and resampling ([Chapter 12](12-dates-and-resampling.md)).

If your code does none of the three, the default `RangeIndex` is the right index. Do not call `set_index` out of habit. A column is easier to filter, to join on and to write to a file.

## Set it, reset it, sort it

`set_index` moves a column into the index. `reset_index` moves it back. `sort_index` sorts by the labels:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
by_id = calls.set_index("call_id")
print(by_id.index.name, by_id.index.is_unique, by_id.index.is_monotonic_increasing)
print(by_id.loc[7, "status"], by_id.loc[[7, 5]].index.tolist())

ordered = by_id.sort_index()
print(ordered.index.is_monotonic_increasing)
print(ordered.reset_index().columns.tolist()[:3])
```

```text
call_id True False
answered [7, 5]
True
['call_id', 'start', 'caller']
```

The index of `by_id` is unique and not sorted. The file has 1,000 late-arriving records at its end ([Chapter 3](03-selection.md)). A list of labels returns the rows in the order of the list, so `[7, 5]` gives call 7 first. The index is not sorted, and `sort_index` fixes that.

`sort_index` has its block in [Chapter 3](03-selection.md). The other two follow.

#### `pd.DataFrame.set_index`

```text
pd.DataFrame.set_index(
    self,
    keys,
    *,
    drop=True,
    append=False,
    inplace=False,
    verify_integrity=<no_default>,
)
```

The method returns the table with one or more columns, or arrays, as the index.

The table under `pd.DataFrame.set_index` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pd.DataFrame.reset_index`

```text
pd.DataFrame.reset_index(
    self,
    level=None,
    *,
    drop=False,
    inplace=False,
    col_level=0,
    col_fill='',
    allow_duplicates=<no_default>,
    names=None,
)
```

The method moves the index, or some levels of it, back into columns, and gives the table a new `RangeIndex`.

The table under `pd.DataFrame.reset_index` in the Reference section of this chapter gives each parameter and what goes wrong with it.

Lookup by label is fast. A boolean mask scans the whole column for each lookup:

```python
import time

from pdbook.io import load_calls

calls = load_calls()
by_id = calls.set_index("call_id")
ids = calls["call_id"].sample(500, random_state=1).tolist()

t0 = time.perf_counter()
a = [by_id.loc[i, "status"] for i in ids]
t_index = time.perf_counter() - t0

t0 = time.perf_counter()
b = [calls.loc[calls["call_id"] == i, "status"].iloc[0] for i in ids]
t_mask = time.perf_counter() - t0

print(a == b)
print(f"index {t_index * 1000:.1f} ms, mask {t_mask * 1000:.1f} ms, ratio {t_mask / t_index:.0f}x")
assert a == b and t_mask / t_index > 3
```

```text
# output varies
True
index 13.9 ms, mask 168.1 ms, ratio 12x
```

The block prints the time of 500 single lookups by the index and by mask. The numbers depend on your hardware. The assertion fails if the index is not at least 3 times faster on yours. If you look up many labels at once, use one `loc` with a list of labels: `by_id.loc[ids]` is a single operation.

## Duplicates in the index

A pandas index can repeat labels. Then `loc` returns a DataFrame where you expected a scalar or a row:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().head(2)
stacked = pd.concat([calls, calls])
print(stacked.index.tolist())
print(stacked.loc[0].shape, calls.loc[0].shape)
print(stacked.reset_index(drop=True).index.tolist())
```

```text
[0, 1, 0, 1]
(2, 9) (9,)
[0, 1, 2, 3]
```

`calls.loc[0]` is one row and has the shape `(9,)`. `stacked.loc[0]` is two rows and has the shape `(2, 9)`. Code that worked on the first table breaks, or gives a wrong answer, on the second. `concat(..., ignore_index=True)` and `reset_index(drop=True)` give a clean index. [Chapter 9](09-joins.md) made the same point about `concat`.

## reindex: choose the labels you want

`reindex` returns the rows for exactly the labels that you give, in that order. A label that does not exist gives a row of `NaN`:

```python
import pandas as pd

from pdbook.io import load_calls

by_id = load_calls().set_index("call_id")
print(by_id["duration_s"].reindex([1, 2, 99999]).tolist())

hours = pd.Series({9: 300, 10: 270, 14: 254})
print(hours.reindex(range(8, 16), fill_value=0).to_dict())
```

```text
[24.0, 0.0, nan]
{8: 0, 9: 300, 10: 270, 11: 0, 12: 0, 13: 0, 14: 254, 15: 0}
```

`loc` with a missing label raises `KeyError`. `reindex` does not. This is the tool for "I want all 24 hours, even the hours without calls", which is what `traffic_grid` did in [Chapter 10](10-pivot-and-melt.md).

#### `pd.DataFrame.reindex`

```text
pd.DataFrame.reindex(
    self,
    labels=None,
    *,
    index=None,
    columns=None,
    axis=None,
    method=None,
    copy=<no_default>,
    level=None,
    fill_value=nan,
    limit=None,
    tolerance=None,
)
```

The method returns the rows, or the columns, for exactly the labels that you give, in that order.

The table under `pd.DataFrame.reindex` in the Reference section of this chapter gives each parameter and what goes wrong with it.

An index with a repeated label cannot be reindexed: it raises `ValueError`, because one label must then give several rows.

## Alignment in arithmetic

An operator aligns on the index. A missing label gives `NaN`. The method form has `fill_value`:

```python
import pandas as pd

a = pd.Series([1, 2, 3], index=[1, 2, 3])
b = pd.Series([10, 20], index=[2, 3])
print((a + b).tolist())
print(a.add(b, fill_value=0).tolist())
```

```text
[nan, 12.0, 23.0]
[1.0, 12.0, 23.0]
```

The sum has a `NaN` at the label that only `a` has. `add(b, fill_value=0)` treats the missing label as 0 and keeps the value 1. This is correct for counts, where a missing label means "none". It is wrong for a price, where a missing label means "unknown".

#### `pd.Series.add`

```text
pd.Series.add(
    self,
    other,
    level=None,
    fill_value=None,
    axis=0,
)
```

The method is the operator `+` with options. `sub`, `mul` and `div` have the same parameters.

The table under `pd.Series.add` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## MultiIndex: several levels

A `groupby` with two keys gives a MultiIndex. So does `set_index` with two columns. It is an index whose labels are tuples:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
counts = calls.groupby(["caller", "status"]).size()
print(counts.index.names, counts.index.nlevels)
print(counts.loc["S0001"].to_dict())
print(int(counts.loc[("S0001", "answered")]))
print(counts.xs("answered", level="status").shape)
```

```text
['caller', 'status'] 2
{'answered': 8, 'failed': 1, 'noanswer': 2}
8
(600,)
```

`loc` with one label selects the first level, and `loc` with a tuple selects both. `xs` selects one value of a level that is not the first. `unstack` and `reset_index` leave the MultiIndex:

```python
import pandas as pd

from pdbook.io import load_calls

counts = load_calls().groupby(["caller", "status"]).size()
wide = counts.unstack(fill_value=0)
flat = counts.reset_index(name="n")
print(wide.shape, wide.loc["S0001"].to_dict())
print(flat.head(2).to_dict("records"))
```

```text
(600, 4) {'answered': 8, 'busy': 0, 'failed': 1, 'noanswer': 2}
[{'caller': 'S0001', 'status': 'answered', 'n': 8}, {'caller': 'S0001', 'status': 'failed', 'n': 1}]
```

For most work, prefer `reset_index` and ordinary columns after a `groupby`. A column is easy to filter, to join and to write. Keep the MultiIndex for a final table that a person reads, or for repeated `loc` lookups on a table.

#### `pd.DataFrame.xs`

```text
pd.DataFrame.xs(
    self,
    key,
    axis=0,
    level=None,
    drop_level=True,
)
```

The method returns the rows for one value of one index level, a cross-section.

The table under `pd.DataFrame.xs` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Sorted or not

Slicing on a MultiIndex needs a sorted index. On an unsorted index, a slice on the second level raises an error:

```python
import pandas as pd
from pandas.errors import UnsortedIndexError

from pdbook.io import load_calls

calls = load_calls()
multi = calls.set_index(["caller", "start"])
window = ("S0001", slice("2026-09-01", "2026-09-10"))
try:
    multi.loc[window, :]
except UnsortedIndexError as error:
    print("UnsortedIndexError:", str(error)[:46])

ordered = multi.sort_index()
print(ordered.index.is_monotonic_increasing)
print(ordered.loc[window, :].shape)
```

```text
UnsortedIndexError: 'MultiIndex slicing requires the index to be l
True
(7, 7)
```

The error is a good one. pandas stops, and it does not guess the order of the rows. A habit that avoids the error: sort the index right after you set it.

## Build: index_audit

`index_audit` is a function that reads the properties of an index, so that the assumptions are explicit. The audit of a table is five facts:

```python
import pandas as pd

from pdbook.indexcheck import index_audit
from pdbook.io import load_calls

calls = load_calls()
for name, table in [
    ("default", calls),
    ("by call_id", calls.set_index("call_id")),
    ("two copies", pd.concat([calls.head(3), calls.head(3)])),
    ("caller, start", calls.set_index(["caller", "start"])),
]:
    a = index_audit(table)
    print(f"{name:14s} levels={a['levels']} unique={a['unique']!s:5} sorted={a['sorted']!s:5} duplicates={a['duplicate_labels']}")
```

```text
default        levels=1 unique=True  sorted=True  duplicates=0
by call_id     levels=1 unique=True  sorted=False duplicates=0
two copies     levels=1 unique=False sorted=False duplicates=3
caller, start  levels=2 unique=False sorted=False duplicates=1
```

The fourth line is a surprise. The index `(caller, start)` has one duplicate label, so even a pair of subscriber and second is not a key: one subscriber started two calls in the same second. Test a key that you assumed.

Put `index_audit` in the first lines of a function that assumes a sorted or unique index. An `assert audit["unique"]` is one line, and it turns a wrong answer into a stop.

#### `pdbook.indexcheck.index_audit`

```text
pdbook.indexcheck.index_audit(
    df,
)
```

The function returns a dict with seven facts about the index of `df`: `levels`, `names`, `dtype`, `unique`, `sorted`, `duplicate_labels` and `has_missing`.

The table under `pdbook.indexcheck.index_audit` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## How it works

An `Index` is an array of labels with a lookup engine. The first call to `get_loc` builds the engine: a hash table for any index, and a binary search for an index that is unique and sorted. Later calls reuse it.

A `MultiIndex` does not store tuples. It stores *levels*, the distinct values of each key, and *codes*, small integers that say which level value each row has. This is the same idea as a `category` ([Chapter 4](04-types-and-memory.md)).

You can see both:

```python
import time

import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
index = pd.Index(calls["call_id"].sort_values().to_numpy())
print(index.is_unique, index.is_monotonic_increasing)
print(index.get_loc(12345), int(index.searchsorted(12345)))

fresh = pd.Index(calls["call_id"].to_numpy())
t0 = time.perf_counter()
fresh.get_loc(12345)
t_first = time.perf_counter() - t0
t0 = time.perf_counter()
for _ in range(1000):
    fresh.get_loc(12345)
t_next = (time.perf_counter() - t0) / 1000
print(f"first lookup {t_first * 1e6:.0f} us, later lookups {t_next * 1e6:.1f} us")
assert t_first > 5 * t_next

multi = calls.groupby(["roaming", "status"]).size().index
print([level.tolist() for level in multi.levels])
print([code.tolist() for code in multi.codes])
rebuilt = [(multi.levels[0][a], multi.levels[1][b]) for a, b in zip(*multi.codes)]
print(rebuilt == multi.tolist())
```

```text
# output varies
True True
12344 12344
first lookup 390 us, later lookups 0.5 us
[[False, True], ['answered', 'busy', 'failed', 'noanswer']]
[[0, 0, 0, 0, 1, 1, 1, 1], [0, 1, 2, 3, 0, 1, 2, 3]]
True
```

The sorted unique index answers with `get_loc` and with `searchsorted`, and both give 12,344 (the position of the call number 12,345). The block prints the time of the first lookup on a new index and of the later ones. The first builds the hash table, and the assertion fails if it is not at least five times slower than the later ones. The `MultiIndex` of a `groupby` on `roaming` and `status` has two levels of 2 and 4 values, and 8 rows of codes. Rebuilding the tuples from the levels and the codes gives the same tuples.

#### `pd.Index.get_loc`

```text
pd.Index.get_loc(
    self,
    key,
)
```

The method returns the position of one label: an integer, a slice or a boolean mask.

The table under `pd.Index.get_loc` in the Reference section of this chapter gives each parameter and what goes wrong with it.

- **Invariant.** A lookup in a unique index is one hash probe, after a build that happens once.
- **Failure.** A non-unique index returns a slice or a mask, and a code that expects one row gets several.
- **Cost.** The build of the engine, on the first lookup of each new index object. A new index object, for example after `reset_index`, pays it again.

The levels and codes also explain the memory of a MultiIndex. The next block adds the deep memory of the levels, the bytes of the codes and the size of the two level names. It compares the sum with `memory_usage`. Then it makes one lookup, and it measures again. Last, it stores the same 20,000 labels as an index of tuples:

```python
import sys

import pandas as pd

from pdbook.io import load_calls

multi = load_calls().set_index(["caller", "status"]).sort_index().index
levels = sum(int(level.memory_usage(deep=True)) for level in multi.levels)
codes = sum(int(code.nbytes) for code in multi.codes)
names = sum(sys.getsizeof(name) for name in multi.names)
before = int(multi.memory_usage(deep=True))
print(f"levels {levels:,} + codes {codes:,} + names {names} = {levels + codes + names:,}   memory_usage {before:,}")
print([len(level) for level in multi.levels], [str(code.dtype) for code in multi.codes])

multi.get_loc(("S0001", "answered"))
after = int(multi.memory_usage(deep=True))
print(f"after one lookup {after:,} (+{after - before:,})")

tuples = pd.Index(multi.tolist(), tupleize_cols=False)
print(f"as tuples {int(tuples.memory_usage(deep=True)):,}")
```

```text
levels 7,934 + codes 60,000 + names 94 = 68,028   memory_usage 68,028
[600, 4] ['int16', 'int8']
after one lookup 84,752 (+16,724)
as tuples 1,280,000
```

The sum is exact. The 600 callers cost 7,875 bytes once, and each row costs only its two codes: 2 bytes of `int16` for the caller and 1 byte of `int8` for the status. After one lookup the same index reports 16,724 bytes more:

`memory_usage` includes the hash table of the engine as soon as it exists. The same labels as Python tuples need 1,280,000 bytes, 19 times as much. The block sorts the index first. A lookup on the unsorted index gives a `PerformanceWarning`, the warning form of the `UnsortedIndexError` of [Sorted or not](#sorted-or-not).

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.set_index` | Set it, reset it, sort it | columns or arrays as the index; repeats are accepted |
| `pd.DataFrame.reset_index` | Set it, reset it, sort it | the index back to columns, and a new `RangeIndex` |
| `pd.DataFrame.sort_index` | Set it, reset it, sort it ([Chapter 3](03-selection.md) has the block) | the rows in the order of their labels |
| `pd.DataFrame.reindex` | reindex: choose the labels you want | exactly the given labels; a new label gives `NaN` |
| `pd.Series.add` | Alignment in arithmetic | `+` with `fill_value` and `level` |
| `pd.DataFrame.xs` | MultiIndex: several levels | the rows for one value of one level |
| `pdbook.indexcheck.index_audit` | Build: index_audit | seven facts about an index, as a dict |
| `pd.Index.get_loc` | How it works | the position of one label: an integer, a slice or a mask |

### Parameters

##### `pd.DataFrame.set_index`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `keys` | required | a column name, a list of names, or an array or `Index` of the same length | a name that is not a column raises `KeyError`. A repeated label is accepted: the pair `(caller, start)` has one repeated label |
| `drop` | `True` | remove the column after it moves into the index | — |
| `append` | `False` | `True` keeps the old index and adds the new key as a second level | with `True`, the old `RangeIndex` stays as the first level |
| `inplace` | `False` | with `True`, change the table and return `None` | — |
| `verify_integrity` | `<no_default>` | `True` raises `ValueError` for a repeated label | any value warns with `Pandas4Warning`: the parameter goes away in pandas 4. Use `index.is_unique` |

##### `pd.DataFrame.reset_index`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `level` | `None` | the levels to move. With `None`, all of them | — |
| `drop` | `False` | `True` throws the old index away | `False` adds it back as a column. An index with no name becomes a column called `index` |
| `inplace` | `False` | with `True`, change the table and return `None` | — |
| `col_level` | `0` | for columns with several levels: the level that gets the name | — |
| `col_fill` | `''` | for columns with several levels: the label of the other levels. `None` repeats the name | — |
| `allow_duplicates` | `<no_default>` | `True` allows a column name that already exists | the name of an existing column raises `ValueError`: `cannot insert k, already exists` |
| `names` | `None` | new names for the columns that the index becomes | — |

##### `pd.DataFrame.reindex`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `labels` | `None` | the new labels for the axis that `axis` names | — |
| `index` | `None` | the new row labels | a label that is not there gives a row of `NaN`, and an `int64` column becomes `float64`. `loc` raises `KeyError` |
| `columns` | `None` | the new column labels | a name that is not there gives a column of `NaN` |
| `axis` | `None` | the axis for `labels`: `0` or `'index'`, `1` or `'columns'` | — |
| `method` | `None` | how to fill a new label: `'ffill'`, `'bfill'` or `'nearest'` from the labels around it | on an unsorted index it gives `NaN` and no error. `get_indexer` raises in the same case |
| `copy` | `<no_default>` | ignored since pandas 3.0 | any value warns with `Pandas4Warning` |
| `level` | `None` | for a MultiIndex, the level that the labels match | — |
| `fill_value` | `nan` | the value for a new label. `fill_value=0` keeps an integer column as integers | — |
| `limit` | `None` | the largest number of new labels in a row that `method` fills | — |
| `tolerance` | `None` | the largest distance between a new label and the label that fills it | — |

##### `pd.Series.add`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `other` | required | a Series, a number, or a list of the same length | a list of another length raises `ValueError`. A list does not align: it goes by position |
| `level` | `None` | for a MultiIndex, the level on which to match the labels of `other` | — |
| `fill_value` | `None` | the value for a label that one side does not have, before the add | it also replaces a `NaN` that is already in one side: at a label where `a` holds `NaN` and `b` holds 10, the result is 10. A label that both sides lack stays `NaN` |
| `axis` | `0` | not used for a Series. A Series has only axis 0, and `axis=1` raises `ValueError` | — |

##### `pd.DataFrame.xs`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `key` | required | the value to select, or a tuple of values for several levels | a value that is not in the level raises `KeyError` |
| `axis` | `0` | `0` selects rows, `1` selects columns | — |
| `level` | `None` | the level of `key`, by name or number. With `None`, the first levels | — |
| `drop_level` | `True` | remove the selected level from the result | with `True`, the result does not say which value you selected. `drop_level=False` keeps it |

##### `pdbook.indexcheck.index_audit`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | any DataFrame or Series with an index | — |

##### `pd.Index.get_loc`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `key` | required | the label | a label that is not there raises `KeyError`. A repeated label returns a slice or a mask, not an integer ([Chapter 3](03-selection.md)) |


## What you have now

- You use the index for lookup, alignment and time, and you keep the default index otherwise.
- You know that an index has duplicates or is unsorted in some tables, and what that does to `loc`.
- You use `reindex` to ask for exact labels, and `add(fill_value=)` when a missing label means none.
- You use a MultiIndex for the output of a `groupby`, and `reset_index` when you continue to work.
- You can audit an index in one call.

The next chapter takes the index that matters most for operations data: time.

Next: [Chapter 12, Dates and resampling](12-dates-and-resampling.md).
