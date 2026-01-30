"""
Экспорт результатов в JSON.
"""

import json
from pathlib import Path
from typing import Optional

from application.analyzer import AnalysisReport


class JsonExporter:
    """Экспортирует результаты анализа в JSON"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self, report: AnalysisReport, filename: str = "report.json") -> Path:
        """
        Экспортирует отчёт в JSON файл.
        
        Args:
            report: Результат анализа
            filename: Имя файла
            
        Returns:
            Путь к созданному файлу
        """
        data = {
            "status": report.status,
            "logs_processed": report.logs_processed,
            "graph": report.graph.export(),
            "alerts": [alert.to_dict() for alert in report.alerts],
            "plots": [str(p) for p in report.plots],
        }
        
        path = self.output_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return path
