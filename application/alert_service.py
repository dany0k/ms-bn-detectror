"""
Сервис управления алертами.

Агрегирует результаты детекции и предоставляет общую картину.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import defaultdict

from domain.detection import DetectionResult, Severity


logger = logging.getLogger(__name__)


@dataclass
class AlertSummary:
    """Сводка по алертам"""
    total: int = 0
    by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_detector: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_edge: Dict[tuple, List[DetectionResult]] = field(
        default_factory=lambda: defaultdict(list)
    )


class AlertService:
    """
    Сервис для работы с алертами.
    
    Собирает, фильтрует и агрегирует результаты детекции.
    """
    
    def __init__(self):
        self._alerts: List[DetectionResult] = []
    
    def add(self, alert: DetectionResult) -> None:
        """Добавляет алерт"""
        self._alerts.append(alert)
        logger.info(
            f"Alert added: [{alert.severity.value}] "
            f"{alert.route} - {alert.detector_name}"
        )
    
    def add_many(self, alerts: List[DetectionResult]) -> None:
        """Добавляет несколько алертов"""
        for alert in alerts:
            self.add(alert)
    
    def get_all(self) -> List[DetectionResult]:
        """Возвращает все алерты"""
        return list(self._alerts)
    
    def get_by_severity(self, severity: Severity) -> List[DetectionResult]:
        """Фильтрует по severity"""
        return [a for a in self._alerts if a.severity == severity]
    
    def get_by_edge(self, src: str, dst: str) -> List[DetectionResult]:
        """Фильтрует по ребру"""
        return [a for a in self._alerts if a.src == src and a.dst == dst]
    
    def get_critical(self) -> List[DetectionResult]:
        """Возвращает критические алерты"""
        return self.get_by_severity(Severity.CRITICAL)
    
    def get_warnings(self) -> List[DetectionResult]:
        """Возвращает предупреждения"""
        return self.get_by_severity(Severity.WARNING)
    
    def clear(self) -> None:
        """Очищает все алерты"""
        self._alerts.clear()
    
    def summarize(self) -> AlertSummary:
        """Создаёт сводку по всем алертам"""
        summary = AlertSummary(total=len(self._alerts))
        
        for alert in self._alerts:
            summary.by_severity[alert.severity.value] += 1
            summary.by_detector[alert.detector_name] += 1
            summary.by_edge[alert.edge_key].append(alert)
        
        return summary
    
    @property
    def overall_status(self) -> str:
        """
        Общий статус системы на основе алертов.
        
        Returns:
            'ok', 'warning', или 'critical'
        """
        critical_count = len(self.get_critical())
        warning_count = len(self.get_warnings())
        
        if critical_count >= 3:
            return "critical"
        elif warning_count >= 3 or critical_count >= 1:
            return "warning"
        return "ok"
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Конвертирует в список словарей"""
        return [alert.to_dict() for alert in self._alerts]
