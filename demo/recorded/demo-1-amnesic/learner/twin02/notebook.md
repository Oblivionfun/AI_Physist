# Notebook

## Session v2_twin02_s2 — sprung stop-block catapult

### Result

- Exam: 8/8 goals hit.
- Pretest: 0/3; the initial guesses used far too much energy.
- Reliable goal-setting policy for this instance: fix `power=-0.12` and
  `shift=0.045`, then vary `cock` from about 0.18 to 0.43.

Useful calibration points (`cock` -> magnitude of landing x):

- 0.18 -> 1.004
- 0.22 -> 1.112
- 0.26 -> 1.191
- 0.30 -> 1.286
- 0.34 -> 1.392
- 0.38 -> 1.486
- 0.42 -> 1.600
- 0.45 -> 1.736

Piecewise-linear inversion of this table was accurate enough for all eight
exam targets. Repeated setup/contact variability caused errors of roughly
0.00–0.04 m, so dense local calibration matters.

### Behavior learned

- Distance rises strongly with motor magnitude and with moving the slug
  inward (negative `shift`).
- Cock angle is not globally monotone. At minimum motor power and outward
  slug, distance rose through `cock=1.2` and then fell by `cock=1.4`.
- There are two impact regimes. In the ordinary regime the arm settles near
  -0.117 rad. At sufficiently high energy it passes the post contact and
  settles near -0.96 rad. This produces a sharp response-surface transition.
- High cock angles make the launch increasingly vertical, explaining why
  more stored energy need not produce more horizontal range.
- The target interval is easiest and most robust in the low-energy ordinary
  regime; adding motor power is unnecessary.

### Model

`predict.py` embeds all 62 observations and uses a cubic RBF interpolant in
normalized `(cock, |power|, shift)` coordinates. For modified post/striker
dimensions it computes the geometric striker-contact angle and maps the run
to an equivalent cock angle by preserving estimated spring release plus
motor work. Experiments suggest `motor gain / spring stiffness` is about 2.

### Unknowns and scope

- World-scoped quantities persist across device instances: material
  friction/rolling values and the bearing, rail, spring, and motor catalog
  parameters.
- Device-scoped quantities must be reidentified: `ball_mass` and
  `slug_mass`.
- Rough current estimates: ball mass 0.05 kg, slug mass 0.14 kg, torsion
  stiffness 2.2 N·m/rad, motor gain 4.4 N·m per command. These are weakly
  identified; outcome data constrain ratios more strongly than absolute
  values.

### What to do differently

- Begin at the absolute minimum-energy corner. The goal range sits very near
  it; midpoint controls overshot by several metres.
- Spend early experiments on a short one-dimensional sweep that brackets the
  goal range, then explore the global response.
- Sample the high-energy pass-through boundary adaptively because smooth
  interpolation performs poorly across it.
- If modified geometry is important, build and fit a contact simulation;
  current experiments cannot directly validate the visible-dimension
  correction.
