# 12. Dates and resampling

> **Build** — `hourly_kpi(kpi)`: a function that turns 5-minute cell measurements into hourly values in local time, removes repeated rows, and keeps the number of samples behind each hour, so that you can see which hours are incomplete. It handles the day with 25 hours.
>
> **Theory kept** — Store time in UTC and convert to a zone to display and to group by day. A timestamp without a zone is a guess. `resample` groups by time bins, and it keeps the empty bins. A local day is not always 24 hours.
>
> **Source** — New. Data: [`data/kpi.csv`](../data/kpi.csv). Library: [`pdbook/kpi.py`](../pdbook/kpi.py).
>
> **Run this first** — `uv run python -m examples.ch12_dates`, which is [`examples/ch12_dates.py`](../examples/ch12_dates.py). Exercises: [`exercises/12.md`](../exercises/12.md). Solutions: [`exercises/solutions/12.md`](../exercises/solutions/12.md).

## Timestamps with a zone

A timestamp can be naive (no zone) or aware (with a zone). A naive time is a wall-clock reading, and it does not say which clock. An aware time is a point on the time line. The call records are aware and in UTC. Two methods change the zone, and they do different things:

| Method | What it does |
|---|---|
| `tz_localize(zone)` | attach a zone to a naive time. The wall-clock reading stays and the instant changes. |
| `tz_convert(zone)` | express an aware time in another zone. The instant stays and the reading changes. |

```python
import pandas as pd

utc = pd.Timestamp("2026-09-10 16:30", tz="UTC")
print(utc.tz_convert("Europe/Brussels"))
print(utc.tz_convert("America/New_York"))

naive = pd.Timestamp("2026-09-10 16:30")
print(naive.tz_localize("Europe/Brussels"))
print(naive.tz_localize("Europe/Brussels") == utc)
```

```text
2026-09-10 18:30:00+02:00
2026-09-10 12:30:00-04:00
2026-09-10 16:30:00+02:00
False
```

The same reading, 16:30, is a different instant in each zone. Belgium is two hours ahead of UTC in September, so 16:30 in Brussels is 14:30 in UTC, and the last line is `False`. Store timestamps as UTC, and convert at the edge, when you show them or group by day.

The block used the methods of one `Timestamp`. For a column, the same two methods are on the `dt` accessor.

#### `pd.Series.dt.tz_convert`

```text
pd.Series.dt.tz_convert(
    self,
    tz,
)
```

The method shows each aware timestamp in another zone. The instant does not change.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `tz` | required | the zone, such as `"Europe/Brussels"` or `"UTC"`. `None` converts to UTC and removes the zone | on a naive column it raises `TypeError`: use `tz_localize` first. — (the stored integers do not change) |

The accessor `dt` gives the parts: `dt.hour`, `dt.dayofweek`, `dt.date`, `dt.floor("h")`, `dt.strftime(...)`. The parts depend on the zone of the column. Convert first.

## Summer time

The zone database knows the rules of summer time, and it makes two kinds of local readings that a naive time cannot represent:

```python
import pandas as pd

zone = "Europe/Brussels"
try:
    pd.Timestamp("2026-10-25 02:30").tz_localize(zone)
except ValueError as error:
    print("ambiguous:", type(error).__name__)

try:
    pd.Timestamp("2027-03-28 02:30").tz_localize(zone)
except ValueError as error:
    print("missing  :", type(error).__name__)

first = pd.Timestamp("2026-10-25 02:30").tz_localize(zone, ambiguous=True)
second = pd.Timestamp("2026-10-25 02:30").tz_localize(zone, ambiguous=False)
print(first, second)
```

```text
ambiguous: ValueError
missing  : ValueError
2026-10-25 02:30:00+02:00 2026-10-25 02:30:00+01:00
```

On 25 October 2026 the clocks go from 03:00 back to 02:00, so the reading 02:30 happens twice. On 28 March 2027 they go from 02:00 to 03:00, so 02:30 never happens. pandas refuses both and does not guess. You choose with `ambiguous=` and `nonexistent=`. A system that logs local time without the offset cannot tell the two readings apart. A log of this kind is ambiguous for one hour in each year.

#### `pd.Series.dt.tz_localize`

```text
pd.Series.dt.tz_localize(
    self,
    tz,
    ambiguous='raise',
    nonexistent='raise',
)
```

The method attaches a zone to each naive timestamp. The reading stays, and the instant is the reading in that zone.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `tz` | required | the zone of the readings. `None` removes the zone and keeps the local reading | on an aware column it raises `TypeError`: use `tz_convert`. The reading is a different instant in each zone |
| `ambiguous` | `'raise'` | what to do with a reading that happens twice: `'raise'`, `'infer'` from the order of the rows, `'NaT'`, `True` for summer time, `False` for winter time, or an array of booleans, one for each row | `2026-10-25 02:30` raises. `True` on a column applies to every row, so two different calls at "02:30" both get `+02:00`. Use `'infer'` or an array |
| `nonexistent` | `'raise'` | what to do with a reading that never happens: `'raise'`, `'shift_forward'`, `'shift_backward'`, `'NaT'` or a `Timedelta` | `2027-03-28 02:30` raises. `'shift_forward'` gives 03:00, and `pd.Timedelta("1h")` gives 03:30: two different answers to the same question |

## A day with 25 hours

The KPI file covers 24 to 26 October 2026 in UTC, and the clocks change on the 25th. Count the hours of each local day with `date_range`:

```python
import pandas as pd

hours = pd.date_range("2026-10-24", "2026-10-27", freq="h", tz="Europe/Brussels", inclusive="left")
per_day = pd.Series(1, index=hours).groupby(hours.date).sum()
print(per_day.to_dict())
```

```text
{datetime.date(2026, 10, 24): 24, datetime.date(2026, 10, 25): 25, datetime.date(2026, 10, 26): 24}
```

The 25th has 25 hours. A daily report that assumes 24 hours is wrong for one day of the year: a "calls per hour" figure divides by 24 and misses by 4%, and a rolling window of 24 rows is not one day on that date. Use the time itself, not the number of rows, to define a day.

#### `pd.date_range`

```text
pd.date_range(
    start=None,
    end=None,
    periods=None,
    freq=None,
    tz=None,
    normalize=False,
    name=None,
    inclusive='both',
    *,
    unit=None,
    **kwargs,
)
```

The function returns a `DatetimeIndex` of regular timestamps. Give exactly three of `start`, `end`, `periods` and `freq`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `start` | `None` | the first timestamp | — |
| `end` | `None` | the last timestamp | all four of `start`, `end`, `periods` and `freq` raise `ValueError` |
| `periods` | `None` | the number of timestamps | — |
| `freq` | `None` | the step: `"h"`, `"5min"`, `"D"`, `"MS"` for the start of a month, `"ME"` for the end. With `None` and no `periods`, one day | `"M"` raises `ValueError` in pandas 3.0: write `"ME"`. On a zone with summer time, `"D"` steps from local midnight to local midnight, and `"24h"` steps 24 hours: on 25 October the second gives 23:00 |
| `tz` | `None` | the zone of the timestamps. With `None`, naive | with `tz="Europe/Brussels"` the day of 25 October has 25 hours |
| `normalize` | `False` | set `start` and `end` to midnight first | — |
| `name` | `None` | the name of the index | — |
| `inclusive` | `'both'` | which ends are in the range: `'both'`, `'neither'`, `'left'` or `'right'` | — |
| `unit` | `None` | the resolution, such as `"s"` or `"us"`. With `None`, the resolution of the inputs | — |
| `**kwargs` | — | accepted and passed on. pandas 3.0 knows no extra name here | an old name such as `closed=` raises `TypeError` |

## A DatetimeIndex

When a column of timestamps becomes the index, you can slice by strings and you get `resample`:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
one = kpi[kpi["cell_id"] == "ANT-001"].set_index("ts")["prb_util_pct"]
print(one.index.is_monotonic_increasing, len(one))
print(len(one["2026-10-25"]))
print(len(one["2026-10-25 08:00":"2026-10-25 08:59"]))
print(len(one.between_time("08:00", "08:59")))
```

```text
True 851
284
12
36
```

The string `"2026-10-25"` selects the whole UTC day. The slice with two times includes both ends, as `.loc` does ([Chapter 3](03-selection.md)). The hour from 08:00 to 08:59 has 12 samples. The method `between_time` takes the same minutes of the three days: 36 samples.

#### `pd.DataFrame.between_time`

```text
pd.DataFrame.between_time(
    self,
    start_time,
    end_time,
    inclusive='both',
    axis=None,
)
```

The method returns the rows whose clock time is between two times, on any date.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `start_time` | required | the first clock time, such as `"08:00"` | — |
| `end_time` | required | the last clock time. A time before `start_time` crosses midnight: `"23:00"` to `"01:00"` is two hours | — |
| `inclusive` | `'both'` | which ends are in: `'both'`, `'neither'`, `'left'` or `'right'` | `"08:00"` to `"09:00"` with `'both'` takes the sample at 09:00 of each day: 39 samples and not 36 |
| `axis` | `None` | `0` for the index, `1` for the columns | on a table without a `DatetimeIndex` it raises `TypeError` |

The clock time is read in the zone of the index. The same call on the series in Brussels time gives 35 samples, because the three UTC days are not the three local days.

The partial-string slice needs a sorted index. The call records are not sorted, and then you get an error:

```python
import pandas as pd

from pdbook.io import load_calls

by_time = load_calls().set_index("start")
print(by_time.index.is_monotonic_increasing)
try:
    by_time.loc["2026-09-10":"2026-09-10"]
except KeyError as error:
    print("KeyError:", str(error)[:50])

ordered = by_time.sort_index()
print(len(ordered.loc["2026-09-10"]))
```

```text
False
KeyError: 'Value based partial slicing on non-monotonic Date
782
```

The 1,000 late records at the end of the file make the index non-monotonic. pandas stops, because a partial-string slice with bounds that are not in the index is not allowed on such an index. After `sort_index`, the slice returns the 782 calls of that UTC day. `resample` itself does not need a sorted index.

## resample

`resample` groups by time bins and aggregates. It is `groupby` with a time key. The frequency is a string: `"5min"`, `"h"`, `"D"`, `"W"`, `"MS"` for the start of a month:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls().set_index("start")
per_hour = calls.resample("h").size()
print(len(per_hour), int(per_hour.sum()))
print(per_hour.idxmax(), int(per_hour.max()))
print(int((per_hour == 0).sum()), "hours without a call")

local_day = calls.tz_convert("Europe/Brussels").resample("D").size()
print(len(local_day), local_day.idxmax().date(), int(local_day.max()))
```

```text
720 20000
2026-09-10 16:00:00+00:00 73
4 hours without a call
30 2026-09-30 793
```

The month has 720 hours, 30 days times 24, and the counts add up to 20,000. The busiest hour is 16:00 UTC on 10 September with 73 calls. Hours without a call stay in the result with a count of 0, because `resample` makes every bin between the first and the last time. The 30 local days are all in September, which has no clock change. The build below uses three days that have one.

For a mean, an empty bin is `NaN` and not 0, because the mean of nothing is not zero. That is the second reason to keep `n` next to a mean.

#### `pd.DataFrame.resample`

```text
pd.DataFrame.resample(
    self,
    rule,
    closed=None,
    label=None,
    convention='start',
    on=None,
    level=None,
    origin='start_day',
    offset=None,
    group_keys=False,
)
```

The method groups the rows into time bins by the `DatetimeIndex`, or by the column `on`. Call an aggregation on the result.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `rule` | required | the size of the bins: `"5min"`, `"h"`, `"D"`, `"W"`, `"MS"` and so on | empty bins stay: 720 hours, 4 with no call. A table without a `DatetimeIndex` and without `on` raises `TypeError` |
| `closed` | `None` | which end of a bin is inside it: `'left'` or `'right'`. `None` means `'left'`, except for `"W"`, `"ME"`, `"QE"` and `"YE"` | with `"W"`, the default is `'right'`: the bins end on Sunday and carry the label of that Sunday. The first bin of this month is 6 September, not 30 August |
| `label` | `None` | which end of a bin names it. The same defaults as `closed` | — |
| `convention` | `'start'` | for a `PeriodIndex` only: put the value at the start or the end of the new period | — |
| `on` | `None` | a column of timestamps to use instead of the index | — |
| `level` | `None` | for a MultiIndex, the level of timestamps | — |
| `origin` | `'start_day'` | the point from which the bins are counted: `'start_day'` is midnight of the first day, `'epoch'` is 1970-01-01 | for bins that do not divide a day, such as `"7h"`, the bins differ: the first starts at 21:00 with `'start_day'` and at 16:00 with `'epoch'` |
| `offset` | `None` | a shift of the origin, such as `"6h"` | with `"D"`, it has no effect and gives a `RuntimeWarning`. A day of 06:00 to 06:00 needs `"24h"` |
| `group_keys` | `False` | for `apply` on the result: add the bin labels as an index level | — |

## Build: hourly_kpi

`hourly_kpi` does the steps that a person does by hand, and it keeps the evidence of each step:

```python
import pandas as pd

from pdbook.io import load_kpi
from pdbook.kpi import hourly_kpi

kpi = load_kpi()
hourly = hourly_kpi(kpi)
print(len(kpi), len(kpi.drop_duplicates(["ts", "cell_id"])), len(hourly))
print(hourly["n"].value_counts().sort_index().to_dict())
print(hourly.groupby("cell_id").size().to_dict())

day = hourly[hourly["ts"].dt.strftime("%Y-%m-%d") == "2026-10-25"]
print(day.groupby("cell_id").size().unique().tolist())
print(int(hourly["n"].sum()), int(hourly["complete"].sum()))
```

```text
5104 5079 432
{0: 2, 10: 5, 11: 71, 12: 354}
{'ANT-001': 72, 'ANT-002': 72, 'BRU-001': 72, 'BRU-002': 72, 'BRU-003': 72, 'BRU-004': 72}
[25]
5079 354
```

The raw file has 5,104 rows. 25 of them are repeats of another row, which leaves 5,079. The result has 432 rows: 6 cells and 72 hours. The hours have 12 samples when they are full.

354 hours are full, 71 have 11 samples, 5 have 10, and 2 have none. The two empty hours are the outage of the cell `BRU-004`, and they show `NaN` in the mean and 0 in `n`. The samples add up to 5,079, so no sample was lost or counted twice. Each cell has 25 hours on 25 October.

A mean of 11 samples is not the same quality as a mean of 12 samples. A mean of 0 samples is not a value. A dashboard that draws only the mean shows all hours with the same confidence. Draw `n` or `complete` with it.

#### `pdbook.kpi.hourly_kpi`

```text
pdbook.kpi.hourly_kpi(
    kpi,
    tz='Europe/Brussels',
    full_hour=12,
)
```

The function returns one row for each cell and local hour: the mean load, the number of samples `n`, and `complete`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `kpi` | required | the KPI samples, with `ts`, `cell_id` and `prb_util_pct` | — (5,104 rows, 25 repeats, 432 hours, 354 complete) |
| `tz` | `'Europe/Brussels'` | the zone of the hours | — |
| `full_hour` | `12` | the number of samples that makes an hour complete | `full_hour=11` makes 425 hours complete instead of 354: the threshold decides what the dashboard calls good |

## How it works

A timestamp is stored as one 64-bit integer: the number of time units (here microseconds) since 1 January 1970, 00:00 UTC. A time zone is not part of the number. It is a label on the column that tells pandas how to *display* the integer and how to cut it into days. This is why `tz_convert` does not change a stored value. A day boundary in another zone is a different cut of the same numbers.

`resample` is a `floor` and a `groupby`: each timestamp is rounded down to the start of its bin, and the bins are grouped. You can check both claims:

```python
import pandas as pd

from pdbook.io import load_calls

calls = load_calls()
utc = calls["start"]
local = utc.dt.tz_convert("Europe/Brussels")
print(utc.dtype, local.dtype)
print(utc.astype("int64").equals(local.astype("int64")))
print(int(utc.astype("int64").iloc[0]), utc.iloc[0].isoformat(), local.iloc[0].isoformat())

by_floor = calls.groupby(utc.dt.floor("h")).size()
by_resample = calls.set_index("start").resample("h").size()
print(len(by_floor), len(by_resample))
print(bool((by_floor.reindex(by_resample.index, fill_value=0) == by_resample).all()))
```

```text
datetime64[us, UTC] datetime64[us, Europe/Brussels]
True
1788214410000000 2026-08-31T22:13:30+00:00 2026-09-01T00:13:30+02:00
716 720
True
```

The two columns have different dtypes and hold the same integers. The first stored value is a number of microseconds, and its UTC and local displays differ by two hours. The `floor` and `groupby` give 716 hours, because they have only the hours that occur. `resample` gives 720, because it keeps the empty bins. After a `reindex` with zeros the two agree in every hour.

- **Invariant.** The stored integer is a point in time, in UTC. The zone changes only the display and the cut into days.
- **Failure.** A naive timestamp has no zone, so the same reading is different points in time for two readers.
- **Cost.** A zone conversion is one pass of arithmetic with the zone rules, and no copy of the text. A `resample` makes every bin, empty ones included.

The rule "a `floor` and a `groupby`" holds in UTC. In local time it breaks on the night of the clock change, and `resample` does not. The next block takes one cell of the KPI file in Brussels time. On 25 October, that time has the hour from 02:00 to 03:00 twice:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
one = kpi[kpi["cell_id"] == "ANT-001"].set_index("ts")["prb_util_pct"]
local = one.tz_convert("Europe/Brussels")
try:
    local.index.floor("h")
except ValueError as error:
    print("floor: ValueError:", str(error)[:46])

by_local = local.resample("h").size()
day = by_local[by_local.index.strftime("%Y-%m-%d") == "2026-10-25"]
print(len(day), [ts.strftime("%H:%M%z") for ts in day.index[1:5]])

by_utc = one.resample("h").size()
print(by_local.index.tz_convert("UTC").equals(by_utc.index), by_local.tolist() == by_utc.tolist())
```

```text
floor: ValueError: Cannot infer dst time from 2026-10-25 02:00:00
25 ['01:00+0200', '02:00+0200', '02:00+0100', '03:00+0100']
True True
```

`floor("h")` on local time must give the reading 02:00, and that reading is two instants. It refuses. `resample("h")` gives 25 bins for the day, and two of them are 02:00, one with `+0200` and one with `+0100`. The last line shows how:

the bins in Brussels time are the bins in UTC, the same instants with the same counts, with local labels. `resample` cuts on the stored integers. A bin of one hour does not depend on the zone. A bin of one day does, because a local day is 23, 24 or 25 hours long.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.Series.dt.tz_convert` | Timestamps with a zone | the same instants shown in another zone |
| `pd.Series.dt.tz_localize` | Summer time | a zone attached to naive readings; ambiguous and missing readings raise by default |
| `pd.date_range` | A day with 25 hours | a regular `DatetimeIndex`; `"D"` follows local midnight |
| `pd.DataFrame.between_time` | A DatetimeIndex | the rows between two clock times, in the zone of the index |
| `pd.DataFrame.resample` | resample | time bins on the index; empty bins stay |
| `pdbook.kpi.hourly_kpi` | Build: hourly_kpi | one row for each cell and local hour, with `n` and `complete` |

## What you have now

- You store time as UTC and convert to a zone to show or group.
- You know `tz_localize` from `tz_convert`, and that summer time makes ambiguous and missing readings.
- You count hours, not rows, in a local day, and you know the day with 25 hours.
- You slice a sorted `DatetimeIndex` by strings, and you sort first.
- You resample, and you keep the sample count with every mean.

The next chapter looks at the series inside each hour: rolling windows, shifts and gaps.

Next: [Chapter 13, Windows, shifts and gaps](13-windows-shifts-gaps.md).
