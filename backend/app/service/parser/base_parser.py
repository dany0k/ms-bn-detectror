from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set

from app.model.edge.call_record import CallRecord

logger = logging.getLogger(__name__)


class BaseParser(ABC):

    def __init__(self, allowed_formats: Set[str]):
        self.allowed_formats = allowed_formats

    @abstractmethod
    def parse(self, file_path: Path) -> List[CallRecord]:
        """
        Абстрактный метод парсинга
        """


    def check_format(self, file_name: str) -> bool:
        return file_name in self.allowed_formats



