import math


COEFFICIENTS = [
    1.0694770366100346,
    0.016974198115057043,
    -0.1676552469466833,
    -0.16727980695796116,
    0.060072888270420004,
    -0.009826979776201268,
    -0.047679867198475126,
    0.0033022557944300526,
    -0.028744751837628413,
    -0.016049044628342297,
    0.5829731630852081,
    0.2855871900791776,
    0.04919723005789236,
    0.009841279334873778,
    0.0860577498112242,
    0.01908122970880535,
    0.12878280209290308,
    -0.35946771066039457,
    -0.020495187846575908,
    0.04369897837011274,
]


def _reference_outcome(knobs):
    p = (-float(knobs["pullback"]) - 0.22) / 0.10
    drive = (float(knobs["drive"]) - 0.3) / 0.3
    tilt = float(knobs["tilt"]) / 0.5
    terms = []
    for i in range(4):
        for j in range(4 - i):
            for k in range(4 - i - j):
                terms.append(p**i * drive**j * tilt**k)
    return sum(c * x for c, x in zip(COEFFICIENTS, terms))


def _edge(length, tilt):
    # The hinge is at the ramp surface.  The ball centre is one radius along
    # the surface normal when it leaves the far edge.
    y = 0.2 + length * math.cos(tilt) - 0.025 * math.sin(tilt)
    z = 0.52 + length * math.sin(tilt) + 0.025 * math.cos(tilt)
    return y, z


def _landing(speed, length, tilt):
    y, z = _edge(length, tilt)
    vertical = speed * math.sin(tilt)
    flight_time = (vertical + math.sqrt(vertical * vertical + 2.0 * 9.81 * z)) / 9.81
    return y + speed * math.cos(tilt) * flight_time


def _speed_from_landing(outcome, length, tilt):
    edge_y, _ = _edge(length, tilt)
    if outcome <= edge_y:
        return 0.0
    low, high = 0.0, 10.0
    for _ in range(60):
        middle = 0.5 * (low + high)
        if _landing(middle, length, tilt) < outcome:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def predict(knobs: dict, visible: dict) -> list[float]:
    reference = _reference_outcome(knobs)
    half_length = float(visible.get("ramp.size1", 0.13))
    length = 2.0 * half_length
    reference_length = 0.26
    if abs(length - reference_length) < 1e-12:
        return [float(reference)]

    tilt = float(knobs["tilt"])
    reference_speed = _speed_from_landing(reference, reference_length, tilt)
    # Sensor trajectories from the related launcher give an effective
    # wood/steel sliding coefficient near 0.204.  Entrance collision losses
    # are already represented by reference_speed; only work over the changed
    # ramp length is applied here.
    effective_friction = 0.204
    work_per_mass = 2.0 * 9.81 * (
        math.sin(tilt) + effective_friction * math.cos(tilt)
    )
    speed_squared = reference_speed * reference_speed - work_per_mass * (
        length - reference_length
    )
    speed = math.sqrt(max(speed_squared, 0.0))
    return [float(_landing(speed, length, tilt))]
