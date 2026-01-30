"""
Time Series plot: RPS и Задержка по времени.

Показывает динамику изменения метрик во времени.
"""

from pathlib import Path
from typing import List
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['font.family'] = 'DejaVu Sans'

from .base import BasePlotter


class TimeSeriesPlotter(BasePlotter):
    """
    Time Series plot: два графика - RPS и Задержка по времени.
    
    Позволяет увидеть корреляцию между ростом нагрузки и задержкой.
    """
    
    SUBDIR = "time_series"
    
    def draw(self) -> List[Path]:
        """Рисует time series для всех рёбер"""
        saved = []
        
        for (src, dst), edge in self.graph.iter_edges():
            if self._should_skip_edge(edge, min_samples=5):
                continue
            
            path = self._draw_edge(src, dst, edge)
            if path:
                saved.append(path)
        
        return saved
    
    def _draw_edge(self, src: str, dst: str, edge) -> Path:
        """Рисует time series для одного ребра"""
        # Извлекаем данные
        timestamps = edge.get_timestamps()
        rps = edge.get_rps_values()
        latency = edge.get_latency_values()
        
        # Конвертируем timestamps в datetime
        times_dt = [datetime.fromtimestamp(t) for t in timestamps]
        
        # Создаём фигуру с двумя subplot'ами
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(12, 7),
            sharex=True
        )
        
        # RPS
        ax1.plot(
            times_dt, rps,
            color="tab:blue",
            linewidth=self.settings.plotting.line_width
        )
        ax1.set_ylabel("RPS (запросов/сек)", fontsize=11)
        ax1.set_title(f"RPS и задержка во времени\n{src} -> {dst}", fontsize=12)
        ax1.grid(True, alpha=self.settings.plotting.grid_alpha)
        ax1.fill_between(times_dt, rps, alpha=0.3)
        
        # Задержка
        ax2.plot(
            times_dt, latency,
            color="tab:red",
            linewidth=self.settings.plotting.line_width
        )
        ax2.set_ylabel("Задержка (мс)", fontsize=11)
        ax2.set_xlabel("Время", fontsize=11)
        ax2.grid(True, alpha=self.settings.plotting.grid_alpha)
        ax2.fill_between(times_dt, latency, alpha=0.3, color='tab:red')
        
        # Форматирование дат
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()
        
        plt.tight_layout()
        
        # Сохраняем
        path = self._make_filename(src, dst)
        return self._save_figure(fig, path)
