"""
Базовый класс для визуализаторов.

Содержит общую логику работы с файлами и matplotlib.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import logging

import matplotlib.pyplot as plt

from domain import ServiceGraph
from config import Settings, get_settings


logger = logging.getLogger(__name__)


class BasePlotter(ABC):
    """
    Абстрактный базовый класс для визуализаторов.
    
    Предоставляет:
    - Управление директориями вывода
    - Именование файлов
    - Сохранение фигур
    """
    
    # Переопределите в подклассах
    SUBDIR: str = "plots"
    
    def __init__(
        self,
        graph: ServiceGraph,
        output_dir: Optional[Path] = None,
        settings: Optional[Settings] = None,
    ):
        self.graph = graph
        self.settings = settings or get_settings()
        
        base_dir = output_dir or self.settings.output_dir
        self.output_dir = base_dir / self.SUBDIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _make_filename(
        self,
        src: str,
        dst: str,
        suffix: str = "",
        ext: str = "png"
    ) -> Path:
        """
        Создаёт имя файла для графика.
        
        Args:
            src: Исходный узел
            dst: Целевой узел
            suffix: Дополнительный суффикс
            ext: Расширение файла
            
        Returns:
            Полный путь к файлу
        """
        # Заменяем / на _ для валидного имени файла
        name = f"{src}__{dst}".replace("/", "_")
        if suffix:
            name = f"{name}_{suffix}"
        return self.output_dir / f"{name}.{ext}"
    
    def _save_figure(
        self,
        fig: plt.Figure,
        path: Path,
        dpi: Optional[int] = None
    ) -> Path:
        """
        Сохраняет фигуру matplotlib.
        
        Args:
            fig: Фигура для сохранения
            path: Путь к файлу
            dpi: DPI (по умолчанию из настроек)
            
        Returns:
            Путь к сохранённому файлу
        """
        dpi = dpi or self.settings.plotting.figure_dpi
        
        fig.tight_layout()
        fig.savefig(path, dpi=dpi)
        plt.close(fig)
        
        logger.debug(f"Saved plot: {path}")
        return path
    
    @abstractmethod
    def draw(self) -> List[Path]:
        """
        Рисует графики.
        
        Returns:
            Список путей к сохранённым файлам
        """
        pass
    
    def _should_skip_edge(self, edge, min_samples: int = 10) -> bool:
        """Проверяет, нужно ли пропустить ребро"""
        return edge.count < min_samples
