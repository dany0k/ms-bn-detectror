from __future__ import annotations

import logging

from app.controller.context import ControllerContext
from flask import Flask, jsonify, Response, request

logger = logging.getLogger(__name__)


class EdgeController:
    def __init__(self, app: Flask, ctx: ControllerContext) -> None:
        self._ctx = ctx
        app.add_url_rule('/api/projects/<int:project_id>/edges',
                         view_func=self.project_edges, methods=['GET'])
        app.add_url_rule('/api/projects/<int:project_id>/analyse/<path:edge_name>',
                         view_func=self.project_analyse_edge, methods=['GET'])

    def project_edges(self, project_id: int) -> Response:
        if not self._ctx.project_repo.get_project(project_id):
            return jsonify({'error': 'Project not found'}), 404

        snapshot = self._ctx.project_repo.get_latest_snapshot(project_id)
        if not snapshot:
            return jsonify({'error': 'No data loaded yet.'}), 400

        result = self._ctx.project_repo.get_edge_results(
            snapshot_id=snapshot['id'],
            severity=request.args.get('severity'),
            rpc_type=request.args.get('rpc_type'),
            service=request.args.get('service'),
            min_p95_growth=request.args.get('min_p95_growth', type=float),
            sort_by=request.args.get('sort_by', 'p95_growth'),
            page=max(1, request.args.get('page', 1, type=int)),
            page_size=min(200, max(1, request.args.get('page_size', 50, type=int))),
        )
        result['snapshot_id'] = snapshot['id']
        result['snapshot_at'] = snapshot.get('created_at')
        return jsonify(result)

    def project_analyse_edge(self, project_id: int, edge_name: str) -> Response:
        snapshot = self._ctx.project_repo.get_latest_snapshot(project_id)
        if not snapshot:
            return jsonify({'error': 'No data loaded for this project.'}), 400

        analysis = self._ctx.project_repo.get_edge_analysis(snapshot['id'], edge_name)
        if analysis is None:
            return jsonify({'error': f'Analysis not found for edge: {edge_name}'}), 404

        return jsonify(analysis)
