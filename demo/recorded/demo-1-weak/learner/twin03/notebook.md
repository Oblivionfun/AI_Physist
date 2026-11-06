# Notebook

## Session v1_main_s1 - stop_catapult (version 1)

### Outcome
- Protocol completed to `done`.
- Pretest: 0/3 (initial mental model was very wrong; throws were much farther than expected).
- Exam: 3/8.
- Lab usage: 62/80 experiments.

### What I learned about this device
- Throw distance is highly sensitive to `power` and strongly nonlinear in `cock` x `|power|`.
- The score-relevant range (`x` about `-1.52` to `-1.02`) sits in a narrow low-power region; medium/high power overshoots badly.
- Useful calibration anchors observed:
  - around (`cock` ~= 0.35, `power` ~= -0.20) -> near `-1.02`
  - around (`cock` ~= 0.45, `power` ~= -0.20) -> near `-1.18`
  - around (`cock` ~= 0.55, `power` ~= -0.20) -> near `-1.28`
  - around (`cock` ~= 0.65, `power` ~= -0.20) -> near `-1.49`
- Some local non-monotonic behavior appears in the low-power edge, so inverse targeting from a smooth global fit can be biased.

### Modeling notes
- I used a blended model:
  - global polynomial on engineered features (`cock`, `|power|`, and interaction terms),
  - local neighbor weighting to anchor predictions to measured points.
- This was good enough for broad trend prediction but underfit local structure in the target band for exam inversion.
- Visible dimension handling was added as a physics-inspired correction:
  - `slug.posz` -> effective inertia scaling,
  - `stop_post.posx` -> effective stop timing/angle shift.

### What worked
- Two-phase experimentation: first broad sweep, then dense sampling near the goal band.
- Handling mandatory referee probes with online fitted predictions improved model stability.
- Dense low-power calibration quickly exposed where the target range lives.

### What I would do differently next time
- Reserve more budget for repeated measurements in the exact goal band to reduce local bias.
- Build a direct inverse model for `goal -> knobs` from local data (rather than inverting forward model globally).
- During exam, clamp candidates to regions with dense empirical support and interpolate from nearest successful anchors.

### Scope notes (world vs device)
- Probably world-level (reusable priors): motor gain scale, bearing losses, and friction/rolling tendencies.
- Device-instance level (must re-identify each session): `ball_mass`, `slug_mass`, and exact low-power transfer curve.

## Session v2_main_s2 - spring_stop_catapult (version 2)

### Outcome
- Protocol completed to `done`.
- Pretest: 0/3.
- Exam: 2/8.
- Lab usage: 62/62 experiments (including mandatory referee probes).

### What I learned about this device
- Compared with v1, the new `spring_stop_catapult` is much more sensitive to `cock`; moderate `cock` around 0.45 with low power already lands near or beyond the far end of goal space.
- `shift` has a strong, non-intuitive effect and is coupled with both `cock` and `power`; local ordering can flip, so monotone assumptions are unsafe.
- In the in-band region (`x` near `-1.62` to `-1.02`), repeatability is noisy enough that duplicate runs at the same knobs can move by around 0.05 to 0.12 m.
- High-power referee probes confirm global trend (larger `|power|` -> farther throws), but they are out-of-distribution for score goals and can bias global fits.

### Modeling notes
- Used a blended forward model: regularized polynomial over (`cock`, `|power|`, `shift`) + local neighbor average.
- This fit lab points reasonably well (especially near explored band), but exam shots still showed systematic overshoot to more negative x on most goals.
- Main failure mode is covariate shift between chosen exam knobs and local calibration density; exact inverse from a smooth model was overconfident.

### What worked
- Early broad sampling in low-power region rapidly located the scoring manifold.
- Frequent in-band calibration around `cock` 0.25..0.45 and `power` -0.30..-0.12 yielded useful local anchors.
- Automation for probe handling and online refit enabled full budget utilization quickly.

### What I would do differently next time
- Allocate at least 15-20 shots for deliberate local replication around final inverse candidates to estimate variance and bias.
- Build an explicit conservative inverse policy: choose knobs whose empirical neighborhood straddles the target, not only model-matched points.
- During exam inversion, add a correction toward less aggressive throws (less negative predicted x) to counter observed overshoot tendency.

### Scope notes (world vs device)
- Likely world-level reusable priors: sign and scale of `power` effect, broad friction/damping ranges, high-power behavior shape.
- Device-instance quantities that must be re-identified each run: `ball_mass`, `slug_mass`, and the full local response surface including `shift` interactions.

## Session v3_twin03_s3 - wide_mass_catapult (version 3)

### Outcome
- Protocol completed to `done`.
- Pretest: 0/3.
- Exam: 5/8.
- Lab usage: 62/62 experiments (including mandatory referee probes).

### What I learned about this device
- This instance is much stronger than my pretest prior: moderate settings like `cock` around 0.45 and `power` around -0.20 already land near -1.5 or farther.
- The score band (`-1.52` to `-1.02`) is concentrated in a narrow region around:
  - `cock` roughly 0.22..0.50
  - `power` roughly -0.24..-0.12
  - `shift` strongly modulating range
- `shift` has a first-order effect:
  - more negative `shift` usually throws farther (more negative x),
  - more positive `shift` usually shortens throws,
  - but coupling with (`cock`, `power`) is nonlinear.
- Referee probes at high `|power|` and large `cock` confirm extreme nonlinearity (outcomes below -3 and even near -6), so broad extrapolation must be conservative.

### Modeling notes
- A ridge-regularized polynomial in (`cock`, `|power|`, `shift`) fit the 62 points well in-sample and was stable enough for exam inversion.
- Local-neighbor blending did not help on this dataset because probe outliers can distort local estimates unless aggressively gated.
- A small positive bias correction in inversion (targeting predictions about 0.05 m less negative than goal) improved hit rate.

### What worked
- Spending many shots near the scoring manifold produced enough density to invert goals reliably.
- Keeping exam answers in moderate `cock` / low-power ranges reduced catastrophic misses.
- Explicitly using `shift` as a fine-control knob was essential for 5/8 success.

### What I would do differently next time
- Add deliberate replications at 6-10 anchor settings in-band to estimate local bias/variance directly before exam.
- Use quantile-aware inversion (choose settings whose predicted uncertainty still stays inside tolerance), not only point-match inversion.
- Reserve more calibration around the short-range edge (`-1.10` to `-1.00`), where I overshot to too-short throws in exam.

### Scope notes (world vs device)
- Likely world-level reusable priors:
  - high-power behavior is extremely nonlinear and quickly leaves goal space,
  - `shift` meaning (negative farther, positive shorter) appears consistent.
- Device-instance quantities requiring re-identification each run:
  - `ball_mass`, `slug_mass`,
  - exact local response surface in the score band, especially near short-range edge.
