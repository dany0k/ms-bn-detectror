from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List

from app.model.edge.call_record import CallRecord
from app.service.parser.base_parser import BaseParser
from app.service.parser.impl.alibaba_parser import AlibabaParser

logger: logging.Logger = logging.getLogger(__name__)


def _parse_file_worker(file_path_str: str) -> List[CallRecord]:
    parser = AlibabaParser()
    return parser.parse(Path(file_path_str))


class TraceRepository:

    def __init__(self, parser: BaseParser) -> None:
        self._parser: BaseParser = parser

    def load_file(self, file_path: Path) -> List[CallRecord]:
        file_extension: str = file_path.suffix.lstrip('.')

        if not self._parser.check_format(file_extension):
            logger.warning(f"Unsupported file format: {file_path.name}")
            return []

        logger.info(f"Loading file: {file_path.name}")
        records: List[CallRecord] = self._parser.parse(file_path)
        logger.info(f"Loaded {len(records)} records from {file_path.name}")

        return records

    def load_directory(self, directory_path: Path) -> List[CallRecord]:
        if not directory_path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")

        supported_files: List[Path] = sorted([
            f for f in directory_path.iterdir()
            if f.is_file() and self._parser.check_format(f.suffix.lstrip('.'))
        ])

        if not supported_files:
            logger.warning(f"No supported files found in: {directory_path}")
            return []

        logger.info(f"Parsing {len(supported_files)} files in parallel...")

        all_records: List[CallRecord] = []
        n_workers: int = min(len(supported_files), 8)

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {
                executor.submit(_parse_file_worker, str(f)): f
                for f in supported_files
            }
            for future in as_completed(futures):
                file_path: Path = futures[future]
                try:
                    records: List[CallRecord] = future.result()
                    all_records.extend(records)
                    logger.info(f"  {file_path.name}: {len(records)} records")
                except Exception as e:
                    logger.error(f"  {file_path.name}: failed — {e}")

        logger.info(f"Total: {len(all_records)} records from {directory_path}")
        return all_records