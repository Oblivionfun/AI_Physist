# Notebook

## Session v1_twin01_s1 — rail launcher

### Results

- Pretest: 0/3. I badly overestimated spring performance before observing the device.
- Exam: 8/8. Absolute errors were 0.0011–0.0176 m.
- A fixed `drive=0.3` plus inversion of the fitted pullback curve was reliable.

### What I learned

- Let spring compression be `c = -pullback - 0.100`. At the reference
  `track.size1=0.200`, range is a smooth, strongly nonlinear function of `c`
  and a smaller, nearly linear function of drive.
- Useful mean ranges at `drive=0.3`:
  - `c=.080 -> y=.616`
  - `c=.090 -> y=.683`
  - `c=.100 -> y=.757`
  - `c=.110 -> y=.837`
  - `c=.120 -> y=.922`
  - `c=.130 -> y=1.009`
  - `c=.140 -> y=1.097`
- The observed initial pullback varies by roughly 0.002–0.004 m around the
  command. Because local range slope is about 7–9, individual outcomes can
  move by 0.02–0.03 m. Fit the mean rather than chasing individual runs.
- The ball leaves the reference track with its centre near `y=0.225`. Its
  ballistic flight time is about 0.3256 s.
- Slow-run velocity traces imply track rolling deceleration near 0.0785
  m/s², corresponding to `rolling.steel` near 0.00020 m. For a longer track,
  propagate `v²` by `v_new² = v_ref² - 2*a*(L-.2)`, then add the new edge
  position and ballistic range.
- Ground-roll traces imply `rolling.concrete` near 0.00042 m.

### Scope and uncertainty

- World-scoped and reusable: material friction, rail damping/friction loss,
  actuator gain, spring stiffness, and rolling-resistance lengths.
- Device-scoped and must be identified again: `ball_mass`.
- Outcome data identify ratios such as stiffness/effective mass and
  actuator-gain/effective mass much better than the individual quantities.
  Keep broad intervals on mass, stiffness, gain, rail losses, and sliding
  friction.

### What to do differently

- For a new instance, do not reuse the ball mass or direct range curve.
- Start with 5–7 runs at `drive=0.3` spanning the goal range, fit a monotone
  pullback curve, then validate midpoint inversions.
- Use low-speed runs to recheck rolling resistance and high/low drive pairs
  to estimate actuator effect.
