from __future__ import annotations

import logging

from app.controller.context import ControllerContext
from flask import Flask, jsonify, Response, request

logger = logging.getLogger(__name__)


class ProjectController:
    """CRUD endpoints for /api/projects."""

    def __init__(self, app: Flask, ctx: ControllerContext) -> None:
        self._ctx = ctx
        app.add_url_rule('/api/projects',
                         view_func=self.list_projects, methods=['GET'])
        app.add_url_rule('/api/projects',
                         view_func=self.create_project, methods=['POST'])
        app.add_url_rule('/api/projects/<int:project_id>',
                         view_func=self.get_project, methods=['GET'])
        app.add_url_rule('/api/projects/<int:project_id>',
                         view_func=self.delete_project, methods=['DELETE'])

    def list_projects(self) -> Response:
        return jsonify(self._ctx.project_repo.get_all_projects())

    def create_project(self) -> Response:
        body = request.get_json(silent=True) or {}
        name = body.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Field "name" is required'}), 400
        try:
            project = self._ctx.project_repo.create_project(
                name=name,
                description=body.get('description', ''),
                fmt=body.get('format', 'alibaba'),
            )
            return jsonify(project), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 409

    def get_project(self, project_id: int) -> Response:
        project = self._ctx.project_repo.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify(project)

    def delete_project(self, project_id: int) -> Response:
        if not self._ctx.project_repo.delete_project(project_id):
            return jsonify({'error': 'Project not found'}), 404
        return jsonify({'deleted': project_id})
