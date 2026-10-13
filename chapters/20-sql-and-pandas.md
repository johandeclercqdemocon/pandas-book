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
without index 365 ms, with index 2.3 ms, ratio 160x
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

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.sqlbridge import build_database, monthly_report_sql

show_signature(pd.DataFrame.to_sql, ["name", "con", "index", "if_exists"])
show_signature(pd.read_sql_query, ["sql", "con", "params", "parse_dates"])
show_signature(build_database)
show_signature(monthly_report_sql)
```

```text
NDFrame.to_sql(
    name: 'str'
    con
    if_exists: "Literal['fail', 'replace', 'append', 'delete_rows']" = 'fail'
    index: 'bool' = True
)  # 6 more parameters
read_sql_query(
    sql
    con
    params: 'list[Any] | Mapping[str, Any] | None' = None
    parse_dates: 'list[str] | dict[str, str] | dict[str, dict[str, Any]] | None' = None
)  # 5 more parameters
build_database(
    conn: 'sqlite3.Connection | None' = None
)
monthly_report_sql(
    conn: 'sqlite3.Connection'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `to_sql(name, con, index=...)` | required, `True` | write a table | `index=True` adds a column `index` |
| `to_sql(if_exists=...)` | `'fail'` | what to do when the table exists | `fail` raises an error on a second run |
| `read_sql_query(sql, con)` | required | run a query and return a DataFrame | — |
| `read_sql_query(params=...)` | `None` | values passed apart from the query text | formatting the value into the text breaks on `O'Neil` and can change the query |
| `read_sql_query(parse_dates=...)` | `None` | columns to convert to timestamps | without it, `start` is text |
| `build_database(conn=...)` | `None` | write the four tables into SQLite, in memory when `conn` is not given | — |
| `monthly_report_sql(conn)` | required | the monthly report as one query | `CEIL` is a math function of SQLite; the chapter prints the version that ran (3.50.4) |

`read_sql_query` returns a DataFrame. Booleans come back as integers and timestamps as text.

## What you have now

- You write a DataFrame to SQLite, query it, and convert the types that the round trip changed.
- You pass values with parameters, and never with string formatting.
- You have one report in two languages, with a test that they agree.
- You know that an index changes a lookup from a scan to a probe, and you measured the ratio.
- You split work between the database and pandas by the size of what moves.

The next chapter draws the results.

Next: [Chapter 21, Plots](21-plots.md).
