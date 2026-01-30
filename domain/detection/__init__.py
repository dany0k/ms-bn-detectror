from .base import BottleneckDetector, DetectionResult, Severity
from .slope_detector import SlopeDetector
from .threshold_detector import ThresholdDetector
from .derivative_detector import SecondDerivativeDetector  # Добавить

__all__ = [
    'BottleneckDetector',
    'DetectionResult',
    'Severity',
    'SlopeDetector',
    'ThresholdDetector',
    'SecondDerivativeDetector',
]