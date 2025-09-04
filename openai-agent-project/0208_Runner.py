#!/usr/bin/env python3
"""
OpenAI Agents SDK - Runner各要素 サンプルプログラム
"""

import asyncio
import os
import sys
import datetime
from dataclasses import dataclass
from typing import Any, List

# OpenAI Agents SDK のインポート
try:
    from pydantic import BaseModel
    from agents import (
        Agent,
        Runner,
        RunConfig,
        AgentOutputSchema,
        RunContextWrapper,
        function_tool,
        RunHooks,
        ModelSettings,
        input_guardrail,
        output_guardrail,
        GuardrailFunctionOutput,
        InputGuardrailTripwireTriggered,
        OutputGuardrailTripwireTriggered,
        MaxTurnsExceeded,
        handoff
    )
    from agents.items import RunItem
    from agents.models.multi_provider import MultiProvider
except ImportError:
    print("❌ エラー: 必要なライブラリがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install openai-agents pydantic")
    sys.exit(1)


# ユーザーコンテキストの定義
@dataclass
class UserContext:
    user_id: str
    session_id: str
    preferences: dict
    conversation_count: int = 0


# 出力データモデル
class TaskResponse(BaseModel):
    result: str
    status: str
    execution_time: float
    metadata: dict


# ツール関数群
@function_tool
def get_current_time() -> str:
    """現在の時刻を取得する"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def calculate_math(expression: str) -> str:
    """数学式を計算する（安全な評価）"""
    try:
        # 安全な数学演算のみ許可
        allowed_names = {
            k: v for k, v in __builtins__.items() 
            if k in ['abs', 'min', 'max', 'round', 'sum']
        }
        allowed_names.update({'__builtins__': {}})
        
        result = eval(expression, allowed_names)
        return f"計算結果: {expression} = {result}"
    except Exception as e:
        return f"計算エラー: {str(e)}"


@function_tool
def simulate_long_task(duration: int = 2) -> str:
    """長時間タスクをシミュレートする"""
    import time
    import random
    
    print(f"🔄 {duration}秒間のタスクを開始...")
    time.sleep(duration)
    
    results = [
        "データ処理が完了しました",
        "ファイルの変換が成功しました", 
        "バックアップが作成されました",
        "システムチェックが完了しました"
    ]
    
    return f"✅ {random.choice(results)} ({duration}秒経過)"


# カスタムRunHooks
class DetailedRunHooks(RunHooks):
    """詳細なRunイベントを監視するフック"""
    
    def __init__(self):
        self.turn_count = 0
        self.start_time = None
        
    async def on_agent_start(self, context: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> None:
        self.turn_count += 1
        if self.start_time is None:
            self.start_time = datetime.datetime.now()
        
        print(f"🎯 [Turn {self.turn_count}] Agent '{agent.name}' を開始")
        print(f"   ユーザー: {context.context.user_id}")
        
    async def on_agent_end(self, context: RunContextWrapper[UserContext], agent: Agent[UserContext], output: Any) -> None:
        elapsed = datetime.datetime.now() - self.start_time if self.start_time else 0
        print(f"✅ [Turn {self.turn_count}] Agent '{agent.name}' 完了 (経過時間: {elapsed})")
        
    async def on_tool_start(self, context: RunContextWrapper[UserContext], agent: Agent[UserContext], tool) -> None:
        print(f"🔧 ツール '{tool.name}' を実行中...")
        
    async def on_tool_end(self, context: RunContextWrapper[UserContext], agent: Agent[UserContext], tool, result: str) -> None:
        print(f"✨ ツール '{tool.name}' 完了: {result[:50]}{'...' if len(result) > 50 else ''}")
        
    async def on_handoff(self, context: RunContextWrapper[UserContext], from_agent: Agent[UserContext], to_agent: Agent[UserContext]) -> None:
        print(f"🔄 ハンドオフ: '{from_agent.name}' → '{to_agent.name}'")


# Guardrail関数
@input_guardrail
async def turn_limit_guardrail(ctx, agent, input_data) -> GuardrailFunctionOutput:
    """ターン数制限のGuardrail"""
    user_context = ctx.context
    user_context.conversation_count += 1
    
    # 10ターンを超えたら警告
    is_too_many_turns = user_context.conversation_count > 10
    
    if is_too_many_turns:
        print(f"⚠️ [Guardrail] 会話ターン数が上限に達しました: {user_context.conversation_count}/10")
    
    return GuardrailFunctionOutput(
        output_info={"turn_count": user_context.conversation_count},
        tripwire_triggered=is_too_many_turns
    )


def check_api_key():
    """OpenAI API キーの存在確認"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ エラー: 環境変数 OPENAI_API_KEY が設定されていません。")
        print("以下の方法で設定してください:")
        print("  Linux/Mac: export OPENAI_API_KEY='your-api-key-here'")
        print("  Windows: set OPENAI_API_KEY=your-api-key-here")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️  警告: API キーの形式が正しくない可能性があります。")
        print("OpenAI API キーは通常 'sk-' で始まります。")
    
    print("✅ API キーが正常に設定されています")
    return True


async def demonstrate_basic_run(user_context: UserContext):
    """基本的なRunner.run()のデモンストレーション"""
    print("\n" + "="*80)
    print("🏃 1. 基本的な Runner.run() デモ")
    print("="*80)
    
    # シンプルなAgent
    basic_agent = Agent[UserContext](
        name="Basic Assistant",
        instructions=(
            f"{user_context.user_id}さんのアシスタントです。"
            "質問に対して簡潔で役立つ回答を提供します。"
        ),
        model="gpt-4o-mini",
        tools=[get_current_time],
        output_type=AgentOutputSchema(TaskResponse, strict_json_schema=False),
    )
    
    try:
        print("📝 質問: 今日の日付と時刻を教えてください")
        
        start_time = datetime.datetime.now()
        result = await Runner.run(
            starting_agent=basic_agent,
            input="今日の日付と時刻を教えてください",
            context=user_context,
            max_turns=5  # 最大5ターンまで
        )
        end_time = datetime.datetime.now()
        
        print(f"✅ 実行成功!")
        print(f"🤖 実行Agent: {result.last_agent.name}")
        print(f"💬 応答: {result.final_output.result}")
        print(f"📊 ステータス: {result.final_output.status}")
        print(f"⏱️ 実行時間: {(end_time - start_time).total_seconds():.2f}秒")
        
        return result
        
    except MaxTurnsExceeded:
        print("❌ 最大ターン数に達しました")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None


async def demonstrate_run_with_config(user_context: UserContext):
    """RunConfigを使用したRunner.run()のデモ"""
    print("\n" + "="*80)
    print("⚙️ 2. RunConfig を使用した Runner.run() デモ")
    print("="*80)
    
    # カスタムRunHooks
    hooks = DetailedRunHooks()
    
    # RunConfigの設定
    run_config = RunConfig(
        model="gpt-4o-mini",  # 全Agentで使用するモデルを統一
        model_settings=ModelSettings(
            temperature=0.7,
            max_tokens=1000,
        ),
        workflow_name="Advanced Calculator Workflow",
        trace_metadata={
            "user_id": user_context.user_id,
            "session_id": user_context.session_id,
            "version": "1.0.0"
        },
        tracing_disabled=False,  # トレースを有効化
        input_guardrails=[turn_limit_guardrail],  # グローバルInput Guardrail
    )
    
    # 計算専用Agent
    calculator_agent = Agent[UserContext](
        name="Calculator Agent",
        instructions=(
            "数学の計算を専門とするエージェントです。"
            "計算ツールを使用して正確な結果を提供します。"
        ),
        tools=[calculate_math, get_current_time],
        output_type=AgentOutputSchema(TaskResponse, strict_json_schema=False),
    )
    
    try:
        print("📝 質問: (15 + 25) * 3 - 10 を計算してください")
        
        result = await Runner.run(
            starting_agent=calculator_agent,
            input="(15 + 25) * 3 - 10 を計算してください", 
            context=user_context,
            hooks=hooks,
            run_config=run_config,
            max_turns=3
        )
        
        print(f"🎯 最終結果: {result.final_output.result}")
        print(f"📈 メタデータ: {result.final_output.metadata}")
        
        return result
        
    except InputGuardrailTripwireTriggered:
        print("🚨 Input Guardrailがトリガーされました（ターン数制限）")
    except MaxTurnsExceeded:
        print("❌ RunConfigで設定された最大ターン数に達しました")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None


async def demonstrate_run_sync(user_context: UserContext):
    """Runner.run_sync()のデモンストレーション（同期実行）"""
    print("\n" + "="*80)
    print("🔄 3. Runner.run_sync() デモ（同期実行）")
    print("="*80)
    
    # 同期実行用Agent
    sync_agent = Agent[UserContext](
        name="Sync Assistant", 
        instructions="同期実行での簡潔な回答を提供します。",
        model="gpt-4o-mini",
        tools=[get_current_time],
    )
    
    try:
        print("📝 質問: こんにちは！元気ですか？")
        
        # 同期実行（asyncio.run内では使用不可のため、コメントアウト）
        # result = Runner.run_sync(
        #     starting_agent=sync_agent,
        #     input="こんにちは！元気ですか？",
        #     context=user_context,
        #     max_turns=2
        # )
        
        print("ℹ️ 注意: run_sync()は非同期環境内では実行できません。")
        print("   通常のPythonスクリプトやJupyterノートブック以外で使用してください。")
        print("   代わりにrun()メソッドを使用します。")
        
        # 代替として非同期実行
        result = await Runner.run(
            starting_agent=sync_agent,
            input="こんにちは！元気ですか？",
            context=user_context,
            max_turns=2
        )
        
        print(f"💬 応答: {result.final_output}")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")


async def demonstrate_run_streamed(user_context: UserContext):
    """Runner.run_streamed()のデモンストレーション（ストリーミング実行）"""
    print("\n" + "="*80)
    print("📡 4. Runner.run_streamed() デモ（ストリーミング実行）")
    print("="*80)
    
    # ストリーミング用Agent
    streaming_agent = Agent[UserContext](
        name="Streaming Assistant",
        instructions=(
            "長い応答をストリーミングで提供するアシスタントです。"
            "タスクの進行状況を詳しく説明します。"
        ),
        model="gpt-4o-mini", 
        tools=[simulate_long_task, get_current_time],
        output_type=AgentOutputSchema(TaskResponse, strict_json_schema=False),
    )
    
    try:
        print("📝 質問: 長時間のデータ処理タスクを実行してください")
        
        # ストリーミング実行
        streaming_result = Runner.run_streamed(
            starting_agent=streaming_agent,
            input="長時間のデータ処理タスクを実行してください",
            context=user_context,
            max_turns=5
        )
        
        print("🌊 ストリーミング開始...")
        print("-" * 60)
        
        # ストリーミングイベントの処理
        event_count = 0
        async for event in streaming_result.stream_events():
            event_count += 1
            
            if event.type == "raw_response_event":
                # 生のレスポンスイベント（テキスト生成等）
                if hasattr(event.data, 'delta') and event.data.delta:
                    print(event.data.delta, end='', flush=True)
                    
            elif event.type == "run_item_stream_event":
                # 高レベルなイベント（ツール実行等）
                item = event.item
                if item.type == "tool_call_item":
                    print(f"\n🔧 [Event {event_count}] ツール呼び出し: {item.tool_name}")
                elif item.type == "tool_call_output_item":
                    print(f"\n✅ [Event {event_count}] ツール出力: {item.output[:50]}...")
                elif item.type == "message_output_item":
                    print(f"\n💬 [Event {event_count}] メッセージ出力完了")
                    
            elif event.type == "agent_updated_stream_event":
                print(f"\n🔄 [Event {event_count}] Agent更新: {event.new_agent.name}")
        
        print(f"\n🏁 ストリーミング完了 (総イベント数: {event_count})")
        print("-" * 60)
        
        # 最終結果の取得
        final_result = streaming_result.final_result
        if final_result and hasattr(final_result.final_output, 'result'):
            print(f"🎯 最終結果: {final_result.final_output.result}")
        else:
            print(f"🎯 最終結果: {final_result.final_output}")
            
    except Exception as e:
        print(f"❌ ストリーミングエラー: {str(e)}")


async def demonstrate_advanced_features(user_context: UserContext):
    """高度な機能のデモンストレーション"""
    print("\n" + "="*80)
    print("🚀 5. 高度な機能デモ（ハンドオフ + 複雑な設定）")
    print("="*80)
    
    # 専門Agentの作成
    math_agent = Agent[UserContext](
        name="Math Specialist",
        instructions="数学計算の専門家です。複雑な計算を正確に実行します。",
        tools=[calculate_math],
        output_type=AgentOutputSchema(TaskResponse, strict_json_schema=False),
    )
    
    time_agent = Agent[UserContext](
        name="Time Specialist", 
        instructions="時間関連の質問に特化した専門家です。",
        tools=[get_current_time],
        output_type=AgentOutputSchema(TaskResponse, strict_json_schema=False),
    )
    
    # マスターAgent（ハンドオフ機能付き）
    master_agent = Agent[UserContext](
        name="Master Coordinator",
        instructions=(
            "質問の内容を分析し、適切な専門Agentにハンドオフします。"
            "数学関連 → Math Specialist, 時間関連 → Time Specialist"
        ),
        model="gpt-4o-mini",
        handoffs=[
            handoff(math_agent, tool_description_override="数学計算が必要な場合"),
            handoff(time_agent, tool_description_override="時間情報が必要な場合"),
        ]
    )
    
    # 高度なRunConfig
    advanced_config = RunConfig(
        workflow_name="Advanced Multi-Agent System",
        model_settings=ModelSettings(
            temperature=0.3,  # より決定論的な応答
            max_tokens=800,
        ),
        trace_metadata={
            "experiment": "multi_agent_handoff",
            "user_type": "advanced_user"
        }
    )
    
    # 複雑なフック
    advanced_hooks = DetailedRunHooks()
    
    questions = [
        "100の平方根を計算してください",
        "現在の時刻を教えてください", 
        "こんにちは、元気ですか？"  # ハンドオフされない質問
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n📝 質問 {i}: 「{question}」")
        print("-" * 50)
        
        try:
            result = await Runner.run(
                starting_agent=master_agent,
                input=question,
                context=user_context,
                hooks=advanced_hooks,
                run_config=advanced_config,
                max_turns=4
            )
            
            print(f"🎯 実行Agent: {result.last_agent.name}")
            if hasattr(result.final_output, 'result'):
                print(f"💬 結果: {result.final_output.result}")
            else:
                print(f"💬 結果: {result.final_output}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            user_id="user_123",
            session_id="session_456", 
            preferences={
                "language": "ja",
                "format": "detailed",
                "max_response_length": 1000
            }
        )
        
        print("🎪 OpenAI Agents SDK - Runner 各要素 デモ")
        print("="*80)
        print(f"👤 ユーザーID: {user_context.user_id}")
        print(f"🔗 セッションID: {user_context.session_id}")
        print(f"⚙️ 設定: {user_context.preferences}")
        print("="*80)
        
        # 1. 基本的なrun()デモ
        await demonstrate_basic_run(user_context)
        
        # 2. RunConfigを使ったrun()デモ
        await demonstrate_run_with_config(user_context)
        
        # 3. run_sync()デモ
        await demonstrate_run_sync(user_context)
        
        # 4. run_streamed()デモ  
        await demonstrate_run_streamed(user_context)
        
        # 5. 高度な機能デモ
        await demonstrate_advanced_features(user_context)
        
        print(f"\n🎉 全デモンストレーション完了！")
        print("="*80)
        print("📊 学習内容まとめ:")
        print("✅ Runner.run() - 基本的な非同期実行")
        print("✅ RunConfig - 実行設定のカスタマイズ")
        print("✅ Runner.run_sync() - 同期実行")
        print("✅ Runner.run_streamed() - ストリーミング実行")
        print("✅ RunHooks - ライフサイクルイベント監視")
        print("✅ max_turns - ターン数制限")
        print("✅ Guardrails - 入力出力の検証")
        print("✅ ハンドオフ - Agent間の連携")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  プログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        print(f"エラー詳細: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())