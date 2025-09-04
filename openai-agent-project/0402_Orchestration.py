#!/usr/bin/env python3
"""
OpenAI Agents SDK Orchestration サンプルプログラム
LLMによるOrchestrationとコードによるOrchestrationの実装例
"""

import os
import asyncio
from typing import List, Dict, Any
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel

# OpenAI Agents SDKのインポート
from agents import (
    Agent,
    Runner,
    set_tracing_disabled,
)


# ========== データモデル定義 ==========

class TaskCategory(str, Enum):
    """タスクカテゴリの定義"""
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    TECHNICAL = "technical"


class TaskClassification(BaseModel):
    """タスク分類結果のモデル"""
    category: TaskCategory
    complexity: str  # "low", "medium", "high"
    reasoning: str
    confidence: float


class ResearchResult(BaseModel):
    """リサーチ結果のモデル"""
    summary: str
    key_points: List[str]
    sources_needed: List[str]
    quality_score: float


class WritingResult(BaseModel):
    """ライティング結果のモデル"""
    content: str
    structure_quality: str
    readability_score: float
    word_count: int


class AnalysisResult(BaseModel):
    """分析結果のモデル"""
    findings: List[str]
    recommendations: List[str]
    confidence_level: str
    data_quality: str


class QualityAssessment(BaseModel):
    """品質評価のモデル"""
    overall_score: float
    strengths: List[str]
    improvements: List[str]
    meets_requirements: bool


# ========== 専門エージェント定義 ==========

# タスク分類エージェント（LLM Orchestrationの入り口）
task_classifier_agent = Agent(
    name="Task Classifier",
    instructions="""
    あなたはタスク分類の専門家です。
    ユーザーからのリクエストを分析し、最適なカテゴリに分類してください。
    
    分類カテゴリ：
    - research: 調査・リサーチが必要なタスク
    - writing: 文書作成・ライティングタスク  
    - analysis: データ分析・評価タスク
    - creative: クリエイティブな作品制作
    - technical: 技術的な問題解決
    
    複雑度は以下で判定：
    - low: 簡単な作業（15分以内）
    - medium: 中程度の作業（1時間以内）
    - high: 複雑な作業（数時間必要）
    
    confidence は 0.0-1.0 で設定してください。
    """,
    output_type=TaskClassification,
)

# リサーチ専門エージェント
research_agent = Agent(
    name="Research Specialist",
    instructions="""
    あなたは調査・リサーチの専門家です。
    与えられたトピックについて体系的に調査し、
    要点を整理して分かりやすくまとめてください。
    
    以下の要素を含めてください：
    - 重要なポイントの箇条書き
    - 必要な情報源の特定
    - 調査の品質評価（1-10スケール）
    """,
    output_type=ResearchResult,
)

# ライティング専門エージェント
writing_agent = Agent(
    name="Writing Specialist", 
    instructions="""
    あなたは文書作成の専門家です。
    与えられた情報やトピックについて、
    読みやすく構造化された文書を作成してください。
    
    以下を考慮してください：
    - 明確な構造と論理的な流れ
    - 読みやすさと理解しやすさ
    - 適切な文章の長さと表現
    - 文字数のカウント
    """,
    output_type=WritingResult,
)

# 分析専門エージェント
analysis_agent = Agent(
    name="Analysis Specialist",
    instructions="""
    あなたはデータ分析・評価の専門家です。
    与えられた情報や問題について詳細に分析し、
    実用的な洞察と推奨事項を提供してください。
    
    以下を含めてください：
    - 主要な発見事項
    - 具体的な推奨事項
    - 分析の信頼性レベル
    - データ品質の評価
    """,
    output_type=AnalysisResult,
)

# 品質評価エージェント
quality_evaluator_agent = Agent(
    name="Quality Evaluator",
    instructions="""
    あなたは品質評価の専門家です。
    他のエージェントの作業結果を評価し、
    改善点や強みを特定してください。
    
    以下の観点で評価：
    - 全体的な品質（1-10スケール）
    - 強みと改善点の特定
    - 要求を満たしているかの判定
    """,
    output_type=QualityAssessment,
)

# オーケストレーション統合エージェント（LLM Orchestration）
orchestrator_agent = Agent(
    name="Master Orchestrator",
    instructions="""
    あなたはタスク管理とエージェント統合の専門家です。
    複数のエージェントの結果を統合し、最終的な成果物を作成してください。
    
    以下のエージェントと連携できます：
    - Research Specialist: 調査とリサーチ
    - Writing Specialist: 文書作成とライティング
    - Analysis Specialist: データ分析と評価
    - Quality Evaluator: 品質評価と改善提案
    
    タスクの複雑さに応じて適切なエージェントを選択し、
    必要に応じて複数のエージェントを組み合わせてください。
    """,
    handoffs=[research_agent, writing_agent, analysis_agent, quality_evaluator_agent],
)


# ========== Orchestration関数定義 ==========

class OrchestrationEngine:
    """Orchestrationエンジンクラス"""
    
    def __init__(self):
        self.execution_log = []
    
    async def llm_orchestration(self, user_request: str) -> Dict[str, Any]:
        """
        LLMによるOrchestration
        LLMの判断に基づいて動的にエージェントを選択・実行
        """
        print("🧠 LLMによるOrchestration を開始...")
        self.execution_log.append("=== LLM Orchestration Start ===")
        
        try:
            # LLMの判断でタスクを処理（オーケストレータに委任）
            print("   オーケストレータエージェントにタスクを委任中...")
            result = await Runner.run(orchestrator_agent, user_request)
            
            # モデル出力がPydanticモデルの場合のスライス安全化
            _final_output_preview = str(result.final_output)
            self.execution_log.append(
                f"LLM Orchestration completed: {_final_output_preview[:100]}..."
            )
            
            return {
                "method": "LLM Orchestration",
                "result": result.final_output,
                "success": True,
                "agent_used": "Master Orchestrator (with handoffs)"
            }
            
        except Exception as e:
            error_msg = f"LLM Orchestration error: {e}"
            self.execution_log.append(error_msg)
            return {
                "method": "LLM Orchestration", 
                "error": str(e),
                "success": False
            }
    
    async def code_orchestration(self, user_request: str) -> Dict[str, Any]:
        """
        コードによるOrchestration  
        予め定義されたロジックに基づいてエージェントを制御
        """
        print("⚙️  コードによるOrchestration を開始...")
        self.execution_log.append("=== Code Orchestration Start ===")
        
        results = {}
        
        try:
            # ステップ1: タスク分類
            print("   ステップ1: タスクを分類中...")
            classification_result = await Runner.run(task_classifier_agent, user_request)
            classification = classification_result.final_output
            
            results["classification"] = classification
            self.execution_log.append(f"Task classified as: {classification.category}")
            
            # ステップ2: 分類に基づいてエージェントを選択・実行
            print(f"   ステップ2: {classification.category}専門エージェントを実行中...")
            
            if classification.category == TaskCategory.RESEARCH:
                specialist_result = await Runner.run(research_agent, user_request)
            elif classification.category == TaskCategory.WRITING:
                specialist_result = await Runner.run(writing_agent, user_request)
            elif classification.category == TaskCategory.ANALYSIS:
                specialist_result = await Runner.run(analysis_agent, user_request)
            else:
                # デフォルトはライティングエージェント
                specialist_result = await Runner.run(writing_agent, user_request)
            
            results["specialist_output"] = specialist_result.final_output
            
            # ステップ3: 品質評価（複雑度がmedium以上の場合）
            if classification.complexity in ["medium", "high"]:
                print("   ステップ3: 品質評価を実行中...")
                
                # 専門エージェントの出力を文字列として評価エージェントに渡す
                output_text = str(specialist_result.final_output)
                evaluation_result = await Runner.run(
                    quality_evaluator_agent, 
                    f"以下の作業結果を評価してください：\n\n{output_text}"
                )
                results["quality_assessment"] = evaluation_result.final_output
                self.execution_log.append("Quality evaluation completed")
            else:
                print("   品質評価をスキップ（低複雑度のため）")
                results["quality_assessment"] = None
            
            # ステップ4: 改善ループ（品質スコアが低い場合）
            if (results.get("quality_assessment") and 
                results["quality_assessment"].overall_score < 7.0):
                
                print("   ステップ4: 品質改善を実行中...")
                improvement_request = f"""
                以下の作業を改善してください：
                
                元の要求: {user_request}
                
                改善点: {', '.join(results["quality_assessment"].improvements)}
                """
                
                if classification.category == TaskCategory.RESEARCH:
                    improved_result = await Runner.run(research_agent, improvement_request)
                elif classification.category == TaskCategory.WRITING:
                    improved_result = await Runner.run(writing_agent, improvement_request)
                elif classification.category == TaskCategory.ANALYSIS:
                    improved_result = await Runner.run(analysis_agent, improvement_request)
                else:
                    improved_result = await Runner.run(writing_agent, improvement_request)
                
                results["improved_output"] = improved_result.final_output
                self.execution_log.append("Improvement iteration completed")
            
            self.execution_log.append("Code Orchestration completed successfully")
            
            return {
                "method": "Code Orchestration",
                "results": results,
                "success": True,
                "steps_completed": len([k for k in results.keys() if results[k] is not None])
            }
            
        except Exception as e:
            error_msg = f"Code Orchestration error: {e}"
            self.execution_log.append(error_msg)
            return {
                "method": "Code Orchestration",
                "error": str(e),
                "success": False,
                "partial_results": results
            }
    
    async def parallel_orchestration(self, user_request: str) -> Dict[str, Any]:
        """
        並列Orchestration
        複数のエージェントを同時実行して結果を統合
        """
        print("⚡ 並列Orchestration を開始...")
        self.execution_log.append("=== Parallel Orchestration Start ===")
        
        try:
            # 複数のエージェントを並列実行
            print("   複数のエージェントを並列実行中...")
            
            # asyncio.gatherで並列実行
            research_task = Runner.run(research_agent, user_request)
            writing_task = Runner.run(writing_agent, user_request)
            analysis_task = Runner.run(analysis_agent, user_request)
            
            research_result, writing_result, analysis_result = await asyncio.gather(
                research_task, writing_task, analysis_task,
                return_exceptions=True
            )
            
            results = {}
            
            # 結果の処理（例外がある場合も含む）
            if not isinstance(research_result, Exception):
                results["research"] = research_result.final_output
            if not isinstance(writing_result, Exception):
                results["writing"] = writing_result.final_output  
            if not isinstance(analysis_result, Exception):
                results["analysis"] = analysis_result.final_output
            
            self.execution_log.append(f"Parallel execution completed: {len(results)} agents succeeded")
            
            return {
                "method": "Parallel Orchestration",
                "results": results,
                "success": True,
                "agents_executed": len(results)
            }
            
        except Exception as e:
            error_msg = f"Parallel Orchestration error: {e}"
            self.execution_log.append(error_msg)
            return {
                "method": "Parallel Orchestration",
                "error": str(e),
                "success": False
            }
    
    def get_execution_log(self) -> List[str]:
        """実行ログを取得"""
        return self.execution_log.copy()
    
    def clear_log(self):
        """実行ログをクリア"""
        self.execution_log.clear()


# ========== ユーティリティ関数 ==========

def load_environment():
    """環境変数を読み込み、必要なチェックを行う"""
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEYが設定されていません。\n"
            ".envファイルに以下の形式で設定してください：\n"
            "OPENAI_API_KEY=your_api_key_here"
        )
    
    print("✅ 環境変数の読み込みが完了しました")
    return api_key


async def demonstrate_orchestrations():
    """様々なOrchestrationパターンのデモンストレーション"""
    
    # Orchestrationエンジンの初期化
    engine = OrchestrationEngine()
    
    # テストケース
    test_cases = [
        {
            "name": "技術ブログ記事の作成",
            "request": "Pythonの非同期プログラミングについて、初心者向けの技術ブログ記事を作成してください。基本概念、実例、ベストプラクティスを含めてください。",
        },
        {
            "name": "市場分析レポート",
            "request": "AI技術の市場動向を分析し、今後5年間の予測と投資機会について報告書を作成してください。",
        },
        {
            "name": "簡単な創作活動",
            "request": "春をテーマにした短い詩を作成してください。",
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"🎯 テストケース {i}: {test_case['name']}")
        print(f"リクエスト: {test_case['request']}")
        print("="*80)
        
        # 各Orchestrationパターンを順番に実行
        orchestration_methods = [
            ("LLM Orchestration", engine.llm_orchestration),
            ("Code Orchestration", engine.code_orchestration), 
            ("Parallel Orchestration", engine.parallel_orchestration),
        ]
        
        for method_name, method_func in orchestration_methods:
            print(f"\n--- {method_name} ---")
            try:
                result = await method_func(test_case["request"])
                
                if result["success"]:
                    print(f"✅ {method_name} 成功")
                    
                    if "result" in result:
                        # LLM Orchestrationの結果表示
                        print(f"結果: {str(result['result'])[:200]}...")
                    elif "results" in result:
                        # Code/Parallel Orchestrationの結果表示
                        print(f"実行ステップ数: {result.get('steps_completed', len(result['results']))}")
                        for key, value in result["results"].items():
                            if value:
                                print(f"  {key}: {str(value)[:150]}...")
                else:
                    print(f"❌ {method_name} 失敗: {result.get('error', '不明なエラー')}")
                    
            except Exception as e:
                print(f"❌ {method_name} で予期しないエラー: {e}")
        
        # 実行ログの表示
        print(f"\n📋 実行ログ:")
        for log_entry in engine.get_execution_log()[-10:]:  # 最新10件のみ表示
            print(f"   {log_entry}")
        
        engine.clear_log()


async def main():
    """メイン関数"""
    print("🚀 OpenAI Agents SDK Orchestration サンプルプログラム開始")
    print("="*80)
    
    try:
        # 環境変数の読み込みとチェック
        load_environment()
        
        # トレーシングを無効化
        set_tracing_disabled(True)
        print("✅ トレーシングを無効化しました")
        
        # Orchestrationのデモンストレーション実行
        await demonstrate_orchestrations()
        
        print(f"\n{'='*80}")
        print("🎉 全てのOrchestrationテストが完了しました")
        print("\nOrchestrationパターンの比較:")
        print("• LLM Orchestration: 柔軟性が高く、複雑な判断に適している")
        print("• Code Orchestration: 予測可能で効率的、構造化されたワークフローに適している") 
        print("• Parallel Orchestration: 速度重視、独立したタスクの並列処理に適している")
        
    except ValueError as e:
        print(f"❌ 環境設定エラー: {e}")
        return 1
        
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        print(f"エラータイプ: {type(e).__name__}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)