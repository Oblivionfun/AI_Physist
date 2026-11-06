# Notebook

## Session v1_twin01_s1 (stop_catapult v1)

### What I learned
- The response surface is strongly nonlinear in `cock` and `power`.
- There is a low-energy band that cleanly covers the goal interval:
  - Around `power = -0.2`, increasing `cock` from about `0.2` to `0.6` moves landing x from about `-0.93` to `-1.54`.
- Higher-energy settings rapidly overshoot (x << -2), with throws reaching roughly `-6` to `-7`.
- A cubic polynomial with interaction terms plus a hinge in energy (`cock * (-power)`) fits observed data well in-sample.

### What worked
- Initial broad exploration quickly identified safe/unsafe regimes.
- Densifying samples near the scoring band (`[-1.52, -1.02]`) was valuable for exam control.
- Keeping exam policy simple (fixed `power = -0.2`, tune only `cock`) produced stable outcomes.
- Probe predictions improved after mapping both low and high-energy regions.

### What did not work / mistakes
- Pretest guesses used too much power and overshot badly on 2 of 3 goals.
- Interpolation-only exam policy had small local bias around some targets (~0.06 to 0.08 m), causing 2 misses.

### World vs device unknowns (tracking)
- Likely world-shared effects:
  - motor gain, bearing damping/frictionloss, and material friction strongly shape overall slope/nonlinearity.
- Device-instance effects:
  - `ball_mass` and `slug_mass` shift throw distance and may explain residual bias between nearby targets.

### If I repeat this family
- Spend 5-8 extra experiments specifically for bias correction in the target band (same power, dense cock sweep).
- Use local recalibration right before exam:
  - fit a 1D monotone curve at fixed power in the exact scoring band and apply bias correction.
- Keep a dual-mode theory model:
  - smooth global model for broad extrapolation,
  - local model prioritized for goal-hitting control.
