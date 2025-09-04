#!/usr/bin/env python3
"""
OpenAI Agents SDK Model サンプルプログラム
モデルの混合とマッチング、LLMプロバイダーの使用方法を実装
"""

import os
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# OpenAI Agents SDKのインポート
from agents import (
    Agent,
    Runner,
    ModelProvider,
    AsyncOpenAI,
    OpenAIResponsesModel,
    OpenAIChatCompletionsModel,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
    set_tracing_export_api_key,
)


# ========== データモデル定義 ==========

class TaskResult(BaseModel):
    """タスク実行結果のモデル"""
    content: str
    model_used: str
    execution_time: float
    token_usage: str
    quality_rating: float


class ModelPerformanceReport(BaseModel):
    """モデルパフォーマンスレポート"""
    model_name: str
    avg_response_time: float
    total_tokens: int
    task_success_rate: float
    cost_estimate: float


# ========== カスタムModelProviderクラス ==========

class CustomModelProvider(ModelProvider):
    """カスタムモデルプロバイダーの実装例"""
    
    def __init__(self):
        # 各モデル名に対応するモデル実装を定義
        self.models = {
            # 高性能モデル（Responses API使用）
            "gpt-4o": OpenAIResponsesModel(
                model="gpt-4o",
                openai_client=AsyncOpenAI()
            ),
            # 標準モデル（Responses API使用） 
            "gpt-4o-mini": OpenAIResponsesModel(
                model="gpt-4o-mini",
                openai_client=AsyncOpenAI()
            ),
            # 軽量モデル（ChatCompletions API使用）
            "gpt-3.5-turbo": OpenAIChatCompletionsModel(
                model="gpt-3.5-turbo", 
                openai_client=AsyncOpenAI()
            ),
            # 推論特化モデル（Responses API対応の近似モデルに置換）
            "o3-mini": OpenAIResponsesModel(
                model="gpt-4o-mini",
                openai_client=AsyncOpenAI()
            ),
        }
    
    def get_model(self, model_name: str):
        """指定されたモデル名に対応するモデル実装を返す"""
        if model_name not in self.models:
            raise ValueError(f"サポートされていないモデル: {model_name}")
        return self.models[model_name]


# ========== エージェント定義（異なるモデルを使用） ==========

class ModelDemonstrationAgents:
    """様々なモデル設定のデモンストレーション用エージェント"""
    
    def __init__(self):
        # 高性能モデルを使用するエージェント（直接モデル指定）
        self.premium_agent = Agent(
            name="Premium Analysis Agent",
            instructions="""
            あなたは高度な分析を行う専門エージェントです。
            複雑な問題に対して詳細で洞察に満ちた分析を提供してください。
            """,
            model=OpenAIResponsesModel(
                model="gpt-4o",
                openai_client=AsyncOpenAI()
            ),
            output_type=TaskResult,
        )
        
        # 標準モデルを使用するエージェント（モデル名指定）
        self.standard_agent = Agent(
            name="Standard Processing Agent", 
            instructions="""
            あなたは一般的なタスクを処理するエージェントです。
            効率的で実用的な回答を提供してください。
            """,
            model="gpt-4o-mini",
            output_type=TaskResult,
        )
        
        # 軽量モデルを使用するエージェント（ChatCompletions API）
        self.lightweight_agent = Agent(
            name="Lightweight Agent",
            instructions="""
            あなたは簡単なタスクを高速で処理するエージェントです。
            簡潔で的確な回答を心がけてください。
            """, 
            model=OpenAIChatCompletionsModel(
                model="gpt-3.5-turbo",
                openai_client=AsyncOpenAI()
            ),
            # ChatCompletions系では構造化出力を使わない
        )
        
        # 推論特化モデルを使用するエージェント（Responses API対応モデルに変更）
        self.reasoning_agent = Agent(
            name="Reasoning Specialist Agent",
            instructions="""
            あなたは論理的推論を得意とする専門エージェントです。
            複雑な論理問題や数学的問題を段階的に解決してください。
            """,
            model=OpenAIResponsesModel(
                model="gpt-4o-mini",
                openai_client=AsyncOpenAI()
            ),
            output_type=TaskResult,
        )
        
        # トリアージエージェント（モデル選択を行う）
        self.triage_agent = Agent(
            name="Model Selection Agent",
            instructions="""
            あなたはタスクの複雑さを判定し、適切なエージェントを選択する専門家です。
            タスクの性質に応じて最適なエージェントにハンドオフしてください。
            """,
            model="gpt-4o-mini",  # トリアージには中間性能のモデルを使用
            handoffs=[
                # ハンドオフ先は後でsetメソッドで設定
            ]
        )
    
    def setup_handoffs(self):
        """ハンドオフ設定（循環参照を避けるため）"""
        self.triage_agent.handoffs = [
            self.premium_agent,
            self.standard_agent, 
            self.lightweight_agent,
            self.reasoning_agent,
        ]


# ========== モデル使用パターンのデモンストレーション ==========

class ModelUsageDemo:
    """モデル使用パターンのデモンストレーション"""
    
    def __init__(self):
        self.agents = ModelDemonstrationAgents()
        self.agents.setup_handoffs()
        self.custom_provider = CustomModelProvider()
        self.performance_data = {}
    
    async def demo_method1_global_client(self):
        """
        方法1: set_default_openai_client を使用したグローバル設定
        """
        print("\n🌐 方法1: グローバルOpenAIクライアント設定")
        print("-" * 50)
        
        try:
            # グローバルクライアントを設定
            global_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                # その他のカスタム設定も可能
                # base_url="https://api.openai.com/v1",
                # timeout=30.0,
            )
            set_default_openai_client(global_client)
            print("✅ グローバルクライアントを設定しました")
            
            # グローバル設定を使用するエージェント
            global_agent = Agent(
                name="Global Client Agent",
                instructions="グローバル設定のクライアントを使用します。",
                model="gpt-4o-mini"
            )
            
            result = await Runner.run(
                global_agent, 
                "グローバルクライアント設定でのテスト実行です。簡潔に応答してください。"
            )
            
            print(f"応答: {result.final_output}")
            return {"method": "Global Client", "success": True, "result": result.final_output}
            
        except Exception as e:
            print(f"❌ グローバルクライアント設定エラー: {e}")
            return {"method": "Global Client", "success": False, "error": str(e)}
    
    async def demo_method2_runner_provider(self):
        """
        方法2: ModelProvider を Runner.run レベルで指定
        """
        print("\n🔧 方法2: Runner.runレベルでのModelProvider指定")
        print("-" * 50)
        
        try:
            # Runner.run に model_provider 引数は無い想定のため、
            # Provider からモデルを取得して一時エージェントを生成して実行
            model_impl = self.custom_provider.get_model("gpt-4o-mini")
            temp_agent = Agent(
                name="Standard Processing Agent (Provider Override)",
                instructions="ModelProvider経由でモデル実装を差し替えて実行します。",
                model=model_impl,
                output_type=TaskResult,
            )

            result = await Runner.run(
                temp_agent,
                "ModelProviderを使用したテスト実行です。"
            )
            
            print(f"✅ ModelProvider実行成功")
            print(f"応答: {result.final_output}")
            return {"method": "Runner ModelProvider", "success": True, "result": result.final_output}
            
        except Exception as e:
            print(f"❌ ModelProvider実行エラー: {e}")
            return {"method": "Runner ModelProvider", "success": False, "error": str(e)}
    
    async def demo_method3_agent_specific(self):
        """
        方法3: Agent.model を使用して特定のAgentにモデルを指定
        """
        print("\n🎯 方法3: エージェント固有のモデル指定")
        print("-" * 50)
        
        test_cases = [
            ("Premium Agent (GPT-4o + Responses API)", self.agents.premium_agent),
            ("Standard Agent (GPT-4o-mini)", self.agents.standard_agent),
            ("Lightweight Agent (GPT-3.5 + ChatCompletions API)", self.agents.lightweight_agent),
            ("Reasoning Agent (gpt-4o-mini)", self.agents.reasoning_agent),
        ]
        
        results = []
        
        for name, agent in test_cases:
            try:
                print(f"\n  🤖 {name} をテスト中...")
                
                import time
                start_time = time.time()
                
                result = await Runner.run(
                    agent,
                    f"{agent.name}として、あなたの専門分野について30文字程度で説明してください。"
                )
                
                execution_time = time.time() - start_time
                
                print(f"     ✅ 実行時間: {execution_time:.2f}秒")
                print(f"     応答: {result.final_output}")
                
                results.append({
                    "agent_name": name,
                    "success": True,
                    "execution_time": execution_time,
                    "result": result.final_output
                })
                
            except Exception as e:
                print(f"     ❌ エラー: {e}")
                results.append({
                    "agent_name": name,
                    "success": False,
                    "error": str(e)
                })
        
        return {"method": "Agent-specific Models", "results": results}
    
    async def demo_model_mixing(self):
        """
        モデルの混合とマッチング: 複雑なタスクでの動的モデル選択
        """
        print("\n🎭 モデル混合・マッチングのデモンストレーション")
        print("-" * 50)
        
        complex_tasks = [
            {
                "task": "人工知能の倫理的課題について論文の概要を作成してください。",
                "expected_agent": "Premium Analysis Agent"
            },
            {
                "task": "今日の天気について教えてください。", 
                "expected_agent": "Lightweight Agent"
            },
            {
                "task": "フィボナッチ数列の10番目の値を計算し、計算過程も示してください。",
                "expected_agent": "Reasoning Specialist Agent"
            }
        ]
        
        results = []
        
        for task_info in complex_tasks:
            try:
                print(f"\n  📝 タスク: {task_info['task']}")
                
                # トリアージエージェントが適切なエージェントを選択
                result = await Runner.run(
                    self.agents.triage_agent,
                    task_info["task"]
                )
                
                print(f"     ✅ 処理完了")
                print(f"     応答: {str(result.final_output)[:100]}...")
                
                results.append({
                    "task": task_info["task"],
                    "success": True,
                    "result": result.final_output
                })
                
            except Exception as e:
                print(f"     ❌ エラー: {e}")
                results.append({
                    "task": task_info["task"], 
                    "success": False,
                    "error": str(e)
                })
        
        return {"method": "Model Mixing", "results": results}
    
    async def demo_api_compatibility(self):
        """
        異なるAPIタイプの互換性テスト
        """
        print("\n🔄 API互換性のデモンストレーション")
        print("-" * 50)
        
        try:
            # Responses API vs ChatCompletions API の比較
            test_query = "APIの違いについて50文字程度で説明してください。"
            
            # Responses API を使用
            responses_agent = Agent(
                name="Responses API Test",
                instructions="Responses APIを使用してテストします。",
                model=OpenAIResponsesModel(
                    model="gpt-4o-mini",
                    openai_client=AsyncOpenAI()
                )
            )
            
            responses_result = await Runner.run(responses_agent, test_query)
            print(f"✅ Responses API結果: {responses_result.final_output}")
            
            # ChatCompletions API を使用
            chat_agent = Agent(
                name="ChatCompletions API Test",
                instructions="ChatCompletions APIを使用してテストします。",
                model=OpenAIChatCompletionsModel(
                    model="gpt-4o-mini",
                    openai_client=AsyncOpenAI()
                )
            )
            
            chat_result = await Runner.run(chat_agent, test_query)
            print(f"✅ ChatCompletions API結果: {chat_result.final_output}")
            
            return {
                "method": "API Compatibility",
                "responses_api": responses_result.final_output,
                "chatcompletions_api": chat_result.final_output,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ API互換性テストエラー: {e}")
            return {"method": "API Compatibility", "success": False, "error": str(e)}
    
    async def handle_common_provider_issues(self):
        """
        他のLLMプロバイダー使用時の一般的な問題への対処
        """
        print("\n⚠️  LLMプロバイダー問題への対処例")
        print("-" * 50)
        
        solutions = []
        
        # 問題1: トレーシングクライアントエラー401
        print("  📋 問題1: トレーシングクライアントエラー401への対処")
        try:
            # 解決策1: トレーシングを無効化
            set_tracing_disabled(True)
            print("     ✅ 解決策1: トレーシングを無効化しました")
            solutions.append("トレーシング無効化")
            
            # 解決策2: トレーシング用APIキーを設定（デモのみ）
            if os.getenv("OPENAI_API_KEY"):
                # 実際の本番環境では専用のAPIキーを使用
                set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
                print("     ✅ 解決策2: トレーシング用APIキーを設定（デモ）")
                solutions.append("トレーシング用APIキー設定")
                
        except Exception as e:
            print(f"     ⚠️ トレーシング設定警告: {e}")
        
        # 問題2: Responses APIサポート不足
        print("\n  📋 問題2: Responses APIサポート不足への対処")
        try:
            # 解決策: ChatCompletions APIを使用
            set_default_openai_api("chat_completions")
            print("     ✅ ChatCompletions APIを使用するように設定しました")
            solutions.append("ChatCompletions API使用")
            
        except Exception as e:
            print(f"     ⚠️ API設定警告: {e}")
        
        # 問題3: 構造化出力サポート不足
        print("\n  📋 問題3: 構造化出力サポート対応")
        try:
            # OpenAI以外のプロバイダーでは構造化出力に制限がある場合の対処
            simple_agent = Agent(
                name="Simple Output Agent",
                instructions="""
                構造化出力をサポートしないプロバイダー向けに、
                シンプルな文字列形式で応答してください。
                """,
                # output_typeを指定しない（プレーンテキスト出力）
            )
            
            result = await Runner.run(
                simple_agent,
                "構造化出力制限の回避テストです。"
            )
            print(f"     ✅ 非構造化出力テスト成功: {result.final_output}")
            solutions.append("非構造化出力使用")
            
        except Exception as e:
            print(f"     ❌ 構造化出力テストエラー: {e}")
        
        return {
            "method": "Provider Issues Handling",
            "solutions_applied": solutions,
            "success": len(solutions) > 0
        }


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


async def main():
    """メイン関数"""
    print("🚀 OpenAI Agents SDK Model サンプルプログラム開始")
    print("=" * 80)
    
    try:
        # 環境変数の読み込みとチェック
        load_environment()
        
        # ModelUsageDemoのインスタンス作成
        demo = ModelUsageDemo()
        
        # 各デモンストレーションを順次実行
        demonstrations = [
            ("グローバルクライアント設定", demo.demo_method1_global_client),
            ("Runner ModelProvider", demo.demo_method2_runner_provider),
            ("エージェント固有モデル", demo.demo_method3_agent_specific),
            ("モデル混合・マッチング", demo.demo_model_mixing),
            ("API互換性テスト", demo.demo_api_compatibility),
            ("プロバイダー問題対処", demo.handle_common_provider_issues),
        ]
        
        results_summary = []
        
        for demo_name, demo_func in demonstrations:
            print(f"\n{'='*80}")
            print(f"🎯 {demo_name} のデモンストレーション")
            print("=" * 80)
            
            try:
                result = await demo_func()
                results_summary.append(result)
                print(f"✅ {demo_name} 完了")
                
            except Exception as e:
                print(f"❌ {demo_name} でエラー: {e}")
                results_summary.append({
                    "method": demo_name,
                    "success": False,
                    "error": str(e)
                })
        
        # 結果サマリーの表示
        print(f"\n{'='*80}")
        print("📊 実行結果サマリー")
        print("=" * 80)
        
        successful_demos = 0
        for result in results_summary:
            if result.get("success", False):
                successful_demos += 1
                print(f"✅ {result.get('method', 'Unknown')}: 成功")
            else:
                print(f"❌ {result.get('method', 'Unknown')}: 失敗 - {result.get('error', '不明')}")
        
        print(f"\n🎉 デモンストレーション完了: {successful_demos}/{len(demonstrations)} 成功")
        
        print(f"\n💡 モデル使用のベストプラクティス:")
        print("• 軽量タスクには高速・低コストモデルを使用")
        print("• 複雑な分析には高性能モデルを使用") 
        print("• 論理推論にはo1シリーズを使用")
        print("• プロバイダー固有の制限に注意して実装")
        
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