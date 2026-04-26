from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List

from app.controller.context import ControllerContext
from app.model.edge.edge import Edge
from flask import Flask, jsonify, Response, request

logger = logging.getLogger(__name__)


class LoadController:
    def __init__(self, app: Flask, ctx: ControllerContext) -> None:
        self._ctx = ctx
        app.add_url_rule('/api/projects/<int:project_id>/load',
                         view_func=self.project_load, methods=['POST'])
        app.add_url_rule('/api/browse',
                         view_func=self.browse_folder, methods=['GET'])

    def browse_folder(self) -> Response:
        if sys.platform != 'win32':
            return jsonify({'error': 'Folder picker is only supported on Windows'}), 400
        ps_script = (
            'Add-Type -AssemblyName System.Windows.Forms;'
            '$d = New-Object System.Windows.Forms.FolderBrowserDialog;'
            '$d.Description = "Выберите папку с логами";'
            '$d.ShowNewFolderButton = $false;'
            'if ($d.ShowDialog() -eq "OK") { Write-Output $d.SelectedPath }'
        )
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=60,
            )
            selected = result.stdout.strip()
            if not selected:
                return jsonify({'cancelled': True})
            return jsonify({'path': selected, 'cancelled': False})
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Dialog timed out'}), 408
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def project_load(self, project_id: int) -> Response:
        if not self._ctx.project_repo.get_project(project_id):
            return jsonify({'error': 'Project not found'}), 404

        body = request.get_json(silent=True) or {}
        path_str = body.get('path', '').strip()
        if not path_str:
            return jsonify({'error': 'Field "path" is required'}), 400

        data_path = Path(path_str)
        if not data_path.exists():
            return jsonify({'error': f'Path not found: {path_str}'}), 404

        logger.info(f'[Project {project_id}] Loading: {data_path}')

        edges: List[Edge] = (
            self._ctx.edge_service.get_edges_from_dir(data_path)
            if data_path.is_dir()
            else self._ctx.edge_service.get_edges_from_file(data_path)
        )

        edge_results = []
        analyses_to_save = []

        for edge in edges:
            analysis = self._ctx.analysis_service.analyse_edge(edge)
            detection = self._ctx.detection_service.detect(analysis)

            edge_results.append({
                'source': edge.source,
                'destination': edge.destination,
                'rpc_type': edge.rpc_type,
                'records_amount': edge.records_amount,
                'severity': detection.severity,
                'p95_growth': detection.p95_growth,
                'is_bottleneck': detection.is_bottleneck,
                'bin_count': len(analysis.rps_bins),
                'onset_rps': detection.onset_rps,
            })

            a = asdict(analysis)
            # Trim raw data to keep DB size reasonable (max 2000 points)
            a['raw_timestamps'] = a['raw_timestamps'][:2000]
            a['raw_latencies'] = a['raw_latencies'][:2000]
            analyses_to_save.append(a)

        total_records = sum(e['records_amount'] for e in edge_results)
        self._ctx.project_repo.add_log_file(project_id, path_str, total_records)
        snapshot = self._ctx.project_repo.save_snapshot(project_id, edge_results)

        # Persist full analysis results so future requests read from DB
        self._ctx.project_repo.save_edge_analyses(snapshot['id'], analyses_to_save)

        logger.info(f'[Project {project_id}] Snapshot {snapshot["id"]} saved: {len(edges)} edges')
        return jsonify({
            'snapshot_id': snapshot['id'],
            'edges': len(edges),
            'bottlenecks': snapshot['bottleneck_count'],
        })
