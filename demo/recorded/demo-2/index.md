# Run `demo-2`

- builder: `llm-builder:cursor-agent:claude-opus-5-thinking-high`; learner: `llm-learner:cursor-agent:gpt-5.6-sol-high`; certification profile: `full`
- isolation audit (canaries): clean

## Timeline

### Round 1: ok
- builder attempt 1: REJECTED - C1 existence: FAIL value=0.292 threshold=0.8. privileged oracle hit 14/48 goals under actuation noise (95% CI 0.18-0.43); some goals are unreachable for parts of the prior, e.g. goals [[1.024], [0.901], [1.21]]. Shrink the goal space, widen the knob ranges, or narrow the hidden priors (12.1 s)
  <details><summary>certificate</summary>

```
REJECTED
C0 construction rules: PASS. all construction checks passed
C0 physics: PASS value=0.000 threshold=0.02. stable for all sampled actions; passive energy gain 0.000% of peak kinetic energy
C1 existence: FAIL value=0.292 threshold=0.8. privileged oracle hit 14/48 goals under actuation noise (95% CI 0.18-0.43); some goals are unreachable for parts of the prior, e.g. goals [[1.024], [0.901], [1.21]]. Shrink the goal space, widen the knob ranges, or narrow the hidden priors
```
</details>
- builder attempt 2: REJECTED - C0 timestep convergence: FAIL value=1.171 threshold=1. halving the timestep moves solving outcomes by 1.17 x tolerance; the solution relies on numerical artefacts (typically violent impacts, tumbling, or near-singular contacts): make the relevant motion gentler (4.7 s)
  <details><summary>certificate</summary>

```
REJECTED
C0 construction rules: PASS. all construction checks passed
C0 physics: PASS value=0.000 threshold=0.02. stable for all sampled actions; passive energy gain 0.000% of peak kinetic energy
C1 existence: PASS value=0.917 threshold=0.8. privileged oracle hit 44/48 goals under actuation noise (95% CI 0.80-0.97)
C0 timestep convergence: FAIL value=1.171 threshold=1. halving the timestep moves solving outcomes by 1.17 x tolerance; the solution relies on numerical artefacts (typically violent impacts, tumbling, or near-singular contacts): make the relevant motion gentler
```
</details>
- builder attempt 3: CERTIFIED (146.4 s)
- device `rail_launcher` (v1); twins A and B studied separately
  - learner A: pretest 0%, exam 100%, experiments 70/70, prediction error first third 0.39 -> last third 0.17 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified track.size1=0.4: 38%
    - belief: damping.rail unit error 0.50, friction.aluminium unit error 0.10 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.rail unit error 0.12 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.11 (covered), rolling.steel unit error 0.17 (covered), stiffness.coil_stiff unit error 0.14 (covered), ball_mass unit error 0.20 (covered)
  - learner B: pretest 0%, exam 100%, experiments 70/70, prediction error first third 0.47 -> last third 0.18 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified track.size1=0.4: 38%
    - belief: damping.rail unit error 0.29 (covered), friction.aluminium unit error 0.10 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.34 (covered), frictionloss.rail unit error 0.12 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.20, rolling.steel unit error 0.57, stiffness.coil_stiff unit error 0.03 (covered), ball_mass unit error 0.25
- swap test (hit rates): {'A_on_A': 1.0, 'B_on_B': 1.0, 'A_on_B': 0.125, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'track.size1': 1.5226566299669142}, 'blackbox_exam_success': 1.0}

### Round 2: ok
- builder attempt 1: CERTIFIED (194.9 s)
- device `ramp_launcher` (v2); twins A and B studied separately
  - learner A: pretest 0%, exam 100%, experiments 50/50, prediction error first third 0.44 -> last third 0.35 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified ramp.size1=0.266: 20%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.43, friction.aluminium unit error 0.10 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.06 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.14 (covered), ball_mass unit error 0.22 (covered)
  - learner B: pretest 0%, exam 100%, experiments 50/50, prediction error first third 0.58 -> last third 0.19 tolerances; theory hit rates in_distribution: 83%, extrapolation: n/a, modified ramp.size1=0.266: 33%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.46, friction.aluminium unit error 0.10 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.29 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.06 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.14 (covered), ball_mass unit error 0.13 (covered)
- swap test (hit rates): {'A_on_A': 1.0, 'B_on_B': 0.8333333333333334, 'A_on_B': 0.0, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'ramp.size1': 3.7537495571335606}, 'blackbox_exam_success': 1.0}

### Round 3: ok
- builder attempt 1: CERTIFIED (245.5 s)
- device `gated_ramp_launcher` (v3); twins A and B studied separately
  - learner A: pretest 0%, exam 100%, experiments 60/60, prediction error first third 0.9 -> last third 0.36 tolerances; theory hit rates in_distribution: 80%, extrapolation: n/a, modified ramp.size1=0.298: 20%, modified gate.size2=0.0118: 0%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.46, friction.aluminium unit error 0.10 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.06 (covered), gain.linear_actuator unit error 0.04 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.12, stiffness.torsion_soft unit error 0.24 (covered), ball_mass unit error 0.49, gate_mass unit error 0.18 (covered)
  - learner B: pretest 100%, exam 75%, experiments 60/60, prediction error first third 0.39 -> last third 0.15 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified ramp.size1=0.298: 67%, modified gate.size2=0.0118: 33%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.43, friction.aluminium unit error 0.17 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.06 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.14 (covered), stiffness.torsion_soft unit error 0.59, ball_mass unit error 0.38 (covered), gate_mass unit error 0.38 (covered)
- swap test (hit rates): {'A_on_A': 0.8, 'B_on_B': 1.0, 'A_on_B': 0.0, 'B_on_A': 0.4}
- controls: {'modification_effect_over_tol': {'ramp.size1': 2.3323730118317676, 'gate.size2': 2.8419999528640068}, 'blackbox_exam_success': 0.75}

### Round 4: ok
- builder attempt 1: CERTIFIED (218.3 s)
- device `gated_ramp_launcher` (v4); twins A and B studied separately
  - learner A: pretest 100%, exam 100%, experiments 54/54, prediction error first third 0.4 -> last third 0.24 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified gate.size2=0.0142: 0%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.43, friction.aluminium unit error 0.14 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.12 (covered), gain.linear_actuator unit error 0.07 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.14, stiffness.torsion_soft unit error 0.24 (covered), ball_mass unit error 0.41, gate_mass unit error 0.21 (covered)
  - learner B: pretest 0%, exam 88%, experiments 54/54, prediction error first third 0.33 -> last third 0.14 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified gate.size2=0.0142: 0%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.38, friction.aluminium unit error 0.17 (covered), friction.concrete unit error 0.03 (covered), friction.steel unit error 0.46 (covered), friction.wood unit error 0.09 (covered), frictionloss.bearing unit error 0.01 (covered), frictionloss.rail unit error 0.06 (covered), gain.linear_actuator unit error 0.03 (covered), rolling.concrete unit error 0.12 (covered), rolling.steel unit error 0.11 (covered), stiffness.coil_stiff unit error 0.14 (covered), stiffness.torsion_soft unit error 0.24 (covered), ball_mass unit error 0.04 (covered), gate_mass unit error 0.04 (covered)
- swap test (hit rates): {'A_on_A': 1.0, 'B_on_B': 1.0, 'A_on_B': 0.0, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'gate.size2': 5.365298761858367}, 'blackbox_exam_success': 1.0}

### Round 5: builder_failed

## Builder sessions

- call 1 (round 1): submitted=True, 17 tool calls, 736 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox and the docs.Docs read. Now writing the device: a latched spring-plunger launcher with a motor-assisted stroke, a sealed-mass ball, and a modifiable rail length.It builds. Running local certification now.Everything passes except the gray-box learnability check (4/6, needs 5/6). I'll give slightly more tolerance and budget, widening the goal space so necessity stays satisfied.Certified, but three margins are thin. Tightening tolerance back a notch and widening the modifiable range to add margin.All checks pass with comfortable margins now. Saving and submitting.Submitted. Now verifying against the stricter `fast` profile in case it reveals a weakness worth fixing before time runs out.Certified under the stricter profile too. Writing the design log now.Round 1 is submitted and certified (also under the stricter `fast` profile).

**What I built** — `rail_launcher`: a latched spring plunger on a rail beside a raised wooden track. Pulling the plunger back compresses a coil spring and drags a steel ball with it; when the drive phase opens the latch, the spring plus a linear actuator throw the plunger forward until it hits its end-stop, handing the ball off to roll down the rail, leave the open end and fly to the floor. The learner picks the pull-back distance and the actuator command to land the ball at a target distance.

**Why it needs experimenting** — launch speed follows `v² ≈ 2c(0.5·k·c + F·drive)/(m_p + m_b)`, where the spring stiffness, the actuator gain, and the ball's sealed mass are all unknown and confounded. Only a learner who sweeps both knobs separately can split `k/M` from `F/M`, since the spring term scales with the stroke squared and the actuator term only linearly. The sealed ball mass is the device-specific unknown, so twin instances must each be identified from scratch.

**Design decision worth noting** — I mounted the plunger on its own ground-standing stand rather than on the track. That decoupling is what makes the rail length safely modifiable: the referee can move `track.size1` from 0.20 up to 0.45 m, which shifts the launch point by up to 0.2 m and simultaneously lengthens the roll, so it interacts with the pull-back knob instead of being a constant offset.

**Sizing** — the knob range had to exceed the spread of the unknowns, or corner worlds would have no reachable goals: `sqrt(k/M)` varies about fourfold across the priors, so the pull-back spans fourfold, and the actuator gives its biggest relative boost exactly in the weak-spring worlds. The pull-back floor is set so even the weakest world still clears the rail rather than stalling partway.

Certification margins: necessity 0.14 and 0.17 against a 0.30 ceiling, fixed-action coverage 0.22, modification effect 3.4 and 1.9 tolerances, gray-box learner 6/6. The main thing I'll watch in the referee's report is whether that 6/6 means the exam lands above the 80% target band — my `design_log.md` records the planned escalation (a latched flap at the rail end giving a second, hidden-mass-bearing launch-angle unknown plus a contact event) rather than merely tightening tolerances.
</details>
- call 2 (round 1): submitted=True, 17 tool calls, 456 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox and the forge docs.31 minutes left. The rejection is C1: the far goals are unreachable in weak worlds. Let me compute the reachable envelope across the priors numerically before editing.Model is well calibrated: it predicts v1's universally-reachable band as [0.63, 0.76] versus a declared goal space of [0.66, 1.25], which matches the referee's 14/48. Now writing v2 with a lighter plunger, longer stroke, and narrower hidden mass.Certified on the strict profile. C2's fixed-action coverage sits at 0.279 against a 0.3 limit, so I'll widen the goal band slightly — that lowers single-action coverage while staying inside the reachable envelope.All checks pass with better margins. Submitting now.Submitted `v2` of `rail_launcher`, certified on the strict `fast` profile.

**What went wrong in v1.** The referee's C1 existence check failed at 0.292 against a 0.8 threshold: the privileged oracle could only reach 14 of 48 goals. The local check had passed because it draws a *single* world, and a typical world does cover the whole goal space — but C1 averages over the prior, so the weak corners (soft spring, weak actuator, heavy ball) decide it.

**How I confirmed it.** Rather than burning 75-second checks on guesses, I wrote a closed-form reach estimator in `envelope.py` (spring plus actuator work over the stroke, minus rail friction and damping, shared by plunger and rolling ball, then roll-out and projectile flight) and swept the corners of the prior. It reproduced v1's failure: the band reachable in *every* world was [0.63, 0.76] while the declared goal space was [0.66, 1.25], so only about 15% of goals were universally reachable — exactly the 14/48 the referee saw.

**The fix** was to buy knob authority that outruns the world spread instead of shrinking the task. I thinned the plunger from 0.175 kg to 0.094 kg so the hidden ball mass dominates the moving mass, lengthened the slide stroke from 0.21 m to 0.30 m (spring energy now spans about 87x across the pullback knob versus the roughly 6x spread of the unknowns), narrowed the hidden mass prior to 0.06–0.3 kg, and moved the goal space to [0.63, 1.08], which sits inside the newly estimated universal band of [0.56, 1.19].

C1 is now 24/24, and the other margins held: necessity 0.11 with prior-centre values, best single action 0.264 against a 0.3 ceiling, modification effect 2.49 tolerances. I deliberately widened the goal band from my first passing attempt at [0.65, 1.05] because its single-action coverage of 0.279 sat too close to the limit; the wider band drops that to 0.264 for only 0.02 of reachability margin at each end.

One thing to watch in the report: gray-box learnability came out 6/6 locally again, and the device is still a single smooth energy balance, so the curve-fitting baseline may crack it unless the referee changes the rail length at exam time. If that's what comes back, the planned v3 adds a latched hinged flap at the rail end — a second hidden mass and a genuine contact event that no smooth range-versus-knob fit can capture.
</details>
- call 3 (round 1): submitted=True, 11 tool calls, 495 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox and the docs.Round 1 was rejected on timestep convergence — the ball separated from the plunger exactly when the plunger slammed its end-stop, so the exit velocity came from an impact. I'll redesign the hand-off so the ball separates smoothly mid-stroke, well before any contact.Certified on the strict `fast` profile with margin everywhere. Saving and submitting.Submitted. Now updating the design log.Submitted and certified. Here's what happened.

**The rejection was a numerics problem, not a design problem.** In v2 the spring's rest point sat at joint coordinate 0, which was also the plunger's forward end-stop. So the plunger accelerated across its entire stroke and the ball left its face at the exact instant the plunger slammed into the stop — the ball's exit velocity was being set by an impact. Halving the timestep moved the landing point by 1.17 tolerances; the limit is 1.

**The fix was to move the hand-off away from the impact.** I set the spring rest back from the stop (`rest=-0.10` on a `(-0.34, 0)` slide). Past the rest point the spring decelerates the plunger, the ball stops being pushed and rolls on alone, so separation is a smooth mid-travel event. The plunger's own arrival at the stop is now gentle, and in stiff worlds it reverses before ever getting there. Convergence dropped to 0.522.

Two sizing changes fall out of guaranteeing the separation always precedes the stop, which requires the motor force to stay below the spring force at the stop: the spring went from `coil_soft` to `coil_stiff` and the `drive` knob is capped at 0.6, and because a stiff spring would otherwise shrink short shots to a sliver of stroke, the hidden `ball_mass` moved up to 0.3–0.9 kg. The hidden mass now dominates the moving mass rather than being masked by the carriage. I also widened the stroke to 0.02–0.22 m and shifted the launcher forward 15 mm so full pullback keeps the ball clear of the rail's back edge.

Certification on the strict `fast` profile has margin on every check: existence 24/24, robustness 96/96, nominal-parameter necessity 0.109, best fixed action 0.238, modification effect 3.45 tolerances, learnability 6/6.

One thing to watch in the referee's report: `relevant_parameters` no longer lists the actuator gain, so `drive` has become a weak second axis. If the learner can ignore it without penalty, the second axis needs to come from real mechanics instead — I've logged a latched flap at the rail end, with its own hidden mass and a locked angle as the second setup knob, as the plan for the next version.
</details>
- call 4 (round 2): submitted=True, 19 tool calls, 718 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox report and the design log.Certified on the first try. The modification effect (1.655 vs 1.5 threshold) is tight, so I'll widen the modifiable range for margin after saving this as a fallback.Better margin on modification (2.69) and the gray-box learner dropped to 5/6 — harder while still certified. Submitting.Submitted. Now updating the design log.**Submitted v4 (`ramp_launcher`), certified on the strict `fast` profile.**

Round 1's report was the problem to solve: both learner instances scored 100% on the exam and so did the model-free curve-fitting baseline, meaning v3's single smooth energy balance could be brute-forced. The one thing both failed was the modification test (0.375).

So v4 keeps the entire v3 launcher — table, rail, plunger, steel ball, stiff coil spring, hidden ball mass — and adds a take-off ramp hinged at the end of the rail, locked by its own latch at a new third knob, `tilt`. Three things make it a different kind of hard rather than a tighter version:

- **The tilt knob changes sign.** Climbing costs speed but buys launch angle and height. For a light ball with a stiff spring, tilting all the way takes the landing point from about 2.1 m out to 3.5 m; for a heavy ball with a soft spring at the same pull-back it pulls the landing point in from 0.82 m to 0.57 m. You cannot know which direction the knob points until you've identified the hidden mass and the stiffness.
- **There's a stall cliff.** Below a tilt-dependent speed the ball fails to crest the ramp and never leaves, so roughly 9% of the action box is a boundary that has to be discovered rather than fitted.
- **Budget cut from 70 to 50** while the action space gained a dimension, and the modifiable dimension is now the ramp length, which moves the launch point, the climb loss and the launch height together.

Certification came back C1 existence 0.958, modification effect 2.695 (I widened the modifiable range from 0.24 to 0.30 after a first run sat at 1.655, uncomfortably near the 1.5 threshold), and gray-box learnability 5/6 — the first time the reference learner has missed anything, which is the signal that the difficulty actually moved. That last number is also the main risk: it now has only one miss of margin against the 0.7 threshold. `design_log.md` has the sizing derivation and the fallback plans; `envelope2.py` is the new reach estimator used to place the goal space inside the universally reachable band.
</details>
- call 5 (round 3): submitted=True, 22 tool calls, 1342 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox report and getting oriented.Now writing v5: adding a sealed knock-over gate at the ramp lip (second hidden quantity, contact impulse loss) plus a budget cut.Gate mechanics work (identifiability jumped to 25× prior spread) but the impact is too violent and reach collapsed. Making the gate light and spring-dominated instead of inertia-dominated.Everything passes except the gray-box learner (3/6, needs 5/6). Raising the budget and tolerance slightly to get it over the line.World draw variance is large. Reverting tolerance, raising budget for learnability margin, and widening both modifiable ranges so their tested values stay consequential.Only timestep convergence is left, and it's marginal (1.09 vs 1.0). Damping the gate hinge and trimming its height to soften the contact.Timestep is world-sensitive and the small gate made the contact marginal. Restoring the stronger-gate candidate and rescaling tolerance/goal band, which moves every borderline metric the right way at once.Certified. Submitting now.Submitted. Now recording the round in the design log.**Round 3 submitted: `gated_ramp_launcher`, certified on the `fast` profile.**

The round 2 report said the learner hit 100% on both twins and the model-free curve-fitting baseline also hit 100%, so v4 was brute-forceable. The escalation I chose adds a **sprung gate plate standing on the ramp lip**, hinged at its base and carrying a second sealed hidden mass. The point of putting the new unknown there is that it is not confounded with the ball's mass: the ball's mass enters as energy divided by launched mass, while the gate's mass enters as work and impulse divided by the ball's mass. Exit speed becomes a square root above a threshold, which also creates a second stall boundary that moves when the tilt knob leans the gate back — so the two knobs now interact through two separate mechanisms rather than one energy balance. Everything else is reused from v4 (table, rail, plunger, steel ball, coil spring, hinged ramp), so the world properties the learner has already fitted still transfer.

Getting it certified took five local checks, and the useful lesson was counterintuitive: my first instinct was that a smaller gate would be a gentler contact, but shrinking it made timestep convergence *worse*, because the ball then nearly rolls over the plate and the contact goes near-singular. The gentle regime is a taller, lighter, spring-dominated plate that gets pushed rather than slammed. The other thing worth recording is that C1 existence, timestep convergence and the modification test all swing by a factor of two to four between world draws, so the final fix was to raise tolerance from 0.05 to 0.06 while widening the goal band proportionally, which keeps the band at ten tolerances and buys margin on every borderline metric at once.

Final numbers: timestep 0.545, C1 0.917, C1b 0.944, fixed-action 0.223, modification 2.57, identifiability 0.001 against a prior spread of 5.6 tolerances, gray-box learner 5/6.

Two risks I logged for next round. **C2 necessity on nominal parameters is flagged borderline** at 0.219 with a confidence interval straddling the 0.3 threshold, so the referee could reject on it; the fix there is widening the hidden priors, not touching the gate. And I loosened tolerance to 0.06 to buy the timestep margin, so if the exam comes back above 80% again, that tolerance and the budget are the first things to claw back.
</details>
- call 6 (round 4): submitted=True, 33 tool calls, 1356 s
  <details><summary>builder's final message</summary>

I'll start by reading the inbox report and getting oriented.Report read: learner hit 88%, above the band. I'll escalate with more unknowns, fewer sensors and a smaller budget, and trim the unreachable top of the goal band flagged by the `suspected_unsolvable` ticket.Now the task block: trimmed goal band, smaller budget, new escalation text.Learnability came in at 2/6 — removing the ball sensors on top of the extra unknown overshot. Restoring the ball instrumentation and giving back some budget.Learnability is one goal short (4/6, needs 5/6). Giving the reference learner the full budget back and widening the gate modification range for margin.Unlucky draw hit three checks at once. Narrowing the new unknown's prior and loosening tolerance slightly — the log shows these three metrics all scale with tolerance, and modification now has margin to spare.Four runs show the third hidden mass consistently breaks the reference learner's fit. Reverting it and taking the escalation from budget, sensors, and the modification range instead.Learnability recovered to 6/6; now the necessity checks are borderline because tolerance 0.07 is too generous. Tightening back to 0.06 with a slightly wider band.Each world draw trips a different borderline check. Making the gate impact gentler (lower drive cap) to attack the timestep risk at its source, and pulling the ramp modification test to a less cancellation-prone value.Dropping the ramp-length modification (it cancels between climb loss and launch height in some worlds) and keeping the reliably consequential gate dimension.Certified. Submitting now before the clock runs out.Submitted. Now the design log.**v6 is certified and submitted** (`outbox/submission.json`, saved as `designs/v6.py`), with the design log updated.

The round-3 report put the learner at 88%, above the band, so this version had to get harder. What I actually shipped is a smaller escalation than I planned, and the reason is the most useful thing I learned this round.

I first tried the obvious move — a third device-specific hidden mass, sealing the plunger carriage — and ran it four times across four world draws. The gray-box reference learner scored 2/6, 4/6, 3/6, 1/6 against a 5/6 bar, while the posterior-predictive check stayed excellent (0.002–0.024 × tolerance). The information is in the data; a single fit at this budget just can't find it because the carriage mass and the ball mass are confounded through the hand-off speed. Adding a parameter punishes the reference learner (which is handed the structure) much more than it punishes the real learner, so it fails certification before it ever reaches the exam.

So the escalation comes from mechanisms and interface instead: the ball's position trace is removed (only its velocity and landing point remain), the budget drops from 60 to 54, and `gate.size2` is now the single announced modification with a range extended to 0.016 — the one both v5 learners already failed, with no flight-geometry modification left to fall back on. I also dropped the ramp-length modification: across draws its effect measured 2.39, 2.76, 3.23, 0.66, 1.07, because a longer ramp raises the launch point and costs climb speed, and in some worlds those cancel right where the referee tests. The goal band is trimmed to [0.71, 1.22], which answers the referee's `suspected_unsolvable` ticket — v5's top really was unreachable.

The one risk I'd flag: timestep convergence passed at 0.893 against a threshold of 1.0, and across this round's draws it ranged from 0.21 to 1.59. That's the likeliest rejection, and the fix is a gentler gate contact rather than rescaling the tolerance.
</details>
- call 7 (round 5): submitted=False, 32 tool calls, 4123 s

## Learner sessions (main lineage)

- v1_main_s1: final phase done, 116 lab calls (0 rejected), 410 s
- v2_main_s2: final phase done, 92 lab calls (0 rejected), 384 s
- v3_main_s3: final phase done, 109 lab calls (3 rejected), 316 s
- v4_main_s4: final phase done, 94 lab calls (3 rejected), 282 s

## Figures

![prediction_error](figures/prediction_error.png)
![success](figures/success.png)

## Replays (instance A, re-simulated without actuation noise)

![r1_device](replays/r1_device.png)
![r1_lab0](replays/r1_lab0.gif)
![r1_exam_hit](replays/r1_exam_hit.gif)
![r2_device](replays/r2_device.png)
![r2_lab0](replays/r2_lab0.gif)
![r2_exam_hit](replays/r2_exam_hit.gif)
![r3_device](replays/r3_device.png)
![r3_lab0](replays/r3_lab0.gif)
![r3_exam_hit](replays/r3_exam_hit.gif)
![r4_device](replays/r4_device.png)
![r4_lab0](replays/r4_lab0.gif)
![r4_exam_hit](replays/r4_exam_hit.gif)

## World values (revealed after the run)

```json
{
 "damping.bearing": 0.01318,
 "damping.bushing": 0.02035,
 "damping.rail": 0.24757,
 "friction.aluminium": 0.41051,
 "friction.concrete": 0.66508,
 "friction.rubber": 1.07644,
 "friction.steel": 0.16285,
 "friction.wood": 0.58519,
 "frictionloss.bearing": 0.00204,
 "frictionloss.bushing": 0.02307,
 "frictionloss.rail": 0.28352,
 "gain.linear_actuator": 5.21372,
 "gain.motor_large": 3.12615,
 "gain.motor_small": 0.51743,
 "rolling.aluminium": 0.00035,
 "rolling.concrete": 0.00063,
 "rolling.rubber": 0.00086,
 "rolling.steel": 0.00064,
 "rolling.wood": 0.00064,
 "stiffness.coil_soft": 47.22585,
 "stiffness.coil_stiff": 282.33184,
 "stiffness.torsion_soft": 2.30015,
 "stiffness.torsion_stiff": 4.63614
}
```

Raw material: `public/` (hash-chained channel log, task cards, round reports), `builder/` (design log and submitted designs), `learner/` (notebooks and theories).
