# Notebook

## 2026-11-07 — rail_launcher v1, session v1_main_s1

- Completed the protocol with 70 experiments. Pretest: 0/3. Exam: 8/8.
- Device-instance result: this ball behaves as a relatively heavy ball; the belief used was
  mass 0.82 kg (90% interval 0.60–0.90 kg). Ball mass must be reidentified on a new instance.
- World properties persist across devices. The response suggests a low-gain actuator
  (about 6 N/command), a relatively soft spring (about 360 N/m), substantial rail damping,
  and effective wood/steel sliding friction around 0.55. These physical estimates are
  weakly identified because launch outcomes mostly constrain ratios of spring, motor, and
  moving mass.
- At the reference track half-length 0.2 m, a cubic in spring compression
  `d = -pullback - 0.1`, with quadratic drive interactions, fit 70 outcomes with RMSE
  about 0.0114 m. The fitted model is in `predict.py`.
- For changed track length, infer edge speed from `outcome = edge + speed * 0.32555`
  and propagate over added wood using `v_new² = v² - 2*0.55*g*delta_length`.
- A simple, robust control strategy is `drive = 0.3` and varying pullback. Useful measured
  points were approximately: (-0.205, 0.605), (-0.215, 0.652), (-0.225, 0.705),
  (-0.235, 0.747), (-0.245, 0.811), (-0.255, 0.894), (-0.265, 0.941),
  (-0.275, 1.023), (-0.285, 1.092).
- Outcomes fluctuate by roughly 0.01–0.02 m beyond the stated outcome noise, so average
  repeated runs or fit a smooth response surface instead of trusting one launch.
- What worked: broad initial mapping, repeated points, referee-probe interpolation, then a
  dense monotonic calibration curve in the goal region.
- What to do differently: the pretest pullbacks were far too weak. For goals 0.6–1.1,
  start near pullback -0.21 to -0.286 at drive 0.3. Spend fewer experiments below
  pullback -0.18 and use more repeats to estimate the stochastic spread.

## 2026-11-07 — ramp_launcher v2, session v2_main_s2

- Completed the protocol with 50 experiments. Pretest: 0/3. Exam: 8/8.
- The prior rail-launcher calibration transferred well at zero tilt once the extra
  0.26 m ramp length and its farther launch edge were accounted for. The pretest
  overestimated the benefit of a 0.15 rad tilt; all three choices landed short.
- On the standard ramp (`ramp.size1 = 0.13`), the most reliable controller was
  `drive = 0.3`, `tilt = 0`, and pullback alone. Measured calibration points were:
  `(-0.18, 0.741)`, `(-0.21, 0.866)`, `(-0.24, 0.990)`,
  `(-0.27, 1.123)`, `(-0.30, 1.257)`, and `(-0.32, 1.376)`.
- Shallow tilt is only mildly useful. At pullback -0.30, outcomes for tilt
  0, 0.1, 0.2, 0.3, 0.4, and 0.5 were approximately
  1.257, 1.289, 1.285, 1.248, 1.201, and 1.066 m. At lower launch energy,
  tilt rapidly reduces range and can cause the ball to reverse and never land
  during the run.
- The actuator has a small but interaction-dependent effect. At zero tilt,
  changing drive from 0 to 0.6 added about 0.048 m at pullbacks -0.18 and -0.30.
  At tilt 0.2 it added about 0.08 m. At the maximum pullback its benefit was
  inconsistent and smaller.
- A cubic ridge model of inferred ramp-exit speed achieved about 0.0084 m
  in-sample outcome RMSE and about 0.013 m leave-one-out RMSE. `predict.py`
  combines this fit with ballistic flight and an energy-based extrapolation for
  changed ramp length. The changed-length correction was not directly testable.
- The current device ball again appears relatively heavy; belief estimate 0.86 kg
  (90% interval 0.68–0.90 kg). Ball mass is device-scoped and must be reidentified.
  Spring, actuator, rail, material, bearing, and rolling properties are world-scoped.
- What worked: broad pullback and tilt sweeps, then using the smooth zero-tilt
  calibration for all exam goals. Directly reusing measured settings also gave
  high confidence near 0.98 m.
- What to do differently: start the pretest at zero tilt and interpolate the prior
  pullback curve. Reserve tilted launches for identifying the model and for the
  very top of the range; do not assume launch angle offsets the uphill energy loss.

## 2026-11-07 — gated_ramp_launcher v3, session v3_twin03_s3

- Completed 60 experiments. Pretest: 3/3. Exam: 6/8; both misses were goals
  above 1.30 m, beyond this instance's observed maximum of roughly 1.15–1.20 m.
- The new sprung gate removes about 0.2 m of range at high energy and creates a
  low-energy no-landing regime. At zero tilt and drive 0.4, pullback -0.18
  landed near 0.56 m, while -0.16 and weaker failed to clear and land.
- The safest standard-geometry controller was drive 0.8, tilt 0, and pullback
  interpolation. Useful measurements were approximately:
  `(-0.235, 0.765)`, `(-0.25, 0.824)`, `(-0.27, 0.921)`,
  `(-0.28, 0.947)`, `(-0.29, 1.022)`, `(-0.30, 1.061)`,
  `(-0.31, 1.094)`, and `(-0.32, 1.15–1.19)`.
- Tilt was consistently range-reducing on this gated launcher. Near maximum
  energy, increasing tilt from 0 through 0.1, 0.2, 0.3, 0.4, and 0.5 reduced
  range from about 1.16 to 1.08, 1.01, 0.92, 0.76, and 0.66 m.
- A cubic ridge response model fit the 56 successful launches with 0.0131 m
  in-sample RMSE and about 0.023 m leave-one-out RMSE. `predict.py` combines
  this reference-geometry fit with projectile motion and an energy correction
  for changed ramp length. The gate-height correction is weak and unvalidated.
- Device-scoped ball and gate masses remain weakly identified; estimates were
  0.65 kg and 0.055 kg with broad intervals. All material, spring, actuator,
  bearing, rail, and rolling properties are world-scoped and carry across
  instances.
- What worked: transferring the zero-tilt strategy, mapping the full pullback
  curve, using maximum drive for monotonic exam control, and reporting the
  unreachable upper goal region.
- What to do differently: prioritize repeated maximum-energy launches earlier
  to quantify their unusually large run-to-run spread, and reserve more trials
  for identifying how the gate-clearance threshold shifts with tilt and drive.
