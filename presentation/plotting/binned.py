"""
Binned plot: Медианная задержка по диапазонам RPS.

Группирует данные по диапазонам RPS и показывает медианную задержку.
"""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = 'DejaVu Sans'

from .base import BasePlotter


class BinnedPlotter(BasePlotter):
    """
    Binned plot: медианная задержка для каждого диапазона RPS.
    
    Сглаживает шум и показывает тренд более наглядно.
    """
    
    SUBDIR = "binned"
    
    def __init__(self, *args, bin_size: int = 5, min_points_per_bin: int = 3, **kwargs):
        super().__init__(*args, **kwargs)
        self.bin_size = bin_size
        self.min_points_per_bin = min_points_per_bin
    
    def draw(self) -> List[Path]:
        """Рисует binned plots для всех рёбер"""
        saved = []
        
        for (src, dst), edge in self.graph.iter_edges():
            if self._should_skip_edge(edge, min_samples=20):
                continue
            
            path = self._draw_edge(src, dst, edge)
            if path:
                saved.append(path)
        
        return saved
    
    def _draw_edge(self, src: str, dst: str, edge) -> Optional[Path]:
        """Рисует binned plot для одного ребра"""
        rps = np.array(edge.get_rps_values())
        latency = np.array(edge.get_latency_values())
        
        # Создаём bins
        bins = np.arange(rps.min(), rps.max() + self.bin_size, self.bin_size)
        
        xs = []
        ys = []
        yerr = []  # Для error bars
        
        for i in range(len(bins) - 1):
            mask = (rps >= bins[i]) & (rps < bins[i + 1])
            if mask.sum() < self.min_points_per_bin:
                continue
            
            bin_latencies = latency[mask]
            xs.append((bins[i] + bins[i + 1]) / 2)
            ys.append(np.median(bin_latencies))
            yerr.append(np.std(bin_latencies))
        
        if not xs:
            return None
        
        # Создаём фигуру
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.errorbar(xs, ys, yerr=yerr, marker='o', capsize=4, capthick=1.5,
                   markersize=8, linewidth=2, color='steelblue', ecolor='gray')
        
        ax.set_xlabel("RPS (запросов/сек)", fontsize=11)
        ax.set_ylabel("Медианная задержка (мс)", fontsize=11)
        ax.set_title(f"Задержка по диапазонам RPS (шаг={self.bin_size})\n{src} -> {dst}", fontsize=12)
        ax.grid(True, alpha=self.settings.plotting.grid_alpha)
        
        # Сохраняем
        path = self._make_filename(src, dst)
        return self._save_figure(fig, path)
