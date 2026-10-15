# 14. Ranks, running totals and sessions

> **Build** — `sessionize(calls, gap)`: a function that groups the calls of each subscriber into sessions, where a quiet period longer than `gap` starts a new session, with tests that the sessions cover every call and do not depend on the row order.
>
> **Theory kept** — A rank, a running total and a "time since the previous event" are window functions: each row gets a value from its neighbours in a group. The idiom for sessions is three steps: sort, flag the rows that start a session, take the running sum of the flags.
>
> **Source** — New. Library: [`pdbook/sessions.py`](../pdbook/sessions.py).
>
> **Run this first** — `uv run python -m examples.ch14_sessions`, which is [`examples/ch14_sessions.py`](../examples/ch14_sessions.py). Exercises: [`exercises/14.md`](../exercises/14.md). Solutions: [`exercises/solutions/14.md`](../exercises/solutions/14.md).

## Rank

`rank` gives each value its position in the sorted order. The argument `method` decides what happens with ties:

```python
import pandas as pd

x = pd.Series([10, 20, 20, 30])
for method in ["average", "min", "max", "dense", "first"]:
    print(f"{method:8s}", x.rank(method=method).tolist())
```

```text
average  [1.0, 2.5, 2.5, 4.0]
min      [1.0, 2.0, 2.0, 4.0]
max      [1.0, 3.0, 3.0, 4.0]
dense    [1.0, 2.0, 2.0, 3.0]
first    [1.0, 2.0, 3.0, 4.0]
```

The two values of 20 share the ranks 2 and 3. `average` gives both 2.5. `min` gives both 2, and `max` gives both 3. `dense` gives both 2 and the next value 3, with no gap.

`first` breaks the tie by the order of the rows. Choose by the question. "One more than the number of values that are strictly lower" is `min`: 10, 20, 20, 30 get 1, 2, 2, 4. With `ascending=False` it counts the strictly higher values. "A number from 1 to n with no ties" is `first`.

#### `pd.Series.rank`

```text
pd.Series.rank(
    self,
    axis=0,
    method='average',
    numeric_only=False,
    na_option='keep',
    ascending=True,
    pct=False,
)
```

The method returns the rank of each value, as `float64`. The DataFrame method ranks each column.

The table under `pd.Series.rank` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Top n in each group

The tool is `rank` inside a `groupby`, or `sort_values` and `head`:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
answered = calls[calls["status"] == "answered"].copy()

answered["rank"] = answered.groupby("caller")["duration_s"].rank(method="first", ascending=False)
top3 = answered[answered["rank"] <= 3]
print(len(top3), top3["caller"].nunique())

same = (answered.sort_values(["caller", "duration_s"], ascending=[True, False])
        .groupby("caller").head(3))
print(len(same), set(same.index) == set(top3.index))
print(top3.groupby("caller").size().value_counts().to_dict())
```

```text
1800 600
1800 True
{3: 600}
```

Both ways give 1,800 rows: 3 calls for each of the 600 subscribers. The sets of rows are the same. The `rank` form keeps the rank as a column, and the sort form is shorter.

In both forms, the order of the rows breaks a tie at the third place: `method="first"` in the first form, and a stable sort in the second. Pass a full sort key when ties matter.

The last line shows that every subscriber has at least 3 answered calls: all 600 groups have size 3. A group with fewer than 3 rows shows a smaller size.

#### `pd.core.groupby.DataFrameGroupBy.head`

```text
pd.core.groupby.DataFrameGroupBy.head(
    self,
    n=5,
)
```

The method returns the first `n` rows of each group, in the order of the table. `tail` returns the last ones.

The table under `pd.core.groupby.DataFrameGroupBy.head` in the Reference section of this chapter gives each parameter and what goes wrong with it.

For the top rows of the whole table, without groups, `nlargest` is one call. It sorts only as much as it needs:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
print(calls.nlargest(3, "duration_s")[["call_id", "caller", "duration_s"]].to_string(index=False))

ties = pd.DataFrame({"v": [5, 9, 9, 7, 9]})
for keep in ["first", "last", "all"]:
    print(f"{keep:5s}", ties.nlargest(2, "v", keep=keep).index.tolist())
```

```text
 call_id caller  duration_s
   19895  S0013      3836.0
    5167  S0576      3354.0
   10196  S0406      2921.0
first [1, 2]
last  [4, 2]
all   [1, 2, 4]
```

The three longest calls last 3,836, 3,354 and 2,921 seconds. The small table shows what `keep` does when the value 9 occurs three times and you ask for two rows. `first` takes the first two in the table, `last` takes the last two, and `all` takes all three: you get more rows than you asked for.

#### `pd.DataFrame.nlargest`

```text
pd.DataFrame.nlargest(
    self,
    n,
    columns,
    keep='first',
)
```

The method returns the `n` rows with the largest values in `columns`, in descending order. `nsmallest` is the opposite.

The table under `pd.DataFrame.nlargest` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Running totals

`cumsum`, `cumcount`, `cummax` and `cummin` give a value from the start of the group to the current row. They need an order, so sort first:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().sort_values(["caller", "start"])
calls["talk_min"] = calls["duration_s"].fillna(0) / 60
calls["n_so_far"] = calls.groupby("caller").cumcount() + 1
calls["talk_so_far"] = calls.groupby("caller")["talk_min"].cumsum()

last = calls.groupby("caller").tail(1)
print(int(last["n_so_far"].sum()), round(float(last["talk_so_far"].sum()), 1))
print(len(calls), round(float(calls["talk_min"].sum()), 1))
```

```text
20000 34372.5
20000 34372.5
```

The last row of each group carries the total of the group, so the sum of the last rows is the sum of the table. That is the check, and it is the same as the totals check of [Chapter 8](08-group-by.md). Without the `sort_values`, `cumsum` follows the row order of the file, and the "so far" is not "so far in time".

#### `pd.core.groupby.DataFrameGroupBy.cumcount`

```text
pd.core.groupby.DataFrameGroupBy.cumcount(
    self,
    ascending=True,
)
```

The method numbers the rows of each group from 0, in the order of the table.

The table under `pd.core.groupby.DataFrameGroupBy.cumcount` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Time since the previous event

On a timestamp column, `groupby(...).diff()` gives the time since the previous row of the same group. It is `NaT` for the first row of each group:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().sort_values(["caller", "start"])
gap = calls.groupby("caller")["start"].diff()
print(int(gap.isna().sum()), calls["caller"].nunique())
print(gap.dropna().median().round("h"))
print(int((gap.dropna() < pd.Timedelta("1min")).sum()))
```

```text
600 600
0 days 10:00:00
49
```

There is one `NaT` for each of the 600 subscribers: the first call. The median gap between two calls of one subscriber is 10 hours, and 49 gaps are under a minute.

## Sessions

A session is a run of events with no gap larger than a threshold. The idiom has three steps:

1. Sort by group and time.
2. Mark the rows that start a session: the first row of a group, or a gap larger than the threshold.
3. Take the running sum of the marks inside the group. The sum is the session number.

```python
import pandas as pd

t = pd.to_datetime(["10:00", "10:05", "10:50", "10:52", "11:30"], format="%H:%M")
df = pd.DataFrame({"caller": "A", "start": t})
gap = df.groupby("caller")["start"].diff()
new = gap.isna() | (gap > pd.Timedelta("30min"))
df["session"] = new.groupby(df["caller"]).cumsum()
print(df.assign(gap=gap.dt.total_seconds() / 60, new=new)[["gap", "new", "session"]].to_string())
```

```text
    gap    new  session
0   NaN   True        1
1   5.0  False        1
2  45.0   True        2
3   2.0  False        2
4  38.0   True        3
```

The gaps are 5, 45, 2 and 38 minutes. Two of them are larger than 30, so there are three sessions: the first two calls, the next two, and the last one. The marks are 1 at the start of each session, and `cumsum` turns them into 1, 1, 2, 2, 3.

## Build: sessionize

`sessionize` applies the three steps to the call records. It sorts inside the function, so the result does not depend on the order of the rows that you pass. It uses `>`, so a gap of exactly `gap` stays in the session. Run it for several gaps:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.sessions import session_table, sessionize

calls = load_calls()
print(f"{'gap':>6s} {'sessions':>9s} {'longest':>8s} {'covers':>7s}")
for gap in ("1min", "5min", "30min", "2h", "1D"):
    table = session_table(sessionize(calls, gap))
    print(f"{gap:>6s} {len(table):>9,d} {int(table['calls'].max()):>8d} {int(table['calls'].sum()):>7,d}")
```

```text
   gap  sessions  longest  covers
  1min    19,951        3  20,000
  5min    19,691        4  20,000
 30min    18,420        8  20,000
    2h    15,450       30  20,000
    1D     5,866      628  20,000
```

The last column is the check: the sessions cover all 20,000 calls for every gap. The number of sessions falls as the gap grows, from 19,951 for one minute to 5,866 for one day, and it never rises. In this data the calls spread over a month, and 17,196 of the 18,420 sessions of 30 minutes have a single call. The generator of the data does not model sessions, so the numbers show no real structure. The code is the same for call records that have bursts.

Two more tests, which are properties of the idea of a session:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.sessions import session_table, sessionize

calls = load_calls()
a = sessionize(calls)
b = sessionize(calls.sample(frac=1, random_state=3))
print(a.equals(b))

counts = [len(session_table(sessionize(calls, g))) for g in ("1min", "5min", "30min", "2h", "1D")]
print(counts == sorted(counts, reverse=True))

table = session_table(a)
print(table.sort_values("calls", ascending=False).head(2)[["session_id", "calls", "first_start", "last_start"]]
      .to_string(index=False))
```

```text
True
True
session_id  calls               first_start                last_start
 S0437-093      8 2026-09-08 15:38:24+00:00 2026-09-08 16:51:00+00:00
 S0437-128      8 2026-09-11 16:22:08+00:00 2026-09-11 18:12:12+00:00
```

The first line is `True`: a shuffled input gives the same table. The second line is `True`: more gap gives fewer or equal sessions. The last block shows the two longest sessions. Both belong to subscriber S0437 and have 8 calls each, the first between 15:38 and 16:51 UTC on 8 September.

The two functions are in [`pdbook/sessions.py`](../pdbook/sessions.py).

#### `pdbook.sessions.sessionize`

```text
pdbook.sessions.sessionize(
    calls,
    gap='30min',
)
```

The function returns a copy of `calls` with two new columns: `session` (1, 2, … for each caller) and `session_id` (such as `S0001-001`).

The table under `pdbook.sessions.sessionize` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.sessions.session_table`

```text
pdbook.sessions.session_table(
    sessions,
)
```

The function returns one row for each session: `session_id`, `caller`, `first_start`, `last_start`, `calls` and `talk_s`.

The table under `pdbook.sessions.session_table` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## How it works

A session number is a running sum of boundary marks. First sort by caller and time. A row then starts a new session when its gap to the previous row is large. The first row of a caller also starts a session.

Mark those rows with 1 and the others with 0, and the running sum inside each caller is the session number. This is a vectorized form of a small state machine: walk the rows in order, keep the caller and the time of the previous row, and add 1 to the counter at each boundary.

You can write the state machine with a plain loop and compare it with `sessionize`:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.sessions import sessionize

calls = load_calls()
ordered = calls.sort_values(["caller", "start", "call_id"], kind="stable").reset_index(drop=True)
limit = pd.Timedelta("30min")

session, previous_caller, previous_time, counter = [], None, None, 0
for caller, start in zip(ordered["caller"], ordered["start"]):
    if caller != previous_caller:
        counter = 1
    elif start - previous_time > limit:
        counter += 1
    session.append(counter)
    previous_caller, previous_time = caller, start

by_pandas = sessionize(calls, "30min")["session"].tolist()
print(len(session), session == by_pandas)
print(max(session), int(ordered.groupby("caller").cumcount().max()) + 1)
```

```text
20000 True
347 628
```

The loop and `sessionize` give the same session number for each of the 20,000 rows. The loop is easy to read and slow, and the vectorized form is the same logic as one running sum. The last line shows the longest session number of any caller (the most sessions of one subscriber), and the largest number of calls of one caller, 628, which bounds it.

- **Invariant.** Session numbers never decrease inside a caller, and they go up by 1 at a boundary.
- **Failure.** Rows in the wrong order: the gap to the previous row is then a gap to a different call. Always sort inside the function.
- **Cost.** One sort, one grouped `diff`, one grouped `cumsum`. The sort is the largest part.

The failure line is easy to see. The next block counts the session starts with the same three steps. It counts once in the order of the file and once after the sort:

```python
import pandas as pd

from pdbook.io import load_calls


def count_starts(df, gap="30min"):
    step = df.groupby("caller")["start"].diff()
    return int((step.isna() | (step > pd.Timedelta(gap))).sum()), int((step < pd.Timedelta(0)).sum())


calls = load_calls()
print("file order:", count_starts(calls))
print("sorted    :", count_starts(calls.sort_values(["caller", "start"])))
```

```text
file order: (18151, 403)
sorted    : (18420, 0)
```

The file order gives 18,151 sessions, and the sorted table gives 18,420, which is the number of `session_table`. The second number of each line is the count of negative gaps. The 1,000 late records at the end of the file make 403 of them: a call that comes after a later call of the same caller.

A negative gap is never larger than 30 minutes, so the late call joins a session in which it does not belong. The result has fewer sessions and no error. This is why `sessionize` sorts inside the function and does not trust its caller.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.Series.rank` | Rank | the rank of each value; `method` decides ties |
| `pd.core.groupby.DataFrameGroupBy.head` | Top n in each group | the first `n` rows of each group, in table order |
| `pd.DataFrame.nlargest` | Top n in each group | the `n` rows with the largest values; `keep` decides ties |
| `pd.core.groupby.DataFrameGroupBy.cumcount` | Running totals | the position of each row in its group, from 0 |
| `pdbook.sessions.sessionize` | Build: sessionize | a session number for each call; sorts inside |
| `pdbook.sessions.session_table` | Build: sessionize | one row for each session |

### Parameters

##### `pd.Series.rank`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `axis` | `0` | not used for a Series. For a DataFrame, `1` ranks along each row | `axis=1` on a Series raises `ValueError` |
| `method` | `'average'` | the rule for ties: `'average'`, `'min'`, `'max'`, `'dense'` or `'first'` | for the values 10, 20, 20, 30 the two 20s get 2.5 (`average`), 2 and 2 (`min`), 3 and 3 (`max`), 2 and 2 (`dense`), 2 and 3 (`first`) |
| `numeric_only` | `False` | for a DataFrame, rank only the number columns | without it, a text column is ranked in alphabetical order |
| `na_option` | `'keep'` | `'keep'` gives a missing value the rank `NaN`. `'top'` ranks it first, `'bottom'` last | with `'top'`, the missing value is rank 1 and every other rank moves up by one |
| `ascending` | `True` | `False` gives rank 1 to the largest | — |
| `pct` | `False` | ranks as a share of 1: the rank divided by the number of values | with `method="dense"`, the share divides by the number of distinct values, not of rows |

##### `pd.core.groupby.DataFrameGroupBy.head`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `n` | `5` | the number of rows to keep from each group. A negative number keeps all but the last `-n` | the rows are the first ones in the table, not the largest: sort before. `head(-1)` keeps 19,400 rows, all but the last call of each of the 600 callers |

##### `pd.DataFrame.nlargest`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `n` | required | the number of rows | a column with fewer real values than `n` adds the `NaN` rows at the end |
| `columns` | required | the column, or a list of columns: the second breaks the ties of the first | a text column raises `TypeError` |
| `keep` | `'first'` | which rows to keep when values tie at the cut: `'first'`, `'last'` or `'all'` | `'all'` can return more than `n` rows |

##### `pd.core.groupby.DataFrameGroupBy.cumcount`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `ascending` | `True` | `True` counts from the first row of the group, `False` from the last | it needs a sorted table to mean "so far in time" |

##### `pdbook.sessions.sessionize`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records, in any order | — |
| `gap` | `'30min'` | the largest gap inside a session, as text for `pd.Timedelta`. A gap of exactly `gap` stays in the session | text that is not a time raises `ValueError`. The same code without a sort gives 18,151 sessions against 18,420 ([How it works](#how-it-works)) |

##### `pdbook.sessions.session_table`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `sessions` | required | the result of `sessionize` | — |


## What you have now

- You rank with a chosen tie rule, and you take the top n of each group in two ways.
- You make running totals after a sort, and you check them against the table.
- You get the time since the previous event with `groupby(...).diff()`.
- You build sessions with sort, mark, running sum, and you test them.

The next chapter looks at the traps that make a pandas result wrong without an error, in one place.

Next: [Chapter 15, Copy-on-Write and traps](15-copy-on-write-and-traps.md).
