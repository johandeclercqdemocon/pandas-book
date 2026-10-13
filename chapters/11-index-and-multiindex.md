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
index 18.1 ms, mask 163.1 ms, ratio 9x
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
first lookup 310 us, later lookups 0.4 us
[[False, True], ['answered', 'busy', 'failed', 'noanswer']]
[[0, 0, 0, 0, 1, 1, 1, 1], [0, 1, 2, 3, 0, 1, 2, 3]]
True
```

The sorted unique index answers with `get_loc` and with `searchsorted`, and both give 12,344 (the position of the call number 12,345). The block prints the time of the first lookup on a new index and of the later ones. The first builds the hash table, and the assertion fails if it is not at least five times slower than the later ones. The `MultiIndex` of a `groupby` on `roaming` and `status` has two levels of 2 and 4 values, and 8 rows of codes. Rebuilding the tuples from the levels and the codes gives the same tuples.

- **Invariant.** A lookup in a unique index is one hash probe, after a build that happens once.
- **Failure.** A non-unique index returns a slice or a mask, and a code that expects one row gets several.
- **Cost.** The build of the engine, on the first lookup of each new index object. A new index object, for example after `reset_index`, pays it again.

## Reference

```python
import pandas as pd

from pdbook.indexcheck import index_audit
from pdbook.sigs import show_signature

show_signature(pd.DataFrame.set_index, ["keys", "drop", "verify_integrity"])
show_signature(pd.DataFrame.reset_index, ["drop", "level", "names"])
show_signature(pd.DataFrame.reindex, ["labels", "fill_value"])
show_signature(pd.DataFrame.sort_index, ["level", "ascending"])
show_signature(pd.Series.add, ["other", "fill_value"])
show_signature(pd.DataFrame.xs, ["key", "axis", "level"])
show_signature(pd.Index.get_loc, ["key"])
show_signature(index_audit)
```

```text
DataFrame.set_index(
    keys
    drop: 'bool' = True
    verify_integrity: 'bool | lib.NoDefault' = <no_default>
)  # 3 more parameters
DataFrame.reset_index(
    level: 'IndexLabel | None' = None
    drop: 'bool' = False
    names: 'Hashable | Sequence[Hashable] | None' = None
)  # 5 more parameters
DataFrame.reindex(
    labels=None
    fill_value: 'Scalar | None' = nan
)  # 9 more parameters
DataFrame.sort_index(
    level: 'IndexLabel | None' = None
    ascending: 'bool | Sequence[bool]' = True
)  # 8 more parameters
Series.add(
    other
    fill_value=None
)  # 3 more parameters
NDFrame.xs(
    key: 'IndexLabel'
    axis: 'Axis' = 0
    level: 'IndexLabel | None' = None
)  # 2 more parameters
Index.get_loc(
    key
)  # 1 more parameters
index_audit(
    df: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `set_index(keys)` | required | a column or list of columns to use as the index | the pair `(caller, start)` has one repeated label |
| `set_index(drop=...)` | `True` | remove the column after it moves | — |
| `reset_index(drop=...)` | `False` | `True` throws the old index away | `False` adds it back as a column |
| `reindex(labels, fill_value=...)` | `None`, `nan` | the rows for exactly these labels | a label that is not there gives a row of `NaN`, and `loc` raises `KeyError` |
| `sort_index(level, ascending)` | `None`, `True` | sort by the labels | slicing a MultiIndex that is not sorted raises `UnsortedIndexError` |
| `add(other, fill_value=...)` | required, `None` | add by label; treat a missing label as this value | `fill_value=0` is right for counts and wrong for prices |
| `xs(key, level=...)` | required, `None` | one value of one level | — |
| `get_loc(key)` | required | an integer, a slice or a mask | a repeated label returns a slice or a mask |
| `index_audit(df)` | required | a dict: levels, names, dtype, unique, sorted, duplicate labels, missing | — |

`index_audit` returns a dict. On the call records indexed by `(caller, start)`: `unique=False`, `duplicate_labels=1`.

## What you have now

- You use the index for lookup, alignment and time, and you keep the default index otherwise.
- You know that an index has duplicates or is unsorted in some tables, and what that does to `loc`.
- You use `reindex` to ask for exact labels, and `add(fill_value=)` when a missing label means none.
- You use a MultiIndex for the output of a `groupby`, and `reset_index` when you continue to work.
- You can audit an index in one call.

The next chapter takes the index that matters most for operations data: time.

Next: [Chapter 12, Dates and resampling](12-dates-and-resampling.md).
