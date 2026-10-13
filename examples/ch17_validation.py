"""Chapter 17: validate the call records, then break them in known ways and check the validator."""
from pdbook.io import load_calls, load_cells, load_subscribers
from pdbook.validate import call_rules, check_schema, plant_faults, validate

calls, subs, cells = load_calls(), load_subscribers(), load_cells()
rules = call_rules(subs, cells)

print("schema problems:", check_schema(calls) or "none")
clean = validate(calls, rules)
print(clean[["rule", "severity", "violations"]].to_string(index=False))

broken, expected = plant_faults(calls)
found = dict(zip(*[validate(broken, rules)[c] for c in ("rule", "violations")]))
print()
for rule, n in expected.items():
    mark = "ok  " if found[rule] == n else "MISS"
    print(f"{mark} planted {n:>2d}, found {found[rule]:>2d}  {rule}")
assert all(found[r] == n for r, n in expected.items())
