# 13. Windows, shifts and gaps

> **Build** — `flag_spikes(kpi)`: a function that flags a measurement that is far above what the same cell did in the previous day, with a score of the flags against the one spike that is known to be in the data.
>
> **Theory kept** — `shift` and `rolling` work on rows. Time series have gaps, so a row is not a unit of time. A window by time (`"1h"`) has a fixed length and a varying count. A baseline that includes the sample that it judges is contaminated.
>
> **Source** — New. Library: [`pdbook/spikes.py`](../pdbook/spikes.py).
>
> **Run this first** — `uv run python -m examples.ch13_windows`, which is [`examples/ch13_windows.py`](../examples/ch13_windows.py). Exercises: [`exercises/13.md`](../exercises/13.md). Solutions: [`exercises/solutions/13.md`](../exercises/solutions/13.md).

## Shift and diff

`shift(n)` moves the values down by `n` rows. `diff()` is the value minus the previous value. `pct_change()` is the relative change:

```python
import pandas as pd

s = pd.Series([10.0, 12.0, 9.0, 9.0], index=pd.date_range("2026-10-24 10:00", periods=4, freq="5min"))
print(s.shift(1).tolist())
print(s.diff().tolist())
print(s.pct_change().round(3).tolist())
```

```text
[nan, 10.0, 12.0, 9.0]
[nan, 2.0, -3.0, 0.0]
[nan, 0.2, -0.25, 0.0]
```

The first row has no previous value, so it is `NaN`. These methods work on the position, one row up. That is only "five minutes ago" when no row is missing.

## Rows are not time

The KPI table has gaps. Look at the cell `BRU-004` and the time between each row and the row before it:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
cell = kpi[kpi["cell_id"] == "BRU-004"].set_index("ts")["prb_util_pct"].sort_index()
step = cell.index.to_series().diff()
print(step.value_counts().head(4).to_dict())
print(step.max(), step.idxmax())

wrong = cell.diff()
right = cell.diff().where(step == pd.Timedelta("5min"))
print(int(wrong.notna().sum()), int(right.notna().sum()))
```

```text
{Timedelta('0 days 00:05:00'): 803, Timedelta('0 days 00:10:00'): 16, Timedelta('0 days 00:15:00'): 1, Timedelta('0 days 02:05:00'): 1}
0 days 02:05:00 2026-10-25 12:00:00+00:00
821 803
```

The first line counts the steps. 803 are 5 minutes, 16 are 10 minutes and one is 15 minutes. One step is 2 hours and 5 minutes: the outage.

At the moment after the outage, `diff()` subtracts a value from two hours earlier, and the number looks like a change of five minutes. The second form keeps only the differences between rows that are 5 minutes apart. The count falls from 821 to 803 rows with a value.

There are two ways to make rows into time. Put the series on a regular grid with `reindex` or `asfreq`, so that a missing sample is an explicit `NaN` and `shift(1)` is five minutes. Or use time-based methods, such as `shift(freq="5min")`, and windows given as a string.

## Rolling windows

A rolling window gives each row a statistic over the rows near it. The window can be a number of rows or a time span:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
cell = kpi[kpi["cell_id"] == "BRU-004"].set_index("ts")["prb_util_pct"].sort_index()
moment = pd.Timestamp("2026-10-25 12:30", tz="UTC")

by_rows = cell.rolling(12).mean().loc[moment]
by_time = cell.rolling("1h").mean().loc[moment]
count = cell.rolling("1h").count().loc[moment]
span = moment - cell.index[cell.index.get_loc(moment) - 11]
print(round(float(by_rows), 2), round(float(by_time), 2), int(count), span)
```

```text
54.26 61.67 7 0 days 02:55:00
```

The window of 12 rows ends at 12:30. It begins 2 hours and 55 minutes earlier, because it counts rows and the outage has none. It holds the 7 samples after the outage and 5 samples from before it. The window of one hour holds only the 7 samples after the outage, and the mean is 61.67 against 54.26. Use the time window when you mean a time span. Use the row window only after you put the series on a regular grid.

The argument `min_periods` says how many samples a window needs before it gives a value. With a time window, the default is 1, so a window with one sample gives a mean of one sample. Set it:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
cell = kpi[kpi["cell_id"] == "BRU-004"].set_index("ts")["prb_util_pct"].sort_index()

loose = cell.rolling("1h").mean()
strict = cell.rolling("1h", min_periods=9).mean()
print(int(loose.isna().sum()), int(strict.isna().sum()))
print(int(cell.rolling("1h").count().eq(1).sum()))
```

```text
0 16
2
```

With the default, no value is `NaN`, and 2 windows hold only one sample. With `min_periods=9`, which is three quarters of a full hour, 16 values are `NaN`: the windows with fewer than 9 samples. This is the same idea as the column `complete` of [Chapter 12](12-dates-and-resampling.md): a statistic needs enough data to mean something.

## Expanding and exponential windows

`expanding()` uses all rows from the start to the current row. `ewm` weights recent rows more:

```python
import pandas as pd

s = pd.Series([1.0, 2.0, 3.0, 10.0])
print(s.expanding().mean().tolist())
print(s.ewm(span=3).mean().round(2).tolist())
```

```text
[1.0, 1.5, 2.0, 4.0]
[1.0, 1.67, 2.43, 6.47]
```

The expanding mean is a running mean, and the exponential mean follows the last value more quickly. The first is the right tool for a cumulative figure, and the second for a signal with a drift.

## The baseline must not contain the sample

An anomaly score compares a sample with a baseline. If the baseline includes the sample, a large sample raises its own baseline and hides itself. `closed="left"` excludes the current row from the window:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
s = kpi[kpi["cell_id"] == "BRU-002"].set_index("ts")["drop_rate_pct"].sort_index()
at = pd.Timestamp("2026-10-25 14:00", tz="UTC")

print(f"sample at 14:00 = {s.loc[at]:.2f}%, median of the cell = {s.median():.2f}%")
for closed in ("right", "left"):
    roll = s.rolling("1D", min_periods=50, closed=closed)
    z = ((s - roll.mean()) / roll.std()).loc[at]
    print(f"closed={closed:5s} score at 14:00 = {z:.1f}")
```

```text
sample at 14:00 = 11.34%, median of the cell = 0.58%
closed=right score at 14:00 = 16.5
closed=left  score at 14:00 = 94.2
```

The sample at 14:00 is 11.34%, and the median of the cell is 0.58%. With `closed="right"` (the default) the baseline contains the spike and the score is lower. With `closed="left"` the score is the score of a sample against the past. Both scores are far above any usual threshold, so the choice does not change the result in this case. It changes the score by a factor of 5.7.

## Build: flag_spikes

`flag_spikes` computes the score for each cell, with a trailing baseline of one day, and flags the samples above a threshold `z`. The data have one injected spike: 7 samples of `BRU-002` from 14:00 to 14:30 UTC on 25 October. That gives a way to score the detector, which is rare with real data:

```python
import pandas as pd

from pdbook.io import load_kpi
from pdbook.spikes import flag_spikes

kpi = load_kpi().drop_duplicates(["ts", "cell_id"]).reset_index(drop=True)
truth = (kpi["cell_id"] == "BRU-002") & kpi["ts"].between("2026-10-25 14:00", "2026-10-25 14:30")
print("injected samples:", int(truth.sum()))
for z in (2, 3, 4, 5, 8):
    flags = flag_spikes(kpi, z=z)
    print(f"z={z}: found {int((flags & truth).sum())}, false {int((flags & ~truth).sum())}")

late = flag_spikes(kpi, z=8) & truth
print("found at z=8:", kpi.loc[late, "ts"].dt.strftime("%H:%M").tolist())
```

```text
injected samples: 7
z=2: found 7, false 174
z=3: found 7, false 10
z=4: found 7, false 0
z=5: found 7, false 0
z=8: found 5, false 0
found at z=8: ['14:00', '14:05', '14:10', '14:15', '14:20']
```

Read the table from the top. At `z=2`, all 7 samples are found, and 174 other samples are flagged: the detector is noisy. At `z=3`, 10 other samples are flagged. At `z=4` and `z=5`, the result is exact:

7 found and none false. At `z=8`, only 5 of the 7 are found, and the last line shows which: the first five, from 14:00 to 14:20. The first spike samples enter the baseline of the later ones. They raise its mean and its standard deviation, and the last two samples no longer pass.

This is the cost of any threshold. A low threshold floods a person with alerts. A high one misses a long event, and it misses the end of an event first. Choose the threshold with a score like this one, on data where you know the answer. Do not choose it by looking at the alerts of one week.

Two properties of the function are worth a test:

```python
import pandas as pd

from pdbook.io import load_kpi
from pdbook.spikes import flag_spikes

kpi = load_kpi().drop_duplicates(["ts", "cell_id"]).reset_index(drop=True)
shuffled = kpi.sample(frac=1, random_state=0)
a = flag_spikes(kpi, z=4)
b = flag_spikes(shuffled, z=4).reindex(kpi.index)
print(bool((a == b).all()))

first_day = kpi["ts"] < pd.Timestamp("2026-10-24 04:10", tz="UTC")
print(int(flag_spikes(kpi, z=0)[first_day].sum()))
```

```text
True
0
```

The first line is `True`: the result does not depend on the order of the rows, because the function sorts by time inside each cell. The second line is 0. With the threshold `z=0`, every sample above the mean is flagged. Still, no sample in the first 4 hours is flagged, because they have fewer than 50 samples of history. A detector has no opinion before it has data.

## How it works

A rolling window by rows is a fixed number of neighbours. A rolling window by time is different. For each timestamp, pandas finds where the window begins in the sorted index, with a binary search. Then it computes the statistic over the rows from that position to the current one.

The window has a fixed length in time and a count that changes. The argument `closed` says which ends belong to the window: `"right"` is the default and includes the current row, and `"left"` leaves it out.

You can compute a few windows by hand with a boolean mask on the time, and compare:

```python
import pandas as pd

from pdbook.io import load_kpi

kpi = load_kpi().drop_duplicates(["ts", "cell_id"])
cell = kpi[kpi["cell_id"] == "BRU-004"].set_index("ts")["prb_util_pct"].sort_index()

rolled = cell.rolling("1h").mean()
rolled_left = cell.rolling("1h", closed="left").mean()
one_hour = pd.Timedelta("1h")

ok = True
for t in cell.index[[20, 300, 400, 600]]:
    right = cell[(cell.index > t - one_hour) & (cell.index <= t)].mean()
    left = cell[(cell.index >= t - one_hour) & (cell.index < t)].mean()
    ok &= abs(right - rolled.loc[t]) < 1e-9 and abs(left - rolled_left.loc[t]) < 1e-9
print(ok)
print(int(cell.rolling("1h").count().max()), int(cell.rolling("1h", closed="left").count().max()))
print(cell.index.is_monotonic_increasing)
```

```text
True
12 12
True
```

The hand computation agrees with `rolling` for four timestamps, for both settings of `closed`. A one-hour window holds at most 12 samples of 5 minutes with the default. The setting `"left"` gives the same maximum, because the window then begins at the sample one hour before and leaves the current one out. The index is sorted, which `rolling` with a time window requires.

- **Invariant.** A time window covers a fixed span of time, and its count of samples varies.
- **Failure.** A window by rows spans a longer time when rows are missing ([the 2 hours 55 minutes of this chapter](#rolling-windows)).
- **Cost.** A binary search for each row, then an incremental update of the statistic, so one pass over the data for the mean.

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.spikes import flag_spikes

show_signature(pd.Series.rolling, ["window", "min_periods", "center", "closed"])
show_signature(pd.Series.expanding, ["min_periods"])
show_signature(pd.Series.ewm, ["span", "alpha", "adjust"])
show_signature(pd.Series.shift, ["periods", "freq"])
show_signature(pd.Series.diff, ["periods"])
show_signature(pd.Series.pct_change, ["periods"])
show_signature(flag_spikes)
```

```text
NDFrame.rolling(
    window: 'int | dt.timedelta | str | BaseOffset | BaseIndexer'
    min_periods: 'int | None' = None
    center: 'bool' = False
    closed: 'IntervalClosedType | None' = None
)  # 5 more parameters
NDFrame.expanding(
    min_periods: 'int' = 1
)  # 2 more parameters
NDFrame.ewm(
    span: 'float | None' = None
    alpha: 'float | None' = None
    adjust: 'bool' = True
)  # 7 more parameters
NDFrame.shift(
    periods: 'int | Sequence[int]' = 1
    freq=None
)  # 4 more parameters
Series.diff(
    periods: 'int' = 1
)  # 1 more parameters
NDFrame.pct_change(
    periods: 'int' = 1
)  # 4 more parameters
flag_spikes(
    kpi: 'pd.DataFrame'
    column: 'str' = 'drop_rate_pct'
    window: 'str' = '1D'
    z: 'float' = 4.0
    min_periods: 'int' = 50
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `rolling(window)` | required | rows (`12`) or time (`"1h"`) | a window of 12 rows reached back 2 hours 55 minutes across the outage |
| `rolling(min_periods=...)` | `None` | the samples a window needs before it gives a value | with a time window the default is 1 sample: 0 `NaN` values, against 16 with `min_periods=9` |
| `rolling(center=...)` | `False` | put the value in the middle of the window | — |
| `rolling(closed=...)` | `None` | which ends of the window are inside; `"left"` leaves the current row out | `closed="right"` scored the spike at 16.5, `"left"` at 94.2 |
| `expanding(min_periods=...)` | `1` | all rows from the start to now | — |
| `ewm(span=..., alpha=...)` | `None`, `None` | a mean that weights recent rows more | — |
| `shift(periods, freq=...)` | `1`, `None` | move values by rows, or by a time with `freq` | across a gap, `shift(1)` is not 5 minutes |
| `diff(periods=...)` | `1` | value minus the value `periods` rows before | across the outage, a difference of two hours looks like one of five minutes |
| `pct_change(periods=...)` | `1` | relative change | — |
| `flag_spikes(kpi, column, window, z, min_periods)` | `'drop_rate_pct'`, `'1D'`, `4.0`, `50` | `True` where the value is more than `z` deviations above the trailing mean | `z=2` flags 174 other samples; `z=8` finds 5 of 7 |

`flag_spikes` returns a boolean Series with the index of `kpi`. The input must be unique on `ts` and `cell_id`.

## What you have now

- You know that `shift`, `diff` and `rolling(n)` work on rows, and that rows are not time when there are gaps.
- You use windows given as time, and you set `min_periods`.
- You exclude the current sample from its own baseline.
- You score a detector against a known event, and you see the cost of the threshold.

The next chapter ranks, accumulates and splits a series of events into sessions.

Next: [Chapter 14, Ranks, running totals and sessions](14-ranks-running-totals-sessions.md).
