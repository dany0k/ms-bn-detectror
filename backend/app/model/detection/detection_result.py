from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectionResult:
    edge_name:    str
    is_bottleneck: bool
    severity:     str # 'ok' | 'warning' | 'critical'
    message:      str
    onset_rps:    Optional[float] # RPS при котором начался bottleneck
    p95_growth:   float # рост P95 от первого бина к последнему