"""
3D Surface plot: Задержка(Время, RPS).

Показывает поверхность задержки в зависимости от времени и RPS.
"""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from scipy import interpolate

plt.rcParams['font.family'] = 'DejaVu Sans'

from .base import BasePlotter


class SurfacePlotter(BasePlotter):
    """
    3D Surface plot:
        X - время (минуты)
        Y - RPS  
        Z - задержка (мс)
    
    Оптимизировано для детекции bottleneck:
    - Видно как задержка растёт с RPS и временем
    """
    
    SUBDIR = "surface"
    
    def __init__(self, *args, smooth: bool = True, grid_resolution: int = 50, **kwargs):
        super().__init__(*args, **kwargs)
        self.smooth = smooth
        self.grid_resolution = grid_resolution
    
    def draw(self) -> List[Path]:
        """Рисует 3D surface для всех рёбер"""
        saved = []
        
        for (src, dst), edge in self.graph.iter_edges():
            if self._should_skip_edge(edge, min_samples=20):
                continue
            
            path = self._draw_edge(src, dst, edge)
            if path:
                saved.append(path)
        
        return saved
    
    def _draw_edge(self, src: str, dst: str, edge) -> Optional[Path]:
        """Рисует 3D surface для одного ребра"""
        # Извлекаем данные
        timestamps = np.array(edge.get_timestamps(), dtype=float)
        rps = np.array(edge.get_rps_values(), dtype=float)
        latency = np.array(edge.get_latency_values(), dtype=float)
        
        if len(timestamps) < 20:
            return None
        
        # Нормализуем время в минуты от начала
        t0 = timestamps.min()
        time_minutes = (timestamps - t0) / 60.0
        
        # Добавляем небольшой шум если RPS почти константа
        if np.std(rps) < 1e-3:
            rps = rps + np.random.uniform(-0.5, 0.5, size=len(rps))
        
        # Создаём 3D фигуру
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")
        
        if self.smooth:
            # Создаём сглаженную поверхность через интерполяцию
            try:
                # Создаём регулярную сетку
                ti = np.linspace(time_minutes.min(), time_minutes.max(), self.grid_resolution)
                ri = np.linspace(rps.min(), rps.max(), self.grid_resolution)
                T, R = np.meshgrid(ti, ri)
                
                # Интерполируем данные на сетку
                points = np.column_stack((time_minutes, rps))
                Z = interpolate.griddata(points, latency, (T, R), method='cubic', fill_value=np.nan)
                
                # Заполняем NaN ближайшими значениями
                mask = np.isnan(Z)
                if mask.any():
                    Z_nearest = interpolate.griddata(points, latency, (T, R), method='nearest')
                    Z[mask] = Z_nearest[mask]
                
                # Рисуем сглаженную поверхность
                surf = ax.plot_surface(
                    T, R, Z,
                    cmap="viridis",
                    linewidth=0,
                    antialiased=True,
                    alpha=0.9,
                )
            except Exception:
                # Fallback на trisurf если интерполяция не удалась
                surf = ax.plot_trisurf(
                    time_minutes, rps, latency,
                    cmap="viridis",
                    linewidth=0.2,
                    edgecolor="gray",
                    alpha=0.9,
                    antialiased=True,
                )
        else:
            # Без сглаживания - trisurf
            surf = ax.plot_trisurf(
                time_minutes, rps, latency,
                cmap="viridis",
                linewidth=0.2,
                edgecolor="gray",
                alpha=0.9,
                antialiased=True,
            )
        
        # Настройки осей
        ax.set_xlabel("Время (мин)", fontsize=11, labelpad=10)
        ax.set_ylabel("RPS", fontsize=11, labelpad=10)
        ax.set_zlabel("Задержка (мс)", fontsize=11, labelpad=10)
        
        ax.set_title(
            f"3D поверхность задержки\n{src} -> {dst}",
            fontsize=12, pad=20
        )
        
        # Настройки камеры
        ax.view_init(elev=25, azim=-60)
        
        # Colorbar
        cbar = fig.colorbar(surf, ax=ax, pad=0.1, shrink=0.6)
        cbar.set_label("Задержка (мс)", fontsize=10)
        
        plt.tight_layout()
        
        # Сохраняем
        path = self._make_filename(src, dst)
        return self._save_figure(fig, path, dpi=150)
