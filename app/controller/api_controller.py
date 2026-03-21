from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Optional

from flask import Flask, jsonify, Response, request, render_template

from app.model.analys.analysis_result import AnalysisResult
from app.model.detection.detection_result import DetectionResult
from app.model.edge.edge import Edge
from app.service.analysis_service import AnalysisService
from app.service.detection_service import DetectionService
from app.service.edge_service import EdgeService

logger: logging.Logger = logging.getLogger(__name__)

"""
ApiController — HTTP-слой приложения.

Оптимизации производительности:
- POST /api/load загружает данные один раз в кеш
- GET /api/edges отдаёт из кеша мгновенно
- GET /api/analyse/<edge> считает анализ только одного ребра и кеширует
- Flask запускается с threaded=True
"""

class ApiController:

    def __init__(
        self,
        app:               Flask,
        edge_service:      EdgeService,
        analysis_service:  AnalysisService,
        detection_service: DetectionService,
    ) -> None:
        self._edge_service:      EdgeService     = edge_service
        self._analysis_service:  AnalysisService = analysis_service
        self._detection_service: DetectionService = detection_service

        self._cached_edges:     List[Edge]                 = []
        self._cached_detection: Dict[str, DetectionResult] = {}
        self._cached_analysis:  Dict[str, AnalysisResult]  = {}

        self._register_routes(app)

    def _register_routes(self, app: Flask) -> None:
        app.add_url_rule('/',            view_func=self.index,                  methods=['GET'])
        app.add_url_rule('/api/status',  view_func=self.get_status,             methods=['GET'])
        app.add_url_rule('/api/load',    view_func=self.load,                   methods=['POST'])
        app.add_url_rule('/api/edges',   view_func=self.get_edges,              methods=['GET'])
        app.add_url_rule('/api/detect',  view_func=self.get_detection,          methods=['GET'])
        app.add_url_rule('/api/analyse/<path:edge_name>',
                         view_func=self.get_analysis_for_edge, methods=['GET'])

    def index(self) -> Response:
        return render_template('index.html')

    def get_status(self) -> Response:
        """GET /api/status — текущее состояние кеша."""
        return jsonify({
            'loaded':      len(self._cached_edges) > 0,
            'edges':       len(self._cached_edges),
            'bottlenecks': sum(1 for d in self._cached_detection.values() if d.is_bottleneck),
        })

    def load(self) -> Response:
        """
        POST /api/load  { "path": "resources/alibaba/" }
        Парсит файлы, считает детекцию, кладёт в кеш.
        Анализ считается лениво — по запросу конкретного ребра.
        """
        body: dict = request.get_json(silent=True) or {}
        path_str: str = body.get('path', '').strip()

        if not path_str:
            return jsonify({'error': 'Field "path" is required'}), 400

        data_path: Path = Path(path_str)
        if not data_path.exists():
            return jsonify({'error': f'Path not found: {path_str}'}), 404

        logger.info(f"Loading: {data_path}")

        edges: List[Edge] = (
            self._edge_service.get_edges_from_dir(data_path)
            if data_path.is_dir()
            else self._edge_service.get_edges_from_file(data_path)
        )

        # Сохраняем рёбра — анализ и детекция считаются лениво при первом запросе
        self._cached_edges     = edges
        self._cached_detection = {}
        self._cached_analysis  = {}

        logger.info(f"Done: {len(edges)} edges loaded")

        return jsonify({'edges': len(edges), 'bottlenecks': 0, 'note': 'detection is lazy'})

    def get_edges(self) -> Response:
        """
        GET /api/edges — список рёбер с severity.
        При первом вызове считает детекцию для всех рёбер и кеширует.
        """
        if not self._cached_edges:
            return jsonify({'error': 'Данные не загружены'}), 400

        # Ленивая детекция: считаем только если кеш пустой
        if not self._cached_detection:
            logger.info("Computing detection for all edges...")
            for edge in self._cached_edges:
                analysis: AnalysisResult = self._analysis_service.analyse_edge(edge)
                detection: DetectionResult = self._detection_service.detect(analysis)
                self._cached_analysis[edge.display_name]  = analysis
                self._cached_detection[edge.display_name] = detection
            bottlenecks: int = sum(1 for d in self._cached_detection.values() if d.is_bottleneck)
            logger.info(f"Detection done: {bottlenecks} bottlenecks")

        result: List[dict] = []
        for edge in self._cached_edges:
            det: Optional[DetectionResult] = self._cached_detection.get(edge.display_name)
            analysis: Optional[AnalysisResult] = self._cached_analysis.get(edge.display_name)
            result.append({
                'name':           edge.display_name,
                'source':         edge.source,
                'destination':    edge.destination,
                'rpc_type':       edge.rpc_type,
                'records_amount': edge.records_amount,
                'severity':       det.severity      if det else 'ok',
                'p95_growth':     det.p95_growth    if det else 0.0,
                'bin_count': len(analysis.rps_bins) if analysis else 0,
                'is_bottleneck':  det.is_bottleneck if det else False,
            })

        return jsonify(result)

    def get_detection(self) -> Response:
        """GET /api/detect — детекция всех рёбер из кеша."""
        if not self._cached_detection:
            return jsonify({'error': 'Данные не загружены'}), 400
        return jsonify([asdict(d) for d in self._cached_detection.values()])

    def get_analysis_for_edge(self, edge_name: str) -> Response:
        """
        GET /api/analyse/<edge_name> — анализ одного ребра.
        Берёт из кеша (уже посчитан при load) или считает лениво.
        """
        if not self._cached_edges:
            return jsonify({'error': 'Данные не загружены'}), 400

        if edge_name in self._cached_analysis:
            return jsonify(asdict(self._cached_analysis[edge_name]))

        edge: Optional[Edge] = next(
            (e for e in self._cached_edges if e.display_name == edge_name), None
        )
        if edge is None:
            return jsonify({'error': f'Edge not found: {edge_name}'}), 404

        analysis: AnalysisResult = self._analysis_service.analyse_edge(edge)
        self._cached_analysis[edge_name] = analysis
        return jsonify(asdict(analysis))