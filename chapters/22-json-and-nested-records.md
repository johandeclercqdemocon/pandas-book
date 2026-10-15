# 22. JSON and nested records

> **Build** — `events_table(records)` and `call_summary(events, call_ids)`: a flat table with one row for each signalling event of a call trace, a summary with one row for each call, and a check of the summary against the call records.
>
> **Theory kept** — JSON nests objects and lists, and a table does not. `json_normalize` flattens nested objects into columns and a list of records into rows. A record that lacks a part gives missing values or no rows, so count the records at each step.
>
> **Source** — New. Data: [`data/traces.jsonl`](../data/traces.jsonl). Library: [`pdbook/traces.py`](../pdbook/traces.py).
>
> **Run this first** — `uv run python -m examples.ch22_json`, which is [`examples/ch22_json.py`](../examples/ch22_json.py). Exercises: [`exercises/22.md`](../exercises/22.md). Solutions: [`exercises/solutions/22.md`](../exercises/solutions/22.md).

## A record with a list inside

The file `data/traces.jsonl` has one JSON object on each line, one for each of 500 sampled calls. Each object has the call id, the caller, a `meta` object and a list of `events`:

```python
import json

from pdbook.traces import read_traces

records = read_traces()
print(len(records))
print(json.dumps(records[0])[:150])
print(sorted(records[0]))
print(sum("meta" not in r for r in records), sum(len(r["events"]) == 0 for r in records))
```

```text
500
{"call_id": 2572, "caller": "S0127", "events": [{"t_ms": 0, "type": "INVITE"}, {"t_ms": 138, "type": "RESPONSE", "code": 100}, {"t_ms": 248, "type": "
['call_id', 'caller', 'events', 'meta']
23 8
```

The structure is not the same for every line. 23 of the 500 records have no `meta`, and 8 have an empty list of events. A loader that assumes the structure fails on the first one, or gives a wrong answer.

The functions of this chapter are in [`pdbook/traces.py`](../pdbook/traces.py).

#### `pdbook.traces.read_traces`

```text
pdbook.traces.read_traces(
    path=None,
)
```

The function returns a list with one dict for each line of a JSON-lines file.

The table under `pdbook.traces.read_traces` in the Reference section of this chapter gives each parameter and what goes wrong with it.

`read_json(lines=True)` reads the file as a table, and it keeps the nested parts as Python objects:

```python
import pandas as pd

from pdbook.datasets import DATA

df = pd.read_json(DATA / "traces.jsonl", lines=True)
print(df.shape, df.dtypes.astype(str).to_dict())
print(type(df["meta"].iloc[0]).__name__, type(df["events"].iloc[0]).__name__)
print(df["meta"].isna().sum(), df["events"].map(len).eq(0).sum())
```

```text
(500, 4) {'call_id': 'int64', 'caller': 'str', 'events': 'object', 'meta': 'object'}
dict list
23 8
```

The columns `meta` and `events` have the dtype `object`: each cell is a dict or a list. You cannot group by a cell that is a list, and you cannot filter on a key of a dict with a mask. The next steps turn them into columns and rows.

#### `pd.read_json`

```text
pd.read_json(
    path_or_buf,
    *,
    orient=None,
    typ='frame',
    dtype=None,
    convert_axes=None,
    convert_dates=True,
    keep_default_dates=True,
    precise_float=False,
    date_unit=None,
    encoding=None,
    encoding_errors='strict',
    lines=False,
    chunksize=None,
    compression='infer',
    nrows=None,
    storage_options=None,
    dtype_backend=<no_default>,
    engine='ujson',
)
```

The function reads JSON into a DataFrame, or with `typ="series"` into a Series. Its defaults convert types, and [How it works](#how-it-works) shows three conversions that change the data.

The table under `pd.read_json` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Flatten the objects, then the list

`json_normalize` turns nested dicts into columns, with the path in the name:

```python
import pandas as pd

from pdbook.traces import read_traces

records = read_traces()
flat = pd.json_normalize(records, sep=".")
print(flat.columns.tolist())
print(flat.shape, flat[["meta.cell", "meta.codec", "meta.roaming"]].isna().sum().to_dict())
```

```text
['call_id', 'caller', 'events', 'meta.cell', 'meta.codec', 'meta.roaming']
(500, 6) {'meta.cell': 30, 'meta.codec': 126, 'meta.roaming': 23}
```

The three keys of `meta` are columns now, and a record with no `meta` has missing values in all three: 23 for `meta.roaming`. `meta.codec` has 126 missing values: the records with no `meta`, and the records where the codec is `None` because the call was not answered.

#### `pd.json_normalize`

```text
pd.json_normalize(
    data,
    record_path=None,
    meta=None,
    meta_prefix=None,
    record_prefix=None,
    errors='raise',
    sep='.',
    max_level=None,
)
```

The function turns a list of nested dicts into a flat table. With `record_path`, it makes one row for each element of a list inside each record.

The table under `pd.json_normalize` in the Reference section of this chapter gives each parameter and what goes wrong with it.

To get one row for each event, give the path to the list in `record_path` and the fields to carry along in `meta`:

```python
import pandas as pd

from pdbook.traces import read_traces

records = read_traces()
events = pd.json_normalize(records, record_path="events",
                           meta=["call_id", "caller", ["meta", "cell"]], errors="ignore")
print(events.shape, events.columns.tolist())
print(events["type"].value_counts().to_dict())
print(events["code"].value_counts(dropna=False).sort_index().to_dict())

exploded = pd.DataFrame(records).explode("events")
print(len(exploded), int(exploded["events"].isna().sum()))

try:
    pd.json_normalize(records, record_path="events", meta=["call_id", "caller", ["meta", "cell"]])
except KeyError as error:
    print("KeyError:", str(error)[:28])
```

```text
(2652, 6) ['t_ms', 'type', 'code', 'call_id', 'caller', 'meta.cell']
{'RESPONSE': 1394, 'INVITE': 492, 'ACK': 383, 'BYE': 383}
{100.0: 472, 180.0: 430, 200.0: 383, 408.0: 47, 486.0: 42, 503.0: 20, nan: 1258}
2660 8
KeyError: "Key 'meta' not found. To re
```

There are 2,652 events for 500 calls. The last two lines show a difference between two tools. `json_normalize` with `record_path` gives no row for a call with an empty list: 492 calls have at least one event, as the 492 `INVITE` rows show. `explode` gives one row for such a call, with a missing value:

2,660 rows, 8 of them missing. Choose by the question. "Every event" wants the first. "Every call, with its events if it has any" wants the second.

#### `pd.DataFrame.explode`

```text
pd.DataFrame.explode(
    self,
    column,
    ignore_index=False,
)
```

The method makes one row for each element of a list in a column. The other columns are repeated, and the index label is repeated.

The table under `pd.DataFrame.explode` in the Reference section of this chapter gives each parameter and what goes wrong with it.

The argument `errors="ignore"` matters. The last line of the block is the same call without it: a record that has no `meta` raises a `KeyError`. With it, the field is `NaN`.

## Build: the events table and the summary

`events_table` does the flattening, names the columns and sorts the events of each call in time. `call_summary` keeps one row for each call id that you pass, so that a call with no events is a row with `n_events` 0:

```python
import pandas as pd

from pdbook.traces import call_summary, events_table, read_traces

records = read_traces()
events = events_table(records)
summary = call_summary(events, [r["call_id"] for r in records])

print(events.shape, events.dtypes.astype(str).to_dict())
print(summary.shape, int(summary["established"].sum()), int((summary["n_events"] == 0).sum()))
print(summary.dropna().head(3).to_string())
print(summary["ring_ms"].describe().round(0).to_dict())
```

```text
(2652, 7) {'call_id': 'int64', 'caller': 'str', 'cell': 'str', 'codec': 'str', 't_ms': 'int64', 'type': 'str', 'code': 'float64'}
(500, 5) 383 8
         n_events  ring_ms  answer_ms  final_code  established
call_id                                                       
13749           6    232.0     8752.0       200.0         True
19802           6    914.0     4375.0       200.0         True
384             6    955.0     3264.0       200.0         True
{'count': 430.0, 'mean': 935.0, 'std': 363.0, 'min': 155.0, '25%': 677.0, '50%': 928.0, '75%': 1193.0, 'max': 1753.0}
```

`code` is `float64` because the `INVITE` and `ACK` events have no code, which is a missing value ([Chapter 5](05-missing-data.md)). 383 calls were established. The time to ringing has 430 values. The next check shows that they are the 383 answered calls and the 47 `noanswer` calls. Its median is 927.5 ms, which the table above rounds to 928.

#### `pdbook.traces.events_table`

```text
pdbook.traces.events_table(
    records,
)
```

The function returns one row for each event, with the `call_id`, `caller`, `cell` and `codec` of its call, sorted by call and time.

The table under `pdbook.traces.events_table` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.traces.call_summary`

```text
pdbook.traces.call_summary(
    events,
    call_ids,
)
```

The function returns one row for each call id: the number of events, the time to ringing and to answer, the last response code, and `established`.

The table under `pdbook.traces.call_summary` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Check the summary against the call records

The trace and the call record describe the same calls, so they must agree. An established call, one with a `200` response, must be `answered`:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.traces import call_summary, events_table, read_traces

records = read_traces()
summary = call_summary(events_table(records), [r["call_id"] for r in records])
status = load_calls().set_index("call_id").loc[summary.index, "status"]

print(pd.crosstab(status, summary["established"]).to_string())
print(bool((status[summary["established"]] == "answered").all()))
print(pd.crosstab(status, summary["ring_ms"].notna()).to_string())
empty = summary[summary["n_events"] == 0].index
print(status.loc[empty].value_counts().to_dict())
```

```text
established  False  True 
status                   
answered         7    383
busy            43      0
failed          20      0
noanswer        47      0
True
ring_ms   False  True 
status                
answered      7    383
busy         43      0
failed       20      0
noanswer      0     47
{'answered': 7, 'busy': 1}
```

All 383 established calls are `answered`, and no call of another status is established. The other side is a finding: 7 calls are `answered` and have no `200` in the trace. All 7 are among the 8 traces with an empty list of events.

The missing `200` is a missing trace and not evidence about the call. The 8th empty trace is a `busy` call. A check in one direction found no fault. The other direction found 7 records to send to the owner of the trace.

## How it works

`json_normalize` is a recursive walk over dicts. For each record it visits the keys. A value that is a dict is entered, and its keys are joined to the path with the separator (`meta` and `cell` give `meta.cell`). Any other value becomes a cell.

With `record_path`, the walk goes into that list. It makes one row for each element, and it copies the fields in `meta` onto each of those rows. The result is the same as nested Python loops, and you can write them:

```python
import pandas as pd

from pdbook.traces import read_traces

records = read_traces()

rows = []
for record in records:
    for event in record["events"]:
        meta = record.get("meta") or {}
        rows.append({"t_ms": event["t_ms"], "type": event["type"], "code": event.get("code"),
                     "call_id": record["call_id"], "meta.cell": meta.get("cell")})
by_hand = pd.DataFrame(rows)

by_pandas = pd.json_normalize(records, record_path="events", meta=["call_id", ["meta", "cell"]], errors="ignore")
print(by_hand.shape, by_pandas.shape)
print(bool((by_hand["t_ms"].to_numpy() == by_pandas["t_ms"].to_numpy()).all()))
print(by_hand["meta.cell"].isna().sum(), by_pandas["meta.cell"].isna().sum())
print(bool((by_hand["call_id"].to_numpy() == by_pandas["call_id"].to_numpy()).all()))
```

```text
(2652, 5) (2652, 5)
True
149 149
True
```

The two loops and `json_normalize` give the same number of rows and the same times and call ids. A missing `meta` is a missing cell in both, with `get` in the loop and `errors="ignore"` in pandas.

- **Invariant.** The number of rows is the number of elements in the lists, summed over the records. A record with an empty list adds none.
- **Failure.** A key that is missing in some records. Without `errors="ignore"` it raises, and with it, it is `NaN`.
- **Cost.** A Python loop over every element, in both versions. `json_normalize` is not a compiled operation, so a very large file needs a streaming reader.

`read_json` has a second walk: after the parse, it converts the columns with rules that look at the values and at the names. The next block reads one record with the defaults, and then with the three arguments that switch the conversions off:

```python
import io

import pandas as pd

text = '[{"msisdn": "0477123456", "created_at": 1788214410000, "rate": 0.3}]'
default = pd.read_json(io.StringIO(text))
kept = pd.read_json(io.StringIO(text), dtype=False, convert_dates=False, precise_float=True)
for name, df in [("default", default), ("kept", kept)]:
    print(f"{name:8s}", df.iloc[0].tolist(), df.dtypes.astype(str).tolist())
```

```text
default  [np.int64(477123456), Timestamp('2026-08-31 22:13:30'), np.float64(0.30000000000000004)] ['int64', 'datetime64[ms]', 'float64']
kept     ['0477123456', np.int64(1788214410000), np.float64(0.3)] ['str', 'int64', 'float64']
```

With the defaults, three values change. The phone number loses its leading zero, because the text looks like a number. The integer `created_at` becomes a timestamp, because the name ends with `_at`. The rate `0.3` comes back as `0.30000000000000004`, because the fast float parser is not exact. With `dtype=False`, `convert_dates=False` and `precise_float=True`, the values are as in the file. Read JSON with the types that you know, as you read a CSV file in [Chapter 2](02-input-and-output.md).

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pdbook.traces.read_traces` | A record with a list inside | one dict for each line of a JSON-lines file |
| `pd.read_json` | A record with a list inside | JSON as a table; the defaults convert types by value and by name |
| `pd.json_normalize` | Flatten the objects, then the list | nested dicts as columns; `record_path` gives one row for each element |
| `pd.DataFrame.explode` | Flatten the objects, then the list | one row for each element of a list; an empty list gives a row of `NaN` |
| `pdbook.traces.events_table` | Build: the events table and the summary | one row for each event, sorted by call and time |
| `pdbook.traces.call_summary` | Build: the events table and the summary | one row for each call id, events or not |

### Parameters

##### `pdbook.traces.read_traces`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | `None` | the file. With `None`, `data/traces.jsonl` | a path that does not exist raises `FileNotFoundError` |

##### `pd.read_json`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path_or_buf` | required | a path, a URL or an open file. Wrap a string of JSON in `io.StringIO` | in pandas 3.0, a string of JSON is read as a file name: `FileNotFoundError` |
| `orient` | `None` | the shape of the JSON: `'records'`, `'columns'`, `'index'`, `'split'`, `'values'` or `'table'`. With `None`, `'columns'` for a frame | an `orient` that does not fit the text raises an error that does not name the `orient`, such as `AttributeError` |
| `typ` | `'frame'` | `'frame'` or `'series'` | — |
| `dtype` | `None` | `None` and `True` infer types. `False` keeps them. A dict gives the type of each column | the inference turns the text `"0477"` into the integer 477 |
| `convert_axes` | `None` | convert the labels to types. With `None`, `True` for most `orient` values | with `True`, the keys `"1"` and `"2"` become the integers 1 and 2 |
| `convert_dates` | `True` | convert the columns that look like dates. A list names the columns | — |
| `keep_default_dates` | `True` | also convert columns by their name: ending with `_at` or `_time`, starting with `timestamp`, or named `modified`, `date` or `datetime` | a column `created_at` of integers becomes timestamps because of its name |
| `precise_float` | `False` | `True` uses the exact parser for floats | with `False`, `0.3` becomes `0.30000000000000004` |
| `date_unit` | `None` | the unit of number timestamps: `'s'`, `'ms'`, `'us'` or `'ns'`. With `None`, pandas guesses | — |
| `encoding` | `None` | the encoding of a binary input. `None` means UTF-8 | a Latin-1 file raises `UnicodeDecodeError` |
| `encoding_errors` | `'strict'` | what to do with bytes that the encoding cannot read | `'replace'` changes `é` to `�` with no error |
| `lines` | `False` | `True` reads one JSON object for each line | `meta` and `events` stay as dicts and lists. A JSON-lines file read without it raises `ValueError: Trailing data` |
| `chunksize` | `None` | return a reader of tables of this many lines. Only with `lines=True` | without `lines=True` it raises `ValueError` |
| `compression` | `'infer'` | the compression. `'infer'` uses the extension | — |
| `nrows` | `None` | read only the first lines. Only with `lines=True` | without `lines=True` it raises `ValueError` |
| `storage_options` | `None` | the connection options for a remote path | — |
| `dtype_backend` | `<no_default>` | not set gives NumPy types. `'numpy_nullable'` keeps an integer column with a null as `Int64` | with the default, an integer column with a null becomes `float64` |
| `engine` | `'ujson'` | the parser. `'pyarrow'` works only with `lines=True` | `engine="pyarrow"` without `lines=True` raises `ValueError` |

##### `pd.json_normalize`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `data` | required | a list of dicts, or one dict | — |
| `record_path` | `None` | the path to a list in each record: one row for each element | a record with an empty list gives no row. A record without the path raises `KeyError` |
| `meta` | `None` | fields of the record to copy onto each row. A list in the list is a path, such as `["meta", "cell"]` | a field with the same name as a key of the elements raises `ValueError`: use `meta_prefix` |
| `meta_prefix` | `None` | a text before the names of the `meta` columns | — |
| `record_prefix` | `None` | a text before the names of the columns from the list, such as `ev.` | — |
| `errors` | `'raise'` | `'ignore'` gives `NaN` for a missing meta field | `'raise'` raises `KeyError` for the 23 records with no `meta` |
| `sep` | `'.'` | the joiner of the path in the column names | — |
| `max_level` | `None` | the deepest level to flatten. With `None`, all levels | `max_level=0` leaves every nested dict as one cell |

##### `pd.DataFrame.explode`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `column` | required | the column of lists, or a list of columns with lists of the same length in each row | an empty list gives one row of missing values: 2,660 rows against 2,652. Lists of different lengths in two columns raise `ValueError` |
| `ignore_index` | `False` | `True` makes a new `RangeIndex` | with `False`, the labels repeat: 0, 0, 1, 2. The new column is `object`, even when every element is an integer |

##### `pdbook.traces.events_table`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `records` | required | the list of `read_traces` | calls with no events have no row. An empty list raises `KeyError` |

##### `pdbook.traces.call_summary`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `events` | required | the table of `events_table` | — |
| `call_ids` | required | the ids to report. Each one gets a row, with or without events | an id that has no trace gets a row of 0 events and `NaN`. It does not say whether the trace is missing or the id is wrong |


## What you have now

- You read JSON lines, and you count the records that lack a part.
- You flatten dicts with `json_normalize`, and lists with `record_path` or `explode`.
- You know that `json_normalize` drops a call with an empty list and `explode` keeps it.
- You check a derived table against a table that you trust, in both directions.

The next chapter uses the tables of this book to build features without leaking the future.

Next: [Chapter 23, Features and evaluation](23-features-and-evaluation.md).
