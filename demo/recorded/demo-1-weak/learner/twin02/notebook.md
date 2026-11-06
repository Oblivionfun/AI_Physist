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

## Session v2_twin02_s2 - spring_stop_catapult (version 2)

### Outcome
- Protocol completed to `done`.
- Pretest: 0/3 (old-version prior was badly miscalibrated; this device throws much farther).
- Exam: 7/8.
- Lab usage: 62/62 experiments.

### What I learned about this device
- Minimum power (`power` near `-0.12`) is still enough to reach the entire goal band; most exam-relevant shots live in a narrow low-power manifold.
- `shift` has a strong and mostly monotone effect in the goal band:
  - positive `shift` (slug outward) moves landing x toward zero (less negative),
  - negative `shift` moves landing x farther (more negative).
- Around low power, `cock` is the primary coarse control and `shift` is an effective fine control.
- There is a regime change at higher energy (`cock * |power|` large): some shots produce much larger ranges and the arm can settle at a different post-impact angle (roughly around `-0.96` rad), so a single simple polynomial is not enough globally.

### Modeling notes
- A nonlinear feature model with a smooth regime gate on energy (`cock * |power|`) fit this instance well enough for inversion during exam.
- Dense calibration around the scoring range was the key: many points at `power` close to `-0.12` with shift sweeps (`-0.03` to `0.03`) gave reliable inverse targeting.
- Predictions were good in-distribution, but some mismatches remained for targets near the upper edge (`~ -1.08`) where tiny knob changes shift outcomes across tolerance.

### What worked
- Early detection that this version is far stronger than v1 avoided wasting budget at moderate powers.
- Alternating broad slices (for global behavior) with dense local mapping (for exam band) improved both theory and control.
- Keeping `power` near the minimum during exam and solving mainly with `cock + shift` produced stable hits.

### What I would do differently next time
- Reserve 3-5 repeated shots at the exact high-score edge (`-1.12` to `-1.02`) to better estimate local noise and sensitivity.
- Add a local bias correction from nearest measured neighbors on top of the global surrogate before exam inversion.
- Spend a few additional points varying one knob at a time around final exam candidates to reduce last-mile miss risk.

### Scope notes (world vs device)
- Likely world-level (reusable priors):
  - high-energy regime transition exists and can be captured by a smooth gate in `cock * |power|`,
  - directionality of `shift` effect (outward shift shortens range magnitude).
- Device-instance level (must re-identify each new instance):
  - exact slopes in the low-power goal band,
  - exact location/sharpness of the high-energy transition,
  - sealed masses (`ball_mass`, `slug_mass`) and resulting absolute scale.
