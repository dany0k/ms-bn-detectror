"""
Вывод результатов в консоль.
"""

from application.analyzer import AnalysisReport


class ConsoleExporter:
    """Выводит результаты анализа в консоль"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def export(self, report: AnalysisReport) -> None:
        """Выводит отчёт в консоль"""
        print()
        print("=" * 60)
        print("ANALYSIS REPORT")
        print("=" * 60)
        print()
        
        # Общая статистика
        status_emoji = {
            "ok": "✅",
            "warning": "⚠️",
            "critical": "🔴"
        }
        print(f"Status: {status_emoji.get(report.status, '')} {report.status.upper()}")
        print(f"Logs processed: {report.logs_processed:,}")
        print(f"Nodes: {report.graph.node_count}")
        print(f"Edges: {report.graph.edge_count}")
        print(f"Bottlenecks: {len(report.graph.bottleneck_edges)}")
        print()
        
        # Детали по рёбрам
        if self.verbose:
            print("EDGES:")
            print("-" * 60)
            for (src, dst), edge in report.graph.iter_edges():
                is_bn = "🔴" if report.graph.is_bottleneck(src, dst) else "  "
                print(
                    f"  {is_bn} {src} → {dst}"
                )
                print(
                    f"      samples: {edge.count}, "
                    f"rps: [{edge.min_rps:.0f}, {edge.max_rps:.0f}], "
                    f"avg_lat: {edge.avg_latency:.1f}ms"
                )
            print()
        
        # Алерты
        if report.alerts:
            print("ALERTS:")
            print("-" * 60)
            for alert in report.alerts:
                severity_emoji = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "critical": "🔴"
                }
                emoji = severity_emoji.get(alert.severity.value, "")
                print(f"  {emoji} [{alert.severity.value.upper()}] {alert.message}")
            print()
        
        # Графики
        if report.plots:
            print(f"Plots generated: {len(report.plots)}")
            if self.verbose:
                for plot in report.plots:
                    print(f"  - {plot}")
            print()
        
        print("=" * 60)
