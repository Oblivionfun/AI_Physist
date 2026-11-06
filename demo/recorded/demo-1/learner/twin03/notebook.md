# Notebook

## Stop-block catapult v1 — session v1_main_s1

- The useful goal band is reached with low-energy settings. A well-resolved control
  curve is `cock=0.30`: power magnitudes 0.224, 0.266, 0.366, 0.394, and 0.411
  produced exam outcomes about 1.05, 1.18, 1.43, 1.45, and 1.51 m. At
  `cock=0.15, power=-0.55`, the outcome is about -1.24 m.
- All 8 exam goals passed. The pretest failed because midpoint knob settings launch
  much farther than the goal band (roughly -2.6 to -3.4 m).
- Landing distance is a smooth two-dimensional function over most of the knob
  domain, but high-energy impacts can pass the post and stop near arm angle
  -0.84 rad rather than -0.107 rad. The landing surface remains fairly continuous
  across this contact-mode change.
- Repeated/setup variation can move the landing point by several centimetres, so
  calibrating directly in the requested distance band is more reliable than
  inverting a global physical model.
- `predict.py` embeds a measured 9x6 response surface. It models post-x changes as
  added arm travel and slug-z changes through driven rotational inertia. Those
  visible-dimension corrections are extrapolations, because the protocol did not
  permit changing visible dimensions during experiments.
- World-scoped quantities are bearing damping/friction loss, material friction and
  rolling resistance, and motor gain; these should transfer to future devices.
  Ball and slug masses are device-scoped and must be reidentified. This session did
  not isolate the unknowns tightly; the submitted belief intervals are deliberately
  broad, with central working estimates of 0.05 kg for the ball, 0.15 kg for the
  slug, and 4.0 N*m per command for the motor.
- Next time: use the first experiments near `cock=0.30, |power|=0.20..0.42` for
  immediate goal calibration, then spend more of the budget identifying visible
  dimension sensitivities or inertial parameters rather than densely sampling
  extreme throws.

## Sprung stop-block catapult v2 — session v2_main_s2

- All 8 exam goals passed; all 3 pretest guesses failed. The spring and movable
  slug make the v1 calibration non-transferable, so this device needs an early
  low-energy recalibration.
- A reliable one-dimensional exam control is `cock=0.30, shift=0`. Measured
  landing positions for power magnitudes `0.12, 0.17, 0.22, 0.27, 0.32, 0.37`
  were approximately `-1.085, -1.199, -1.299, -1.414, -1.491, -1.648` m.
  Smooth interpolation on this curve put every exam result within 0.040 m.
- Moving the slug inward strongly increases launch speed. At
  `cock=0.30, |power|=0.22`, shifts `-0.045, 0, +0.045` landed at about
  `-1.439, -1.299, -1.184` m. Converting these distances to impact angular
  speeds gives an outer/inner inertia ratio near 1.56.
- Combining that inertia ratio with the known part inertias and the transferable
  motor range suggests this device has a ball near 0.02 kg and a slug near
  0.10 kg. These are device-scoped and must be estimated again on a new instance.
- The submitted nominal predictor is a cubic radial-basis response surface over
  all 62 experiments. Leave-one-out error was about 0.105 m overall and 0.037 m
  for outcomes under 2 m; the sparse high-energy corners dominate the larger
  global errors.
- Visible-dimension handling is physics-based but unvalidated experimentally.
  The stop angle is computed from rotated striker-corner/post-face contact,
  motor plus spring work is mapped to an equivalent nominal cock angle, and the
  ballistic flight is recomputed at the changed stop angle. The nominal contact
  calculation reproduces the observed stopped arm angle of about -0.117 rad.
- Working world estimates are motor gain about 4.4 N*m/command and torsion
  stiffness about 0.7 N*m/rad. Material friction, rail parameters, and rolling
  resistance remain weakly identified because they barely affect first contact.
- Next time: first measure the six-point `cock=0.30, shift=0` power curve, then
  use symmetric slug shifts at one setting to infer the instance mass ratio.
  Spend remaining runs on global coverage only if theory scoring matters.

## Sprung stop-block catapult v3 — session v3_twin03_s3

- Seven of eight exam goals passed. The sole miss was only about 0.0013 m
  outside the 0.048 m tolerance: reusing the exact measured setting
  `cock=0.30, power=-0.12, shift=-0.045` moved from -1.090 m in calibration to
  -1.044 m in the exam. Avoid relying on a single boundary-adjacent replicate.
- The robust exam control remained `cock=0.30, shift=0`. A smoothed inverse
  curve gave powers 0.192, 0.240--0.249, and 0.264 for goals around 1.13, 1.24,
  and 1.29 m; these all passed. The measured nominal curve at powers
  0.22, 0.27, 0.32, 0.37, and 0.39 landed near -1.204, -1.298, -1.381,
  -1.470, and -1.551 m.
- All three pretest attempts failed because the v2 curve overpredicted range.
  Ball and slug masses are device-scoped, so even the same mechanism needs a
  fresh six-point calibration before goal inversion.
- Slug shift has a large, repeatable effect. At `cock=0.30`, symmetric
  `shift=-0.045/+0.045` pairs gave landing distances 1.517/1.215 m at power
  0.32 and 1.644/1.303 m at power 0.37. The inferred outer/inner rotational
  inertia ratio is about 1.68.
- Combining that ratio with motor/spring energy suggests this instance has a
  ball near 0.04 kg and slug near 0.155 kg. These estimates are device-scoped.
  The transferred world estimates remain motor gain about 4.4 N*m/command and
  torsion stiffness about 0.71 N*m/rad.
- `predict.py` now embeds all 62 v3 measurements in a cubic RBF surface and
  retains the geometric stop-angle/ballistic correction for modified post-x
  and striker-z dimensions. Those visible-dimension corrections remain
  analytical extrapolations because dimensions cannot be modified in lab runs.
- Next time: take duplicate measurements at low-range candidate settings and
  aim for the center of tolerance rather than selecting a setting from one
  apparently exact observation.
