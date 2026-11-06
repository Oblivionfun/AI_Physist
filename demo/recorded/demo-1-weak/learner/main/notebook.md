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

## Session v3_main_s3 - wide_mass_catapult (version 3)

### Outcome
- Protocol completed to `done`.
- Pretest: 0/3.
- Exam: 2/8.
- Lab usage: 62/62 experiments.

### What I learned about this device
- The new `wide_mass_catapult` is much stronger than v1/v2 in the goal region: many low-power settings still overshoot to much more negative x than the target range.
- `shift` remains a first-order control in the scoring band and can move land position by around 0.2 to 0.3 m at fixed `cock` and `power`.
- High `cock` and/or high `|power|` quickly pushes outcomes far negative (often <-4), so exam-relevant control lives in a narrow slice near `cock` 0.16..0.46 and `power` -0.20..-0.12.
- Local behavior in that slice is curved and sensitive enough that one-shot inversion from a smooth model still incurs significant bias.

### Modeling notes
- Used an online blended model during lab:
  - regularized polynomial forward model in (`cock`, `power`, `shift`) with cubic and interaction terms,
  - local Gaussian-neighbor averaging for calibration around explored points.
- Final submitted `predict.py` uses the fitted polynomial with a mild visible-geometry correction for `stop_post.posx` and `striker.posz`.
- In-band residuals showed systematic bias around 0.07 to 0.10 m, which remained large enough to hurt one-shot exam shots.

### What worked
- Broad-first then local-second sampling gave enough coverage to identify the scoring manifold rapidly.
- Mandatory referee probes were handled with model-based predictions and integrated into the fit.
- Dense low-power observations exposed where extrapolation is unsafe.

### What I would do differently next time
- Spend fewer shots in extreme high-power regions once global trend is established; reallocate to replicated low-power points near likely exam goals.
- Build a direct inverse policy from local empirical anchors (goal-to-knob interpolation) instead of only minimizing forward-model error.
- Add explicit bias correction learned from replicated in-band points, stratified by `shift` sign/magnitude.

### Scope notes (world vs device)
- Likely reusable world-level priors:
  - larger `|power|` and larger `cock` monotonically increase throw distance in broad trend,
  - interactions with `shift` are consistently strong across versions.
- Must re-identify every instance:
  - `ball_mass`, `slug_mass`,
  - local low-power response surface and exam-band bias.
