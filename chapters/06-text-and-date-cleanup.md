# 6. Text and date cleanup

> **Build** — `clean_contacts(raw)`: a function that turns the messy contact export into a clean table and returns a second table with each value that it could not repair, so that nothing is guessed in silence.
>
> **Theory kept** — The `.str` accessor applies a text operation to a whole column and passes missing values through. Clean to a form that you can compare, and keep the raw value. A cleaner must return what it rejected.
>
> **Source** — New. Data: [`data/contacts_messy.csv`](../data/contacts_messy.csv). Library: [`pdbook/clean.py`](../pdbook/clean.py).
>
> **Run this first** — `uv run python -m examples.ch06_cleanup`, which is [`examples/ch06_cleanup.py`](../examples/ch06_cleanup.py). Exercises: [`exercises/06.md`](../exercises/06.md). Solutions: [`exercises/solutions/06.md`](../exercises/solutions/06.md).

## The mess

The file `data/contacts_messy.csv` is an export of a customer list that several people typed. It has 271 rows and five columns, and every column has several formats. Read all columns as text, so that pandas guesses nothing:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
print(raw.shape)
print(raw.sample(6, random_state=4).to_string())
print(sorted(raw["plan"].unique())[:8])
```

```text
(271, 5)
                  name             phone      plan             signup     balance
210        Rik De Smet  +32 444 36 50 82     BASIC         2023-03-23       24.19
39     Quinten Peeters  +32 492 60 19 31     plus   February 27, 2022      123.59
162     Petra  Jacobs          402725725     plus           23-May-25  127.07 EUR
121       Lambert, Rik     0427 77 34 15    basic          29/01/2023      364.03
103       lotte MARTIN     0466 93 07 36  BUSINESS       May 13, 2025         NaN
133    maarten WILLEMS     0400 55 87 97    basic           16-Jan-24         NaN
['BASIC', 'BUSINESS', 'Basic', 'Business', 'PLUS', 'PREPAID', 'Plus', 'Prepaid']
```

The same plan is written `basic`, `Basic`, `BASIC` and `basic ` with a space at the end. The phone numbers have five formats. The dates have four formats. The balance has euro signs, thousands separators, a unit, and markers for "no value". Four things are wrong with the names: extra spaces, upper case, lower case and the order "Last, First".

The method is the same for each column: look at the formats, write one rule for each, count what the rules did not catch, and keep that count visible.

## The .str accessor

`.str` gives a Series of text the operations of a Python string, applied to each element:

| Method | What it does |
|---|---|
| `strip()`, `lower()`, `casefold()` | trim, change case |
| `replace(pat, repl, regex=True)` | substitute by pattern |
| `contains(pat)`, `startswith(s)`, `match(pat)` | a boolean mask |
| `extract(pat)` | the groups of a regular expression, as columns |
| `split(sep, expand=True)` | split into columns |
| `len()` | length of each text |

A missing value stays missing. No method fails on it:

```python
import pandas as pd

s = pd.Series(["  Basic ", "PLUS", None, "business"])
print(s.str.strip().str.lower().tolist())
print(s.str.len().tolist())
```

```text
['basic', 'plus', nan, 'business']
[8.0, 4.0, nan, 8.0]
```

## Plan: trim and lower

One rule, then one check that the rule was enough:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
plan = raw["plan"].str.strip().str.lower()
print(raw["plan"].nunique(), "->", plan.nunique())
print(plan.value_counts().to_dict())
print(sorted(set(plan) - {"prepaid", "basic", "plus", "business"}))
```

```text
17 -> 5
{'business': 76, 'plus': 72, 'basic': 63, 'prepaid': 59, 'gold': 1}
['gold']
```

Seventeen spellings became five values. The last line is the check: the plan `gold` is not one of the four plans. No spelling rule repairs it, because it is a different value. The cleaner must reject it, not map it to the nearest plan.

## Names: compare on a key, not on a pretty form

Two jobs hide behind "clean a name". One is to display it. The other is to compare it. Do not use one result for both. For comparison, build a key: trim, collapse the spaces, turn "Last, First" round and fold the case:

```python
import pandas as pd

from pdbook.clean import name_key

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
examples = pd.Series(["  hugo PEETERS", "Peeters, Hugo", "Hugo  Peeters ", "Van den Berg, An"])
print(name_key(examples).tolist())
print(raw["name"].str.strip().nunique(), "->", name_key(raw["name"]).nunique())
print("straße".casefold() == "strasse", "straße".lower() == "strasse")
```

```text
['hugo peeters', 'hugo peeters', 'hugo peeters', 'an van den berg']
236 -> 172
True False
```

The first three names become one key. The key for `Van den Berg, An` is `an van den berg`. Use `casefold` and not `lower`, because `casefold` also maps the German `ß` to `ss`. The block prints the proof.

A display form is harder than it looks. The method `title()` capitalizes every word:

```python
print("van den berg".title())
print("mcdonald".title())
print("o'neil".title())
```

```text
Van Den Berg
Mcdonald
O'Neil
```

All three are wrong for the people who own the names: `Van den Berg`, `McDonald` and `O'Neil` are the usual forms. There is no rule that repairs all names. Keep the raw name for display, and use the key for comparison.

## Phones: one canonical form

The canonical form for a telephone number is E.164: a plus, the country code and the number, with no space. Belgian mobile numbers are `+32` and nine digits. The five formats in the file reduce to one in four steps, and each step is a `str.replace` with a pattern:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
phone = raw["phone"]
step1 = phone.str.replace(r"[^\d+]", "", regex=True)       # drop spaces
step2 = step1.str.replace(r"^\+", "00", regex=True)         # + becomes 00
step3 = step2.str.replace(r"^0032", "", regex=True)         # remove the country code
step4 = step3.str.replace(r"^0", "", regex=True)            # remove the trunk zero
for i in [1, 4, 7, 2]:
    print(f"{phone.iloc[i]!r:20} -> {('+32' + step4.iloc[i])!r}")
print(step4.str.len().value_counts().to_dict())
```

```text
'+32 478 98 50 35'   -> '+32478985035'
'0489 26 66 69'      -> '+32489266669'
'427792646'          -> '+32427792646'
'0032484095226'      -> '+32484095226'
{9: 269, 4: 1, 13: 1}
```

The last line is the check. After the four steps, 269 numbers have 9 digits, and two do not. Those two are the cases that the rules cannot repair: `12 34` is too short, and the UK number `+44 7700 900123` is a valid number of another country. The function `e164` in `pdbook/clean.py` returns `NaN` for them, and `clean_contacts` lists them in the rejects.

## Dates: mixed formats

`to_datetime` looks at the first value to choose a format. A column with four formats fails on the first value that does not fit:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
try:
    pd.to_datetime(raw["signup"])
except ValueError as error:
    print("ValueError:", str(error).splitlines()[0][:60])

parsed = pd.to_datetime(raw["signup"].str.strip(), format="mixed", dayfirst=True, errors="coerce")
print(int(parsed.isna().sum()), "not parsed")
print(raw.loc[parsed.isna(), "signup"].tolist())
```

```text
ValueError: time data "18/07/2025" doesn't match format "%Y-%m-%d". You 
2 not parsed
['31/02/2024', 'someday']
```

`format="mixed"` parses each element on its own. `errors="coerce"` turns what it cannot parse into `NaT`, and the last line shows which values those are. `31/02/2024` is not a date and `someday` is not a date. The cleaner must reject both. The argument `coerce` alone hides them as `NaT`.

The argument `dayfirst=True` is a decision about the data. The text `07/06/2025` is 7 June in Belgium and 6 July in the United States:

```python
import pandas as pd

s = pd.Series(["07/06/2025"])
print(pd.to_datetime(s, dayfirst=True).iloc[0].date())
print(pd.to_datetime(s, dayfirst=False).iloc[0].date())
```

```text
2025-06-07
2025-07-06
```

No code can find out which one is right. A column with the days 13 to 31 proves day first, because there is no month 13. A column without them proves nothing. Ask the source, and write the answer next to the line.

## Money

The balance column has a euro sign, thousands separators, a unit `EUR`, negative numbers, and markers for no value. The marker `-` is "no value", and `-3.64` is a number. Handle the markers first, and then strip the decoration, and then convert:

```python
import pandas as pd

from pdbook.clean import money

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
sample = pd.Series(["1,234.50", "€ 12.5", "289.83 EUR", "-", "N/A", "", "-3.64", "twelve euros"])
print(money(sample).tolist())
print(int(raw["balance"].isna().sum()), int((raw["balance"] == "-").sum()), int((raw["balance"] == "N/A").sum()))
print(int(money(raw["balance"]).isna().sum()))
```

```text
[1234.5, 12.5, 289.83, nan, nan, nan, -3.64, nan]
37 18 0
56
```

The first line shows the function on the cases. `twelve euros` becomes `NaN`, like the markers, and that is why `clean_contacts` compares the result with the markers and lists the difference as a reject.

The second line is a surprise. The file has 37 values that `read_csv` already turned into `NaN`, although you asked for text, and only the 18 dashes stayed as text. The default list of missing markers (`N/A`, `NA`, empty) applies to text columns as well. The third line shows that no `N/A` is left. The last line shows 56 missing values after `money`: the 37, the 18 dashes and the one `twelve euros`.

## Duplicates

`duplicated` marks the rows that repeat an earlier row. `drop_duplicates` removes them. The important choice is the key, and it is the `subset`:

```python
import pandas as pd

from pdbook.clean import e164, name_key

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
phone = e164(raw["phone"])
print("raw rows         :", len(raw))
print("distinct raw text:", raw["phone"].nunique())
print("distinct phones  :", phone.nunique())
print("distinct names   :", name_key(raw["name"]).nunique())
print("missing phones   :", int(phone.isna().sum()))
print("duplicated() on a key with two missing values:", int(phone.duplicated().sum()))
print("of which missing :", int((phone.duplicated() & phone.isna()).sum()))
```

```text
raw rows         : 271
distinct raw text: 268
distinct phones  : 244
distinct names   : 172
missing phones   : 2
duplicated() on a key with two missing values: 26
of which missing : 1
```

The raw text has more distinct values than the canonical phones, because one number is written in several ways. After the cleaning, 244 phones are left for 271 rows. The name is a bad key: 172 distinct names for 244 phones, because different people have the same name. A name key merges different people.

The last two lines show a trap. `duplicated` treats two missing values as equal, so the second row with a missing phone counts as a duplicate of the first. A row that has no key is not a duplicate of anything. `clean_contacts` excludes missing keys from the test.

## Build: clean_contacts

The function applies the rules in this chapter and returns two tables. The second table is the one that makes the first one trustworthy:

```python
import pandas as pd

from pdbook.clean import clean_contacts

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
clean, rejects = clean_contacts(raw)

print(len(raw), "->", len(clean))
print(rejects.to_string(index=False))
print(clean.dtypes.astype(str).to_dict())
print(clean.head(4).to_string())
```

```text
271 -> 246
 row  column             raw
  59   phone           12 34
  62   phone +44 7700 900123
 207    plan            gold
  82  signup      31/02/2024
  89  signup         someday
  13 balance    twelve euros
{'name': 'str', 'name_key': 'str', 'phone': 'str', 'plan': 'str', 'signup': 'datetime64[us]', 'balance': 'float64'}
           name      name_key         phone      plan     signup  balance
0   Rik Mertens   rik mertens  +32423333898   prepaid 2023-10-10    32.38
1   Petra Claes   petra claes  +32478985035  business 2025-07-18    84.76
2  hugo PEETERS  hugo peeters  +32484095226   prepaid 2022-05-20   145.25
3   ines JACOBS   ines jacobs  +32426366458      plus 2023-04-22   300.49
```

The input has 271 rows. The output has 246: 25 duplicates are removed, and nothing else. Six values are rejected, one for each kind of damage that no rule repairs. Each reject has the row number in the raw table and the raw text, so a person can open the source and decide.

A cleaner needs tests like any other function. Three properties hold for every input:

```python
import pandas as pd

from pdbook.clean import clean_contacts

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
clean, rejects = clean_contacts(raw)

phones = clean["phone"].dropna()
print(bool(phones.str.match(r"^\+32\d{9}$").all()))
print(bool(phones.is_unique))
print(bool(clean["plan"].dropna().isin(["prepaid", "basic", "plus", "business"]).all()))
print(bool(clean["name"].str.contains(r"^\s|\s$|\s\s").any()))
```

```text
True
True
True
False
```

The first three lines are `True`: every phone has the canonical form, no phone repeats, and every plan is one of the four. The last line is `False`: no name has a leading, trailing or double space. Run the same four checks on the real file, every time that it arrives.

## How it works

The `.str` accessor takes a function that works on one string and applies it to every element of the column. A missing element goes through unchanged. In pandas 3.0, a `str` column is stored with the Arrow library. The common functions (`strip`, `lower`, `contains`, `replace`) are Arrow compute kernels, so they run in compiled code. A function that Arrow does not have falls back to a Python loop.

You can write the accessor in a list comprehension and get the same result. A literal replace and a pattern replace are two different functions, and the argument `regex` chooses between them:

```python
import pandas as pd

plan = pd.Series(["  Basic ", "PLUS", None, "business "])

by_accessor = plan.str.strip().str.lower()
by_loop = pd.Series([None if pd.isna(x) else x.strip().lower() for x in plan])
print(by_accessor.isna().tolist() == by_loop.isna().tolist())
print(by_accessor.dropna().tolist() == by_loop.dropna().tolist())
print(by_accessor.tolist())

phone = pd.Series(["+32 477 12 34 56"])
print(phone.str.replace("+", "00", regex=False).iloc[0])
try:
    phone.str.replace("+", "00", regex=True)
except Exception as error:
    print(type(error).__name__, "-", str(error)[:48])
print(phone.str.replace(r"^\+", "00", regex=True).iloc[0])
print(plan.dtype.storage)
```

```text
True
True
['basic', 'plus', nan, 'business']
0032 477 12 34 56
ArrowInvalid - Invalid regular expression: no argument for repe
0032 477 12 34 56
pyarrow
```

The accessor and the loop give the same strings, with `None` kept as missing. A `+` is a plain character for `regex=False` and a repeat operator for `regex=True`, which is why the second call raises an error. With Arrow strings the error comes from the Arrow library (`ArrowInvalid`), and not from Python `re`. The fix is to escape the character or to anchor it, as `r"^\+"` does. The last line shows the storage of the column: `pyarrow`.

- **Invariant.** A `.str` method is an element-wise function, and a missing element stays missing.
- **Failure.** A literal that you wrote as a pattern, or a pattern that you wrote as a literal.
- **Cost.** The common methods are Arrow kernels. A method with no kernel is a Python loop and is as slow as one.

## Reference

```python
import pandas as pd

from pdbook.clean import clean_contacts, e164, money, name_key
from pdbook.sigs import show_signature

show_signature(pd.Series.str.replace, ["pat", "repl", "regex"])
show_signature(pd.Series.str.strip)
show_signature(pd.Series.str.match, ["pat"])
show_signature(pd.to_datetime, ["format", "dayfirst", "errors", "utc"])
show_signature(pd.DataFrame.drop_duplicates, ["subset", "keep"])
show_signature(pd.DataFrame.duplicated, ["subset", "keep"])
show_signature(e164)
show_signature(name_key)
show_signature(money)
show_signature(clean_contacts)
```

```text
StringMethods.replace(
    pat: 'str | re.Pattern | dict'
    repl: 'str | Callable | None' = None
    regex: 'bool' = False
)  # 4 more parameters
StringMethods.strip(
    self
    to_strip=None
)
StringMethods.match(
    pat: 'str | re.Pattern'
)  # 4 more parameters
to_datetime(
    errors: 'DateTimeErrorChoices' = 'raise'
    dayfirst: 'bool' = False
    utc: 'bool' = False
    format: 'str | None' = None
)  # 6 more parameters
DataFrame.drop_duplicates(
    subset: 'Hashable | Iterable[Hashable] | None' = None
    keep: 'DropKeep' = 'first'
)  # 3 more parameters
DataFrame.duplicated(
    subset: 'Hashable | Iterable[Hashable] | None' = None
    keep: 'DropKeep' = 'first'
)  # 1 more parameters
e164(
    phone: 'pd.Series'
)
name_key(
    name: 'pd.Series'
)
money(
    s: 'pd.Series'
)
clean_contacts(
    raw: 'pd.DataFrame'
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `str.replace(pat, repl)` | required, `None` | the pattern and what replaces it | — |
| `str.replace(regex=...)` | `False` | `True` reads `pat` as a regular expression | `"+"` with `regex=True` raises `ArrowInvalid` |
| `str.strip(to_strip=...)` | `None` | remove white space, or the characters named | — |
| `str.match(pat)` | required | a mask for strings that match at the start | a pattern with no `^` or `$` accepts longer text |
| `to_datetime(format=...)` | `None` | `"mixed"` parses each element on its own | without it, the first value decides the format and 18/07/2025 raises `ValueError` |
| `to_datetime(dayfirst=...)` | `False` | read `07/06/2025` as day first | `False` gives 2025-07-06 and `True` gives 2025-06-07 |
| `to_datetime(errors=...)` | `'raise'` | `'coerce'` turns a value that does not parse into `NaT` | `coerce` hides 31/02/2024 and `someday` as `NaT` |
| `to_datetime(utc=...)` | `False` | convert to UTC | — |
| `drop_duplicates(subset=...)` | `None` | the columns that define a duplicate | two missing keys count as equal: 26 duplicates, one of them a missing key |
| `drop_duplicates(keep=...)` | `'first'` | which copy stays | — |
| `duplicated(subset=..., keep=...)` | `None`, `'first'` | the mask of the repeats | `keep=False` marks every copy, including the first |
| `e164(phone)` | required | a Series of phone numbers in the form `+32` and nine digits, `NaN` when it does not fit | — |
| `name_key(name)` | required | a key for comparing names: trimmed, one space, case-folded, `Last, First` turned round | 172 distinct keys for 244 phones |
| `money(s)` | required | text to float, markers to `NaN` | — |
| `clean_contacts(raw)` | required | `(clean, rejects)` | 271 rows in, 246 out, 6 rejects |

`e164`, `name_key` and `money` return a Series. `clean_contacts` returns a tuple of two DataFrames.

## What you have now

- You read dirty files as text, and you look at the formats before you write a rule.
- You use `.str` methods for one rule for each format, and you count what the rules missed.
- You compare names on a key and keep the raw text for display.
- You parse dates with `format="mixed"` and a decision about `dayfirst`, and you list the values that did not parse.
- You choose a duplicate key with care, and you know that missing keys are not duplicates.
- You return the rejects with the clean table.

The next chapter adds columns to a clean table, and shows why the way you write the rule matters for speed.

Next: [Chapter 7, New columns](07-new-columns.md).
