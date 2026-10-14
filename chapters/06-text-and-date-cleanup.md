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

#### `pd.Series.str.strip`

```text
pd.Series.str.strip(
    self,
    to_strip=None,
)
```

The method removes characters from both ends of each string. `lstrip` and `rstrip` remove them from one end.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `to_strip` | `None` | the characters to remove, as one string that is read as a set. With `None`, white space | the argument is a set, not a word: `strip("ab")` on `abcba` gives `c`. `strip("x€ ")` on `€ 12` gives `12` |

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

#### `pdbook.clean.name_key`

```text
pdbook.clean.name_key(
    name,
)
```

The function returns a Series of keys for comparison, not for display.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `name` | required | the names as text | 172 distinct keys for 244 phones: two people with the same name get one key |

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

#### `pd.Series.str.replace`

```text
pd.Series.str.replace(
    self,
    pat,
    repl=None,
    n=-1,
    case=None,
    flags=0,
    regex=False,
)
```

The method replaces each occurrence of `pat` in each string.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `pat` | required | the text or the pattern to find. A dict of old to new replaces several texts at one time | with `regex=True`, `.` is any character: `replace(".", "-", regex=True)` on `a.b.c` gives `-----` |
| `repl` | `None` | the new text, or a function that receives the match and returns text. `None` is allowed only with a dict for `pat` | without `repl` and without a dict, it raises `TypeError`. A function needs `regex=True`, or it raises `ValueError` |
| `n` | `-1` | the largest number of replacements in each string. `-1` replaces all | `n=1` on `a.b.c` gives `a-b.c` |
| `case` | `None` | `False` ignores upper and lower case. `None` means case-sensitive | — |
| `flags` | `0` | flags of the `re` module, such as `re.IGNORECASE` | — |
| `regex` | `False` | `True` reads `pat` as a regular expression | `"+"` with `regex=True` raises `ArrowInvalid`, because `+` means "repeat" |

The last line is the check. After the four steps, 269 numbers have 9 digits, and two do not. Those two are the cases that the rules cannot repair: `12 34` is too short, and the UK number `+44 7700 900123` is a valid number of another country. The function `e164` in `pdbook/clean.py` returns `NaN` for them, and `clean_contacts` lists them in the rejects.

#### `pdbook.clean.e164`

```text
pdbook.clean.e164(
    phone,
)
```

The function returns each Belgian number as `+32` and nine digits. A number that does not fit becomes `NaN`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `phone` | required | the phone numbers as text, in any of the five formats | a column of integers raises `AttributeError`: read the column with `dtype=str` ([Chapter 2](02-input-and-output.md)) |

## Dates: mixed formats

`to_datetime` looks at the first value to choose a format. A column with four formats fails on the first value that does not fit:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
try:
    pd.to_datetime(raw["signup"])
except ValueError as error:
    print("ValueError:", str(error).splitlines()[0][:60])
```

```text
ValueError: time data "18/07/2025" doesn't match format "%Y-%m-%d". You
```

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

#### `pd.to_datetime`

```text
pd.to_datetime(
    arg,
    errors='raise',
    dayfirst=False,
    yearfirst=False,
    utc=False,
    format=None,
    exact=<no_default>,
    unit=None,
    origin='unix',
    cache=True,
)
```

The function converts text, numbers or a table of year, month and day columns to timestamps.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `arg` | required | a value, a list, a Series, or a DataFrame with the columns `year`, `month` and `day` | — |
| `errors` | `'raise'` | `'raise'` stops at the first value that does not parse. `'coerce'` makes it `NaT` | `'coerce'` hides `31/02/2024` and `someday` as `NaT`. `errors="ignore"` raises an error in pandas 3.0 |
| `dayfirst` | `False` | read `07/06/2025` as day first | `False` gives 2025-07-06 and `True` gives 2025-06-07. `True` also swaps an ISO date: `2025-01-02` becomes 1 February |
| `yearfirst` | `False` | read `10/11/12` as year first: 2010-11-12 | — |
| `utc` | `False` | return timestamps in UTC. Text with a zone is converted, text without a zone is taken as UTC | text with two different offsets, such as `+01:00` and `+02:00`, raises `ValueError` without `utc=True` |
| `format` | `None` | the exact format, such as `"%d/%m/%Y"`, or `"ISO8601"`, or `"mixed"` for a format for each value. With `None`, the first value decides the format | without it, a column with four formats raises `ValueError` at the first value of another format |
| `exact` | `<no_default>` | with `False`, the `format` can match a part of the text. Not set means `True` | `"on 2025-01-02 ok"` with `format="%Y-%m-%d"` raises `ValueError`. With `exact=False` it gives 2025-01-02 |
| `unit` | `None` | the unit of numbers: `'s'`, `'ms'`, `'us'` or `'ns'`, counted from `origin` | without it, an integer is read as nanoseconds: 1788214410 gives 1970-01-01 00:00:01.788. With `unit="s"` it is 2026-08-31 22:13:30 |
| `origin` | `'unix'` | the start of the count for numbers. `'unix'` is 1970-01-01 | — |
| `cache` | `True` | convert each distinct value once | — |

The obvious repair is `format="mixed"`, which parses each element on its own, with `dayfirst=True` for the Belgian dates. It is wrong. `dayfirst` is not limited to the dates with slashes: the mixed parser also applies it to an ISO date, where the year comes first and the order is fixed. The file holds the same signup date in four formats, so you can compare the mixed parser with one exact format for each pattern:

```python
import pandas as pd

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
signup = raw["signup"].str.strip()
iso = signup[signup.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)]

mixed = pd.to_datetime(iso, format="mixed", dayfirst=True)
exact = pd.to_datetime(iso, format="%Y-%m-%d")
wrong = mixed != exact
print(len(iso), "ISO dates,", int(wrong.sum()), "with day and month swapped")
print(pd.DataFrame({"raw": iso[wrong], "mixed": mixed[wrong].dt.date}).head(3).to_string())
```

```text
78 ISO dates, 30 with day and month swapped
           raw       mixed
4   2024-11-04  2024-04-11
13  2024-05-04  2024-04-05
18  2022-05-11  2022-11-05
```

The mixed parser reads `2024-11-04` as 11 April. It changes every ISO date whose day is 12 or lower, and it gives no warning: the result is a valid date. The repair is the method of this chapter. Write one rule for each format that you found, and count what no rule caught. The function `dates` in [`pdbook/clean.py`](../pdbook/clean.py) tries the four exact formats in turn:

```python
import pandas as pd

from pdbook.clean import DATE_FORMATS, dates

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
parsed = dates(raw["signup"])
print(DATE_FORMATS)
print(int(parsed.isna().sum()), "not parsed:", raw.loc[parsed.isna(), "signup"].tolist())
print(parsed.loc[[4, 13]].dt.date.tolist(), raw.loc[[4, 13], "signup"].tolist())
```

```text
('%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y', '%d-%b-%y')
2 not parsed: ['31/02/2024', 'someday']
[datetime.date(2024, 11, 4), datetime.date(2024, 5, 4)] ['2024-11-04', '2024-05-04']
```

`31/02/2024` is not a date and `someday` is not a date. The cleaner must reject both, and `errors="coerce"` alone hides them as `NaT`. The ISO dates keep their order: `2024-11-04` is 4 November.

#### `pdbook.clean.dates`

```text
pdbook.clean.dates(
    s,
)
```

The function returns a `datetime64[us]` Series. A value that fits none of `DATE_FORMATS` becomes `NaT`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `s` | required | the text of the dates | a fifth format in a new export becomes `NaT`. The rejects table of `clean_contacts` lists each one, so the count shows it |

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

#### `pdbook.clean.money`

```text
pdbook.clean.money(
    s,
)
```

The function returns the amounts as `float64`. A marker for no value and text that is not an amount become `NaN`.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `s` | required | the amounts as text, with `€`, `EUR`, thousands separators or a sign | a decimal comma is read as a thousands separator: `12,5` gives 125 and `1.234,50` gives 1.2345, with no error. The rule fits this export, which uses a decimal point |

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

#### `pd.DataFrame.duplicated`

```text
pd.DataFrame.duplicated(
    self,
    subset=None,
    keep='first',
)
```

The method returns a boolean Series: `True` for each row that repeats an earlier row. The Series method has the parameter `keep` only.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `subset` | `None` | the columns that define a repeat. With `None`, all columns | two missing keys count as equal: 26 duplicates, one of them a missing key |
| `keep` | `'first'` | `'first'` marks every copy after the first. `'last'` marks every copy before the last. `False` marks every copy | `keep=False` marks the first copy too |

#### `pd.DataFrame.drop_duplicates`

```text
pd.DataFrame.drop_duplicates(
    self,
    subset=None,
    *,
    keep='first',
    inplace=False,
    ignore_index=False,
)
```

The method returns the table without the rows that `duplicated` marks.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `subset` | `None` | the columns that define a duplicate. One name or a list | a name that is not a column raises `KeyError` |
| `keep` | `'first'` | which copy stays: `'first'`, `'last'`, or `False` for none | `keep=False` removes every row that has a copy, the first one included |
| `inplace` | `False` | with `True`, change the table and return `None` | — |
| `ignore_index` | `False` | with `True`, the result gets the labels 0, 1, 2 and so on | with `False`, the labels have holes where rows were removed |

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

#### `pdbook.clean.clean_contacts`

```text
pdbook.clean.clean_contacts(
    raw,
)
```

The function returns two tables: the clean contacts, and one row for each value that no rule could repair.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `raw` | required | the export, read with `dtype=str` so that no column is guessed | 271 rows in, 246 out, 6 rejects |

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

#### `pd.Series.str.match`

```text
pd.Series.str.match(
    self,
    pat,
    case=<no_default>,
    flags=<no_default>,
    na=<no_default>,
)
```

The method returns a boolean Series: `True` where the start of the string matches the pattern.

| parameter | default | what it does | what goes wrong |
|---|---|---|---|
| `pat` | required | a regular expression | the match is at the start only: `\+32\d{9}` accepts `+3247712345678`, which has 13 digits. End the pattern with `$`, or use `str.fullmatch` |
| `case` | `<no_default>` | `False` ignores upper and lower case. Not set means case-sensitive | — |
| `flags` | `<no_default>` | flags of the `re` module | — |
| `na` | `<no_default>` | the result for a missing value. Not set means `False` for the `str` dtype | on the `object` dtype, a missing value gives `NaN`, and the result cannot be a mask ([Chapter 3](03-selection.md)) |

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

The next block measures the cost line. It times three ways to change the case of one million short strings. `lower` has an Arrow kernel. `casefold` has none in this version, so pandas runs it element by element in Python. The third way is a list comprehension:

```python
import timeit

import numpy as np
import pandas as pd

words = np.array(["Basic", "PLUS", "business", "Prepaid ", "  Gold"])
s = pd.Series(np.random.default_rng(0).choice(words, 1_000_000))


def best(f):
    return min(timeit.repeat(f, number=1, repeat=3))


t_lower = best(lambda: s.str.lower())
t_casefold = best(lambda: s.str.casefold())
t_loop = best(lambda: [x.lower() for x in s])
assert t_casefold / t_lower > 4
assert t_loop / t_lower > 4
print(f"str.lower (Arrow kernel) {t_lower * 1e3:7.0f} ms")
print(f"str.casefold (no kernel) {t_casefold * 1e3:7.0f} ms")
print(f"list comprehension       {t_loop * 1e3:7.0f} ms")
```

```text
# output varies
str.lower (Arrow kernel)      19 ms
str.casefold (no kernel)     233 ms
list comprehension           903 ms
```

The kernel is the fast case by more than four times, which is what the assertions check. `casefold` is the right method for a key, and it is also the slow one. For a column of one million rows the difference is a fraction of a second, and correctness wins. For a column of a hundred million rows, compute the key once and keep it.

## Reference

| Callable | Introduced in | Contract |
|---|---|---|
| `pd.Series.str.strip` | The .str accessor | the characters of a set removed from both ends |
| `pdbook.clean.name_key` | Names: compare on a key, not on a pretty form | a key for comparison: trimmed, one space, case-folded, `Last, First` turned round |
| `pd.Series.str.replace` | Phones: one canonical form | each occurrence of a text or a pattern replaced |
| `pdbook.clean.e164` | Phones: one canonical form | Belgian numbers as `+32` and nine digits, `NaN` when they do not fit |
| `pd.to_datetime` | Dates: mixed formats | text or numbers to timestamps; the first value decides the format unless you give one |
| `pdbook.clean.dates` | Dates: mixed formats | the four date formats of the export, each with its exact format |
| `pdbook.clean.money` | Money | amounts as floats, markers to `NaN` |
| `pd.DataFrame.duplicated` | Duplicates | a mask of the rows that repeat an earlier row |
| `pd.DataFrame.drop_duplicates` | Duplicates | the table without the repeats |
| `pdbook.clean.clean_contacts` | Build: clean_contacts | `(clean, rejects)` |
| `pd.Series.str.match` | Build: clean_contacts | a mask: the start of the string matches a pattern |

## What you have now

- You read dirty files as text, and you look at the formats before you write a rule.
- You use `.str` methods for one rule for each format, and you count what the rules missed.
- You compare names on a key and keep the raw text for display.
- You parse each date format with its exact format, and you list the values that did not parse. First, you decide the order of day and month. You know that `format="mixed"` with `dayfirst=True` also swaps day and month in ISO dates.
- You choose a duplicate key with care, and you know that missing keys are not duplicates.
- You return the rejects with the clean table.

The next chapter adds columns to a clean table, and shows why the way you write the rule matters for speed.

Next: [Chapter 7, New columns](07-new-columns.md).
