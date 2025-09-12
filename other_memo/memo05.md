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