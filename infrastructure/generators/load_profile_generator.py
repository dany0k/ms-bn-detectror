"""
Генератор логов с конфигурируемым профилем нагрузки.

Позволяет задать:
- Ступеньки RPS с длительностью
- Триггеры bottleneck при определённых RPS
- Разные сервисы с разным поведением
"""

import csv
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LoadStep:
    """
    Одна ступенька нагрузки.
    
    Attributes:
        rps: Целевой RPS на этой ступени
        duration_seconds: Длительность ступени в секундах
        ramp_seconds: Время перехода от предыдущего RPS (плавный рост)
    """
    rps: float
    duration_seconds: int
    ramp_seconds: int = 0  # 0 = мгновенный переход
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LoadStep':
        return cls(
            rps=float(data['rps']),
            duration_seconds=int(data['duration_seconds']),
            ramp_seconds=int(data.get('ramp_seconds', 0)),
        )


@dataclass
class BottleneckTrigger:
    """
    Триггер bottleneck — при каком RPS начинается degradation.json.
    
    Attributes:
        rps_threshold: При каком RPS включается bottleneck
        latency_multiplier: Во сколько раз растёт latency
        latency_per_rps: Дополнительная latency за каждый RPS выше порога
    """
    rps_threshold: float
    latency_multiplier: float = 1.0  # Базовый множитель
    latency_per_rps: float = 0.0     # ms за каждый RPS выше порога
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BottleneckTrigger':
        return cls(
            rps_threshold=float(data['rps_threshold']),
            latency_multiplier=float(data.get('latency_multiplier', 1.0)),
            latency_per_rps=float(data.get('latency_per_rps', 0.0)),
        )
    
    def compute_latency(self, base_latency: float, current_rps: float) -> float:
        """Вычисляет latency с учётом bottleneck"""
        if current_rps < self.rps_threshold:
            return base_latency
        
        # Применяем множитель и добавляем latency за превышение
        excess_rps = current_rps - self.rps_threshold
        degraded = base_latency * self.latency_multiplier
        degraded += excess_rps * self.latency_per_rps
        
        return degraded


@dataclass 
class ServiceConfig:
    """
    Конфигурация одного сервиса/endpoint.
    
    Attributes:
        src_service: Исходный сервис
        src_route: Исходный endpoint
        dst_service: Целевой сервис  
        dst_route: Целевой endpoint
        base_latency: Базовая latency в нормальном режиме
        latency_noise: Случайный шум ±
        bottleneck: Опциональный триггер bottleneck
    """
    src_service: str
    src_route: str
    dst_service: str
    dst_route: str
    base_latency: float = 10.0
    latency_noise: float = 1.0
    bottleneck: Optional[BottleneckTrigger] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceConfig':
        bottleneck = None
        if 'bottleneck' in data:
            bottleneck = BottleneckTrigger.from_dict(data['bottleneck'])
        
        return cls(
            src_service=data['src_service'],
            src_route=data['src_route'],
            dst_service=data['dst_service'],
            dst_route=data['dst_route'],
            base_latency=float(data.get('base_latency', 10.0)),
            latency_noise=float(data.get('latency_noise', 1.0)),
            bottleneck=bottleneck,
        )
    
    def get_latency(self, current_rps: float) -> float:
        """Вычисляет latency для текущего RPS"""
        base = self.base_latency
        
        # Применяем bottleneck если есть
        if self.bottleneck:
            base = self.bottleneck.compute_latency(base, current_rps)
        
        # Добавляем шум
        noise = random.uniform(-self.latency_noise, self.latency_noise)
        return max(base + noise, 0.1)
    
    @property
    def edge_name(self) -> str:
        return f"{self.src_service}{self.src_route} → {self.dst_service}{self.dst_route}"


@dataclass
class LoadProfileConfig:
    """
    Полная конфигурация генератора.
    """
    name: str = "default"
    description: str = ""
    start_time: datetime = field(
        default_factory=lambda: datetime.fromisoformat("2025-01-01T12:00:00+00:00")
    )
    load_steps: List[LoadStep] = field(default_factory=list)
    services: List[ServiceConfig] = field(default_factory=list)
    
    @classmethod
    def from_json(cls, path: Path) -> 'LoadProfileConfig':
        """Загружает конфигурацию из JSON файла"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LoadProfileConfig':
        start_time = datetime.fromisoformat(
            data.get('start_time', "2025-01-01T12:00:00+00:00")
        )
        
        return cls(
            name=data.get('name', 'default'),
            description=data.get('description', ''),
            start_time=start_time,
            load_steps=[LoadStep.from_dict(s) for s in data.get('load_steps', [])],
            services=[ServiceConfig.from_dict(s) for s in data.get('services', [])],
        )
    
    def to_json(self, path: Path) -> None:
        """Сохраняет конфигурацию в JSON файл"""
        data = {
            'name': self.name,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'load_steps': [
                {
                    'rps': step.rps,
                    'duration_seconds': step.duration_seconds,
                    'ramp_seconds': step.ramp_seconds,
                }
                for step in self.load_steps
            ],
            'services': [
                {
                    'src_service': svc.src_service,
                    'src_route': svc.src_route,
                    'dst_service': svc.dst_service,
                    'dst_route': svc.dst_route,
                    'base_latency': svc.base_latency,
                    'latency_noise': svc.latency_noise,
                    **(
                        {
                            'bottleneck': {
                                'rps_threshold': svc.bottleneck.rps_threshold,
                                'latency_multiplier': svc.bottleneck.latency_multiplier,
                                'latency_per_rps': svc.bottleneck.latency_per_rps,
                            }
                        }
                        if svc.bottleneck else {}
                    ),
                }
                for svc in self.services
            ],
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @property
    def total_duration(self) -> int:
        """Общая длительность в секундах"""
        return sum(
            step.duration_seconds + step.ramp_seconds 
            for step in self.load_steps
        )


class LoadProfileGenerator:
    """
    Генератор логов с профилем нагрузки.
    
    Создаёт CSV с логами, где RPS меняется по заданным ступеням,
    и latency деградирует при достижении bottleneck-порогов.
    """
    
    CSV_HEADER = [
        'traceId', 'spanId', 'parentSpanId', 'timestamp',
        'srcService', 'srcRoute', 'dstService', 'dstRoute',
        'latency_ms', 'latency', 'rps'
    ]
    
    def __init__(self, config: LoadProfileConfig):
        self.config = config
    
    @classmethod
    def from_json(cls, path: Path) -> 'LoadProfileGenerator':
        """Создаёт генератор из JSON конфига"""
        config = LoadProfileConfig.from_json(path)
        return cls(config)
    
    def _build_rps_timeline(self) -> List[float]:
        """
        Строит timeline RPS для каждой секунды.
        
        Returns:
            Список RPS для каждой секунды
        """
        timeline = []
        current_rps = 0.0
        
        for step in self.config.load_steps:
            # Фаза рампы (плавный переход)
            if step.ramp_seconds > 0:
                rps_delta = (step.rps - current_rps) / step.ramp_seconds
                for _ in range(step.ramp_seconds):
                    current_rps += rps_delta
                    # Добавляем небольшой шум
                    noisy_rps = current_rps + random.uniform(-0.5, 0.5)
                    timeline.append(max(noisy_rps, 1.0))
            
            # Фаза плато (стабильный RPS)
            current_rps = step.rps
            for _ in range(step.duration_seconds):
                # Добавляем небольшой шум на плато
                noisy_rps = current_rps + random.uniform(-1.0, 1.0)
                timeline.append(max(noisy_rps, 1.0))
        
        return timeline
    
    def generate(self, output_path: Path) -> int:
        """
        Генерирует CSV файл с логами.
        
        Args:
            output_path: Путь для сохранения
            
        Returns:
            Количество сгенерированных записей
        """
        rps_timeline = self._build_rps_timeline()
        total_records = 0
        
        logger.info(f"Generating logs: {self.config.name}")
        logger.info(f"Total duration: {len(rps_timeline)} seconds")
        logger.info(f"Services: {len(self.config.services)}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_HEADER)
            
            trace_id = 1
            span_id = 1
            
            for second, rps in enumerate(rps_timeline):
                timestamp = self.config.start_time + timedelta(seconds=second)
                
                for service in self.config.services:
                    latency = service.get_latency(rps)
                    
                    writer.writerow([
                        f"trace{trace_id:06d}",
                        f"span{span_id:06d}",
                        '',  # no parent
                        timestamp.isoformat(),
                        service.src_service,
                        service.src_route,
                        service.dst_service,
                        service.dst_route,
                        round(latency, 1),
                        round(latency + random.uniform(-0.3, 0.3), 1),
                        int(rps),
                    ])
                    
                    span_id += 1
                    trace_id += 1
                    total_records += 1
        
        logger.info(f"Generated {total_records} records to {output_path}")
        return total_records
    
    def print_profile(self) -> None:
        """Выводит профиль нагрузки в консоль"""
        print(f"\n{'='*60}")
        print(f"Load Profile: {self.config.name}")
        print(f"{'='*60}")
        
        if self.config.description:
            print(f"Description: {self.config.description}")
        
        print(f"\nTotal duration: {self.config.total_duration} seconds")
        
        print(f"\nLoad Steps:")
        print("-" * 40)
        time_offset = 0
        for i, step in enumerate(self.config.load_steps, 1):
            ramp_info = f" (ramp: {step.ramp_seconds}s)" if step.ramp_seconds else ""
            print(f"  {i}. RPS: {step.rps:>5.0f} | Duration: {step.duration_seconds:>4}s{ramp_info}")
            print(f"      Time: {time_offset}s - {time_offset + step.ramp_seconds + step.duration_seconds}s")
            time_offset += step.ramp_seconds + step.duration_seconds
        
        print(f"\nServices:")
        print("-" * 40)
        for svc in self.config.services:
            print(f"  • {svc.edge_name}")
            print(f"    Base latency: {svc.base_latency}ms (±{svc.latency_noise})")
            if svc.bottleneck:
                bn = svc.bottleneck
                print(f"    🔴 BOTTLENECK at RPS > {bn.rps_threshold}:")
                print(f"       Multiplier: {bn.latency_multiplier}x")
                if bn.latency_per_rps > 0:
                    print(f"       +{bn.latency_per_rps}ms per RPS above threshold")
            else:
                print(f"    ✅ No bottleneck configured")
        
        print(f"{'='*60}\n")


def create_example_config() -> LoadProfileConfig:
    """
    Создаёт пример конфигурации для демонстрации.
    
    Сценарий:
    - Нагрузка растёт ступенями: 10 → 30 → 50 → 70 → 50 → 30
    - Сервис db-service имеет bottleneck при RPS > 40
    - Сервис cache-service работает стабильно
    """
    return LoadProfileConfig(
        name="bottleneck-demo",
        description="Демонстрация bottleneck при высокой нагрузке",
        start_time=datetime.fromisoformat("2025-01-15T10:00:00+00:00"),
        load_steps=[
            # Разогрев
            LoadStep(rps=10, duration_seconds=30, ramp_seconds=5),
            # Рост нагрузки
            LoadStep(rps=30, duration_seconds=60, ramp_seconds=10),
            LoadStep(rps=50, duration_seconds=60, ramp_seconds=10),
            LoadStep(rps=70, duration_seconds=60, ramp_seconds=10),
            # Спад нагрузки
            LoadStep(rps=50, duration_seconds=30, ramp_seconds=5),
            LoadStep(rps=30, duration_seconds=30, ramp_seconds=5),
        ],
        services=[
            # Сервис БЕЗ bottleneck — всегда стабильный
            ServiceConfig(
                src_service="api-gateway",
                src_route="/v1/users",
                dst_service="cache-service",
                dst_route="/get",
                base_latency=5.0,
                latency_noise=0.5,
                bottleneck=None,
            ),
            # Сервис С bottleneck — деградирует при RPS > 40
            ServiceConfig(
                src_service="api-gateway",
                src_route="/v1/users",
                dst_service="db-service",
                dst_route="/query",
                base_latency=15.0,
                latency_noise=2.0,
                bottleneck=BottleneckTrigger(
                    rps_threshold=40,
                    latency_multiplier=2.0,    # При пороге latency x2
                    latency_per_rps=1.5,       # +1.5ms за каждый RPS выше 40
                ),
            ),
            # Ещё один сервис с мягким bottleneck
            ServiceConfig(
                src_service="api-gateway",
                src_route="/v1/orders",
                dst_service="inventory-service", 
                dst_route="/check",
                base_latency=20.0,
                latency_noise=3.0,
                bottleneck=BottleneckTrigger(
                    rps_threshold=60,
                    latency_multiplier=1.5,
                    latency_per_rps=0.8,
                ),
            ),
        ],
    )


# CLI для быстрого использования
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load Profile Log Generator")
    parser.add_argument('-c', '--config', help='Path to JSON config')
    parser.add_argument('-o', '--output', default='generated_logs.csv', help='Output CSV path')
    parser.add_argument('--example', action='store_true', help='Generate example config')
    parser.add_argument('--print', action='store_true', help='Print load profile')
    
    args = parser.parse_args()
    
    if args.example:
        config = create_example_config()
        config_path = Path('load_profile_example.json')
        config.to_json(config_path)
        print(f"✅ Example config saved to {config_path}")
        
        generator = LoadProfileGenerator(config)
        generator.print_profile()
    elif args.config:
        generator = LoadProfileGenerator.from_json(Path(args.config))
        
        if getattr(args, 'print'):
            generator.print_profile()
        
        count = generator.generate(Path(args.output))
        print(f"✅ Generated {count} records to {args.output}")
    else:
        parser.print_help()
