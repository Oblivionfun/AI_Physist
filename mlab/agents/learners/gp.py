"""Minimal Gaussian-process regression (RBF kernel) on the unit knob cube."""

from __future__ import annotations

import numpy as np

LENGTH_SCALES = (0.05, 0.1, 0.2, 0.35, 0.6, 1.0)


def rbf(a: np.ndarray, b: np.ndarray, ls: float) -> np.ndarray:
    d2 = np.sum((a[:, None, :] - b[None, :, :]) ** 2, axis=-1)
    return np.exp(-0.5 * d2 / ls**2)


class GP:
    def __init__(self, x: np.ndarray, y: np.ndarray, noise: float):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.mean = float(np.mean(self.y))
        self.scale = float(np.std(self.y)) or 1.0
        self.noise = noise / self.scale
        yn = (self.y - self.mean) / self.scale
        best = None
        for ls in LENGTH_SCALES:
            k = rbf(self.x, self.x, ls) + (self.noise**2 + 1e-6) * np.eye(len(self.x))
            try:
                chol = np.linalg.cholesky(k)
            except np.linalg.LinAlgError:
                continue
            alpha = np.linalg.solve(chol.T, np.linalg.solve(chol, yn))
            nll = 0.5 * yn @ alpha + np.sum(np.log(np.diag(chol)))
            if best is None or nll < best[0]:
                best = (nll, ls, chol, alpha)
        assert best is not None
        _, self.ls, self.chol, self.alpha = best

    def predict(self, xq: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ks = rbf(np.atleast_2d(xq), self.x, self.ls)
        mu = ks @ self.alpha
        v = np.linalg.solve(self.chol, ks.T)
        var = np.clip(1.0 - np.sum(v**2, axis=0), 1e-12, None)
        return self.mean + self.scale * mu, self.scale * np.sqrt(var)
