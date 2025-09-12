ユーザーがアップロードしたresearch-bot.txtは、OpenAI Agent SDKを使ったリサーチボットのコードベースのようです。これは以下のような構成になっています：

1. **PlannerAgent**: クエリに対してWeb検索プランを作成
2. **SearchAgent**: Web検索を実行して結果を要約
3. **WriterAgent**: 検索結果を基にレポートを作成
4. **ResearchManager**: 全体のワークフローを管理

このリサーチボットに対する評価スクリプトを作成する必要があります。提供されたURLを参考に、OpenAIのEvals APIを使った評価スクリプトを作成します。

評価すべき点：
1. PlannerAgentが適切な検索プランを生成できているか
2. SearchAgentが検索結果を適切に要約できているか
3. WriterAgentが質の高いレポートを生成できているか
4. 全体のワークフローがエラーなく動作するか
5. レスポンス時間
6. コスト効率

OpenAIのEvals APIやsimple-evalsを参考に、適切な評価スクリプトを作成します。

アップロードされたresearch-bot.txtを分析しました。これはOpenAI Agent SDKを使った研究アシスタントボットで、3つのエージェント（Planner、Search、Writer）が協調して動作する構成になっています。

以下、このリサーチボットに最適な評価用スクリプトを作成します：

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

次に、評価スクリプトの設定ファイルと、より高度な評価機能を追加したファイルも作成します。

次に、評価設定ファイルと追加の評価ユーティリティを作成します：

"""
eval_config.py - 評価設定とユーティリティ
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import yaml
import json
from enum import Enum


# ==================== 評価タイプの定義 ====================

class EvalType(str, Enum):
    """評価タイプの列挙型"""
    FUNCTIONALITY = "functionality"  # 機能性評価
    QUALITY = "quality"              # 品質評価
    PERFORMANCE = "performance"      # パフォーマンス評価
    COST = "cost"                   # コスト評価
    REGRESSION = "regression"        # 回帰テスト


# ==================== 評価基準の定義 ====================

class PlannerCriteria(BaseModel):
    """PlannerAgent評価基準"""
    min_searches: int = Field(default=3, description="最小検索数")
    max_searches: int = Field(default=20, description="最大検索数")
    relevance_threshold: float = Field(default=0.7, description="関連性閾値")
    diversity_threshold: float = Field(default=0.6, description="多様性閾値")
    
    class Config:
        schema_extra = {
            "example": {
                "min_searches": 5,
                "max_searches": 15,
                "relevance_threshold": 0.75,
                "diversity_threshold": 0.65
            }
        }


class SearchCriteria(BaseModel):
    """SearchAgent評価基準"""
    max_summary_length: int = Field(default=300, description="要約の最大語数")
    min_summary_length: int = Field(default=50, description="要約の最小語数")
    accuracy_threshold: float = Field(default=0.7, description="正確性閾値")
    conciseness_threshold: float = Field(default=0.8, description="簡潔性閾値")


class WriterCriteria(BaseModel):
    """WriterAgent評価基準"""
    min_report_length: int = Field(default=1000, description="レポート最小語数")
    max_report_length: int = Field(default=5000, description="レポート最大語数")
    structure_threshold: float = Field(default=0.7, description="構造化閾値")
    completeness_threshold: float = Field(default=0.8, description="完全性閾値")
    min_follow_up_questions: int = Field(default=3, description="最小フォローアップ質問数")


class PerformanceCriteria(BaseModel):
    """パフォーマンス評価基準"""
    max_latency_seconds: float = Field(default=60.0, description="最大レイテンシ（秒）")
    max_cost_usd: float = Field(default=0.5, description="最大コスト（USD）")
    timeout_seconds: float = Field(default=120.0, description="タイムアウト（秒）")


# ==================== 評価設定 ====================

class EvalConfig(BaseModel):
    """評価設定の総合クラス"""
    
    name: str = Field(default="ResearchBot Evaluation", description="評価名")
    description: Optional[str] = Field(default=None, description="評価の説明")
    
    # 評価タイプ
    eval_types: List[EvalType] = Field(
        default=[EvalType.FUNCTIONALITY, EvalType.QUALITY],
        description="実行する評価タイプ"
    )
    
    # 各エージェントの評価基準
    planner_criteria: PlannerCriteria = Field(default_factory=PlannerCriteria)
    search_criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    writer_criteria: WriterCriteria = Field(default_factory=WriterCriteria)
    performance_criteria: PerformanceCriteria = Field(default_factory=PerformanceCriteria)
    
    # モデル設定
    eval_model: str = Field(default="gpt-4o-mini", description="評価用モデル")
    temperature: float = Field(default=0.0, description="評価時の温度パラメータ")
    
    # 出力設定
    output_dir: str = Field(default="./eval_results", description="結果出力ディレクトリ")
    save_intermediate_results: bool = Field(default=True, description="中間結果を保存")
    generate_report: bool = Field(default=True, description="評価レポートを生成")
    
    @classmethod
    def from_yaml(cls, filepath: str) -> "EvalConfig":
        """YAMLファイルから設定を読み込む"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, filepath: str) -> "EvalConfig":
        """JSONファイルから設定を読み込む"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_yaml(self, filepath: str) -> None:
        """設定をYAMLファイルに保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.dict(), f, allow_unicode=True, default_flow_style=False)
    
    def to_json(self, filepath: str) -> None:
        """設定をJSONファイルに保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.dict(), f, ensure_ascii=False, indent=2)


# ==================== 評価テストケース ====================

class TestCase(BaseModel):
    """個別のテストケース"""
    
    id: str = Field(description="テストケースID")
    query: str = Field(description="入力クエリ")
    category: Optional[str] = Field(default=None, description="カテゴリ")
    tags: List[str] = Field(default_factory=list, description="タグ")
    
    # 期待される出力
    expected_topics: Optional[List[str]] = Field(
        default=None,
        description="レポートに含まれるべきトピック"
    )
    expected_min_length: Optional[int] = Field(
        default=None,
        description="期待される最小文字数"
    )
    expected_search_queries: Optional[List[str]] = Field(
        default=None,
        description="期待される検索クエリ"
    )
    
    # 評価の重み
    weight: float = Field(default=1.0, description="評価時の重み")
    
    # 特別な評価設定
    custom_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="カスタム評価基準"
    )


class TestSuite(BaseModel):
    """テストスイート"""
    
    name: str = Field(description="テストスイート名")
    description: Optional[str] = Field(default=None, description="説明")
    test_cases: List[TestCase] = Field(description="テストケースのリスト")
    
    # 実行設定
    parallel_execution: bool = Field(default=False, description="並列実行")
    max_parallel: int = Field(default=3, description="最大並列数")
    retry_on_failure: bool = Field(default=True, description="失敗時の再試行")
    max_retries: int = Field(default=2, description="最大再試行回数")
    
    @classmethod
    def from_file(cls, filepath: str) -> "TestSuite":
        """ファイルからテストスイートを読み込む"""
        if filepath.endswith('.yaml') or filepath.endswith('.yml'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        return cls(**data)
    
    def to_file(self, filepath: str) -> None:
        """テストスイートをファイルに保存"""
        if filepath.endswith('.yaml') or filepath.endswith('.yml'):
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(self.dict(), f, allow_unicode=True, default_flow_style=False)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.dict(), f, ensure_ascii=False, indent=2)


# ==================== 評価メトリクス計算 ====================

class MetricsCalculator:
    """評価メトリクスを計算するユーティリティクラス"""
    
    @staticmethod
    def calculate_weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """重み付きスコアを計算"""
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(
            scores.get(key, 0) * weight 
            for key, weight in weights.items()
        )
        return weighted_sum / total_weight
    
    @staticmethod
    def calculate_success_rate(results: List[Dict[str, Any]]) -> float:
        """成功率を計算"""
        if not results:
            return 0.0
        
        successful = sum(1 for r in results if r.get("success", False))
        return successful / len(results)
    
    @staticmethod
    def calculate_avg_latency(results: List[Dict[str, Any]]) -> float:
        """平均レイテンシを計算"""
        latencies = [r.get("latency", 0) for r in results if "latency" in r]
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)
    
    @staticmethod
    def calculate_cost_efficiency(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """コスト効率を計算"""
        total_cost = sum(r.get("cost", 0) for r in results)
        successful_cost = sum(
            r.get("cost", 0) for r in results 
            if r.get("success", False)
        )
        
        return {
            "total_cost": total_cost,
            "successful_cost": successful_cost,
            "cost_per_query": total_cost / len(results) if results else 0,
            "cost_efficiency": successful_cost / total_cost if total_cost > 0 else 0
        }


# ==================== サンプル設定生成 ====================

def create_sample_config() -> EvalConfig:
    """サンプル評価設定を生成"""
    return EvalConfig(
        name="ResearchBot Standard Evaluation",
        description="標準的な評価設定",
        eval_types=[EvalType.FUNCTIONALITY, EvalType.QUALITY, EvalType.PERFORMANCE],
        planner_criteria=PlannerCriteria(
            min_searches=5,
            max_searches=15,
            relevance_threshold=0.75,
            diversity_threshold=0.65
        ),
        search_criteria=SearchCriteria(
            max_summary_length=250,
            min_summary_length=100,
            accuracy_threshold=0.75,
            conciseness_threshold=0.80
        ),
        writer_criteria=WriterCriteria(
            min_report_length=1000,
            max_report_length=3000,
            structure_threshold=0.75,
            completeness_threshold=0.80,
            min_follow_up_questions=3
        ),
        performance_criteria=PerformanceCriteria(
            max_latency_seconds=45.0,
            max_cost_usd=0.3,
            timeout_seconds=90.0
        ),
        eval_model="gpt-4o-mini",
        temperature=0.0,
        output_dir="./eval_results",
        save_intermediate_results=True,
        generate_report=True
    )


def create_sample_test_suite() -> TestSuite:
    """サンプルテストスイートを生成"""
    return TestSuite(
        name="ResearchBot Comprehensive Test Suite",
        description="リサーチボットの包括的なテストスイート",
        test_cases=[
            TestCase(
                id="TC001",
                query="人工知能の倫理的課題と規制の現状",
                category="AI Ethics",
                tags=["AI", "ethics", "regulation"],
                expected_topics=["プライバシー", "バイアス", "透明性", "規制"],
                expected_min_length=1200,
                weight=1.0
            ),
            TestCase(
                id="TC002",
                query="カーボンニュートラル達成に向けた各国の取り組み",
                category="Climate",
                tags=["climate", "carbon", "sustainability"],
                expected_topics=["再生可能エネルギー", "炭素税", "排出削減目標"],
                expected_min_length=1500,
                weight=1.5
            ),
            TestCase(
                id="TC003",
                query="最新のサイバーセキュリティ脅威と対策",
                category="Security",
                tags=["cybersecurity", "threats", "defense"],
                expected_topics=["ランサムウェア", "ゼロトラスト", "AI活用"],
                expected_min_length=1000,
                weight=1.2
            ),
            TestCase(
                id="TC004",
                query="メタバースビジネスの現状と将来性",
                category="Technology",
                tags=["metaverse", "VR", "business"],
                expected_topics=["VR/AR", "NFT", "仮想経済"],
                expected_min_length=1300,
                weight=1.0
            ),
            TestCase(
                id="TC005",
                query="少子高齢化社会における医療システムの課題",
                category="Healthcare",
                tags=["healthcare", "aging", "society"],
                expected_topics=["在宅医療", "デジタルヘルス", "医療費"],
                expected_min_length=1400,
                weight=1.3
            )
        ],
        parallel_execution=True,
        max_parallel=3,
        retry_on_failure=True,
        max_retries=2
    )


# ==================== 評価レポート生成 ====================

class EvalReportGenerator:
    """評価レポートを生成するクラス"""
    
    @staticmethod
    def generate_markdown_report(
        config: EvalConfig,
        results: List[Dict[str, Any]],
        test_suite: Optional[TestSuite] = None
    ) -> str:
        """Markdown形式の評価レポートを生成"""
        
        calculator = MetricsCalculator()
        
        report = f"""# {config.name} - Evaluation Report

## 概要
- **実行日時**: {results[0].get('timestamp', 'N/A')}
- **評価モデル**: {config.eval_model}
- **テストケース数**: {len(results)}

## 全体メトリクス

### 成功率
- **全体成功率**: {calculator.calculate_success_rate(results):.1%}

### パフォーマンス
- **平均レイテンシ**: {calculator.calculate_avg_latency(results):.2f}秒
- **最大レイテンシ閾値**: {config.performance_criteria.max_latency_seconds}秒

### コスト効率
"""
        
        cost_metrics = calculator.calculate_cost_efficiency(results)
        for key, value in cost_metrics.items():
            if "cost" in key:
                report += f"- **{key.replace('_', ' ').title()}**: ${value:.4f}\n"
            else:
                report += f"- **{key.replace('_', ' ').title()}**: {value:.2%}\n"
        
        report += """
## エージェント別評価

### PlannerAgent
"""
        planner_scores = [r.get("planner_quality_score", 0) for r in results]
        avg_planner = sum(planner_scores) / len(planner_scores) if planner_scores else 0
        report += f"- **平均品質スコア**: {avg_planner:.2f}/1.0\n"
        report += f"- **閾値**: 関連性 {config.planner_criteria.relevance_threshold}, 多様性 {config.planner_criteria.diversity_threshold}\n"
        
        report += """
### SearchAgent
"""
        search_scores = [r.get("search_quality_score", 0) for r in results]
        avg_search = sum(search_scores) / len(search_scores) if search_scores else 0
        report += f"- **平均品質スコア**: {avg_search:.2f}/1.0\n"
        report += f"- **要約長さ範囲**: {config.search_criteria.min_summary_length}-{config.search_criteria.max_summary_length}語\n"
        
        report += """
### WriterAgent
"""
        writer_scores = [r.get("report_quality_score", 0) for r in results]
        avg_writer = sum(writer_scores) / len(writer_scores) if writer_scores else 0
        report += f"- **平均品質スコア**: {avg_writer:.2f}/1.0\n"
        report += f"- **レポート長さ範囲**: {config.writer_criteria.min_report_length}-{config.writer_criteria.max_report_length}語\n"
        
        if test_suite:
            report += """
## テストケース詳細

| ID | クエリ | 成功 | レイテンシ | 総合スコア |
|---|---|---|---|---|
"""
            for result, test_case in zip(results, test_suite.test_cases):
                success = "✓" if result.get("success") else "✗"
                latency = result.get("latency", 0)
                total_score = (
                    result.get("planner_quality_score", 0) +
                    result.get("search_quality_score", 0) +
                    result.get("report_quality_score", 0)
                ) / 3
                
                query_short = test_case.query[:30] + "..." if len(test_case.query) > 30 else test_case.query
                report += f"| {test_case.id} | {query_short} | {success} | {latency:.1f}s | {total_score:.2f} |\n"
        
        report += """
## 推奨事項

"""
        # スコアに基づく推奨事項
        if avg_planner < config.planner_criteria.relevance_threshold:
            report += "- **PlannerAgent**: 検索クエリの関連性を改善する必要があります\n"
        
        if avg_search < config.search_criteria.accuracy_threshold:
            report += "- **SearchAgent**: 要約の正確性を向上させる必要があります\n"
        
        if avg_writer < config.writer_criteria.completeness_threshold:
            report += "- **WriterAgent**: レポートの完全性を改善する必要があります\n"
        
        avg_latency = calculator.calculate_avg_latency(results)
        if avg_latency > config.performance_criteria.max_latency_seconds:
            report += f"- **パフォーマンス**: レイテンシが目標値を超えています（現在: {avg_latency:.1f}s、目標: {config.performance_criteria.max_latency_seconds}s）\n"
        
        return report


# ==================== メイン実行例 ====================

if __name__ == "__main__":
    # サンプル設定の生成と保存
    config = create_sample_config()
    config.to_yaml("eval_config.yaml")
    config.to_json("eval_config.json")
    print("Sample configuration saved to eval_config.yaml and eval_config.json")
    
    # サンプルテストスイートの生成と保存
    test_suite = create_sample_test_suite()
    test_suite.to_file("test_suite.yaml")
    test_suite.to_file("test_suite.json")
    print("Sample test suite saved to test_suite.yaml and test_suite.json")
    
    # 設定の表示
    print("\n=== Evaluation Configuration ===")
    print(f"Name: {config.name}")
    print(f"Eval Types: {config.eval_types}")
    print(f"Model: {config.eval_model}")
    print(f"Output Dir: {config.output_dir}")
    
    print("\n=== Test Suite ===")
    print(f"Name: {test_suite.name}")
    print(f"Test Cases: {len(test_suite.test_cases)}")
    for tc in test_suite.test_cases:
        print(f"  - {tc.id}: {tc.query[:50]}...")

最後に、継続的な評価とモニタリングのためのスクリプトも作成します。

最後に、継続的な評価とモニタリングのためのスクリプトを作成します：

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

ユーザーのリサーチボットに対して、包括的な評価スクリプトセットを作成しました。これらのスクリプトは以下の機能を提供します：

1. **基本評価スクリプト（research_bot_eval.py）**
   - 各エージェント（Planner、Search、Writer）の個別評価
   - 品質スコアの算出
   - レイテンシとコストの測定
   - 結果のJSON/CSV形式での保存

2. **評価設定とユーティリティ（eval_config.py）**
   - 評価基準の設定管理
   - テストスイートの定義
   - メトリクス計算ユーティリティ
   - 評価レポート生成

3. **継続的評価とモニタリング（continuous_eval.py）**
   - リアルタイムパフォーマンス監視
   - データベースによる履歴管理
   - アラート機能
   - トレンド分析とグラフ生成
   - エグゼクティブサマリー生成

これらのスクリプトは、OpenAIのEvals APIのベストプラクティスに従って設計されており、リサーチボットの品質を継続的に監視し、改善点を特定するのに役立ちます。

## 評価スクリプトの概要

アップロードされたResearchBotに対して、OpenAI Evals APIのベストプラクティスに基づいた包括的な評価システムを作成しました。3つの主要なコンポーネントで構成されています：

### 📊 作成した評価スクリプト

#### 1. **基本評価スクリプト（research_bot_eval.py）**
- **各エージェントの個別評価**
  - PlannerAgent: 検索プランの関連性、多様性、具体性を評価
  - SearchAgent: 要約の正確性、簡潔性、要点抽出を評価
  - WriterAgent: レポートの完全性、構造、詳細度を評価
- **パフォーマンスメトリクス**: レイテンシ、コスト、成功率を測定
- **結果の保存**: JSON/CSV形式で詳細な評価結果を出力

#### 2. **評価設定管理（eval_config.py）**
- **柔軟な評価基準設定**: YAML/JSON形式での設定管理
- **テストスイート定義**: カテゴリ別、重み付きテストケース
- **メトリクス計算**: 加重平均スコア、成功率、コスト効率
- **レポート生成**: Markdown形式の詳細な評価レポート

#### 3. **継続的モニタリング（continuous_eval.py）**
- **リアルタイム監視**: 定期的な自動評価実行
- **SQLiteデータベース**: 履歴データの永続化
- **アラートシステム**: 閾値超過時の自動通知
- **トレンド分析**: 時系列グラフによる性能推移の可視化
- **エグゼクティブサマリー**: 経営層向けの要約レポート

### 🎯 主な特徴

1. **OpenAI標準準拠**
   - Evals APIのベストプラクティスに従った実装
   - GPT-4oによる品質評価
   - 構造化された評価プロンプト

2. **包括的な評価**
   - 機能性、品質、パフォーマンス、コストの4側面評価
   - エージェント間の協調動作の検証
   - エンドツーエンドのワークフロー評価

3. **自動化とスケーラビリティ**
   - 並列実行による効率的な評価
   - 再試行メカニズム
   - カスタマイズ可能な評価間隔

4. **実用的な洞察**
   - 失敗パターンの自動分析
   - パフォーマンス劣化の早期検出
   - 具体的な改善提案の生成

### 🚀 使用方法

```bash
# 基本的な評価実行
python research_bot_eval.py

# 継続的モニタリング開始
python continuous_eval.py
# オプション2を選択して30分間隔でモニタリング

# カスタム設定での評価
# 1. eval_config.yamlを編集
# 2. test_suite.yamlにテストケースを追加
# 3. 評価を実行
```

### 📈 評価指標

各エージェントは0-1のスコアで評価され、以下の基準が適用されます：

- **PlannerAgent**: 関連性(30%)、多様性(20%)、具体性(20%)、検索数(20%)、明確性(10%)
- **SearchAgent**: 正確性(30%)、関連性(30%)、簡潔性(20%)、要点抽出(20%)
- **WriterAgent**: 回答度(30%)、構造(20%)、詳細度(20%)、要約(15%)、フォローアップ(15%)

これらのスクリプトにより、ResearchBotの品質を継続的に監視し、データドリブンな改善を実現できます。