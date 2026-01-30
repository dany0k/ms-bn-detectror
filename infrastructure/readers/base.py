"""
Базовые абстракции для чтения логов.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Protocol, runtime_checkable

from domain.models import LogEntry


@runtime_checkable
class LogReader(Protocol):
    """Протокол для reader'ов логов"""
    
    def read(self) -> Iterator[LogEntry]:
        """Читает логи и возвращает итератор LogEntry"""
        ...
    
    def close(self) -> None:
        """Закрывает ресурсы"""
        ...


class BaseLogReader(ABC):
    """Абстрактный базовый класс для reader'ов"""
    
    @abstractmethod
    def read(self) -> Iterator[LogEntry]:
        """Читает логи"""
        pass
    
    def close(self) -> None:
        """Закрывает ресурсы (переопределите если нужно)"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
