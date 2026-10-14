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

#### `pd.Series.shift`

```text
pd.Series.shift(
    self,
    periods=1,
    freq=None,
    axis=0,
    fill_value=<no_default>,
    suffix=None,
)
```

The method moves the values by a number of rows, or with `freq` moves the index by a time.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `periods` | `1` | the number of rows to move. A negative number moves up. A list gives one column for each value | across a gap, `shift(1)` is not 5 minutes |
| `freq` | `None` | a time, such as `"5min"`: the labels move and the values stay with them | with `freq`, nothing becomes `NaN`. The index moves, so the result does not align with the original rows |
| `axis` | `0` | not used for a Series | — |
| `fill_value` | `<no_default>` | the value for the rows that the shift empties. Not set means `NaN` | without it, an `int64` Series becomes `float64` |
| `suffix` | `None` | with a list of `periods` on a DataFrame, a text between the column name and the number: `v_lag_1` | on a Series it has no effect: the columns are `0_1`, `0_2` |

#### `pd.Series.diff`

```text
pd.Series.diff(
    self,
    periods=1,
)
```

The method returns each value minus the value `periods` rows before it.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `periods` | `1` | how many rows back. A negative number looks ahead | across the outage, a difference over two hours looks like one over five minutes. On booleans the result is `True` where the value changed |

#### `pd.Series.pct_change`

```text
pd.Series.pct_change(
    self,
    periods=1,
    fill_method=None,
    freq=None,
    **kwargs,
)
```

The method returns the relative change from the value `periods` rows before: `(new - old) / old`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `periods` | `1` | how many rows back | — |
| `fill_method` | `None` | must be `None`. The old forward fill before the computation is gone | any other value raises `ValueError`. A gap gives `NaN` for the gap and for the row after it |
| `freq` | `None` | compare with the value one `freq` earlier in time, not one row earlier | — |
| `**kwargs` | — | passed to `shift` | a change from 0 gives `inf`, not an error |

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

#### `pd.Series.rolling`

```text
pd.Series.rolling(
    self,
    window,
    min_periods=None,
    center=False,
    win_type=None,
    on=None,
    closed=None,
    step=None,
    method='single',
)
```

The method returns a window object. Call an aggregation on it, such as `mean`, `count` or `max`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `window` | required | a number of rows (`12`) or a time span (`"1h"`) | a window of 12 rows reached back 2 hours 55 minutes across the outage. A time window on an unsorted index raises `ValueError` |
| `min_periods` | `None` | the samples a window needs before it gives a value. Not set means the window size for rows, and 1 for time | with a time window the default is 1 sample: 0 `NaN` values, against 16 with `min_periods=9` |
| `center` | `False` | put the value in the middle of the window, not at its end | `center=True` uses future samples. A detector must not see the future |
| `win_type` | `None` | weights of a SciPy window, such as `"triang"` | it needs SciPy, which this book does not install: `ImportError` |
| `on` | `None` | for a DataFrame, a column of timestamps to use instead of the index | — |
| `closed` | `None` | which ends of the window are inside: `'right'`, `'left'`, `'both'` or `'neither'`. Not set means `'right'` | `closed="right"` scored the spike at 16.5, `"left"` at 94.2. On a window of 12 rows, `'both'` holds 13 |
| `step` | `None` | compute only every `step`-th window | it works only with a window of rows: with `"1h"` it raises `NotImplementedError` |
| `method` | `'single'` | `'table'` computes over all columns at one time, with `engine="numba"` only | `'table'` on a Series raises `ValueError` |

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

#### `pd.Series.expanding`

```text
pd.Series.expanding(
    self,
    min_periods=1,
    method='single',
)
```

The method returns a window object that holds all rows from the start to the current row.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `min_periods` | `1` | the rows needed before the first value | — |
| `method` | `'single'` | `'table'` works only on a DataFrame with `engine="numba"` | `'table'` on a Series raises `ValueError` |

#### `pd.Series.ewm`

```text
pd.Series.ewm(
    self,
    com=None,
    span=None,
    halflife=None,
    alpha=None,
    min_periods=0,
    adjust=True,
    ignore_na=False,
    times=None,
    method='single',
)
```

The method returns an exponentially weighted window. Give exactly one of `com`, `span`, `halflife` and `alpha`: they are four ways to set the decay `alpha`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `com` | `None` | the centre of mass: `alpha = 1 / (1 + com)` | — |
| `span` | `None` | `alpha = 2 / (span + 1)`. `span=3` is `alpha=0.5` | — |
| `halflife` | `None` | the number of rows, or with `times` the time, after which a weight is half | — |
| `alpha` | `None` | the decay itself, between 0 and 1 | two of the four raise `ValueError`, and none raises `ValueError` |
| `min_periods` | `0` | the rows needed before the first value | — |
| `adjust` | `True` | `True` divides by the sum of the weights. `False` uses the recursion `y = alpha * x + (1 - alpha) * y_previous` | the two give different values at the start: 6.47 and 6.12 for the last row of the example ([How it works](#how-it-works)) |
| `ignore_na` | `False` | `False` counts a missing row in the distance between two values. `True` skips it | on `[1, nan, 3]` with `alpha=0.5`, the last mean is 2.6 with `False` and 2.333 with `True` |
| `times` | `None` | the timestamps of the rows. The decay then follows time, not rows. Only with `halflife` and `mean` | with `span` it raises `ValueError`. With `halflife="5min"`, a sample after a gap of 2 hours gets almost all the weight |
| `method` | `'single'` | `'table'` works only on a DataFrame with `engine="numba"` | — |

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

#### `pdbook.spikes.flag_spikes`

```text
pdbook.spikes.flag_spikes(
    kpi,
    column='drop_rate_pct',
    window='1D',
    z=4.0,
    min_periods=50,
)
```

The function returns a boolean Series, aligned on the rows of `kpi`: `True` where the value is more than `z` standard deviations above its trailing mean.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `kpi` | required | the KPI samples, with `ts` and `cell_id` | — |
| `column` | `'drop_rate_pct'` | the column to score | — |
| `window` | `'1D'` | the length of the trailing baseline | a window that holds fewer samples than `min_periods` never gives a score: `"1h"` holds at most 12 samples, fewer than 50, and nothing is flagged, with no warning |
| `z` | `4.0` | the threshold, in standard deviations | `z=2` flags 174 other samples. `z=8` finds 5 of 7 |
| `min_periods` | `50` | the samples of history that a baseline needs | — |

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

An exponential mean is a weighted mean too, and its weights fall by the factor `1 - alpha` for each row back. `adjust=True`, the default, divides by the sum of the weights that exist so far. `adjust=False` is a recursion that starts at the first value. The next block computes both by hand for the four values of [Expanding and exponential windows](#expanding-and-exponential-windows) and compares them with pandas:

```python
import numpy as np
import pandas as pd

s = pd.Series([1.0, 2.0, 3.0, 10.0])
alpha = 2 / (3 + 1)

adjusted = []
for i in range(len(s)):
    weights = [(1 - alpha) ** (i - j) for j in range(i + 1)]
    adjusted.append(sum(w * s[j] for j, w in enumerate(weights)) / sum(weights))

recursive = [s[0]]
for x in s[1:]:
    recursive.append(alpha * x + (1 - alpha) * recursive[-1])

print([round(v, 2) for v in adjusted], bool(np.allclose(adjusted, s.ewm(span=3).mean())))
print([round(v, 2) for v in recursive], bool(np.allclose(recursive, s.ewm(span=3, adjust=False).mean())))
```

```text
[np.float64(1.0), np.float64(1.67), np.float64(2.43), np.float64(6.47)] True
[np.float64(1.0), np.float64(1.5), np.float64(2.25), np.float64(6.12)] True
```

Both hand computations agree with pandas. `span=3` is `alpha=0.5`, so the weight halves for each row back. The two forms differ only at the start. The adjusted form gives the first value the weight that it has in a long series. The recursive form lets it count for all the past. After many rows the two are the same, because the weights of the start are close to zero.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.Series.shift` | Shift and diff | values moved by rows, or the index moved by a time |
| `pd.Series.diff` | Shift and diff | the value minus the value some rows before |
| `pd.Series.pct_change` | Shift and diff | the relative change from some rows before |
| `pd.Series.rolling` | Rolling windows | a window of rows or of time; `closed` decides if the current row is in it |
| `pd.Series.expanding` | Expanding and exponential windows | all rows from the start |
| `pd.Series.ewm` | Expanding and exponential windows | weights that fall by `1 - alpha` for each row back |
| `pdbook.spikes.flag_spikes` | Build: flag_spikes | `True` where a value is `z` deviations above its trailing mean |

## What you have now

- You know that `shift`, `diff` and `rolling(n)` work on rows, and that rows are not time when there are gaps.
- You use windows given as time, and you set `min_periods`.
- You exclude the current sample from its own baseline.
- You score a detector against a known event, and you see the cost of the threshold.

The next chapter ranks, accumulates and splits a series of events into sessions.

Next: [Chapter 14, Ranks, running totals and sessions](14-ranks-running-totals-sessions.md).
