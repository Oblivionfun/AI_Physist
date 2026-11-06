import numpy as np

_T = 0.22
_K = 20.0

# Linear coefficients over a nonlinear feature basis fitted on all 62 lab experiments.
_COEF = np.array(
    [
        -1.0473319773972436,
        0.3586620274751045,
        4.576156468191001,
        -2.8513687467987716,
        -2.5936503656390366,
        -5.968333629280543,
        -27.915600179621094,
        -24.990255224815925,
        6.049659346398868,
        18.531979348689013,
        16.001595092992275,
        5.274237524271442,
        2.511057791297837,
        -7.2229416542429945,
        3.9313739982667224,
        24.97659647763381,
        -18.474053821377776,
        -10.231520138483637,
    ],
    dtype=float,
)


def _feature_vector(cock: float, power: float, shift: float) -> np.ndarray:
    # power is negative in the interface; model uses its magnitude.
    p = -power
    e = cock * p
    h = 1.0 / (1.0 + np.exp(-_K * (e - _T)))
    a = abs(shift)
    return np.array(
        [
            1.0,
            cock,
            p,
            shift,
            cock * cock,
            p * p,
            shift * shift,
            cock * p,
            cock * p * p,
            cock * cock * p,
            cock * shift,
            p * shift,
            a,
            h,
            h * cock,
            h * p,
            h * cock * p,
            h * p * p,
        ],
        dtype=float,
    )


def predict(knobs: dict, visible: dict) -> list[float]:
    cock = float(knobs["cock"])
    power = float(knobs["power"])
    shift = float(knobs["shift"])

    base = float(_feature_vector(cock, power, shift) @ _COEF)

    # Physics-inspired corrections for held-out visible changes.
    # More negative stop_post.posx means later impact and typically longer range.
    dx = float(visible.get("stop_post.posx", -0.04)) - (-0.04)
    # Higher striker slightly advances post contact in this mechanism.
    dz = float(visible.get("striker.posz", 0.71)) - 0.71

    corrected = base + 3.2 * dx - 0.9 * dz
    return [float(corrected)]
