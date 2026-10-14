# 19. Data larger than memory

> **Build** — `talk_by_caller_chunked(path)`: an aggregation that reads a large CSV file in chunks and gives exactly the result of reading the whole file, with a measure of the peak memory of three strategies.
>
> **Theory kept** — Memory is the first limit of pandas. Reduce the data before you reduce the problem: read fewer columns, use smaller types, filter at the read. When that is not enough, read in chunks and keep only an aggregate that you can add across chunks.
>
> **Source** — New. Library: [`pdbook/chunked.py`](../pdbook/chunked.py).
>
> **Run this first** — `uv run python -m examples.ch19_chunked`, which is [`examples/ch19_chunked.py`](../examples/ch19_chunked.py). It writes a 170 MB file to a temporary folder and takes about 30 seconds. Exercises: [`exercises/19.md`](../exercises/19.md). Solutions: [`exercises/solutions/19.md`](../exercises/solutions/19.md).

## How much memory is a file

A table in memory needs more than the file on disk, and the read itself needs more than the table. In this book's data, the 1.56 MB call file is 2.2 MB as a table, which is 1.4 times. The peak while pandas reads a file of 170 MB is about 580 MB, which is 3.4 times (measured in the build section below). Plan for the peak and not for the table.

Look at the size before you read the whole file:

```python
import pandas as pd

head = pd.read_csv("data/calls.csv", nrows=1000)
per_row = head.memory_usage(deep=True).sum() / len(head)
rows = sum(1 for _ in open("data/calls.csv")) - 1
print(rows, round(per_row), "bytes per row")
print(f"estimate for the file: {rows * per_row / 1e6:.1f} MB")
print(f"measured             : {pd.read_csv('data/calls.csv').memory_usage(deep=True).sum() / 1e6:.1f} MB")
```

```text
20000 109 bytes per row
estimate for the file: 2.2 MB
measured             : 2.2 MB
```

The estimate from 1,000 rows is close to the measured size. Use this when a file has 200 million rows and you must decide what to do before you start.

## Four steps, in order

1. **Read fewer columns.** `usecols` ([Chapter 2](02-input-and-output.md)). This is often the whole answer.
2. **Use smaller types.** `dtype={"status": "category"}` at the read, and integer types that fit ([Chapter 4](04-types-and-memory.md)).
3. **Filter at the read.** Parquet reads only the columns and row groups that you ask for.
4. **Read in chunks.** Keep an aggregate, not the rows.

A step is enough when the result fits. Do not go to the next one before you measure.

## Filter at the read with parquet

CSV must be read in full to find a row. Parquet stores the columns separately, so you can read some columns without the rest, and `read_parquet` can apply a filter at the read. The block measures both:

```python
import pathlib
import tempfile
import time

import pandas as pd

from pdbook.bench import replicate
from pdbook.io import load_calls

big = replicate(load_calls(), 50)
with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / "big.parquet"
    big.to_parquet(path)

    def timed(**kwargs):
        t0 = time.perf_counter()
        df = pd.read_parquet(path, **kwargs)
        return time.perf_counter() - t0, df

    t_all, everything = timed()
    t_cols, two = timed(columns=["caller", "duration_s"])
    t_filter, some = timed(columns=["caller", "duration_s"], filters=[("status", "==", "answered")])

print(len(big), everything.shape, two.shape, some.shape)
print(round(everything.memory_usage(deep=True).sum() / 1e6), round(two.memory_usage(deep=True).sum() / 1e6),
      round(some.memory_usage(deep=True).sum() / 1e6), "MB in memory")
print(f"read all {t_all * 1000:.0f} ms, two columns {t_cols * 1000:.0f} ms, two columns and rows {t_filter * 1000:.0f} ms")
```

```text
# output varies
1000000 (1000000, 9) (1000000, 2) (776300, 2)
101 21 16 MB in memory
read all 103 ms, two columns 40 ms, two columns and rows 50 ms
```

The table of 1,000,000 rows needs 101 MB with nine columns and 21 MB with two columns. It needs 16 MB with two columns and the answered calls only (776,300 rows). In every run that I made, the read with the filter was not faster than the read of the same two columns. The file is small, and the filter is an extra step. The saving is in memory. With a file that does not fit in memory, memory is the limit that matters.

## Chunks

`read_csv(..., chunksize=n)` returns an iterator of DataFrames of `n` rows. Only one chunk is in memory at a time. The idea is to reduce each chunk to a small result and to combine the small results:

```python
import pathlib
import tempfile

import pandas as pd

from pdbook.chunked import make_big_csv

with tempfile.TemporaryDirectory() as tmp:
    path = make_big_csv(pathlib.Path(tmp) / "big.csv", times=5)
    reader = pd.read_csv(path, usecols=["caller", "status", "duration_s"], chunksize=30_000)
    sizes, parts = [], []
    for chunk in reader:
        sizes.append(len(chunk))
        answered = chunk[chunk["status"] == "answered"]
        parts.append(answered.groupby("caller")["duration_s"].agg(["sum", "size"]))

    total = pd.concat(parts).groupby(level=0).sum()
    whole = pd.read_csv(path, usecols=["caller", "status", "duration_s"])
    check = whole[whole["status"] == "answered"].groupby("caller")["duration_s"].agg(["sum", "size"])

print(len(sizes), sizes)
print(total.shape, bool((total == check).all().all()))
```

```text
4 [30000, 30000, 30000, 10000]
(600, 2) True
```

100,000 rows in 4 chunks, and the combined result is equal to the result of reading the whole file. Each chunk gives one row for each caller, and the rows with the same caller are added.

The functions of this chapter are in [`pdbook/chunked.py`](../pdbook/chunked.py).

#### `pdbook.chunked.make_big_csv`

```text
pdbook.chunked.make_big_csv(
    path,
    times=50,
)
```

The function writes the call records `times` over to `path`, with a unique `call_id`, and returns the path as a `pathlib.Path`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | required | the file to write | an existing file is replaced, with no question |
| `times` | `50` | the number of copies: 50 gives 1,000,000 rows and 84 MB | `times=100` writes 2,000,000 rows and 170 MB. Check the free disk space first |

The method works for aggregates that you can add across chunks: sum, count, minimum, maximum. A mean is the sum divided by the count, so keep both and divide at the end. It does not work for the median, a quantile, or the number of distinct values. Those need all the values of a group at once, or an approximation with a different structure. The mean of the means of the chunks is also wrong, because chunks hold different counts.

## Build: chunked and whole

The function in `pdbook/chunked.py` does the steps and returns sum, count and mean for each caller. A second function does the same on the whole file. You can then compare the two:

```python
import pathlib
import tempfile

import pandas as pd

from pdbook.chunked import make_big_csv, talk_by_caller_chunked, talk_by_caller_whole

with tempfile.TemporaryDirectory() as tmp:
    path = make_big_csv(pathlib.Path(tmp) / "big.csv", times=20)
    a = talk_by_caller_chunked(path, chunksize=70_000)
    b = talk_by_caller_whole(path)

pd.testing.assert_frame_equal(a, b)
print(a.shape, a.columns.tolist())
print(a.head(3).round(1).to_string())
print(round(float(a["sum"].sum())), int(a["size"].sum()))
```

```text
(600, 3) ['sum', 'size', 'mean']
            sum  size   mean
caller                      
S0001   12060.0   160   75.4
S0002   19280.0   180  107.1
S0003   40520.0   360  112.6
41246960 310520
```

The two results are equal in every cell. The chunk size of 70,000 rows does not divide the file, so the last chunk is shorter, and the result is still the same. The file has 400,000 rows, and 310,520 of its calls are answered.

#### `pdbook.chunked.talk_by_caller_chunked`

```text
pdbook.chunked.talk_by_caller_chunked(
    path,
    chunksize=100000,
)
```

The function returns, for each caller, the `sum`, the `size` and the `mean` of the duration of the answered calls. Only one chunk is in memory at a time.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | required | the CSV file of call records | a path that does not exist raises `FileNotFoundError` |
| `chunksize` | `100000` | the rows in each chunk. It changes the memory and not the result | — (with 10 rows for each chunk the result is still equal, and the job is much slower) |

#### `pdbook.chunked.talk_by_caller_whole`

```text
pdbook.chunked.talk_by_caller_whole(
    path,
)
```

The function returns the same table as `talk_by_caller_chunked`, from one read of the whole file.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | required | the CSV file of call records | it needs the memory of the whole file: see the next block |

Now the memory. Each measure starts a new Python process, because the peak of one process includes everything that it did before. The figure is `VmHWM`, the high-water mark of the resident memory of the new process, from `/proc/self/status`, so the function works on Linux only. The block writes a file of 2,000,000 rows and 170 MB, and it takes about 30 seconds:

```python
import pathlib
import tempfile
import time

import pandas as pd

from pdbook.chunked import make_big_csv, peak_rss_mb, talk_by_caller_chunked, talk_by_caller_whole

with tempfile.TemporaryDirectory() as tmp:
    path = make_big_csv(pathlib.Path(tmp) / "big.csv", times=100)
    t0 = time.perf_counter()
    chunked_result = talk_by_caller_chunked(path)
    t_chunked = time.perf_counter() - t0
    pd.testing.assert_frame_equal(chunked_result, talk_by_caller_whole(path))

    base = peak_rss_mb("import pandas, pyarrow")
    everything = peak_rss_mb(f"import pandas as pd\ndf = pd.read_csv({str(path)!r})")
    whole = peak_rss_mb(f"from pdbook.chunked import *\nr = talk_by_caller_whole({str(path)!r})")
    chunked = peak_rss_mb(f"from pdbook.chunked import *\nr = talk_by_caller_chunked({str(path)!r})")

print(f"python and pandas {base:.0f} MB | all 9 columns {everything:.0f} MB | "
      f"3 columns {whole:.0f} MB | 3 columns in chunks {chunked:.0f} MB")
print(f"chunked job: {t_chunked:.1f} s for {int(chunked_result['size'].sum()):,d} answered calls")
assert chunked < whole < everything
```

```text
# output varies
python and pandas 100 MB | all 9 columns 583 MB | 3 columns 335 MB | 3 columns in chunks 178 MB
chunked job: 2.1 s for 1,552,600 answered calls
```

On the machine that wrote this book, a file of 170 MB gave these peaks. Python and pandas alone need about 100 MB. Reading all nine columns needs about 580 MB, and reading three columns needs about 340 MB. Chunks of 100,000 rows need about 180 MB.

The peaks stayed within about 10 MB between the runs that I made. Reading three columns instead of nine saves about 240 MB, and chunks save about 160 MB more. The assertion in the block fails if the order of the three is different on your machine.

#### `pdbook.chunked.peak_rss_mb`

```text
pdbook.chunked.peak_rss_mb(
    code,
)
```

The function runs `code` in a new Python process and returns its peak resident memory in MB, the `VmHWM` line of `/proc/self/status`. It works on Linux only.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `code` | required | Python source as a string | `ru_maxrss` of a child includes the memory of the parent at the fork, so the function reads `VmHWM`. Code that fails raises `CalledProcessError`. A plain `x = 1` gives about 11 MB: the interpreter alone |

The chunked version does not grow with the file. Its peak is the baseline plus one chunk. That is the property that you buy. You pay for it in more code, in aggregates that you can add, and in a read that is not faster. The block prints the time of the chunked job for 2,000,000 rows.

## When the file is still too large

Other tools exist for data that does not fit in memory. `polars` and `duckdb` are two of them. They are not installed here (the check in Chapter 2 prints it), so this book did not test them and makes no claim about them. Test one on your own data before you rely on it. [Appendix A](../appendices/A-described-not-built.md) lists them.

## How it works

`read_csv(..., chunksize=n)` does not read the file at once. It returns a reader, an iterator, and each step of the iteration parses the next `n` rows into a DataFrame. Each chunk is parsed on its own, and the dtype of a column is chosen again from the values of that chunk. This is the source of one trap: the same column can have different dtypes in different chunks.

The reader and the trap are visible on a small text:

```python
import io

import pandas as pd

text = "id,minutes\n1,5\n2,6\n3,\n4,8\n"
reader = pd.read_csv(io.StringIO(text), chunksize=2)
print(type(reader).__name__)

chunks = list(reader)
print([c["minutes"].dtype.name for c in chunks], [len(c) for c in chunks])
print(pd.concat(chunks)["minutes"].dtype.name)

fixed = pd.read_csv(io.StringIO(text), chunksize=2, dtype={"minutes": "float64"})
print([c["minutes"].dtype.name for c in fixed])
```

```text
TextFileReader
['int64', 'float64'] [2, 2]
float64
['float64', 'float64']
```

The first chunk has the rows 1 and 2, all whole numbers, so `minutes` is `int64`. The second chunk has a missing value, so it is `float64`. The two chunks have different dtypes for one column, and `concat` makes `float64`. A sum over the chunks mixes the two types. With `dtype` in the call, every chunk has the type that you chose.

This is not the `low_memory` chunking of [Chapter 2](02-input-and-output.md). There, the chunks are inside one read, and pandas joins their types into one type for the column. Here, each chunk is a table of its own, and nothing joins them.

- **Invariant.** A chunk holds a fixed number of rows and is parsed alone. At any time one chunk and your aggregate are in memory.
- **Failure.** The dtype of a column can change from chunk to chunk. Give `dtype` for every column that you use.
- **Cost.** The parse of every row, as in a whole read. The memory is the chunk, and the time is not smaller.

A reader is an iterator, and an iterator is used up. The next block reads the same text twice from one reader, and then uses `iterator=True`, which gives the chunks on request with `get_chunk`:

```python
import io

import pandas as pd

text = "id,minutes\n1,5\n2,6\n3,\n4,8\n"
reader = pd.read_csv(io.StringIO(text), chunksize=2)
print("first pass :", sum(len(chunk) for chunk in reader), "rows")
print("second pass:", sum(len(chunk) for chunk in reader), "rows")

on_request = pd.read_csv(io.StringIO(text), iterator=True)
print(len(on_request.get_chunk(3)), len(on_request.get_chunk(3)))

with pd.read_csv(io.StringIO(text), chunksize=2) as reader:
    print(type(reader).__name__, len(next(iter(reader))))
```

```text
first pass : 4 rows
second pass: 0 rows
3 1
TextFileReader 2
```

The second pass gives no rows, and no error. A job that computes the sum over the chunks and then the count over the same reader gets a count of 0. Make one pass and compute every aggregate in it, or make a new reader. `get_chunk(3)` gives three rows and then the one row that is left. The `with` form closes the file when the block ends, even after an error.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.read_csv` | How much memory is a file ([Chapter 2](02-input-and-output.md) has the block) | with `chunksize`, a reader of tables of `n` rows |
| `pd.read_parquet` | Filter at the read with parquet ([Chapter 2](02-input-and-output.md) has the block) | only the columns and rows that you ask for |
| `pdbook.chunked.make_big_csv` | Chunks | the call records repeated in a CSV file |
| `pdbook.chunked.talk_by_caller_chunked` | Build: chunked and whole | sum, size and mean for each caller, with bounded memory |
| `pdbook.chunked.talk_by_caller_whole` | Build: chunked and whole | the same result from one read |
| `pdbook.chunked.peak_rss_mb` | Build: chunked and whole | the peak memory of a fresh process, in MB (Linux) |

## What you have now

- You estimate the memory of a file from a sample of rows.
- You follow four steps, in order: fewer columns, smaller types, filters at the read, chunks.
- You aggregate in chunks with sums and counts, and you check against the whole.
- You measure the peak memory in a fresh process.

The next chapter moves part of the work to a database.

Next: [Chapter 20, SQL and pandas](20-sql-and-pandas.md).
