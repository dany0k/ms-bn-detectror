from dataclasses import dataclass

from app.model.edge.call_record import CallRecord


@dataclass
class Edge:
    source: str
    destination: str
    rpc_type: str
    records: list[CallRecord]

    @property
    def display_name(self) -> str:
        return f"{self.source} → {self.destination}/{self.rpc_type}"

    @property
    def records_amount(self) -> int:
        return len(self.records)