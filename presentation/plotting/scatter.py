"""
Scatter plot: Задержка vs RPS.

Показывает зависимость задержки от RPS для каждого ребра.
"""

from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = 'DejaVu Sans'

from .base import BasePlotter


class ScatterPlotter(BasePlotter):
    """
    Scatter plot: точки (RPS, Задержка) для каждого ребра.
    
    Позволяет визуально оценить корреляцию между нагрузкой и задержкой.
    """
    
    SUBDIR = "scatter"
    
    def draw(self) -> List[Path]:
        """Рисует scatter plots для всех рёбер"""
        saved = []
        
        for (src, dst), edge in self.graph.iter_edges():
            if self._should_skip_edge(edge):
                continue
            
            path = self._draw_edge(src, dst, edge)
            if path:
                saved.append(path)
        
        return saved
    
    def _draw_edge(self, src: str, dst: str, edge) -> Path:
        """Рисует scatter plot для одного ребра"""
        # Извлекаем данные
        rps = np.array(edge.get_rps_values())
        latency = np.array(edge.get_latency_values())
        
        # Создаём фигуру
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.scatter(
            rps, latency,
            s=self.settings.plotting.scatter_size,
            alpha=self.settings.plotting.scatter_alpha,
            c='steelblue',
            edgecolors='none',
        )
        
        ax.set_xlabel("RPS (запросов/сек)", fontsize=11)
        ax.set_ylabel("Задержка (мс)", fontsize=11)
        ax.set_title(f"Зависимость задержки от RPS\n{src} -> {dst}", fontsize=12)
        ax.grid(True, alpha=self.settings.plotting.grid_alpha)
        
        # Добавляем линию тренда если есть вариация
        if len(set(rps)) > 1:
            z = np.polyfit(rps, latency, 1)
            p = np.poly1d(z)
            x_line = np.linspace(rps.min(), rps.max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2,
                   label=f"Тренд: {z[0]:.2f}x + {z[1]:.1f}")
            ax.legend(loc='upper left')
        
        # Сохраняем
        path = self._make_filename(src, dst)
        return self._save_figure(fig, path)
