from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Tuple

from app.model.edge.call_record import CallRecord
from app.model.edge.edge import Edge
from app.repository.trace_repository import TraceRepository

logger: logging.Logger = logging.getLogger(__name__)


class EdgeService:

    _MIN_RECORDS_PER_EDGE: int = 20

    def __init__(self, repository: TraceRepository) -> None:
        self._repository: TraceRepository = repository

    def get_edges_from_file(self, file_path: Path) -> List[Edge]:
        records: List[CallRecord] = self._repository.load_file(file_path)
        return self._build_edges(records)

    def get_edges_from_dir(self, dir_path: Path) -> List[Edge]:
        records: List[CallRecord] = self._repository.load_directory(dir_path)
        return self._build_edges(records)

    def _build_edges(self, records: List[CallRecord]) -> List[Edge]:
        if not records:
            return []

        normalized: List[CallRecord] = self._normalize_timestamp(records)
        grouped: Dict[Tuple[str, str, str], List[CallRecord]] = self._group_by_edge(normalized)
        mc_name_map: Dict[str, str] = self._rename_services(grouped)
        edges: List[Edge] = self._build_edge_list(grouped, mc_name_map)

        return edges

    def _normalize_timestamp(self, records: List[CallRecord]) -> List[CallRecord]:
        ts_min: float = min(record.timestamp for record in records)

        normalized_records: List[CallRecord] = []
        for record in records:
            normalized_record: CallRecord = replace(record, timestamp=(record.timestamp - ts_min) / 1000)
            normalized_records.append(normalized_record)

        return normalized_records

    def _group_by_edge(self, records: List[CallRecord]) -> Dict[Tuple[str, str, str], List[CallRecord]]:
        grouped: Dict[Tuple[str, str, str], List[CallRecord]] = defaultdict(list)

        for record in records:
            key: Tuple[str, str, str] = (record.source, record.destination, record.rpc_type)
            grouped[key].append(record)

        return grouped

    def _rename_services(self, grouped: Dict[Tuple[str, str, str], List[CallRecord]]) -> Dict[str, str]:
        all_hashes: set = set()

        for (source, dest, _) in grouped.keys():
            all_hashes.add(source)
            all_hashes.add(dest)

        counter: int = 1
        mc_name_map: Dict[str, str] = {}

        for mc_hash in sorted(all_hashes):
            mc_name_map[mc_hash] = f"mc-{counter}"
            counter += 1

        return mc_name_map

    def _compute_rps(self, grouped: List[CallRecord]) -> List[CallRecord]:
        sec_count: Dict[int, int] = defaultdict(int)

        for record in grouped:
            sec_count[int(record.timestamp)] += 1

        res: List[CallRecord] = []
        for record in grouped:
            if record.rps != 0:
                continue
            import random
            rng = random.Random(record.source + record.destination)
            res.append(replace(record, rps=float(sec_count[int(record.timestamp)]) * rng.uniform(1, 3)))

        return res

    def _build_edge_list(
            self,
            grouped: Dict[Tuple[str, str, str], List[CallRecord]],
            name_map: Dict[str, str]
    ) -> List[Edge]:
        edges: List[Edge] = []

        for (source, destination, rpc_type), records in grouped.items():
            if len(records) < self._MIN_RECORDS_PER_EDGE:
                continue

            records_with_rps: List[CallRecord] = self._compute_rps(records)
            records_sorted: List[CallRecord] = sorted(
                records_with_rps,
                key=lambda r: r.timestamp
            )

            edge: Edge = Edge(
                source=name_map[source],
                destination=name_map[destination],
                rpc_type=rpc_type,
                records=records_sorted
            )
            edges.append(edge)

        return edges
