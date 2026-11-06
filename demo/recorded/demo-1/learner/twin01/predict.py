import numpy as np
from scipy.interpolate import RBFInterpolator


# Measured response surface for the unmodified device.  The two input columns
# are cock angle and positive power magnitude; the third is landing x.
_DATA = np.array([
    [0.700000, 0.300000, -2.41277],
    [0.500000, 0.150000, -1.12101],
    [0.500000, 0.200000, -1.36098],
    [0.500000, 0.250000, -1.60155],
    [0.500000, 0.400000, -2.27638],
    [0.500000, 0.700000, -3.28799],
    [0.150000, 0.150000, -0.71970],
    [0.300000, 0.150000, -0.92492],
    [1.300000, 0.150000, -1.28629],
    [1.221102, 0.825592, -6.18433],
    [0.150000, 1.000000, -1.93593],
    [0.800000, 1.000000, -6.75333],
    [1.050000, 0.550000, -4.65007],
    [0.150000, 0.550000, -1.42526],
    [1.050000, 0.300000, -2.68182],
    [0.450000, 0.950000, -3.68275],
    [0.800000, 0.700000, -5.19507],
    [1.300000, 0.400000, -3.05837],
    [1.050000, 1.000000, -7.64534],
    [0.265621, 0.520881, -1.85612],
    [1.300000, 1.000000, -6.48501],
    [0.800000, 0.150000, -1.43256],
    [0.600000, 0.550000, -3.25567],
    [0.150000, 0.400000, -1.23960],
    [0.150000, 0.850000, -1.71750],
    [0.800000, 0.850000, -5.86631],
    [1.300000, 0.550000, -4.06008],
    [1.050000, 0.150000, -1.50514],
    [0.150000, 0.700000, -1.62109],
    [0.493520, 0.634432, -3.06382],
    [1.050000, 0.700000, -5.66414],
    [0.300000, 0.300000, -1.41343],
    [0.600000, 0.850000, -4.45196],
    [0.800000, 0.550000, -4.25437],
    [1.300000, 0.700000, -5.06042],
    [1.050000, 0.850000, -6.59953],
    [0.800000, 0.400000, -3.25127],
    [0.600000, 1.000000, -5.38726],
    [0.300000, 0.950000, -2.77948],
    [0.993045, 0.326572, -2.91083],
    [0.300000, 0.550000, -2.00050],
    [0.300000, 0.700000, -2.27989],
    [0.450000, 0.550000, -2.58116],
    [0.300000, 0.850000, -2.50344],
    [0.450000, 0.850000, -3.41882],
    [0.150000, 0.300000, -1.07935],
    [0.300000, 0.400000, -1.65383],
    [1.050000, 0.400000, -3.53541],
    [1.300000, 0.300000, -2.36192],
    [0.775381, 0.736408, -5.26462],
    [0.800000, 0.300000, -2.55750],
    [0.600000, 0.150000, -1.22948],
    [0.600000, 0.400000, -2.59660],
    [0.600000, 0.700000, -3.95558],
    [0.600000, 0.300000, -2.12505],
    [1.300000, 0.850000, -5.92345],
    [0.450000, 0.300000, -1.71119],
    [0.150000, 0.200000, -0.84762],
    [0.300000, 0.200000, -1.07717],
    [0.711034, 0.217540, -1.86459],
    [0.600000, 0.200000, -1.56008],
    [0.800000, 0.200000, -1.78741],
    [1.050000, 0.200000, -1.86350],
    [1.300000, 0.200000, -1.64386],
    [0.150000, 0.950000, -1.83634],
    [0.300000, 1.000000, -2.88703],
    [0.450000, 1.000000, -3.91146],
    [0.600000, 0.950000, -5.18468],
    [0.800000, 0.950000, -6.47867],
    [0.334753, 0.926985, -2.94433],
    [1.050000, 0.950000, -7.06964],
    [1.300000, 0.950000, -6.34682],
    [0.450000, 0.150000, -1.05893],
    [0.450000, 0.200000, -1.30256],
    [0.450000, 0.400000, -2.10771],
    [0.450000, 0.700000, -3.02277],
    [0.150000, 0.150000, -0.74138],
    [0.300000, 0.150000, -0.89933],
    [1.300000, 0.150000, -1.28929],
    [1.151540, 0.411603, -3.56014],
], dtype=float)

_CENTER = np.array([0.15, 0.15])
_SCALE = np.array([1.15, 0.85])
_MODEL = RBFInterpolator(
    (_DATA[:, :2] - _CENTER) / _SCALE,
    _DATA[:, 2],
    kernel="cubic",
    neighbors=12,
    smoothing=0.001,
    degree=1,
)


def _surface(cock, magnitude):
    """Interpolate, with stable linear continuation for inertia corrections."""
    clipped = float(np.clip(magnitude, 0.15, 1.0))
    q = (np.array([[cock, clipped]]) - _CENTER) / _SCALE
    value = float(_MODEL(q)[0])
    if magnitude < 0.15:
        q2 = (np.array([[cock, 0.16]]) - _CENTER) / _SCALE
        slope = (float(_MODEL(q2)[0]) - value) / 0.01
        value += slope * (magnitude - 0.15)
    elif magnitude > 1.0:
        q2 = (np.array([[cock, 0.99]]) - _CENTER) / _SCALE
        slope = (value - float(_MODEL(q2)[0])) / 0.01
        value += slope * (magnitude - 1.0)
    return value


def _equivalent_power(cock, magnitude, slug_z):
    # The slug changes both rotational inertia and the gravitational work
    # required before the ball releases near the arm's vertical position.
    slug_mass = 0.13
    ball_mass = 0.07
    motor_gain = 5.0
    z0 = 0.690 - 0.620
    z = slug_z - 0.620

    # Known assembly inertia plus ball and slug parallel-axis terms.
    fixed_inertia = 0.001522
    slug_rot_inertia = slug_mass * (0.044 ** 2 + 0.044 ** 2) / 12.0
    ball_inertia = ball_mass * (0.200 ** 2 + 0.4 * 0.016 ** 2)
    inertia0 = (
        fixed_inertia + ball_inertia + slug_rot_inertia
        + slug_mass * (0.034 ** 2 + z0 ** 2)
    )
    inertia = (
        fixed_inertia + ball_inertia + slug_rot_inertia
        + slug_mass * (0.034 ** 2 + z ** 2)
    )

    # Current-device gravitational work to rotate from cock to vertical.
    weighted_z0 = 0.013064 + slug_mass * z0 + ball_mass * 0.200
    weighted_x = slug_mass * 0.034 + 0.010 * 0.025
    gravity0 = 9.81 * (
        weighted_z0 * (1.0 - np.cos(cock)) + weighted_x * np.sin(cock)
    )
    gravity_delta = (
        9.81 * slug_mass * (z - z0) * (1.0 - np.cos(cock))
    )
    energy0 = motor_gain * magnitude * cock - gravity0
    equivalent_energy = inertia0 / inertia * (energy0 - gravity_delta)
    return float((equivalent_energy + gravity0) / (motor_gain * cock))


def predict(knobs: dict, visible: dict) -> list[float]:
    cock = float(knobs["cock"])
    magnitude = -float(knobs["power"])
    slug_z = float(visible.get("slug.posz", 0.690))
    magnitude = _equivalent_power(cock, magnitude, slug_z)

    # Across the allowed range the post remains beyond q=0.  Sensor traces show
    # that the unrestrained ball leaves the cup around q=0, before the striker
    # reaches the post, so changing stop_post.posx does not alter first landing.
    return [_surface(cock, magnitude)]
