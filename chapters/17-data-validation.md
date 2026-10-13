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

## Measure the validator

A validator that finds nothing on the real data is right, or it is blind. The way to know is to break the data in a known way and count. The function `plant_faults` makes six kinds of fault on separate rows and returns the number of violations that each rule must find:

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

## Reference

```python
import pandas as pd

from pdbook.sigs import show_signature
from pdbook.validate import Rule, assert_valid, call_rules, check_schema, plant_faults, validate

show_signature(pd.testing.assert_frame_equal, ["check_dtype", "check_like", "check_exact", "rtol", "atol"])
show_signature(pd.Series.isin, ["values"])
show_signature(Rule)
show_signature(check_schema)
show_signature(call_rules)
show_signature(validate)
show_signature(assert_valid)
show_signature(plant_faults)
```

```text
assert_frame_equal(
    check_dtype: "bool | Literal['equiv']" = True
    check_exact: 'bool | lib.NoDefault' = <no_default>
    check_like: 'bool' = False
    rtol: 'float | lib.NoDefault' = <no_default>
    atol: 'float | lib.NoDefault' = <no_default>
)  # 12 more parameters
Series.isin(
    values
)  # 1 more parameters
Rule(
    name: 'str'
    violated: 'Callable[[pd.DataFrame], pd.Series]'
    severity: 'str' = 'error'
)
check_schema(
    df: 'pd.DataFrame'
    expected: 'dict[str, str]' = {'call_id': 'int64', 'start': 'datetime64[us, UTC]', 'caller': 'str', 'callee': 'str', 'duration_s': 'float64', 'status': 'str', 'cell_id': 'str', 'codec': 'str', 'roaming': 'bool'}
)
call_rules(
    subs: 'pd.DataFrame'
    cells: 'pd.DataFrame'
    first: 'str' = '2026-08-31 22:00'
    last: 'str' = '2026-09-30 22:00'
)
validate(
    df: 'pd.DataFrame'
    rules: 'list[Rule]'
)
assert_valid(
    report: 'pd.DataFrame'
)
plant_faults(
    df: 'pd.DataFrame'
    seed: 'int' = 0
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `assert_frame_equal(check_like=...)` | `False` | ignore the order of rows and columns | `False` fails on a reordered table |
| `assert_frame_equal(rtol=..., atol=...)` | `1e-5`, `1e-8` when not set | the tolerance for floats | `rtol=0` alone still accepts a difference of 1e-9, because `atol` does |
| `assert_frame_equal(check_exact=...)` | not set | `True` compares floats exactly | — |
| `assert_frame_equal(check_dtype=...)` | `True` | compare the dtypes | — |
| `Rule(name, violated, severity=...)` | required, `'error'` | a name, a function that returns `True` for each bad row, and a severity | a range rule such as `d < 0` does not fire on a null |
| `check_schema(df, expected=...)` | required, the call schema | a list of problems with the names and dtypes | — |
| `call_rules(subs, cells, first, last)` | required, month bounds in UTC | the 10 rules for call records | — |
| `validate(df, rules)` | required | one row for each rule: violations, share, first three row labels | — |
| `assert_valid(report)` | required | raises `ValueError` when a rule of severity `error` has violations | — |
| `plant_faults(df, seed=...)` | required, `0` | a broken copy and the exact count that each rule must find | the counts are the same for every seed: 7, 5, 11, 4, 3, 4, 2 |

`validate` returns a DataFrame with the columns `rule`, `severity`, `violations`, `share` and `first_rows`.

## What you have now

- You name six classes of rule and write one line for each.
- You keep rules as data, and get a report with a count for each rule.
- You test a validator with faults that you plant, and you expect exact counts.
- You stop a job on an `error` rule, and report a `warn` rule.
- You compare tables in tests with a tolerance that you chose.

The next chapter measures speed, and shows where the time of a pandas job goes.

Next: [Chapter 18, Performance](18-performance.md).
