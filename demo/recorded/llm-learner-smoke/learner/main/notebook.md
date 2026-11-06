# Notebook

## Session v1_main_s1 — ball_launcher

### Outcome
- Finished full protocol to `done`.
- Pretest: 0/3 (before calibration).
- Exam: 8/8.
- Experiments used: 16/40.

### Device behavior learned
- Main control is monotonic: more negative `compression` gives farther landing x.
- At very low compression (`~ -0.02`), the ball may never leave the deck (`no_landing`).
- In the useful range, landing x is well-approximated by a quadratic in compression:
  - `x ≈ 0.3626 - 3.2015*c - 2.4199*c^2` (c is compression in metres)
  - Linear fit is also decent: `x ≈ 0.3792 - 2.7771*c`.
- Launch/landing noise appears small (outcome noise ~0.003 on card, seen residuals around a few mm to ~1 cm).

### What worked
- Quick boundary sweep first (`-0.02` to `-0.14`) established monotonicity and failure zone.
- Mid-range calibration around scoring band (`0.55` to `0.68`) improved inverse targeting.
- Using interpolation/inversion for exam goals was enough for perfect exam score.

### What to do differently next time
- Pretest should use a safer prior map; I overshot all three pretest goals.
- Spend 1-2 more experiments near the exact pretest target region if protocol allows in future variants.
- If visible dimensions are modified in evaluation, add a stronger physics-based impact model and (if possible) targeted experiments that emulate contact timing changes.

### Transferable vs instance-specific unknowns
- World/material-level (likely transferable across device instances in same world):
  - `friction.concrete`, `friction.steel`, `friction.wood`
  - `rolling.concrete`, `rolling.steel`
- Device-instance-level (must re-identify each device):
  - `stiffness.coil_stiff`
  - `damping.rail`
  - `frictionloss.rail`
- Practical implication: for new instances, re-calibrate control-to-outcome map even if material priors are reused.
