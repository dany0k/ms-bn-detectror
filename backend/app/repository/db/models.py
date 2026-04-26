from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, default="")
    format = Column(String(64), default="alibaba")
    created_at = Column(DateTime, default=datetime.utcnow)

    log_files = relationship("LogFile", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "format": self.format,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "snapshots_count": len(self.snapshots),
        }


class LogFile(Base):
    __tablename__ = "log_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    path = Column(String(1024), nullable=False)
    loaded_at = Column(DateTime, default=datetime.utcnow)
    records_count = Column(Integer, default=0)

    project = relationship("Project", back_populates="log_files")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "path": self.path,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "records_count": self.records_count,
        }


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    edge_count = Column(Integer, default=0)
    bottleneck_count = Column(Integer, default=0)

    project = relationship("Project", back_populates="snapshots")
    edge_results = relationship("EdgeResult", back_populates="snapshot", cascade="all, delete-orphan")
    edge_analyses = relationship("EdgeAnalysis", back_populates="snapshot", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "edge_count": self.edge_count,
            "bottleneck_count": self.bottleneck_count,
        }


class EdgeResult(Base):
    __tablename__ = "edge_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    source = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    rpc_type = Column(String(64), nullable=False)
    records_amount = Column(Integer, default=0)
    severity = Column(String(32), default="ok")
    p95_growth = Column(Float, default=0.0)
    is_bottleneck = Column(Boolean, default=False)
    bin_count = Column(Integer, default=0)
    onset_rps = Column(Float, nullable=True)

    snapshot = relationship("Snapshot", back_populates="edge_results")

    @property
    def edge_name(self) -> str:
        return f"{self.source} \u2192 {self.destination}/{self.rpc_type}"

    def to_dict(self) -> dict:
        return {
            "name": self.edge_name,
            "source": self.source,
            "destination": self.destination,
            "rpc_type": self.rpc_type,
            "records_amount": self.records_amount,
            "severity": self.severity,
            "p95_growth": self.p95_growth,
            "is_bottleneck": self.is_bottleneck,
            "bin_count": self.bin_count,
            "onset_rps": self.onset_rps,
        }


class EdgeAnalysis(Base):
    """
    Full analysis result persisted to DB so we never need to re-parse logs.
    rps_bins and per_second are stored as JSON text.
    raw_timestamps / raw_latencies are stored as compact JSON arrays.
    """
    __tablename__ = "edge_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    edge_name = Column(String(512), nullable=False, index=True)

    # Global stats
    global_min_ms = Column(Float, default=0.0)
    global_max_ms = Column(Float, default=0.0)
    global_p50_ms = Column(Float, default=0.0)
    global_p75_ms = Column(Float, default=0.0)
    global_p95_ms = Column(Float, default=0.0)
    total_records = Column(Integer, default=0)

    # Heavy data as JSON
    rps_bins_json = Column(Text, default="[]")
    per_second_json = Column(Text, default="[]")
    raw_timestamps_json = Column(Text, default="[]")
    raw_latencies_json = Column(Text, default="[]")

    snapshot = relationship("Snapshot", back_populates="edge_analyses")

    def to_dict(self) -> dict:
        return {
            "edge_name": self.edge_name,
            "global_min_ms": self.global_min_ms,
            "global_max_ms": self.global_max_ms,
            "global_p50_ms": self.global_p50_ms,
            "global_p75_ms": self.global_p75_ms,
            "global_p95_ms": self.global_p95_ms,
            "total_records": self.total_records,
            "rps_bins": json.loads(self.rps_bins_json or "[]"),
            "per_second": json.loads(self.per_second_json or "[]"),
            "raw_timestamps": json.loads(self.raw_timestamps_json or "[]"),
            "raw_latencies": json.loads(self.raw_latencies_json or "[]"),
        }


def init_db(db_url: str = "sqlite:///bottleneck.db"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    return engine, Session
