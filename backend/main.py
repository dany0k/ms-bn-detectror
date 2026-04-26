from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure the backend/ directory is on sys.path so that
# 'app.*' imports resolve regardless of how/where you launch main.py
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from flask_cors import CORS

from app.repository.db.models import init_db
from app.repository.db.project_repository import ProjectRepository
from app.repository.trace_repository import TraceRepository
from app.controller.api_controller import ApiController
from app.service.analysis_service import AnalysisService
from app.service.detection_service import DetectionService
from app.service.edge_service import EdgeService
from app.service.parser.impl.alibaba_parser import AlibabaParser

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description="Microservice Bottleneck Detector — Backend")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--db", type=str, default="sqlite:///bottleneck.db")
    args = parser.parse_args()

    _, Session = init_db(args.db)
    project_repo = ProjectRepository(Session)

    alibaba_parser    = AlibabaParser()
    trace_repository  = TraceRepository(alibaba_parser)
    edge_service      = EdgeService(trace_repository)
    analysis_service  = AnalysisService(edge_service)
    detection_service = DetectionService(analysis_service)

    app = Flask(__name__, template_folder="resources/templates")
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    ApiController(
        app=app,
        edge_service=edge_service,
        analysis_service=analysis_service,
        detection_service=detection_service,
        project_repository=project_repo,
    )

    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
