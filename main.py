#!/usr/bin/env python3
"""
Bottleneck Detector — CLI точка входа.

Использование:
    python -m bn_detector.main analyze --log-file logs_bn.csv
    python -m bn_detector.main generate --output logs_bn.csv
"""

import argparse
import logging
import sys
from pathlib import Path

from application import LogAnalyzer
from config import get_settings
from domain import ServiceGraph
from domain.detection import SlopeDetector, ThresholdDetector, SecondDerivativeDetector
from infrastructure import CsvLogReader, LogGenerator
from infrastructure.generators.log_generator import create_example_config
from presentation import ScatterPlotter, BinnedPlotter, TimeSeriesPlotter, SurfacePlotter, DerivativePlotter, ConsoleExporter, JsonExporter


def setup_logging(verbose: bool = False):
    """Настраивает логирование"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )


def cmd_analyze(args):
    """Команда анализа логов"""
    settings = get_settings()
    
    log_file = Path(args.log_file) if args.log_file else settings.log_file
    output_dir = Path(args.output) if args.output else settings.output_dir
    
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)
    
    # Создаём компоненты
    reader = CsvLogReader(log_file)
    graph = ServiceGraph()
    
    detectors = [
        SlopeDetector(
            min_samples=settings.detection.min_samples,
            stability_window=settings.detection.stability_window,
            rps_min=settings.detection.rps_min,
            slope_critical=settings.detection.slope_critical,
            latency_warn=settings.detection.latency_warn,
        ),
        ThresholdDetector(
            min_samples=settings.detection.min_samples,
            latency_warn=settings.detection.latency_warn,
            latency_critical=settings.detection.latency_critical,
        ),
        SecondDerivativeDetector(
            min_samples=20,
            second_derivative_threshold=0.01,
            r_squared_min=0.3,
        )
    ]
    
    plotters = []
    if not args.no_plots:
        plotters = [
            ScatterPlotter(graph, output_dir, settings),
            BinnedPlotter(graph, output_dir, settings, bin_size=settings.plotting.bin_size),
            TimeSeriesPlotter(graph, output_dir, settings),
            SurfacePlotter(graph, output_dir, settings),
            DerivativePlotter(graph, output_dir, settings, second_derivative_threshold=0.01),
        ]
    
    analyzer = LogAnalyzer(
        reader=reader,
        graph=graph,
        detectors=detectors,
        plotters=plotters,
    )
    
    report = analyzer.run()
    
    console = ConsoleExporter(verbose=args.verbose)
    console.export(report)
    
    if args.json:
        json_exporter = JsonExporter(output_dir)
        json_path = json_exporter.export(report)
        print(f"JSON report saved: {json_path}")
    
    if report.status == "critical":
        sys.exit(2)
    elif report.status == "warning":
        sys.exit(1)
    sys.exit(0)


def cmd_generate(args):
    output_path = Path(args.output)
    
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)
        generator = LogGenerator.from_json(config_path)
    else:
        config = create_example_config()
        if args.duration:
            config.duration_seconds = args.duration
        generator = LogGenerator(config)
    
    count = generator.generate(output_path)
    print(f"Generated {count} log entries to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Bottleneck Detector — анализ логов микросервисов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    analyze_parser = subparsers.add_parser('analyze', help='Анализ логов')
    analyze_parser.add_argument(
        '-l', '--log-file',
        help='Путь к CSV файлу с логами'
    )
    analyze_parser.add_argument(
        '-o', '--output',
        help='Директория для вывода'
    )
    analyze_parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Не генерировать графики'
    )
    analyze_parser.add_argument(
        '--json',
        action='store_true',
        help='Сохранить JSON отчёт'
    )
    
    generate_parser = subparsers.add_parser('generate', help='Генерация логов')
    generate_parser.add_argument(
        '-o', '--output',
        default='generated_logs.csv',
        help='Путь для сохранения логов'
    )
    generate_parser.add_argument(
        '-c', '--config',
        help='Путь к JSON конфигурации'
    )
    generate_parser.add_argument(
        '-d', '--duration',
        type=int,
        help='Длительность в секундах'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'generate':
        cmd_generate(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
