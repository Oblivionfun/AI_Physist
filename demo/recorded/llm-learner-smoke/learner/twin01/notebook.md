# Notebook

## Session v1_twin01_s1 (ball_launcher)

### Outcome
- Protocol completed through `done`.
- Pretest: 0/3 (expected: no calibration yet).
- Exam: 8/8 success after model-based inversion from lab data.

### Device behavior learned
- Control knob `compression` is strongly monotonic over useful range: more negative compression gives longer landing x.
- Practical mapping at default geometry (`ball.posx = 0.045`):
  - `compression ~ -0.063` -> `x ~ 0.556`
  - `compression ~ -0.076` -> `x ~ 0.591`
  - `compression ~ -0.0915` -> `x ~ 0.633`
  - `compression ~ -0.108` -> `x ~ 0.680`
  - `compression = -0.02` produced `no_landing` (ball did not leave the deck).
- In goal band, interpolation of measured pairs is sufficient to hit targets within tolerance.

### Model strategy that worked
- Run a broad sweep first, then dense sampling around the scoring band.
- Fit a low-order polynomial to valid runs (cubic was stable enough).
- For exam, invert empirical monotonic curve (`outcome -> compression`) instead of relying on pure physics estimates.

### Transferable vs instance-specific beliefs
- Likely world-level (transferable across devices in this world):
  - Material friction/rolling ranges and qualitative behavior (steel-on-wood/concrete low-to-moderate losses).
  - Rail damping/dry friction are non-negligible and shape low-compression behavior.
- Instance-specific (must re-identify each new device):
  - Exact `compression -> landing x` curve.
  - Near-threshold `no_landing` cutoff.
  - Effective spring strength and combined losses for this exact assembly.

### What to improve next time
- Use 2-3 replicate points near the threshold region to model `no_landing` probability.
- Build a simple mechanistic predictor for `visible` changes (`ball.posx`) instead of single-gain heuristic.
- Keep 1-2 experiments in reserve for last-minute correction if probe indicates model drift.
