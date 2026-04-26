from __future__ import annotations

from typing import Dict, List

from app.model.detection.detection_result import DetectionResult
from app.model.edge.edge import Edge
from app.repository.db.project_repository import ProjectRepository
from app.service.analysis_service import AnalysisService
from app.service.detection_service import DetectionService
from app.service.edge_service import EdgeService


class ControllerContext:
    """Shared services injected into every sub-controller."""

    def __init__(
            self,
            edge_service: EdgeService,
            analysis_service: AnalysisService,
            detection_service: DetectionService,
            project_repository: ProjectRepository,
    ) -> None:
        self.edge_service = edge_service
        self.analysis_service = analysis_service
        self.detection_service = detection_service
        self.project_repo = project_repository

        # Legacy in-memory cache (for /api/load backward compat only)
        self.cached_edges: List[Edge] = []
        self.cached_detection: Dict[str, DetectionResult] = {}
        self.cached_analysis: Dict[str, object] = {}
