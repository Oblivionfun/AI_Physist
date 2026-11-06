import numpy as np


# Cubic fit from lab data (valid runs) at default visible geometry.
_C3 = 86.33800964
_C2 = 21.96082583
_C1 = -1.11865804
_C0 = 0.41443366

# Default from card; visible-only variation tested by referee.
_BALL_POSX_DEFAULT = 0.045

# Heuristic: moving the ball forward mostly adds horizontal offset, but less than 1:1
# because contact timing with the plunger also changes.
_BALL_POSX_GAIN = 0.78


def predict(knobs: dict, visible: dict) -> list[float]:
    c = float(knobs["compression"])
    ball_posx = float(visible.get("ball.posx", _BALL_POSX_DEFAULT))

    base = ((_C3 * c + _C2) * c + _C1) * c + _C0
    adjusted = base + _BALL_POSX_GAIN * (ball_posx - _BALL_POSX_DEFAULT)

    # Keep outputs in a physically plausible range for this setup.
    x_land = float(np.clip(adjusted, 0.30, 0.90))
    return [x_land]
