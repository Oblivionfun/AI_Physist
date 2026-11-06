import numpy as np
from scipy.interpolate import RBFInterpolator


# Columns are cock, |power|, shift, and measured first-contact x.
_DATA = np.array([
    [0.8, 0.6, 0.0, -6.90141], [0.15, 0.12, 0.045, -0.94224],
    [0.3, 0.12, 0.045, -1.28646], [0.45, 0.12, 0.045, -1.73605],
    [0.3, 0.3, 0.045, -1.82411], [0.3, 0.6, 0.045, -2.41756],
    [0.3, 1.0, 0.045, -3.26755], [0.3, 0.12, 0.0, -1.43435],
    [0.3, 0.12, -0.045, -1.53954],
    [0.71582398, 0.3808259, -0.0340793, -5.07979],
    [0.6, 0.12, 0.045, -2.15506], [0.9, 0.12, 0.045, -3.15538],
    [1.2, 0.12, 0.045, -3.73507], [1.4, 0.12, 0.045, -3.28623],
    [0.8, 0.12, 0.0, -3.30454], [0.8, 0.12, -0.045, -3.62456],
    [0.8, 0.6, 0.045, -6.11302], [0.8, 1.0, 0.045, -8.48955],
    [0.8, 0.6, -0.045, -7.64731],
    [1.16105417, 0.77119097, 0.03405576, -8.25248],
    [1.4, 1.0, -0.045, -8.07927], [0.15, 1.0, 0.045, -2.16148],
    [1.0, 0.45, 0.0, -6.74175], [0.55, 0.8, -0.02, -5.95985],
    [1.25, 0.35, -0.045, -6.58466], [0.4, 0.75, 0.02, -3.58558],
    [0.65, 0.25, -0.025, -3.75369], [1.05, 0.9, 0.045, -9.00451],
    [1.35, 0.6, 0.015, -6.64452],
    [0.98612613, 0.336401, -0.00723752, -5.9587],
    [1.15, 0.5, 0.045, -6.44124], [1.15, 0.5, -0.045, -8.24902],
    [0.9, 0.75, 0.0, -8.76357], [0.7, 1.0, 0.0, -8.97627],
    [1.3, 0.12, 0.0, -4.20121], [1.4, 0.12, -0.045, -4.27546],
    [0.15, 0.5, -0.045, -1.8454], [0.4, 0.4, -0.045, -3.04141],
    [0.6, 0.5, 0.045, -4.05997],
    [0.26619966, 0.80917033, 0.00726108, -2.95255],
    [0.18, 0.12, 0.045, -1.00422], [0.22, 0.12, 0.045, -1.11197],
    [0.26, 0.12, 0.045, -1.1914], [0.34, 0.12, 0.045, -1.39207],
    [0.38, 0.12, 0.045, -1.48591], [0.42, 0.12, 0.045, -1.60016],
    [0.5, 1.0, 0.045, -4.92325], [1.0, 1.0, -0.045, -12.42852],
    [1.25, 0.7, 0.045, -7.34009],
    [0.346738, 0.2237059, 0.02928363, -1.79273],
    [0.15, 0.12, 0.0, -1.03385], [0.15, 0.12, -0.045, -1.09953],
    [0.45, 0.12, 0.0, -1.89434], [0.45, 0.12, -0.045, -2.07392],
    [0.15, 1.0, -0.045, -2.45633], [0.5, 0.6, 0.0, -4.2276],
    [0.75, 0.35, 0.045, -4.26579], [1.0, 0.12, -0.045, -4.42477],
    [1.4, 1.0, 0.045, -7.54632],
    [0.87623486, 0.91971386, -0.02934843, -10.87636],
    [0.9, 0.55, -0.045, -7.8583], [1.1, 0.3, 0.02, -5.51079],
], dtype=float)

_LO = np.array([0.15, 0.12, -0.045])
_SPAN = np.array([1.25, 0.88, 0.09])
_MODEL = RBFInterpolator(
    (_DATA[:, :3] - _LO) / _SPAN,
    _DATA[:, 3],
    kernel="cubic",
    degree=1,
)


def _impact_angle(post_x, striker_z):
    """First angle where the striker's left face reaches the post's right face."""
    target = post_x + 0.020
    a = striker_z - 0.620 + 0.014
    lo, hi = -0.8, 0.0
    for _ in range(50):
        mid = (lo + hi) * 0.5
        left_face = a * np.sin(mid) - 0.008 * np.cos(mid)
        if left_face < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def _equivalent_cock(cock, power, theta):
    # Preserve spring release plus motor work at the calibrated impact angle.
    # Experiments identify motor-gain / spring-stiffness as approximately 2.
    theta0 = -0.1168
    energy = (
        (cock + 0.3) ** 2 - (theta + 0.3) ** 2
        + 4.0 * power * (cock - theta)
    )
    b = 0.6 + 4.0 * power
    constant = (
        0.09 - (theta0 + 0.3) ** 2 - 4.0 * power * theta0 - energy
    )
    disc = max(0.0, b * b - 4.0 * constant)
    return (-b + np.sqrt(disc)) * 0.5


def predict(knobs: dict, visible: dict) -> list[float]:
    cock = float(knobs["cock"])
    power = -float(knobs["power"])
    shift = float(knobs["shift"])
    post_x = float(visible.get("stop_post.posx", -0.04))
    striker_z = float(visible.get("striker.posz", 0.71))

    if abs(post_x + 0.04) > 1e-12 or abs(striker_z - 0.71) > 1e-12:
        theta = _impact_angle(post_x, striker_z)
        cock = _equivalent_cock(cock, power, theta)

    point = (np.array([[cock, power, shift]]) - _LO) / _SPAN
    outcome = float(_MODEL(point)[0])
    return [outcome]
