import json
from collections import defaultdict
from pathlib import Path
import numpy as np

PATH = Path("data/training/metadata/step1_oracle_tensor_results.json")

data = json.loads(PATH.read_text(encoding="utf-8"))["records"]

grouped = defaultdict(list)

for r in data:
    family = r["family"]
    tier = float(r["tier"])

    mono = np.asarray(r["mono_shift"], dtype=float)
    serial = np.asarray(r["serial_shift"], dtype=float)

    for bit in range(23):
        grouped[(family, tier, "mono", bit)].append(abs(mono[bit]))
        grouped[(family, tier, "serial", bit)].append(abs(serial[bit]))

print("=== STEP 1B: ORACLE SUMMARY ===")
print("unit = modified tensor/layer")
print()

for family in ("S1", "S2", "S3"):
    for tier in (0.005, 0.01, 0.02, 0.05):

        print(f"\n--- {family} tier={tier:.1%} ---")

        rows = []

        for stat in ("mono", "serial"):
            for bit in range(23):
                vals = np.asarray(grouped[(family, tier, stat, bit)], dtype=float)

                if vals.size == 0:
                    continue

                median = float(np.median(vals))
                frac3 = float(np.mean(vals > 3.0))

                rows.append((median, frac3, stat, bit, vals.size))

        rows.sort(reverse=True)

        print("top 8 bit/stat cells by median |paired shift|:")
        print("stat    bit   n_tensors   median_shift_sigma   frac_|shift|>3")

        for median, frac3, stat, bit, n in rows[:8]:
            print(
                f"{stat:<7} {bit:>3}   {n:>9}   "
                f"{median:>18.6f}   {frac3:>15.3%}"
            )

        # best cell for this family/tier
        if rows:
            median, frac3, stat, bit, n = rows[0]

            if median < 0.5 and frac3 < 0.10:
                decision = "LIKELY_INFORMATION_CEILING"
            elif median >= 1.0 or frac3 >= 0.25:
                decision = "MEASURABLE_SIGNAL"
            else:
                decision = "WEAK_OR_MIXED_SIGNAL"

            print(
                f"best_cell={stat}/bit{bit:02d} "
                f"median_sigma={median:.6f} "
                f"frac_gt_3sigma={frac3:.3%} "
                f"decision={decision}"
            )

print("\n=== STEP 1B COMPLETE ===")
