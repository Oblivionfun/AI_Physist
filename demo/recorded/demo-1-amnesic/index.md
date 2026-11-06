# Run `demo-1-amnesic`

- builder: `recorded:demo-1`; learner: `llm-learner:cursor-agent:gpt-5.6-sol-high`; certification profile: `full`
- isolation audit (canaries): clean

## Timeline

### Round 1: ok
- builder attempt 1: CERTIFIED (0.0 s)
- device `stop_catapult` (v1); twins A and B studied separately
  - learner A: pretest 0%, exam 100%, experiments 80/80, prediction error first third 1.58 -> last third 0.44 tolerances; theory hit rates in_distribution: 100%, extrapolation: n/a, modified stop_post.posx=-0.064: 38%, modified slug.posz=0.734: 0%
    - belief: damping.bearing unit error 0.22 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44 (covered), friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.45 (covered), gain.motor_large unit error 0.41 (covered), rolling.concrete unit error 0.21 (covered), rolling.steel unit error 0.71, ball_mass unit error 0.34 (covered), slug_mass unit error 0.42 (covered)
  - learner B: pretest 0%, exam 100%, experiments 80/80, prediction error first third 5.05 -> last third 0.58 tolerances; theory hit rates in_distribution: 88%, extrapolation: n/a, modified stop_post.posx=-0.064: 50%, modified slug.posz=0.734: 75%
    - belief: damping.bearing unit error 0.25 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44, friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.44 (covered), gain.motor_large unit error 0.07 (covered), rolling.concrete unit error 0.05 (covered), rolling.steel unit error 0.40, ball_mass unit error 0.06 (covered), slug_mass unit error 0.08 (covered)
- swap test (hit rates): {'A_on_A': 1.0, 'B_on_B': 0.875, 'A_on_B': 0.0, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'stop_post.posx': 3.198663514581333, 'slug.posz': 2.46244834474315}, 'blackbox_exam_success': 1.0}

### Round 2: ok
- builder attempt 1: CERTIFIED (0.0 s)
- device `spring_stop_catapult` (v2); twins A and B studied separately
  - learner A: pretest 33%, exam 88%, experiments 62/62, prediction error first third 0.86 -> last third 3.09 tolerances; theory hit rates in_distribution: 75%, extrapolation: n/a, modified stop_post.posx=-0.064: 0%, modified striker.posz=0.726: 100%
    - belief: damping.bearing unit error 0.40 (covered), damping.rail unit error 0.00 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44, friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.59 (covered), frictionloss.rail unit error 0.14 (covered), gain.motor_large unit error 0.61, rolling.concrete unit error 0.18 (covered), rolling.steel unit error 0.68, stiffness.torsion_soft unit error 0.60, ball_mass unit error 0.18 (covered), slug_mass unit error 0.29 (covered)
  - learner B: pretest 0%, exam 100%, experiments 62/62, prediction error first third 8.25 -> last third 2.77 tolerances; theory hit rates in_distribution: 50%, extrapolation: n/a, modified stop_post.posx=-0.064: 0%, modified striker.posz=0.726: 38%
    - belief: damping.bearing unit error 0.25 (covered), damping.rail unit error 0.00 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44 (covered), friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.40 (covered), frictionloss.rail unit error 0.14 (covered), gain.motor_large unit error 0.27 (covered), rolling.concrete unit error 0.18 (covered), rolling.steel unit error 0.68 (covered), stiffness.torsion_soft unit error 0.18 (covered), ball_mass unit error 0.26 (covered), slug_mass unit error 0.25 (covered)
- swap test (hit rates): {'A_on_A': 0.75, 'B_on_B': 0.5, 'A_on_B': 0.0, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'stop_post.posx': 1.8010099386518996, 'striker.posz': 0.6302546945812186}, 'blackbox_exam_success': 0.75}

### Round 3: ok
- builder attempt 1: CERTIFIED (0.0 s)
- device `wide_mass_catapult` (v3); twins A and B studied separately
  - learner A: pretest 0%, exam 100%, experiments 62/62, prediction error first third 2.35 -> last third 8.95 tolerances; theory hit rates in_distribution: 62%, extrapolation: n/a, modified stop_post.posx=-0.072: 0%, modified striker.posz=0.7308: 38%
    - belief: damping.bearing unit error 0.60, damping.rail unit error 0.00 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44 (covered), friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.15 (covered), frictionloss.rail unit error 0.13 (covered), gain.motor_large unit error 0.52, rolling.concrete unit error 0.21 (covered), rolling.steel unit error 0.71, stiffness.torsion_soft unit error 0.48, ball_mass unit error 0.22 (covered), slug_mass unit error 0.32
  - learner B: pretest 0%, exam 100%, experiments 62/62, prediction error first third 4.93 -> last third 2.74 tolerances; theory hit rates in_distribution: 75%, extrapolation: n/a, modified stop_post.posx=-0.072: 38%, modified striker.posz=0.7308: 38%
    - belief: damping.bearing unit error 0.05 (covered), damping.rail unit error 0.00 (covered), friction.concrete unit error 0.08 (covered), friction.steel unit error 0.44, friction.wood unit error 0.32 (covered), frictionloss.bearing unit error 0.59 (covered), frictionloss.rail unit error 0.14 (covered), gain.motor_large unit error 0.62, rolling.concrete unit error 0.21 (covered), rolling.steel unit error 0.71, stiffness.torsion_soft unit error 0.36 (covered), ball_mass unit error 0.50 (covered), slug_mass unit error 0.59
- swap test (hit rates): {'A_on_A': 0.625, 'B_on_B': 0.75, 'A_on_B': 0.0, 'B_on_A': 0.0}
- controls: {'modification_effect_over_tol': {'stop_post.posx': 0.0, 'striker.posz': 1.7185414117823021}, 'blackbox_exam_success': 0.625}


## Learner sessions (main lineage)

- v1_main_s1: final phase done, 182 lab calls (0 rejected), 1188 s
- v2_main_s2: final phase done, 152 lab calls (1 rejected), 325 s
- v3_main_s3: final phase done, 152 lab calls (0 rejected), 367 s

## Figures

![prediction_error](figures/prediction_error.png)
![success](figures/success.png)

## Replays (instance A, re-simulated without actuation noise)

![r1_device](replays/r1_device.png)
![r1_lab0](replays/r1_lab0.gif)
![r1_exam_hit](replays/r1_exam_hit.gif)
![r2_device](replays/r2_device.png)
![r2_lab0](replays/r2_lab0.gif)
![r2_exam_miss](replays/r2_exam_miss.gif)
![r2_exam_hit](replays/r2_exam_hit.gif)
![r3_device](replays/r3_device.png)
![r3_lab0](replays/r3_lab0.gif)
![r3_exam_hit](replays/r3_exam_hit.gif)

## World values (revealed after the run)

```json
{
 "damping.bearing": 0.01337,
 "damping.bushing": 0.02896,
 "damping.rail": 0.4491,
 "friction.aluminium": 0.24396,
 "friction.concrete": 0.61149,
 "friction.rubber": 0.98882,
 "friction.steel": 0.167,
 "friction.wood": 0.57757,
 "frictionloss.bearing": 0.00087,
 "frictionloss.bushing": 0.01572,
 "frictionloss.rail": 0.29568,
 "gain.linear_actuator": 7.24935,
 "gain.motor_large": 5.59889,
 "gain.motor_small": 1.12916,
 "rolling.aluminium": 0.00025,
 "rolling.concrete": 0.00056,
 "rolling.rubber": 0.00077,
 "rolling.steel": 0.0002,
 "rolling.wood": 0.00049,
 "stiffness.coil_soft": 94.03997,
 "stiffness.coil_stiff": 357.84994,
 "stiffness.torsion_soft": 1.58721,
 "stiffness.torsion_stiff": 7.38532
}
```

Raw material: `public/` (hash-chained channel log, task cards, round reports), `builder/` (design log and submitted designs), `learner/` (notebooks and theories).
