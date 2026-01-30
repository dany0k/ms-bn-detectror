"""
Централизованная конфигурация приложения.

Поддерживает загрузку из переменных окружения с префиксом BN_
Например: BN_LOG_FILE, BN_OUTPUT_DIR, BN_SLOPE_CRITICAL
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class DetectionSettings:
    """Настройки детекции bottleneck"""
    min_samples: int = 10
    stability_window: int = 3
    rps_min: float = 5.0
    slope_critical: float = 2.0
    latency_warn: float = 150.0
    latency_critical: float = 250.0


@dataclass
class PlottingSettings:
    """Настройки визуализации"""
    figure_dpi: int = 150
    bin_size: int = 5
    scatter_alpha: float = 0.5
    scatter_size: int = 14
    line_width: float = 2.0
    grid_alpha: float = 0.3


@dataclass
class Settings:
    """Главный класс конфигурации"""
    
    # Пути
    log_file: Path = field(default_factory=lambda: Path("resources/generated_logs.csv"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    
    # Режим работы
    mode: str = "offline"  # "offline" | "online"
    stream_interval: float = 0.1
    
    # Лимиты данных
    max_samples_per_edge: int = 1000
    max_latencies_per_node: int = 200
    
    # Вложенные настройки
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    plotting: PlottingSettings = field(default_factory=PlottingSettings)
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Создаёт Settings из переменных окружения"""
        settings = cls()
        
        # Основные пути
        if log_file := os.getenv('BN_LOG_FILE'):
            settings.log_file = Path(log_file)
        if output_dir := os.getenv('BN_OUTPUT_DIR'):
            settings.output_dir = Path(output_dir)
        
        # Режим
        if mode := os.getenv('BN_MODE'):
            settings.mode = mode
        
        # Detection settings
        if val := os.getenv('BN_MIN_SAMPLES'):
            settings.detection.min_samples = int(val)
        if val := os.getenv('BN_SLOPE_CRITICAL'):
            settings.detection.slope_critical = float(val)
        if val := os.getenv('BN_LATENCY_WARN'):
            settings.detection.latency_warn = float(val)
        if val := os.getenv('BN_LATENCY_CRITICAL'):
            settings.detection.latency_critical = float(val)
        
        # Plotting settings
        if val := os.getenv('BN_FIGURE_DPI'):
            settings.plotting.figure_dpi = int(val)
        if val := os.getenv('BN_BIN_SIZE'):
            settings.plotting.bin_size = int(val)
        
        return settings


# Singleton для глобального доступа
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Возвращает глобальный экземпляр Settings"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def configure(settings: Settings) -> None:
    """Устанавливает глобальный экземпляр Settings"""
    global _settings
    _settings = settings
