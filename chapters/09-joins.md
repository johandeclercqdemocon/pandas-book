# 9. Joins

> **Build** — `enrich(calls, subs, cells, plans)`: a function that adds the plan, the cities, the technology, the price per minute and an on-net flag to each call. It refuses to run when a lookup table has a duplicate key, and it reports every key that it could not find.
>
> **Theory kept** — A join matches rows on a key. The number of result rows depends on how many rows match each key. A lookup table must have a unique key, and `validate` states and checks that.
>
> **Source** — New. Library: [`pdbook/enrich.py`](../pdbook/enrich.py).
>
> **Run this first** — `uv run python -m examples.ch09_joins`, which is [`examples/ch09_joins.py`](../examples/ch09_joins.py). Exercises: [`exercises/09.md`](../exercises/09.md). Solutions: [`exercises/solutions/09.md`](../exercises/solutions/09.md).

## Four joins on two small tables

```python
import pandas as pd

left = pd.DataFrame({"k": ["a", "b", "c"], "x": [1, 2, 3]})
right = pd.DataFrame({"k": ["b", "c", "d"], "y": [20, 30, 40]})
for how in ["inner", "left", "right", "outer"]:
    m = left.merge(right, on="k", how=how)
    print(f"{how:6s}", m["k"].tolist(), m["x"].tolist(), m["y"].tolist())
```

```text
inner  ['b', 'c'] [2, 3] [20, 30]
left   ['a', 'b', 'c'] [1, 2, 3] [nan, 20.0, 30.0]
right  ['b', 'c', 'd'] [2.0, 3.0, nan] [20, 30, 40]
outer  ['a', 'b', 'c', 'd'] [1.0, 2.0, 3.0, nan] [nan, 20.0, 30.0, 40.0]
```

| `how` | Rows in the result |
|---|---|
| `inner` | the keys that are in both tables |
| `left` | all keys of the left table, with `NaN` where the right table has no match |
| `right` | all keys of the right table |
| `outer` | all keys of both tables |

For enrichment, use `left`: the table that you enrich keeps all its rows, and a missing match shows as `NaN`. An `inner` join drops the rows without a match, and you lose them in silence.

#### `pd.DataFrame.merge`

```text
pd.DataFrame.merge(
    self,
    right,
    how='inner',
    on=None,
    left_on=None,
    right_on=None,
    left_index=False,
    right_index=False,
    sort=False,
    suffixes=('_x', '_y'),
    copy=<no_default>,
    indicator=False,
    validate=None,
)
```

The method joins two tables on key columns or on the index, and returns a new table. `pd.merge(left, right, ...)` is the same function.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `right` | required | the other table, or a named Series | — |
| `how` | `'inner'` | `'left'`, `'right'`, `'outer'`, `'inner'` or `'cross'`. `'cross'` gives every pair of rows | the default `'inner'` loses rows without a match in silence: the join with the cell table keeps 19,723 of 20,000 calls |
| `on` | `None` | the key columns, which have the same name in both tables. With `None`, every column that has the same name in both | with `None`, a second column with the same name becomes part of the key: a shared column `x` gave 0 rows, with no error. Name the key |
| `left_on` | `None` | the key columns of the left table, when the names differ | `left_on` without `right_on` or `right_index` raises `MergeError` |
| `right_on` | `None` | the key columns of the right table | a text key and an integer key raise `ValueError`. Two text keys in different forms match nothing |
| `left_index` | `False` | use the index of the left table as the key | — |
| `right_index` | `False` | use the index of the right table as the key, for example a lookup table indexed by its key | — |
| `sort` | `False` | sort the result by the keys | — |
| `suffixes` | `('_x', '_y')` | the endings for columns that exist on both sides and are not keys | `(None, None)` with such a column raises `ValueError` |
| `copy` | `<no_default>` | ignored since pandas 3.0 | any value warns with `Pandas4Warning` |
| `indicator` | `False` | `True` adds the column `_merge` with `both`, `left_only` or `right_only`. A string names the column | — (277 `left_only`, all with a missing key) |
| `validate` | `None` | `"1:1"`, `"1:m"`, `"m:1"` or `"m:m"`: check that the key is unique on each side marked `1` | without it, 10 duplicate subscribers add 284 rows and no error |

## The number of rows

A join of one row on the left with `n` rows on the right gives `n` rows. The result has as many rows as there are pairs of matching rows. Three relationships matter:

| Relationship | Left key | Right key | Rows in a left join |
|---|---|---|---|
| one-to-one (`1:1`) | unique | unique | as many as the left table |
| many-to-one (`m:1`) | repeats | unique | as many as the left table |
| many-to-many (`m:m`) | repeats | repeats | more than the left table |

The call records to a lookup table is `m:1`: many calls for each subscriber, one row for each subscriber. This is the join that you want. The `m:m` join is the one that multiplies:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().head(1000)
pairs = calls.merge(calls[["caller", "call_id"]], on="caller", suffixes=("", "_other"))
print(len(calls), len(pairs), round(len(pairs) / len(calls), 2))
```

```text
1000 5356 5.36
```

The first 1,000 calls have 5,356 pairs of calls with the same caller. Nobody wanted that, and no error was raised. A join of the calls with themselves on the caller is the pattern behind "all pairs of calls of one subscriber", and it grows with the square of the group size.

## A duplicate in the lookup table

The same effect appears by accident. A subscriber table that has the same `subscriber_id` twice gives each call of that subscriber twice:

```python
import pandas as pd
from pandas.errors import MergeError

from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()
dirty = pd.concat([subs, subs.head(10)], ignore_index=True)

joined = calls.merge(dirty[["subscriber_id", "plan"]], left_on="caller", right_on="subscriber_id", how="left")
print(len(calls), "->", len(joined), "rows;", len(joined) - len(calls), "extra")
print(round(float(calls["duration_s"].sum()), 0), "->", round(float(joined["duration_s"].sum()), 0))

try:
    calls.merge(dirty[["subscriber_id", "plan"]], left_on="caller", right_on="subscriber_id",
                how="left", validate="m:1")
except MergeError as error:
    print("MergeError:", str(error).splitlines()[0])
```

```text
20000 -> 20284 rows; 284 extra
2062348.0 -> 2088598.0
MergeError: Merge keys are not unique in right dataset; not a many-to-one merge
```

Ten duplicate subscribers added 284 rows, and the total talk time grew from 2,062,348 to 2,088,598 seconds. Every later sum, count and mean is wrong, and the table looks normal. The argument `validate="m:1"` makes pandas check the right table and raise `MergeError`. Write it on every join that is a lookup. The check is cheap, because pandas only tests that the key is unique.

The values of `validate` are `"1:1"`, `"1:m"`, `"m:1"` and `"m:m"`. The check is on uniqueness of the key on the side that you mark with `1`.

## Keys must have the same type

A key of integers does not join a key of text:

```python
import pandas as pd

from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()
as_int = subs.assign(msisdn=subs["msisdn"].str[1:].astype("int64"))
try:
    calls.merge(as_int, left_on="callee", right_on="msisdn")
except ValueError as error:
    print("ValueError:", str(error)[:60])
```

```text
ValueError: You are trying to merge on str and int64 columns for key 'ca
```

That is the good case: pandas stops. The dangerous case is two keys of the same type and different form. `+32477123456` and `0477123456` are both text, and they never match.

The join runs, and every row is unmatched. [Chapter 6](06-text-and-date-cleanup.md) gave one form for phone numbers for this reason: clean both sides first.

## Missing keys match each other

A missing key matches a missing key. This differs from SQL, where `NULL` never equals `NULL`:

```python
import numpy as np
import pandas as pd

left = pd.DataFrame({"k": [1.0, np.nan], "a": [1, 2]})
right = pd.DataFrame({"k": [1.0, np.nan], "b": [10, 20]})
print(left.merge(right, on="k").to_dict("records"))
```

```text
[{'k': 1.0, 'a': 1, 'b': 10}, {'k': nan, 'a': 2, 'b': 20}]
```

The row with the missing key found a partner. On the call records this is invisible, because the cell table has no missing key. With a lookup table that has a row with a missing key, every call without a cell gets the values of that row. Drop rows with a missing key from a lookup table before the join.

## Which keys did not match?

`indicator=True` adds a column `_merge` with `both`, `left_only` or `right_only`. Use it to find the unmatched keys, and separate them from the missing keys:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells

calls, cells = load_calls(), load_cells()
m = calls.merge(cells[["cell_id", "tech"]], on="cell_id", how="left", indicator=True)
print(m["_merge"].value_counts().to_dict())
print(int(m["cell_id"].isna().sum()))
print(int(((m["_merge"] == "left_only") & m["cell_id"].notna()).sum()))
```

```text
{'both': 19723, 'left_only': 277, 'right_only': 0}
277
0
```

277 rows are `left_only`, and all 277 have a missing `cell_id`. They did not fail to match. They had nothing to match. The third line counts the real misses, a `cell_id` that is present and not in the cell table, and it is 0. The same split is what `enrich` reports.

To find the keys of one table that are missing from another without a join, use `isin`:

```python
from pdbook.io import load_calls, load_cells

calls, cells = load_calls(), load_cells()
unknown = ~calls["cell_id"].dropna().isin(cells["cell_id"])
unused = ~cells["cell_id"].isin(calls["cell_id"])
print(int(unknown.sum()), int(unused.sum()))
```

```text
0 0
```

## concat: stacking tables

`concat` puts tables under each other (`axis=0`) or next to each other (`axis=1`). It aligns on column names for the first and on the index for the second:

```python
import pandas as pd

a = pd.DataFrame({"call_id": [1, 2], "status": ["answered", "busy"]})
b = pd.DataFrame({"call_id": [3], "status": ["failed"], "codec": ["EVS"]})
both = pd.concat([a, b], ignore_index=True)
print(both.to_dict("list"))
print(both.index.tolist())
```

```text
{'call_id': [1, 2, 3], 'status': ['answered', 'busy', 'failed'], 'codec': [nan, nan, 'EVS']}
[0, 1, 2]
```

A column that one table lacks becomes `NaN`. Use `ignore_index=True` to get a new `RangeIndex`. Without it, the index repeats labels (0, 1, 0), and a later `.loc[0]` returns two rows. Build a list of tables and call `concat` once. A `concat` inside a loop copies the growing table at each step ([Chapter 18](18-performance.md)).

#### `pd.concat`

```text
pd.concat(
    objs,
    *,
    axis=0,
    join='outer',
    ignore_index=False,
    keys=None,
    levels=None,
    names=None,
    verify_integrity=False,
    sort=<no_default>,
    copy=<no_default>,
)
```

The function puts a list of tables or Series together along one axis.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `objs` | required | a list of tables or Series, or a dict of name to table. A `None` in the list is skipped | an empty list raises `ValueError`. A column of integers in one table and of text in the other becomes `object` |
| `axis` | `0` | `0` stacks the rows, `1` puts the tables next to each other | with `axis=1` the rows align on the index: two tables with the labels 0, 1 and 1 give a `NaN` in row 0 |
| `join` | `'outer'` | `'outer'` keeps every column, `'inner'` keeps only the columns in all the tables | — |
| `ignore_index` | `False` | `True` makes a new `RangeIndex` | `False` repeats labels: `loc[0]` returns two rows |
| `keys` | `None` | one name for each table. It becomes a new outer level of the index | — |
| `levels` | `None` | the allowed values of the `keys` level, in order | — |
| `names` | `None` | the names of the levels of the new index | — |
| `verify_integrity` | `False` | `True` raises `ValueError` when a label repeats | it costs a check of the whole index |
| `sort` | `<no_default>` | sort the columns that are not in all the tables. Not set means no sort | — |
| `copy` | `<no_default>` | ignored since pandas 3.0 | any value warns with `Pandas4Warning` |

## Build: enrich

`enrich` chains four many-to-one lookups. Each one is a `left` join with `validate="m:1"` and `indicator=True`. After each join it checks that the row count did not change, and it counts the keys that were present and not found:

```python
import pandas as pd

from pdbook.enrich import enrich
from pdbook.io import load_calls, load_cells, load_plans, load_subscribers

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
enriched, report = enrich(calls, subs, cells, plans)
print(len(calls), "->", len(enriched), "rows,", enriched.shape[1], "columns")
print(report)
print(int(enriched["on_net"].sum()), round(float(enriched["on_net"].mean()), 3))
print(enriched.groupby("tech", dropna=False).size().to_dict())
```

```text
20000 -> 20000 rows, 16 columns
{'caller -> subscribers': 0, 'cell_id -> cells': 0, 'plan -> plans': 0}
5982 0.299
{'4G': 11383, '5G': 8340, nan: 277}
```

The table keeps its 20,000 rows and gets seven new columns. No key is unmatched. 5,982 calls (29.9%) go to a number that belongs to one of the 600 subscribers. The last line has three groups. The 277 calls without a cell have no technology, and that group exists only because of `dropna=False` ([Chapter 5](05-missing-data.md)).

#### `pdbook.enrich.enrich`

```text
pdbook.enrich.enrich(
    calls,
    subs,
    cells,
    plans,
)
```

The function returns `(table, report)`: the calls with seven new columns, and a dict with the count of unmatched keys for each lookup.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | — |
| `subs` | required | the subscribers | a duplicate `subscriber_id` raises `MergeError` |
| `cells` | required | the cells, with `cell_id`, `city` and `tech` | a duplicate `cell_id` raises `MergeError` |
| `plans` | required | the plans, with `plan` and `rate_per_min_eur` | a duplicate plan raises `MergeError` |

The function must also refuse bad input. Plant a fault and see:

```python
import pandas as pd
from pandas.errors import MergeError

from pdbook.enrich import enrich
from pdbook.io import load_calls, load_cells, load_plans, load_subscribers

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
dirty_subs = pd.concat([subs, subs.head(10)], ignore_index=True)
dirty_plans = pd.concat([plans, plans.head(1)], ignore_index=True)

for label, args in [("duplicate subscribers", (dirty_subs, cells, plans)),
                    ("duplicate plans", (subs, cells, dirty_plans))]:
    try:
        enrich(calls, *args)
        print(label, "-> accepted")
    except MergeError:
        print(label, "-> MergeError")
```

```text
duplicate subscribers -> MergeError
duplicate plans -> MergeError
```

Both faults stop the job. A fault that stops a nightly job is a good fault, because someone looks at it the next morning.

## How it works

A join is a lookup of keys. For a many-to-one left join, pandas builds a hash table from the keys of the right table. It looks up each key of the left table in it. The result is one position in the right table, or the value `-1` for a key that is not there. It then takes the rows of the right table at those positions and puts them next to the left rows. The number of result rows is the number of left rows, because each key has at most one position.

The lookup step is `Index.get_indexer`, and you can use it as a join:

```python
import pandas as pd

from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()

lookup = subs.set_index("subscriber_id")
positions = lookup.index.get_indexer(calls["caller"])
print(positions[:5].tolist(), int((positions == -1).sum()))

by_hand = lookup["plan"].to_numpy()[positions]
merged = calls.merge(subs[["subscriber_id", "plan"]], left_on="caller", right_on="subscriber_id", how="left")
print(bool((merged["plan"].to_numpy() == by_hand).all()), len(merged))

few = calls.head(1000)
left_counts = few["caller"].value_counts()
pairs = int((left_counts * left_counts).sum())
print(pairs, len(few.merge(few[["caller"]], on="caller")))
```

```text
[124, 107, 413, 261, 502] 0
True 20000
5356 5356
```

The positions are integers into the 600 subscriber rows, and none is `-1`, because every caller is known. Taking the plans at those positions gives the same column as `merge`. The last line is the many-to-many rule: for each key, the result has the left count times the right count, so the total is the sum of the products. The 1,000 calls have 5,356 pairs, which is the number that [the section on row counts](#the-number-of-rows) printed.

#### `pd.Index.get_indexer`

```text
pd.Index.get_indexer(
    self,
    target,
    method=None,
    limit=None,
    tolerance=None,
)
```

The method returns, for each label of `target`, its position in the index, or -1 when the label is not there.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `target` | required | the labels to look up | an index with a repeated label raises `InvalidIndexError`: a position must be one number |
| `method` | `None` | for a label that is not there: `'pad'` or `'ffill'` takes the previous label, `'backfill'` or `'bfill'` the next, `'nearest'` the closest | with a `method`, the index must be sorted, or it raises `ValueError` |
| `limit` | `None` | the largest number of target labels in a row that an inexact match can fill | — |
| `tolerance` | `None` | the largest distance for an inexact match. A label farther away gets -1 | on the index 10, 20, 30 with `nearest` and `tolerance=3`, 24 gets -1 and 29 gets the position of 30 |

- **Invariant.** A left join on a unique right key keeps the number of left rows and the order of the left table.
- **Failure.** A repeated right key makes one position into several, and the row count goes up by the sum of the repeats.
- **Cost.** One hash table of the right keys and one lookup for each left row. A smaller right table is cheaper to build.

The lookup also fixes the order of the rows. A left join and an inner join walk the left table, so the result has the order of the left keys. A right join walks the right table. An outer join must merge two key sets, and it sorts them. The next block shows the four orders on two small tables with repeated and missing keys:

```python
import pandas as pd

left = pd.DataFrame({"k": ["c", "a", "b", "c"], "x": [1, 2, 3, 4]})
right = pd.DataFrame({"k": ["b", "d", "c", "a"], "y": [20, 40, 30, 10]})
for how in ["left", "inner", "right", "outer"]:
    print(f"{how:6s}", left.merge(right, on="k", how=how)["k"].tolist())
```

```text
left   ['c', 'a', 'b', 'c']
inner  ['c', 'a', 'b', 'c']
right  ['b', 'd', 'c', 'c', 'a']
outer  ['a', 'b', 'c', 'c', 'd']
```

`left` and `inner` keep `c, a, b, c`: the order of the left table, with the repeated `c` in both places. `right` follows the right table, and the two left rows for `c` appear together where `c` is in the right table. `outer` gives the keys in sorted order. A report that depends on the order of the rows after a join must sort them itself.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.merge` | Four joins on two small tables | rows joined on keys; `validate` checks the relationship |
| `pd.concat` | concat: stacking tables | tables stacked, aligned on column names or on the index |
| `pdbook.enrich.enrich` | Build: enrich | the calls with seven lookups, and a report of unmatched keys |
| `pd.Index.get_indexer` | How it works | the position of each label, -1 when not found |

## What you have now

- You use `left` joins for enrichment, and `validate="m:1"` on every lookup.
- You know the three relationships, and that `m:m` multiplies.
- You separate unmatched keys from missing keys with `indicator=True`.
- You know that keys must have the same type and the same form, and that missing keys match each other.
- You stack with one call to `concat` and `ignore_index=True`.

The next chapter reshapes a table from long to wide and back.

Next: [Chapter 10, Pivot and melt](10-pivot-and-melt.md).
