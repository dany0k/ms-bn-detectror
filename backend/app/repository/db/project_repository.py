from __future__ import annotations

from typing import List, Optional

from app.repository.db.models import EdgeResult, LogFile, Project, Snapshot
from sqlalchemy import or_
from sqlalchemy.orm import scoped_session


class ProjectRepository:

    def __init__(self, Session: scoped_session) -> None:
        self._Session = Session

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def create_project(self, name: str, description: str = "", fmt: str = "alibaba") -> dict:
        session = self._Session()
        try:
            project = Project(name=name, description=description, format=fmt)
            session.add(project)
            session.commit()
            session.refresh(project)
            return self._project_to_dict(project)
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def get_project(self, project_id: int) -> Optional[dict]:
        session = self._Session()
        try:
            project = session.get(Project, project_id)
            return self._project_to_dict(project) if project else None
        finally:
            self._Session.remove()

    def get_all_projects(self) -> List[dict]:
        session = self._Session()
        try:
            projects = session.query(Project).order_by(Project.created_at.desc()).all()
            return [self._project_to_dict(p) for p in projects]
        finally:
            self._Session.remove()

    def delete_project(self, project_id: int) -> bool:
        session = self._Session()
        try:
            project = session.get(Project, project_id)
            if not project:
                return False
            session.delete(project)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    @staticmethod
    def _project_to_dict(project: Project) -> dict:
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "format": project.format,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "snapshots_count": len(project.snapshots),
        }

    # ------------------------------------------------------------------
    # Log files
    # ------------------------------------------------------------------

    def add_log_file(self, project_id: int, path: str, records_count: int) -> dict:
        session = self._Session()
        try:
            lf = LogFile(project_id=project_id, path=path, records_count=records_count)
            session.add(lf)
            session.commit()
            session.refresh(lf)
            return lf.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def get_log_files(self, project_id: int) -> List[dict]:
        session = self._Session()
        try:
            rows = (
                session.query(LogFile)
                .filter(LogFile.project_id == project_id)
                .order_by(LogFile.loaded_at.asc())
                .all()
            )
            return [r.to_dict() for r in rows]
        finally:
            self._Session.remove()

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def save_snapshot(self, project_id: int, edge_results: List[dict]) -> dict:
        session = self._Session()
        try:
            bottleneck_count = sum(1 for e in edge_results if e["is_bottleneck"])
            snapshot = Snapshot(
                project_id=project_id,
                edge_count=len(edge_results),
                bottleneck_count=bottleneck_count,
            )
            session.add(snapshot)
            session.flush()

            for e in edge_results:
                session.add(EdgeResult(
                    snapshot_id=snapshot.id,
                    source=e["source"],
                    destination=e["destination"],
                    rpc_type=e["rpc_type"],
                    records_amount=e["records_amount"],
                    severity=e["severity"],
                    p95_growth=e["p95_growth"],
                    is_bottleneck=e["is_bottleneck"],
                    bin_count=e["bin_count"],
                    onset_rps=e.get("onset_rps"),
                ))

            session.commit()
            return snapshot.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def get_snapshots(self, project_id: int) -> List[dict]:
        session = self._Session()
        try:
            rows = (
                session.query(Snapshot)
                .filter(Snapshot.project_id == project_id)
                .order_by(Snapshot.created_at.desc())
                .all()
            )
            return [s.to_dict() for s in rows]
        finally:
            self._Session.remove()

    def get_latest_snapshot(self, project_id: int) -> Optional[dict]:
        session = self._Session()
        try:
            row = (
                session.query(Snapshot)
                .filter(Snapshot.project_id == project_id)
                .order_by(Snapshot.created_at.desc())
                .first()
            )
            return row.to_dict() if row else None
        finally:
            self._Session.remove()

    # ------------------------------------------------------------------
    # Edge results  — filtering + pagination
    # ------------------------------------------------------------------

    def get_edge_results(
            self,
            snapshot_id: int,
            severity: Optional[str] = None,
            rpc_type: Optional[str] = None,
            service: Optional[str] = None,
            min_p95_growth: Optional[float] = None,
            sort_by: str = "p95_growth",
            page: int = 1,
            page_size: int = 50,
    ) -> dict:
        session = self._Session()
        try:
            q = session.query(EdgeResult).filter(EdgeResult.snapshot_id == snapshot_id)

            if severity:
                q = q.filter(EdgeResult.severity == severity)
            if rpc_type:
                q = q.filter(EdgeResult.rpc_type == rpc_type)
            if service:
                q = q.filter(or_(EdgeResult.source == service, EdgeResult.destination == service))
            if min_p95_growth is not None:
                q = q.filter(EdgeResult.p95_growth >= min_p95_growth)

            sort_col = {
                "p95_growth": EdgeResult.p95_growth,
                "records_amount": EdgeResult.records_amount,
                "severity": EdgeResult.severity,
                "source": EdgeResult.source,
            }.get(sort_by, EdgeResult.p95_growth)

            q = q.order_by(sort_col.desc())

            total = q.count()
            items = q.offset((page - 1) * page_size).limit(page_size).all()

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": max(1, (total + page_size - 1) // page_size),
                "items": [e.to_dict() for e in items],
            }
        finally:
            self._Session.remove()

    # ------------------------------------------------------------------
    # Edge analysis — persist full analysis result to DB
    # ------------------------------------------------------------------

    def save_edge_analyses(self, snapshot_id: int, analyses: list[dict]) -> None:
        """Bulk-save full analysis results for a snapshot."""
        import json
        session = self._Session()
        try:
            from app.repository.db.models import EdgeAnalysis
            for a in analyses:
                session.add(EdgeAnalysis(
                    snapshot_id=snapshot_id,
                    edge_name=a["edge_name"],
                    global_min_ms=a["global_min_ms"],
                    global_max_ms=a["global_max_ms"],
                    global_p50_ms=a["global_p50_ms"],
                    global_p75_ms=a["global_p75_ms"],
                    global_p95_ms=a["global_p95_ms"],
                    total_records=a["total_records"],
                    rps_bins_json=json.dumps(a["rps_bins"]),
                    per_second_json=json.dumps(a["per_second"]),
                    raw_timestamps_json=json.dumps(a["raw_timestamps"]),
                    raw_latencies_json=json.dumps(a["raw_latencies"]),
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def get_edge_analysis(self, snapshot_id: int, edge_name: str) -> Optional[dict]:
        """Retrieve persisted analysis for one edge. Returns None if not found."""
        from app.repository.db.models import EdgeAnalysis
        session = self._Session()
        try:
            row = (
                session.query(EdgeAnalysis)
                .filter(
                    EdgeAnalysis.snapshot_id == snapshot_id,
                    EdgeAnalysis.edge_name == edge_name,
                )
                .first()
            )
            return row.to_dict() if row else None
        finally:
            self._Session.remove()
