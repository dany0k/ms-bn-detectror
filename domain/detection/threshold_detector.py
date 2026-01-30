"""
Детектор bottleneck на основе адаптивных порогов.

Идея: вычисляем статистику по всем рёбрам и детектируем выбросы.
"""

import statistics
from typing import List, Optional, Callable

from ..models import Sample
from .base import BaseDetector, DetectionResult, Severity


class ThresholdDetector(BaseDetector):
    """
    Детектор на основе порогов latency.
    
    Поддерживает два режима:
    1. Статические пороги (warn/critical заданы явно)
    2. Адаптивные пороги (вычисляются из статистики)
    """
    
    def __init__(
        self,
        min_samples: int = 10,
        latency_warn: float = 150.0,
        latency_critical: float = 250.0,
        adaptive: bool = False,
        adaptive_sigma_warn: float = 1.0,
        adaptive_sigma_critical: float = 2.0,
    ):
        super().__init__(min_samples)
        self.latency_warn = latency_warn
        self.latency_critical = latency_critical
        self.adaptive = adaptive
        self.adaptive_sigma_warn = adaptive_sigma_warn
        self.adaptive_sigma_critical = adaptive_sigma_critical
        
        # Для адаптивного режима: функция получения глобальной статистики
        self._global_stats_fn: Optional[Callable[[], tuple[float, float]]] = None
    
    @property
    def name(self) -> str:
        return "ThresholdDetector"
    
    def set_global_stats_provider(
        self,
        fn: Callable[[], tuple[float, float]]
    ) -> None:
        """
        Устанавливает функцию для получения глобальной статистики.
        
        Args:
            fn: Функция, возвращающая (median_latency, stddev_latency)
        """
        self._global_stats_fn = fn
    
    def analyze(
        self,
        samples: List[Sample],
        src: str,
        dst: str
    ) -> Optional[DetectionResult]:
        """
        Анализирует samples и возвращает результат.
        
        Проверяет среднюю latency против порогов.
        """
        if not self._has_enough_samples(samples):
            return None
        
        avg_latency = statistics.mean(s.latency for s in samples)
        
        # Получаем пороги
        warn_threshold, critical_threshold = self._get_thresholds()
        
        # Проверяем critical
        if avg_latency > critical_threshold:
            return DetectionResult(
                src=src,
                dst=dst,
                severity=Severity.CRITICAL,
                detector_name=self.name,
                message=(
                    f"Latency exceeds critical threshold: "
                    f"{avg_latency:.1f}ms > {critical_threshold:.1f}ms"
                ),
                avg_latency=avg_latency,
                threshold_exceeded=critical_threshold,
            )
        
        # Проверяем warning
        if avg_latency > warn_threshold:
            return DetectionResult(
                src=src,
                dst=dst,
                severity=Severity.WARNING,
                detector_name=self.name,
                message=(
                    f"Latency exceeds warning threshold: "
                    f"{avg_latency:.1f}ms > {warn_threshold:.1f}ms"
                ),
                avg_latency=avg_latency,
                threshold_exceeded=warn_threshold,
            )
        
        return None
    
    def _get_thresholds(self) -> tuple[float, float]:
        """
        Возвращает (warn_threshold, critical_threshold).
        
        В адаптивном режиме вычисляет из глобальной статистики.
        """
        if not self.adaptive or self._global_stats_fn is None:
            return self.latency_warn, self.latency_critical
        
        median, stddev = self._global_stats_fn()
        
        warn = median + self.adaptive_sigma_warn * stddev
        critical = median + self.adaptive_sigma_critical * stddev
        
        # Не опускаемся ниже минимальных значений
        warn = max(warn, self.latency_warn)
        critical = max(critical, self.latency_critical)
        
        return warn, critical
