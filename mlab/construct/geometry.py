from __future__ import annotations

import math

import numpy as np

from mlab.construct.ir import PartIR, ShapeIR


def rot_x(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def euler_to_mat(euler: tuple[float, float, float]) -> np.ndarray:
    """Extrinsic x, then y, then z rotation (radians)."""
    return rot_z(euler[2]) @ rot_y(euler[1]) @ rot_x(euler[0])


def mat_to_quat(m: np.ndarray) -> np.ndarray:
    """Rotation matrix to unit quaternion (w, x, y, z), MuJoCo convention."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = np.array([w, x, y, z], dtype=float)
    q /= np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    return q


def shape_volume(shape: ShapeIR) -> float:
    s = shape.size
    if shape.kind == "box":
        return 8.0 * s[0] * s[1] * s[2]
    if shape.kind == "sphere":
        return 4.0 / 3.0 * math.pi * s[0] ** 3
    if shape.kind == "cylinder":
        return math.pi * s[0] ** 2 * 2.0 * s[1]
    r, h = s[0], s[1]
    return math.pi * r**2 * 2.0 * h + 4.0 / 3.0 * math.pi * r**3


def shape_char_size(shape: ShapeIR) -> float:
    """Smallest meaningful thickness of the shape, used to scale penetration tolerances."""
    s = shape.size
    if shape.kind == "box":
        return 2.0 * min(s)
    return 2.0 * s[0]


def expected_size_len(kind: str) -> int:
    return {"box": 3, "sphere": 1, "capsule": 2, "cylinder": 2}[kind]


def part_aabb(part: PartIR) -> tuple[np.ndarray, np.ndarray]:
    """World axis-aligned bounding box of a part in the initial configuration."""
    center = np.asarray(part.pos, dtype=float)
    rot = euler_to_mat(part.euler)
    s = part.shape.size
    kind = part.shape.kind
    if kind == "box":
        half = np.abs(rot) @ np.asarray(s, dtype=float)
    elif kind == "sphere":
        half = np.full(3, s[0])
    elif kind == "capsule":
        axis = rot[:, 2]
        half = np.abs(axis) * s[1] + s[0]
    else:
        axis = rot[:, 2]
        radial = s[0] * np.sqrt(np.clip(1.0 - axis**2, 0.0, 1.0))
        half = np.abs(axis) * s[1] + radial
    return center - half, center + half


def point_in_aabb(point: np.ndarray, lo: np.ndarray, hi: np.ndarray, margin: float) -> bool:
    return bool(np.all(point >= lo - margin) and np.all(point <= hi + margin))


def aabb_gap(a: tuple[np.ndarray, np.ndarray], b: tuple[np.ndarray, np.ndarray]) -> float:
    """Largest axis separation between two boxes; negative means they overlap on every axis."""
    gaps = np.maximum(a[0] - b[1], b[0] - a[1])
    return float(np.max(gaps))


def aabb_overlap_depth(a: tuple[np.ndarray, np.ndarray], b: tuple[np.ndarray, np.ndarray]) -> float:
    overlap = np.minimum(a[1], b[1]) - np.maximum(a[0], b[0])
    return float(np.min(overlap))
