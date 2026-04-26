from __future__ import annotations

from app.controller.context import ControllerContext
from app.controller.edge_controller import EdgeController
from app.controller.legacy_controller import LegacyController
from app.controller.load_controller import LoadController
from app.controller.project_controller import ProjectController
from app.controller.snapshot_controller import SnapshotController
from app.repository.db.project_repository import ProjectRepository
from app.service.analysis_service import AnalysisService
from app.service.detection_service import DetectionService
from app.service.edge_service import EdgeService
from flask import Flask


class ApiController:
    """
    Thin assembler: creates shared ControllerContext and wires
    all sub-controllers to the Flask app.

    Sub-controllers:
      LegacyController    — /api/load, /api/edges, /api/detect (backward compat)
      ProjectController   — CRUD /api/projects
      LoadController      — POST /api/projects/<id>/load, GET /api/browse
      EdgeController      — GET  /api/projects/<id>/edges + analyse
      SnapshotController  — GET  /api/projects/<id>/snapshots
    """

    def __init__(
            self,
            app: Flask,
            edge_service: EdgeService,
            analysis_service: AnalysisService,
            detection_service: DetectionService,
            project_repository: ProjectRepository,
    ) -> None:
        ctx = ControllerContext(
            edge_service=edge_service,
            analysis_service=analysis_service,
            detection_service=detection_service,
            project_repository=project_repository,
        )

        LegacyController(app, ctx)
        ProjectController(app, ctx)
        LoadController(app, ctx)
        EdgeController(app, ctx)
        SnapshotController(app, ctx)
