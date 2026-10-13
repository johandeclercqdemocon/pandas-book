# 2. Input and output

> **Build** — `load_calls()`: a loader that reads the call records with the right type for every column, plus a round-trip test that proves a file format keeps those types.
>
> **Theory kept** — A CSV file has no types. `read_csv` guesses them, and every guess can be wrong without an error message. You must state the types that matter. Parquet stores the types, so it does not guess.
>
> **Source** — New. Loader: [`pdbook/io.py`](../pdbook/io.py).
>
> **Run this first** — `uv run python -m examples.ch02_input_output`, which is [`examples/ch02_input_output.py`](../examples/ch02_input_output.py). Exercises: [`exercises/02.md`](../exercises/02.md). Solutions: [`exercises/solutions/02.md`](../exercises/solutions/02.md).

## A file is text, and types are guesses

A CSV file contains characters. The characters `24.0` can be a duration, a price or a version number. The function `read_csv` looks at the characters in each column and chooses a dtype. The choice is correct often enough that you stop checking, and that is the danger.

[Chapter 1](01-series-and-dataframe.md) found one wrong guess already: `callee` came back as `int64`. Here is the same problem on four lines of text:

```python
import io

import pandas as pd

text = "phone\n0477123456\n+32477123456\n"
print(pd.read_csv(io.StringIO(text))["phone"].tolist())

text = "phone\n0477123456\n0477123457\n"
print(pd.read_csv(io.StringIO(text))["phone"].tolist())
print(pd.read_csv(io.StringIO(text), dtype={"phone": "str"})["phone"].tolist())
```

```text
[477123456, 32477123456]
[477123456, 477123457]
['0477123456', '0477123457']
```

Without a dtype, the number `0477123456` loses its leading zero. Nothing warns you. The value `+32477123456` becomes the integer 32477123456, which is a different string. With `dtype={"phone": "str"}`, the characters stay as they are.

The rule: any column that is an identifier must be read as text. Identifiers are phone numbers, postcodes, account numbers, product codes and IMEI numbers. You do not do arithmetic on them, so integers give you nothing and can destroy information.

## Say what you know

The arguments of `read_csv` that you use every day are few:

| Argument | What it does |
|---|---|
| `dtype` | A dict of column name to dtype. Use it for identifiers. |
| `parse_dates` | A list of columns to convert to timestamps. |
| `usecols` | Read only these columns. Faster and smaller. |
| `nrows` | Read only the first n rows. Use it to look at a large file. |
| `na_values` | More strings that mean "missing". |
| `index_col` | Use a column as the index. |

Read the call records with the first three:

```python
import pandas as pd

calls = pd.read_csv("data/calls.csv",
                    dtype={"caller": "str", "callee": "str"},
                    parse_dates=["start"])
print(calls[["start", "caller", "callee"]].dtypes.astype(str).to_dict())
print(calls["start"].iloc[0])
print(calls["callee"].iloc[0])
```

```text
{'start': 'datetime64[us, UTC]', 'caller': 'str', 'callee': 'str'}
2026-08-31 22:13:30+00:00
+32434086075
```

The column `start` now has the dtype `datetime64[us, UTC]`. The `UTC` is there because every string in the file ends with `Z`, which means UTC. If the strings had no zone, the column has no zone, and [Chapter 12](12-dates-and-resampling.md) shows why that matters. The `us` means microsecond resolution. pandas 2.x used nanoseconds for every timestamp, and nanoseconds cannot hold a date before the year 1678. pandas 3.0 picks the resolution from the data:

```python
import pandas as pd

for text in ["1500-01-01", "2026-10-12 10:00:00", "2026-10-12 10:00:00.123456789"]:
    print(text, "->", pd.to_datetime([text]).dtype)

try:
    pd.Timestamp("1500-01-01").as_unit("ns")
except Exception as error:
    print("as nanoseconds:", type(error).__name__)
```

```text
1500-01-01 -> datetime64[us]
2026-10-12 10:00:00 -> datetime64[us]
2026-10-12 10:00:00.123456789 -> datetime64[ns]
as nanoseconds: OutOfBoundsDatetime
```

A string with nine decimals gets nanosecond resolution, because microseconds lose digits. The year 1500 is a valid timestamp at microsecond resolution, and it is out of bounds at nanosecond resolution.

## Missing markers

`read_csv` treats a fixed list of strings as missing: the empty string, `NA`, `N/A`, `NaN`, `null` and a few more. It does not treat `-` as missing:

```python
import io

import pandas as pd

text = "a,b\n1,5\n2,N/A\n3,-\n4,7\n"
default = pd.read_csv(io.StringIO(text))
print(default["b"].tolist(), default["b"].dtype)

custom = pd.read_csv(io.StringIO(text), na_values=["-"])
print(custom["b"].tolist(), custom["b"].dtype)
```

```text
['5', nan, '-', '7'] str
[5.0, nan, nan, 7.0] float64
```

The dash stays a string, and one string forces the whole column to the text dtype. A column of numbers with one dash in it is a column of strings. [Chapter 6](06-text-and-date-cleanup.md) cleans such columns after the read. When you know the marker, `na_values` is the better place to handle it: the column keeps its numeric dtype, as the second line shows.

## Read less

Most analyses need a few columns of a wide file. `usecols` does not parse the columns you drop, so the read is faster and the table is smaller:

```python
import pandas as pd

wide = pd.read_csv("data/calls.csv")
narrow = pd.read_csv("data/calls.csv", usecols=["call_id", "status"])
print(wide.shape, narrow.shape)
print(int(wide.memory_usage(deep=True).sum()), int(narrow.memory_usage(deep=True).sum()))
```

```text
(20000, 9) (20000, 2)
2177698 472354
```

The narrow table needs about a fifth of the memory. With a file that is larger than memory, this is the first thing you try ([Chapter 19](19-data-larger-than-memory.md)).

## Write without the index

`to_csv` writes the index as a column unless you tell it not to. On the way back, that column has no name and pandas calls it `Unnamed: 0`:

```python
import io

import pandas as pd

df = pd.DataFrame({"a": [1, 2]})
print(pd.read_csv(io.StringIO(df.to_csv())).columns.tolist())
print(pd.read_csv(io.StringIO(df.to_csv(index=False))).columns.tolist())
```

```text
['Unnamed: 0', 'a']
['a']
```

Write `index=False` unless the index carries information that you want to keep. If it does, name it and read it back with `index_col`.

CSV loses more than the index. It stores no dtype, so a round trip through CSV is a round trip through a guess:

```python
import io

import pandas as pd

from pdbook.io import load_calls

calls = load_calls().head(1000)
back = pd.read_csv(io.StringIO(calls.to_csv(index=False)))
print(calls.dtypes.astype(str).to_dict()["callee"], "->", back.dtypes.astype(str).to_dict()["callee"])
print(calls.dtypes.astype(str).to_dict()["start"], "->", back.dtypes.astype(str).to_dict()["start"])
```

```text
str -> int64
datetime64[us, UTC] -> str
```

## Parquet keeps the types

Parquet is a binary column format. It stores the dtype of each column, compresses well and lets you read a subset of columns without reading the rest. pandas uses the `pyarrow` package for it.

```python
import pathlib
import tempfile

import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / "calls.parquet"
    calls.to_parquet(path)
    back = pd.read_parquet(path)
    only_two = pd.read_parquet(path, columns=["call_id", "status"])
    pd.testing.assert_frame_equal(calls, back)
    print("round trip equal")
    print("csv bytes    :", pathlib.Path("data/calls.csv").stat().st_size)
    print("parquet bytes:", path.stat().st_size)
    print(only_two.shape)
```

```text
round trip equal
csv bytes    : 1559678
parquet bytes: 527534
(20000, 2)
```

`assert_frame_equal` compares values, dtypes, index and column names. It raised no error, so every type survived, including the UTC timestamp and the text identifiers. The parquet file is about a third of the size of the CSV file.

The sizes are exact for this data. The read times depend on your machine, and the module `examples/ch02_input_output.py` prints them for each format. Run it to see yours.

## JSON needs care

`to_json` and `read_json` work, but JSON has no timestamp type either. In pandas 3.0 the default `date_format` is the old `epoch`, and it warns about its removal:

```python
import tempfile
import warnings

import pandas as pd

from pdbook.io import load_calls

calls = load_calls().head(3)
with tempfile.TemporaryDirectory() as tmp:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calls.to_json(f"{tmp}/a.jsonl", orient="records", lines=True)
    print(caught[0].category.__name__)
    print(open(f"{tmp}/a.jsonl").readline()[:60])
    calls.to_json(f"{tmp}/b.jsonl", orient="records", lines=True, date_format="iso")
    print(open(f"{tmp}/b.jsonl").readline()[:60])
```

```text
Pandas4Warning
{"call_id":1,"start":1788214410000,"caller":"S0125","callee"
{"call_id":1,"start":"2026-08-31T22:13:30.000Z","caller":"S0
```

The warning class is `Pandas4Warning`. It tells you that behavior will change in pandas 4. Write `date_format="iso"` and the warning goes away. The result is also readable by people and by other tools.

## Excel

`read_excel` and `to_excel` exist. The pandas documentation names `openpyxl` as the package for `.xlsx` files. This book does not install it, so the text does not run Excel code, and the next block checks that:

```python
import importlib.util

installed = {name: importlib.util.find_spec(name) is not None
             for name in ["openpyxl", "numexpr", "polars", "duckdb"]}
print(installed)
```

```text
{'openpyxl': False, 'numexpr': False, 'polars': False, 'duckdb': False}
```

None of the four optional packages that this book mentions is installed, so every statement about them is *described, not run* ([Appendix A](../appendices/A-described-not-built.md)). From the documentation, the arguments of `read_excel` that matter are the same as for `read_csv`: `dtype`, `usecols`, `nrows` and `na_values`, plus `sheet_name`. The same identifier rule applies. [Appendix A](../appendices/A-described-not-built.md) lists what the book describes and does not run.

## Build: load_calls and a round-trip test

The loader is two lines of code. Its value is that it is the only place that knows the file format:

```python
import io

import pandas as pd

from pdbook.io import load_calls


def round_trip_ok(df: pd.DataFrame, write, read) -> bool:
    """True when write() then read() returns an identical frame, dtypes included."""
    try:
        pd.testing.assert_frame_equal(df, read(write(df)))
    except AssertionError:
        return False
    return True


calls = load_calls()
print(calls.dtypes.astype(str).to_dict()["callee"])
print(round_trip_ok(calls.head(500),
                    write=lambda d: d.to_csv(index=False),
                    read=lambda s: pd.read_csv(io.StringIO(s))))
print(round_trip_ok(calls.head(500),
                    write=lambda d: d.to_csv(index=False),
                    read=lambda s: pd.read_csv(io.StringIO(s),
                                               dtype={"caller": "str", "callee": "str"},
                                               parse_dates=["start"])))
```

```text
str
False
True
```

The first test fails, and the second passes. The test tells you which formats you can trust with your data. Run it for each format that you plan to use for storage. Use a sample of your own data. Do it before the first night that the job runs.

## How it works

`read_csv` does not know the types of the columns. It reads the characters and then tries a fixed order of types for each column: boolean, integer, float, and last text. A column becomes the first type that every non-missing value fits.

The rule explains every surprise of this chapter. The text `+32434086075` fits an integer, so `callee` is an integer. The text `0477123456` fits an integer too, and the integer has no leading zero.

You can write the rule in ten lines and compare it with `read_csv` on the call records:

```python
import pandas as pd


def guess(column: pd.Series) -> str:
    values = column.dropna()
    if values.isin(["True", "False"]).all():
        return "bool"
    if values.str.fullmatch(r"[+-]?\d+").all():
        return "int64"
    if values.str.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?").all():
        return "float64"
    return "str"


raw = pd.read_csv("data/calls.csv", dtype=str)
guessed = {name: guess(raw[name]) for name in raw.columns}
actual = pd.read_csv("data/calls.csv").dtypes.astype(str).to_dict()
print(guessed == actual)
print(guessed["callee"], guessed["duration_s"], guessed["start"])
```

```text
True
int64 float64 str
```

The rule gives the same nine types as `read_csv`. The guess is the first type in the order that fits, with no knowledge of what the column means. Real `read_csv` has more rules (thousands separators, dates, a `NaN` in an integer column makes a float), but this is the core. The dtype argument of `read_csv` replaces the guess for the columns that you name. The argument `parse_dates` adds one more step after the guess.

- **Invariant.** A column that you did not name gets the first type that fits all its values.
- **Failure.** A type that is good for the sample and wrong for the file. One dash makes a numeric column text.
- **Cost.** One extra pass over the characters. `usecols` skips the columns that you do not need, before the guess.

## Reference

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.sigs import show_signature

show_signature(pd.read_csv, ["filepath_or_buffer", "dtype", "parse_dates", "usecols", "nrows", "na_values", "index_col"])
show_signature(pd.DataFrame.to_csv, ["path_or_buf", "index"])
show_signature(pd.read_parquet, ["path", "columns", "filters"])
show_signature(pd.DataFrame.to_parquet, ["path", "index"])
show_signature(pd.DataFrame.to_json, ["path_or_buf", "orient", "lines", "date_format"])
show_signature(load_calls)
```

```text
read_csv(
    filepath_or_buffer: 'FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str]'
    index_col: 'IndexLabel | Literal[False] | None' = None
    usecols: 'UsecolsArgType' = None
    dtype: 'DtypeArg | None' = None
    nrows: 'int | None' = None
    na_values: 'Hashable | Iterable[Hashable] | Mapping[Hashable, Iterable[Hashable]] | None' = None
    parse_dates: 'bool | Sequence[Hashable] | None' = None
)  # 37 more parameters
NDFrame.to_csv(
    path_or_buf: 'FilePath | WriteBuffer[bytes] | WriteBuffer[str] | None' = None
    index: 'bool' = True
)  # 20 more parameters
read_parquet(
    path: 'FilePath | ReadBuffer[bytes]'
    columns: 'list[str] | None' = None
    filters: 'list[tuple] | list[list[tuple]] | None' = None
)  # 6 more parameters
DataFrame.to_parquet(
    path: 'FilePath | WriteBuffer[bytes] | None' = None
    index: 'bool | None' = None
)  # 7 more parameters
NDFrame.to_json(
    path_or_buf: 'FilePath | WriteBuffer[bytes] | WriteBuffer[str] | None' = None
    orient: "Literal['split', 'records', 'index', 'table', 'columns', 'values'] | None" = None
    date_format: 'str | None' = None
    lines: 'bool' = False
)  # 10 more parameters
load_calls(
    path: 'str | pathlib.Path | None' = None
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `read_csv(dtype=...)` | `None` | a dict of column to type; use it for every identifier | without it `callee` is `int64`, and `0477123456` becomes 477123456 |
| `read_csv(parse_dates=...)` | `None` | columns to convert to timestamps | without it `start` stays text; with the `Z` suffix the type is `datetime64[us, UTC]` |
| `read_csv(usecols=...)` | `None` | read only these columns | — (3 of 9 columns: 472,354 bytes against 2,177,698) |
| `read_csv(nrows=...)` | `None` | first n rows only | — |
| `read_csv(na_values=...)` | `None` | more strings that mean missing | a `-` in a numeric column makes the whole column `str`; `na_values=["-"]` keeps `float64` |
| `read_csv(index_col=...)` | `None` | use a column as the index | — |
| `to_csv(index=...)` | `True` | write the index as a column | read back as a column `Unnamed: 0` |
| `read_parquet(columns=...)` | `None` | read only these columns | — |
| `read_parquet(filters=...)` | `None` | skip rows that fail a test, at the read | — (Chapter 19: 776,300 of 1,000,000 rows, 13 MB against 101 MB) |
| `to_parquet(index=...)` | `None` | write the index or not | — |
| `to_json(date_format=...)` | `None` | `"iso"` writes timestamps as ISO text | the default is epoch milliseconds, and it warns with `Pandas4Warning` |
| `to_json(orient=..., lines=...)` | `None`, `False` | `orient="records", lines=True` writes one JSON object for each row | — |
| `load_calls(path=...)` | `None` | the file in `data/`, or your own path | — |

`read_csv` returns a DataFrame. It raises `FileNotFoundError` for a missing file, and `ParserError` for a file that is not valid CSV.

## What you have now

- `callee` is text, and `start` is a UTC timestamp.
- You know four arguments that make `read_csv` safe: `dtype`, `parse_dates`, `usecols`, `na_values`.
- You write CSV with `index=False`, and you do not trust CSV with types.
- You can prove that a file format keeps your types with `assert_frame_equal`.

The next chapter selects rows and columns from the loaded table.

Next: [Chapter 3, Selection](03-selection.md).
