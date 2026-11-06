import numpy as np


def _phi(c: float, p: float, s: float) -> np.ndarray:
    a = abs(p)
    return np.array(
        [
            1.0,
            c,
            a,
            s,
            c * c,
            a * a,
            s * s,
            c * a,
            c * s,
            a * s,
            c * c * c,
            a * a * a,
            s * s * s,
            c * c * a,
            c * a * a,
            c * c * s,
            c * s * s,
            a * a * s,
            a * s * s,
            c * a * s,
        ],
        dtype=float,
    )


_COEF = np.array(
    [
        -0.29704962994682405,
        -1.0128818020180108,
        -1.5718350735678175,
        2.2227300380053987,
        -1.466694501914256,
        0.22939169412924204,
        0.055100031318990994,
        -1.6429571372354825,
        1.4203660220778234,
        0.8041914937301358,
        1.33451020496321,
        0.4287050788761545,
        0.002383815757395538,
        -2.1968130811235347,
        -0.31746237777449343,
        1.0116378666476524,
        0.028903587554854268,
        0.38292721196091206,
        0.015425131590922828,
        0.5231262297762574,
    ],
    dtype=float,
)


def predict(knobs: dict, visible: dict) -> list[float]:
    c = float(np.clip(knobs["cock"], 0.15, 1.4))
    p = float(np.clip(knobs["power"], -1.0, -0.12))
    s = float(np.clip(knobs["shift"], -0.045, 0.045))

    stop_x = float(visible.get("stop_post.posx", -0.04))
    striker_z = float(visible.get("striker.posz", 0.71))

    # Conservative transfer to handle evaluation with modified geometry.
    dx = stop_x + 0.04
    dz = striker_z - 0.71
    c_eff = c - 1.8 * dx - 0.35 * dz

    y = float(_phi(c_eff, p, s) @ _COEF)
    y += 1.3 * dx - 0.25 * dz
    return [y]
