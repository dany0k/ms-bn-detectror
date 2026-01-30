"""
Тесты для Bottleneck Detector.
"""

import pytest
from datetime import datetime
from collections import deque

from bn_detector.domain.models import Sample, LogEntry, EdgeMetrics, NodeMetrics
from bn_detector.domain.graph import ServiceGraph
from bn_detector.domain.detection import SlopeDetector, ThresholdDetector, Severity


class TestSample:
    """Тесты для Sample"""
    
    def test_sample_creation(self):
        s = Sample(timestamp=1000.0, rps=50.0, latency=10.5)
        assert s.timestamp == 1000.0
        assert s.rps == 50.0
        assert s.latency == 10.5
    
    def test_sample_is_immutable(self):
        s = Sample(1000.0, 50.0, 10.5)
        with pytest.raises(AttributeError):
            s.timestamp = 2000.0


class TestLogEntry:
    """Тесты для LogEntry"""
    
    def test_log_entry_edge_key(self):
        entry = LogEntry(
            trace_id="t1",
            span_id="s1",
            parent_span_id="",
            timestamp=datetime.now(),
            src_service="api",
            src_route="/users",
            dst_service="db",
            dst_route="/query",
            latency_ms=10.0,
            latency=10.5,
            rps=100.0,
        )
        assert entry.edge_key == ("api/users", "db/query")
        assert entry.src_node == "api/users"
        assert entry.dst_node == "db/query"
    
    def test_to_sample(self):
        ts = datetime(2025, 1, 1, 12, 0, 0)
        entry = LogEntry(
            trace_id="t1",
            span_id="s1", 
            parent_span_id="",
            timestamp=ts,
            src_service="api",
            src_route="/users",
            dst_service="db",
            dst_route="/query",
            latency_ms=10.0,
            latency=10.5,
            rps=100.0,
        )
        sample = entry.to_sample()
        assert sample.timestamp == ts.timestamp()
        assert sample.rps == 100.0
        assert sample.latency == 10.5


class TestEdgeMetrics:
    """Тесты для EdgeMetrics"""
    
    def test_empty_edge(self):
        edge = EdgeMetrics()
        assert edge.count == 0
        assert edge.avg_latency == 0.0
        assert edge.avg_rps == 0.0
    
    def test_add_samples(self):
        edge = EdgeMetrics()
        edge.add_sample(Sample(1000.0, 50.0, 10.0))
        edge.add_sample(Sample(1001.0, 60.0, 20.0))
        
        assert edge.count == 2
        assert edge.avg_latency == 15.0
        assert edge.avg_rps == 55.0
        assert edge.min_rps == 50.0
        assert edge.max_rps == 60.0
    
    def test_max_samples_limit(self):
        edge = EdgeMetrics(max_samples=5)
        for i in range(10):
            edge.add_sample(Sample(float(i), float(i), float(i)))
        
        assert edge.count == 5
        # Должны остаться последние 5
        assert edge.get_timestamps() == [5.0, 6.0, 7.0, 8.0, 9.0]


class TestServiceGraph:
    """Тесты для ServiceGraph"""
    
    def test_empty_graph(self):
        graph = ServiceGraph()
        assert graph.node_count == 0
        assert graph.edge_count == 0
    
    def test_add_sample(self):
        graph = ServiceGraph()
        sample = Sample(1000.0, 50.0, 10.0)
        graph.add_sample("A", "B", sample)
        
        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert graph.get_edge("A", "B") is not None
        assert graph.get_edge("A", "B").count == 1
    
    def test_mark_bottleneck(self):
        graph = ServiceGraph()
        graph.add_sample("A", "B", Sample(1000.0, 50.0, 10.0))
        
        assert not graph.is_bottleneck("A", "B")
        graph.mark_bottleneck("A", "B")
        assert graph.is_bottleneck("A", "B")
    
    def test_export(self):
        graph = ServiceGraph()
        graph.add_sample("A", "B", Sample(1000.0, 50.0, 10.0))
        
        exported = graph.export()
        assert len(exported["nodes"]) == 2
        assert len(exported["edges"]) == 1
        assert exported["edges"][0]["source"] == "A"
        assert exported["edges"][0]["target"] == "B"


class TestSlopeDetector:
    """Тесты для SlopeDetector"""
    
    def test_not_enough_samples(self):
        detector = SlopeDetector(min_samples=10)
        samples = [Sample(float(i), 50.0, 10.0) for i in range(5)]
        
        result = detector.analyze(samples, "A", "B")
        assert result is None
    
    def test_no_bottleneck_stable_latency(self):
        detector = SlopeDetector(
            min_samples=10,
            slope_critical=2.0,
            latency_warn=150.0,
        )
        # Стабильная latency независимо от RPS
        samples = [
            Sample(float(i), float(20 + i), 10.0 + (i % 2))  # latency ~10ms
            for i in range(20)
        ]
        
        result = detector.analyze(samples, "A", "B")
        assert result is None
    
    def test_detects_bottleneck(self):
        detector = SlopeDetector(
            min_samples=10,
            stability_window=3,
            rps_min=5.0,
            slope_critical=1.0,  # Низкий порог для теста
            latency_warn=50.0,   # Низкий порог для теста
        )
        # Latency растёт с RPS
        samples = [
            Sample(float(i), float(20 + i * 2), float(50 + i * 5))  # latency растёт
            for i in range(20)
        ]
        
        result = detector.analyze(samples, "A", "B")
        assert result is not None
        assert result.severity == Severity.CRITICAL
        assert result.src == "A"
        assert result.dst == "B"


class TestThresholdDetector:
    """Тесты для ThresholdDetector"""
    
    def test_normal_latency(self):
        detector = ThresholdDetector(
            min_samples=5,
            latency_warn=100.0,
            latency_critical=200.0,
        )
        samples = [Sample(float(i), 50.0, 50.0) for i in range(10)]
        
        result = detector.analyze(samples, "A", "B")
        assert result is None
    
    def test_warning_latency(self):
        detector = ThresholdDetector(
            min_samples=5,
            latency_warn=100.0,
            latency_critical=200.0,
        )
        samples = [Sample(float(i), 50.0, 150.0) for i in range(10)]
        
        result = detector.analyze(samples, "A", "B")
        assert result is not None
        assert result.severity == Severity.WARNING
    
    def test_critical_latency(self):
        detector = ThresholdDetector(
            min_samples=5,
            latency_warn=100.0,
            latency_critical=200.0,
        )
        samples = [Sample(float(i), 50.0, 250.0) for i in range(10)]
        
        result = detector.analyze(samples, "A", "B")
        assert result is not None
        assert result.severity == Severity.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
