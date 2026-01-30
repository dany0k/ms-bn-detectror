"""
Детектор bottleneck на основе наклона latency/rps.

Идея: если latency растёт пропорционально RPS, это признак bottleneck.
Вычисляет линейную регрессию и проверяет наклон.
"""

import statistics
from typing import List, Optional

from ..models import Sample
from .base import BaseDetector, DetectionResult, Severity


class SlopeDetector(BaseDetector):
    """
    Детектор на основе наклона кривой latency(rps).
    
    Bottleneck детектируется когда:
    1. Наклон dLatency/dRPS превышает порог
    2. Средний RPS выше минимума (чтобы исключить шум при низкой нагрузке)
    3. Средняя latency выше warn-порога
    """
    
    def __init__(
        self,
        min_samples: int = 10,
        stability_window: int = 3,
        rps_min: float = 5.0,
        slope_critical: float = 2.0,
        latency_warn: float = 150.0,
    ):
        super().__init__(min_samples)
        self.stability_window = stability_window
        self.rps_min = rps_min
        self.slope_critical = slope_critical
        self.latency_warn = latency_warn
    
    @property
    def name(self) -> str:
        return "SlopeDetector"
    
    def analyze(
        self,
        samples: List[Sample],
        src: str,
        dst: str
    ) -> Optional[DetectionResult]:
        """
        Анализирует samples и возвращает результат.
        
        Алгоритм:
        1. Проверяем достаточность данных
        2. Вычисляем наклон линейной регрессии latency(rps)
        3. Проверяем последние stability_window точек
        4. Если условия bottleneck выполнены — возвращаем результат
        """
        if not self._has_enough_samples(samples):
            return None
        
        slope = self._compute_slope(samples)
        
        # Берём последние точки для оценки стабильности
        recent = samples[-self.stability_window:]
        if len(recent) < self.stability_window:
            return None
        
        avg_rps = statistics.mean(s.rps for s in recent)
        avg_latency = statistics.mean(s.latency for s in recent)
        
        # Проверяем условия bottleneck
        if (
            slope > self.slope_critical
            and avg_rps > self.rps_min
            and avg_latency > self.latency_warn
        ):
            return DetectionResult(
                src=src,
                dst=dst,
                severity=Severity.CRITICAL,
                detector_name=self.name,
                message=(
                    f"High latency growth detected: "
                    f"dLatency/dRPS={slope:.2f} ms/rps, "
                    f"avg_rps={avg_rps:.1f}, "
                    f"avg_latency={avg_latency:.1f}ms"
                ),
                slope=slope,
                avg_rps=avg_rps,
                avg_latency=avg_latency,
            )
        
        return None
    
    def _compute_slope(self, samples: List[Sample]) -> float:
        """
        Вычисляет наклон линейной регрессии latency(rps).
        
        Использует метод наименьших квадратов.
        
        Returns:
            Наклон (dLatency/dRPS) в ms на единицу RPS
        """
        if len(samples) < 5:
            return 0.0
        
        # ВАЖНО: правильный порядок распаковки!
        rps_vals = [s.rps for s in samples]
        lat_vals = [s.latency for s in samples]
        
        # Проверяем вариацию RPS
        if len(set(rps_vals)) < 2:
            return 0.0
        
        mean_rps = statistics.mean(rps_vals)
        mean_lat = statistics.mean(lat_vals)
        
        # Линейная регрессия: slope = Σ((x-x̄)(y-ȳ)) / Σ((x-x̄)²)
        numerator = sum(
            (r - mean_rps) * (l - mean_lat)
            for r, l in zip(rps_vals, lat_vals)
        )
        denominator = sum((r - mean_rps) ** 2 for r in rps_vals)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
