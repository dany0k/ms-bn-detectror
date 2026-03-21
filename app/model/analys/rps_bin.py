from dataclasses import dataclass


@dataclass
class RpsBin:
    rps_center: float
    p50_ms: float
    p75_ms: float
    p95_ms: float
    count: int
    is_reliable: bool
