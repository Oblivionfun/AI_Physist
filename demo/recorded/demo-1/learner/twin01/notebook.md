# Notebook

## Session v1_twin01_s1 — stop-block catapult

### Results

- Used all 80 experiments and passed 6/8 exam goals. All three uninformed
  pretest attempts overshot badly.
- The pretest guesses used cock 0.7–0.8 and power magnitude 0.28–0.30, producing
  landings around -2.27 to -2.53. Goal-range throws require power very near the
  lower end of its range.
- Exam strategy fixed `cock=0.5` and varied power. It was reliable for targets
  from about -1.11 to -1.38. Both misses were long-range targets near -1.50:
  powers -0.229 and -0.231 landed near -1.57, just outside tolerance.

### Empirical behavior

- At `cock=0.5`, measured calibration points were approximately:
  - power -0.15 -> x=-1.121
  - power -0.20 -> x=-1.361
  - power -0.25 -> x=-1.602
  - power -0.40 -> x=-2.276
  - power -0.70 -> x=-3.288
- Exam runs showed enough contact sensitivity that simple interpolation was
  overconfident around power magnitude 0.23. In a future session, use about
  0.215–0.220 for a requested x near -1.50, or choose a lower-power solution by
  increasing cock angle.
- The full two-knob response is smooth over most of the domain but strongly
  nonlinear. At high cock and high power, the soft stop can be overrun and
  throws reach x below -7. At minimum power, distance rises with cock through
  roughly 1.05 rad and then falls by cock 1.3.
- A cubic local RBF over normalized `(cock, |power|)` with 12 neighbors and
  smoothing 0.001 gave about 0.040 m mean absolute leave-one-probe error.
- Sensor traces indicate the ball leaves near the arm's vertical position
  (`q≈0`), before the striker's resting contact angle (`q≈-0.107`). Therefore
  the submitted model treated allowed changes in `stop_post.posx` as largely
  causally irrelevant to first landing.
- `slug.posz` is expected to matter through rotational inertia and gravitational
  work. The submitted model maps it to an equivalent power before querying the
  empirical response surface. This extrapolation was not experimentally
  testable in the session.

### Unknowns and scope

- World-scoped quantities persist across devices: bearing damping and dry
  friction, material sliding/rolling coefficients, and `motor_large` gain.
- Device-scoped quantities must be reidentified each instance: `ball_mass` and
  `slug_mass`.
- Early-arm dynamics constrain roughly `motor gain / effective inertia`, but do
  not separately identify gain and the two sealed masses because the loose ball
  ceases to contribute rigidly during acceleration. Friction and rolling
  parameters are especially weakly identified because the graded outcome is
  first ground contact.

### What to do differently

- Begin calibration at the minimum power, around `cock=0.45–0.55`; do not infer
  scale from actuator range.
- Spend several repeated trials around the exact goal band to measure contact
  variability instead of allocating every run to broad factorial coverage.
- For inverse control, optimize for the center of the tolerance band with a
  conservative short-landing bias near the far edge. Prefer solutions whose
  local response slope is smaller.
- Keep broad response-surface coverage for theory, but reserve 10–15 trials for
  repeated validation and local inverse calibration.
