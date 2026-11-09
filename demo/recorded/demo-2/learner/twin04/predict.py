import numpy as np


# Ridge-regularized response surface fit to this device's successful launches.
# Pullback is scaled so the well-sampled interval [-0.32, -0.22] maps to [1, 0].
_COEF = np.array([
    0.6380462841458807,
    0.3373425720654305,
    0.03962841701438244,
    -0.37696806168100094,
    0.11463220933802373,
    0.016345025540446246,
    -0.3462509087163074,
    0.07153464307655413,
    -0.23420255630522144,
    -0.16091255194678164,
    -0.18989341195248893,
])


def predict(knobs: dict, visible: dict) -> list[float]:
    pullback = float(knobs["pullback"])
    drive = float(knobs["drive"])
    tilt = float(knobs["tilt"])
    x = (-pullback - 0.22) / 0.1

    features = np.array([
        1.0,
        x,
        drive,
        tilt,
        x * x,
        drive * drive,
        tilt * tilt,
        x * drive,
        x * tilt,
        drive * tilt,
        tilt * tilt * tilt,
    ])
    reference_distance = float(features @ _COEF)

    # Convert the reference landing point to lip speed, apply the energy cost
    # of a changed gate half-height, and project the adjusted shot.
    g = 9.81
    edge_y = 0.2 + 0.26 * np.cos(tilt)
    edge_z = 0.52 + 0.26 * np.sin(tilt)
    horizontal_range = max(reference_distance - edge_y, 0.005)
    denominator = max(
        np.cos(tilt) ** 2
        * (edge_z + horizontal_range * np.tan(tilt)),
        1e-6,
    )
    speed_sq = 0.5 * g * horizontal_range**2 / denominator

    gate_half_height = float(visible.get("gate.size2", 0.007))
    speed_sq -= 4.0 * g * (gate_half_height - 0.007)
    speed = np.sqrt(max(speed_sq, 0.0))

    flight_time = (
        speed * np.sin(tilt)
        + np.sqrt((speed * np.sin(tilt)) ** 2 + 2.0 * g * edge_z)
    ) / g
    distance = edge_y + speed * np.cos(tilt) * flight_time
    return [float(distance)]
