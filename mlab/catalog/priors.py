from __future__ import annotations

import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, model_validator

MAX_PRIOR_RATIO = 10.0


class Prior(BaseModel):
    """Distribution of an unknown physical quantity; only its range is ever disclosed."""

    low: float
    high: float
    scale: Literal["linear", "log"] = "linear"
    unit: str = ""
    description: str = ""

    @model_validator(mode="after")
    def _check(self) -> Prior:
        if not (math.isfinite(self.low) and math.isfinite(self.high)):
            raise ValueError("prior bounds must be finite")
        if self.high <= self.low:
            raise ValueError(f"prior high ({self.high}) must exceed low ({self.low})")
        if self.scale == "log" and self.low <= 0:
            raise ValueError("log-scale prior needs a positive lower bound")
        if self.low > 0 and self.high / self.low > MAX_PRIOR_RATIO:
            raise ValueError(
                f"prior range ratio {self.high / self.low:.1f} exceeds {MAX_PRIOR_RATIO:.0f}; "
                "narrow the range so the challenge comes from mechanism, not from inflated priors"
            )
        return self

    def to_unit(self, value: float) -> float:
        """Map a physical value to [0, 1] in the prior's natural coordinate."""
        if self.scale == "log":
            return (math.log(value) - math.log(self.low)) / (math.log(self.high) - math.log(self.low))
        return (value - self.low) / (self.high - self.low)

    def from_unit(self, u: float) -> float:
        u = min(max(u, 0.0), 1.0)
        if self.scale == "log":
            return math.exp(math.log(self.low) + u * (math.log(self.high) - math.log(self.low)))
        return self.low + u * (self.high - self.low)


class NamedPrior(Prior):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.]{0,47}$")


def sample_prior(prior: Prior, rng: np.random.Generator) -> float:
    return prior.from_unit(float(rng.uniform()))


def nominal_value(prior: Prior) -> float:
    """Prior centre in its natural coordinate (geometric mean for log priors)."""
    return prior.from_unit(0.5)
