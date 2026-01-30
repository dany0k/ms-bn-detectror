"""
Детектор bottleneck на основе второй производной латенси.
"""

import statistics
import numpy as np
from typing import List, Optional
from dataclasses import dataclass

from ..models import Sample
from .base import BaseDetector, DetectionResult, Severity


@dataclass
class DerivativeAnalysis:
    """Результат анализа производных"""
    first_derivative: float
    second_derivative: float
    r_squared: float
    inflection_rps: Optional[float]


class SecondDerivativeDetector(BaseDetector):
    """
    Детектор bottleneck на основе второй производной.

    Полином: L(rps) = a*rps² + b*rps + c
    Вторая производная: d²L/drps² = 2a

    Если a > 0 → кривая выпуклая вверх → bottleneck
    """

    def __init__(
            self,
            min_samples: int = 20,
            second_derivative_threshold: float = 0.01,
            r_squared_min: float = 0.3,
    ):
        super().__init__(min_samples)
        self.second_derivative_threshold = second_derivative_threshold
        self.r_squared_min = r_squared_min

    @property
    def name(self) -> str:
        return "SecondDerivativeDetector"

    def analyze(
            self,
            samples: List[Sample],
            src: str,
            dst: str
    ) -> Optional[DetectionResult]:
        if not self._has_enough_samples(samples):
            return None

        analysis = self._compute_derivatives(samples)

        if analysis is None:
            return None

        if analysis.r_squared < self.r_squared_min:
            return None

        if analysis.second_derivative > self.second_derivative_threshold:
            return DetectionResult(
                src=src,
                dst=dst,
                severity=Severity.CRITICAL if analysis.second_derivative > self.second_derivative_threshold * 2 else Severity.WARNING,
                detector_name=self.name,
                message=(
                    f"Accelerating latency growth: "
                    f"d²L/dRPS²={analysis.second_derivative:.4f}, "
                    f"R²={analysis.r_squared:.2f}"
                ),
                slope=analysis.first_derivative,
                avg_rps=statistics.mean(s.rps for s in samples),
                avg_latency=statistics.mean(s.latency for s in samples),
            )

        return None

    def _compute_derivatives(self, samples: List[Sample]) -> Optional[DerivativeAnalysis]:
        rps = np.array([s.rps for s in samples])
        latency = np.array([s.latency for s in samples])

        if np.std(rps) < 1e-6:
            return None

        try:
            coeffs = np.polyfit(rps, latency, 2)
            a, b, c = coeffs

            second_derivative = 2 * a
            first_derivative = 2 * a * np.mean(rps) + b

            predicted = np.polyval(coeffs, rps)
            ss_res = np.sum((latency - predicted) ** 2)
            ss_tot = np.sum((latency - np.mean(latency)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            inflection_rps = None
            if abs(a) > 1e-10:
                inflection = -b / (2 * a)
                if rps.min() <= inflection <= rps.max() * 1.5:
                    inflection_rps = inflection

            return DerivativeAnalysis(
                first_derivative=first_derivative,
                second_derivative=second_derivative,
                r_squared=r_squared,
                inflection_rps=inflection_rps,
            )
        except Exception:
            return None