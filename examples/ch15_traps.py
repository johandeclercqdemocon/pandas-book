"""Chapter 15: ten traps, each shown as the naive result and the intended result."""
from pdbook.traps import TRAPS, live

print(f"{'#':>2s} {'ch':>3s}  {'naive':<14s} {'intended':<14s} trap")
for i, t in enumerate(TRAPS, 1):
    print(f"{i:>2d} {t.chapter:>3d}  {t.naive()!s:<14.14s} {t.correct()!s:<14.14s} {t.name}")
dead = [t.name for t in TRAPS if not live(t)]
assert not dead, f"these traps no longer exist in this version of pandas: {dead}"
print("\nall", len(TRAPS), "traps are live in this version of pandas")
