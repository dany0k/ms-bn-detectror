"""
Главный сервис анализа логов.

LogAnalyzer оркестрирует все компоненты системы.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from domain import ServiceGraph
from domain.detection import BottleneckDetector, DetectionResult
from infrastructure.readers import LogReader


logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    """
    Результат анализа логов.
    
    Содержит граф сервисов, обнаруженные проблемы и сгенерированные графики.
    """
    graph: ServiceGraph
    alerts: List[DetectionResult] = field(default_factory=list)
    plots: List[Path] = field(default_factory=list)
    logs_processed: int = 0
    
    @property
    def has_critical(self) -> bool:
        """Есть ли критические проблемы"""
        return any(a.severity.value == "critical" for a in self.alerts)
    
    @property
    def has_warnings(self) -> bool:
        """Есть ли предупреждения"""
        return any(a.severity.value == "warning" for a in self.alerts)
    
    @property
    def status(self) -> str:
        """Общий статус: 'ok', 'warning', 'critical'"""
        critical_count = sum(1 for a in self.alerts if a.severity.value == "critical")
        warning_count = sum(1 for a in self.alerts if a.severity.value == "warning")
        
        if critical_count >= 3:
            return "critical"
        elif warning_count >= 3 or critical_count >= 1:
            return "warning"
        return "ok"
    
    def summary(self) -> str:
        """Текстовое описание результатов"""
        lines = [
            f"Analysis Report",
            f"===============",
            f"Status: {self.status.upper()}",
            f"Logs processed: {self.logs_processed}",
            f"Nodes: {self.graph.node_count}",
            f"Edges: {self.graph.edge_count}",
            f"Bottlenecks: {len(self.graph.bottleneck_edges)}",
            f"Alerts: {len(self.alerts)}",
        ]
        
        if self.alerts:
            lines.append("")
            lines.append("Alerts:")
            for alert in self.alerts:
                lines.append(f"  [{alert.severity.value.upper()}] {alert.message}")
        
        if self.plots:
            lines.append("")
            lines.append(f"Plots generated: {len(self.plots)}")
        
        return "\n".join(lines)


class LogAnalyzer:
    """
    Главный сервис анализа логов.
    
    Оркестрирует чтение логов, детекцию bottleneck и визуализацию.
    Использует Dependency Injection для всех компонентов.
    """
    
    def __init__(
        self,
        reader: LogReader,
        graph: Optional[ServiceGraph] = None,
        detectors: Optional[List[BottleneckDetector]] = None,
        plotters: Optional[List] = None,  # List[BasePlotter]
    ):
        """
        Args:
            reader: Источник логов
            graph: Граф сервисов (создаётся новый если не указан)
            detectors: Список детекторов bottleneck
            plotters: Список визуализаторов
        """
        self.reader = reader
        self.graph = graph or ServiceGraph()
        self.detectors = detectors or []
        self.plotters = plotters or []
    
    def run(self) -> AnalysisReport:
        """
        Запускает полный цикл анализа.
        
        1. Читает логи и строит граф
        2. Запускает детекторы на каждом ребре
        3. Генерирует визуализации
        
        Returns:
            AnalysisReport с результатами
        """
        logger.info("Starting analysis...")
        
        # 1. Читаем логи
        logs_count = self._load_logs()
        logger.info(f"Loaded {logs_count} log entries")
        
        if not self.graph.edges:
            logger.warning("No edges in graph after loading logs")
            return AnalysisReport(
                graph=self.graph,
                logs_processed=logs_count,
            )
        
        # 2. Детектим bottlenecks
        alerts = self._run_detectors()
        logger.info(f"Detection complete: {len(alerts)} alerts")
        
        # 3. Визуализация
        plots = self._generate_plots()
        logger.info(f"Generated {len(plots)} plots")
        
        return AnalysisReport(
            graph=self.graph,
            alerts=alerts,
            plots=plots,
            logs_processed=logs_count,
        )
    
    def _load_logs(self) -> int:
        """Читает логи и заполняет граф"""
        count = 0
        for entry in self.reader.read():
            self.graph.add_log_entry(entry)
            count += 1
        return count
    
    def _run_detectors(self) -> List[DetectionResult]:
        """Запускает все детекторы на всех рёбрах"""
        alerts = []
        
        for (src, dst), edge in self.graph.iter_edges():
            samples = list(edge.samples)
            
            for detector in self.detectors:
                result = detector.analyze(samples, src, dst)
                if result is not None:
                    alerts.append(result)
                    self.graph.mark_bottleneck(src, dst)
        
        return alerts
    
    def _generate_plots(self) -> List[Path]:
        """Генерирует все графики"""
        plots = []
        
        for plotter in self.plotters:
            try:
                generated = plotter.draw()
                if generated:
                    plots.extend(generated)
            except Exception as e:
                logger.error(f"Plotter {plotter.__class__.__name__} failed: {e}")
        
        return plots
