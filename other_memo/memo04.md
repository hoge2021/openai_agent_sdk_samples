"""
ResearchBot Evaluation Script
OpenAI Evals APIを使用したリサーチボットの評価スクリプト
"""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import traceback

from openai import AsyncOpenAI
from pydantic import BaseModel
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import research bot components
from agents import Runner, planner_agent, search_agent, writer_agent
from agents.planner_agent import WebSearchPlan
from agents.writer_agent import ReportData
from manager import ResearchManager


# ==================== 評価用データクラス ====================

@dataclass
class EvalMetrics:
    """評価メトリクスを格納するデータクラス"""
    query: str
    success: bool
    latency: float
    total_cost: float
    planner_quality_score: float
    search_quality_score: float
    report_quality_score: float
    report_length: int
    num_searches: int
    error_message: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class EvalDataset(BaseModel):
    """評価用データセット"""
    queries: List[Dict[str, Any]]
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "EvalDataset":
        """JSONファイルからデータセットを読み込む"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


# ==================== 評価器クラス ====================

class ResearchBotEvaluator:
    """リサーチボットの評価を行うクラス"""
    
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        self.client = openai_client or AsyncOpenAI()
        self.console = Console()
        self.results: List[EvalMetrics] = []
        
    async def evaluate_planner(
        self, 
        query: str, 
        search_plan: WebSearchPlan
    ) -> Tuple[float, Dict[str, Any]]:
        """PlannerAgentの出力を評価"""
        
        eval_prompt = f"""
        以下の検索プランの質を評価してください：
        
        元のクエリ: {query}
        
        生成された検索プラン:
        {json.dumps([{"reason": s.reason, "query": s.query} for s in search_plan.searches], ensure_ascii=False, indent=2)}
        
        以下の基準で0-1のスコアと詳細な評価を返してください：
        1. クエリとの関連性 (0.3)
        2. 検索語の多様性 (0.2)
        3. 検索語の具体性 (0.2)
        4. 検索数の適切性 (0.2)
        5. 理由の明確性 (0.1)
        
        JSONフォーマットで返答してください：
        {{
            "total_score": 0.0-1.0,
            "relevance": 0.0-1.0,
            "diversity": 0.0-1.0,
            "specificity": 0.0-1.0,
            "search_count": 0.0-1.0,
            "clarity": 0.0-1.0,
            "feedback": "改善点の説明"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation["total_score"], evaluation
            
        except Exception as e:
            self.console.print(f"[red]Planner evaluation error: {e}[/red]")
            return 0.0, {"error": str(e)}
    
    async def evaluate_search_summaries(
        self, 
        query: str,
        search_results: List[str]
    ) -> Tuple[float, Dict[str, Any]]:
        """SearchAgentの要約を評価"""
        
        eval_prompt = f"""
        以下の検索結果要約の質を評価してください：
        
        元のクエリ: {query}
        
        検索結果要約:
        {json.dumps(search_results, ensure_ascii=False, indent=2)}
        
        以下の基準で0-1のスコアと詳細な評価を返してください：
        1. 要約の正確性 (0.3)
        2. 情報の関連性 (0.3)
        3. 簡潔性（300語未満） (0.2)
        4. 要点の抽出 (0.2)
        
        JSONフォーマットで返答してください：
        {{
            "total_score": 0.0-1.0,
            "accuracy": 0.0-1.0,
            "relevance": 0.0-1.0,
            "conciseness": 0.0-1.0,
            "key_points": 0.0-1.0,
            "feedback": "改善点の説明"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation["total_score"], evaluation
            
        except Exception as e:
            self.console.print(f"[red]Search evaluation error: {e}[/red]")
            return 0.0, {"error": str(e)}
    
    async def evaluate_report(
        self,
        query: str,
        report: ReportData
    ) -> Tuple[float, Dict[str, Any]]:
        """WriterAgentのレポートを評価"""
        
        eval_prompt = f"""
        以下のレポートの質を評価してください：
        
        元のクエリ: {query}
        
        レポート要約: {report.short_summary}
        
        レポート本文（一部）: {report.markdown_report[:2000]}...
        
        フォローアップ質問: {json.dumps(report.follow_up_questions, ensure_ascii=False)}
        
        以下の基準で0-1のスコアと詳細な評価を返してください：
        1. クエリへの回答度 (0.3)
        2. 構造と流れ (0.2)
        3. 詳細度（1000語以上目標） (0.2)
        4. 要約の的確性 (0.15)
        5. フォローアップ質問の質 (0.15)
        
        JSONフォーマットで返答してください：
        {{
            "total_score": 0.0-1.0,
            "query_answer": 0.0-1.0,
            "structure": 0.0-1.0,
            "detail": 0.0-1.0,
            "summary": 0.0-1.0,
            "follow_up": 0.0-1.0,
            "feedback": "改善点の説明"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation["total_score"], evaluation
            
        except Exception as e:
            self.console.print(f"[red]Report evaluation error: {e}[/red]")
            return 0.0, {"error": str(e)}
    
    async def run_single_evaluation(
        self,
        query: str,
        expected_output: Optional[Dict[str, Any]] = None
    ) -> EvalMetrics:
        """単一クエリの評価を実行"""
        
        start_time = time.time()
        metrics = EvalMetrics(
            query=query,
            success=False,
            latency=0,
            total_cost=0,
            planner_quality_score=0,
            search_quality_score=0,
            report_quality_score=0,
            report_length=0,
            num_searches=0
        )
        
        try:
            # Research Managerの実行をシミュレート
            # (実際の実装では、各エージェントを個別に実行して評価)
            
            # 1. Planner実行
            self.console.print(f"[cyan]Planning searches for: {query}[/cyan]")
            planner_result = await Runner.run(
                planner_agent,
                f"クエリ: {query}"
            )
            search_plan = planner_result.final_output_as(WebSearchPlan)
            metrics.num_searches = len(search_plan.searches)
            
            # Planner評価
            planner_score, planner_eval = await self.evaluate_planner(query, search_plan)
            metrics.planner_quality_score = planner_score
            
            # 2. Search実行（並列処理）
            self.console.print(f"[cyan]Executing {len(search_plan.searches)} searches[/cyan]")
            search_tasks = []
            for item in search_plan.searches:
                input_text = f"検索ワード: {item.query}\n検索理由: {item.reason}"
                task = Runner.run(search_agent, input_text)
                search_tasks.append(task)
            
            search_results = []
            for task in asyncio.as_completed(search_tasks):
                try:
                    result = await task
                    search_results.append(str(result.final_output))
                except Exception:
                    pass
            
            # Search評価
            if search_results:
                search_score, search_eval = await self.evaluate_search_summaries(query, search_results)
                metrics.search_quality_score = search_score
            
            # 3. Writer実行
            self.console.print(f"[cyan]Writing report[/cyan]")
            writer_input = f"オリジナルクエリ: {query}\n要約された検索結果: {search_results}"
            writer_result = await Runner.run(
                writer_agent,
                writer_input
            )
            report = writer_result.final_output_as(ReportData)
            metrics.report_length = len(report.markdown_report.split())
            
            # Report評価
            report_score, report_eval = await self.evaluate_report(query, report)
            metrics.report_quality_score = report_score
            
            # 成功とレイテンシ
            metrics.success = True
            metrics.latency = time.time() - start_time
            
            # コスト計算（簡易版 - 実際のトークン数に基づく計算が必要）
            metrics.total_cost = self._estimate_cost(metrics.num_searches)
            
            self.console.print(f"[green]✓ Evaluation complete for: {query}[/green]")
            
        except Exception as e:
            metrics.error_message = str(e)
            metrics.latency = time.time() - start_time
            self.console.print(f"[red]✗ Evaluation failed: {e}[/red]")
            traceback.print_exc()
        
        return metrics
    
    def _estimate_cost(self, num_searches: int) -> float:
        """コストの概算（実際のトークン数に基づいて調整が必要）"""
        # 概算値：
        # Planner (GPT-4o): ~$0.01
        # Search x N (GPT-4o-mini): ~$0.002 * N
        # Writer (o3-mini): ~$0.05
        return 0.01 + (0.002 * num_searches) + 0.05
    
    async def run_evaluation_suite(
        self,
        dataset: EvalDataset,
        output_dir: str = "./eval_results"
    ) -> None:
        """評価スイート全体を実行"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        self.console.print("[bold]Starting ResearchBot Evaluation Suite[/bold]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"Evaluating {len(dataset.queries)} queries...",
                total=len(dataset.queries)
            )
            
            for i, query_data in enumerate(dataset.queries):
                query = query_data["query"]
                expected = query_data.get("expected", None)
                
                self.console.print(f"\n[bold]Query {i+1}/{len(dataset.queries)}:[/bold] {query}")
                
                metrics = await self.run_single_evaluation(query, expected)
                self.results.append(metrics)
                
                progress.update(task, advance=1)
        
        # 結果の保存と表示
        self._save_results(output_path)
        self._display_summary()
    
    def _save_results(self, output_dir: Path) -> None:
        """評価結果を保存"""
        
        # JSON形式で保存
        json_path = output_dir / f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(m) for m in self.results],
                f,
                ensure_ascii=False,
                indent=2
            )
        
        # CSV形式で保存
        df = pd.DataFrame([asdict(m) for m in self.results])
        csv_path = output_dir / f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        self.console.print(f"\n[green]Results saved to:[/green]")
        self.console.print(f"  - JSON: {json_path}")
        self.console.print(f"  - CSV: {csv_path}")
    
    def _display_summary(self) -> None:
        """評価結果のサマリーを表示"""
        
        if not self.results:
            return
        
        # 集計
        success_rate = sum(1 for m in self.results if m.success) / len(self.results)
        avg_latency = sum(m.latency for m in self.results) / len(self.results)
        avg_cost = sum(m.total_cost for m in self.results) / len(self.results)
        
        avg_planner_score = sum(m.planner_quality_score for m in self.results) / len(self.results)
        avg_search_score = sum(m.search_quality_score for m in self.results) / len(self.results)
        avg_report_score = sum(m.report_quality_score for m in self.results) / len(self.results)
        
        # テーブル表示
        table = Table(title="Evaluation Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Queries", str(len(self.results)))
        table.add_row("Success Rate", f"{success_rate:.1%}")
        table.add_row("Avg Latency", f"{avg_latency:.2f}s")
        table.add_row("Avg Cost", f"${avg_cost:.4f}")
        table.add_row("Avg Planner Score", f"{avg_planner_score:.2f}")
        table.add_row("Avg Search Score", f"{avg_search_score:.2f}")
        table.add_row("Avg Report Score", f"{avg_report_score:.2f}")
        
        self.console.print("\n")
        self.console.print(table)
        
        # 詳細結果
        detail_table = Table(title="Detailed Results", show_header=True)
        detail_table.add_column("Query", style="cyan", width=40)
        detail_table.add_column("Success", style="green")
        detail_table.add_column("Latency", style="yellow")
        detail_table.add_column("Planner", style="blue")
        detail_table.add_column("Search", style="blue")
        detail_table.add_column("Report", style="blue")
        
        for m in self.results:
            query_short = m.query[:37] + "..." if len(m.query) > 40 else m.query
            detail_table.add_row(
                query_short,
                "✓" if m.success else "✗",
                f"{m.latency:.1f}s",
                f"{m.planner_quality_score:.2f}",
                f"{m.search_quality_score:.2f}",
                f"{m.report_quality_score:.2f}"
            )
        
        self.console.print("\n")
        self.console.print(detail_table)


# ==================== サンプルデータセット ====================

def create_sample_dataset() -> EvalDataset:
    """サンプル評価データセットを作成"""
    
    return EvalDataset(
        queries=[
            {
                "query": "2024年のAI業界の主要なトレンドと今後の展望",
                "expected": {
                    "topics": ["生成AI", "マルチモーダル", "エージェント"],
                    "min_length": 800
                }
            },
            {
                "query": "気候変動対策における再生可能エネルギーの最新技術",
                "expected": {
                    "topics": ["太陽光", "風力", "水素"],
                    "min_length": 1000
                }
            },
            {
                "query": "リモートワークが企業文化に与える影響の分析",
                "expected": {
                    "topics": ["生産性", "コミュニケーション", "ワークライフバランス"],
                    "min_length": 900
                }
            },
            {
                "query": "量子コンピューティングの現状と実用化への課題",
                "expected": {
                    "topics": ["量子ビット", "エラー訂正", "応用分野"],
                    "min_length": 1000
                }
            },
            {
                "query": "世界の食糧安全保障の現状と持続可能な解決策",
                "expected": {
                    "topics": ["農業技術", "食品廃棄", "供給チェーン"],
                    "min_length": 1200
                }
            }
        ]
    )


# ==================== メイン実行 ====================

async def main():
    """メイン実行関数"""
    
    console = Console()
    console.print("[bold blue]ResearchBot Evaluation System[/bold blue]\n")
    
    # データセットの準備
    dataset_choice = console.input(
        "Use [bold]sample[/bold] dataset or load from [bold]file[/bold]? [sample/file]: "
    ).lower()
    
    if dataset_choice == "file":
        filepath = console.input("Enter dataset file path: ")
        try:
            dataset = EvalDataset.load_from_file(filepath)
        except Exception as e:
            console.print(f"[red]Error loading dataset: {e}[/red]")
            console.print("[yellow]Using sample dataset instead[/yellow]")
            dataset = create_sample_dataset()
    else:
        dataset = create_sample_dataset()
        
        # サンプルデータセットを保存
        with open("sample_dataset.json", 'w', encoding='utf-8') as f:
            json.dump(dataset.dict(), f, ensure_ascii=False, indent=2)
        console.print("[green]Sample dataset saved to sample_dataset.json[/green]")
    
    # 評価の実行
    evaluator = ResearchBotEvaluator()
    await evaluator.run_evaluation_suite(dataset)
    
    console.print("\n[bold green]Evaluation complete![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())