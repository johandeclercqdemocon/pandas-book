# 17. Data validation

> **Build** — A small validation layer for the call records: a list of rules, a report of how many rows break each one, a schema check and a way to stop a job. The layer is measured. It must find exactly the faults that a function plants in a copy of the table.
>
> **Theory kept** — A cleaner repairs what it can. A validator states what must be true and reports the rows where it is not. Run it where data enter the job, before the first join and before the report. Test the validator itself with faults that you plant.
>
> **Source** — New. Library: [`pdbook/validate.py`](../pdbook/validate.py).
>
> **Run this first** — `uv run python -m examples.ch17_validation`, which is [`examples/ch17_validation.py`](../examples/ch17_validation.py). Exercises: [`exercises/17.md`](../exercises/17.md). Solutions: [`exercises/solutions/17.md`](../exercises/solutions/17.md).

## What to check

Most faults in a table fall in six classes. A rule in each class costs one line:

| Class | Question | Example in the call records |
|---|---|---|
| schema | right columns, right dtypes? | `callee` is text, not an integer |
| domain | values in the allowed set or range? | `status` is one of four words; duration is not negative |
| uniqueness | is the key unique? | `call_id` |
| completeness | are required values present? | a call has a cell |
| relational | does the key exist in the other table? | the caller is a known subscriber |
| cross-column | do two columns agree? | an answered call has a duration above 0 |

Cleaning ([Chapter 6](06-text-and-date-cleanup.md)) and validation do different work. A cleaner changes data. A validator never changes data. It says which rows break a rule, and it lets the job decide: stop, drop, or send to a person.

## The schema

The first check is cheap and finds the largest class of faults, a file that changed format:

```python
import pandas as pd

from pdbook.io import load_calls
from pdbook.validate import check_schema

calls = load_calls()
print(check_schema(calls))

naive = pd.read_csv("data/calls.csv")
for problem in check_schema(naive):
    print(problem)
```

```text
[]
start: dtype str, expected datetime64[us, UTC]
callee: dtype int64, expected str
```

The loader gives a table that passes. The plain `read_csv` gives two problems: `start` is text and `callee` is an integer. This check, on the first line of a job, finds a changed file before the job spends an hour on it.

The functions of this chapter are in [`pdbook/validate.py`](../pdbook/validate.py).

#### `pdbook.validate.check_schema`

```text
pdbook.validate.check_schema(
    df,
    expected={'call_id': 'int64', 'start': 'datetime64[us, UTC]', 'caller': 'str', 'callee': 'str', 'duration_s': 'float64', 'status': 'str', 'cell_id': 'str', 'codec': 'str', 'roaming': 'bool'},
)
```

The function returns a list of problems with the column names and dtypes. An empty list means that the schema is as expected.

The table under `pdbook.validate.check_schema` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Rules as data

A rule is a name, a function that returns `True` for each row that breaks it, and a severity. Keep the rules in a list, so that a report can go through them:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells, load_subscribers
from pdbook.validate import call_rules, validate

calls, subs, cells = load_calls(), load_subscribers(), load_cells()
rules = call_rules(subs, cells)
print(len(rules), rules[3].name)

report = validate(calls, rules)
print(report[["rule", "severity", "violations"]].to_string(index=False))
```

```text
10 an answered call has a duration above 0
                                           rule severity  violations
                              call_id is unique    error           0
                      status is one of the four    error           0
                       duration is not negative    error           0
        an answered call has a duration above 0    error           0
a call that is not answered has a codec of none    error           0
      callee is in the form +32 and nine digits    error           0
                   caller is a known subscriber    error           0
                      start is inside the month    error           0
               cell is known when it is present    error           0
                              a call has a cell     warn         277
```

On the real data, nine rules have no violation. The tenth, "a call has a cell", has 277 with the severity `warn`. [Chapter 5](05-missing-data.md) showed those 277 calls: the loss of cell identifiers is a known property of the data. A `warn` rule is reported and does not stop the job. An `error` rule stops it.

#### `pdbook.validate.Rule`

```text
pdbook.validate.Rule(
    name,
    violated,
    severity='error',
)
```

The class is a dataclass: one rule as a name, a function and a severity.

The table under `pdbook.validate.Rule` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.validate.call_rules`

```text
pdbook.validate.call_rules(
    subs,
    cells,
    first='2026-08-31 22:00',
    last='2026-09-30 22:00',
)
```

The function returns the 10 rules for the call records, as a list of `Rule`.

The table under `pdbook.validate.call_rules` in the Reference section of this chapter gives each parameter and what goes wrong with it.

#### `pdbook.validate.validate`

```text
pdbook.validate.validate(
    df,
    rules,
)
```

The function returns one row for each rule: `rule`, `severity`, `violations`, `share` and `first_rows`, the first three row labels.

The table under `pdbook.validate.validate` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Measure the validator

A validator that finds nothing on the real data is right, or it is blind. The way to know is to break the data in a known way and count. The function `plant_faults` makes seven kinds of fault on separate rows and returns the number of violations that each rule must find:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells, load_subscribers
from pdbook.validate import call_rules, plant_faults, validate

calls, subs, cells = load_calls(), load_subscribers(), load_cells()
broken, expected = plant_faults(calls)
report = validate(broken, call_rules(subs, cells))
found = dict(zip(report["rule"], report["violations"]))

for rule, n in expected.items():
    print(f"planted {n:>2d} found {found[rule]:>2d}  {rule}")
print(all(found[r] == n for r, n in expected.items()))
print({r: v for r, v in found.items() if r not in expected})
```

```text
planted  7 found  7  call_id is unique
planted  5 found  5  duration is not negative
planted 11 found 11  an answered call has a duration above 0
planted  4 found  4  a call that is not answered has a codec of none
planted  3 found  3  callee is in the form +32 and nine digits
planted  4 found  4  caller is a known subscriber
planted  2 found  2  start is inside the month
True
{'status is one of the four': 0, 'cell is known when it is present': 0, 'a call has a cell': 277}
```

The rule for answered calls finds 11, not 6 or 5. The function broke 5 durations to a negative value and 6 to a missing value. A negative value is not "above 0" either, so both kinds break that rule. The expected number includes it. A rule can have two causes, and the report says only how many rows break it.

#### `pdbook.validate.plant_faults`

```text
pdbook.validate.plant_faults(
    df,
    seed=0,
)
```

The function returns a broken copy of `df` and a dict: the exact number of violations that each rule must report.

The table under `pdbook.validate.plant_faults` in the Reference section of this chapter gives each parameter and what goes wrong with it.

The last line shows the rules that no fault was planted for: `status`, `cell is known` and the warning. They find 0, 0 and 277, the same as on the clean data. A validator that is exact on 7 rules, and gives the clean-data result on the other 3, is what you want.

## Stop the job

`assert_valid` raises an error when a rule with the severity `error` has any violation, and it lists the rules and the counts:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells, load_subscribers
from pdbook.validate import assert_valid, call_rules, plant_faults, validate

calls, subs, cells = load_calls(), load_subscribers(), load_cells()
rules = call_rules(subs, cells)

assert_valid(validate(calls, rules))
print("clean data pass")

broken, _ = plant_faults(calls)
try:
    assert_valid(validate(broken, rules))
except ValueError as error:
    print(error)
```

```text
clean data pass
data validation failed:
  call_id is unique: 7
  duration is not negative: 5
  an answered call has a duration above 0: 11
  a call that is not answered has a codec of none: 4
  callee is in the form +32 and nine digits: 3
  caller is a known subscriber: 4
  start is inside the month: 2
```

A job that stops on a violation is a design choice. The alternative is to remove the rows and to continue, and to send the removed rows to a person. Both are better than a report that has the faults inside it. Which one you choose depends on the cost of a missing row against the cost of a wrong row. A billing job prefers to stop. A dashboard prefers to drop and to show the count.

#### `pdbook.validate.assert_valid`

```text
pdbook.validate.assert_valid(
    report,
)
```

The function returns nothing when no rule of severity `error` has a violation. Otherwise it raises `ValueError` with each failing rule and its count.

The table under `pdbook.validate.assert_valid` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Compare tables in tests

The validator checks a table against rules. A test of a function checks a result against an expected table. The tool is `pd.testing.assert_frame_equal`, and its arguments say what "equal" means:

```python
import pandas as pd

a = pd.DataFrame({"x": [1.0, 2.0], "y": ["u", "v"]}, index=[0, 1])
b = pd.DataFrame({"y": ["v", "u"], "x": [2.0, 1.0 + 1e-9]}, index=[1, 0])

for label, kwargs in [("strict", {}), ("like", {"check_like": True}),
                      ("rtol=0", {"check_like": True, "rtol": 0}),
                      ("exact", {"check_like": True, "check_exact": True})]:
    try:
        pd.testing.assert_frame_equal(a, b, **kwargs)
        print(f"{label:12s} equal")
    except AssertionError as error:
        print(f"{label:12s} different: {str(error).splitlines()[0]}")
```

```text
strict       different: DataFrame.index are different
like         equal
rtol=0       equal
exact        different: DataFrame.iloc[:, 1] (column name="x") are different
```

The strict comparison fails on the order of the rows and the columns. With `check_like=True` the order does not matter, and the two tables are equal. The difference of 1e-9 is inside the default tolerances, which are `rtol=1e-5` and `atol=1e-8`. Setting `rtol=0` alone is not enough, because the absolute tolerance still accepts the difference.

Only `check_exact=True` makes the same two tables different. Set the tolerance on purpose. A test with the defaults hides a relative difference of 0.001%, and a test for money must be exact.

#### `pd.testing.assert_frame_equal`

```text
pd.testing.assert_frame_equal(
    left,
    right,
    check_dtype=True,
    check_index_type='equiv',
    check_column_type='equiv',
    check_frame_type=True,
    check_names=True,
    by_blocks=False,
    check_exact=<no_default>,
    check_datetimelike_compat=False,
    check_categorical=True,
    check_like=False,
    check_freq=True,
    check_flags=True,
    rtol=<no_default>,
    atol=<no_default>,
    obj='DataFrame',
)
```

The function returns nothing when the two tables are equal, and raises `AssertionError` with the first difference when they are not.

The table under `pd.testing.assert_frame_equal` in the Reference section of this chapter gives each parameter and what goes wrong with it.

## Where to put it

Run the validator at three places:

1. **At the input.** Right after the load, before you spend time on the data.
2. **Before a join.** The lookup table must be unique on its key (`validate="m:1"` in [Chapter 9](09-joins.md)).
3. **Before the output.** The report must add up to the input ([Chapter 8](08-group-by.md)).

At each place, write the rule as a line of code and not as a comment. A comment that says "the ids are unique" is true on the day that you write it.

## How it works

A rule is a function from a table to a boolean Series: `True` on the rows that break the rule. The report counts the `True` values. The validator has no other part.

The consequence is the one of [Chapter 3](03-selection.md): a comparison with a missing value is `False`, so a rule of the form "value below 0" does not fire on a null. A null needs its own rule.

You can check that the report is the sum of the masks, and see what a null does to a range rule:

```python
import pandas as pd

from pdbook.io import load_calls, load_cells, load_subscribers
from pdbook.validate import Rule, call_rules, validate

calls = load_calls()
broken = calls.copy()
broken.loc[broken.index[:3], "duration_s"] = -1.0
broken.loc[broken.index[3:5], "duration_s"] = float("nan")

negative = Rule("duration is not negative", lambda d: d["duration_s"] < 0)
mask = negative.violated(broken)
report = validate(broken, [negative])
print(int(mask.sum()), int(report["violations"].iloc[0]), report["first_rows"].iloc[0])

s = pd.Series([1.0, None, -1.0])
print((s < 0).tolist(), (~s.isin([1.0, 2.0])).tolist())

rules = call_rules(load_subscribers(), load_cells())
print(len(rules), sum(1 for r in rules if r.severity == "error"))
```

```text
3 3 [0, 1, 2]
[False, False, True] [False, True, True]
10 9
```

The mask has 3 `True` values, and the report says 3 with the labels 0, 1 and 2. The two rows that were set to `NaN` are not in the count, because `NaN < 0` is `False`. The second line shows the same for `~isin`: the missing value is "not in the list", so it is `True`, and a rule of that form fires on nulls. The two forms differ, and a rule needs to be written with its behavior on nulls in mind.

- **Invariant.** The number in the report is the number of `True` values in the mask of the rule.
- **Failure.** A range rule does not see a null. A set rule (`~isin`) does.
- **Cost.** One pass over the table for each rule. Ten rules on 20,000 rows are ten column operations, not ten loops.

The tolerance of `assert_frame_equal` is a rule too, and it is not the rule of NumPy. `np.isclose(a, b)` tests `|a - b| <= atol + rtol * |b|`: it adds the two tolerances, and it uses only `b`, so it is not symmetric. pandas tests `|a - b| <= max(rtol * max(|a|, |b|), atol)`, the rule of `math.isclose`. The next block puts the three side by side on pairs near the edge:

```python
import math

import numpy as np
import pandas as pd


def pandas_equal(a, b):
    try:
        pd.testing.assert_series_equal(pd.Series([a]), pd.Series([b]))
    except AssertionError:
        return False
    return True


pairs = [(1 + 1.0005e-5, 1.0), (1000.0100001, 1000.0), (1000.0, 1000.0100001), (9e-9, 0.0), (1.5e-8, 0.0)]
print(f"{'a':>14s} {'b':>14s}  pandas  math   numpy")
for a, b in pairs:
    print(f"{a!r:>14} {b!r:>14}  {pandas_equal(a, b)!s:6s}  {math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-8)!s:5s}  "
          f"{bool(np.isclose(a, b))!s}")
```

```text
             a              b  pandas  math   numpy
   1.000010005            1.0  False   False  True
  1000.0100001         1000.0  True    True   False
        1000.0   1000.0100001  True    True   True
         9e-09            0.0  True    True   True
       1.5e-08            0.0  False   False  False
```

pandas and `math.isclose` agree on every pair. NumPy differs twice. On the first pair it says equal, because it adds `atol` to the relative tolerance. On the second it says different and on the third equal:

the same two numbers in the other order. A test that compares with `np.isclose` and a test that uses `assert_frame_equal` can disagree at the edge. Choose one and write its tolerance in the test.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pdbook.validate.check_schema` | The schema | a list of problems with names and dtypes; empty when the schema is right |
| `pdbook.validate.Rule` | Rules as data | a name, a function that marks bad rows, and a severity |
| `pdbook.validate.call_rules` | Rules as data | the 10 rules for the call records |
| `pdbook.validate.validate` | Rules as data | one row for each rule: violations, share, first labels |
| `pd.Series.isin` | Rules as data ([Chapter 3](03-selection.md) has the block) | a mask: the value is in a list; a set rule sees nulls |
| `pdbook.validate.plant_faults` | Measure the validator | a broken copy and the exact count each rule must find |
| `pdbook.validate.assert_valid` | Stop the job | `ValueError` when an `error` rule has violations |
| `pd.testing.assert_frame_equal` | Compare tables in tests | `AssertionError` at the first difference; floats within a tolerance |

### Parameters

##### `pdbook.validate.check_schema`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the table to check | — |
| `expected` | `{'call_id': 'int64', 'start': 'datetime64[us, UTC]', 'caller': 'str', 'callee': 'str', 'duration_s': 'float64', 'status': 'str', 'cell_id': 'str', 'codec': 'str', 'roaming': 'bool'}` | a dict of column name to dtype, as text. The default is the schema of the call records | a dtype is compared as text: `datetime64[us, UTC]` and `datetime64[ns, UTC]` are different schemas |

##### `pdbook.validate.Rule`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `name` | required | the sentence that the report shows | — |
| `violated` | required | a function of the table that returns a boolean Series: `True` on each row that breaks the rule | a range rule such as `d < 0` does not fire on a null ([How it works](#how-it-works)) |
| `severity` | `'error'` | `'error'` stops the job in `assert_valid`. `'warn'` is reported only | — |

##### `pdbook.validate.call_rules`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `subs` | required | the subscribers, for the rule "caller is a known subscriber" | — |
| `cells` | required | the cells, for the rule "cell is known when it is present" | — |
| `first` | `'2026-08-31 22:00'` | the first allowed `start`, in UTC: midnight of 1 September in Brussels | — |
| `last` | `'2026-09-30 22:00'` | the end of the allowed range, in UTC | the default bounds are for September 2026. A file of October breaks the rule "start is inside the month" on every row |

##### `pdbook.validate.validate`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the table to check. It never changes | — |
| `rules` | required | a list of `Rule` | — |

##### `pdbook.validate.plant_faults`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `df` | required | the call records. It does not change | — |
| `seed` | `0` | the seed for the choice of the rows | — (the counts are the same for every seed: 7, 5, 11, 4, 3, 4, 2. Only the rows change) |

##### `pdbook.validate.assert_valid`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `report` | required | the result of `validate` | a `warn` rule never stops the job, however many rows break it |

##### `pd.testing.assert_frame_equal`

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `left` | required | the table that the code made | — |
| `right` | required | the expected table | — |
| `check_dtype` | `True` | compare the dtypes | `False` makes `int64` and `float64` with the same values equal |
| `check_index_type` | `'equiv'` | compare the class of the index. `'equiv'` treats a `RangeIndex` and an `Index` of integers as the same | `True` makes them different |
| `check_column_type` | `'equiv'` | the same for the column labels | — |
| `check_frame_type` | `True` | compare the class of the two objects | a subclass of `DataFrame` raises an `AssertionError` with no message |
| `check_names` | `True` | compare the `names` of the index and the columns | an index named `a` differs from one with no name |
| `by_blocks` | `False` | compare the internal blocks, not the columns | — |
| `check_exact` | `<no_default>` | `True` compares floats exactly. Not set means exact for integers and tolerant for floats | — |
| `check_datetimelike_compat` | `False` | compare timestamps of different types by value | any value warns with `Pandas4Warning`: it goes away in pandas 4 |
| `check_categorical` | `True` | compare categories exactly, their order included | the same values with the categories in another order are different |
| `check_like` | `False` | ignore the order of rows and columns: match them by label | `False` fails on a reordered table. With `True`, the labels must still carry the same values |
| `check_freq` | `True` | compare the `freq` of a `DatetimeIndex` | the message is only `(<Day>, None)` |
| `check_flags` | `True` | compare the `flags`, such as `allows_duplicate_labels` | — |
| `rtol` | `<no_default>` | the relative tolerance for floats. Not set means `1e-5` | `rtol=0` alone still accepts a difference of 1e-9, because `atol` does. The rule is not the one of `np.isclose` ([How it works](#how-it-works)) |
| `atol` | `<no_default>` | the absolute tolerance for floats. Not set means `1e-8` | with `check_exact=True`, `rtol` and `atol` are not used |
| `obj` | `'DataFrame'` | the name in the error message | — |


## What you have now

- You name six classes of rule and write one line for each.
- You keep rules as data, and get a report with a count for each rule.
- You test a validator with faults that you plant, and you expect exact counts.
- You stop a job on an `error` rule, and report a `warn` rule.
- You compare tables in tests with a tolerance that you chose.

The next chapter measures speed, and shows where the time of a pandas job goes.

Next: [Chapter 18, Performance](18-performance.md).
