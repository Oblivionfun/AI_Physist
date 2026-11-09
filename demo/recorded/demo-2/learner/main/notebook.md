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

## 2026-11-07 — gated_ramp_launcher v3, session v3_main_s3

- Completed the protocol with 60 experiments. Pretest: 0/3. Exam: 8/8.
- The new gate changes the low-energy response substantially and makes the
  pullback curve more nonlinear. At `drive = 0.3`, `tilt = 0`, useful measured
  points were approximately: `(-0.220, 0.760)`, `(-0.225, 0.779)`,
  `(-0.240, 0.883)`, `(-0.250, 0.946)`, `(-0.260, 0.993)`,
  `(-0.270, 1.058)`, `(-0.280, 1.141)`, `(-0.290, 1.191)`,
  `(-0.300, 1.258)`, `(-0.305, 1.319)`, and `(-0.310, 1.368)`.
- Zero tilt with fixed drive and interpolated pullback remained the most robust
  controller. It hit all eight exam goals. Individual high-energy launches varied
  by up to about 0.04 m, but the 0.06 m goal tolerance absorbed this variation.
- At low energy the ball may never leave the apparatus: pullbacks -0.12 and -0.15
  at drive 0.3, zero tilt produced `no_landing`. Increasing tilt lowers range
  strongly except for a small optimum near 0.1 rad at high energy. At pullback
  -0.30 and drive 0.3, outcomes at tilt 0, 0.1, 0.2, 0.3, and 0.4 were about
  1.26, 1.23, 1.16, 1.03, and 0.87 m.
- Drive has a smooth but modest effect: changing it from 0 to 0.8 typically adds
  about 0.09–0.13 m. It is better kept fixed for goal control.
- The submitted theory is a ridge-regularized quadratic response surface
  (leave-one-out RMSE about 0.027 m). It converts the fitted standard-dimension
  outcome to launch speed, then applies gravity and rolling-energy corrections
  for changed ramp length and a geometric energy correction for gate height.
- Initial acceleration regressed against compression and drive gave approximately
  `stiffness / moving_mass = 362 s^-2` and
  `actuator_gain / moving_mass = 6.36 m/s^2`. Combined with the persistent world
  estimates, this device's ball is likely heavy: about 0.87 kg, with a 0.75–0.90
  kg 90% interval. Ball and gate masses are device-scoped and must be reidentified;
  spring, actuator, damping, friction, rolling, and torsion properties are
  world-scoped.
- What worked: broad tilt/drive mapping, dense zero-tilt calibration in the goal
  range, repeats near the high-energy nonlinear region, and conservative
  interpolation for the exam.
- What to do differently: use the transferred zero-tilt curve for pretest rather
  than adding speculative gate compensation. The three pretest settings were all
  too energetic. Also reserve more repeats for pullbacks -0.30 to -0.31, where
  run-to-run variation was largest.

## 2026-11-07 — gated_ramp_launcher v4, session v4_main_s4

- Completed the protocol with 54 experiments. Pretest: 3/3. Exam: 8/8.
- The v3 zero-tilt controller transferred directly and fixed the previous pretest
  failure. With `drive = 0.3`, `tilt = 0`, the fitted mean calibration for pullbacks
  -0.21 through -0.30 was approximately 0.730, 0.774, 0.823, 0.876, 0.933,
  0.995, 1.062, 1.132, 1.208, and 1.288 m.
- Direct measurements around that curve included `(-0.21, 0.710)`,
  `(-0.22, 0.772)`, `(-0.24, 0.896)`, `(-0.26, 1.007)`,
  `(-0.27, 1.071)`, `(-0.28, 1.117)`, and `(-0.30, 1.297)`.
  The high-energy region remained noisy and occasionally non-monotonic.
- Tilt consistently reduced range for this instance. At pullback -0.30 and drive
  0.3, tilt 0, 0.1, 0.2, 0.3, 0.4, and 0.5 produced about 1.297, 1.262,
  1.178, 1.018, 0.865, and 0.722 m.
- Drive had a modest, smooth effect. At zero tilt, changing drive from 0 to 0.7
  added roughly 0.07–0.10 m over the tested goal region.
- A ridge-regularized quadratic response surface fit successful launches with
  RMSE 0.0247 m and leave-one-out RMSE 0.0350 m. The submitted model uses a
  ballistic speed conversion and the prior `-4 g delta_gate_half_height`
  correction for modified gate height; that dimension correction remains
  experimentally unvalidated.
- Initial-velocity regression gave `stiffness / moving_mass ≈ 401 s^-2` and
  `actuator_gain / moving_mass ≈ 7.55 m/s²`. With the persistent world prior,
  the device-scoped ball mass is estimated near 0.82 kg (90% interval 0.68–0.90);
  gate mass remains weakly identified.
- What worked: transfer the prior controller immediately, map tilt and drive
  interactions, then reserve a dense zero-tilt calibration for goal control.
- What to do differently: allocate more repeated runs at identical pullbacks
  instead of densely spacing high-energy pullbacks, because setup/contact
  variability dominates millimetre-scale knob changes. The interface also needs
  an explicit way to predict `no_landing`; `[null]` currently errors.
