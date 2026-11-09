# Design log

## v1 — `rail_launcher` (round 1, submitted)

Saved as `designs/v1.py`.

### What it is
A latched spring plunger throws a ball off the end of a raised rail onto the floor.

- `table` (concrete base) carries `track` (wood, the rail the ball runs on, top at z = 0.52).
- `stand` is a *separate base* beside the rail, so the sliding plunger is not attached to the
  track. That decoupling is what lets the rail length be modified without breaking geometry or
  creating collisions.
- `plunger` (wood box) slides along +y on a `rail` joint with a `coil_soft` spring at rest 0,
  range (-0.21, 0). A `latch` holds it at the setup value; the `linear_actuator` motor `drive`
  pushes along the same axis.
- `ball` (steel sphere, r = 0.025) is `carried_by` the plunger so it retracts with it and stays
  in contact. Its mass is the device-specific hidden quantity (`ball_mass`, 0.12–0.6 kg).

### Mechanics the learner has to recover
Release energy is `0.5*k*c^2 + F*drive*c` over the stroke `c`, shared by plunger + ball
(`m_p` known from geometry, `m_b` hidden). The plunger stops at its end-stop and hands the ball
off; the ball then rolls to the open end (rolling resistance + contact friction) and flies.

`v^2 ≈ 2c(0.5*k*c + F*drive) / (m_p + m_b)`, so stiffness, actuator gain and hidden mass are
confounded; only sweeping *both* knobs separates `k/M` from `F/M`. Certification confirmed the
relevant parameters: `ball_mass`, `stiffness.coil_soft`, `gain.linear_actuator`, and
friction/rolling of steel.

### Knobs / outcome
- `pullback` ∈ [-0.20, -0.05] m (slide setup), `drive` ∈ [0, 1].
- Outcome: ball `landing_point` y ∈ [0.66, 1.25] m, tolerance 0.05, budget 70, horizon 2.5 s.
- Modifiable: `track.size1` ∈ [0.18, 0.45] (default 0.20). Moves the launch point by up to
  ~0.2 m *and* lengthens the roll, so it interacts with the pullback knob.
- Sensors: plunger coordinate and velocity, ball velocity and position.

### Sizing reasoning
Knob authority must exceed the world spread or the goal space is unreachable in corner worlds.
`sqrt(k/M)` spans about 4x across the priors, so `pullback` spans 4x and `drive` adds a further
boost that is largest exactly in the weak-spring worlds. The pullback floor (0.05 m) is set so
even the weakest world still clears the rail instead of stalling (rolling resistance needs
roughly v > 0.55 m/s over the longest rail).

### Certification history
- tol 0.045 / budget 50: everything passed except C3 learnability (4/6, needs 5/6).
- tol 0.06 / budget 70 / goals [0.66, 1.25]: certified, but C2 nominal (0.281) was flagged
  borderline and the modification test sat at 1.501.
- tol 0.05 / budget 70 / modifiable up to 0.45: certified with margin on both the default and
  the stricter `fast` profile (C2 nominal 0.14/0.17, fixed action 0.22/0.20, modification
  3.41/1.92, learnability 6/6). Submitted this one.

### Risks carried into the report
Learnability came out 6/6 locally, which may mean the real learner scores above the 80% target
band. The structure is a single smooth energy balance, so a curve-fitting baseline could do well
if the referee does not move the rail length at exam time.

## v2 — `rail_launcher` (round 1, resubmitted after rejection)

Saved as `designs/v2.py`.

### Why v1 was rejected
C1 existence: 0.292 vs 0.8. The oracle hit only 14/48 goals; goals near 0.90-1.21 are
unreachable in the weak corners of the prior. Local checks had passed because a single drawn
world happens to cover the whole goal space — the failure only shows up when averaging over
the prior, which the local check does not do for C1.

### Diagnosis
I wrote `envelope.py`, a closed-form reach estimator
(`E = 0.5 k c^2 + F d c - f c - damping losses`, `v = sqrt(2E/(m_p + 1.4 m_b))`, roll to the
rail end, projectile flight) and swept the 2^6 corners of the prior. It reproduced v1 exactly:
the band reachable in *every* world was [0.63, 0.76], while the declared goal space was
[0.66, 1.25]. So roughly 15% of the goal space was universally reachable, matching 14/48.
The lesson: the goal space must sit inside `[max_worlds(min reach), min_worlds(max reach)]`,
not inside the reach of a typical world.

### What changed
Widen knob authority and shrink the mass spread so that the universally reachable band is wide
enough to hold a goal space several tolerances across:
- plunger thinned from half-z 0.03 to 0.008 (0.175 -> 0.094 kg), so the hidden ball mass
  dominates the moving mass instead of being masked by the carriage;
- slide range (-0.21, 0) -> (-0.30, 0) and `pullback` -0.28..-0.03 (stroke span 9x, so spring
  energy spans ~87x and comfortably outruns the ~6x world spread);
- `ball_mass` prior 0.12-0.6 -> 0.06-0.3 kg (still 5x, densities 917-4584 kg/m^3);
- goal space 0.66-1.25 -> 0.63-1.08, inside the estimated universal band [0.56, 1.19].

Full pullback puts the ball at y = -0.135, still on the rail even at the shortest modifiable
rail (back end -0.18), and the thinner plunger still clears the rail top by 17 mm.

### Certification (fast profile, both runs)
C1 1.000 (24/24), C1b 0.99, C2 nominal 0.11, C2 fixed action 0.264, C3 modification 2.49,
identifiability 0.002, learnability 6/6. The first attempt at goals [0.65, 1.05] gave fixed
action 0.279, uncomfortably near the 0.3 ceiling, so I widened the band to [0.63, 1.08]: that
lowers single-action coverage to 0.264 and costs only 0.02 of C1 margin at each end.

### Risks carried into the report
Learnability is again 6/6 locally and the structure is one smooth energy balance, so the
curve-fitting baseline may do well unless the referee moves the rail length at exam time.
Expect the report to say the learner scored above the 80% band rather than below it.

### Next round (planned, superseded by v3)
Keep the table, rail, plunger and ball (world properties transfer), and add genuinely new
piecewise mechanics rather than tighter tolerances: a hinged, latched flap at the rail end whose
locked angle is a second setup knob (launch angle, with a second hidden mass on the flap), plus
a mid-rail obstacle that the ball must clear or bounce over. That adds an interacting unknown
and a contact event that no smooth fit of range-vs-knobs can capture.

## v3 — `rail_launcher` (round 1, resubmitted after second rejection)

Saved as `designs/v3.py`. Certified on `--profile fast` and submitted.

### Why v2 was rejected
C0 timestep convergence: 1.171 vs 1.0. Everything else passed (C1 0.917). In v2 the spring
rest sat at joint coordinate 0, which is also the forward end-stop of the slide. So the plunger
accelerated over the whole stroke and the ball separated from its face at the exact instant the
plunger slammed into the stop: the ball's exit velocity was set by an impact, and halving the
timestep moved the landing point by more than a tolerance.

### The fix: a spring-rest hand-off instead of an end-stop hand-off
Move the spring's rest point back from the stop (`rest=-0.10`, range `(-0.34, 0)`). Past the
rest point the spring decelerates the plunger, the ball stops being pushed and rolls on alone.
Separation now happens at joint coordinate `rest + F_motor/k`, a smooth event in the middle of
the travel, and the plunger's own arrival at the stop (gentle or absent — in stiff worlds it
reverses before reaching it) no longer touches the outcome. Measured convergence: 0.522.

Two sizing consequences follow from requiring `F_motor_max / k_min < 0.10` so the separation is
always strictly before the stop:
- spring `coil_soft` -> `coil_stiff` (k_min 40 -> 250 N/m), and `drive` capped at 0.6
  (F <= 18 N, so the worst corner separates at 0.072 < 0.10);
- the stiffer spring needs a heavier projectile or the short shots collapse to a sliver of
  stroke, so `ball_mass` went 0.06-0.3 -> 0.3-0.9 kg (density 4584-13751, inside the 20000
  ceiling). The hidden mass now dominates the moving mass (plunger is 0.094 kg).
- knob `pullback` -0.32..-0.12 (stroke 0.02..0.22, 11x; energy 121x) and the whole launcher
  shifted +0.015 in y so full pullback keeps the ball 0.04 clear of the rail's back edge at the
  shortest modifiable rail;
- `modifiable track.size1` lower bound 0.18 -> 0.20 (the built value) to pay for that shift;
- goal space 0.63-1.08 -> 0.60-1.10. Hand reach estimate for the universal band was
  [0.52, 1.18]; the declared band is 10 tolerances wide, which keeps fixed-action coverage low.

### Certification (fast profile)
C0 physics 0.000, timestep 0.522, C1 1.000 (24/24), C1b 1.000 (96/96), C2 nominal 0.109,
C2 fixed action 0.238, C3 modification 3.45, identifiability 0.001, learnability 6/6.

### Risks carried into the report
- `relevant_parameters` is now `stiffness.coil_stiff, ball_mass, friction.steel, rolling.steel`:
  `gain.linear_actuator` dropped out, so the `drive` knob has become a weak second axis. If the
  referee reports the learner ignoring `drive` with no penalty, that knob is dead weight and the
  second axis has to come from somewhere else (see below).
- Learnability is 6/6 locally for the third time and the structure is still one smooth energy
  balance, so expect the learner to score above the 80% band rather than below it.

### Next round (planned)
Replace the weak motor-on-the-plunger axis with a genuinely interacting one: a hinged, latched
flap at the rail end carrying its own hidden mass, whose locked angle is the second setup knob,
so the launch angle and the energy split are coupled and a contact event (the ball striking the
flap) sits between the spring and the flight. Keep table, rail, plunger, steel ball and the
coil_stiff spring so the world properties learned this round transfer.

## v4 — `ramp_launcher` (round 2, submitted)

Saved as `designs/v4.py`. Certified on `--profile fast`, first attempt.

### What the round 1 report said
v3 was accepted and run. Both twin instances scored pretest 0%, **exam 100%**, using the whole
70-experiment budget; the model-free curve-fitting baseline also scored 100%. The swap test was
clean (A_on_B 0.125, B_on_A 0.0), so the hidden mass really is device-specific and has to be
re-identified — but the in-distribution task itself was too easy and brute-forceable. The one
place both learners broke down was the modification: theory hit rate on `track.size1=0.4` was
0.375 for both. Verdict: above the 30-80% band, need a new hard dimension, not tighter numbers.

### What changed (escalation)
Everything from v3 is reused — table, rail, stand, plunger, steel ball, `coil_stiff` spring,
the spring-rest hand-off, the hidden `ball_mass` — so the world properties the learner fits
transfer. The new mechanism is a **take-off ramp hinged at the far end of the rail**, locked by
its own latch at a third knob `tilt` (0 to 0.5 rad, up only). At tilt 0 its top face is flush
with the rail, so the ball runs straight on; at larger tilt it must run uphill before it flies.

Why this is a different kind of hard rather than a tighter version of the same thing:
- **Sign reversal.** Climbing costs `g*L*sin(theta)/0.7` of `v^2` but buys launch angle and
  height. Hand calculation over the prior corners: with a light ball and a stiff spring, tilting
  to 0.5 rad takes the landing point from 2.14 m to 3.54 m; with a heavy ball and a soft spring
  at the same pull-back it goes from 0.82 m down to 0.57 m. The learner cannot know which way
  the tilt knob points until it has pinned down the hidden mass and the stiffness.
- **A cliff in the action space.** Below a tilt-dependent speed the ball fails to crest the ramp
  and never leaves the device. The corner sweep puts roughly 9% of the action box in that stalled
  region, so part of the budget is spent discovering a boundary rather than fitting a curve.
- **Budget 70 -> 50** while the action space gained a dimension.
- **New modifiable:** `ramp.size1` in [0.13, 0.30] (built 0.13). It moves the launch point, the
  climb loss and the launch height at once, so it cannot be absorbed into a refit constant.

### Sizing
`envelope2.py` is the v4 reach estimator: `E = 0.5 k (s+e)^2 - f (s+e)` with `s = rest - pullback`
and `e = F*drive/k` (the separation point sits `e` past the spring rest, which is what makes the
closed form that simple), then rolling to the rail end, the ramp climb with rolling resistance,
and projectile flight. Over the 2^6 corners of the prior the band reachable in *every* world is
[0.61, 1.66] with a 9% stall rate; the declared goal space [0.75, 1.48] sits inside it with a
margin of about 0.15 at each end (v3's margin was 0.08 and C1 came out 1.0).

Ramp geometry: box half extents [0.06, 0.13, 0.008] at y = 0.33, top face at z = 0.52, hinged on
a `bearing` at the rail's top-far corner (0, 0.20, 0.52) with range (0, 0.55) and held by the
`tilt_lock` latch, which is never released. Tilt is up-only on purpose: when the referee grows
`size1`, the extra length appears *behind* the hinge, and an up-tilt sinks that rear part below
the rail surface instead of raising a step into the ball's path.

### Certification (fast profile)
First run, modifiable [0.13, 0.24]: all green but the modification test was 1.655 against a 1.5
threshold — too close given the real world differs. Widening to [0.13, 0.30] (tested value moves
from 0.218 to 0.266) gave the submitted version:

C0 physics 0.000, timestep 0.205, C1 0.958 (23/24), C1b 0.993, C2 nominal 0.172, C2 fixed action
0.164, C3 modification 2.695, identifiability 0.002, learnability 5/6 (0.833).
`relevant_parameters`: stiffness.coil_stiff, ball_mass, gain.linear_actuator, friction.wood.

### Risks carried into the report
- The gray-box reference learner slipped from 6/6 to 5/6, the first time it has missed anything,
  which is the signal I wanted — but it also means C3 learnability (threshold 0.7) now has only
  one miss of margin. If the real world is unluckier than the drawn one this is the check that
  fails.
- The stall region is deliberate. If the referee reports runs with no landing being scored as
  errors rather than as misses, the tilt range has to be capped so the weakest shot still crests
  the ramp, and the low-end authority has to come from somewhere else.
- `friction.wood` entered the relevant set (the ball now rolls on the wooden ramp as well as the
  rail), so there is one more world property to identify than in v3.

### Next round (planned)
If the exam lands in the band, keep the ramp and add a second *device-specific* unknown that is
not confounded with `ball_mass`: a sealed, spring-loaded flap at the ramp lip that the ball must
push through, whose hidden mass sets an impulse loss that only shows up at the contact. That
breaks the single-energy-balance structure that has carried every version so far. If the exam is
still above 80%, cut the budget to 30 and make the tilt knob continuous over a wider range so the
stall boundary has to be mapped before any fitting can start.

## v5 — `gated_ramp_launcher` (round 3, submitted)

Saved as `designs/v5.py`. Certified on `--profile fast` and submitted.

### What the round 2 report said
v4 was accepted and run. Both twins: pretest 0%, **exam 100%**, budget exhausted, and the
model-free curve-fitting baseline also hit 100%. The swap test was clean (A_on_B 0.0,
B_on_A 0.0), so the hidden mass is genuinely device-specific. The only breakdown was the
modification: theory hit rate on `ramp.size1=0.266` was 0.2 / 0.33. Verdict: still above the
30-80% band, and brute-forceable; prefer changes that need physical understanding.

### What changed (escalation)
Everything from v4 is reused — table, rail, stand, plunger, steel ball, `coil_stiff` spring with
the spring-rest hand-off, the hinged take-off ramp locked at `tilt`, the hidden `ball_mass` — so
all world properties learned so far transfer. The new mechanism is a **sprung gate plate standing
on the ramp lip**, hinged at its base on the ramp with a `torsion_soft` spring at rest 0, and
carrying a *second* device-specific hidden mass (`gate_mass`, sealed aluminium plate).

Why this is a different kind of hard:
- **A second hidden quantity that is not confounded with the first.** `ball_mass` enters as part
  of the launched mass (energy/mass); `gate_mass` enters as a barrier the ball must pay for, i.e.
  as work and impulse *divided by* `ball_mass`. The two appear in different combinations, so they
  cannot be collapsed into one effective parameter the way a sealed carriage mass would.
- **A square root above a threshold.** Exit speed is `sqrt(v_arrive^2 - 2W/m_b)`, so the response
  to every knob is sharply non-linear near the gate's threshold instead of a smooth power law.
- **A second stall boundary.** A shot that reaches the lip too slowly is simply held by the gate
  and never flies — and because the gate rides on the ramp, raising `tilt` leans the gate back and
  moves that boundary, so the two knobs now interact through two separate mechanisms.
- **Two modifiable dimensions** instead of one: `ramp.size1` in [0.13, 0.34] (wide enough that the
  referee can move the gate from the lip into the middle of the ramp) and `gate.size2` in
  [0.005, 0.013], which changes the barrier rather than the flight geometry.
- Budget 50 -> 60 (see below), one extra sensor (`gate_a`).

### Tuning history (five local checks, world draw dominates the variance)
1. Tall heavy gate (half-height 0.010, mass 0.045-0.22, bearing): C1 0.500, **timestep 3.277**,
   learnability 0.333. The plate was being slammed: a violent impact, not a push.
2. Light short gate (0.007, 0.02-0.10), drive capped raised 0.6 -> 0.8, goals [0.80, 1.30]:
   everything green except learnability 0.500 (3/6). Timestep 0.378 — the lighter, more
   spring-dominated gate fixed the impact.
3. Budget 46 / tolerance 0.055: a different world draw, and C1 0.792, timestep 1.715,
   modification 0.73 all failed. Lesson: these three metrics swing by 2-4x across world draws,
   so a single local pass near a threshold means nothing.
4. Budget 60, modifiable ranges widened: only timestep failed, at **1.092**.
5. Shrinking the gate further (0.006, lighter, `bushing` hinge) made timestep *worse* (1.563) and
   killed the gate modification (1.02). A smaller plate makes the ball nearly roll over it — a
   near-singular contact. Taller and spring-dominated is the gentler regime, not smaller.

Final: back to configuration 4 and rescale, since timestep, modification and C1 are all measured
in units of tolerance. Tolerance 0.05 -> 0.06 with the goal band widened 0.50 -> 0.60 keeps the
band at 10 tolerances (so fixed-action coverage does not rise) while moving every borderline
metric the right way at once.

### Certification (fast profile)
C0 physics 0.000, timestep 0.545, C1 0.917 (22/24), C1b 0.944, C2 nominal 0.219 (BORDERLINE,
CI 0.14-0.33), C2 fixed action 0.223, C3 modification 2.57 (ramp 4.99, gate 2.57),
identifiability 0.001 (prior spread 5.64 x tol), learnability 5/6.
`relevant_parameters`: stiffness.coil_stiff, ball_mass, gain.linear_actuator, friction.wood.

### Risks carried into the report
- **C2 nominal is borderline** (0.219, CI straddles 0.3). If the referee rejects on it, the fix is
  to widen the hidden priors or push the goal band further from the prior-centre reach, not to
  touch the gate.
- Tolerance was loosened 0.05 -> 0.06 to buy timestep margin. If the learner comes back above 80%
  again, the first thing to take back is that tolerance, together with the budget (60 -> 40).
- The gray-box learner needed 60 experiments to reach 5/6 (v4 needed 50 for 5/6 on a smaller
  action space), so the structure is measurably harder to fit. Whether that is enough to stop the
  model-free baseline is the open question this round answers.

### Next round (planned, superseded by v6)
If the exam lands in the band, keep the gate and attack the remaining weakness: the outcome is
still a scalar distance from a monotone energy chain. Make the goal two-dimensional by mounting
the ramp on a yaw bearing (a fourth knob setting launch azimuth), so the learner has to model
where the ball goes, not just how far. If the exam is still above 80%, release `tilt_lock` during
the run so the ramp is a dynamic body with its own sealed mass: the ramp angle at the moment the
ball crosses then depends on arrival time, which couples the energy knobs to the launch angle and
defeats any fit that treats tilt as a static setting.

## v6 — `gated_ramp_launcher` (round 4, submitted)

Saved as `designs/v6.py`. Certified on `--profile fast` and submitted with 10 minutes to spare.

### What the round 3 report said
v5 was accepted and run. Instance A: pretest 0%, exam 100%. Instance B: pretest 100%, exam 75%
(tagged `no_improvement_over_pretest`). Average 88%, still above the 30-80% band. Both exhausted
the 60-experiment budget and both failed the modifications (hit rates 0.0-0.67 on
`ramp.size1=0.298` and `gate.size2=0.0118`), and the model-free baseline scored 75%. The swap
test was clean in one direction (A_on_B 0.0) but B_on_A 0.4, so the hidden masses are doing
real work. Three tickets mattered to me:
- `suspected_unsolvable`: the attainable maximum landing distance is materially below the top of
  the declared goal band, i.e. 1.36 was never reachable in the real world (my C1 margin estimate
  was too optimistic again).
- two `ambiguous_spec` tickets: there is no legal way for the learner to *predict* `no_landing`,
  so every deliberately stalled shot costs it a prediction it cannot express. My stall regions
  are therefore partly a protocol tax rather than a physics challenge.

### What I tried and what the certifier said (seven local checks, one per world draw)
The headline lesson of this round: **every borderline metric is world-draw noise of 2-4x**, and
the local check draws a new world each time. Nothing here was a monotone tuning curve.

1. v5 + third hidden (`carriage_mass` 0.08-0.25, sealed plunger) + both ball sensors removed +
   budget 40: everything green except learnability **2/6**.
2. Ball sensors restored, budget 48: learnability **4/6** (0.667, one goal short of 0.7).
3. Budget 60, gate modifiable to 0.016: C1 0.75, timestep 1.03, learnability **3/6**.
4. `carriage_mass` narrowed to 0.08-0.18, tolerance 0.07: C1 0.958, timestep 0.419, learnability
   **1/6**.
   Conclusion after four runs: the third sealed mass is not a tolerable escalation. It is
   genuinely confounded with `ball_mass` through the hand-off speed, and the gray-box reference
   learner lands in the wrong basin and stays there — the posterior predictive was always
   excellent (0.002-0.024 x tol), so the information is in the data, but a single fit at this
   budget cannot find it. Reverted to two hidden masses.
5. Two hidden, `ball_p` dropped, budget 48, tol 0.07: learnability 6/6 and timestep 0.205, but
   both C2 necessity checks failed (nominal 0.312, fixed action 0.301) — 0.07 is simply too
   generous for a 0.5 m band.
6. Tolerance back to 0.06, band [0.72, 1.26]: necessity comfortable again (0.062 / 0.264) but
   timestep 1.585 and the ramp modification collapsed to **0.66**.
7. `drive` capped 0.8 -> 0.7 (gentler gate impact, which is the violent contact that drives
   timestep), goal top trimmed to 1.22, ramp modifiable high 0.34 -> 0.30: timestep 0.399, but
   the ramp modification was still only 1.07.

The ramp-length modification is unreliable *for a physical reason*, not a numerical one: a
longer ramp raises the launch point (further) and costs more climb (nearer), and in some worlds
those two cancel at exactly the value the referee tests. Observed across draws: 2.39, 2.76,
3.23, 0.66, 1.07. So I dropped it and kept `gate.size2`, whose effect has never been below 1.7
(observed 1.71, 2.34, 3.62, 4.09, 4.25, 4.74, 5.12).

### What changed versus v5 (the submitted escalation)
- **Fewer sensors**: `ball_p` is gone. The ball is now only observed through its landing point
  and its velocity; the flight and the gate crossing cannot be watched as a trace.
- **Smaller budget**: 60 -> 54, on the same three-knob action space with two stall boundaries.
- **One modification, and it is the hard one**: `gate.size2` up to 0.016 (v5 stopped at 0.013),
  which is well outside anything the learner can measure on the built device, and there is no
  flight-geometry modification left to fall back on. v5's learners already failed this one at
  0.0118; now it is the only one, and it is bigger.
- **Trimmed goal band**: [0.76, 1.36] -> [0.71, 1.22], which answers the `suspected_unsolvable`
  ticket; the top of v5's band was unreachable in the real world.
- `drive` capped at 0.7 for a gentler gate impact (timestep margin).

### Certification (fast profile)
C0 physics 0.000, timestep 0.893, C1 0.917 (22/24), C1b 0.868, C2 nominal 0.031, C2 fixed action
0.277, C3 modification 5.12 (gate only), identifiability 0.015 (prior spread 12.6 x tol),
learnability 5/6. `relevant_parameters`: stiffness.coil_stiff, ball_mass, gain.linear_actuator,
damping.rail.

### Risks carried into the report
- **Timestep 0.893 against a threshold of 1.0 is the likeliest rejection.** Across this round's
  draws it came out 0.21, 0.40, 0.42, 0.88, 0.89, 1.03, 1.59 — a coin flip in the worst worlds.
  The source is the gate impact. If it is rejected on this, the fix is not rescaling: make the
  gate taller and more spring-dominated (round 3 already showed smaller plates are *worse*,
  because the ball nearly rolls over them, which is a near-singular contact), or cap `drive`
  lower still and buy the lost reach back from the stroke.
- **Fixed-action coverage 0.277 is close to 0.3.** Trimming the goal top to answer the
  unsolvable ticket cost band width, which is what pushed it up.
- This version is a *smaller* escalation than I wanted. Four runs of evidence say a third
  confounded mass breaks the reference learner outright, so the difficulty has to come from
  mechanisms, not parameters.

### Next round (planned)
The structural lesson of rounds 1-4 is that **adding a parameter hurts the gray-box reference
learner (which is given the structure) far more than it hurts the real learner, while adding a
mechanism hurts the real learner more than the reference.** So: no more hidden masses. Build the
two-dimensional outcome instead — mount the ramp on a yaw bearing as a fourth knob and score the
landing point in x and y. Note the trap I must size for: a yawed but untilted plate is still
horizontal, so lateral deflection only exists when `tilt > 0`; the reachable set in (x, y) is a
curved region and a rectangular `goal_space` would put unreachable corners inside the declared
band and fail C1 exactly the way v1 did. Declare a narrow x band, and verify the reachable set
with an envelope script (`envelope3.py`) over the prior corners *before* spending a local check.
