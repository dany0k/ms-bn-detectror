"""
Реалистичный генератор логов микросервисов.

Имитирует реальное поведение:
- Шум и случайные спайки latency
- Периодические аномалии (GC паузы, сетевые задержки)
- Естественные колебания RPS
- Корреляция между сервисами
- Дневные паттерны нагрузки
"""

import csv
import json
import math
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class NoiseType(str, Enum):
    """Типы шума для latency"""
    NORMAL = "normal"           # Обычный гауссов шум
    LOGNORMAL = "lognormal"     # Логнормальный (чаще в реальности)
    SPIKY = "spiky"             # С редкими большими спайками


@dataclass
class RealisticServiceConfig:
    """Конфигурация сервиса с реалистичными параметрами"""
    
    src_service: str
    src_route: str
    dst_service: str
    dst_route: str
    
    # Базовые параметры
    base_latency: float = 10.0
    
    # Шум
    noise_type: NoiseType = NoiseType.LOGNORMAL
    noise_stddev: float = 0.2          # Стандартное отклонение (доля от base)
    
    # Спайки (редкие большие задержки)
    spike_probability: float = 0.02     # 2% запросов — спайки
    spike_multiplier: float = 5.0       # Спайк = latency × 5
    
    # Периодические аномалии (например GC)
    periodic_anomaly_interval: int = 0  # Каждые N секунд (0 = выкл)
    periodic_anomaly_duration: int = 2  # Длительность аномалии
    periodic_anomaly_multiplier: float = 3.0
    
    # Bottleneck
    bottleneck_rps: float = 0           # 0 = нет bottleneck
    bottleneck_multiplier: float = 2.0
    bottleneck_per_rps: float = 1.0
    
    # "Залипающий" bottleneck — латенси не восстанавливается после спада RPS
    bottleneck_sticky: bool = False     # Включить залипание
    bottleneck_sticky_decay: float = 0.0  # Скорость восстановления (0 = никогда, 0.01 = медленно)
    bottleneck_degradation_rate: float = 0.0  # Рост латенси после bottleneck (ms в секунду)

    # Зависимость от других сервисов (propagation delay)
    depends_on: Optional[str] = None    # Имя сервиса-зависимости
    dependency_factor: float = 0.3      # Какую долю latency зависимости добавлять

    @classmethod
    def from_dict(cls, data: Dict) -> 'RealisticServiceConfig':
        return cls(
            src_service=data['src_service'],
            src_route=data['src_route'],
            dst_service=data['dst_service'],
            dst_route=data['dst_route'],
            base_latency=float(data.get('base_latency', 10.0)),
            noise_type=NoiseType(data.get('noise_type', 'lognormal')),
            noise_stddev=float(data.get('noise_stddev', 0.2)),
            spike_probability=float(data.get('spike_probability', 0.02)),
            spike_multiplier=float(data.get('spike_multiplier', 5.0)),
            periodic_anomaly_interval=int(data.get('periodic_anomaly_interval', 0)),
            periodic_anomaly_duration=int(data.get('periodic_anomaly_duration', 2)),
            periodic_anomaly_multiplier=float(data.get('periodic_anomaly_multiplier', 3.0)),
            bottleneck_rps=float(data.get('bottleneck_rps', 0)),
            bottleneck_multiplier=float(data.get('bottleneck_multiplier', 2.0)),
            bottleneck_per_rps=float(data.get('bottleneck_per_rps', 1.0)),
            bottleneck_sticky=bool(data.get('bottleneck_sticky', False)),
            bottleneck_sticky_decay=float(data.get('bottleneck_sticky_decay', 0.0)),
            bottleneck_degradation_rate=float(data.get('bottleneck_degradation_rate', 0.0)),
            depends_on=data.get('depends_on'),
            dependency_factor=float(data.get('dependency_factor', 0.3)),
        )

    @property
    def name(self) -> str:
        return f"{self.dst_service}{self.dst_route}"


@dataclass
class RealisticLoadConfig:
    """Конфигурация реалистичной нагрузки"""

    name: str = "realistic-load"
    description: str = ""
    start_time: datetime = field(
        default_factory=lambda: datetime.fromisoformat("2025-01-20T08:00:00+00:00")
    )
    duration_seconds: int = 3600  # 1 час по умолчанию

    # Базовый RPS и вариации
    base_rps: float = 50.0
    rps_noise_stddev: float = 0.1       # 10% колебания RPS

    # Тренд нагрузки (синусоида для имитации дневного паттерна)
    daily_pattern: bool = False
    daily_peak_hour: int = 14           # Пик в 14:00
    daily_amplitude: float = 0.3        # ±30% от base_rps

    # Линейный тренд
    rps_trend_per_hour: float = 0.0     # Рост RPS в час (0 = без тренда)

    # Ступеньки (опционально, поверх базового)
    load_steps: List[Dict] = field(default_factory=list)

    # Сервисы
    services: List[RealisticServiceConfig] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Path) -> 'RealisticLoadConfig':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RealisticLoadConfig':
        config = cls(
            name=data.get('name', 'realistic-load'),
            description=data.get('description', ''),
            start_time=datetime.fromisoformat(
                data.get('start_time', "2025-01-20T08:00:00+00:00")
            ),
            duration_seconds=int(data.get('duration_seconds', 3600)),
            base_rps=float(data.get('base_rps', 50.0)),
            rps_noise_stddev=float(data.get('rps_noise_stddev', 0.1)),
            daily_pattern=bool(data.get('daily_pattern', False)),
            daily_peak_hour=int(data.get('daily_peak_hour', 14)),
            daily_amplitude=float(data.get('daily_amplitude', 0.3)),
            rps_trend_per_hour=float(data.get('rps_trend_per_hour', 0.0)),
            load_steps=data.get('load_steps', []),
            services=[
                RealisticServiceConfig.from_dict(s)
                for s in data.get('services', [])
            ],
        )
        return config

    def to_json(self, path: Path) -> None:
        data = {
            'name': self.name,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'base_rps': self.base_rps,
            'rps_noise_stddev': self.rps_noise_stddev,
            'daily_pattern': self.daily_pattern,
            'daily_peak_hour': self.daily_peak_hour,
            'daily_amplitude': self.daily_amplitude,
            'rps_trend_per_hour': self.rps_trend_per_hour,
            'load_steps': self.load_steps,
            'services': [
                {
                    'src_service': s.src_service,
                    'src_route': s.src_route,
                    'dst_service': s.dst_service,
                    'dst_route': s.dst_route,
                    'base_latency': s.base_latency,
                    'noise_type': s.noise_type.value,
                    'noise_stddev': s.noise_stddev,
                    'spike_probability': s.spike_probability,
                    'spike_multiplier': s.spike_multiplier,
                    'periodic_anomaly_interval': s.periodic_anomaly_interval,
                    'periodic_anomaly_duration': s.periodic_anomaly_duration,
                    'periodic_anomaly_multiplier': s.periodic_anomaly_multiplier,
                    'bottleneck_rps': s.bottleneck_rps,
                    'bottleneck_multiplier': s.bottleneck_multiplier,
                    'bottleneck_per_rps': s.bottleneck_per_rps,
                    'depends_on': s.depends_on,
                    'dependency_factor': s.dependency_factor,
                }
                for s in self.services
            ],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class RealisticLogGenerator:
    """Генератор реалистичных логов"""

    CSV_HEADER = [
        'traceId', 'spanId', 'parentSpanId', 'timestamp',
        'srcService', 'srcRoute', 'dstService', 'dstRoute',
        'latency_ms', 'latency', 'rps'
    ]

    def __init__(self, config: RealisticLoadConfig):
        self.config = config
        self._service_latencies: Dict[str, float] = {}  # Для корреляций
        self._sticky_state: Dict[str, float] = {}       # Для залипающего bottleneck
        self._max_rps_seen: Dict[str, float] = {}       # Максимальный RPS для каждого сервиса
        self._bottleneck_triggered_at: Dict[str, int] = {}  # Когда сработал bottleneck
        self._degradation_accumulator: Dict[str, float] = {}  # Накопленная деградация

    @classmethod
    def from_json(cls, path: Path) -> 'RealisticLogGenerator':
        config = RealisticLoadConfig.from_json(path)
        return cls(config)

    def _get_rps_at_second(self, second: int) -> float:
        """Вычисляет RPS для конкретной секунды"""
        base = self.config.base_rps

        # 1. Линейный тренд
        hours_elapsed = second / 3600
        base += self.config.rps_trend_per_hour * hours_elapsed

        # 2. Дневной паттерн (синусоида)
        if self.config.daily_pattern:
            current_time = self.config.start_time + timedelta(seconds=second)
            hour = current_time.hour + current_time.minute / 60

            # Синусоида с пиком в daily_peak_hour
            phase = (hour - self.config.daily_peak_hour) * math.pi / 12
            daily_factor = 1 + self.config.daily_amplitude * math.cos(phase)
            base *= daily_factor

        # 3. Ступеньки (если заданы)
        if self.config.load_steps:
            time_offset = 0
            for step in self.config.load_steps:
                step_duration = step.get('duration_seconds', 0)
                ramp = step.get('ramp_seconds', 0)

                if second < time_offset + ramp + step_duration:
                    # Мы на этой ступеньке
                    if second < time_offset + ramp:
                        # В фазе рампы
                        progress = (second - time_offset) / ramp if ramp > 0 else 1
                        prev_rps = base if time_offset == 0 else self.config.load_steps[
                            self.config.load_steps.index(step) - 1
                        ].get('rps', base)
                        base = prev_rps + (step['rps'] - prev_rps) * progress
                    else:
                        base = step['rps']
                    break
                time_offset += ramp + step_duration

        # 4. Случайный шум
        noise = random.gauss(0, self.config.rps_noise_stddev * base)

        return max(base + noise, 1.0)

    def _get_latency(
        self,
        service: RealisticServiceConfig,
        current_rps: float,
        second: int
    ) -> float:
        """Вычисляет реалистичную latency"""
        base = service.base_latency
        svc_name = service.name

        # 1. Bottleneck (обычный или залипающий)
        if service.bottleneck_rps > 0:
            if service.bottleneck_sticky:
                # Залипающий bottleneck — запоминаем максимальный RPS
                if svc_name not in self._max_rps_seen:
                    self._max_rps_seen[svc_name] = 0
                    self._sticky_state[svc_name] = 0
                    self._bottleneck_triggered_at[svc_name] = -1
                    self._degradation_accumulator[svc_name] = 0

                # Обновляем максимум если текущий RPS выше
                if current_rps > self._max_rps_seen[svc_name]:
                    self._max_rps_seen[svc_name] = current_rps

                # Вычисляем "эффективный" RPS для расчёта latency
                effective_rps = self._max_rps_seen[svc_name]

                # Медленное восстановление (decay)
                if service.bottleneck_sticky_decay > 0 and current_rps < effective_rps:
                    decay = service.bottleneck_sticky_decay
                    self._max_rps_seen[svc_name] = effective_rps - decay * (effective_rps - current_rps)
                    effective_rps = self._max_rps_seen[svc_name]

                # Применяем bottleneck на основе effective_rps
                if effective_rps > service.bottleneck_rps:
                    excess = effective_rps - service.bottleneck_rps
                    base = base * service.bottleneck_multiplier + excess * service.bottleneck_per_rps

                    # Запоминаем момент срабатывания bottleneck
                    if self._bottleneck_triggered_at[svc_name] < 0:
                        self._bottleneck_triggered_at[svc_name] = second

                    # Накапливаем деградацию (латенси растёт со временем после bottleneck)
                    if service.bottleneck_degradation_rate > 0:
                        time_since_trigger = second - self._bottleneck_triggered_at[svc_name]
                        self._degradation_accumulator[svc_name] = time_since_trigger * service.bottleneck_degradation_rate
                        base += self._degradation_accumulator[svc_name]
            else:
                # Обычный bottleneck
                if current_rps > service.bottleneck_rps:
                    excess = current_rps - service.bottleneck_rps
                    base = base * service.bottleneck_multiplier + excess * service.bottleneck_per_rps

        # 2. Периодическая аномалия
        if service.periodic_anomaly_interval > 0:
            cycle_pos = second % service.periodic_anomaly_interval
            if cycle_pos < service.periodic_anomaly_duration:
                base *= service.periodic_anomaly_multiplier

        # 3. Зависимость от другого сервиса
        if service.depends_on and service.depends_on in self._service_latencies:
            dep_latency = self._service_latencies[service.depends_on]
            base += dep_latency * service.dependency_factor

        # 4. Шум
        if service.noise_type == NoiseType.NORMAL:
            noise = random.gauss(0, service.noise_stddev * base)
            latency = base + noise
        elif service.noise_type == NoiseType.LOGNORMAL:
            # Логнормальное распределение — более реалистичное
            sigma = service.noise_stddev
            mu = math.log(base) - sigma**2 / 2  # Чтобы среднее было = base
            latency = random.lognormvariate(mu, sigma)
        else:  # SPIKY
            noise = random.gauss(0, service.noise_stddev * base * 0.5)
            latency = base + noise

        # 5. Случайные спайки
        if random.random() < service.spike_probability:
            latency *= service.spike_multiplier
            # Добавляем вариацию к спайкам
            latency *= random.uniform(0.8, 1.5)

        # Сохраняем для корреляций
        self._service_latencies[service.name] = latency

        return max(latency, 0.1)

    def generate(self, output_path: Path) -> int:
        """Генерирует CSV с реалистичными логами"""
        total_records = 0

        logger.info(f"Generating realistic logs: {self.config.name}")
        logger.info(f"Duration: {self.config.duration_seconds}s, Base RPS: {self.config.base_rps}")

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_HEADER)

            trace_id = 1
            span_id = 1

            for second in range(self.config.duration_seconds):
                rps = self._get_rps_at_second(second)
                timestamp = self.config.start_time + timedelta(seconds=second)

                # Очищаем кэш latency для новой секунды
                self._service_latencies.clear()

                for service in self.config.services:
                    latency = self._get_latency(service, rps, second)

                    writer.writerow([
                        f"trace{trace_id:08d}",
                        f"span{span_id:08d}",
                        '',
                        timestamp.isoformat(),
                        service.src_service,
                        service.src_route,
                        service.dst_service,
                        service.dst_route,
                        round(latency, 2),
                        round(latency + random.uniform(-0.1, 0.1), 2),
                        int(rps),
                    ])

                    span_id += 1
                    trace_id += 1
                    total_records += 1

        logger.info(f"Generated {total_records} records")
        return total_records

    def print_config(self) -> None:
        """Выводит конфигурацию"""
        print(f"\n{'='*60}")
        print(f"Realistic Load Config: {self.config.name}")
        print(f"{'='*60}")

        if self.config.description:
            print(f"Description: {self.config.description}")

        print(f"\nDuration: {self.config.duration_seconds}s ({self.config.duration_seconds/60:.1f} min)")
        print(f"Base RPS: {self.config.base_rps}")
        print(f"RPS noise: ±{self.config.rps_noise_stddev*100:.0f}%")

        if self.config.daily_pattern:
            print(f"Daily pattern: peak at {self.config.daily_peak_hour}:00, ±{self.config.daily_amplitude*100:.0f}%")

        if self.config.rps_trend_per_hour:
            print(f"RPS trend: {self.config.rps_trend_per_hour:+.1f}/hour")

        print(f"\nServices ({len(self.config.services)}):")
        print("-" * 50)

        for svc in self.config.services:
            print(f"\n  • {svc.src_service}{svc.src_route} → {svc.dst_service}{svc.dst_route}")
            print(f"    Base latency: {svc.base_latency}ms")
            print(f"    Noise: {svc.noise_type.value}, σ={svc.noise_stddev}")
            print(f"    Spikes: {svc.spike_probability*100:.1f}% @ {svc.spike_multiplier}x")

            if svc.periodic_anomaly_interval > 0:
                print(f"    Periodic anomaly: every {svc.periodic_anomaly_interval}s, "
                      f"{svc.periodic_anomaly_duration}s duration, {svc.periodic_anomaly_multiplier}x")

            if svc.bottleneck_rps > 0:
                print(f"    🔴 Bottleneck: RPS > {svc.bottleneck_rps} → "
                      f"{svc.bottleneck_multiplier}x + {svc.bottleneck_per_rps}ms/rps")

            if svc.depends_on:
                print(f"    Depends on: {svc.depends_on} ({svc.dependency_factor*100:.0f}%)")

        print(f"\n{'='*60}")


def create_realistic_example() -> RealisticLoadConfig:
    """Создаёт пример реалистичной конфигурации"""
    return RealisticLoadConfig(
        name="realistic-microservices",
        description="Реалистичная симуляция: плавный рост RPS до 120 с bottleneck на БД после 90 RPS",
        start_time=datetime.fromisoformat("2025-01-20T10:00:00+00:00"),
        duration_seconds=600,  # 10 минут
        base_rps=30.0,
        rps_noise_stddev=0.08,
        daily_pattern=False,
        rps_trend_per_hour=60.0,  # Рост на 60 RPS в час = 10 RPS за 10 минут → итого ~40 RPS к концу
        load_steps=[
            # Плавные ступеньки
            {"rps": 30, "duration_seconds": 60, "ramp_seconds": 10},
            {"rps": 50, "duration_seconds": 60, "ramp_seconds": 20},
            {"rps": 70, "duration_seconds": 60, "ramp_seconds": 20},
            {"rps": 90, "duration_seconds": 60, "ramp_seconds": 20},
            {"rps": 100, "duration_seconds": 80, "ramp_seconds": 20},
            {"rps": 110, "duration_seconds": 80, "ramp_seconds": 20},
            {"rps": 120, "duration_seconds": 100, "ramp_seconds": 20},
        ],
        services=[
            # Redis кэш — быстрый и стабильный
            RealisticServiceConfig(
                src_service="api-gateway",
                src_route="/v1/data",
                dst_service="redis",
                dst_route="/cache",
                base_latency=2.0,
                noise_type=NoiseType.LOGNORMAL,
                noise_stddev=0.15,
                spike_probability=0.005,  # Редкие спайки
                spike_multiplier=3.0,
            ),
            # PostgreSQL — bottleneck после 90 RPS
            RealisticServiceConfig(
                src_service="api-gateway",
                src_route="/v1/data",
                dst_service="postgres",
                dst_route="/query",
                base_latency=12.0,
                noise_type=NoiseType.LOGNORMAL,
                noise_stddev=0.25,
                spike_probability=0.02,
                spike_multiplier=4.0,
                periodic_anomaly_interval=120,  # Каждые 2 минуты
                periodic_anomaly_duration=3,
                periodic_anomaly_multiplier=2.5,
                bottleneck_rps=90,
                bottleneck_multiplier=3.0,
                bottleneck_per_rps=2.0,
            ),
            # Внешний API — зависит от состояния системы
            RealisticServiceConfig(
                src_service="api-gateway",
                src_route="/v1/external",
                dst_service="external-api",
                dst_route="/fetch",
                base_latency=50.0,
                noise_type=NoiseType.LOGNORMAL,
                noise_stddev=0.4,  # Высокая вариативность
                spike_probability=0.05,  # 5% спайков
                spike_multiplier=3.0,
                depends_on="postgres/query",  # Если БД тормозит, этот тоже
                dependency_factor=0.2,
            ),
        ],
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Realistic Log Generator")
    parser.add_argument('-c', '--config', help='JSON config path')
    parser.add_argument('-o', '--output', default='realistic_logs.csv')
    parser.add_argument('--example', action='store_true', help='Create example config')

    args = parser.parse_args()

    if args.example:
        config = create_realistic_example()
        config.to_json(Path('realistic_config_example.json'))
        print("✅ Example config saved to realistic_config_example.json")

        generator = RealisticLogGenerator(config)
        generator.print_config()
    elif args.config:
        generator = RealisticLogGenerator.from_json(Path(args.config))
        generator.print_config()
        generator.generate(Path(args.output))
        print(f"✅ Logs saved to {args.output}")
    else:
        parser.print_help()