"""
Доменные модели данных.

Все модели здесь — чистые data classes без внешних зависимостей.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, Deque, Optional, List
from collections import deque
import statistics


class Sample(NamedTuple):
    """
    Единица измерения для ребра графа.
    
    Порядок полей:
    (timestamp, rps, latency)
    """
    timestamp: float
    rps: float
    latency: float


@dataclass(frozen=True)
class LogEntry:
    """
    Одна запись лога — immutable value object.
    
    Создаётся из CSV строки и содержит все данные одного span'а.
    """
    trace_id: str
    span_id: str
    parent_span_id: str
    timestamp: datetime
    src_service: str
    src_route: str
    dst_service: str
    dst_route: str
    latency_ms: float
    latency: float
    rps: float
    
    @property
    def edge_key(self) -> tuple[str, str]:
        """Уникальный ключ ребра графа: (source_node, destination_node)"""
        src = f"{self.src_service}{self.src_route}"
        dst = f"{self.dst_service}{self.dst_route}"
        return (src, dst)
    
    @property
    def src_node(self) -> str:
        """Полное имя исходного узла"""
        return f"{self.src_service}{self.src_route}"
    
    @property
    def dst_node(self) -> str:
        """Полное имя целевого узла"""
        return f"{self.dst_service}{self.dst_route}"
    
    def to_sample(self) -> Sample:
        """Конвертирует в Sample для хранения в EdgeMetrics"""
        return Sample(
            timestamp=self.timestamp.timestamp(),
            rps=self.rps,
            latency=self.latency
        )


@dataclass
class EdgeMetrics:
    """
    Метрики ребра графа (связи между двумя сервисами).
    
    Хранит историю измерений (samples) с ограничением по размеру.
    """
    max_samples: int = 1000
    samples: Deque[Sample] = field(default_factory=lambda: deque(maxlen=1000))
    
    def __post_init__(self):
        # Пересоздаём deque с правильным maxlen если нужно
        if not isinstance(self.samples, deque) or self.samples.maxlen != self.max_samples:
            self.samples = deque(self.samples, maxlen=self.max_samples)
    
    def add_sample(self, sample: Sample) -> None:
        """Добавляет новый sample"""
        self.samples.append(sample)
    
    def update(self, timestamp: float, rps: float, latency: float) -> None:
        """Добавляет sample из отдельных значений"""
        self.add_sample(Sample(timestamp, rps, latency))
    
    @property
    def count(self) -> int:
        """Количество samples"""
        return len(self.samples)
    
    @property
    def avg_latency(self) -> float:
        """Средняя latency по всем samples"""
        if not self.samples:
            return 0.0
        return statistics.mean(s.latency for s in self.samples)
    
    @property
    def avg_rps(self) -> float:
        """Средний RPS по всем samples"""
        if not self.samples:
            return 0.0
        return statistics.mean(s.rps for s in self.samples)
    
    @property
    def max_latency(self) -> float:
        """Максимальная latency"""
        if not self.samples:
            return 0.0
        return max(s.latency for s in self.samples)
    
    @property
    def min_rps(self) -> float:
        """Минимальный RPS"""
        if not self.samples:
            return 0.0
        return min(s.rps for s in self.samples)
    
    @property
    def max_rps(self) -> float:
        """Максимальный RPS"""
        if not self.samples:
            return 0.0
        return max(s.rps for s in self.samples)
    
    def get_timestamps(self) -> List[float]:
        """Возвращает список timestamps"""
        return [s.timestamp for s in self.samples]
    
    def get_rps_values(self) -> List[float]:
        """Возвращает список RPS значений"""
        return [s.rps for s in self.samples]
    
    def get_latency_values(self) -> List[float]:
        """Возвращает список latency значений"""
        return [s.latency for s in self.samples]


@dataclass  
class NodeMetrics:
    """
    Метрики узла графа (сервис + endpoint).
    
    Отслеживает входящие и исходящие вызовы.
    """
    name: str
    max_latencies: int = 200
    
    outgoing_calls: int = 0
    outgoing_latencies: List[float] = field(default_factory=list)
    
    incoming_calls: int = 0
    incoming_latencies: List[float] = field(default_factory=list)
    
    bottleneck_score: float = 0.0
    _forced_status: Optional[str] = None
    
    def add_outgoing_call(self, latency: float) -> None:
        """Регистрирует исходящий вызов"""
        self.outgoing_calls += 1
        self.outgoing_latencies.append(latency)
        if len(self.outgoing_latencies) > self.max_latencies:
            self.outgoing_latencies.pop(0)
    
    def add_incoming_call(self, latency: float) -> None:
        """Регистрирует входящий вызов"""
        self.incoming_calls += 1
        self.incoming_latencies.append(latency)
        if len(self.incoming_latencies) > self.max_latencies:
            self.incoming_latencies.pop(0)
    
    @property
    def outgoing_avg_latency(self) -> float:
        """Средняя latency исходящих вызовов"""
        if not self.outgoing_latencies:
            return 0.0
        return statistics.mean(self.outgoing_latencies)
    
    @property
    def incoming_avg_latency(self) -> float:
        """Средняя latency входящих вызовов"""
        if not self.incoming_latencies:
            return 0.0
        return statistics.mean(self.incoming_latencies)
    
    @property
    def total_calls(self) -> int:
        """Общее количество вызовов"""
        return self.incoming_calls + self.outgoing_calls
    
    @property
    def total_avg_latency(self) -> float:
        """Средняя latency всех вызовов"""
        all_latencies = self.incoming_latencies + self.outgoing_latencies
        if not all_latencies:
            return 0.0
        return statistics.mean(all_latencies)
    
    @property
    def max_observed_latency(self) -> float:
        """Максимальная наблюдаемая latency"""
        all_latencies = self.incoming_latencies + self.outgoing_latencies
        if not all_latencies:
            return 0.0
        return max(all_latencies)
    
    @property
    def status(self) -> str:
        """
        Статус узла: 'normal', 'warning', 'critical'
        
        Может быть установлен принудительно через _forced_status
        """
        if self._forced_status is not None:
            return self._forced_status
        
        base_avg = self.incoming_avg_latency or self.total_avg_latency
        
        if base_avg > 200:
            return "critical"
        elif base_avg > 100:
            return "warning"
        return "normal"
    
    @status.setter
    def status(self, value: str) -> None:
        """Принудительно устанавливает статус"""
        if value not in ('normal', 'warning', 'critical', None):
            raise ValueError(f"Invalid status: {value}")
        self._forced_status = value
