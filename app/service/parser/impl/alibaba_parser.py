import csv
import gzip
from pathlib import Path
from typing import List, TextIO, Optional

from app.model.edge.call_record import CallRecord
from app.service.parser.base_parser import BaseParser, logger


class AlibabaParser(BaseParser):

    _COL_TIMESTAMP: int = 1
    _COL_UM: int = 3
    _COL_RPCTYPE: int = 4
    _COL_DM: int = 5
    _COL_RT: int = 7
    _MIN_COLUMNS: int = 8

    def __init__(self):
        allowed_formats = {'csv', 'gz'}
        super().__init__(allowed_formats)

    def parse(self, file_path: Path) -> List[CallRecord]:
        records: List[CallRecord] = []
        total = 0
        skipped = 0

        with self._open(file_path) as f:
            reader = csv.reader(f)
            next(reader)

            for row in reader:
                total += 1
                record: Optional[CallRecord] = self._parse_row(row)

                if record is None:
                    skipped += 1
                    continue

                records.append(record)

            logger.info(f"{file_path.name}: total={total}, parsed={total - skipped}, skipped={skipped}")
            return records


    def _open(self, file_path: Path) -> TextIO:
        if file_path.suffix == '.gz':
            return gzip.open(file_path, 'rt', encoding='utf-8', errors='replace')

        if file_path.suffix == '.csv':
            return open(file_path, 'rt', encoding='utf-8', errors='replace')

        raise ValueError(f"Unsupported file extension: {file_path.suffix}")

    def _read_header(self, file_path: Path) -> str:
        with self._open(file_path) as f:
            return f.readline().strip().lower()

    def _parse_row(self, row) -> Optional[CallRecord]:

        if len(row) < self._MIN_COLUMNS:
            return None

        rpc_type: str = row[self._COL_RPCTYPE]
        if rpc_type not in {'http', 'rpc'}:
            return None

        um: str = row[self._COL_UM]
        dm: str = row[self._COL_DM]

        if um == '(?)' or dm == '(?)':
            return None

        if um == dm:
            return None

        rt: float = float(row[self._COL_RT])
        if rt <= 0:
            return None

        time_ms: int = int(row[self._COL_TIMESTAMP])

        return CallRecord(
            source=um.__str__(),
            destination=dm.__str__(),
            rpc_type=rpc_type,
            latency_ms=rt,
            timestamp=time_ms
        )
