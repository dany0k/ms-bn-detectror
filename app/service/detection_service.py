from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

from app.model.analys.analysis_result import AnalysisResult
from app.model.analys.rps_bin import RpsBin
from app.model.detection.detection_result import DetectionResult
from app.service.analysis_service import AnalysisService

logger: logging.Logger = logging.getLogger(__name__)


class DetectionService:

    _MIN_RELIABLE_BINS: int = 3
    _WARNING_GROWTH_THRESHOLD:  float = 1.5
    _CRITICAL_GROWTH_THRESHOLD: float = 3.0

    def __init__(self, analysis_service: AnalysisService) -> None:
        self._analysis_service: AnalysisService = analysis_service

    def detect_file(self, file_path: Path) -> List[DetectionResult]:
        results: List[AnalysisResult] = self._analysis_service.analyse_file(file_path)
        return [self.detect(result) for result in results]

    def detect_dir(self, dir_path: Path) -> List[DetectionResult]:
        results: List[AnalysisResult] = self._analysis_service.analyse_dir(dir_path)
        return [self.detect(result) for result in results]

    def detect(self, analysis: AnalysisResult) -> DetectionResult:
        reliable_bins: List[RpsBin] = [b for b in analysis.rps_bins if b.is_reliable]

        if len(reliable_bins) < self._MIN_RELIABLE_BINS:
            return DetectionResult(
                edge_name=analysis.edge_name,
                is_bottleneck=False,
                severity='ok',
                message='Недостаточно данных для детекции',
                onset_rps=None,
                p95_growth=0.0,
            )

        p95_values: List[float] = [b.p95_ms for b in reliable_bins]
        rps_centers: List[float] = [b.rps_center for b in reliable_bins]

        is_accelerating: bool = self._is_accelerating(p95_values)
        p95_growth: float = self._compute_growth(p95_values)
        onset_rps: Optional[float] = self._find_onset_rps(rps_centers, p95_values)
        severity: str = self._compute_severity(p95_growth)

        if not is_accelerating or severity == 'ok':
            return DetectionResult(
                edge_name=analysis.edge_name,
                is_bottleneck=False,
                severity='ok',
                message='P95 не растёт ускоренно с ростом RPS',
                onset_rps=None,
                p95_growth=p95_growth,
            )

        message: str = self._build_message(p95_growth, onset_rps)

        logger.info(f"{analysis.edge_name}: bottleneck={severity}, growth={p95_growth:.1f}x, onset_rps={onset_rps}")

        return DetectionResult(
            edge_name=analysis.edge_name,
            is_bottleneck=True,
            severity=severity,
            message=message,
            onset_rps=onset_rps,
            p95_growth=p95_growth,
        )

    def _is_accelerating(self, p95_values: List[float]) -> bool:
        p95_arr: np.ndarray = np.array(p95_values, dtype=float)

        # метод конечных разностей (скорость изменения скорости)
        d1: np.ndarray = np.diff(p95_arr)
        d2: np.ndarray = np.diff(d1)

        if len(d2) == 0:
            return False

        avg_d2: float = float(np.mean(d2))

        # Или лучше сделать чтобы все точки были положительные?
        is_avg_positive: bool = avg_d2 > 0
        is_growing: bool = p95_values[-1] > p95_values[0]

        return is_avg_positive and is_growing

    def _compute_growth(self, p95_values: List[float]) -> float:
        first: float = p95_values[0]
        last: float  = p95_values[-1]

        if first <= 0:
            return 0.0

        return last / first

    def _find_onset_rps(self, rps_centers: List[float], p95_values:  List[float]) -> Optional[float]:
        p95_list: np.ndarray = np.array(p95_values, dtype=float)
        d1: np.ndarray = np.diff(p95_list)

        if len(d1) == 0:
            return None

        mean_diff: float = float(np.mean(np.abs(d1)))

        if mean_diff <= 0:
            return None

        for i in range(len(d1)):
            if d1[i] > mean_diff: # Прирост больше чем средний. Не уверен. Возможно нужно брать удвоенное значение
                return rps_centers[i]

        return None

    def _compute_severity(self, p95_growth: float) -> str:
        if p95_growth >= self._CRITICAL_GROWTH_THRESHOLD:
            return 'critical'
        if p95_growth >= self._WARNING_GROWTH_THRESHOLD:
            return 'warning'
        return 'ok'

    def _build_message(self, p95_growth: float, onset_rps: Optional[float]) -> str:
        message: str = f"P95 вырос в {p95_growth:.1f}x с ростом RPS"

        if onset_rps is not None:
            message += f", начало при RPS={onset_rps:.0f}"

        return message