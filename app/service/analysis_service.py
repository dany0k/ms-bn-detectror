from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np

from app.model.analys.analysis_result import AnalysisResult, RpsBin, SecondAggregate
from app.model.edge.edge import Edge
from app.service.edge_service import EdgeService

logger: logging.Logger = logging.getLogger(__name__)

class AnalysisService:
    _MIN_RECORDS_PER_BIN: int = 10
    _MIN_RECORDS_PER_SECOND: int = 10

    def __init__(self, edge_service: EdgeService) -> None:
        self._edge_service: EdgeService = edge_service

    def analyse_file(self, file_path: Path) -> List[AnalysisResult]:
        edges: List[Edge] = self._edge_service.get_edges_from_file(file_path)
        return self._analyse_edges(edges)

    def analyse_dir(self, dir_path: Path) -> List[AnalysisResult]:
        edges: List[Edge] = self._edge_service.get_edges_from_dir(dir_path)
        return self._analyse_edges(edges)

    def analyse_edge(self, edge: Edge) -> AnalysisResult:
        if edge.records_amount == 0:
            raise ValueError(f"Edge {edge.display_name} has no records")

        latencies: np.ndarray = np.array([r.latency_ms for r in edge.records], dtype=float)
        rps_values: np.ndarray = np.array([r.rps for r in edge.records], dtype=float)
        timestamps: np.ndarray = np.array([r.timestamp for r in edge.records], dtype=float)

        rps_bins: List[RpsBin] = self._compute_rps_bins(latencies, rps_values)
        per_second: List[SecondAggregate] = self._compute_per_second(timestamps, latencies, rps_values)

        result: AnalysisResult = AnalysisResult(
            edge_name=edge.display_name,
            global_min_ms=float(np.min(latencies)),
            global_max_ms=float(np.max(latencies)),
            global_p50_ms=float(np.percentile(latencies, 50)),
            global_p75_ms=float(np.percentile(latencies, 75)),
            global_p95_ms=float(np.percentile(latencies, 95)),
            raw_latencies=latencies.tolist(),
            raw_timestamps=timestamps.tolist(),
            total_records=edge.records_amount,
            rps_bins=rps_bins,
            per_second=per_second,
        )

        return result

    def _analyse_edges(self, edges: List[Edge]) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []

        for edge in edges:
            result: AnalysisResult = self.analyse_edge(edge)
            results.append(result)

        return results

    def _compute_rps_bins(
            self,
            latencies: np.ndarray,
            rps_values: np.ndarray,
    ) -> List[RpsBin]:
        rps_min: float = float(rps_values.min())
        rps_max: float = float(rps_values.max())

        if rps_max - rps_min <= 0:
            return []

        # Либо использовать констунту, либо формулу Стёрджеса, мб есть еще какие-то формулы
        # https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%BE_%D0%A1%D1%82%D1%91%D1%80%D0%B4%D0%B6%D0%B5%D1%81%D0%B0
        bin_amount: int = int(1 + np.log2(len(rps_values)))
        bin_size: float = (rps_max - rps_min) / bin_amount
        bins: List[RpsBin] = []

        for i in range(bin_amount):
            bin_left_border: float = rps_min + i * bin_size
            bin_right_border: float = rps_min + (i + 1) * bin_size

            bin_latencies: List[float] = []

            for j in range(len(rps_values)):
                if bin_left_border <= rps_values[j] < bin_right_border:
                    bin_latencies.append(float(latencies[j]))

            if len(bin_latencies) == 0:
                continue

            bin_arr: np.ndarray = np.array(bin_latencies, dtype=float)
            rps_bin: RpsBin = RpsBin(
                rps_center=round((bin_left_border + bin_right_border) / 2.0, 1),
                p50_ms=float(np.percentile(bin_arr, 50)),
                p75_ms=float(np.percentile(bin_arr, 75)),
                p95_ms=float(np.percentile(bin_arr, 95)),
                count=len(bin_latencies),
                is_reliable=len(bin_latencies) >= self._MIN_RECORDS_PER_BIN
            )
            bins.append(rps_bin)

        return bins

    def _compute_per_second(self, timestamps: np.ndarray, latencies: np.ndarray, rps_values: np.ndarray) -> List[SecondAggregate]:
        lats_rps_by_sec: Dict[int, Dict] = defaultdict(lambda: {'lats': [], 'rps': 0.0})

        for i in range(len(timestamps)):
            sec: int = int(timestamps[i])
            lats_rps_by_sec[sec]['lats'].append(float(latencies[i]))
            lats_rps_by_sec[sec]['rps'] = float(rps_values[i])

        secs_sorted: List[int] = sorted(lats_rps_by_sec.keys())
        result: List[SecondAggregate] = []

        for sec in secs_sorted:
            sec_latencies: List[float] = lats_rps_by_sec[sec]['lats']
            sec_arr: np.ndarray = np.array(sec_latencies, dtype=float)
            count: int = len(sec_latencies)

            aggregate: SecondAggregate = SecondAggregate(
                timestamp=float(sec),
                p50_ms=float(np.percentile(sec_arr, 50)),
                p75_ms=float(np.percentile(sec_arr, 75)),
                p95_ms=float(np.percentile(sec_arr, 95)),
                rps=lats_rps_by_sec[sec]['rps'],
                lat=lats_rps_by_sec[sec]['lats'],
                count=count,
                is_reliable=count >= self._MIN_RECORDS_PER_SECOND,
            )
            result.append(aggregate)

        return result
