# 20. SQL and pandas

> **Build** — `monthly_report_sql(conn)`: the monthly report of Chapter 16 written as one SQL query over SQLite, with a proof that it gives the same 20 rows as the pandas chain, in every cell and every dtype.
>
> **Theory kept** — SQL and pandas answer the same questions with different tools. The database is strong at storage, indexes and joins on data that does not fit in memory. pandas is strong at the steps after the query. Pass values with parameters, and know which types the round trip changes.
>
> **Source** — New. Library: [`pdbook/sqlbridge.py`](../pdbook/sqlbridge.py). SQLite is in the Python standard library, so the chapter needs no server.
>
> **Run this first** — `uv run python -m examples.ch20_sql`, which is [`examples/ch20_sql.py`](../examples/ch20_sql.py). Exercises: [`exercises/20.md`](../exercises/20.md). Solutions: [`exercises/solutions/20.md`](../exercises/solutions/20.md).

## Write a table, read a query

`to_sql` writes a DataFrame as a table. `read_sql_query` runs a query and returns a DataFrame:

```python
import sqlite3

import pandas as pd

from pdbook.io import load_calls

conn = sqlite3.connect(":memory:")
calls = load_calls()
calls.assign(start=calls["start"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("calls", conn, index=False)

answered = pd.read_sql_query("SELECT COUNT(*) AS n FROM calls WHERE status = 'answered'", conn)
print(int(answered["n"].iloc[0]))
print(pd.read_sql_query("SELECT * FROM calls LIMIT 2", conn).dtypes.astype(str).to_dict())
```

```text
15526
{'call_id': 'int64', 'start': 'str', 'caller': 'str', 'callee': 'str', 'duration_s': 'float64', 'status': 'str', 'cell_id': 'str', 'codec': 'str', 'roaming': 'int64'}
```

The count is the 15,526 answered calls. The dtypes show what the round trip did: `start` is text. The code wrote it as an ISO string, and SQLite has no timestamp storage class.

`roaming` is `int64`, because SQLite stores a boolean as the integer 1 or 0. The section on how it works prints the storage classes. Convert on the way out:

```python
import sqlite3

import pandas as pd

from pdbook.sqlbridge import build_database

conn = build_database()
back = pd.read_sql_query("SELECT start, roaming FROM calls LIMIT 3", conn, parse_dates=["start"])
back["roaming"] = back["roaming"].astype(bool)
print(back.dtypes.astype(str).to_dict())
```

```text
{'start': 'datetime64[us, UTC]', 'roaming': 'bool'}
```

`parse_dates` converts the text to timestamps. A column that holds 0 and 1 and means a boolean needs `astype(bool)`. [Chapter 2](02-input-and-output.md) made the same point: a format with weak types needs types on the way out.

#### `pd.DataFrame.to_sql`

```text
pd.DataFrame.to_sql(
    self,
    name,
    con,
    *,
    schema=None,
    if_exists='fail',
    index=True,
    index_label=None,
    chunksize=None,
    dtype=None,
    method=None,
)
```

The method writes the table into a database table, and returns the number of rows written.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `name` | required | the name of the database table | — |
| `con` | required | a connection: a `sqlite3` connection, an SQLAlchemy engine or an ADBC connection | — |
| `schema` | `None` | the schema of the table, for a database that has schemas | — |
| `if_exists` | `'fail'` | what to do when the table exists: `'fail'`, `'replace'`, `'append'`, or `'delete_rows'`, which empties the table and keeps its definition | `fail` raises `ValueError` on a second run. `append` doubles the rows on a second run, with no error |
| `index` | `True` | write the index as a column | `index=True` adds a column `index` |
| `index_label` | `None` | the name of the index column | — |
| `chunksize` | `None` | the rows in each batch. With `None`, all rows at one time | — |
| `dtype` | `None` | the column types in the database: a dict of column to type. For `sqlite3`, a type name such as `"TEXT"` | — |
| `method` | `None` | the insert form: `None` for one row in each statement, `'multi'` for many rows in one statement, or a function | — |

A timestamp with a zone is written as text, such as `2026-09-01 10:00:00+00:00`, and a boolean as the integer 1 or 0.

#### `pd.read_sql_query`

```text
pd.read_sql_query(
    sql,
    con,
    index_col=None,
    coerce_float=True,
    params=None,
    parse_dates=None,
    chunksize=None,
    dtype=None,
    dtype_backend=<no_default>,
)
```

The function runs a query and returns the result as a DataFrame.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `sql` | required | the query text | — |
| `con` | required | the connection | — |
| `index_col` | `None` | a column, or columns, to use as the index | — |
| `coerce_float` | `True` | convert numbers of other types, such as `decimal.Decimal`, to float | — |
| `params` | `None` | the values for the placeholders: a tuple for `?`, a dict for `:name` | formatting the value into the text breaks on `O'Neil` and can change the query |
| `parse_dates` | `None` | columns to convert to timestamps, or a dict of column to format | without it, `start` is text |
| `chunksize` | `None` | return an iterator of tables of this many rows | the result is an iterator, used up after one pass ([Chapter 19](19-data-larger-than-memory.md)) |
| `dtype` | `None` | a type, or a dict of column to type, for the result | — |
| `dtype_backend` | `<no_default>` | not set gives NumPy types. `'numpy_nullable'` keeps an integer column with a null as `Int64` | with the default, an integer column with a null becomes `float64` |

#### `pdbook.sqlbridge.build_database`

```text
pdbook.sqlbridge.build_database(
    conn=None,
)
```

The function writes the four tables into SQLite, with `start` as ISO text, and returns the connection.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `conn` | `None` | the connection to write into. With `None`, a new database in memory | it replaces the four tables if they exist. A second call is not an error, and it removes any index that you made on them |

## Parameters

Never build a query with string formatting. A value that contains a quote breaks the query, and a value from outside can change it. Pass values with `params`:

```python
import sqlite3

import pandas as pd

conn = sqlite3.connect(":memory:")
pd.DataFrame({"name": ["O'Neil", "Peeters"], "n": [3, 5]}).to_sql("people", conn, index=False)

name = "O'Neil"
try:
    pd.read_sql_query(f"SELECT n FROM people WHERE name = '{name}'", conn)
except Exception as error:
    print(type(error).__name__)

safe = pd.read_sql_query("SELECT n FROM people WHERE name = ?", conn, params=(name,))
print(int(safe["n"].iloc[0]))
```

```text
DatabaseError
3
```

The first query is not valid SQL after the substitution, so it fails. A value of the form `x' OR '1'='1` does not fail, and it returns every row. The second exercise of this chapter runs it. The second form passes the value separately from the query text, and the database never reads it as SQL.

## The same report in two languages

The monthly report of [Chapter 16](16-method-chains-and-pipelines.md) is one chain of ten steps. In SQL it is one query. The two give the same result:

```python
import sqlite3

import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
from pdbook.report import monthly_report
from pdbook.sqlbridge import MONTHLY_REPORT_SQL, build_database, monthly_report_sql

print(MONTHLY_REPORT_SQL.strip())
print("SQLite", sqlite3.sqlite_version)

conn = build_database()
sql_report = monthly_report_sql(conn)
pandas_report = monthly_report(load_calls(), load_subscribers(), load_cells(), load_plans())
pd.testing.assert_frame_equal(sql_report, pandas_report[sql_report.columns])
print(sql_report.shape, "equal, dtypes included")
```

```text
SELECT s.plan                                              AS plan,
       s.city                                              AS home_city,
       COUNT(*)                                            AS calls,
       SUM(c.status = 'answered')                          AS answered,
       SUM(CASE WHEN c.status = 'answered'
                THEN CAST(MAX(1, CEIL(c.duration_s / 60.0)) AS INTEGER) ELSE 0 END)  AS billed_min,
       ROUND(SUM(CASE WHEN c.status = 'answered'
                THEN ROUND(MAX(1, CEIL(c.duration_s / 60.0)) * p.rate_per_min_eur, 2)
                ELSE 0 END), 2)                            AS revenue_eur,
       ROUND(1.0 * SUM(c.status = 'answered') / COUNT(*), 3) AS answer_rate
FROM calls c
JOIN subscribers s ON s.subscriber_id = c.caller
JOIN plans p       ON p.plan = s.plan
GROUP BY s.plan, s.city
ORDER BY s.plan, s.city
SQLite 3.50.4
(20, 7) equal, dtypes included
```

Compare the two side by side. The `JOIN` lines are the two `merge` steps of `enrich`. `GROUP BY` and the aggregate functions are `groupby` and `agg`. `CASE WHEN` is `np.where`. `CEIL(duration_s / 60.0)` is `np.ceil(duration_s / 60)`.

`CEIL` is a math function of SQLite. The documentation says that these functions exist from version 3.35 and need a build with them, so the block prints the version that ran. The test says that the two agree. This is the strongest check that a report is right: two implementations in two systems that were written separately.

#### `pdbook.sqlbridge.monthly_report_sql`

```text
pdbook.sqlbridge.monthly_report_sql(
    conn,
)
```

The function runs `MONTHLY_REPORT_SQL` and returns the report with the dtypes of the pandas version.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `conn` | required | a connection with the four tables of `build_database` | a database without the tables raises `DatabaseError`. `CEIL` is a math function of SQLite: the chapter prints the version that ran (3.50.4) |

## An index

A database makes a lookup fast with an index, in the same way as a pandas index ([Chapter 11](11-index-and-multiindex.md)):

```python
import time

from pdbook.sqlbridge import build_database

conn = build_database()
ids = list(range(1, 20001, 40))


def lookups():
    return [conn.execute("SELECT status FROM calls WHERE call_id = ?", (i,)).fetchone() for i in ids]


t0 = time.perf_counter()
before = lookups()
t_scan = time.perf_counter() - t0

conn.execute("CREATE INDEX ix_call_id ON calls(call_id)")
t0 = time.perf_counter()
after = lookups()
t_index = time.perf_counter() - t0

print(len(ids), before == after)
print(f"without index {t_scan * 1000:.0f} ms, with index {t_index * 1000:.1f} ms, ratio {t_scan / t_index:.0f}x")
assert before == after and t_scan / t_index > 10
```

```text
# output varies
500 True
without index 368 ms, with index 1.5 ms, ratio 244x
```

The block prints the time of 500 lookups without an index, where each one scans the table, and with an index. The answers are the same. The times depend on the hardware, and the assertion fails if the index is not at least 10 times faster on yours.

## Window functions

SQL has window functions, and they match [Chapter 14](14-ranks-running-totals-sessions.md). The top 3 answered calls of each caller, in SQL and in pandas:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.sqlbridge import build_database

conn = build_database()
query = """
SELECT caller, call_id, duration_s FROM (
    SELECT caller, call_id, duration_s,
           ROW_NUMBER() OVER (PARTITION BY caller ORDER BY duration_s DESC, call_id) AS rn
    FROM calls WHERE status = 'answered')
WHERE rn <= 3
"""
sql_top = pd.read_sql_query(query, conn)

calls = load_calls()
answered = calls[calls["status"] == "answered"]
pandas_top = (answered.sort_values(["caller", "duration_s", "call_id"], ascending=[True, False, True])
              .groupby("caller").head(3)[["caller", "call_id", "duration_s"]])

key = ["caller", "call_id"]
a = sql_top.sort_values(key).reset_index(drop=True)
b = pandas_top.sort_values(key).reset_index(drop=True)
print(len(a), a["caller"].nunique())
pd.testing.assert_frame_equal(a, b)
print("equal")
```

```text
1800 600
equal
```

Both give 1,800 rows, 3 for each of 600 callers, and the rows are the same. The tie rule is in both: longer first, then the lower `call_id`. Give a full sort key, so that the result does not depend on how an engine orders ties.

## Who does what

A rule for the work:

- **In the database:** filter rows, select columns, join large tables, aggregate to a size that fits in memory, and everything that an index speeds up.
- **In pandas:** the steps after the query: reshape, pivot, rolling windows, plots, models, anything that needs your own Python function.

A query that returns 600 rows from 20,000,000 is the right size to move to pandas. A `SELECT *` that moves 20,000,000 rows to filter them in pandas pays for the move and for the memory.

## How it works

SQLite is a library, not a server: the database is a file, or a memory area, in your process. It stores each value in one of five storage classes: null, integer, real, text and blob.

The class belongs to the value, and the declared type of a column is only a preference. There is no class for a timestamp or a boolean. This is why the chapter wrote the time as text and got the boolean back as an integer. An index is a B-tree of the values of a column, and the query planner decides whether to use it.

You can ask SQLite for the classes and for its plan:

```python
import sqlite3

from pdbook.sqlbridge import build_database

conn = build_database()
row = conn.execute(
    "SELECT typeof(call_id), typeof(start), typeof(duration_s), typeof(roaming), typeof(cell_id) "
    "FROM calls WHERE cell_id IS NULL AND status = 'failed' LIMIT 1").fetchone()
print(row)
print(conn.execute("SELECT typeof(1), typeof(1.5), typeof('x'), typeof(NULL), typeof(x'00')").fetchone())

query = "SELECT status FROM calls WHERE call_id = 12345"
before = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + query)]
conn.execute("CREATE INDEX ix_call_id ON calls(call_id)")
after = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + query)]
print(before)
print(after)
```

```text
('integer', 'text', 'null', 'integer', 'null')
('integer', 'real', 'text', 'null', 'blob')
['SCAN calls']
['SEARCH calls USING INDEX ix_call_id (call_id=?)']
```

The first line is one failed call without a cell: the id is an integer, the time is text, the duration and the cell are null, and the boolean is an integer. The second line lists the five classes. The plan before the index is a scan of the whole table, and after the index it is a search that uses it. The same query gave different plans, and the same answer.

- **Invariant.** A value has one of five classes, and a query plan is either a scan of the table or a search of an index.
- **Failure.** A type that SQLite does not have (a timestamp, a boolean) comes back as text or integer, and pandas gets `str` or `int64`.
- **Cost.** A scan costs one pass over the table for each query. An index costs space and time at each insert, and it saves the scan.

The declared type of a column is a preference that SQLite calls the affinity. When a value arrives, SQLite converts it to the class of the affinity if no information is lost. If not, SQLite stores the value as it is. The next block declares a column `INTEGER` and inserts five values:

```python
import sqlite3

import pandas as pd

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t (x INTEGER)")
conn.executemany("INSERT INTO t VALUES (?)", [("12",), ("abc",), (3.0,), (3.5,), (None,)])
print(conn.execute("SELECT x, typeof(x) FROM t").fetchall())
column = pd.read_sql_query("SELECT x FROM t", conn)["x"]
print(column.dtype, column.tolist())
```

```text
[(12, 'integer'), ('abc', 'text'), (3, 'integer'), (3.5, 'real'), (None, 'null')]
object [12, 'abc', 3, 3.5, None]
```

The text `"12"` became the integer 12, and `3.0` became the integer 3: both convert without loss. The text `abc` and the number `3.5` stayed as they were, in a column that says `INTEGER`. SQLite raised no error.

pandas receives four classes in one column and makes it `object`. A column of a database is not a promise about its values. Check the types after the read, as [Chapter 17](17-data-validation.md) does for a file.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.DataFrame.to_sql` | Write a table, read a query | the table written into a database; returns the row count |
| `pd.read_sql_query` | Write a table, read a query | the result of a query as a DataFrame; values go in `params` |
| `pdbook.sqlbridge.build_database` | Write a table, read a query | the four tables in SQLite, and the connection |
| `pdbook.sqlbridge.monthly_report_sql` | The same report in two languages | the monthly report as one query |

## What you have now

- You write a DataFrame to SQLite, query it, and convert the types that the round trip changed.
- You pass values with parameters, and never with string formatting.
- You have one report in two languages, with a test that they agree.
- You know that an index changes a lookup from a scan to a probe, and you measured the ratio.
- You split work between the database and pandas by the size of what moves.

The next chapter draws the results.

Next: [Chapter 21, Plots](21-plots.md).
