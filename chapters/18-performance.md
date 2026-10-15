# 18. Performance

> **Build** — A benchmark of one task written five ways on 100,000 rows, with a check that all five give the same answer, and the measured cost of three common choices: a loop, a `category` key and a `concat` inside a loop.
>
> **Theory kept** — Measure before you change code. The cost of a pandas job is mostly Python code that runs once for each row. Move that work into whole-column operations. A data type is a speed choice as well as a memory choice. Some advice does not give a gain, and you find out by measuring.
>
> **Source** — New. Library: [`pdbook/bench.py`](../pdbook/bench.py).
>
> **Run this first** — `uv run python -m examples.ch18_performance`, which is [`examples/ch18_performance.py`](../examples/ch18_performance.py). Exercises: [`exercises/18.md`](../exercises/18.md). Solutions: [`exercises/solutions/18.md`](../exercises/solutions/18.md).

## Measure first

A change that you believe is faster is a guess until you time it. Use `time.perf_counter`, take the best of a few runs (the fastest run has the least noise from other work on the machine), and check that the two versions give the same result. The helper in `pdbook/bench.py` does the first two:

```python
import time

import pandas as pd


def best_of(fn, repeat=3):
    best, result = float("inf"), None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        best = min(best, time.perf_counter() - t0)
    return best, result


seconds, total = best_of(lambda: pd.Series(range(1_000_000)).sum())
print(total, seconds < 1.0)
```

```text
499999500000 True
```

Time the part that you want to improve, and not the load of the file. Time it on the size of the real data: the ratio between two methods changes with the number of rows. The section [How it works](#how-it-works) measures the bill of [Chapter 7](07-new-columns.md) at three sizes.

The function `best_of` and the other helpers of this chapter are in [`pdbook/bench.py`](../pdbook/bench.py).

#### `pdbook.bench.best_of`

```text
pdbook.bench.best_of(
    fn,
    repeat=3,
)
```

The function runs `fn()` `repeat` times and returns `(seconds, result)`: the time of the fastest run and the result of the last run.

The table under `pdbook.bench.best_of` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## One task, five ways

The task: for each caller, the total talk minutes of answered calls that are longer than 60 seconds. The table has 100,000 rows, which is the call records repeated five times. Each rung of the ladder is a different way to write the same task, in [`pdbook/bench.py`](../pdbook/bench.py):

| Rung | Idea |
|---|---|
| `iterrows` loop | a Python loop over rows as Series |
| `itertuples` loop | a Python loop over rows as tuples |
| `groupby().apply` | a Python function for each group |
| mask + `groupby` | whole-column operations |
| category + mask + `groupby` | the same, with a `category` key |

```python
import pandas as pd

from pdbook.bench import (best_of, replicate, task_category, task_groupby_apply, task_iterrows,
                          task_itertuples, task_mask_groupby)
from pdbook.io import load_calls

calls = replicate(load_calls(), 5)
rungs = [("iterrows", task_iterrows, 1), ("itertuples", task_itertuples, 1),
         ("groupby.apply", task_groupby_apply, 1), ("mask+groupby", task_mask_groupby, 5),
         ("category", task_category, 5)]

seconds, results = {}, {}
for name, fn, repeat in rungs:
    seconds[name], results[name] = best_of(lambda fn=fn: fn(calls), repeat)

reference = results["mask+groupby"]
for name, result in results.items():
    pd.testing.assert_series_equal(result, reference, check_names=False)

print(len(calls), len(reference))
print(" ".join(f"{n}={s:.3f}s" for n, s in seconds.items()))
assert seconds["iterrows"] / seconds["mask+groupby"] > 20
assert seconds["itertuples"] / seconds["mask+groupby"] > 5
```

```text
# output varies
100000 600
iterrows=3.091s itertuples=0.598s groupby.apply=0.429s mask+groupby=0.013s category=0.018s
```

The five give the same 600 totals. The block prints the times of one run. Two assertions fail on your machine in these cases. `iterrows` is not more than 20 times slower than the mask with `groupby`.

`itertuples` is not more than 5 times slower. Read the order of magnitude and not the digits. On the machine that wrote this book, the times changed by a factor of two between runs when other work ran at the same time.

Two things are worth a second look.

First, `itertuples` was between 2.8 and 6.2 times faster than `iterrows` in every run that I made. The column form was faster than both by a large factor. `itertuples` avoids the creation of a Series for each row, and it still runs Python code for each row. If you must loop, loop over tuples.

Second, the `category` rung is not faster than the plain mask in the block. It converts two columns on every call, and the conversion costs more than it saves. The next section separates the two.

#### `pd.DataFrame.iterrows`

```text
pd.DataFrame.iterrows(
    self,
)
```

The method yields a pair `(label, Series)` for each row. It takes no parameters. Each row becomes a new Series, and a Series has one dtype: `object` for the call records, which mix text and numbers.

For a row of numbers only, the integers become floats. An integer above 2^53 then loses its last digit: 9007199254740993 comes back as 9007199254740992, with no warning.

#### `pd.DataFrame.itertuples`

```text
pd.DataFrame.itertuples(
    self,
    index=True,
    name='Pandas',
)
```

The method yields a named tuple for each row. The values keep the types of their columns.

The table under `pd.DataFrame.itertuples` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.bench.replicate`

```text
pdbook.bench.replicate(
    df,
    times,
)
```

The function returns `times` copies of `df` stacked, with a new `call_id` that is unique.

The table under `pdbook.bench.replicate` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.bench.task_mask_groupby`

```text
pdbook.bench.task_mask_groupby(
    df,
)
```

The function returns, for each caller, the total talk minutes of answered calls longer than 60 seconds. It is the fourth rung, and the reference that the other rungs must equal.

The table under `pdbook.bench.task_mask_groupby` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Types and speed

A `category` column compares and groups on small integer codes. The saving is real when the column is already a category. Time both on 1,000,000 rows:

```python
import pandas as pd

from pdbook.bench import best_of, replicate
from pdbook.io import load_calls

big = replicate(load_calls(), 50)
t_convert, caller_cat = best_of(lambda: big["caller"].astype("category"))
as_cat = big.assign(caller=caller_cat, status=big["status"].astype("category"))

t_str, a = best_of(lambda: big.groupby("caller")["duration_s"].mean())
t_cat, b = best_of(lambda: as_cat.groupby("caller", observed=True)["duration_s"].mean())
pd.testing.assert_series_equal(a.astype("float64"), b.astype("float64"), check_index=False)

t_eq_str, n1 = best_of(lambda: int((big["status"] == "answered").sum()))
t_eq_cat, n2 = best_of(lambda: int((as_cat["status"] == "answered").sum()))
assert n1 == n2

print(len(big))
print(f"groupby  str {t_str * 1000:.1f} ms, category {t_cat * 1000:.1f} ms, ratio {t_str / t_cat:.1f}x")
print(f"compare  str {t_eq_str * 1000:.1f} ms, category {t_eq_cat * 1000:.1f} ms, ratio {t_eq_str / t_eq_cat:.1f}x")
print(f"convert caller to category: {t_convert * 1000:.1f} ms")
assert t_str / t_cat > 1.2 and t_eq_str / t_eq_cat > 3
```

```text
# output varies
1000000
groupby  str 46.1 ms, category 22.7 ms, ratio 2.0x
compare  str 11.9 ms, category 1.0 ms, ratio 11.7x
convert caller to category: 40.1 ms
```

On a million rows, two assertions apply. A `groupby` on a category key must be at least 1.2 times faster. An equality test must be at least 3 times faster. The block prints the times and the cost of the conversion of one column.

Subtract the two `groupby` times to get the saving of one use. The conversion pays after the number of uses that you get when you divide the conversion time by that saving. This confirms [Chapter 4](04-types-and-memory.md), and it adds the condition: convert once, at load or at the start of the job, and not inside each step.

## Do not grow a table in a loop

`concat` builds a new table every time. A loop that appends to a growing table copies it again at every step:

```python
import pandas as pd

from pdbook.bench import best_of
from pdbook.io import load_calls

piece = load_calls().head(200)
parts = [piece] * 100


def in_a_loop():
    out = parts[0]
    for p in parts[1:]:
        out = pd.concat([out, p])
    return out


t_loop, a = best_of(in_a_loop, 1)
t_once, b = best_of(lambda: pd.concat(parts), 3)
print(len(a), len(b), a.equals(b))
print(f"loop {t_loop * 1000:.1f} ms, once {t_once * 1000:.1f} ms, ratio {t_loop / t_once:.0f}x")
assert t_loop / t_once > 3
```

```text
# output varies
20000 20000 True
loop 41.9 ms, once 2.7 ms, ratio 16x
```

100 pieces of 200 rows give 20,000 rows in both ways, and the results are equal. The loop is slower by the ratio that the block prints, and the assertion requires at least 3 times. The cost grows faster than the number of pieces, because each step copies all the rows so far. Collect the pieces in a list, and call `concat` once. The same rule holds for `df.loc[len(df)] = row` in a loop, and for `df = df.append(...)` in code that you find on the web.

## Advice that did not give a gain

Two common tips are worth a test on your own data. Here they gave no gain:

```python
import pandas as pd

from pdbook.bench import best_of, replicate
from pdbook.io import load_calls, load_subscribers

big = replicate(load_calls(), 50)
lookup = load_subscribers()[["subscriber_id", "plan"]]

t_q, a = best_of(lambda: big.query("duration_s > 60 and duration_s < 300 and status == 'answered'"))
t_m, b = best_of(lambda: big[(big["duration_s"] > 60) & (big["duration_s"] < 300) & (big["status"] == "answered")])
print(len(a) == len(b), f"query {t_q * 1000:.0f} ms, mask {t_m * 1000:.0f} ms")

def wide():
    return big.merge(lookup, left_on="caller", right_on="subscriber_id", how="left")

def narrow():
    return big[["caller", "status", "duration_s"]].merge(lookup, left_on="caller", right_on="subscriber_id", how="left")

t_w, _ = best_of(wide)
t_n, _ = best_of(narrow)
print(f"merge wide {t_w * 1000:.0f} ms, narrow {t_n * 1000:.0f} ms")
```

```text
# output varies
True query 92 ms, mask 76 ms
merge wide 176 ms, narrow 175 ms
```

`query` was slower than the mask in every run that I made. The documentation says that `query` can use the optional `numexpr` package. That package is not installed here (Chapter 2 prints the check), so this book makes no claim about its gain. Selecting three columns before the merge made no difference, because the merge cost is in the key and not in the columns that come along. A tip is a hypothesis about your data, and the only test is a timing.

## Where the time goes

The five rungs, the category and the loop have one pattern. The slow versions run Python code for each row, or copy a table many times. The fast versions call compiled code a few times on whole columns. When a job is slow, ask three questions in this order:

1. **Is there a Python loop, `apply(axis=1)`, `iterrows` or `itertuples` over rows?** Replace it with a column expression.
2. **Is a table copied in a loop, or are rows added one at a time?** Collect in a list and build once.
3. **Is a column text where it can be a category, or an integer that is float?** Fix the type once, at the start.

If the answers are all no and the job is slow, you have a data size problem, and the next chapter is for that.

## How it works

Most of the speed in this chapter comes from two facts. A column operation makes one call into compiled code instead of one Python call for each row ([Chapter 7](07-new-columns.md)). And `concat` copies: it allocates a new table and copies every row of its inputs into it.

A loop that concatenates one piece at a time copies the whole table so far at each step. The rows copied are 1 + 2 + 3 + ... + n pieces. That sum is about n squared divided by 2.

You can count the rows that are copied, with no timing at all:

```python
import pandas as pd

from pdbook.io import load_calls

piece = load_calls().head(200)


def rows_copied_in_a_loop(n_pieces: int) -> int:
    out, copied = piece, 0
    for _ in range(n_pieces - 1):
        out = pd.concat([out, piece])
        copied += len(out)
    return copied


for n in (100, 200, 400):
    loop = rows_copied_in_a_loop(n)
    once = n * len(piece)
    print(f"{n:>4d} pieces: loop copies {loop:>10,d} rows, one concat copies {once:>7,d}, ratio {loop / once:.0f}")

small, large = rows_copied_in_a_loop(100), rows_copied_in_a_loop(400)
print(round(large / small, 1))
```

```text
 100 pieces: loop copies  1,009,800 rows, one concat copies  20,000, ratio 50
 200 pieces: loop copies  4,019,800 rows, one concat copies  40,000, ratio 100
 400 pieces: loop copies 16,039,800 rows, one concat copies  80,000, ratio 200
15.9
```

For 100 pieces the loop copies about 50 times as many rows as the single `concat`, and for 400 pieces about 200 times. When the number of pieces grows by 4, the rows copied grow by about 16. This count does not depend on the machine, and it is the cause of the quadratic time in the loop.

- **Invariant.** The time of a vectorized job is proportional to the number of rows. The time of a loop that copies is proportional to the square of the number of steps.
- **Failure.** A test with 10 pieces. The square of 10 is small, and the same code with 4,000 pieces is a different program.
- **Cost.** A copy of every row at every step. Collect pieces in a list and call `concat` once.

A column operation also has a fixed cost: the call into pandas, the checks of types and the build of the result. A loop has no such fixed cost, and it pays for each row. So the ratio between the two depends on the number of rows. The next block times the bill of [Chapter 7](07-new-columns.md) at three sizes:

```python
import timeit

from pdbook.io import load_calls, load_plans, load_subscribers
from pdbook.rating import rate_loop, rate_vector

calls, subs, plans = load_calls(), load_subscribers(), load_plans()
ratios = {}
for n in (200, 2_000, 20_000):
    part = calls.head(n)
    t_loop = min(timeit.repeat(lambda: rate_loop(part, subs, plans), number=1, repeat=3))
    t_vector = min(timeit.repeat(lambda: rate_vector(part, subs, plans), number=1, repeat=5))
    ratios[n] = t_loop / t_vector
    print(f"{n:6,d} rows: loop {t_loop * 1e3:7.1f} ms, columns {t_vector * 1e3:6.2f} ms, ratio {ratios[n]:4.0f}x")
assert ratios[20_000] > 3 * ratios[200]
```

```text
# output varies
200 rows: loop     7.7 ms, columns   3.79 ms, ratio    2x
 2,000 rows: loop    59.1 ms, columns   4.17 ms, ratio   14x
20,000 rows: loop   577.9 ms, columns   9.00 ms, ratio   64x
```

The loop grows with the rows: ten times the rows, about ten times the time. The column form hardly grows, because most of its time at these sizes is the fixed cost. The ratio is small for 200 rows and large for 20,000, and the assertion checks that it grows by more than three times. A benchmark on a sample of 200 rows says that the loop is fine. The same code on the real table is the slow job.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pdbook.bench.best_of` | Measure first | the time of the fastest run, and the result |
| `pd.DataFrame.iterrows` | One task, five ways | `(label, Series)` for each row; mixed rows become `object` |
| `pd.DataFrame.itertuples` | One task, five ways | a named tuple for each row, with the column types |
| `pdbook.bench.replicate` | One task, five ways | the table repeated, with a unique `call_id` |
| `pdbook.bench.task_mask_groupby` | One task, five ways | the reference rung: a mask and a `groupby` |
| `pd.Series.astype` | Types and speed ([Chapter 4](04-types-and-memory.md) has the block) | a conversion; to `category` it pays only when used more than once |
| `pd.concat` | Do not grow a table in a loop ([Chapter 9](09-joins.md) has the block) | tables stacked; one call copies each row once |

### Parameters

##### `pdbook.bench.best_of`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `fn` | required | a function with no arguments | the first run includes warm-up, such as the build of a hash table. With `repeat=1`, that is the time you get |
| `repeat` | `3` | the number of runs | — |

##### `pd.DataFrame.itertuples`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `index` | `True` | put the row label first, as the field `Index` | — |
| `name` | `'Pandas'` | the name of the named tuple type. `None` yields plain tuples, which are faster | a column name that is not a Python name, such as `my col` or `class`, becomes `_1`, `_2` and so on: `row.class` does not exist |

##### `pdbook.bench.replicate`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the call records | — |
| `times` | required | the number of copies | `times=0` raises `ValueError: No objects to concatenate` |

##### `pdbook.bench.task_mask_groupby`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the call records, or a replica of them | — |


## What you have now

- You time with the best of a few runs, on the real size, and you check that the results are equal.
- You know that `iterrows` and `itertuples` are one to two orders of magnitude slower than a column expression (the assertions of the ladder).
- You convert to `category` once, and you know when it pays.
- You collect pieces in a list and call `concat` once.
- You test a tip before you believe it.

The next chapter handles data that is larger than memory.

Next: [Chapter 19, Data larger than memory](19-data-larger-than-memory.md).
