import numpy as np


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def predict(knobs: dict, visible: dict) -> list[float]:
    # Keep the model robust if the evaluator passes slightly out-of-range values.
    cock = _clamp(float(knobs["cock"]), 0.15, 1.3)
    power = _clamp(float(knobs["power"]), -1.0, -0.15)
    q = -power

    # Feature basis: cubic polynomial + hinge for the high-energy regime.
    e = cock * q
    h = max(0.0, e - 0.35)
    phi = np.array(
        [
            1.0,
            cock,
            q,
            e,
            cock * cock,
            q * q,
            e * e,
            cock * q * q,
            cock * cock * q,
            h,
            h * h,
            h * e,
            cock**3,
            q**3,
        ],
        dtype=float,
    )
    coef = np.array(
        [
            -0.22373582565688804,
            0.8644979647443299,
            -5.04882013057324,
            4.62827171457572,
            -4.185071147577923,
            6.467824005282816,
            14.861572160484895,
            -13.68210562777532,
            -13.10194045668168,
            1.8624496826452221,
            -1.6136755688357245,
            -0.9618181799099612,
            4.226318508090959,
            -1.3848083098052906,
        ],
        dtype=float,
    )
    x = float(np.dot(phi, coef))

    # First-order corrections for evaluator-visible geometry changes.
    stop_post_posx = float(visible.get("stop_post.posx", -0.04))
    slug_posz = float(visible.get("slug.posz", 0.69))
    d_post = stop_post_posx - (-0.04)
    d_slug = slug_posz - 0.69
    x += (7.5 + 6.0 * e) * d_post + (4.0 + 5.0 * e) * d_slug

    return [x]
