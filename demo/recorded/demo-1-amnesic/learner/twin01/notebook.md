# Notebook

## v1_twin01_s1 — stop-block catapult

### Results

- Pretest: 0/3. Initial guesses used far too much energy; outcomes were roughly
  -2.85 to -4.02 m for goals near -1.2 m.
- Exam: 8/8, with absolute errors 0.007–0.049 m.
- Full-space five-fold model error was about 0.060 m RMSE; local fold-model
  disagreement at the chosen exam controls was 0.001–0.008 m.

### Behavior learned

- The useful goal range is a low-energy region, typically `cock=0.17..0.39`
  and `|power|=0.28..0.37`. A good central example is approximately
  `cock=0.258, power=-0.315 -> x=-1.32` (model predicted -1.351).
- Outcome is smooth in both controls but strongly nonlinear. More cock and more
  power generally increase distance.
- There are two launch regimes. With modest cock, the ball is retained until
  the striker/post impact and launches nearly horizontally. At large cock it
  centrifugally separates while the arm is still at positive angle, launching
  upward before the post impact. High-energy final arm angles around -0.84 rad
  are therefore not the ball-release angle.
- At nominal geometry the striker first contacts the post near arm angle
  -0.106 rad. Geometrically, changed post positions satisfy
  `0.114*sin(q)-0.008*cos(q)=post_x+0.020`.
- The rolling ball slowed by about 0.21 m/s² after landing, suggesting the
  larger steel/concrete rolling-resistance length is around 0.0005 m.

### Model and identification

- `predict.py` embeds all 80 measurements and uses a quadratic trend plus a
  Matérn-5/2 residual process. It applies mechanics-based corrections for the
  two visible changes: a stop-angle/equivalent-travel correction that fades
  out in the early-release regime, and an inertia/gravity-work correction for
  slug height.
- Initial arm acceleration gave `gain / effective_inertia ≈ 1158`. Combining
  this with plausible device masses puts `gain.motor_large` near 5.3 N·m per
  command. Masses are correlated and less sharply identified; working values
  were ball 0.052 kg and slug 0.15 kg.
- World-scoped quantities carry across devices: bearing damping/frictionloss,
  material sliding and rolling parameters, and motor gain. Device-scoped
  quantities must be reidentified each instance: ball mass and slug mass.

### What to do differently

- For the next related device, begin pretest near the minimum-energy corner,
  not the middle of both control ranges.
- Spend initial experiments directly around the goal band before mapping the
  full rectangle.
- Use low-disagreement inverse solutions rather than merely inverting one
  fitted surface. This produced all eight successful exam throws.
- Sensor traces are essential for separating release regimes; final arm angle
  alone is misleading.
