# Pandas at Work: Practical Data Analysis on Call Records

*A practical book on pandas 3.0. Code that ships with the text printed every number in it.*

This book teaches pandas with one small data set, the call records of a mobile operator. It follows one rule: **nothing is asserted that was not run**. Each chapter builds something that you keep. Examples are a loader, a validator, a report and a leak test.

Each chapter shows the mechanism under the code. At the first use of each function, it prints the full signature and explains every parameter in a table. It ends with exercises and worked solutions. The checker of the book executes every code block. It compares every printed output with what the code prints now.

It targets **pandas 3.0**. Most tutorials on the web describe pandas 1.x or 2.x, and 3.0 changed behavior that matters: text is stored as `str`, copy-on-write is always on, timestamps have microsecond resolution. Chapter 24 lists each change that the book ran.

The data are synthetic. A generator, [`pdbook/datasets.py`](pdbook/datasets.py), makes them, and they ship in [`data/`](data/). You can reproduce every number.

## Contents

| # | Chapter | You build | Run first |
|---|---|---|---|
| | **Part I — The data in, and what you have** | | |
| 1 | [Series and DataFrame](chapters/01-series-and-dataframe.md) | `first_look`: what each column holds, what is missing, what it costs | `python -m examples.ch01_first_look` |
| 2 | [Input and output](chapters/02-input-and-output.md) | a loader with the right type for every column, and a round-trip test | `python -m examples.ch02_input_output` |
| 3 | [Selection](chapters/03-selection.md) | five operations questions, each one selection | `python -m examples.ch03_selection` |
| 4 | [Types and memory](chapters/04-types-and-memory.md) | `shrink`: the smallest dtype that holds the values, with a proof of equal content | `python -m examples.ch04_types_memory` |
| 5 | [Missing data](chapters/05-missing-data.md) | a null report that finds which column decides each null | `python -m examples.ch05_missing` |
| 6 | [Text and date cleanup](chapters/06-text-and-date-cleanup.md) | a cleaner that returns the rejects with the clean table | `python -m examples.ch06_cleanup` |
| | **Part II — Transform** | | |
| 7 | [New columns](chapters/07-new-columns.md) | a bill from three tables, three ways, with the cost of each | `python -m examples.ch07_new_columns` |
| 8 | [Group by](chapters/08-group-by.md) | one row for each subscriber, with four totals checks | `python -m examples.ch08_group_by` |
| 9 | [Joins](chapters/09-joins.md) | enrichment that refuses to multiply rows | `python -m examples.ch09_joins` |
| 10 | [Pivot and melt](chapters/10-pivot-and-melt.md) | a weekday-by-hour grid and an exact round trip | `python -m examples.ch10_pivot` |
| 11 | [The index and MultiIndex](chapters/11-index-and-multiindex.md) | `index_audit`: what an index promises | `python -m examples.ch11_index` |
| | **Part III — Time, windows and the traps** | | |
| 12 | [Dates and resampling](chapters/12-dates-and-resampling.md) | hourly KPIs in local time, including the day with 25 hours | `python -m examples.ch12_dates` |
| 13 | [Windows, shifts and gaps](chapters/13-windows-shifts-gaps.md) | a spike flagger, scored against a known spike | `python -m examples.ch13_windows` |
| 14 | [Ranks, running totals and sessions](chapters/14-ranks-running-totals-sessions.md) | sessions that do not depend on row order | `python -m examples.ch14_sessions` |
| 15 | [Copy-on-Write and traps](chapters/15-copy-on-write-and-traps.md) | ten traps, each with a test that it is still live | `python -m examples.ch15_traps` |
| 16 | [Method chains and pipelines](chapters/16-method-chains-and-pipelines.md) | the monthly report as one chain with checks inside | `python -m examples.ch16_chain` |
| | **Part IV — Doing it right and at scale** | | |
| 17 | [Data validation](chapters/17-data-validation.md) | rules, a report, and a validator measured with planted faults | `python -m examples.ch17_validation` |
| 18 | [Performance](chapters/18-performance.md) | one task five ways, timed, and the cost of three common choices | `python -m examples.ch18_performance` |
| 19 | [Data larger than memory](chapters/19-data-larger-than-memory.md) | a chunked aggregate equal to the whole, with measured peak memory | `python -m examples.ch19_chunked` |
| 20 | [SQL and pandas](chapters/20-sql-and-pandas.md) | the same report in SQL and in pandas, proved equal | `python -m examples.ch20_sql` |
| 21 | [Plots](chapters/21-plots.md) | four figures, each tested by the data in it | `python -m examples.ch21_plots` |
| | **Part V — Other shapes of data, and the field guide** | | |
| 22 | [JSON and nested records](chapters/22-json-and-nested-records.md) | a flat events table, checked against the call records in both directions | `python -m examples.ch22_json` |
| 23 | [Features and evaluation](chapters/23-features-and-evaluation.md) | features with no leak, and a paired comparison with an interval | `python -m examples.ch23_features` |
| 24 | [Field guide](chapters/24-field-guide.md) | question-to-idiom map, what changed in 3.0, what went wrong while writing | `python -m examples.ch24_field_guide` |

Run the commands from the root of the book with `uv run`, for example `uv run python -m examples.ch01_first_look`.

Each chapter has the same shape:

- A header with *Build*, *Theory kept*, *Source* and *Run this first*.
- The working material.
- **How it works**: the mechanism, with one executed block and three lines (invariant, failure, cost).
- A `####` block at the first use of each function: the full signature of the installed library, then one row for each parameter, with its default and a measured consequence or `—`. A later chapter links back to the block. It does not repeat it.
- **Reference**: an index of the functions of the chapter, with the section that introduces each one.
- A summary with a link to the next chapter.

Exercises are in [`exercises/`](exercises/) (`NN.md`) and worked solutions in [`exercises/solutions/`](exercises/solutions/). Each chapter has three kinds:

- **[measure]**: run something and report a number. The expected answer is given.
- **[break]**: change one thing so that a result reverses, and say why.
- **[judge]**: no single right answer. The solution gives a position, the strongest objection, and what changes the position.

The code in the solutions runs under the same checker.

Appendices: [A — described, not built](appendices/A-described-not-built.md) (what the book says and did not run) · [B — what Python already gives you](appendices/B-python-tools.md) · [C — what went wrong](appendices/C-what-went-wrong.md) (the statements of the book that a run showed to be wrong, and the statements of the documentation that pandas 3.0.6 does not follow).

## How to run and check it

```bash
uv sync                                          # installs pandas 3.0, numpy, pyarrow, matplotlib
uv run python scripts/check_snippets.py          # every block runs, every output matches, every link resolves
uv run python scripts/verify_claims.py           # key numbers recomputed without pandas, and the data pinned by SHA-256
python3 scripts/audit_numbers.py                 # lists numbers in the prose that no output contains
uv run python scripts/audit_examples.py          # lists samples that break the four sample rules
```

`check_snippets.py` also fails on any warning that a block writes to stderr, because a reader copies the block. Blocks that print a time have `# output varies` above the output and an assertion that checks an order of magnitude. The checker runs the blocks that measure time one at a time, after the others. Run it on an idle machine all the same: a timing assertion can fail under load, and that is not an error in the book. `scripts/refresh_varies.py` rewrites the printed timings from a fresh run.

## What the checks cover, and what they do not

At the last full run, the checker executed 280 Python blocks and compared 258 printed outputs. It checked the signature, the defaults and one row for each parameter of 143 callables.

`verify_claims.py` agreed on 24 claims that it computed without pandas. The number audit lists the numbers of the prose that no output contains. Each of them is a derived value (a percentage, a difference, a unit conversion), a value that quotes a block of another chapter, or an example that was not measured. The audit is a list for a person to read. It is not a pass or a fail.

What is **not** checked: statements about other versions of pandas, about packages that are not installed, and about real networks. [Appendix A](appendices/A-described-not-built.md) lists them. The timings are from one machine. Chapter 19 measures peak memory with `/proc` and works on Linux only. The data are synthetic, so the book says nothing about how often a fault occurs in real call records.

The book also shows its own corrections. [Chapter 24](chapters/24-field-guide.md) lists the first-draft claims that the machine contradicted, with the cause of each. [Appendix C](appendices/C-what-went-wrong.md) lists the statements that later audits found wrong. Four tools exist because of them: [`scripts/audit_numbers.py`](scripts/audit_numbers.py), [`scripts/refresh_varies.py`](scripts/refresh_varies.py), [`scripts/audit_examples.py`](scripts/audit_examples.py) and the signature printer [`pdbook/sigs.py`](pdbook/sigs.py).

## The data

| File | What it is |
|---|---|
| [`data/calls.csv`](data/calls.csv) | 20,000 call records for September 2026 (UTC timestamps; the last 1,000 rows arrive late) |
| [`data/subscribers.csv`](data/subscribers.csv), [`data/plans.csv`](data/plans.csv), [`data/cells.csv`](data/cells.csv) | lookup tables: 600 subscribers, 4 plans, 12 cells |
| [`data/kpi.csv`](data/kpi.csv) | 5-minute KPIs for 6 cells over three days, with gaps, an outage, repeats and one injected spike |
| [`data/contacts_messy.csv`](data/contacts_messy.csv) | a customer export with mixed formats, duplicates and six values that no rule can repair |
| [`data/traces.jsonl`](data/traces.jsonl) | 500 call traces with nested events, some with missing parts |
| [`data/runs.jsonl`](data/runs.jsonl) | an evaluation: 150 tasks, 2 configurations, 3 seeds |

`uv run python -m pdbook.datasets` regenerates them. Another version of numpy can change the bytes, which is why `verify_claims.py` pins the SHA-256 of each file.

## Written in Simplified Technical English

The prose follows the rules of ASD-STE100: short sentences, one instruction in each, active voice, approved words and named technical terms. The structural rules (sentence and paragraph length, modal verbs, passive, semicolons) were checked with a script on every chapter. The check of the vocabulary is advisory, because the technical names of pandas are not in the approved list. This is not an official ASD document.
