import numpy as np


G = 9.81
COEF = np.array(
    [
        0.7762651649044153,
        -0.133639842668496,
        -0.20409582116372463,
        0.016891253536170398,
        -0.020580034473488676,
        0.012263282182600881,
        0.4696461009761283,
        -0.23956568670658854,
        0.04216384989805104,
        0.22272248372419207,
    ]
)


def _geometry(tilt):
    # Ball-centre position at the ramp lip, measured relative to first floor contact.
    y0 = 0.2 + 0.26 * np.cos(tilt) - 0.025 * np.sin(tilt)
    h = 0.52 + 0.26 * np.sin(tilt) + 0.025 * (np.cos(tilt) - 1.0)
    return y0, h


def _landing(v, tilt):
    y0, h = _geometry(tilt)
    vz = v * np.sin(tilt)
    flight_time = (vz + np.sqrt(max(0.0, vz * vz + 2.0 * G * h))) / G
    return y0 + v * np.cos(tilt) * flight_time


def _speed_from_landing(distance, tilt):
    lo, hi = 0.0, 10.0
    for _ in range(55):
        mid = 0.5 * (lo + hi)
        if _landing(mid, tilt) < distance:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def predict(knobs: dict, visible: dict) -> list[float]:
    pullback = float(knobs["pullback"])
    drive = float(knobs["drive"])
    tilt = float(knobs["tilt"])

    x = (-pullback - 0.22) / 0.10
    d = (drive - 0.35) / 0.35
    z = tilt / 0.5
    features = np.array(
        [1.0, z, z * z, d, d * z, d * d, x, x * z, x * d, x * x]
    )
    standard_distance = float(features @ COEF)

    # The fit is for the 7 mm gate half-height. Convert its predicted distance to
    # lip speed, then account for the extra geometric work of clearing a taller gate.
    speed = _speed_from_landing(standard_distance, tilt)
    gate_half_height = float(visible.get("gate.size2", 0.007))
    speed_sq = speed * speed - 4.0 * G * (gate_half_height - 0.007)
    adjusted_speed = np.sqrt(max(0.0, speed_sq))
    return [float(_landing(adjusted_speed, tilt))]
import numpy as np


_EXPONENTS = np.array([
    [0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 1, 0],
    [0, 1, 1], [0, 2, 0], [1, 0, 0], [1, 0, 1],
    [1, 1, 0], [2, 0, 0],
], dtype=int)

_COEFFICIENTS = np.array([
    0.7830091795805936, -0.17157263732568676,
    -0.24032955524300373, 0.03602335868256039,
    -0.012133366661514922, -0.0034817837653475484,
    0.4916890816687676, -0.1380722146410425,
    0.04370889642706358, 0.18616243388116074,
])


def predict(knobs: dict, visible: dict) -> list[float]:
    pullback = float(knobs["pullback"])
    drive = float(knobs["drive"])
    tilt = float(knobs["tilt"])
    half_length = float(visible.get("ramp.size1", 0.13))
    gate_half_height = float(visible.get("gate.size2", 0.007))

    # A ridge-regularized quadratic response surface fit to the 57 successful
    # launches at the reference dimensions.
    scaled = np.array([
        (-pullback - 0.22) / 0.1,
        (drive - 0.4) / 0.4,
        tilt / 0.5,
    ])
    features = np.prod(scaled[np.newaxis, :] ** _EXPONENTS, axis=1)
    reference_outcome = float(features @ _COEFFICIENTS)

    # Convert the fitted reference outcome into launch speed using projectile
    # motion, then apply dimension changes through an energy balance.
    reference_edge = 0.2 + 0.26 * np.cos(tilt)
    reference_height = 0.52 + 0.26 * np.sin(tilt)
    reference_range = max(0.001, reference_outcome - reference_edge)
    speed_sq = (
        9.81 * reference_range * reference_range
        / (
            2.0 * np.cos(tilt) ** 2
            * (reference_height + reference_range * np.tan(tilt))
        )
    )

    # A longer ramp consumes gravitational and rolling energy. A taller gate
    # raises the ball's centre while it crosses the plate.
    delta_length = half_length - 0.13
    speed_sq = (
        speed_sq
        - 4.0 * 9.81 * delta_length * np.sin(tilt)
        - 1.0 * delta_length
        - 4.0 * 9.81 * (gate_half_height - 0.007)
    )
    speed = np.sqrt(max(0.0, float(speed_sq)))

    edge_y = 0.2 + 2.0 * half_length * np.cos(tilt)
    flight_height = 0.52 + 2.0 * half_length * np.sin(tilt)
    vertical_speed = speed * np.sin(tilt)
    flight_time = (
        vertical_speed
        + np.sqrt(vertical_speed * vertical_speed + 2.0 * 9.81 * flight_height)
    ) / 9.81
    outcome = edge_y + speed * np.cos(tilt) * flight_time
    return [float(outcome)]
