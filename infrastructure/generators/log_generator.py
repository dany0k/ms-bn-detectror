"""
Генератор синтетических логов микросервисов.

Поддерживает:
- Настройку threshold-порогов RPS
- Контроль роста latency для каждого диапазона
- Симуляцию плато (RPS не растёт)
- Разные сценарии для разных edge
"""

import csv
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThresholdConfig:
    """Конфигурация одного порога RPS"""
    rps_limit: float
    latency_stable: bool
    rps_start: float = 0.0
    latency_growth_factor: float = 3.0


@dataclass
class BottleneckScenario:
    """
    Сценарий поведения для одного edge.
    
    Определяет как latency зависит от RPS.
    """
    src_service: str
    src_route: str
    dst_service: str
    dst_route: str
    max_rps: float
    baseline_latency: float
    thresholds: List[ThresholdConfig] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BottleneckScenario':
        """Создаёт из словаря (для загрузки из JSON)"""
        thresholds = [
            ThresholdConfig(
                rps_limit=t['rps_limit'],
                latency_stable=t['latency_stable'],
                rps_start=t.get('rps_start', 0.0),
                latency_growth_factor=t.get('latency_growth_factor', 3.0),
            )
            for t in data.get('thresholds', [])
        ]
        
        return cls(
            src_service=data['src_service'],
            src_route=data['src_route'],
            dst_service=data['dst_service'],
            dst_route=data['dst_route'],
            max_rps=data['max_rps'],
            baseline_latency=data.get('baseline_latency', 10.0),
            thresholds=thresholds,
        )
    
    def get_latency(self, current_rps: float) -> float:
        """
        Вычисляет latency на основе текущего RPS и thresholds.
        
        Args:
            current_rps: Текущий RPS
            
        Returns:
            Latency в миллисекундах
        """
        for threshold in self.thresholds:
            if current_rps <= threshold.rps_limit:
                if threshold.latency_stable:
                    # Стабильная latency с небольшим шумом
                    return self.baseline_latency + random.uniform(-0.4, 0.4)
                else:
                    # Latency растёт с RPS (bottleneck!)
                    rps_range = threshold.rps_limit - threshold.rps_start
                    progress = (current_rps - threshold.rps_start) / max(rps_range, 1)
                    
                    growth = threshold.latency_growth_factor
                    latency = self.baseline_latency + (self.baseline_latency * growth * progress)
                    latency += random.uniform(-1.0, 1.0)
                    
                    return max(latency, 1.0)
        
        # Превысили все пороги — используем последний
        if self.thresholds:
            last = self.thresholds[-1]
            if last.latency_stable:
                return self.baseline_latency + random.uniform(-0.4, 0.4)
            else:
                growth = last.latency_growth_factor
                return self.baseline_latency * (1 + growth) + random.uniform(-2.0, 2.0)
        
        return self.baseline_latency


@dataclass
class GeneratorConfig:
    """Конфигурация генератора"""
    duration_seconds: int = 1200
    start_time: datetime = field(
        default_factory=lambda: datetime.fromisoformat("2025-11-21T15:00:00+00:00")
    )
    initial_rps: float = 20.0
    rps_growth_rate: float = 0.05
    scenarios: List[BottleneckScenario] = field(default_factory=list)
    
    @classmethod
    def from_json(cls, path: Path) -> 'GeneratorConfig':
        """Загружает из JSON файла"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        return cls(
            duration_seconds=data.get('duration_seconds', 1200),
            start_time=datetime.fromisoformat(
                data.get('start_time', "2025-11-21T15:00:00+00:00")
            ),
            initial_rps=data.get('initial_rps', 20.0),
            rps_growth_rate=data.get('rps_growth_rate', 0.05),
            scenarios=[
                BottleneckScenario.from_dict(s)
                for s in data.get('scenarios', [])
            ],
        )
    
    def to_json(self, path: Path) -> None:
        """Сохраняет в JSON файл"""
        data = {
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time.isoformat(),
            'initial_rps': self.initial_rps,
            'rps_growth_rate': self.rps_growth_rate,
            'scenarios': [
                {
                    'src_service': s.src_service,
                    'src_route': s.src_route,
                    'dst_service': s.dst_service,
                    'dst_route': s.dst_route,
                    'max_rps': s.max_rps,
                    'baseline_latency': s.baseline_latency,
                    'thresholds': [
                        {
                            'rps_limit': t.rps_limit,
                            'latency_stable': t.latency_stable,
                            'rps_start': t.rps_start,
                            'latency_growth_factor': t.latency_growth_factor,
                        }
                        for t in s.thresholds
                    ],
                }
                for s in self.scenarios
            ],
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


class LogGenerator:
    """
    Генератор логов с поддержкой bottleneck-сценариев.
    
    Создаёт CSV файл с логами, имитирующими трафик микросервисов.
    """
    
    CSV_HEADER = [
        'traceId', 'spanId', 'parentSpanId', 'timestamp',
        'srcService', 'srcRoute', 'dstService', 'dstRoute',
        'latency_ms', 'latency', 'rps'
    ]
    
    def __init__(self, config: GeneratorConfig):
        self.config = config
    
    @classmethod
    def from_json(cls, path: Path) -> 'LogGenerator':
        """Создаёт генератор из JSON конфига"""
        config = GeneratorConfig.from_json(path)
        return cls(config)
    
    def generate_rps_curve(self) -> List[float]:
        """
        Генерирует кривую RPS с учётом plateau.
        
        Returns:
            Список RPS для каждой секунды
        """
        rps_values = []
        current_rps = self.config.initial_rps
        
        max_rps_limit = max(
            s.max_rps for s in self.config.scenarios
        ) if self.config.scenarios else 100.0
        
        for _ in range(self.config.duration_seconds):
            if current_rps < max_rps_limit:
                # RPS растёт
                current_rps += self.config.rps_growth_rate
                current_rps += random.uniform(-0.1, 0.1)
            else:
                # Плато — RPS не растёт
                current_rps += random.uniform(-0.3, 0.3)
            
            current_rps = max(current_rps, self.config.initial_rps)
            rps_values.append(current_rps)
        
        return rps_values
    
    def generate(self, output_path: Path) -> int:
        """
        Генерирует CSV файл с логами.
        
        Args:
            output_path: Путь для сохранения
            
        Returns:
            Количество сгенерированных записей
        """
        rps_curve = self.generate_rps_curve()
        total_records = 0
        
        logger.info(f"Generating logs to {output_path}")
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_HEADER)
            
            trace_id = 1
            span_id = 1
            
            for second, rps in enumerate(rps_curve):
                timestamp = self.config.start_time + timedelta(seconds=second)
                
                for scenario in self.config.scenarios:
                    parent_span_id = f"span{span_id:05d}"
                    trace_id_str = f"trace{trace_id:05d}"
                    
                    latency = scenario.get_latency(rps)
                    latency_with_noise = latency + random.uniform(-0.5, 0.5)
                    
                    writer.writerow([
                        trace_id_str,
                        parent_span_id,
                        '',  # no parent
                        timestamp.isoformat(),
                        scenario.src_service,
                        scenario.src_route,
                        scenario.dst_service,
                        scenario.dst_route,
                        round(latency, 1),
                        round(latency_with_noise, 1),
                        int(rps),
                    ])
                    
                    span_id += 1
                    trace_id += 1
                    total_records += 1
        
        logger.info(
            f"Generated {total_records} records, "
            f"duration={self.config.duration_seconds}s, "
            f"RPS: {self.config.initial_rps} → {rps_curve[-1]:.1f}"
        )
        
        return total_records


def create_example_config() -> GeneratorConfig:
    """Создаёт пример конфигурации для демонстрации"""
    return GeneratorConfig(
        duration_seconds=1200,
        start_time=datetime.fromisoformat("2025-11-21T15:00:00+00:00"),
        initial_rps=20.0,
        rps_growth_rate=0.05,
        scenarios=[
            # Сценарий 1: Нормальный сервис (без bottleneck)
            BottleneckScenario(
                src_service="recommendation-service",
                src_route="/getUserRecommendations",
                dst_service="cache-service",
                dst_route="/getProfileCache",
                max_rps=80,
                baseline_latency=4.2,
                thresholds=[
                    ThresholdConfig(rps_limit=30, latency_stable=True),
                    ThresholdConfig(rps_limit=50, latency_stable=True),
                    ThresholdConfig(rps_limit=90, latency_stable=True),
                ],
            ),
            # Сценарий 2: Bottleneck после 50 RPS
            BottleneckScenario(
                src_service="recommendation-service",
                src_route="/getUserRecommendations",
                dst_service="db-analytics",
                dst_route="/updateRecStats",
                max_rps=80,
                baseline_latency=17.5,
                thresholds=[
                    ThresholdConfig(
                        rps_limit=30, rps_start=0,
                        latency_stable=True,
                    ),
                    ThresholdConfig(
                        rps_limit=50, rps_start=30,
                        latency_stable=False,
                        latency_growth_factor=0.5,
                    ),
                    ThresholdConfig(
                        rps_limit=90, rps_start=50,
                        latency_stable=False,
                        latency_growth_factor=3.0,  # Сильный рост!
                    ),
                ],
            ),
        ],
    )
