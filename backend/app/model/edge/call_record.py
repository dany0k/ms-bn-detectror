from dataclasses import dataclass


@dataclass(frozen=True)
class CallRecord:
    source: str
    destination: str
    rpc_type: str
    latency_ms: float
    timestamp: float
    rps: float = 0.0