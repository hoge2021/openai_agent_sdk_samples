"""
continuous_eval.py - 継続的評価とモニタリング
リサーチボットの継続的な品質監視とパフォーマンス追跡
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import schedule

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn

from openai import AsyncOpenAI
from eval_config import (
    EvalConfig, TestSuite, MetricsCalculator,
    create_sample_config, create_sample_test_suite
)


# ==================== データベース管理 ====================

class EvalDatabase:
    """評価結果を管理するデータベース"""
    
    def __init__(self, db_path: str = "eval_results.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 評価結果テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT NOT NULL,
                success BOOLEAN,
                latency REAL,
                total_cost REAL,
                planner_score REAL,
                search_score REAL,
                report_score REAL,
                report_length INTEGER,
                num_searches INTEGER,
                error_message TEXT,
                metadata JSON
            )
        """)
        
        # パフォーマンストレンドテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                agent_name TEXT,
                metadata JSON
            )
        """)
        
        # アラートテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                metadata JSON
            )
        """)
        
        conn.commit()
        conn.close()
    
    def insert_result(self, result: Dict[str, Any]) -> int:
        """評価結果を挿入"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO eval_results (
                query, success, latency, total_cost,
                planner_score, search_score, report_score,
                report_length, num_searches, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.get("query"),
            result.get("success"),
            result.get("latency"),
            result.get("total_cost"),
            result.get("planner_quality_score"),
            result.get("search_quality_score"),
            result.get("report_quality_score"),
            result.get("report_length"),
            result.get("num_searches"),
            result.get("error_message"),
            json.dumps(result.get("metadata", {}))
        ))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return result_id
    
    def get_recent_results(self, hours: int = 24) -> pd.DataFrame:
        """最近の評価結果を取得"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM eval_results
            WHERE timestamp > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        """.format(hours)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def insert_metric(self, metric_name: str, metric_value: float, 
                     agent_name: Optional[str] = None, metadata: Optional[Dict] = None):
        """パフォーマンスメトリクスを挿入"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_trends (
                metric_name, metric_value, agent_name, metadata
            ) VALUES (?, ?, ?, ?)
        """, (
            metric_name,
            metric_value,
            agent_name,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def create_alert(self, alert_type: str, severity: str, message: str, 
                    metadata: Optional[Dict] = None):
        """アラートを作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts (
                alert_type, severity, message, metadata
            ) VALUES (?, ?, ?, ?)
        """, (
            alert_type,
            severity,
            message,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()


# ==================== モニタリングシステム ====================

class PerformanceMonitor:
    """パフォーマンスモニタリングシステム"""
    
    def __init__(self, db: EvalDatabase, config: EvalConfig):
        self.db = db
        self.config = config
        self.console = Console()
        self.alerts = []
    
    def check_thresholds(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """閾値チェックとアラート生成"""
        alerts = []
        
        # レイテンシチェック
        if metrics.get("latency", 0) > self.config.performance_criteria.max_latency_seconds:
            alerts.append({
                "type": "LATENCY",
                "severity": "WARNING",
                "message": f"Latency exceeded threshold: {metrics['latency']:.2f}s > {self.config.performance_criteria.max_latency_seconds}s"
            })
        
        # コストチェック
        if metrics.get("total_cost", 0) > self.config.performance_criteria.max_cost_usd:
            alerts.append({
                "type": "COST",
                "severity": "WARNING",
                "message": f"Cost exceeded threshold: ${metrics['total_cost']:.4f} > ${self.config.performance_criteria.max_cost_usd}"
            })
        
        # 品質スコアチェック
        if metrics.get("planner_quality_score", 1) < self.config.planner_criteria.relevance_threshold:
            alerts.append({
                "type": "QUALITY",
                "severity": "INFO",
                "message": f"Planner quality below threshold: {metrics['planner_quality_score']:.2f}"
            })
        
        if metrics.get("report_quality_score", 1) < self.config.writer_criteria.completeness_threshold:
            alerts.append({
                "type": "QUALITY",
                "severity": "INFO",
                "message": f"Report quality below threshold: {metrics['report_quality_score']:.2f}"
            })
        
        # エラーチェック
        if not metrics.get("success", True):
            alerts.append({
                "type": "ERROR",
                "severity": "ERROR",
                "message": f"Evaluation failed: {metrics.get('error_message', 'Unknown error')}"
            })
        
        return alerts
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """メトリクスを更新してデータベースに保存"""
        
        # データベースに結果を保存
        self.db.insert_result(metrics)
        
        # 個別メトリクスを保存
        self.db.insert_metric("latency", metrics.get("latency", 0))
        self.db.insert_metric("cost", metrics.get("total_cost", 0))
        self.db.insert_metric("planner_score", metrics.get("planner_quality_score", 0), "planner")
        self.db.insert_metric("search_score", metrics.get("search_quality_score", 0), "search")
        self.db.insert_metric("report_score", metrics.get("report_quality_score", 0), "writer")
        
        # 閾値チェック
        alerts = self.check_thresholds(metrics)
        for alert in alerts:
            self.db.create_alert(
                alert["type"],
                alert["severity"],
                alert["message"],
                {"metrics": metrics}
            )
            self.alerts.append(alert)
    
    def generate_dashboard(self) -> Table:
        """ダッシュボードテーブルを生成"""
        
        # 最近24時間のデータを取得
        df = self.db.get_recent_results(24)
        
        if df.empty:
            table = Table(title="No data available")
            return table
        
        # 統計を計算
        success_rate = df['success'].mean() * 100
        avg_latency = df['latency'].mean()
        avg_cost = df['total_cost'].mean()
        avg_planner = df['planner_score'].mean()
        avg_search = df['search_score'].mean()
        avg_report = df['report_score'].mean()
        
        # テーブル作成
        table = Table(title="Performance Dashboard (Last 24 Hours)")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")
        
        # 成功率
        status = "✓" if success_rate > 80 else "⚠"
        table.add_row("Success Rate", f"{success_rate:.1f}%", status)
        
        # レイテンシ
        status = "✓" if avg_latency < self.config.performance_criteria.max_latency_seconds else "⚠"
        table.add_row("Avg Latency", f"{avg_latency:.2f}s", status)
        
        # コスト
        status = "✓" if avg_cost < self.config.performance_criteria.max_cost_usd else "⚠"
        table.add_row("Avg Cost", f"${avg_cost:.4f}", status)
        
        # エージェントスコア
        table.add_row("Planner Score", f"{avg_planner:.2f}/1.0", "✓" if avg_planner > 0.7 else "⚠")
        table.add_row("Search Score", f"{avg_search:.2f}/1.0", "✓" if avg_search > 0.7 else "⚠")
        table.add_row("Report Score", f"{avg_report:.2f}/1.0", "✓" if avg_report > 0.7 else "⚠")
        
        # 総評価数
        table.add_row("Total Evaluations", str(len(df)), "ℹ")
        
        return table
    
    def plot_trends(self, output_dir: str = "./monitoring"):
        """トレンドグラフを生成"""
        
        Path(output_dir).mkdir(exist_ok=True)
        
        # データを取得
        df = self.db.get_recent_results(168)  # 1週間分
        
        if df.empty:
            self.console.print("[yellow]No data available for plotting[/yellow]")
            return
        
        # タイムスタンプをdatetimeに変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 図を作成
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('ResearchBot Performance Trends', fontsize=16)
        
        # 成功率のトレンド
        df_hourly = df.set_index('timestamp').resample('1H')['success'].mean()
        axes[0, 0].plot(df_hourly.index, df_hourly.values * 100)
        axes[0, 0].set_title('Success Rate (%)')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Success Rate')
        axes[0, 0].grid(True, alpha=0.3)
        
        # レイテンシのトレンド
        df_latency = df.set_index('timestamp').resample('1H')['latency'].mean()
        axes[0, 1].plot(df_latency.index, df_latency.values)
        axes[0, 1].axhline(y=self.config.performance_criteria.max_latency_seconds, 
                          color='r', linestyle='--', label='Threshold')
        axes[0, 1].set_title('Average Latency (seconds)')
        axes[0, 1].set_xlabel('Time')
        axes[0, 1].set_ylabel('Latency (s)')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].legend()
        
        # コストのトレンド
        df_cost = df.set_index('timestamp').resample('1H')['total_cost'].mean()
        axes[0, 2].plot(df_cost.index, df_cost.values)
        axes[0, 2].axhline(y=self.config.performance_criteria.max_cost_usd,
                          color='r', linestyle='--', label='Threshold')
        axes[0, 2].set_title('Average Cost (USD)')
        axes[0, 2].set_xlabel('Time')
        axes[0, 2].set_ylabel('Cost ($)')
        axes[0, 2].grid(True, alpha=0.3)
        axes[0, 2].legend()
        
        # エージェントスコアのトレンド
        df_planner = df.set_index('timestamp').resample('1H')['planner_score'].mean()
        axes[1, 0].plot(df_planner.index, df_planner.values, label='Planner')
        axes[1, 0].set_title('Planner Quality Score')
        axes[1, 0].set_xlabel('Time')
        axes[1, 0].set_ylabel('Score')
        axes[1, 0].set_ylim(0, 1)
        axes[1, 0].grid(True, alpha=0.3)
        
        df_search = df.set_index('timestamp').resample('1H')['search_score'].mean()
        axes[1, 1].plot(df_search.index, df_search.values, label='Search')
        axes[1, 1].set_title('Search Quality Score')
        axes[1, 1].set_xlabel('Time')
        axes[1, 1].set_ylabel('Score')
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].grid(True, alpha=0.3)
        
        df_report = df.set_index('timestamp').resample('1H')['report_score'].mean()
        axes[1, 2].plot(df_report.index, df_report.values, label='Report')
        axes[1, 2].set_title('Report Quality Score')
        axes[1, 2].set_xlabel('Time')
        axes[1, 2].set_ylabel('Score')
        axes[1, 2].set_ylim(0, 1)
        axes[1, 2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(output_dir) / f"trends_{timestamp}.png"
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        self.console.print(f"[green]Trends plot saved to: {filepath}[/green]")


# ==================== 継続的評価ランナー ====================

class ContinuousEvaluator:
    """継続的評価を実行するクラス"""
    
    def __init__(self, config: EvalConfig, test_suite: TestSuite):
        self.config = config
        self.test_suite = test_suite
        self.db = EvalDatabase()
        self.monitor = PerformanceMonitor(self.db, config)
        self.console = Console()
        self.client = AsyncOpenAI()
        self.is_running = False
    
    async def run_evaluation_cycle(self):
        """評価サイクルを1回実行"""
        
        self.console.print("\n[bold cyan]Starting evaluation cycle...[/bold cyan]")
        
        # テストケースをランダムに選択（または全て実行）
        import random
        num_tests = min(3, len(self.test_suite.test_cases))
        test_cases = random.sample(self.test_suite.test_cases, num_tests)
        
        for test_case in test_cases:
            self.console.print(f"Evaluating: {test_case.query[:50]}...")
            
            # ここで実際の評価を実行
            # (簡略化のため、ダミーデータを使用)
            metrics = await self._evaluate_query(test_case.query)
            
            # モニターに結果を送信
            self.monitor.update_metrics(metrics)
            
            # 短い待機
            await asyncio.sleep(2)
        
        # ダッシュボード表示
        dashboard = self.monitor.generate_dashboard()
        self.console.print(dashboard)
        
        # アラートチェック
        if self.monitor.alerts:
            self._display_alerts()
            self.monitor.alerts.clear()
    
    async def _evaluate_query(self, query: str) -> Dict[str, Any]:
        """クエリを評価（簡略版）"""
        
        # 実際の評価ロジックをここに実装
        # この例では、ダミーデータを返す
        import random
        
        success = random.random() > 0.1
        
        return {
            "query": query,
            "success": success,
            "latency": random.uniform(10, 60),
            "total_cost": random.uniform(0.05, 0.5),
            "planner_quality_score": random.uniform(0.6, 0.95),
            "search_quality_score": random.uniform(0.6, 0.95),
            "report_quality_score": random.uniform(0.6, 0.95),
            "report_length": random.randint(800, 2000),
            "num_searches": random.randint(3, 15),
            "error_message": None if success else "Simulated error",
            "timestamp": datetime.now().isoformat()
        }
    
    def _display_alerts(self):
        """アラートを表示"""
        
        alert_table = Table(title="⚠ Alerts", show_header=True)
        alert_table.add_column("Type", style="yellow")
        alert_table.add_column("Severity", style="red")
        alert_table.add_column("Message", style="white")
        
        for alert in self.monitor.alerts:
            severity_color = {
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red"
            }.get(alert["severity"], "white")
            
            alert_table.add_row(
                alert["type"],
                f"[{severity_color}]{alert['severity']}[/{severity_color}]",
                alert["message"]
            )
        
        self.console.print(alert_table)
    
    async def start_continuous_monitoring(self, interval_minutes: int = 30):
        """継続的モニタリングを開始"""
        
        self.is_running = True
        self.console.print(f"[bold green]Starting continuous monitoring (interval: {interval_minutes} minutes)[/bold green]")
        
        while self.is_running:
            try:
                # 評価サイクルを実行
                await self.run_evaluation_cycle()
                
                # トレンドグラフを生成（1時間ごと）
                if datetime.now().minute < interval_minutes:
                    self.monitor.plot_trends()
                
                # 次のサイクルまで待機
                self.console.print(f"\n[dim]Next evaluation in {interval_minutes} minutes...[/dim]")
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Monitoring interrupted by user[/yellow]")
                self.is_running = False
                break
            except Exception as e:
                self.console.print(f"[red]Error in monitoring cycle: {e}[/red]")
                await asyncio.sleep(60)  # エラー後は1分待機
    
    def stop(self):
        """モニタリングを停止"""
        self.is_running = False


# ==================== レポート分析 ====================

class ReportAnalyzer:
    """評価結果の詳細分析"""
    
    def __init__(self, db: EvalDatabase):
        self.db = db
        self.console = Console()
    
    def analyze_failure_patterns(self, days: int = 7) -> Dict[str, Any]:
        """失敗パターンを分析"""
        
        df = self.db.get_recent_results(days * 24)
        
        if df.empty:
            return {}
        
        failures = df[df['success'] == False]
        
        if failures.empty:
            return {"message": "No failures found"}
        
        # エラーメッセージでグループ化
        error_patterns = {}
        for _, row in failures.iterrows():
            error = row['error_message'] or 'Unknown'
            if error not in error_patterns:
                error_patterns[error] = []
            error_patterns[error].append({
                'query': row['query'],
                'timestamp': row['timestamp']
            })
        
        return {
            "total_failures": len(failures),
            "failure_rate": len(failures) / len(df),
            "error_patterns": error_patterns
        }
    
    def analyze_performance_degradation(self, days: int = 7) -> Dict[str, Any]:
        """パフォーマンス劣化を分析"""
        
        df = self.db.get_recent_results(days * 24)
        
        if df.empty or len(df) < 10:
            return {"message": "Insufficient data for analysis"}
        
        # 時系列でソート
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # 前半と後半で比較
        mid_point = len(df) // 2
        first_half = df.iloc[:mid_point]
        second_half = df.iloc[mid_point:]
        
        degradation = {}
        
        # 各メトリクスの変化を計算
        metrics = ['latency', 'planner_score', 'search_score', 'report_score']
        
        for metric in metrics:
            first_avg = first_half[metric].mean()
            second_avg = second_half[metric].mean()
            
            if metric == 'latency':
                # レイテンシは増加が悪化
                change_pct = ((second_avg - first_avg) / first_avg) * 100
                is_degraded = second_avg > first_avg * 1.1  # 10%以上の増加
            else:
                # スコアは減少が悪化
                change_pct = ((second_avg - first_avg) / first_avg) * 100
                is_degraded = second_avg < first_avg * 0.9  # 10%以上の減少
            
            degradation[metric] = {
                'first_half_avg': first_avg,
                'second_half_avg': second_avg,
                'change_percent': change_pct,
                'is_degraded': is_degraded
            }
        
        return degradation
    
    def generate_executive_summary(self, days: int = 30) -> str:
        """エグゼクティブサマリーを生成"""
        
        df = self.db.get_recent_results(days * 24)
        
        if df.empty:
            return "No data available for summary"
        
        calculator = MetricsCalculator()
        
        summary = f"""
# Executive Summary - ResearchBot Performance
## Period: Last {days} days

### Key Metrics
- **Total Evaluations**: {len(df)}
- **Success Rate**: {df['success'].mean():.1%}
- **Average Latency**: {df['latency'].mean():.2f} seconds
- **Average Cost per Query**: ${df['total_cost'].mean():.4f}

### Quality Scores (Average)
- **Planner Agent**: {df['planner_score'].mean():.2f}/1.0
- **Search Agent**: {df['search_score'].mean():.2f}/1.0  
- **Writer Agent**: {df['report_score'].mean():.2f}/1.0

### Trends
"""
        
        # 週ごとの比較
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.isocalendar().week
        
        weekly_success = df.groupby('week')['success'].mean()
        weekly_latency = df.groupby('week')['latency'].mean()
        
        summary += "#### Weekly Success Rate\n"
        for week, rate in weekly_success.items():
            summary += f"- Week {week}: {rate:.1%}\n"
        
        summary += "\n#### Weekly Average Latency\n"
        for week, latency in weekly_latency.items():
            summary += f"- Week {week}: {latency:.2f}s\n"
        
        # 問題点の特定
        failures = self.analyze_failure_patterns(days)
        if 'failure_rate' in failures:
            summary += f"\n### Issues Identified\n"
            summary += f"- Failure Rate: {failures['failure_rate']:.1%}\n"
            summary += f"- Most Common Errors:\n"
            
            for error, instances in list(failures.get('error_patterns', {}).items())[:3]:
                summary += f"  - {error}: {len(instances)} occurrences\n"
        
        # 推奨事項
        summary += "\n### Recommendations\n"
        
        if df['latency'].mean() > 40:
            summary += "- Consider optimizing search operations to reduce latency\n"
        
        if df['success'].mean() < 0.9:
            summary += "- Investigate and fix recurring errors to improve success rate\n"
        
        if df['planner_score'].mean() < 0.75:
            summary += "- Review and improve PlannerAgent prompts and logic\n"
        
        return summary


# ==================== メイン実行 ====================

async def main():
    """メイン実行関数"""
    
    console = Console()
    console.print("[bold blue]ResearchBot Continuous Evaluation System[/bold blue]\n")
    
    # 設定とテストスイートを読み込むか作成
    try:
        config = EvalConfig.from_yaml("eval_config.yaml")
        console.print("[green]Loaded configuration from eval_config.yaml[/green]")
    except FileNotFoundError:
        config = create_sample_config()
        config.to_yaml("eval_config.yaml")
        console.print("[yellow]Created sample configuration[/yellow]")
    
    try:
        test_suite = TestSuite.from_file("test_suite.yaml")
        console.print("[green]Loaded test suite from test_suite.yaml[/green]")
    except FileNotFoundError:
        test_suite = create_sample_test_suite()
        test_suite.to_file("test_suite.yaml")
        console.print("[yellow]Created sample test suite[/yellow]")
    
    # メニュー表示
    console.print("\n[bold]Select operation mode:[/bold]")
    console.print("1. Run single evaluation cycle")
    console.print("2. Start continuous monitoring")
    console.print("3. Generate performance report")
    console.print("4. Analyze failure patterns")
    console.print("5. Plot performance trends")
    
    choice = console.input("\nEnter choice (1-5): ")
    
    evaluator = ContinuousEvaluator(config, test_suite)
    db = EvalDatabase()
    monitor = PerformanceMonitor(db, config)
    analyzer = ReportAnalyzer(db)
    
    if choice == "1":
        # 単一評価サイクル
        await evaluator.run_evaluation_cycle()
        
    elif choice == "2":
        # 継続的モニタリング
        interval = int(console.input("Enter monitoring interval (minutes): ") or "30")
        await evaluator.start_continuous_monitoring(interval)
        
    elif choice == "3":
        # パフォーマンスレポート生成
        days = int(console.input("Report period (days): ") or "7")
        summary = analyzer.generate_executive_summary(days)
        console.print(summary)
        
        # ファイルに保存
        with open(f"executive_summary_{datetime.now().strftime('%Y%m%d')}.md", 'w') as f:
            f.write(summary)
        console.print("[green]Summary saved to file[/green]")
        
    elif choice == "4":
        # 失敗パターン分析
        days = int(console.input("Analysis period (days): ") or "7")
        patterns = analyzer.analyze_failure_patterns(days)
        
        if patterns:
            console.print("\n[bold]Failure Pattern Analysis[/bold]")
            console.print(json.dumps(patterns, indent=2, default=str))
        
    elif choice == "5":
        # トレンドグラフ生成
        monitor.plot_trends()
    
    else:
        console.print("[red]Invalid choice[/red]")


if __name__ == "__main__":
    asyncio.run(main())