#!/usr/bin/env python3
"""
OpenAI Agents SDK - Result各要素 サンプルプログラム
"""

import asyncio
import os
import sys
import datetime
import json
from dataclasses import dataclass
from typing import Any, List

# OpenAI Agents SDK のインポート
try:
    from pydantic import BaseModel
    from agents import (
        Agent,
        Runner,
        RunContextWrapper,
        function_tool,
        handoff,
        input_guardrail,
        output_guardrail,
        GuardrailFunctionOutput,
        InputGuardrailTripwireTriggered,
        OutputGuardrailTripwireTriggered,
    )
    from agents.items import (
        RunItem, 
        MessageOutputItem, 
        ToolCallItem, 
        ToolCallOutputItem,
        HandoffCallItem,
        HandoffOutputItem
    )
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
    conversation_history: List[str]


# 出力データモデル
class TaskResponse(BaseModel):
    content: str
    category: str
    confidence: float
    timestamp: str


class AnalysisResponse(BaseModel):
    analysis: str
    recommendations: List[str]
    urgency_level: str


# ツール関数群
@function_tool
def get_current_time() -> str:
    """現在の日時を取得する"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def analyze_text(text: str) -> str:
    """テキストの簡単な分析を行う"""
    word_count = len(text.split())
    char_count = len(text)
    
    # 感情分析（簡易版）
    positive_words = ["良い", "素晴らしい", "最高", "嬉しい", "ありがとう", "good", "great", "excellent"]
    negative_words = ["悪い", "最悪", "残念", "困った", "問題", "bad", "terrible", "awful"]
    
    positive_count = sum(1 for word in positive_words if word in text.lower())
    negative_count = sum(1 for word in negative_words if word in text.lower())
    
    if positive_count > negative_count:
        sentiment = "ポジティブ"
    elif negative_count > positive_count:
        sentiment = "ネガティブ"
    else:
        sentiment = "中性"
    
    return f"分析結果: 文字数={char_count}, 単語数={word_count}, 感情={sentiment} (P:{positive_count}, N:{negative_count})"


@function_tool
def generate_recommendation(context: str) -> str:
    """コンテキストに基づいて推奨事項を生成する"""
    recommendations = [
        "詳細な分析が必要です",
        "追加情報の収集をお勧めします",
        "専門家との相談を検討してください",
        "段階的なアプローチを取ることをお勧めします"
    ]
    
    import random
    selected = random.sample(recommendations, min(2, len(recommendations)))
    return f"推奨事項: {', '.join(selected)}"


# Guardrail関数
@input_guardrail
async def input_logger_guardrail(ctx, agent, input_data) -> GuardrailFunctionOutput:
    """入力をログに記録するGuardrail"""
    timestamp = datetime.datetime.now().isoformat()
    input_text = str(input_data)
    
    log_info = {
        "timestamp": timestamp,
        "agent": agent.name,
        "user_id": ctx.context.user_id,
        "input_length": len(input_text),
        "input_preview": input_text[:50] + "..." if len(input_text) > 50 else input_text
    }
    
    print(f"📝 [Input Guardrail] ログ記録: {log_info}")
    
    return GuardrailFunctionOutput(
        output_info=log_info,
        tripwire_triggered=False
    )


@output_guardrail
async def output_validator_guardrail(ctx, agent, output) -> GuardrailFunctionOutput:
    """出力を検証するGuardrail"""
    validation_info = {
        "agent_name": agent.name,
        "output_type": type(output).__name__,
        "has_content": hasattr(output, 'content') and bool(getattr(output, 'content', '')),
        "validation_time": datetime.datetime.now().isoformat()
    }
    
    print(f"✅ [Output Guardrail] 検証完了: {validation_info}")
    
    return GuardrailFunctionOutput(
        output_info=validation_info,
        tripwire_triggered=False
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


def analyze_run_items(new_items: List[RunItem]):
    """RunItemの詳細分析"""
    print("\n🔍 Run Items 詳細分析:")
    print("-" * 60)
    
    item_counts = {}
    
    for i, item in enumerate(new_items):
        item_type = item.type
        item_counts[item_type] = item_counts.get(item_type, 0) + 1
        
        print(f"📋 Item {i+1}: {item_type}")
        
        if item_type == "message_output_item":
            # MessageOutputItem の詳細
            if hasattr(item, 'raw_item') and hasattr(item.raw_item, 'content'):
                content = str(item.raw_item.content)[:100]
                print(f"   💬 メッセージ: {content}{'...' if len(str(item.raw_item.content)) > 100 else ''}")
                
        elif item_type == "tool_call_item":
            # ToolCallItem の詳細
            if hasattr(item, 'tool_name'):
                print(f"   🔧 ツール名: {item.tool_name}")
            if hasattr(item, 'raw_item') and hasattr(item.raw_item, 'function'):
                args = getattr(item.raw_item.function, 'arguments', 'N/A')
                print(f"   📥 引数: {args}")
                
        elif item_type == "tool_call_output_item":
            # ToolCallOutputItem の詳細
            if hasattr(item, 'output'):
                output_preview = str(item.output)[:80]
                print(f"   📤 出力: {output_preview}{'...' if len(str(item.output)) > 80 else ''}")
                
        elif item_type == "handoff_call_item":
            # HandoffCallItem の詳細
            print(f"   🔄 ハンドオフ呼び出し")
            
        elif item_type == "handoff_output_item":
            # HandoffOutputItem の詳細
            if hasattr(item, 'source_agent') and hasattr(item, 'target_agent'):
                print(f"   🔄 ハンドオフ: {item.source_agent.name} → {item.target_agent.name}")
    
    print(f"\n📊 アイテム統計:")
    for item_type, count in item_counts.items():
        print(f"   {item_type}: {count}個")


async def demonstrate_basic_result_analysis(user_context: UserContext):
    """基本的なResult分析のデモ"""
    print("\n" + "="*80)
    print("📊 1. 基本的なResult分析デモ")
    print("="*80)
    
    # 基本Agent
    basic_agent = Agent[UserContext](
        name="Basic Analyzer",
        instructions=(
            "テキスト分析の専門家として、入力されたテキストを詳細に分析し、"
            "構造化された結果を返してください。"
        ),
        model="gpt-4o-mini",
        tools=[analyze_text, get_current_time],
        output_type=TaskResponse,
        input_guardrails=[input_logger_guardrail],
        output_guardrails=[output_validator_guardrail],
    )
    
    test_input = "今日は素晴らしい天気ですね！プログラミングの勉強が捗りそうです。"
    
    try:
        print(f"📝 入力: 「{test_input}」")
        print("-" * 50)
        
        result = await Runner.run(
            starting_agent=basic_agent,
            input=test_input,
            context=user_context,
            max_turns=5
        )
        
        # === 1. final_output の分析 ===
        print(f"🎯 final_output 分析:")
        print(f"   タイプ: {type(result.final_output).__name__}")
        if hasattr(result.final_output, 'content'):
            print(f"   内容: {result.final_output.content}")
            print(f"   カテゴリ: {result.final_output.category}")
            print(f"   信頼度: {result.final_output.confidence}")
            print(f"   タイムスタンプ: {result.final_output.timestamp}")
        else:
            print(f"   値: {result.final_output}")
        
        # === 2. last_agent の分析 ===
        print(f"\n🤖 last_agent 分析:")
        print(f"   名前: {result.last_agent.name}")
        print(f"   モデル: {result.last_agent.model}")
        print(f"   ツール数: {len(result.last_agent.tools)}")
        print(f"   ツール: {[tool.name for tool in result.last_agent.tools]}")
        
        # === 3. new_items の詳細分析 ===
        print(f"\n📋 new_items 分析:")
        print(f"   総アイテム数: {len(result.new_items)}")
        analyze_run_items(result.new_items)
        
        # === 4. Guardrail結果の分析 ===
        print(f"\n🛡️  Guardrail 結果分析:")
        if result.input_guardrail_results:
            print(f"   Input Guardrails: {len(result.input_guardrail_results)}件")
            for i, gr in enumerate(result.input_guardrail_results):
                print(f"     {i+1}. {gr.output_info}")
        
        if result.output_guardrail_results:
            print(f"   Output Guardrails: {len(result.output_guardrail_results)}件")
            for i, gr in enumerate(result.output_guardrail_results):
                print(f"     {i+1}. {gr.output_info}")
        
        # === 5. raw_responses の分析 ===
        print(f"\n🔤 raw_responses 分析:")
        print(f"   総レスポンス数: {len(result.raw_responses)}")
        for i, response in enumerate(result.raw_responses):
            print(f"   レスポンス {i+1}: {type(response).__name__}")
            if hasattr(response, 'model'):
                print(f"     モデル: {response.model}")
            if hasattr(response, 'usage'):
                print(f"     使用量: {response.usage}")
        
        # === 6. input の確認 ===
        print(f"\n📥 元の入力:")
        print(f"   入力: {result.input}")
        
        return result
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None


async def demonstrate_handoff_result_analysis(user_context: UserContext):
    """ハンドオフを含むResult分析のデモ"""
    print("\n" + "="*80)
    print("🔄 2. ハンドオフを含むResult分析デモ")
    print("="*80)
    
    # 専門Agent群
    text_analyzer = Agent[UserContext](
        name="Text Analysis Specialist",
        instructions="テキスト分析の専門家として詳細な分析を提供します。",
        tools=[analyze_text],
        output_type=AnalysisResponse,
    )
    
    recommendation_agent = Agent[UserContext](
        name="Recommendation Specialist", 
        instructions="推奨事項の提供専門家として実用的なアドバイスを提供します。",
        tools=[generate_recommendation],
        output_type=AnalysisResponse,
    )
    
    # マスターAgent
    master_agent = Agent[UserContext](
        name="Master Coordinator",
        instructions=(
            "入力内容を分析し、適切な専門Agentにハンドオフします。"
            "テキスト分析が必要 → Text Analysis Specialist"
            "推奨事項が必要 → Recommendation Specialist"
        ),
        model="gpt-4o-mini",
        handoffs=[
            handoff(text_analyzer, tool_description_override="詳細なテキスト分析が必要な場合"),
            handoff(recommendation_agent, tool_description_override="推奨事項の提供が必要な場合"),
        ]
    )
    
    test_inputs = [
        "このテキストの感情を分析してください：とても素晴らしい一日でした！",
        "新しいプロジェクトを始めるのにアドバイスをください"
    ]
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n📝 テストケース {i}: 「{test_input}」")
        print("-" * 60)
        
        try:
            result = await Runner.run(
                starting_agent=master_agent,
                input=test_input,
                context=user_context,
                max_turns=6
            )
            
            # === ハンドオフ特化分析 ===
            print(f"🎯 ハンドオフ結果分析:")
            print(f"   開始Agent: {master_agent.name}")
            print(f"   最終Agent: {result.last_agent.name}")
            print(f"   ハンドオフ発生: {'Yes' if result.last_agent != master_agent else 'No'}")
            
            # === HandoffItem の詳細分析 ===
            handoff_items = [item for item in result.new_items if 'handoff' in item.type]
            if handoff_items:
                print(f"\n🔄 ハンドオフアイテム分析:")
                for j, item in enumerate(handoff_items):
                    print(f"   ハンドオフ {j+1}: {item.type}")
                    if hasattr(item, 'source_agent') and hasattr(item, 'target_agent'):
                        print(f"     {item.source_agent.name} → {item.target_agent.name}")
            
            # === 最終出力 ===
            print(f"\n💬 最終出力:")
            if hasattr(result.final_output, 'analysis'):
                print(f"   分析: {result.final_output.analysis}")
                print(f"   推奨事項: {result.final_output.recommendations}")
                print(f"   緊急度: {result.final_output.urgency_level}")
            else:
                print(f"   出力: {result.final_output}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")


async def demonstrate_conversation_continuation(user_context: UserContext):
    """会話継続のためのto_input_list()デモ"""
    print("\n" + "="*80)
    print("💬 3. 会話継続 (to_input_list) デモ")
    print("="*80)
    
    conversation_agent = Agent[UserContext](
        name="Conversation Agent",
        instructions=(
            "前の会話内容を覚えて、自然な対話を続けてください。"
            "ユーザーの質問に対して、コンテキストを考慮した回答を提供します。"
        ),
        model="gpt-4o-mini",
        tools=[get_current_time],
    )
    
    # 会話のシミュレーション
    conversation_turns = [
        "こんにちは！今日はプログラミングについて話したいです。",
        "OpenAI Agents SDKについて詳しく教えてください。",
        "先ほど説明してもらったSDKの中で一番重要な機能は何ですか？"
    ]
    
    current_input = None
    
    for turn_num, user_input in enumerate(conversation_turns, 1):
        print(f"\n🗨️  ターン {turn_num}")
        print(f"👤 ユーザー: {user_input}")
        print("-" * 40)
        
        try:
            # 最初のターン以外は前の結果を引き継ぎ
            if current_input is None:
                run_input = user_input
                print("📝 初回入力を使用")
            else:
                # to_input_list()で前の会話履歴を含める
                run_input = current_input + [{"role": "user", "content": user_input}]
                print(f"📚 会話履歴を含む入力を使用 (アイテム数: {len(run_input)})")
            
            result = await Runner.run(
                starting_agent=conversation_agent,
                input=run_input,
                context=user_context,
                max_turns=4
            )
            
            print(f"🤖 Agent: {result.final_output}")
            
            # === to_input_list() の活用 ===
            current_input = result.to_input_list()
            print(f"📋 次回用入力リスト準備完了 (要素数: {len(current_input)})")
            
            # 会話履歴をユーザーコンテキストに記録
            user_context.conversation_history.append(f"User: {user_input}")
            user_context.conversation_history.append(f"Agent: {str(result.final_output)[:100]}...")
            
        except Exception as e:
            print(f"❌ ターン {turn_num} エラー: {str(e)}")
            break
    
    print(f"\n📚 会話履歴サマリー:")
    for i, entry in enumerate(user_context.conversation_history, 1):
        print(f"  {i}. {entry}")


async def demonstrate_streaming_result_analysis(user_context: UserContext):
    """ストリーミング結果の分析デモ"""
    print("\n" + "="*80)
    print("📡 4. ストリーミング結果分析デモ")
    print("="*80)
    
    streaming_agent = Agent[UserContext](
        name="Streaming Analyzer",
        instructions=(
            "詳細で段階的な分析を提供するエージェントです。"
            "分析過程を段階的に説明し、ツールを活用して総合的な結果を提供します。"
        ),
        model="gpt-4o-mini",
        tools=[analyze_text, generate_recommendation, get_current_time],
        output_type=TaskResponse,
    )
    
    test_input = "最近、チームでの協力が問題になっています。効果的な解決策を教えてください。"
    
    try:
        print(f"📝 入力: 「{test_input}」")
        print("🌊 ストリーミング開始...")
        print("-" * 60)
        
        # ストリーミング実行
        streaming_result = Runner.run_streamed(
            starting_agent=streaming_agent,
            input=test_input,
            context=user_context,
            max_turns=5
        )
        
        # リアルタイムイベント処理
        event_log = []
        text_chunks = []
        
        async for event in streaming_result.stream_events():
            event_info = {
                "type": event.type,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            if event.type == "raw_response_event":
                if hasattr(event.data, 'delta') and event.data.delta:
                    text_chunks.append(event.data.delta)
                    print(event.data.delta, end='', flush=True)
                    event_info["content"] = event.data.delta
                    
            elif event.type == "run_item_stream_event":
                item = event.item
                if item.type == "tool_call_item":
                    print(f"\n🔧 [ツール呼び出し] {item.tool_name}")
                    event_info["tool_name"] = item.tool_name
                elif item.type == "tool_call_output_item":
                    print(f"\n✅ [ツール完了] {item.output[:50]}...")
                    event_info["tool_output"] = item.output[:100]
                    
            event_log.append(event_info)
        
        print(f"\n\n🏁 ストリーミング完了")
        print("-" * 60)
        
        # === ストリーミング結果の詳細分析 ===
        final_result = streaming_result.final_result
        if final_result:
            print(f"📊 ストリーミング結果分析:")
            print(f"   最終出力タイプ: {type(final_result.final_output).__name__}")
            print(f"   処理されたイベント数: {len(event_log)}")
            print(f"   生成されたテキストチャンク数: {len(text_chunks)}")
            print(f"   総文字数: {sum(len(chunk) for chunk in text_chunks)}")
            
            # イベントタイプの統計
            event_types = {}
            for event in event_log:
                event_type = event['type']
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            print(f"\n📈 イベント統計:")
            for event_type, count in event_types.items():
                print(f"   {event_type}: {count}回")
        
    except Exception as e:
        print(f"❌ ストリーミングエラー: {str(e)}")


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            user_id="user_789",
            session_id="session_abc",
            conversation_history=[]
        )
        
        print("🎪 OpenAI Agents SDK - Result 各要素 デモ")
        print("="*80)
        print(f"👤 ユーザーID: {user_context.user_id}")
        print(f"🔗 セッションID: {user_context.session_id}")
        print("="*80)
        
        # 1. 基本的なResult分析
        await demonstrate_basic_result_analysis(user_context)
        
        # 2. ハンドオフを含むResult分析
        await demonstrate_handoff_result_analysis(user_context)
        
        # 3. 会話継続デモ
        await demonstrate_conversation_continuation(user_context)
        
        # 4. ストリーミング結果分析
        await demonstrate_streaming_result_analysis(user_context)
        
        print(f"\n🎉 全Result要素デモンストレーション完了！")
        print("="*80)
        print("📚 学習内容まとめ:")
        print("✅ final_output - Agent実行の最終結果")
        print("✅ last_agent - 最後に実行されたAgent情報")
        print("✅ new_items - 実行中に生成された各種アイテム")
        print("✅ to_input_list() - 会話継続のための入力準備")
        print("✅ guardrail_results - 入力/出力検証結果")
        print("✅ raw_responses - LLMの生レスポンス")
        print("✅ input - 元の入力情報")
        print("✅ ストリーミング結果 - リアルタイム処理結果")
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