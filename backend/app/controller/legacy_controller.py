from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from app.controller.context import ControllerContext
from flask import Flask, jsonify, Response, request, render_template

logger = logging.getLogger(__name__)


class LegacyController:
    """Backward-compatible endpoints: /api/load, /api/edges, /api/detect, /api/analyse."""

    def __init__(self, app: Flask, ctx: ControllerContext) -> None:
        self._ctx = ctx
        app.add_url_rule('/', view_func=self.index, methods=['GET'])
        app.add_url_rule('/api/status', view_func=self.get_status, methods=['GET'])
        app.add_url_rule('/api/load', view_func=self.load, methods=['POST'])
        app.add_url_rule('/api/edges', view_func=self.get_edges, methods=['GET'])
        app.add_url_rule('/api/detect', view_func=self.get_detection, methods=['GET'])
        app.add_url_rule('/api/analyse/<path:edge_name>',
                         view_func=self.get_analysis_for_edge, methods=['GET'])

    def index(self) -> Response:
        return render_template('index.html')

    def get_status(self) -> Response:
        return jsonify({
            'loaded': len(self._ctx.cached_edges) > 0,
            'edges': len(self._ctx.cached_edges),
            'bottlenecks': sum(1 for d in self._ctx.cached_detection.values() if d.is_bottleneck),
        })

    def load(self) -> Response:
        body = request.get_json(silent=True) or {}
        path_str = body.get('path', '').strip()
        if not path_str:
            return jsonify({'error': 'Field "path" is required'}), 400
        data_path = Path(path_str)
        if not data_path.exists():
            return jsonify({'error': f'Path not found: {path_str}'}), 404

        edges = (
            self._ctx.edge_service.get_edges_from_dir(data_path)
            if data_path.is_dir()
            else self._ctx.edge_service.get_edges_from_file(data_path)
        )
        self._ctx.cached_edges = edges
        self._ctx.cached_detection = {}
        self._ctx.cached_analysis = {}
        return jsonify({'edges': len(edges), 'note': 'detection is lazy'})

    def get_edges(self) -> Response:
        if not self._ctx.cached_edges:
            return jsonify({'error': 'Данные не загружены'}), 400
        if not self._ctx.cached_detection:
            for edge in self._ctx.cached_edges:
                analysis = self._ctx.analysis_service.analyse_edge(edge)
                detection = self._ctx.detection_service.detect(analysis)
                self._ctx.cached_analysis[edge.display_name] = analysis
                self._ctx.cached_detection[edge.display_name] = detection

        result = []
        for edge in self._ctx.cached_edges:
            det = self._ctx.cached_detection.get(edge.display_name)
            ana = self._ctx.cached_analysis.get(edge.display_name)
            result.append({
                'name': edge.display_name,
                'source': edge.source,
                'destination': edge.destination,
                'rpc_type': edge.rpc_type,
                'records_amount': edge.records_amount,
                'severity': det.severity if det else 'ok',
                'p95_growth': det.p95_growth if det else 0.0,
                'bin_count': len(ana.rps_bins) if ana else 0,
                'is_bottleneck': det.is_bottleneck if det else False,
            })
        return jsonify(result)

    def get_detection(self) -> Response:
        if not self._ctx.cached_detection:
            return jsonify({'error': 'Данные не загружены'}), 400
        return jsonify([asdict(d) for d in self._ctx.cached_detection.values()])

    def get_analysis_for_edge(self, edge_name: str) -> Response:
        if not self._ctx.cached_edges:
            return jsonify({'error': 'Данные не загружены'}), 400
        if edge_name in self._ctx.cached_analysis:
            return jsonify(asdict(self._ctx.cached_analysis[edge_name]))
        edge = next((e for e in self._ctx.cached_edges if e.display_name == edge_name), None)
        if edge is None:
            return jsonify({'error': f'Edge not found: {edge_name}'}), 404
        analysis = self._ctx.analysis_service.analyse_edge(edge)
        self._ctx.cached_analysis[edge_name] = analysis
        return jsonify(asdict(analysis))
