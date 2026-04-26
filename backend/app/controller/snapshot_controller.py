from __future__ import annotations

import logging

from app.controller.context import ControllerContext
from flask import Flask, jsonify, Response

logger = logging.getLogger(__name__)


class SnapshotController:
    """GET /api/projects/<id>/snapshots — load history."""

    def __init__(self, app: Flask, ctx: ControllerContext) -> None:
        self._ctx = ctx
        app.add_url_rule('/api/projects/<int:project_id>/snapshots',
                         view_func=self.project_snapshots, methods=['GET'])

    def project_snapshots(self, project_id: int) -> Response:
        if not self._ctx.project_repo.get_project(project_id):
            return jsonify({'error': 'Project not found'}), 404
        return jsonify(self._ctx.project_repo.get_snapshots(project_id))
