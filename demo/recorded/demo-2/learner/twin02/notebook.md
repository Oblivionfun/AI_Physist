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

## 2026-11-07 — ramp_launcher v2, session v2_twin02_s2

- Completed 50 experiments. Pretest: 0/3; exam: 8/8.
- This device's ball is much lighter than the previous instance. The working estimate is
  0.35 kg (90% interval 0.30–0.45 kg). Ball mass is device-scoped and must be identified
  again for every instance.
- At drive 0.3 and tilt 0, the useful pullback calibration was approximately:
  (-0.160, 0.752), (-0.180, 0.855), (-0.190, 0.920), (-0.200, 0.969),
  (-0.210, 1.016), (-0.220, 1.073), (-0.230, 1.115), (-0.240, 1.188),
  (-0.245, 1.210), (-0.250, 1.241), (-0.255, 1.265), (-0.260, 1.311),
  (-0.265, 1.357), (-0.270, 1.387), (-0.2725, 1.430), and
  (-0.275, about 1.46). Individual launches fluctuate by roughly 0.01–0.03 m.
- Drive has a modest effect: changing drive from 0 to 0.6 usually changes range by only
  about 0.07–0.11 m. Tilt has a strongly energy-dependent effect. At pullback -0.24,
  tilt 0.2 changed range only slightly but tilt 0.4 reduced it by about 0.135 m.
- Low-energy, tilted launches can fail to crest the ramp and produce `no_landing`.
  Observed failures included (-0.143, 0.204, 0.425) and (-0.14, 0.2, 0.2).
- The submitted model is a ridge-regularized cubic response surface in pullback, drive,
  and tilt (training RMSE about 0.013 m). For modified ramp length it inverts the
  reference outcome to launch speed, applies gravity plus effective sliding work over
  the length change, then computes the ballistic landing point.
- World-scoped priors remain a soft spring near 360 N/m, low actuator gain near
  6 N/command, substantial rail damping, and effective wood/steel sliding coefficient
  near 0.204 from trajectory fitting. Physical parameters remain weakly identified.
- What worked: use tilt 0 and drive 0.3 for exam control, build a dense inverse
  calibration in the goal interval, and interpolate locally. Exam errors were all below
  0.011 m.
- What to do differently: infer the new device mass with an early pullback sweep before
  making pretest-like extrapolations. The pretest reused heavy-ball intuition and
  overshot every target by about 0.21–0.22 m.
