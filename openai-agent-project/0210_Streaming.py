#!/usr/bin/env python3
"""
OpenAI Agents SDK - Streaming各要素 サンプルプログラム
"""

import asyncio
import os
import sys
import datetime
import time
from dataclasses import dataclass
from typing import Any, List, Dict

# OpenAI Agents SDK のインポート
try:
    from pydantic import BaseModel
    from openai.types.responses import ResponseTextDeltaEvent
    from agents import (
        Agent,
        Runner,
        AgentOutputSchema,
        RunContextWrapper,
        function_tool,
        handoff,
        ItemHelpers
    )
    from agents.stream_events import (
        StreamEvent,
        RawResponsesStreamEvent,
        RunItemStreamEvent,
        AgentUpdatedStreamEvent
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
    preferences: Dict[str, Any]


# 出力データモデル
class StreamingResponse(BaseModel):
    content: str
    status: str
    processing_time: float
    metadata: Dict[str, Any]


# ツール関数群
@function_tool
def get_current_time() -> str:
    """現在の日時を取得する"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def generate_random_number(min_val: int = 1, max_val: int = 100) -> str:
    """指定範囲のランダム数を生成する"""
    import random
    number = random.randint(min_val, max_val)
    return f"生成されたランダム数: {number}"


@function_tool
def simulate_data_processing(duration: int = 3) -> str:
    """データ処理をシミュレートする（時間のかかる処理）"""
    print(f"   🔄 データ処理開始... ({duration}秒)")
    time.sleep(duration)  # 処理時間をシミュレート
    
    results = [
        "データベースの最適化が完了しました",
        "1000件のレコードを処理しました",
        "統計分析レポートを生成しました",
        "機械学習モデルを更新しました"
    ]
    
    import random
    result = random.choice(results)
    print(f"   ✅ データ処理完了: {result}")
    return result


@function_tool
def search_knowledge_base(query: str) -> str:
    """知識ベースを検索する（模擬）"""
    knowledge_base = {
        "プログラミング": "プログラミングは論理的思考とクリエイティビティを組み合わせたスキルです",
        "AI": "人工知能は機械学習、自然言語処理、コンピュータビジョンなどの技術を含みます",
        "python": "Pythonは読みやすく、多目的なプログラミング言語です",
        "機械学習": "機械学習はデータからパターンを学習する技術です"
    }
    
    # 簡単な検索ロジック
    for key, value in knowledge_base.items():
        if key.lower() in query.lower():
            return f"検索結果: {value}"
    
    return f"'{query}'に関する情報は見つかりませんでしたが、一般的な技術サポートを提供できます。"


class StreamingEventAnalyzer:
    """ストリーミングイベントの分析・統計クラス"""
    
    def __init__(self):
        self.event_stats = {}
        self.raw_text_chunks = []
        self.tool_executions = []
        self.agent_changes = []
        self.start_time = None
        self.total_events = 0
        
    def reset(self):
        """統計をリセット"""
        self.__init__()
        
    def _safe_tool_name(self, item: Any) -> str:
        raw = getattr(item, 'raw_item', None)
        name = getattr(raw, 'name', None)
        if name:
            return name
        item_type = getattr(raw, 'type', None)
        return item_type if isinstance(item_type, str) else 'Unknown'

    def record_event(self, event: StreamEvent):
        """イベントを記録"""
        if self.start_time is None:
            self.start_time = time.time()
            
        self.total_events += 1
        event_type = event.type
        
        # イベントタイプ別統計
        self.event_stats[event_type] = self.event_stats.get(event_type, 0) + 1
        
        # イベント詳細の記録
        if event_type == "raw_response_event":
            if hasattr(event.data, 'delta') and event.data.delta:
                self.raw_text_chunks.append(event.data.delta)
                
        elif event_type == "run_item_stream_event":
            item = event.item
            if item.type == "tool_call_item":
                self.tool_executions.append({
                    "tool_name": self._safe_tool_name(item),
                    "timestamp": time.time()
                })
                
        elif event_type == "agent_updated_stream_event":
            self.agent_changes.append({
                "new_agent": event.new_agent.name,
                "timestamp": time.time()
            })
    
    def get_summary(self) -> Dict[str, Any]:
        """分析結果のサマリーを取得"""
        total_time = time.time() - self.start_time if self.start_time else 0
        total_text_length = sum(len(chunk) for chunk in self.raw_text_chunks)
        
        return {
            "execution_time": total_time,
            "total_events": self.total_events,
            "event_breakdown": self.event_stats,
            "text_generation": {
                "chunks": len(self.raw_text_chunks),
                "total_characters": total_text_length,
                "avg_chunk_size": total_text_length / max(1, len(self.raw_text_chunks))
            },
            "tool_usage": {
                "executions": len(self.tool_executions),
                "tools_used": list(set(t["tool_name"] for t in self.tool_executions))
            },
            "agent_changes": len(self.agent_changes)
        }


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


async def demonstrate_basic_streaming(user_context: UserContext):
    """基本的なストリーミングのデモ"""
    print("\n" + "="*80)
    print("📡 1. 基本的なストリーミングデモ")
    print("="*80)
    
    # 基本ストリーミングAgent
    streaming_agent = Agent[UserContext](
        name="Basic Streaming Agent",
        instructions=(
            "あなたは親切で詳細な説明をするアシスタントです。"
            "質問に対して、段階的で分かりやすい回答を提供してください。"
            "必要に応じてツールを使用して情報を取得します。"
        ),
        model="gpt-4o-mini",
        tools=[get_current_time, generate_random_number],
        output_type=AgentOutputSchema(StreamingResponse, strict_json_schema=False),
    )
    
    test_input = "現在の時刻を教えて、そして1から10の間でランダムな数字を生成してください。"
    
    try:
        print(f"📝 入力: 「{test_input}」")
        print("🌊 ストリーミング開始...")
        print("-" * 80)
        
        # ストリーミング実行
        streaming_result = Runner.run_streamed(
            starting_agent=streaming_agent,
            input=test_input,
            context=user_context,
            max_turns=5
        )
        
        # イベント分析器
        analyzer = StreamingEventAnalyzer()
        
        print("💭 生成中: ", end="", flush=True)
        
        # ストリーミングイベントの処理
        async for event in streaming_result.stream_events():
            analyzer.record_event(event)
            
            # === Raw Response Events ===
            if event.type == "raw_response_event":
                # トークンレベルのリアルタイム表示
                if isinstance(event.data, ResponseTextDeltaEvent):
                    print(event.data.delta, end="", flush=True)
                    
            # === Run Item Stream Events ===
            elif event.type == "run_item_stream_event":
                item = event.item
                
                if item.type == "tool_call_item":
                    tool_name = StreamingEventAnalyzer()._safe_tool_name(item)
                    print(f"\n🔧 [ツール呼び出し] {tool_name}")
                    if hasattr(item, 'raw_item') and hasattr(item.raw_item, 'function'):
                        args = getattr(item.raw_item.function, 'arguments', 'N/A')
                        print(f"   引数: {args}")
                        
                elif item.type == "tool_call_output_item":
                    print(f"🔨 [ツール完了] {item.output}")
                    
                elif item.type == "message_output_item":
                    print(f"\n💬 [メッセージ完了]")
                    # ItemHelpersを使用してテキスト抽出
                    message_text = ItemHelpers.text_message_output(item)
                    if message_text:
                        print(f"   内容プレビュー: {message_text[:100]}...")
                        
            # === Agent Updated Events ===
            elif event.type == "agent_updated_stream_event":
                print(f"\n🔄 [Agent変更] {event.new_agent.name}")
        
        print(f"\n🏁 ストリーミング完了")
        print("-" * 80)
        
        # 分析結果の表示
        summary = analyzer.get_summary()
        print(f"📊 ストリーミング分析結果:")
        print(f"   実行時間: {summary['execution_time']:.2f}秒")
        print(f"   総イベント数: {summary['total_events']}")
        print(f"   イベント内訳: {summary['event_breakdown']}")
        print(f"   テキスト生成: {summary['text_generation']}")
        print(f"   ツール使用: {summary['tool_usage']}")
        
        # 最終結果の取得
        final_result = streaming_result.final_output
        if final_result:
            print(f"\n🎯 最終結果:")
            if hasattr(final_result, 'content'):
                print(f"   内容: {final_result.content}")
                if hasattr(final_result, 'status'):
                    print(f"   ステータス: {final_result.status}")
            else:
                print(f"   出力: {final_result}")
                
    except Exception as e:
        print(f"❌ ストリーミングエラー: {str(e)}")


async def demonstrate_advanced_streaming_with_tools(user_context: UserContext):
    """ツールを多用する高度なストリーミングデモ"""
    print("\n" + "="*80)
    print("🔧 2. 高度なツールストリーミングデモ")
    print("="*80)
    
    # ツール集約型Agent
    tool_heavy_agent = Agent[UserContext](
        name="Tool-Heavy Processing Agent",
        instructions=(
            "あなたは複数のツールを効率的に使用して、"
            "複雑な処理を実行するスペシャリストです。"
            "処理の進行状況を詳しく説明し、各ツールの実行結果を統合してください。"
        ),
        model="gpt-4o-mini",
        tools=[
            get_current_time,
            simulate_data_processing,
            search_knowledge_base,
            generate_random_number
        ],
        output_type=AgentOutputSchema(StreamingResponse, strict_json_schema=False),
    )
    
    test_input = "AIについて調べて、データ処理を実行し、現在時刻と共に総合レポートを作成してください。"
    
    try:
        print(f"📝 複雑な処理要求: 「{test_input}」")
        print("🔄 高度なストリーミング処理開始...")
        print("-" * 80)
        
        streaming_result = Runner.run_streamed(
            starting_agent=tool_heavy_agent,
            input=test_input,
            context=user_context,
            max_turns=8
        )
        
        # 詳細な分析器
        analyzer = StreamingEventAnalyzer()
        tool_start_times = {}
        
        print("🎬 処理実況中継:")
        print("-" * 40)
        
        async for event in streaming_result.stream_events():
            analyzer.record_event(event)
            
            if event.type == "raw_response_event":
                # 生テキストは控えめに表示
                if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                    if len(event.data.delta.strip()) > 0:  # 空白でない場合のみ
                        print(".", end="", flush=True)
                        
            elif event.type == "run_item_stream_event":
                item = event.item
                
                if item.type == "tool_call_item":
                    tool_name = StreamingEventAnalyzer()._safe_tool_name(item)
                    tool_start_times[tool_name] = time.time()
                    print(f"\n🚀 [{datetime.datetime.now().strftime('%H:%M:%S')}] {tool_name} 実行開始")
                    
                elif item.type == "tool_call_output_item":
                    tool_name = getattr(getattr(item, 'raw_item', None), 'name', None) or getattr(item, 'tool_name', 'Unknown')
                    duration = time.time() - tool_start_times.get(tool_name, time.time())
                    
                    print(f"✅ [{datetime.datetime.now().strftime('%H:%M:%S')}] {tool_name} 完了 ({duration:.1f}秒)")
                    print(f"   結果: {item.output[:80]}{'...' if len(item.output) > 80 else ''}")
                    
                elif item.type == "message_output_item":
                    print(f"\n📝 [{datetime.datetime.now().strftime('%H:%M:%S')}] メッセージ生成完了")
                    
            elif event.type == "agent_updated_stream_event":
                print(f"\n🔄 [{datetime.datetime.now().strftime('%H:%M:%S')}] Agent変更: {event.new_agent.name}")
        
        print(f"\n🎉 複雑処理完了！")
        print("-" * 80)
        
        # 詳細分析結果
        summary = analyzer.get_summary()
        print(f"📈 詳細分析結果:")
        print(f"   総処理時間: {summary['execution_time']:.2f}秒")
        print(f"   使用ツール: {', '.join(summary['tool_usage']['tools_used'])}")
        print(f"   ツール実行回数: {summary['tool_usage']['executions']}")
        print(f"   平均実行間隔: {summary['execution_time']/max(1, summary['total_events']):.2f}秒/イベント")
        
        # 最終結果
        final_result = streaming_result.final_output
        if final_result and hasattr(final_result, 'content'):
            print(f"\n📋 最終レポート:")
            print(f"   {final_result.content}")
            
    except Exception as e:
        print(f"❌ 高度ストリーミングエラー: {str(e)}")


async def demonstrate_handoff_streaming(user_context: UserContext):
    """ハンドオフを含むストリーミングデモ"""
    print("\n" + "="*80)
    print("🔄 3. ハンドオフストリーミングデモ")
    print("="*80)
    
    # 専門Agent群
    time_specialist = Agent[UserContext](
        name="Time Management Specialist",
        instructions="時間管理と時刻に関する専門的なアドバイスを提供します。",
        tools=[get_current_time],
        output_type=AgentOutputSchema(StreamingResponse, strict_json_schema=False),
    )
    
    data_specialist = Agent[UserContext](
        name="Data Processing Specialist", 
        instructions="データ処理と分析の専門家として詳細な処理を実行します。",
        tools=[simulate_data_processing, search_knowledge_base],
        output_type=AgentOutputSchema(StreamingResponse, strict_json_schema=False),
    )
    
    # コーディネーターAgent
    coordinator_agent = Agent[UserContext](
        name="Task Coordinator",
        instructions=(
            "タスクの内容を分析し、適切な専門Agentにハンドオフします。"
            "時間関連 → Time Management Specialist"
            "データ処理関連 → Data Processing Specialist"
        ),
        model="gpt-4o-mini",
        handoffs=[
            handoff(time_specialist, tool_description_override="時間管理や時刻関連の処理が必要"),
            handoff(data_specialist, tool_description_override="データ処理や分析が必要"),
        ]
    )
    
    test_cases = [
        "現在の時刻を確認して、効率的な時間管理のアドバイスをください",
        "大量のデータを処理して、結果の統計分析をお願いします",
        "こんにちは、今日の調子はどうですか？"  # ハンドオフされない場合
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n📋 テストケース {i}: 「{test_input}」")
        print("-" * 60)
        
        try:
            streaming_result = Runner.run_streamed(
                starting_agent=coordinator_agent,
                input=test_input,
                context=user_context,
                max_turns=6
            )
            
            analyzer = StreamingEventAnalyzer()
            current_agent = coordinator_agent.name
            handoff_count = 0
            
            print(f"🎯 開始Agent: {current_agent}")
            print("🌊 実行フロー:")
            
            async for event in streaming_result.stream_events():
                analyzer.record_event(event)
                
                if event.type == "raw_response_event":
                    # ハンドオフ中は生テキスト表示を控える
                    if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                        print("•", end="", flush=True)
                        
                elif event.type == "agent_updated_stream_event":
                    handoff_count += 1
                    old_agent = current_agent
                    current_agent = event.new_agent.name
                    
                    print(f"\n🔄 ハンドオフ {handoff_count}: {old_agent} → {current_agent}")
                    
                elif event.type == "run_item_stream_event":
                    item = event.item
                    
                    if item.type == "tool_call_item":
                        tool_name = StreamingEventAnalyzer()._safe_tool_name(item)
                        print(f"\n🔧 [{current_agent}] {tool_name} 実行")
                        
                    elif item.type == "tool_call_output_item":
                        print(f"✅ [{current_agent}] ツール完了")
                        
                    elif "handoff" in item.type:
                        print(f"🚀 [{current_agent}] ハンドオフ処理")
            
            print(f"\n📊 ハンドオフ統計:")
            print(f"   開始Agent: {coordinator_agent.name}")
            print(f"   最終Agent: {current_agent}")
            print(f"   ハンドオフ回数: {handoff_count}")
            print(f"   処理時間: {analyzer.get_summary()['execution_time']:.2f}秒")
            
            # 最終結果
            final_result = streaming_result.final_output
            if final_result:
                print(f"💬 最終結果: {final_result}")
                
        except Exception as e:
            print(f"❌ ハンドオフストリーミングエラー: {str(e)}")


async def demonstrate_custom_streaming_ui(user_context: UserContext):
    """カスタムストリーミングUIデモ"""
    print("\n" + "="*80)
    print("🎨 4. カスタムストリーミングUIデモ")
    print("="*80)
    
    # UIフレンドリーなAgent
    ui_agent = Agent[UserContext](
        name="UI-Friendly Agent",
        instructions=(
            "ユーザーインターフェースに最適化された、"
            "段階的で視覚的に分かりやすい応答を提供します。"
            "進行状況を明確に示し、結果を構造化して表示します。"
        ),
        model="gpt-4o-mini",
        tools=[search_knowledge_base, generate_random_number, get_current_time],
        output_type=AgentOutputSchema(StreamingResponse, strict_json_schema=False),
    )
    
    test_input = "プログラミング学習について調べて、学習計画を立ててください"
    
    try:
        print(f"📝 UI最適化クエリ: 「{test_input}」")
        print("🎨 カスタムUI表示開始...")
        print("="*80)
        
        streaming_result = Runner.run_streamed(
            starting_agent=ui_agent,
            input=test_input,
            context=user_context,
            max_turns=5
        )
        
        # UIコンポーネント風の表示
        ui_state = {
            "current_phase": "初期化中...",
            "progress": 0,
            "generated_text": "",
            "tool_results": [],
            "status": "進行中"
        }
        
        total_expected_events = 50  # 概算
        event_count = 0
        
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 🤖 AI アシスタント - リアルタイム処理                                        │")
        print("├─────────────────────────────────────────────────────────────────────────────┤")
        
        async for event in streaming_result.stream_events():
            event_count += 1
            progress = min(100, (event_count / total_expected_events) * 100)
            ui_state["progress"] = progress
            
            if event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                    ui_state["generated_text"] += event.data.delta
                    ui_state["current_phase"] = "テキスト生成中..."
                    
                    # プログレスバー風表示
                    bar_length = 30
                    filled = int(bar_length * progress / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    print(f"\r│ 📊 進行状況: [{bar}] {progress:5.1f}% - {ui_state['current_phase']:<20} │", end="", flush=True)
                    
            elif event.type == "run_item_stream_event":
                item = event.item
                
                if item.type == "tool_call_item":
                    tool_name = StreamingEventAnalyzer()._safe_tool_name(item)
                    ui_state["current_phase"] = f"ツール実行: {tool_name}"
                    print(f"\n│ 🔧 {tool_name} を実行しています...                                      │")
                    
                elif item.type == "tool_call_output_item":
                    tool_name = getattr(getattr(item, 'raw_item', None), 'name', None) or getattr(item, 'tool_name', 'Unknown')
                    ui_state["tool_results"].append({
                        "name": tool_name,
                        "output": item.output[:60] + "..." if len(item.output) > 60 else item.output
                    })
                    ui_state["current_phase"] = "ツール結果処理中..."
                    print(f"│ ✅ ツール完了: {item.output[:50]}{'...' if len(item.output) > 50 else '':<50} │")
                    
                elif item.type == "message_output_item":
                    ui_state["current_phase"] = "応答完成"
                    print(f"│ 💬 メッセージ生成完了                                                      │")
        
        # 最終UI表示
        ui_state["status"] = "完了"
        ui_state["progress"] = 100
        
        print(f"\n├─────────────────────────────────────────────────────────────────────────────┤")
        print(f"│ 🎉 処理完了! ステータス: {ui_state['status']:<55} │")
        print(f"│ 📊 使用ツール数: {len(ui_state['tool_results']):<60} │")
        print(f"│ 📝 生成文字数: {len(ui_state['generated_text']):<58} │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 最終結果の整理表示
        final_result = streaming_result.final_output
        if final_result:
            print(f"\n📋 最終出力:")
            if hasattr(final_result, 'content'):
                print(f"   {final_result.content}")
            else:
                print(f"   {final_result}")
                
    except Exception as e:
        print(f"\n❌ カスタムUIストリーミングエラー: {str(e)}")


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            user_id="streaming_user_001",
            session_id="streaming_session_456",
            preferences={
                "ui_mode": "detailed",
                "streaming_speed": "normal",
                "show_progress": True
            }
        )
        
        print("🎪 OpenAI Agents SDK - Streaming 各要素 デモ")
        print("="*80)
        print(f"👤 ユーザーID: {user_context.user_id}")
        print(f"🔗 セッションID: {user_context.session_id}")
        print(f"⚙️ 設定: {user_context.preferences}")
        print("="*80)
        
        # 1. 基本的なストリーミングデモ
        #await demonstrate_basic_streaming(user_context)
        
        # 2. 高度なツールストリーミングデモ
        #await demonstrate_advanced_streaming_with_tools(user_context)
        
        # 3. ハンドオフストリーミングデモ
        await demonstrate_handoff_streaming(user_context)
        
        # 4. カスタムUIストリーミングデモ
        #await demonstrate_custom_streaming_ui(user_context)
        
        print(f"\n🎉 全ストリーミングデモンストレーション完了！")
        print("="*80)
        print("📚 学習内容まとめ:")
        print("✅ Runner.run_streamed() - ストリーミング実行")
        print("✅ RawResponsesStreamEvent - トークンレベルリアルタイム")
        print("✅ RunItemStreamEvent - 完了単位イベント")
        print("✅ AgentUpdatedStreamEvent - Agent変更イベント")
        print("✅ ItemHelpers - メッセージ抽出ヘルパー")
        print("✅ ストリーミング分析・統計")
        print("✅ カスタムUI実装")
        print("✅ リアルタイムプログレス表示")
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