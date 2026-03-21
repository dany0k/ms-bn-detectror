from dataclasses import dataclass, field
from typing import List

from app.model.analys.rps_bin import RpsBin
from app.model.analys.second_agregate import SecondAggregate


@dataclass
class AnalysisResult:
    edge_name: str
    global_min_ms: float
    global_max_ms: float
    global_p50_ms: float
    global_p75_ms: float
    global_p95_ms: float
    total_records: int
    rps_bins: List[RpsBin] = field(default_factory=list)
    per_second: List[SecondAggregate] = field(default_factory=list)
    raw_timestamps: List[float] = field(default_factory=list)
    raw_latencies: List[float] = field(default_factory=list)

