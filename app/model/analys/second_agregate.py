from dataclasses import dataclass


@dataclass
class SecondAggregate:
    timestamp: float
    p50_ms: float
    p75_ms: float
    p95_ms: float
    rps: float
    lat: float
    count: int
    is_reliable: bool