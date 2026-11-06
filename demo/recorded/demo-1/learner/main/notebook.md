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

## Wide-mass sprung stop-block catapult v3 — session v3_main_s3

- All 8 exam goals passed; all 3 pretest guesses failed. The new instance threw
  about 0.18--0.29 m farther than the inherited v2 calibration, confirming that
  the device-scoped masses must be reidentified before goal solving.
- The most useful local control slice was `cock=0.30, shift=+0.045`. Powers
  `0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24` gave landing positions near
  `-1.108, -1.158, -1.219, -1.238, -1.316, -1.343, -1.426` m. At `shift=0`,
  powers `0.12, 0.17, 0.22` gave about `-1.260, -1.402, -1.559` m. Interpolation
  on these two curves solved the exam with errors of 0.002--0.033 m.
- The near edge of the goal interval required lowering cock because power was
  already at its minimum: `cock=0.265, power=-0.12, shift=+0.045` landed at
  `-1.023` m.
- At `cock=0.30, power=-0.12`, moving the slug from `+0.045` to `0` to
  `-0.045` changed range from about `1.108` to `1.260` to `1.371` m. The
  inferred inertia ratio remains close to v2. Early-swing energy fitting and
  this shift response suggest `ball_mass` near the lower bound (about
  0.02--0.03 kg) and `slug_mass` about 0.10 kg. These are device-scoped.
- The 62-run campaign combined dense goal calibration with scrambled Sobol
  coverage of the full three-knob cube. A local cubic RBF had leave-one-out MAE
  about 0.17 m overall; the largest errors occur around the discontinuous
  high-momentum contact transition.
- Most runs halt near arm angle `-0.117` rad, but some high-cock/high-momentum
  runs penetrate the nominal stop contact and halt near `-0.96` rad. The mode
  depends on momentum and slug position, not just motor work, and is the main
  obstacle to a globally smooth response model.
- The submitted visible-dimension correction uses striker/post corner geometry,
  motor-plus-spring work equivalence with inherited `stiffness/gain ~= 0.16`,
  striker inertia, and a ballistic angle correction. It remains an analytical
  extrapolation because visible dimensions cannot be modified during lab runs.
- Working transferable estimates remain motor gain about 4.5 N*m/command and
  torsion stiffness about 0.7 N*m/rad. Friction, damping, and rolling parameters
  remain weakly identified for the first-contact outcome.
- Next time: retain the seven-point outer-shift calibration and add two
  low-cock points immediately, which covers the entire goal interval. For
  theory, target extra samples near the normal-stop/post-penetration boundary
  instead of spending all global runs on uniform space filling.
