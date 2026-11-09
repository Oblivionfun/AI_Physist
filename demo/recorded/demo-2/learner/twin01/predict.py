import numpy as np


def predict(knobs: dict, visible: dict) -> list[float]:
    """Predict the ball's first ground-contact y coordinate."""
    pullback = float(knobs["pullback"])
    drive = float(knobs["drive"])

    # Spring compression relative to the -0.100 m relaxed position.
    c = np.clip(-pullback - 0.100, 0.020, 0.220)
    d = np.clip(drive, 0.0, 0.6)

    # Empirical launch-range surface at the measured 0.200 m track half-length.
    # The coefficients are a smooth least-squares fit to all 70 runs.
    base = (
        1.37007723e-1
        + 1.08933325e1 * c
        - 1.91390967e2 * c**2
        + 2.28259765e3 * c**3
        - 1.05499047e4 * c**4
        + 1.71712644e4 * c**5
    )
    drive_effect = d * (
        -9.04626085e-3
        + 2.25492012 * c
        - 6.86137630 * c**2
    ) + 1.01634738e-2 * d**2
    y_at_reference_track = base + drive_effect

    # Convert the reference range to edge speed, propagate rolling resistance
    # over any added track, then perform the same horizontal ballistic flight.
    track_half_length = float(visible.get("track.size1", 0.200))
    reference_edge = 0.200 + 0.025
    edge = track_half_length + 0.025
    flight_time = np.sqrt(2.0 * (0.545 - 0.025) / 9.81)
    reference_speed = max(
        0.0, (y_at_reference_track - reference_edge) / flight_time
    )
    extra_track = track_half_length - 0.200
    rolling_deceleration = 9.81 * 0.00020 / 0.025
    speed_sq = reference_speed**2 - 2.0 * rolling_deceleration * extra_track
    edge_speed = np.sqrt(max(0.0, speed_sq))

    return [float(edge + flight_time * edge_speed)]
