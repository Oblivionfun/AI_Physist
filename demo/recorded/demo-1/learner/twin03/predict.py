import numpy as np
from scipy.interpolate import RBFInterpolator

# All 62 measurements are embedded because the submitted model is isolated.
_X = np.array([
    [0.3,0.12,0],[0.3,0.17,0],[0.3,0.22,0],[0.3,0.27,0],
    [0.3,0.32,0],[0.3,0.37,0],[0.3,0.40,0],[0.3,0.30,-0.045],
    [0.3,0.30,0.045],[0.990476,0.346361,0.037554],
    [1.3764,0.9958,-0.0381],[0.8141,0.9943,0.0421],
    [0.1946,0.9995,-0.0430],[1.3912,0.2251,-0.0425],
    [1.3967,0.5820,0.0123],[0.1584,0.8585,0.0116],
    [0.8280,0.6179,-0.0314],[1.1707,0.1238,0.0024],
    [0.7522,0.5667,0.0246],[0.229603,0.985652,-0.012273],
    [1.2659,0.7617,-0.0275],[0.7589,0.9857,-0.0049],
    [1.3986,0.1655,0.0443],[1.3965,0.9852,0.0270],
    [0.1790,0.6104,-0.0280],[0.8460,0.1337,-0.0328],
    [0.2056,0.6300,0.0441],[0.8138,0.9779,-0.0439],
    [1.1407,0.7101,0.0443],[0.684566,0.256535,0.018618],
    [0.3199,0.9783,0.0438],[0.9893,0.5269,0.0041],
    [0.4805,0.6346,-0.0023],[1.3397,0.4333,-0.0173],
    [1.0214,0.3833,0.0444],[1.3482,0.9978,-0.0058],
    [0.5125,0.8405,-0.0258],[1.0476,0.8439,0.0144],
    [0.1555,0.5605,0.0150],[1.170946,0.662090,-0.043879],
    [0.5696,0.8571,0.0203],[0.5126,0.4087,-0.0252],
    [0.4331,0.8343,-0.0185],[0.3,0.12,-0.045],
    [0.3,0.12,0.045],[0.3,0.17,-0.045],[0.3,0.17,0.045],
    [0.3,0.27,-0.045],[0.3,0.27,0.045],
    [1.397624,0.217277,-0.008458],[0.3,0.32,-0.045],
    [0.3,0.32,0.045],[0.3,0.37,-0.045],[0.3,0.37,0.045],
    [0.2,0.2,-0.045],[0.2,0.2,0.045],[0.4,0.15,-0.045],
    [0.4,0.15,0.045],[0.25,0.14,0.045],
    [0.481711,0.691575,0.028197],[0.3,0.39,0],[0.3,0.19,0]
], dtype=float)
_Y = np.array([
    -0.97027,-1.02699,-1.20383,-1.29848,-1.38124,-1.46952,-1.55273,
    -1.46975,-1.17746,-2.96610,-6.12277,-4.87702,-2.05973,-3.16328,
    -3.85350,-1.55594,-4.73603,-2.45430,-3.53425,-2.16919,-5.97254,
    -5.59171,-1.88733,-4.86090,-1.53594,-2.37135,-1.39485,-6.54233,
    -4.43806,-2.17197,-2.15911,-4.34977,-2.71731,-4.00630,-3.04240,
    -5.97106,-3.53633,-5.64433,-1.27179,-5.93323,-3.39951,-2.42617,
    -2.96122,-1.09015,-0.83620,-1.18456,-0.95697,-1.46181,-1.16714,
    -2.73969,-1.51689,-1.21503,-1.64352,-1.30327,-1.04872,-0.84604,
    -1.35663,-1.05900,-0.79533,-2.58319,-1.55106,-1.16686
], dtype=float)
_LO = np.array([0.15, 0.12, -0.045])
_HI = np.array([1.40, 1.00, 0.045])
_Z = 2.0 * (_X - _LO) / (_HI - _LO) - 1.0
_MODEL = RBFInterpolator(_Z, _Y, kernel="cubic", smoothing=0.002, degree=1)

_G = 9.81
_HINGE_Z = 0.620
_BALL_R = 0.016
_ARM_TO_BALL = 0.200
_SPRING_MOTOR_RATIO = 0.16


def _stop_angle(post_x, striker_z):
    # For negative arm angles, the striker's leftmost rotated corner meets the
    # post's right face.  This reproduces the measured nominal stop (-0.117 rad).
    a = (striker_z - _HINGE_Z) + 0.014
    hx = 0.008
    radius = np.hypot(a, hx)
    phase = np.arctan2(hx, a)
    face = post_x + 0.020
    return float(phase + np.arcsin(np.clip(face / radius, -0.999, 0.999)))


_THETA0 = _stop_angle(-0.040, 0.710)


def _equivalent_cock(cock, power, theta):
    # Match motor work plus torsion-spring energy at the nominal stop angle.
    q = _SPRING_MOTOR_RATIO
    energy = (power * (cock - theta)
              + 0.5 * q * ((cock + 0.3) ** 2 - (theta + 0.3) ** 2))
    a = 0.5 * q
    b = power + 0.3 * q
    c = (0.045 * q - power * _THETA0
         - 0.5 * q * (_THETA0 + 0.3) ** 2 - energy)
    return float((-b + np.sqrt(max(0.0, b * b - 4.0 * a * c))) / (2.0 * a))


def _striker_inertia_scale(shift, striker_z):
    # The relocation changes only a small part of total driven inertia.
    ball_and_fixed_arm = 0.002864
    slug = 0.155 * (0.034 ** 2 + (0.080 + shift) ** 2 + 0.0003227)
    striker_shape = (0.016 ** 2 + 0.028 ** 2) / 12.0
    nominal = 0.026 * (0.090 ** 2 + striker_shape)
    changed = 0.026 * ((striker_z - _HINGE_Z) ** 2 + striker_shape)
    return float(np.sqrt((ball_and_fixed_arm + slug + nominal) /
                         (ball_and_fixed_arm + slug + changed)))


def predict(knobs: dict, visible: dict) -> list[float]:
    cock = float(knobs["cock"])
    power = abs(float(knobs["power"]))
    shift = float(knobs["shift"])
    post_x = float(visible.get("stop_post.posx", -0.040))
    striker_z = float(visible.get("striker.posz", 0.710))

    theta = _stop_angle(post_x, striker_z)
    effective_cock = _equivalent_cock(cock, power, theta)
    query = np.array([[effective_cock, power, shift]])
    zq = 2.0 * (query - _LO) / (_HI - _LO) - 1.0
    nominal_x = float(_MODEL(zq)[0])

    # Decode the nominal landing point into impact angular speed, then redo the
    # ballistic flight at the modified stop angle.  At nominal dimensions this
    # round trip returns the response-surface prediction.
    distance = max(0.10, -nominal_x)
    x0_nom = _ARM_TO_BALL * np.sin(_THETA0)
    h_nom = _HINGE_Z + _ARM_TO_BALL * np.cos(_THETA0) - _BALL_R
    horizontal_nom = max(0.02, distance + x0_nom)
    t_nom = np.sqrt(max(1e-6, 2.0 * (h_nom + np.tan(_THETA0)
                                     * horizontal_nom) / _G))
    omega = horizontal_nom / (t_nom * _ARM_TO_BALL * np.cos(_THETA0))
    omega *= _striker_inertia_scale(shift, striker_z)

    x0 = _ARM_TO_BALL * np.sin(theta)
    h = _HINGE_Z + _ARM_TO_BALL * np.cos(theta) - _BALL_R
    speed_x = _ARM_TO_BALL * np.cos(theta) * omega
    speed_z = speed_x * np.tan(theta)
    flight = (speed_z + np.sqrt(max(0.0, speed_z ** 2 + 2.0 * _G * h))) / _G
    return [float(x0 - speed_x * flight)]
