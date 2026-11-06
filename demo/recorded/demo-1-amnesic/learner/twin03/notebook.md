# Notebook

## v3_twin03_s3 — wide_mass_catapult

- Completed all 62 experiments and hit all 8 exam goals. The three pretest
  guesses failed badly because high cock and high power produce roughly
  -6 m, far beyond the target band.
- Reliable exam control family: hold `cock=0.15`, `shift=0.045`, and vary
  `power`. Measured anchors `(power, x)` were `(-0.12,-0.63770)`,
  `(-0.30,-0.87795)`, `(-0.55,-1.17559)`, and `(-1.00,-1.49400)`.
  Monotone PCHIP inversion of these anchors put all eight exam shots within
  the 0.048 m tolerance. This is preferable to inverting the full 3-D model
  for target-range goals.
- Knob effects: more-negative power and larger cock increase distance.
  Moving the slug inward (negative shift) lowers inertia and also increases
  distance. Effects interact strongly and motor-power gains saturate at the
  high-power end.
- A normalized 3-D Gaussian RBF (`epsilon=0.7`, smoothing `1e-5`) had about
  0.068 m leave-one-out RMSE over the full sampled cube. An ensemble with a
  multiquadric RBF was embedded in `predict.py`.
- Visible stop geometry has the analytic contact-angle relation
  `(striker_z-0.62+0.014)*sin(q) - 0.008*cos(q) = stop_x+0.020`.
  At the default dimensions this gives about `q=-0.116`. Most throws release
  the loose ball before the stop is reached, so visible-dimension changes
  matter mainly in the very-low-energy corner when a closer post pre-empts
  natural separation.
- Approximate device-specific estimates from early arm motion: ball mass
  about 0.04 kg (weakly identified; broad interval), slug mass about 0.13 kg.
- Approximate world estimates: motor-large gain about 2.8 N*m/command and
  torsion-soft stiffness about 0.83 N*m/rad. These were model-dependent and
  should be reused only as priors, with broad uncertainty. Bearing damping
  and dry friction were poorly separated; rail and material quantities were
  effectively unidentifiable because the slug was clamped and the outcome
  was first ground contact.
- Next time: begin with minimum-energy settings, establish a one-dimensional
  target-spanning calibration curve first, then spend the remaining budget
  on full-space and visible-dimension theory. Add more points between power
  -0.55 and -1.0 because this interval caused the largest exam interpolation
  error (still within tolerance).
