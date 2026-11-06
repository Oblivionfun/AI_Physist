import numpy as np


def _predict_x(compression: float, ball_posx: float) -> float:
    # Effective compression heuristic:
    # moving the ball forward delays first contact with the plunger.
    c_eff = compression + (ball_posx - 0.045)

    # Fitted on lab data (quadratic in compression around default visible setup).
    x = 0.36257349 - 3.20154304 * c_eff - 2.41993031 * (c_eff ** 2)

    # Very low effective compression often fails to launch; keep output bounded.
    if c_eff > -0.03:
        x = min(x, 0.47)

    return float(x)


def predict(knobs: dict, visible: dict) -> list[float]:
    compression = float(knobs["compression"])
    ball_posx = float(visible.get("ball.posx", 0.045))
    return [_predict_x(compression, ball_posx)]
