"""
Чтение логов из CSV файлов.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from domain.models import LogEntry
from .base import BaseLogReader


logger = logging.getLogger(__name__)


class CsvLogReader(BaseLogReader):
    """
    Читает логи из CSV файла.
    
    Ожидаемый формат:
    traceId,spanId,parentSpanId,timestamp,srcService,srcRoute,dstService,dstRoute,latency_ms,latency,rps
    """
    
    # Индексы колонок
    COL_TRACE_ID = 0
    COL_SPAN_ID = 1
    COL_PARENT_SPAN_ID = 2
    COL_TIMESTAMP = 3
    COL_SRC_SERVICE = 4
    COL_SRC_ROUTE = 5
    COL_DST_SERVICE = 6
    COL_DST_ROUTE = 7
    COL_LATENCY_MS = 8
    COL_LATENCY = 9
    COL_RPS = 10
    
    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        self._file = None
        self._reader = None
        self._errors_count = 0
        self._max_errors = 100
    
    def read(self) -> Iterator[LogEntry]:
        """
        Читает CSV и возвращает LogEntry для каждой строки.
        
        Пропускает заголовок и невалидные строки.
        """
        logger.info(f"Opening log file: {self.file_path}")
        
        with open(self.file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            for line_num, row in enumerate(reader, start=1):
                # Пропускаем заголовок
                if line_num == 1 and row and row[0] == 'traceId':
                    continue
                
                entry = self._parse_row(row, line_num)
                if entry is not None:
                    yield entry
        
        if self._errors_count > 0:
            logger.warning(f"Total parse errors: {self._errors_count}")
    
    def _parse_row(self, row: list[str], line_num: int) -> Optional[LogEntry]:
        """
        Парсит строку CSV в LogEntry.
        
        Returns:
            LogEntry или None при ошибке парсинга
        """
        try:
            if len(row) < 11:
                raise ValueError(f"Expected 11 columns, got {len(row)}")
            
            timestamp = datetime.fromisoformat(row[self.COL_TIMESTAMP])
            
            return LogEntry(
                trace_id=row[self.COL_TRACE_ID],
                span_id=row[self.COL_SPAN_ID],
                parent_span_id=row[self.COL_PARENT_SPAN_ID],
                timestamp=timestamp,
                src_service=row[self.COL_SRC_SERVICE],
                src_route=row[self.COL_SRC_ROUTE],
                dst_service=row[self.COL_DST_SERVICE],
                dst_route=row[self.COL_DST_ROUTE],
                latency_ms=float(row[self.COL_LATENCY_MS]),
                latency=float(row[self.COL_LATENCY]),
                rps=float(row[self.COL_RPS]),
            )
        
        except Exception as e:
            self._errors_count += 1
            if self._errors_count <= self._max_errors:
                logger.debug(f"Parse error at line {line_num}: {e}")
            return None
    
    def close(self) -> None:
        """Закрывает файл если открыт"""
        if self._file is not None:
            self._file.close()
            self._file = None
