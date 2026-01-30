# Bottleneck Detector v2.0

Система анализа логов микросервисов для выявления узких мест (bottlenecks).

## Особенности

- **Чистая архитектура**: разделение на domain/infrastructure/application/presentation
- **Dependency Injection**: все компоненты легко тестируются и заменяются
- **Множественные детекторы**: SlopeDetector (по наклону) и ThresholdDetector (по порогам)
- **Визуализация**: scatter, binned, time series и 3D surface графики
- **Экспорт**: JSON отчёты и консольный вывод

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### Анализ логов

```bash
# Базовый анализ
python -m bn_detector.main analyze -l logs_bn.csv

# С JSON отчётом
python -m bn_detector.main analyze -l logs_bn.csv --json

# Без графиков
python -m bn_detector.main analyze -l logs_bn.csv --no-plots

# Подробный вывод
python -m bn_detector.main analyze -l logs_bn.csv -v
```

### Генерация тестовых логов

```bash
# С настройками по умолчанию
python -m bn_detector.main generate -o test_logs.csv

# С кастомной конфигурацией
python -m bn_detector.main generate -o test_logs.csv -c config.json

# С указанием длительности
python -m bn_detector.main generate -o test_logs.csv -d 600
```

### Программное использование

```python
from bn_detector import (
    CsvLogReader,
    ServiceGraph,
    LogAnalyzer,
    SlopeDetector,
    ThresholdDetector,
    ScatterPlotter,
    ConsoleExporter,
)

# Создаём компоненты
reader = CsvLogReader("logs_bn.csv")
graph = ServiceGraph()
detectors = [SlopeDetector(), ThresholdDetector()]
plotters = [ScatterPlotter(graph)]

# Запускаем анализ
analyzer = LogAnalyzer(
    reader=reader,
    graph=graph,
    detectors=detectors,
    plotters=plotters,
)

report = analyzer.run()

# Выводим результаты
ConsoleExporter(verbose=True).export(report)
```

## Структура проекта

```
bn_detector/
├── config/              # Конфигурация
│   └── settings.py
├── domain/              # Бизнес-логика (без внешних зависимостей)
│   ├── models.py        # Sample, LogEntry, EdgeMetrics, NodeMetrics
│   ├── graph.py         # ServiceGraph
│   └── detection/       # Детекторы bottleneck
│       ├── base.py
│       ├── slope_detector.py
│       └── threshold_detector.py
├── infrastructure/      # Внешние интеграции
│   ├── readers/         # Чтение логов
│   │   └── csv_reader.py
│   └── generators/      # Генерация логов
│       └── log_generator.py
├── application/         # Use cases
│   ├── analyzer.py      # LogAnalyzer
│   └── alert_service.py
├── presentation/        # Вывод результатов
│   ├── plotting/        # Графики
│   └── exporters/       # JSON, консоль
├── tests/
└── main.py              # CLI
```

## Формат логов

CSV с колонками:
```
traceId,spanId,parentSpanId,timestamp,srcService,srcRoute,dstService,dstRoute,latency_ms,latency,rps
```

## Детекторы

### SlopeDetector
Детектирует bottleneck когда latency растёт пропорционально RPS.
Вычисляет наклон линейной регрессии `latency(rps)`.

### ThresholdDetector  
Детектирует bottleneck когда средняя latency превышает пороги.
Поддерживает статические и адаптивные пороги.

## Тестирование

```bash
pytest bn_detector/tests/ -v
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| BN_LOG_FILE | Путь к логам | resources/generated_logs.csv |
| BN_OUTPUT_DIR | Директория вывода | output |
| BN_MODE | Режим (offline/online) | offline |
| BN_MIN_SAMPLES | Минимум samples | 10 |
| BN_SLOPE_CRITICAL | Порог наклона | 2.0 |
| BN_LATENCY_WARN | Warning порог | 150.0 |
| BN_LATENCY_CRITICAL | Critical порог | 250.0 |

## Лицензия

MIT
