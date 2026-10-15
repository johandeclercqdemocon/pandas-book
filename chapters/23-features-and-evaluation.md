# 23. Features and evaluation

> **Build** — `past_features` with `assert_no_leak`: features for each subscriber that use only calls before a cutoff, and a test that proves it by changing the future. `compare_configs`: a paired comparison of two configurations on the same tasks, with a bootstrap interval, written as a table of results.
>
> **Theory kept** — A feature must be computable at the moment of the decision. A group statistic over the whole table uses the future. Test it by changing the future and checking that the features do not move. Compare two systems on the same tasks, and make the task, not the run, the unit.
>
> **Source** — New. Data: [`data/runs.jsonl`](../data/runs.jsonl). Libraries: [`pdbook/features.py`](../pdbook/features.py) and [`pdbook/evals.py`](../pdbook/evals.py).
>
> **Run this first** — `uv run python -m examples.ch23_features`, which is [`examples/ch23_features.py`](../examples/ch23_features.py). Exercises: [`exercises/23.md`](../exercises/23.md). Solutions: [`exercises/solutions/23.md`](../exercises/solutions/23.md).

## The question and the cutoff

The question: how many calls will each subscriber make from 22 September on, given what we know before? The cutoff is local midnight at the start of 22 September. Everything before it is the past, and everything from it on is the future:

```python
import pandas as pd

from pdbook.features import TZ, past_features, target
from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()["subscriber_id"]
cutoff = "2026-09-22"
limit = pd.Timestamp(cutoff, tz=TZ)
print(limit, "=", limit.tz_convert("UTC"))
print(int((calls["start"] < limit).sum()), int((calls["start"] >= limit).sum()))

X = past_features(calls, subs, cutoff)
y = target(calls, subs, cutoff)
print(X.shape, int(y.sum()))
print(X.describe().round(2).loc[["mean", "min", "max"]].to_string())
```

```text
2026-09-22 00:00:00+02:00 = 2026-09-21 22:00:00+00:00
13905 6095
(600, 5) 6095
       calls  answered_share  talk_min  active_days  days_since_last
mean   23.18            0.77     39.40        11.72             1.35
min     3.00            0.43      0.90         2.00             0.01
max   450.00            1.00    731.02        21.00            13.73
```

The cutoff in UTC is 22:00 on 21 September, because Brussels is two hours ahead. A cutoff at UTC midnight is two hours off. Calls between 22:00 and 24:00 then fall on the wrong side. The past has 13,905 calls and the future 6,095.

The feature table has one row for each of the 600 subscribers. Every subscriber has at least 3 calls in the past, so there are no missing features here. In another table a subscriber with no past calls has a missing `answered_share`, and that must be a decision and not an accident.

The functions of the first half are in [`pdbook/features.py`](../pdbook/features.py).

#### `pdbook.features.past_features`

```text
pdbook.features.past_features(
    calls,
    subscribers,
    cutoff,
)
```

The function returns one row for each subscriber id: `calls`, `answered_share`, `talk_min`, `active_days` and `days_since_last`, from the calls before the cutoff only.

The table under `pdbook.features.past_features` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.features.target`

```text
pdbook.features.target(
    calls,
    subscribers,
    cutoff,
)
```

The function returns, for each subscriber id, the number of calls at or after the cutoff.

The table under `pdbook.features.target` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## The easy feature leaks

The shortest code for "calls of each subscriber" is a `groupby` over the whole table. It includes the future, which is the thing that we want to predict:

```python
import numpy as np
import pandas as pd

from pdbook.features import leaky_features, past_features, target
from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()["subscriber_id"]
cutoff = "2026-09-22"
X, y, L = past_features(calls, subs, cutoff), target(calls, subs, cutoff), leaky_features(calls, subs)


def score(x: pd.Series) -> tuple[float, float]:
    prediction = x * (y.sum() / x.sum())
    return float(np.corrcoef(x, y)[0, 1]), float((prediction - y).abs().mean())


for name, feature in [("past features", X["calls"]), ("leaky feature", L["calls"])]:
    corr, mae = score(feature)
    print(f"{name:14s} correlation {corr:.3f}  mean absolute error {mae:.2f} calls")
```

```text
past features  correlation 0.955  mean absolute error 2.87 calls
leaky feature  correlation 0.978  mean absolute error 2.00 calls
```

The leaky feature looks better: a higher correlation and a lower error. It is better because it contains the answer. A person who reports the second line reports a result that nobody can reproduce when the model runs for real.

The future is not there on that day. The difference here is small, 2.87 against 2.00 calls, because most of the signal is the difference between heavy and light subscribers. A leak can be small, and it is still wrong.

#### `pdbook.features.leaky_features`

```text
pdbook.features.leaky_features(
    calls,
    subscribers,
)
```

The function returns the count of calls of each subscriber over the whole table. It is the easy version, and it leaks the target.

The table under `pdbook.features.leaky_features` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Test for the leak

Reading the code is not a test. The test is a property. A feature that uses only the past does not change when the future changes. `assert_no_leak` changes the future in two ways and compares the features before and after:

```python
import pandas as pd

from pdbook.features import assert_no_leak, leaky_features, past_features
from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()["subscriber_id"]
cutoff = "2026-09-22"

assert_no_leak(lambda c, s: past_features(c, s, cutoff), calls, subs, cutoff)
print("past_features: no change when the future changes")

try:
    assert_no_leak(leaky_features, calls, subs, cutoff)
except AssertionError as error:
    print("leaky_features:", error)
```

```text
past_features: no change when the future changes
leaky_features: features change when the future changes (future removed)
```

The function that uses the past passes. The function that groups over the whole table fails, and the message names the change that exposed it. The two changes are: remove the future, and give every future call to one subscriber.

My first version of this test shuffled the callers of the future, and it did not find the leak. A shuffle keeps the number of calls of each caller, so a count does not move. A test of a property must change what the feature reads.

#### `pdbook.features.assert_no_leak`

```text
pdbook.features.assert_no_leak(
    feature_fn,
    calls,
    subscribers,
    cutoff,
)
```

The function returns nothing when `feature_fn(calls, subscribers)` gives the same table after each of two changes to the future. Otherwise it raises `AssertionError` and names the change.

The table under `pdbook.features.assert_no_leak` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Compare two configurations

The file `data/runs.jsonl` holds the results of an evaluation: 150 tasks, run with two configurations, `baseline` and `improved`, with 3 seeds each. Each line has a nested `tokens` object, and `load_runs` flattens it:

```python
import numpy as np
import pandas as pd

from pdbook.evals import load_runs

runs = load_runs()
print(runs.shape, runs.columns.tolist())
print(runs.groupby("config")["passed"].agg(["mean", "size"]).round(4).to_dict("index"))

per_task = runs.groupby(["task_id", "config"])["passed"].mean().unstack()
diff = per_task["improved"] - per_task["baseline"]
print(len(diff), round(float(diff.mean()), 4))
print(int((diff > 0).sum()), int((diff < 0).sum()), int((diff == 0).sum()))
```

```text
(900, 8) ['task_id', 'category', 'config', 'seed', 'passed', 'latency_ms', 'tokens.prompt', 'tokens.completion']
{'baseline': {'mean': 0.5756, 'size': 450}, 'improved': {'mean': 0.64, 'size': 450}}
150 0.0644
67 42 41
```

The pass rate is 0.576 for `baseline` and 0.640 for `improved`, from 450 runs each: a difference of 0.064. The second part is the paired table: for each task, the mean over its three seeds for each configuration. 67 tasks are better with `improved`, 42 are worse and 41 are equal. The mean of the 150 differences is the same 0.064.

#### `pdbook.evals.load_runs`

```text
pdbook.evals.load_runs(
    path=None,
)
```

The function returns one row for each task, configuration and seed. The nested `tokens` object becomes the columns `tokens.prompt` and `tokens.completion`, with `json_normalize` ([Chapter 22](22-json-and-nested-records.md)).

The table under `pdbook.evals.load_runs` in the Reference section of this chapter gives each parameter and what goes wrong with it.

A claim that one configuration is better needs an interval. `compare_configs` resamples the *tasks* with replacement 2,000 times, and takes the mean difference of each resample:

```python
import pandas as pd

from pdbook.evals import compare_configs, load_runs

runs = load_runs()
r = compare_configs(runs)
for key in ["tasks", "rate_a", "rate_b", "diff", "paired_se", "unpaired_se", "ci_low", "ci_high"]:
    print(f"{key:12s} {r[key]:.4f}")

by_category = {}
for category, part in runs.groupby("category"):
    c = compare_configs(part)
    by_category[category] = (round(c["diff"], 3), round(c["paired_se"], 3), int(c["tasks"]))
print(by_category)
```

```text
tasks        150.0000
rate_a       0.5756
rate_b       0.6400
diff         0.0644
paired_se    0.0308
unpaired_se  0.0325
ci_low       0.0022
ci_high      0.1244
{'billing': (-0.022, 0.07, 30), 'device': (0.078, 0.071, 30), 'outage': (0.022, 0.06, 30), 'roaming': (0.144, 0.069, 30), 'routing': (0.1, 0.075, 30)}
```

The interval of the difference is 0.002 to 0.124. The lower end is close to zero, so the data are compatible with a very small effect and with an effect of twelve points. The paired standard error is 0.031 and the unpaired one is 0.033, so pairing helped by about 5% here. The reason that it helps little is in the construction of these data. A run passes with a probability between about 0.2 and 0.9. The result of one run is mostly chance, and the difficulty of the task is a small part of it.

The breakdown by category is the trap of the table. Each category has 30 tasks, and the standard error of its difference is between 0.06 and 0.075. Four of the five differences are inside two standard errors of zero. `roaming` is 0.144, which is 2.1 standard errors.

Five categories give five chances. Suppose that no category has a real effect. The chance that at least one of five is beyond 1.96 standard errors is 1 − 0.95⁵, which is 23%. A report that says "the improvement is in `roaming`" can be a report of noise. Report the interval for the whole set, and name the number of tasks behind every cell.

#### `pdbook.evals.compare_configs`

```text
pdbook.evals.compare_configs(
    runs,
    a='baseline',
    b='improved',
    n_boot=2000,
    seed=0,
)
```

The function returns a dict: `tasks`, `rate_a`, `rate_b`, `diff` (b minus a), `paired_se`, `unpaired_se`, `ci_low`, `ci_high`, `tasks_better` and `tasks_worse`.

The table under `pdbook.evals.compare_configs` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Build: the results as a table

The numbers that go in a report are the ones in `compare_configs`. A report that shows a difference without its interval, or without the number of tasks, is not finished:

```python
import pandas as pd

from pdbook.evals import compare_configs, load_runs

r = compare_configs(load_runs())
table = pd.DataFrame({
    "baseline": [r["rate_a"]],
    "improved": [r["rate_b"]],
    "difference": [r["diff"]],
    "95% low": [r["ci_low"]],
    "95% high": [r["ci_high"]],
    "tasks": [int(r["tasks"])],
    "better": [int(r["tasks_better"])],
    "worse": [int(r["tasks_worse"])],
}).round(3)
print(table.to_string(index=False))
```

```text
 baseline  improved  difference  95% low  95% high  tasks  better  worse
    0.576      0.64       0.064    0.002     0.124    150      67     42
```

## How it works

The bootstrap is a way to ask "how much would the mean change with other tasks?" without a formula. It draws tasks with replacement from the tasks that you have, and makes many new data sets of the same size. It takes the mean difference of each, and it reads the spread of those means. The 95% interval is the 2.5th and the 97.5th percentile. The unit of the draw is the task, because the three seeds of a task are not three independent tasks.

You can run it by hand with another seed, to see how much the interval moves with the draw itself:

```python
import numpy as np

from pdbook.evals import compare_configs, load_runs

runs = load_runs()
per_task = runs.groupby(["task_id", "config"])["passed"].mean().unstack()
diff = (per_task["improved"] - per_task["baseline"]).to_numpy()

ends = []
for seed in range(5):
    rng = np.random.default_rng(100 + seed)
    means = np.array([rng.choice(diff, size=len(diff), replace=True).mean() for _ in range(2000)])
    ends.append(np.percentile(means, [2.5, 97.5]))
ends = np.array(ends)
print(ends.round(3).tolist())
print(round(float(ends[:, 0].max() - ends[:, 0].min()), 3), round(float(ends[:, 1].max() - ends[:, 1].min()), 3))
print(round(float(diff.mean() - 1.96 * diff.std(ddof=1) / np.sqrt(len(diff))), 3),
      round(float(diff.mean() + 1.96 * diff.std(ddof=1) / np.sqrt(len(diff))), 3))
```

```text
[[0.004, 0.122], [0.004, 0.122], [0.004, 0.124], [0.0, 0.124], [0.007, 0.124]]
0.007 0.002
0.004 0.125
```

Five seeds give five intervals. The lower ends are 0.000 to 0.007. The upper ends are 0.122 to 0.124. The second decimal is stable, and the third is noise. The normal-theory interval in the last line, the mean plus and minus 1.96 standard errors, agrees with the bootstrap to the second decimal.

- **Invariant.** The bootstrap interval is a statement about the tasks that you have. It says how the mean difference varies when you draw other tasks like them.
- **Failure.** The unit of the draw is wrong: the runs, and not the tasks. The interval is then too narrow if runs of one task are alike.
- **Cost.** 2,000 resamples of 150 numbers each, which is a fraction of a second. The cost is small, so use enough resamples that the ends do not move in the second decimal.

The failure line says that the unit of the draw matters when the runs of one task are alike. The next block measures how much it matters here. It resamples three sets. The first is the 150 task differences. The second is the 450 differences of task and seed, as if they were independent. The third is the 150 task differences copied three times, the extreme case of runs that are all alike:

```python
import numpy as np

from pdbook.evals import load_runs

runs = load_runs()
wide = runs.pivot_table(index=["task_id", "seed"], columns="config", values="passed")
by_pair = (wide["improved"] - wide["baseline"]).to_numpy()
by_task = (wide["improved"] - wide["baseline"]).groupby(level="task_id").mean().to_numpy()
copies = np.repeat(by_task, 3)
rng = np.random.default_rng(0)


def interval(x, n=2000):
    means = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return np.percentile(means, [2.5, 97.5])


for name, x in [("150 tasks", by_task), ("450 pairs as independent", by_pair), ("150 tasks copied 3 times", copies)]:
    low, high = interval(x)
    print(f"{name:26s} {low:6.3f} {high:6.3f}  width {high - low:.3f}")
seeds = wide["baseline"].unstack()
print("correlation of two seeds of one task:", round(float(np.corrcoef(seeds[0], seeds[1])[0, 1]), 2))
```

```text
150 tasks                   0.002  0.124  width 0.122
450 pairs as independent    0.004  0.120  width 0.116
150 tasks copied 3 times    0.031  0.099  width 0.067
correlation of two seeds of one task: 0.19
```

The draw of 450 pairs gives an interval only a little narrower than the draw of 150 tasks. The seeds of one task are only weakly alike here: the correlation of two seeds is small, so the 450 pairs carry almost 450 pieces of information. The copies show the other end.

Three copies of one result carry no more information than one. The interval still shrinks by about the square root of 3, with no new evidence. Real evaluations sit between the two. Draw the tasks, and the interval is right in both cases.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pdbook.features.past_features` | The question and the cutoff | features from the calls before a local cutoff |
| `pdbook.features.target` | The question and the cutoff | the calls from the cutoff on, 0 for none |
| `pdbook.features.leaky_features` | The easy feature leaks | the count over the whole table; it leaks |
| `pdbook.features.assert_no_leak` | Test for the leak | `AssertionError` when the features move with the future |
| `pdbook.evals.load_runs` | Compare two configurations | the runs as a flat table |
| `pdbook.evals.compare_configs` | Compare two configurations | rates, the paired difference, and a bootstrap interval over tasks |
| `pd.json_normalize` | Compare two configurations ([Chapter 22](22-json-and-nested-records.md) has the block) | nested dicts as columns |
| `pd.DataFrame.groupby` | Compare two configurations ([Chapter 8](08-group-by.md) has the block) | groups of rows by keys |

### Parameters

##### `pdbook.features.past_features`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records, with a zoned `start` | — |
| `subscribers` | required | the subscriber ids, as a Series. Each id gets a row | an id with no past call gets `calls` 0 and `NaN` for `answered_share` and `days_since_last` |
| `cutoff` | required | the cutoff as text, such as `"2026-09-22"`. It is local midnight in `Europe/Brussels` | a `Timestamp` that already has a zone raises `ValueError`. A UTC midnight would put the calls from 22:00 to 24:00 on the wrong side: 8 calls |

##### `pdbook.features.target`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | — |
| `subscribers` | required | the subscriber ids | an id with no future call gets 0, not `NaN` |
| `cutoff` | required | the same cutoff as for `past_features` | a different cutoff for the target and the features leaks or loses days, with no error |

##### `pdbook.features.leaky_features`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `calls` | required | the call records | it has no cutoff, so it reads the future: it fails `assert_no_leak` |
| `subscribers` | required | the subscriber ids | — |

##### `pdbook.features.assert_no_leak`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `feature_fn` | required | a function of `(calls, subscribers)` that returns the features | — |
| `calls` | required | the call records | — |
| `subscribers` | required | the subscriber ids | — |
| `cutoff` | required | the cutoff that defines the future for the test | the test trusts this cutoff. A feature with a cutoff of 22 September passes a test with a cutoff of 25 September, although it is wrong for that later date. A feature with a cutoff of 25 September fails a test at 22 September, as it must |

##### `pdbook.evals.load_runs`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `path` | `None` | the JSON-lines file. With `None`, `data/runs.jsonl` | — |

##### `pdbook.evals.compare_configs`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `runs` | required | the runs of `load_runs` | — |
| `a` | `'baseline'` | the configuration to compare against | a name that is not in `runs` raises `KeyError`. Swap `a` and `b`, and the difference changes sign |
| `b` | `'improved'` | the configuration to test | — |
| `n_boot` | `2000` | the number of bootstrap resamples | with 50, the lower end went from 0.006 to 0.020 over the seeds 0 to 5. With 2000, it went from 0.002 to 0.004 over the seeds 0 to 2 |
| `seed` | `0` | the seed of the resampling | — |


## What you have now

- You split by time, in the zone of the business, and build features from the past only.
- You test a feature for leakage by changing the future, and you know a shuffle is not enough.
- You compare two configurations on the same tasks, with the task as the unit and an interval.
- You report the number of tasks next to every cell, and you do not read a breakdown that has 30 tasks.

The last chapter collects what the book measured into one field guide.

Next: [Chapter 24, Field guide](24-field-guide.md).
