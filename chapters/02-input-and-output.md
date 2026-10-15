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

The six arguments above are the ones that you use every day. The function has 44. The block below prints all of them, and the table explains each one. Most of them you leave at the default, and the table says what the default does.

#### `pd.read_csv`

```text
pd.read_csv(
    filepath_or_buffer,
    *,
    sep=<no_default>,
    delimiter=None,
    header='infer',
    names=<no_default>,
    index_col=None,
    usecols=None,
    dtype=None,
    engine=None,
    converters=None,
    true_values=None,
    false_values=None,
    skipinitialspace=False,
    skiprows=None,
    skipfooter=0,
    nrows=None,
    na_values=None,
    keep_default_na=True,
    na_filter=True,
    skip_blank_lines=True,
    parse_dates=None,
    date_format=None,
    dayfirst=False,
    cache_dates=True,
    iterator=False,
    chunksize=None,
    compression='infer',
    thousands=None,
    decimal='.',
    lineterminator=None,
    quotechar='"',
    quoting=0,
    doublequote=True,
    escapechar=None,
    comment=None,
    encoding=None,
    encoding_errors='strict',
    dialect=None,
    on_bad_lines='error',
    low_memory=True,
    memory_map=False,
    float_precision=None,
    storage_options=None,
    dtype_backend=<no_default>,
)
```

The function reads a CSV file into a DataFrame. It guesses the type of each column that you do not name in `dtype`.

The table under `pd.read_csv` in the Reference section of this chapter gives each parameter and what goes wrong with it.

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

#### `pd.DataFrame.to_csv`

```text
pd.DataFrame.to_csv(
    self,
    path_or_buf=None,
    *,
    sep=',',
    na_rep='',
    float_format=None,
    columns=None,
    header=True,
    index=True,
    index_label=None,
    mode='w',
    encoding=None,
    compression='infer',
    quoting=None,
    quotechar='"',
    lineterminator=None,
    chunksize=None,
    date_format=None,
    doublequote=True,
    escapechar=None,
    decimal='.',
    errors='strict',
    storage_options=None,
)
```

The method writes the table as CSV text, to a file or, with no path, to a string.

The table under `pd.DataFrame.to_csv` in the Reference section of this chapter gives each parameter and what goes wrong with it.

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

#### `pd.read_parquet`

```text
pd.read_parquet(
    path,
    engine='auto',
    columns=None,
    storage_options=None,
    dtype_backend=<no_default>,
    filesystem=None,
    filters=None,
    to_pandas_kwargs=None,
    **kwargs,
)
```

The function reads a Parquet file or a directory of Parquet files.

The table under `pd.read_parquet` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pd.DataFrame.to_parquet`

```text
pd.DataFrame.to_parquet(
    self,
    path=None,
    *,
    engine='auto',
    compression='snappy',
    index=None,
    partition_cols=None,
    storage_options=None,
    filesystem=None,
    **kwargs,
)
```

The method writes the table as Parquet. With no path, it returns the file as `bytes`.

The table under `pd.DataFrame.to_parquet` in the Reference section of this chapter gives each parameter and what goes wrong with it.

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

#### `pd.DataFrame.to_json`

```text
pd.DataFrame.to_json(
    self,
    path_or_buf=None,
    *,
    orient=None,
    date_format=None,
    double_precision=10,
    force_ascii=True,
    date_unit='ms',
    default_handler=None,
    lines=False,
    compression='infer',
    index=None,
    indent=None,
    storage_options=None,
    mode='w',
)
```

The method writes the table as JSON, to a file or, with no path, to a string.

The table under `pd.DataFrame.to_json` in the Reference section of this chapter gives each parameter and what goes wrong with it.

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

#### `pdbook.io.load_calls`

```text
pdbook.io.load_calls(
    path=None,
)
```

The function reads the call records with the right types: text for the phone numbers and a UTC timestamp for `start`.

The table under `pdbook.io.load_calls` in the Reference section of this chapter gives each parameter and what goes wrong with it.

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

The parser does not guess on the whole file at one time. With `low_memory=True`, which is the default, it reads the file in chunks of rows, guesses a type for each chunk, and then joins the types. The pandas documentation warns that the join can leave one column with values of two types. The next block tests that on pandas 3.0.6. Each column has 300,000 rows of `7`, then one other value, then 10 more rows of `7`. The odd value is in a later chunk than the first rows:

```python
import io

import pandas as pd

n = 300_000
for tail, name in (("1.5", "float"), ("A1", "text"), ("", "gap")):
    text = "code\n" + "7\n" * n + tail + "\n" + "7\n" * 10
    col = pd.read_csv(io.StringIO(text), skip_blank_lines=False)["code"]
    kinds = sorted({type(v).__name__ for v in col})
    print(f"{name:6} {str(col.dtype):8} {kinds} first value {col.iloc[0]!r}")
```

```text
float  float64  ['float'] first value np.float64(7.0)
text   str      ['str'] first value '7'
gap    float64  ['float'] first value np.float64(7.0)
```

Each column has one type, and every value has that type. The join of the chunks takes the type that holds all the values: one float makes the integers floats, one text value makes every value text, and one gap makes a float. The warning about mixed types did not come back on this version.

The guess is still the guess of the whole column: the 300,000 integers became text because of one value. Name the type in `dtype` when you know it.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.read_csv` | Say what you know | a CSV file as a DataFrame; the types of columns that you do not name are guessed |
| `pd.DataFrame.to_csv` | Write without the index | the table as CSV text; no types are stored |
| `pd.read_parquet` | Parquet keeps the types | a Parquet file or directory as a DataFrame, with its types |
| `pd.DataFrame.to_parquet` | Parquet keeps the types | the table as Parquet, with its types |
| `pd.DataFrame.to_json` | JSON needs care | the table as JSON; timestamps need `date_format="iso"` |
| `pdbook.io.load_calls` | Build: load_calls and a round-trip test | the call records with text phone numbers and a UTC `start` |

### Parameters

##### `pd.read_csv`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `filepath_or_buffer` | required | a path, a URL or an open file. `io.StringIO(text)` reads a string | — |
| `sep` | `<no_default>` | the character between fields. Not set means `','` | a file with `;` read with the default gives one column, named `'a;b'` |
| `delimiter` | `None` | another name for `sep` | `sep` and `delimiter` together raise `ValueError` |
| `header` | `'infer'` | the row number of the column names. `'infer'` means row 0, or no header row when you give `names` | `header=None` on a file with a header row reads the names as data, and every column becomes `str` |
| `names` | `<no_default>` | the column names to use | with a header row in the file, add `header=0`. Without it, the old names become the first data row, and the columns become `str` |
| `index_col` | `None` | a column, or a list of columns, to use as the index | — |
| `usecols` | `None` | read only these columns, by name or position | — (3 of 9 columns: 472,354 bytes against 2,177,698) |
| `dtype` | `None` | a dict of column to type. The named columns skip the guess. Use it for every identifier | without it `callee` is `int64`, and `0477123456` becomes 477123456 |
| `engine` | `None` | the parser: `'c'`, `'python'` or `'pyarrow'`. `None` means `'c'`, or `'python'` for an option that only Python supports | `'pyarrow'` does not support all options: with `nrows` it raises `ValueError` |
| `converters` | `None` | a dict of column to a function that converts each text value | with `dtype` for the same column, pandas ignores the `dtype` and gives a `ParserWarning` |
| `true_values` | `None` | more strings that mean `True` | `true_values=["yes"]` alone leaves `no` as text, so the column is `str`. Give `false_values` too |
| `false_values` | `None` | more strings that mean `False` | the same: both lists are necessary to get a `bool` column |
| `skipinitialspace` | `False` | remove the spaces after each separator | without it, the header `a, b` gives the column name `' b'`, with a space |
| `skiprows` | `None` | a number of lines to skip at the start, or a list of line numbers | `skiprows=1` skips the header line, and the first data row becomes the header. `skiprows=[1]` skips the first data row |
| `skipfooter` | `0` | the number of lines to skip at the end | the `'c'` engine does not support it. pandas changes to the `'python'` engine and gives a `ParserWarning` |
| `nrows` | `None` | read only the first n data rows, to look at a large file | — |
| `na_values` | `None` | more strings that mean missing, as a list or as a dict for each column | a `-` in a numeric column makes the whole column `str`. `na_values=["-"]` keeps `float64` |
| `keep_default_na` | `True` | also use the built-in list of missing markers, such as `NA` and the empty string | with `False` and no `na_values`, `NA` and the empty field stay as the strings `'NA'` and `''` |
| `na_filter` | `True` | look for missing markers at all | with `False`, an empty field is the string `''`, and a numeric column with a gap becomes `str` |
| `skip_blank_lines` | `True` | skip empty lines | with `False`, an empty line is a row of `NaN`, and an integer column becomes `float64` |
| `parse_dates` | `None` | columns to convert to timestamps | without it `start` stays text. With the `Z` suffix the type is `datetime64[us, UTC]` |
| `date_format` | `None` | the format of the dates in `parse_dates`, such as `'%d/%m/%Y'` | a format that does not match leaves the column as `str`, with no warning |
| `dayfirst` | `False` | read `01/02/2026` as 1 February. With `False`, it is 2 January | with the default, `01/02/2026` is 2 January. A column that also holds `13/02/2026` stays `str`, with no warning |
| `cache_dates` | `True` | convert each distinct date string once | — |
| `iterator` | `False` | return a reader that gives the file in parts with `get_chunk` | the result is a `TextFileReader`, not a DataFrame |
| `chunksize` | `None` | return a reader that gives DataFrames of this many rows ([Chapter 19](19-data-larger-than-memory.md)) | the result is a `TextFileReader`, not a DataFrame. Iterate it |
| `compression` | `'infer'` | the compression of the file. `'infer'` uses the extension, such as `.gz` or `.zip` | — |
| `thousands` | `None` | the thousands separator | without it, `"1,234"` stays text. With `thousands=","` it is 1234 |
| `decimal` | `'.'` | the decimal point. Use `','` for European numbers | a European file read with the default gives `1,5` as text |
| `lineterminator` | `None` | the character that ends a line. Only the `'c'` engine accepts it | — |
| `quotechar` | `'"'` | the character that starts and ends a quoted field. A separator inside quotes is part of the value | — |
| `quoting` | `0` | the quoting rule, as a `csv.QUOTE_*` number. `0` is `csv.QUOTE_MINIMAL` | — |
| `doublequote` | `True` | read two quote characters inside a quoted field as one | — |
| `escapechar` | `None` | the character that escapes a separator or a quote | — |
| `comment` | `None` | a character that starts a comment. The rest of the line is not read | the character also cuts a value: `x#1,2` with `comment="#"` gives the row `x`, `NaN` |
| `encoding` | `None` | the text encoding. `None` means `'utf-8'` | a Latin-1 file with `é` raises `UnicodeDecodeError`. Use `encoding="latin-1"` |
| `encoding_errors` | `'strict'` | what to do with bytes that the encoding cannot read | `'replace'` reads `café` as `caf�`, with no error. The data are then changed |
| `dialect` | `None` | a `csv.Dialect` that sets the separator and the quoting in one object | — |
| `on_bad_lines` | `'error'` | what to do with a line that has too many fields: `'error'`, `'warn'` or `'skip'` | `'skip'` drops the line with no message. The row count is then lower than the line count |
| `low_memory` | `True` | parse the file in chunks to use less memory | the documentation warns about mixed types in one column. On pandas 3.0.6 the section [How it works](#how-it-works) shows one type for the whole column |
| `memory_map` | `False` | map the file into memory instead of a normal read | — |
| `float_precision` | `None` | the converter for floats: `None` or `'high'`, `'legacy'`, or `'round_trip'` | — |
| `storage_options` | `None` | the connection options for a remote file, such as S3 | — |
| `dtype_backend` | `<no_default>` | not set gives NumPy types. `'numpy_nullable'` or `'pyarrow'` gives types that hold a gap | with the default, an integer column with a gap becomes `float64`. With `'numpy_nullable'` it is `Int64` |

##### `pd.DataFrame.to_csv`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path_or_buf` | `None` | a path or an open file. With `None`, the method returns the text as a string | — |
| `sep` | `','` | the character between fields | — |
| `na_rep` | `''` | the text for a missing value | with `na_rep="NULL"`, a reader must know that `NULL` means missing |
| `float_format` | `None` | a format for floats, such as `'%.2f'` | the file keeps only the digits of the format: 0.123456 comes back as 0.12 |
| `columns` | `None` | the columns to write, in this order | — |
| `header` | `True` | write the column names. A list writes other names | — |
| `index` | `True` | write the index as a column | read back as a column `Unnamed: 0` |
| `index_label` | `None` | the name of the index column in the header | — |
| `mode` | `'w'` | the file mode: `'w'` replaces the file, `'a'` appends, `'x'` refuses to replace | `'a'` writes the header again, in the middle of the file. `'x'` on a file that exists raises `FileExistsError` |
| `encoding` | `None` | the text encoding. `None` means `'utf-8'` | — |
| `compression` | `'infer'` | the compression. `'infer'` uses the extension of the path | — (`.gz`: 22,215 bytes against 48,892 for 10,000 integers) |
| `quoting` | `None` | the quoting rule, as a `csv.QUOTE_*` number. `None` means `csv.QUOTE_MINIMAL` | — |
| `quotechar` | `'"'` | the quote character | — |
| `lineterminator` | `None` | the end of a line. `None` means the line end of the system | — |
| `chunksize` | `None` | the number of rows to write at one time | — |
| `date_format` | `None` | a format for timestamps | a format without `%z` drops the time zone: `2026-08-31 22:13:30+00:00` becomes `2026-08-31 22:13` |
| `doublequote` | `True` | write a quote inside a field as two quotes | — |
| `escapechar` | `None` | the character that escapes a separator or a quote | — |
| `decimal` | `'.'` | the decimal point | with the default `sep=","`, each number is quoted, as `"1,5"`. A reader with the default `decimal` reads it as text. Use `sep=";"` with it |
| `errors` | `'strict'` | what to do with characters that the encoding cannot write | — |
| `storage_options` | `None` | the connection options for a remote path | — |

##### `pd.read_parquet`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | required | a file, a directory or an open binary file | — |
| `engine` | `'auto'` | the library: `'pyarrow'` or `'fastparquet'`. `'auto'` tries `pyarrow` first | `engine="fastparquet"` raises `ImportError` here, because the package is not installed |
| `columns` | `None` | read only these columns | a name that is not in the file raises an error from `pyarrow` |
| `storage_options` | `None` | the connection options for a remote path | — |
| `dtype_backend` | `<no_default>` | not set gives NumPy types. `'pyarrow'` gives Arrow types, such as `int64[pyarrow]` | — |
| `filesystem` | `None` | a file system object of `pyarrow`, for remote storage | — |
| `filters` | `None` | conditions such as `[("a", "<", 10)]`. Rows that fail are not read | — ([Chapter 19](19-data-larger-than-memory.md): 776,300 of 1,000,000 rows, 13 MB against 101 MB) |
| `to_pandas_kwargs` | `None` | arguments for the conversion of `pyarrow` to pandas | a key that pandas also sets, such as `types_mapper`, raises `TypeError` |
| `**kwargs` | — | more arguments for the engine. For `pyarrow`, they go to `pyarrow.parquet.read_table` | — |

##### `pd.DataFrame.to_parquet`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | `None` | a file, a directory for `partition_cols`, or an open binary file. With `None`, the result is `bytes` | — |
| `engine` | `'auto'` | the library. `'auto'` tries `pyarrow` first | — |
| `compression` | `'snappy'` | the compression: `'snappy'`, `'gzip'`, `'brotli'`, `'lz4'`, `'zstd'` or `None` | — |
| `index` | `None` | `True` writes the index as data. `False` drops it. `None` writes a `RangeIndex` as metadata only, and any other index as data | with `index=False`, the labels `a`, `b` come back as 0, 1 |
| `partition_cols` | `None` | columns that split the data into one directory for each value, such as `cell=A` | the column comes back as the last column, with the type `category` |
| `storage_options` | `None` | the connection options for a remote path | — |
| `filesystem` | `None` | a file system object of `pyarrow` | — |
| `**kwargs` | — | more arguments for the engine | — |

##### `pd.DataFrame.to_json`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path_or_buf` | `None` | a path or an open file. With `None`, the result is a string | — |
| `orient` | `None` | the shape of the JSON. `None` means `'columns'` for a DataFrame: one object for each column. `'records'` gives one object for each row | — |
| `date_format` | `None` | `'iso'` writes timestamps as ISO text. `None` means `'epoch'` | the default is epoch milliseconds, and it warns with `Pandas4Warning` |
| `double_precision` | `10` | the number of decimals for floats. The maximum is 15 | `1/3` is written as `0.3333333333`. A value of 16 raises `ValueError` |
| `force_ascii` | `True` | write every character that is not ASCII as an escape | `café` is written as `caf\u00e9`. Use `force_ascii=False` for text that people read |
| `date_unit` | `'ms'` | the time unit of the timestamps | the default drops the microseconds: `.123456` is written as `.123` |
| `default_handler` | `None` | a function for a value that JSON cannot hold | with `None`, an object of your own class is written as `{}`, with no error |
| `lines` | `False` | with `orient="records"`, one JSON object on each line | with another `orient`, it raises `ValueError` |
| `compression` | `'infer'` | the compression. `'infer'` uses the extension | — |
| `index` | `None` | write the index. It has an effect only for some values of `orient` | with the default `orient`, `index=False` is ignored, and the labels are still written |
| `indent` | `None` | the number of spaces for each level, for JSON that people read | — |
| `storage_options` | `None` | the connection options for a remote path | — |
| `mode` | `'w'` | `'w'` replaces the file. `'a'` appends | `'a'` works only with `lines=True` and `orient="records"`. Otherwise it raises `ValueError` |

##### `pdbook.io.load_calls`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | `None` | the CSV file. With `None`, the file `data/calls.csv` | — |


## What you have now

- `callee` is text, and `start` is a UTC timestamp.
- You know four arguments that make `read_csv` safe: `dtype`, `parse_dates`, `usecols`, `na_values`.
- You write CSV with `index=False`, and you do not trust CSV with types.
- You can prove that a file format keeps your types with `assert_frame_equal`.

The next chapter selects rows and columns from the loaded table.

Next: [Chapter 3, Selection](03-selection.md).
