"""
Граф сервисов — структура данных для хранения топологии и метрик.

ServiceGraph — это чистая структура данных без бизнес-логики.
Вся логика детекции вынесена в domain/detection/.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Tuple, Iterator, Any
from collections import deque

from .models import NodeMetrics, EdgeMetrics, LogEntry, Sample


EdgeKey = Tuple[str, str]


@dataclass
class ServiceGraph:
    """
    Граф микросервисов с узлами и рёбрами.
    
    Узел = сервис + endpoint (например: "api-gateway/users")
    Ребро = связь между двумя узлами с метриками latency/rps
    """
    
    nodes: Dict[str, NodeMetrics] = field(default_factory=dict)
    edges: Dict[EdgeKey, EdgeMetrics] = field(default_factory=dict)
    
    # Статистика
    total_logs: int = 0
    recent_logs: deque = field(default_factory=lambda: deque(maxlen=200))
    
    # Результаты анализа (заполняются детекторами)
    bottleneck_edges: Set[EdgeKey] = field(default_factory=set)
    global_max_flow: float = 0.0
    
    # Настройки
    max_samples_per_edge: int = 1000
    
    def _ensure_node(self, name: str) -> NodeMetrics:
        """Создаёт узел если его нет, возвращает существующий"""
        if name not in self.nodes:
            self.nodes[name] = NodeMetrics(name=name)
        return self.nodes[name]
    
    def _ensure_edge(self, key: EdgeKey) -> EdgeMetrics:
        """Создаёт ребро если его нет, возвращает существующее"""
        if key not in self.edges:
            self.edges[key] = EdgeMetrics(max_samples=self.max_samples_per_edge)
        return self.edges[key]
    
    def add_log_entry(self, entry: LogEntry) -> None:
        """
        Добавляет запись лога в граф.
        
        Обновляет узлы, рёбра и общую статистику.
        """
        self.total_logs += 1
        
        # Обновляем узлы
        src_node = self._ensure_node(entry.src_node)
        dst_node = self._ensure_node(entry.dst_node)
        
        src_node.add_outgoing_call(entry.latency)
        dst_node.add_incoming_call(entry.latency)
        
        # Обновляем ребро
        edge = self._ensure_edge(entry.edge_key)
        edge.add_sample(entry.to_sample())
        
        # Сохраняем в recent
        self.recent_logs.append(entry)
    
    def add_sample(self, src: str, dst: str, sample: Sample) -> None:
        """
        Добавляет sample напрямую к ребру.
        
        Более низкоуровневый метод чем add_log_entry.
        """
        self._ensure_node(src)
        self._ensure_node(dst)
        
        edge = self._ensure_edge((src, dst))
        edge.add_sample(sample)
        self.total_logs += 1
    
    def get_edge(self, src: str, dst: str) -> EdgeMetrics | None:
        """Возвращает ребро или None"""
        return self.edges.get((src, dst))
    
    def get_node(self, name: str) -> NodeMetrics | None:
        """Возвращает узел или None"""
        return self.nodes.get(name)
    
    def iter_edges(self) -> Iterator[Tuple[EdgeKey, EdgeMetrics]]:
        """Итератор по рёбрам"""
        yield from self.edges.items()
    
    def iter_nodes(self) -> Iterator[Tuple[str, NodeMetrics]]:
        """Итератор по узлам"""
        yield from self.nodes.items()
    
    def mark_bottleneck(self, src: str, dst: str) -> None:
        """Отмечает ребро как bottleneck"""
        self.bottleneck_edges.add((src, dst))
    
    def is_bottleneck(self, src: str, dst: str) -> bool:
        """Проверяет, является ли ребро bottleneck"""
        return (src, dst) in self.bottleneck_edges
    
    @property
    def node_count(self) -> int:
        """Количество узлов"""
        return len(self.nodes)
    
    @property
    def edge_count(self) -> int:
        """Количество рёбер"""
        return len(self.edges)
    
    def get_incoming_edges(self, node: str) -> List[Tuple[str, EdgeMetrics]]:
        """Возвращает все входящие рёбра для узла"""
        result = []
        for (src, dst), edge in self.edges.items():
            if dst == node:
                result.append((src, edge))
        return result
    
    def get_outgoing_edges(self, node: str) -> List[Tuple[str, EdgeMetrics]]:
        """Возвращает все исходящие рёбра для узла"""
        result = []
        for (src, dst), edge in self.edges.items():
            if src == node:
                result.append((dst, edge))
        return result
    
    def export(self) -> Dict[str, Any]:
        """
        Экспортирует граф в словарь для сериализации.
        
        Формат совместим с визуализаторами графов.
        """
        nodes_out = []
        for name, node in self.nodes.items():
            incoming = self.get_incoming_edges(name)
            load = sum(edge.count for _, edge in incoming)
            avg_lat = 0.0
            if incoming:
                total_lat = sum(
                    sum(edge.get_latency_values()) 
                    for _, edge in incoming
                )
                total_count = sum(edge.count for _, edge in incoming)
                avg_lat = total_lat / total_count if total_count > 0 else 0.0
            
            nodes_out.append({
                "id": name,
                "label": name,
                "load": load,
                "avg_latency": avg_lat,
                "status": node.status,
                "bottleneck_score": node.bottleneck_score,
            })
        
        edges_out = []
        for (src, dst), edge in self.edges.items():
            edges_out.append({
                "id": f"{src}->{dst}",
                "source": src,
                "target": dst,
                "count": edge.count,
                "avg_latency": edge.avg_latency,
                "avg_rps": edge.avg_rps,
                "capacity": round(1.0 / edge.avg_latency, 4) if edge.avg_latency else None,
                "is_bottleneck": (src, dst) in self.bottleneck_edges,
            })
        
        return {
            "nodes": nodes_out,
            "edges": edges_out,
            "total_logs": self.total_logs,
            "max_flow": self.global_max_flow,
            "bottlenecks": [f"{src}->{dst}" for (src, dst) in self.bottleneck_edges],
        }
    
    def export_timeseries(self) -> Dict[EdgeKey, Dict[str, List[float]]]:
        """
        Экспортирует временные ряды для каждого ребра.
        
        Формат для построения графиков.
        """
        result = {}
        
        for (src, dst), edge in self.edges.items():
            if not edge.samples:
                continue
            
            result[(src, dst)] = {
                "timestamps": edge.get_timestamps(),
                "rps": edge.get_rps_values(),
                "latency": edge.get_latency_values(),
            }
        
        return result
    
    def summary(self) -> str:
        """Возвращает текстовое описание графа"""
        lines = [
            f"ServiceGraph: {self.node_count} nodes, {self.edge_count} edges",
            f"Total logs processed: {self.total_logs}",
            f"Bottlenecks detected: {len(self.bottleneck_edges)}",
            "",
            "Edges:"
        ]
        
        for (src, dst), edge in self.edges.items():
            is_bn = "🔴" if (src, dst) in self.bottleneck_edges else "  "
            lines.append(
                f"  {is_bn} {src} → {dst}: "
                f"samples={edge.count}, "
                f"rps=[{edge.min_rps:.0f}, {edge.max_rps:.0f}], "
                f"avg_lat={edge.avg_latency:.1f}ms"
            )
        
        return "\n".join(lines)
