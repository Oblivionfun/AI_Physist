import numpy as np


def predict(knobs: dict, visible: dict) -> list[float]:
    """Predict the ball's first ground-contact y coordinate."""
    pullback = float(knobs["pullback"])
    drive = float(knobs["drive"])
    tilt = float(knobs["tilt"])

    # Cubic ridge fit to 56 successful launches at the reference geometry.
    x = (-pullback - 0.22) / 0.10
    d = drive / 0.8
    t = tilt / 0.5
    powers = (
        (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
        (0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1),
        (1, 1, 0), (2, 0, 0), (0, 0, 3), (0, 1, 2),
        (0, 2, 1), (0, 3, 0), (1, 0, 2), (1, 1, 1),
        (1, 2, 0), (2, 0, 1), (2, 1, 0), (3, 0, 0),
    )
    coef = np.array([
        0.6435172042248398, -0.14434992260438087,
        0.017218923919949093, 0.2841263307069868,
        -0.13385886546534617, -0.2785282517133974,
        0.13168793776528231, -0.12402189016550574,
        0.1394251848327429, 0.2192998281832156,
        0.35509810285252935, 0.022723390872720572,
        0.08876722996468789, -0.09978286931451741,
        -0.6375213983372167, 0.2165159659192869,
        -0.01941545626282094, 0.19913258126248617,
        -0.11493035253959162, -0.04362020654668647,
    ])
    y_ref = float(sum(c * x**a * d**b * t**c3
                      for c, (a, b, c3) in zip(coef, powers)))
    y_ref = float(np.clip(y_ref, 0.43, 1.20))

    # Convert the reference range to post-gate speed, then propagate over a
    # changed ramp length by energy before applying projectile motion.
    g = 9.81
    radius = 0.025
    l_ref = 0.13
    length = float(visible.get("ramp.size1", l_ref))
    y0_ref = 0.2 + 2.0 * l_ref * np.cos(tilt) - radius * np.sin(tilt)
    z0_ref = 0.52 + 2.0 * l_ref * np.sin(tilt) + radius * np.cos(tilt)
    dy_ref = max(y_ref - y0_ref, 0.005)
    denom = 2.0 * np.cos(tilt)**2 * (
        z0_ref - radius + dy_ref * np.tan(tilt)
    )
    speed2 = g * dy_ref**2 / max(denom, 1e-6)

    delta_l = length - l_ref
    speed2 -= 4.0 * g * delta_l * np.sin(tilt) + 1.0 * delta_l

    # The sealed gate's inertia largely cancels its height-dependent contact
    # lever arm. Keep only a small residual correction for the changed plate.
    gate_half_height = float(visible.get("gate.size2", 0.007))
    speed2 -= 20.0 * (gate_half_height - 0.007)
    speed = float(np.sqrt(max(speed2, 0.0025)))

    y0 = 0.2 + 2.0 * length * np.cos(tilt) - radius * np.sin(tilt)
    z0 = 0.52 + 2.0 * length * np.sin(tilt) + radius * np.cos(tilt)
    vz = speed * np.sin(tilt)
    flight_time = (vz + np.sqrt(vz*vz + 2.0*g*max(z0-radius, 0.0))) / g
    y = y0 + speed * np.cos(tilt) * flight_time
    return [float(y)]
