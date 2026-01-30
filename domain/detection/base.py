"""
Базовые абстракции для детекции bottleneck.

Определяет протокол BottleneckDetector и структуру результата DetectionResult.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, List, Optional, runtime_checkable
from enum import Enum

from ..models import Sample


class Severity(str, Enum):
    """Уровень серьёзности проблемы"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DetectionResult:
    """
    Результат детекции bottleneck.
    
    Immutable value object с информацией о найденной проблеме.
    """
    src: str
    dst: str
    severity: Severity
    detector_name: str
    message: str
    
    # Метрики (опциональные, зависят от детектора)
    slope: Optional[float] = None
    avg_rps: Optional[float] = None
    avg_latency: Optional[float] = None
    threshold_exceeded: Optional[float] = None
    
    @property
    def edge_key(self) -> tuple[str, str]:
        """Ключ ребра"""
        return (self.src, self.dst)
    
    @property
    def route(self) -> str:
        """Строковое представление маршрута"""
        return f"{self.src} → {self.dst}"
    
    def to_dict(self) -> dict:
        """Конвертирует в словарь"""
        return {
            "type": self.severity.value,
            "detector": self.detector_name,
            "title": f"Bottleneck detected by {self.detector_name}",
            "message": self.message,
            "route": self.route,
            "meta": {
                "slope": self.slope,
                "avg_rps": self.avg_rps,
                "avg_latency": self.avg_latency,
                "threshold_exceeded": self.threshold_exceeded,
            }
        }


@runtime_checkable
class BottleneckDetector(Protocol):
    """
    Протокол для детекторов bottleneck.
    
    Каждый детектор реализует свою стратегию обнаружения.
    """
    
    @property
    def name(self) -> str:
        """Имя детектора для логов и отчётов"""
        ...
    
    def analyze(
        self,
        samples: List[Sample],
        src: str,
        dst: str
    ) -> Optional[DetectionResult]:
        """
        Анализирует samples и возвращает результат.
        
        Args:
            samples: Список измерений для ребра
            src: Имя исходного узла
            dst: Имя целевого узла
            
        Returns:
            DetectionResult если bottleneck найден, иначе None
        """
        ...


class BaseDetector(ABC):
    """
    Абстрактный базовый класс для детекторов.
    
    Предоставляет общую функциональность.
    """
    
    def __init__(self, min_samples: int = 10):
        self.min_samples = min_samples
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя детектора"""
        pass
    
    @abstractmethod
    def analyze(
        self,
        samples: List[Sample],
        src: str,
        dst: str
    ) -> Optional[DetectionResult]:
        """Анализирует samples"""
        pass
    
    def _has_enough_samples(self, samples: List[Sample]) -> bool:
        """Проверяет достаточность данных"""
        return len(samples) >= self.min_samples
