from __future__ import annotations

import argparse
import logging
from flask import Flask

from app.repository.trace_repository import TraceRepository
from app.controller.api_controller import ApiController
from app.service.analysis_service import AnalysisService
from app.service.detection_service import DetectionService
from app.service.edge_service import EdgeService
from app.service.parser.impl.alibaba_parser import AlibabaParser

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description='Microservice Bottleneck Detector')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()

    alibaba_parser    = AlibabaParser()
    trace_repository  = TraceRepository(alibaba_parser)
    edge_service      = EdgeService(trace_repository)
    analysis_service  = AnalysisService(edge_service)
    detection_service = DetectionService(analysis_service)

    app = Flask(__name__, template_folder='resources/templates')

    ApiController(
        app=app,
        edge_service=edge_service,
        analysis_service=analysis_service,
        detection_service=detection_service,
    )

    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == '__main__':
    main()