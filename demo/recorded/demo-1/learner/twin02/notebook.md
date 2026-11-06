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

## Sprung stop-block catapult v2 — session v2_twin02_s2

- All 8 exam goals passed; all 3 pretest goals failed. The v1 settings transfer
  poorly because the torsion spring and movable slug add substantial energy.
- The safest goal-control slice is `cock=0.15, shift=0`. Measured landing-distance
  magnitudes at power magnitudes `0.12, 0.20, 0.30, 0.40` were respectively
  `1.045, 1.201, 1.416, 1.609` m. Piecewise-linear inversion of this curve gave
  exam errors from 0.002 to 0.045 m.
- At `cock=0.15, power=-0.12`, moving the slug from `shift=-0.045` to `+0.045`
  shortened the range from 1.098 to 0.935 m. At `power=-1.0`, the corresponding
  inward/outward ranges were 2.620 and 2.197 m. Positive shift increases driven
  inertia and consistently shortens the throw.
- Range is strongly nonlinear in cock and power. At high energy the arm can pass
  the normal stop mode and settle near -0.96 rad rather than -0.117 rad. A 62-run
  three-dimensional response surface is more reliable than a single global
  energy equation across that transition.
- The submitted theory uses an exact quintic RBF surface blended with a small
  multiquadric component. Eight-fold held-out tests gave about 0.24 m mean
  absolute error for the quintic model over the full 0.9–11.3 m response range.
- For modified visible dimensions, striker/post contact geometry gives
  `q_stop = atan2(0.008, r+0.014) + asin((post_x+0.020)/hypot(r+0.014,0.008))`,
  where `r = striker_z-0.620`. The model converts the stop-angle change into an
  equivalent cock-travel change. This correction is physically motivated but
  could not be directly validated under the fixed-dimension experiment protocol.
- World-scoped bearing/rail damping and friction loss, material friction/rolling,
  motor gain, and torsion-spring stiffness transfer between devices. Ball and
  slug masses are device-scoped and must be reidentified. This session strongly
  identified the response surface but did not separately identify those physical
  unknowns, so the submitted belief intervals remain broad.
- Next time on v2: begin immediately with the `cock=0.15, shift=0` calibration
  slice. Spend additional runs near the high-energy contact-mode boundary only
  if global theory accuracy matters; goal hitting does not require that regime.
