# Notebook

## 2026-11-07 — Sprung stop-block catapult v3 (`wide_mass_catapult`)

### Result

- Pretest: 0/3. Initial intuition severely overestimated the controls needed.
- Exam: 8/8 within the 0.048 m tolerance.
- Used all 62 experiments.

### What I learned

- The outcome is strongly nonlinear in cock, motor magnitude, and slug shift. A
  simple additive response is not adequate. For example, `(0.8, -0.5, 0.0)`
  lands near `-5.25 m`, while the useful goal range is reached with controls
  near the lower ends of cock and power.
- Moving the slug inward generally increases range by reducing rotational
  inertia. At `(cock=0.15, |power|=0.12)`, changing shift from `+0.045` to
  `-0.045` increased distance from about `0.822` to `1.008 m`.
- A cubic RBF surrogate on normalized `(cock, |power|, shift)` worked well.
  Tuned coordinate scales `(2.0, 1.0, 0.5)` and smoothing `0.03` gave
  six-fold CV RMSE about `0.112 m` overall and `0.042 m` below `2 m`.
- Dense sampling in the actual goal range mattered more for control than
  fitting a globally elegant physical model. Reusing measured settings near a
  goal and making one-dimensional interpolations produced 8/8 exam hits.
- The striker/post contact angle can be computed geometrically. With striker
  height `z_s` and post center `x_p`, the first-corner contact estimate is
  `theta = atan2(0.008, z_s-0.606) +
  asin((x_p+0.020)/hypot(z_s-0.606, 0.008))`. It is about `-0.1165 rad` for
  the nominal dimensions.
- Before impact, the ball sits against the outer lip. Its local offset explains
  why the stop impulse can produce a positive vertical launch component even
  though the arm is rotating toward negative angle.

### Estimated unknowns

World-scoped quantities should transfer to later devices in this world:

- `gain.motor_large ≈ 3.26 N*m/unit`, rough 90% interval `[2.8, 3.8]`
- `stiffness.torsion_soft ≈ 0.67 N*m/rad`, rough interval `[0.50, 0.95]`
- Bearing losses appeared small, but were weakly identified.
- Rail losses and material/rolling coefficients were not identified because
  the slug was clamped and the outcome stops at first ground contact.

Device-scoped quantities must be re-identified on every new instance:

- `ball_mass ≈ 0.022 kg`, rough interval `[0.020, 0.040]`
- `slug_mass ≈ 0.083 kg`, rough interval `[0.060, 0.110]`

These dynamic estimates came from pre-contact arm angle/rate energy balances.
They are correlated: motor gain, spring stiffness, and carried inertia can
trade off, so do not treat the point estimates as independently precise.

### What worked

- A two-stage design: dense Latin-hypercube samples in
  `cock=[0.15,0.53]`, `|power|=[0.12,0.44]`, plus broad whole-domain samples.
- Refitting the surrogate after every result kept mandatory predictions honest
  and increasingly accurate.
- For exam goals, prefer exact previously measured settings already within
  tolerance; otherwise vary one knob from a nearby measured anchor.

### What I would do differently

- Spend the first probes on an explicit low-energy calibration curve rather
  than guessing three increasingly energetic pretest settings.
- Allocate more experiments to repeated one-dimensional sweeps at fixed cock
  and shift. That would improve inverse control and separate simulator
  variability from local slope.
- Use fewer broad high-energy samples; they help theory coverage but are much
  less valuable for the stated goal interval.
- Save full release-time/velocity features from every trace during the lab,
  not only outcomes, to improve prediction under modified stop dimensions.
