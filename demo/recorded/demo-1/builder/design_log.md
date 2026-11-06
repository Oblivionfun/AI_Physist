# Design log

## v3 — `wide_mass_catapult` (round 3, submitted)

Saved as `designs/v3.py`; the intermediate certified variant is `designs/v3_fallback.py`.

### What the round-2 report said
Learner exam 100% on both instances (band is 30-80%) and the model-free baseline hit 75%,
so v2 was too easy and partly brute-forceable. Swap test was clean (A_on_B = B_on_A = 0),
and the modification tests were already hard (0.0 on `stop_post.posx`), so the hiddens and
the modifiables were doing their job. Asked for a new hard dimension.

### What I tried, and what the gray-box learner would not accept
Two genuinely new mechanics were built, certified on everything except C3 learnability,
and had to be abandoned with the clock running:
1. **Releasing slug.** The clamp opens mid-throw (`dwell` as a fourth knob), so the slug
   runs along the rail under centrifugal load and the arm inertia changes *during* the
   swing, with a piecewise boundary where the dwell outlasts the swing. Physics was clean:
   C1 24/24, C1b 192/192, C2 nominal 0.172, posterior predictive 0.001 x tol. The gray-box
   reference learner scored 1/6 at budget 46 and **0/6 at budget 72** — more budget made it
   worse, so budget was not the constraint.
2. **Burst-and-coast drive.** Motor held for a `burst` of chosen length, then switched off
   so the torsion spring finishes the throw: path-dependent energy, no new contacts.
   Reference learner 1/6 at budget 56.
The common factor in both is a **knob that sets a phase duration**. `PhaseIR.duration`
accepts a knob reference, but the reference learner apparently cannot fit a model whose
phase lengths move. Avoid duration knobs until the report says otherwise.

### The decisive observation
The C3 learnability statistic is 6 trials and is **dominated by seed noise**. The identical
structure scored 6/6 (tol 0.055, budget 68) and 1/6 (tol 0.050, budget 76) on two draws;
0.048/64 gave 4/6 while the looser 0.052/64 gave 1/6. Any single check is weak evidence
about C3, so chasing it by tuning tolerance or budget is mostly chasing noise. Widening
both hidden masses to a decade each also pushed average reference success down (3/6, 1/6,
1/6, 6/6 across draws) while C2 nominal improved to 0.094; I kept the v2 ranges in the end.

### What actually shipped
v2's mechanism unchanged (tower, sprung hinge, clamped slug on the rail, striker, stop
post, sealed ball), so world knowledge transfers, plus:
- Tolerance 0.055 -> **0.048** on a landing point: the real escalation.
- Modifiables widened: `stop_post.posx` [-0.080, -0.030] (was [-0.070, -0.034]) and
  `striker.posz` [0.684, 0.736] (was [0.690, 0.730]). Both stay valid: the post sits at
  y 0.13-0.19, clear of the arm/cup/ball at y <= 0.122, so only the striker can reach it.
- Added a `slug_where` joint sensor (the slug is clamped, so it mostly confirms the setup).
- Goal span trimmed to [-1.52, -1.02]. The oracle was missing 1-2 goals at the far end and
  the reference learner was missing the same ones; trimming took the oracle to 24/24 and
  the learner to 5/6, at the price of fixed-action coverage 0.174 -> 0.232 (cap 0.3). This
  was the one change that raised C3 for a reason rather than by luck.

### Final local certification
CERTIFIED. Oracle 24/24, neighbours 135/144, nominal necessity 0.094, fixed action 0.232,
posterior predictive 0.001 x tol (prior spread 6.5 x), gray-box learner 5/6.

### Next version
1. The escalation shipped here is thin (tolerance plus modifiable range). If the report
   again says too easy, the next real step is a new mechanism that is *not* a duration
   knob: a second actuator (`linear_actuator` on the slug rail) driven by a constant
   command over the existing fixed phase, so the inertia changes during the swing without
   any phase length moving.
2. A sealed counterweight below the hinge (a third hidden) to decouple the inertia from the
   gravity torque; needs the arm extended below the pivot, clear of the column at y=0.1.
3. Two-dimensional outcome (landing x and max height) to force a real trajectory model.
4. Budget cuts are not a reliable lever: the reference learner's score barely tracks it.

## v2 — `spring_stop_catapult` (round 2, submitted)

Saved as `designs/v2.py`.

### What the round-1 report said
Learner exam 88% (target band 30-80%), and a model-free curve-fitting baseline also hit
100%: v1 could be brute-forced. The report asked for more knobs, a smaller budget and
consequential modifiable dimensions. The swap test was already clean (A_on_B = 0), so the
device-specific hiddens were doing their job.

### What changed
Same tower, arm, cup, striker and stop post as v1, so world knowledge transfers. New:
- A `torsion_soft` spring on the hinge with `rest=-0.6`, later softened to `rest=-0.3`.
  Spring work and motor work now both drive the throw and have to be separated by designed
  experiments (vary `cock` at fixed `power` and vice versa). Both `stiffness.torsion_soft`
  and `gain.motor_large` show up in `relevant_parameters`.
- The sealed slug moved from a fixed mount onto a `rail` slide along the arm, clamped by a
  latch that is never released. Its clamp position is a third knob, `shift`, so the two
  sealed masses no longer collapse into one multiplier: `shift` moves the inertia while
  leaving the ball's kinetic-energy share alone.
- Dropped the ball velocity sensor (joint angle, joint rate and ball position remain).
- Budget 80 -> 62.
- Second modifiable is now `striker.posz` (it sets the arm angle at which the striker meets
  the post, hence the launch elevation) alongside v1's `stop_post.posx`.

### Iteration notes
- My local sweep harness appeared to show the outcome was independent of motor gain and
  spring stiffness. That was a harness bug, not physics: `forge check`'s
  `relevant_parameters` lists both. Trust the certification stats over hand-rolled sweeps.
- `rest=-0.6` made the spring strongly relevant but pushed C2 nominal necessity from 0.047
  to 0.17 and left the oracle at 21/24. `rest=-0.3` keeps the spring relevant with far
  better margins.
- Budget 50 failed C3 learnability (4/6). 62 restores it.
- Narrowing the goal span to [-1.46, -1.02] *failed* C1: the unreachable goals were in the
  middle of the span, not at the edges, so shrinking did not help. Extending the far end
  instead ([-1.62, -1.02]) fixed everything at once - a wider span also cuts the
  fixed-action coverage, which had crept up to 0.27 against the 0.3 cap.
- C1/C2 vary a lot between check seeds (oracle 1.00 / 0.875 / 0.708 on three draws), so
  margin matters more than a single pass.

### Final local certification
Oracle 24/24, neighbours 144/144, nominal necessity 0.109, fixed action 0.219, posterior
predictive 0.003 x tol (prior spread 8.1 x tol), gray-box learner 6/6.

### Next version (ideas, in escalation order)
1. Two-phase motor command (`power_a` for a short first phase, `power_b` after), making the
   energy integral path-dependent so a static formula no longer suffices.
2. Release the slug latch mid-throw so the slug slides under centrifugal load: genuine
   stick-slip on the rail, with `frictionloss.rail` entering the throw.
3. A second actuator (`linear_actuator` on the slug rail) changing inertia during the throw.
4. Two-dimensional outcome to force a real trajectory model.
5. Tolerance back towards 0.05 once the mechanics carry the difficulty.

## v1 — `stop_catapult` (round 1, submitted)

Saved as `designs/v1.py`.

### What it is
A motor-driven catapult arm on a concrete column. A hinge (`bearing`) at the top of the
column carries a wooden arm; at the tip sits a shallow cup with a single retaining lip on
the `+x` side, and a sealed steel ball rests in it (`carried_by` the cup, so it stays put
while the arm is cocked). A sealed slug is clamped to the arm part-way out. A striker plate
offset in `+y` sticks out of the arm and is the only part that can meet the concrete stop
post, which is offset in `+y` as well so it never blocks the ball's flight path.

Sequence: the arm is cocked to `cock` radians (towards `+x`, away from the post), the motor
holds command `power` (negative = towards the post) for 2 s, the striker slams the post, the
arm stops dead, and the ball leaves the cup over its open `-x` side as a projectile. The
outcome is the ball's landing x.

### Why it needs experimenting
Launch speed is set by `gain.motor_large * power * (cock + stop_angle)` minus the climb of
the centre of mass, divided by the arm's moment of inertia — and the inertia contains two
device-specific hidden masses (`ball_mass`, `slug_mass`) plus the ball mass again in the
kinetic-energy budget. The motor gain spans 4x over the prior, so prior-centre parameters
land far outside tolerance (C2 nominal 16%).

Hidden: `ball_mass`, `slug_mass`. Modifiable: `stop_post.posx` (sets the stop angle, hence
the launch elevation — a big outcome lever) and `slug.posz` (sets the slug's radius, hence
the inertia).

### Iteration notes
- `b.hidden()` returns a log string, not a handle: pass the hidden's *name* to `hidden_mass`.
- Positive motor command drives the hinge coordinate positive, i.e. *away* from the post, so
  the `power` knob is declared negative. Caught by a direct sweep (`sweep.py`), not by check.
- The device is far more energetic than hand estimates suggested; I used `sweep.py` over
  weak/heavy and strong/light corners of the prior to find the landing window that is
  reachable in *every* world: roughly x in [-1.06, -1.57]. The goal space sits inside it.
- C3 learnability failed repeatedly (0/6) with budget 40 and only joint sensors. Adding ball
  velocity + position sensors and raising the budget to 80 fixed it. Tolerance is the knife
  edge between C2 and C3: 0.05 -> learner 3/6 (fail); 0.055 with a 0.50 m goal span ->
  learner 6/6 and fixed-action coverage 25%.

### Final local certification
All checks pass: oracle 23/24, neighbours 93%, nominal 15.6%, fixed action 24.8%,
posterior predictive 0.001 x tol, gray-box learner 6/6.

### Next version (ideas, in escalation order)
1. Latch the slug on a slide along the arm and make its setup position a third knob: the
   inertia then interacts with the motor work, so the two hidden masses stop being a single
   multiplier.
2. Add a torsion spring on the hinge, so spring energy and motor work confound and must be
   separated by designed experiments (vary `cock` at fixed `power` and vice versa).
3. Reduce sensors back to joint-only once the mechanics give a cleaner signal, and/or cut
   the budget back towards 40.
4. Two-dimensional outcome (landing x and max height) to force a real trajectory model.
