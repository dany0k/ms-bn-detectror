"""
Визуализация анализа второй производной.

Показывает:
- Scatter plot данных
- Аппроксимацию полиномом 2-й степени
- Значение второй производной
- Определение bottleneck
"""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = 'DejaVu Sans'

from .base import BasePlotter


class DerivativePlotter(BasePlotter):
    """
    Визуализация анализа второй производной.
    
    Для каждого ребра строит график:
    - Точки (RPS, Задержка)
    - Аппроксимирующий полином L(rps) = a*rps^2 + b*rps + c
    - Аннотации с d^2L/dRPS^2 и R^2
    """
    
    SUBDIR = "derivative_analysis"
    
    def __init__(self, *args, second_derivative_threshold: float = 0.01, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = second_derivative_threshold
    
    def draw(self) -> List[Path]:
        """Рисует графики анализа производных для всех рёбер"""
        saved = []
        
        for (src, dst), edge in self.graph.iter_edges():
            if self._should_skip_edge(edge, min_samples=20):
                continue
            
            path = self._draw_edge(src, dst, edge)
            if path:
                saved.append(path)
        
        return saved
    
    def _draw_edge(self, src: str, dst: str, edge) -> Optional[Path]:
        """Рисует анализ для одного ребра"""
        rps = np.array(edge.get_rps_values())
        latency = np.array(edge.get_latency_values())
        
        if np.std(rps) < 1e-6:
            return None
        
        # Аппроксимация полиномом 2-й степени
        try:
            coeffs = np.polyfit(rps, latency, 2)
            a, b, c = coeffs
        except Exception:
            return None
        
        second_derivative = 2 * a
        
        # R^2
        predicted = np.polyval(coeffs, rps)
        ss_res = np.sum((latency - predicted) ** 2)
        ss_tot = np.sum((latency - np.mean(latency)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Определяем bottleneck
        is_bottleneck = second_derivative > self.threshold
        
        # Создаём фигуру
        fig, ax = plt.subplots(figsize=(11, 7))
        
        # Scatter plot
        color = 'crimson' if is_bottleneck else 'steelblue'
        ax.scatter(rps, latency, alpha=0.4, s=20, color=color, label='Данные')
        
        # Аппроксимирующая кривая
        rps_smooth = np.linspace(rps.min(), rps.max(), 200)
        latency_fit = np.polyval(coeffs, rps_smooth)
        ax.plot(rps_smooth, latency_fit, 'k-', linewidth=2.5, label='Аппроксимация')
        
        # Если есть bottleneck - показываем зону
        if is_bottleneck and a > 0:
            # Точка перегиба (минимум параболы)
            vertex_rps = -b / (2 * a)
            if rps.min() < vertex_rps < rps.max():
                ax.axvline(x=vertex_rps, color='orange', linestyle='--', 
                          linewidth=2, label=f'Точка перегиба (RPS={vertex_rps:.0f})')
        
        # Аннотации
        formula = f'L(rps) = {a:.4f}*rps^2 + {b:.2f}*rps + {c:.1f}'
        
        textstr = '\n'.join([
            f'Вторая производная: d^2L/dRPS^2 = {second_derivative:.4f}',
            f'Коэффициент детерминации: R^2 = {r_squared:.3f}',
            f'',
            f'Формула: {formula}',
            f'',
            f'Bottleneck: {"ДА" if is_bottleneck else "НЕТ"}',
        ])
        
        # Бокс с текстом
        box_color = '#ffcccc' if is_bottleneck else '#ccffcc'
        props = dict(boxstyle='round,pad=0.5', facecolor=box_color, alpha=0.9)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace', bbox=props)
        
        # Заголовок с индикатором
        status = "BOTTLENECK ОБНАРУЖЕН" if is_bottleneck else "Норма"
        status_color = 'red' if is_bottleneck else 'green'
        ax.set_title(f'Анализ второй производной: {src} -> {dst}\nСтатус: {status}', 
                    fontsize=12, color='black')
        
        ax.set_xlabel("RPS (запросов/сек)", fontsize=11)
        ax.set_ylabel("Задержка (мс)", fontsize=11)
        ax.legend(loc='lower right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Сохраняем
        path = self._make_filename(src, dst)
        return self._save_figure(fig, path, dpi=150)
