import os
import asyncio
import json
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from agents import (
    Agent, 
    Runner, 
    function_tool,
    RunContextWrapper
)
from agents.tracing import (
    trace,
    custom_span,
    function_span,
    generation_span,
    agent_span,
    guardrail_span,
    handoff_span,
    get_current_trace,
    get_current_span,
    add_trace_processor,
    set_trace_processors,
    TracingProcessor,
    Trace,
    Span
)

# 環境変数の読み込み
load_dotenv()

# エラーハンドリング: 環境変数の確認
def validate_environment():
    """環境変数が正しく設定されているか確認する"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEYが設定されていません。.envファイルに以下の形式で設定してください:\n"
            "OPENAI_API_KEY=your_api_key_here"
        )
    print(f"✅ OPENAI_API_KEY loaded (length: {len(api_key)})")

# 3-8. カスタムTraceプロセッサの実装
class CustomTraceProcessor(TracingProcessor):
    """カスタムトレースプロセッサ - ログに出力する例"""
    
    def __init__(self, name: str = "CustomLogger"):
        self.name = name
        self.traces = []
        self.spans = []
    
    def on_trace_start(self, trace: Trace) -> None:
        """トレース開始時の処理"""
        print(f"🚀 [{self.name}] Trace started: {trace.name} (ID: {trace.trace_id})")
        self.traces.append({
            "event": "trace_start",
            "trace_id": trace.trace_id,
            "workflow_name": trace.name,
            "timestamp": datetime.now().isoformat()
        })
    
    def on_trace_end(self, trace: Trace) -> None:
        """トレース終了時の処理"""
        print(f"✅ [{self.name}] Trace finished: {trace.name} (ID: {trace.trace_id})")
        self.traces.append({
            "event": "trace_end",
            "trace_id": trace.trace_id,
            "workflow_name": trace.name,
            "timestamp": datetime.now().isoformat()
        })
    
    def on_span_start(self, span: Span[Any]) -> None:
        """スパン開始時の処理"""
        span_type = type(span.span_data).__name__ if hasattr(span, 'span_data') else "Unknown"
        print(f"  📊 [{self.name}] Span started: {span_type} (ID: {span.span_id})")
        self.spans.append({
            "event": "span_start",
            "span_id": span.span_id,
            "span_type": span_type,
            "trace_id": span.trace_id if hasattr(span, 'trace_id') else None,
            "timestamp": datetime.now().isoformat()
        })
    
    def on_span_end(self, span: Span[Any]) -> None:
        """スパン終了時の処理"""
        span_type = type(span.span_data).__name__ if hasattr(span, 'span_data') else "Unknown"
        print(f"  ✅ [{self.name}] Span finished: {span_type} (ID: {span.span_id})")
        self.spans.append({
            "event": "span_end",
            "span_id": span.span_id,
            "span_type": span_type,
            "trace_id": span.trace_id if hasattr(span, 'trace_id') else None,
            "timestamp": datetime.now().isoformat()
        })
    
    def shutdown(self) -> None:
        """プロセッサのシャットダウン処理"""
        print(f"🔄 [{self.name}] Processor shutting down")
        print(f"📈 Total traces processed: {len([t for t in self.traces if t['event'] == 'trace_start'])}")
        print(f"📊 Total spans processed: {len([s for s in self.spans if s['event'] == 'span_start'])}")

    def force_flush(self) -> None:
        """即時フラッシュ（バッファは保持していないためログ出力のみ）"""
        print(f"🧹 [{self.name}] Force flush invoked (no pending buffers)")

# JSONファイルに出力するカスタムプロセッサ
class JSONExportProcessor(TracingProcessor):
    """トレース情報をJSONファイルに保存するプロセッサ"""
    
    def __init__(self, filename: str = "trace_export.json"):
        self.filename = filename
        self.data = {"traces": [], "spans": []}
    
    def on_trace_start(self, trace: Trace) -> None:
        self.data["traces"].append({
            "event": "start",
            "trace_id": trace.trace_id,
            "workflow_name": trace.name,
            "group_id": getattr(trace, 'group_id', None),
            "timestamp": datetime.now().isoformat()
        })
    
    def on_trace_end(self, trace: Trace) -> None:
        self.data["traces"].append({
            "event": "end",
            "trace_id": trace.trace_id,
            "workflow_name": trace.name,
            "timestamp": datetime.now().isoformat()
        })
        # ファイルに保存
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def on_span_start(self, span: Span[Any]) -> None:
        self.data["spans"].append({
            "event": "start",
            "span_id": span.span_id,
            "trace_id": getattr(span, 'trace_id', None),
            "timestamp": datetime.now().isoformat()
        })
    
    def on_span_end(self, span: Span[Any]) -> None:
        self.data["spans"].append({
            "event": "end",
            "span_id": span.span_id,
            "trace_id": getattr(span, 'trace_id', None),
            "timestamp": datetime.now().isoformat()
        })
    
    def shutdown(self) -> None:
        print(f"💾 JSONExportProcessor: データを{self.filename}に保存しました")

    def force_flush(self) -> None:
        """保持中データを即時にファイルへ書き出す"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"💾 JSONExportProcessor: force flushed -> {self.filename}")

# ユーザーコンテキストの定義
@dataclass
class UserContext:
    user_name: str
    user_id: int
    preferences: dict

# 3-6. 各種Spanを使用したツール関数の定義
@function_tool
async def get_weather(ctx: RunContextWrapper[UserContext], city: str) -> str:
    """指定された都市の天気情報を取得する
    
    Args:
        city: 天気を取得したい都市名
    """
    # 3-6. function_spanを使用した関数の追跡
    with function_span(name="weather_api_call", input=f"city: {city}") as span:
        # 模擬的な処理
        await asyncio.sleep(0.1)  # API呼び出しのシミュレート
        weather_data = f"{city}の天気: 晴れ、気温25度"
        span.span_data.output = weather_data
        print(f"  🌤️  Weather API called for {city}")
        return weather_data

@function_tool 
async def analyze_sentiment(ctx: RunContextWrapper[UserContext], text: str) -> str:
    """テキストの感情分析を行う
    
    Args:
        text: 分析対象のテキスト
    """
    # カスタムスパンの使用例
    with custom_span(
        name="sentiment_analysis",
        data={"input_text": text, "model": "sentiment-v1.0"}
    ) as span:
        await asyncio.sleep(0.2)  # 処理のシミュレート
        sentiment = "positive" if "good" in text.lower() else "neutral"
        span.span_data.data["result"] = sentiment
        print(f"  😊 Sentiment analysis completed: {sentiment}")
        return f"感情分析結果: {sentiment}"

@function_tool
async def security_check(ctx: RunContextWrapper[UserContext], content: str) -> str:
    """セキュリティチェックを行う（Guardrailの例）
    
    Args:
        content: チェック対象のコンテンツ
    """
    # 3-6. guardrail_spanの使用例
    triggered = "危険" in content or "禁止" in content
    
    with guardrail_span(name="security_guardrail", triggered=triggered) as span:
        if triggered:
            print(f"  🚨 Security check triggered for content")
            return "セキュリティチェックに引っかかりました。内容を確認してください。"
        else:
            print(f"  ✅ Security check passed")
            return "セキュリティチェック通過"

# エージェントの定義
def create_main_agent():
    """メインエージェントを作成"""
    return Agent(
        name="MainAssistant",
        instructions="""
あなたは親切なアシスタントです。
ユーザーからの質問に対して、利用可能なツールを使用して回答してください。
""",
        tools=[get_weather, analyze_sentiment, security_check]
    )

def create_specialized_agent():
    """専門的な処理を行うエージェント"""
    return Agent(
        name="SpecializedAgent", 
        instructions="特別な処理を担当するエージェントです。"
    )

# 3-7. 機密データの処理例
async def handle_sensitive_data_example():
    """機密データを含む処理の例"""
    print("\n=== 3-7. 機密データの処理例 ===")
    
    # 機密データを含むスパンの例
    sensitive_input = "ユーザーのパスワード: secret123"
    
    # generation_spanを使用（機密データを含む可能性）
    with generation_span(
        input=[{"role": "user", "content": "パスワードをチェックして"}],
        model="gpt-4",
        model_config={"temperature": 0.1}
    ) as span:
        # 実際のLLM呼び出しの代わりにシミュレート
        await asyncio.sleep(0.1)
        output_message = {"role": "assistant", "content": "パスワードは安全です"}
        span.span_data.output = [output_message]
        span.span_data.usage = {"input_tokens": 10, "output_tokens": 5}
        print("  🔒 Generation span with sensitive data created")

# 3-4. 上位レベルのTraceの例
async def high_level_trace_example():
    """複数のエージェント実行を1つのトレースでまとめる例"""
    print("\n=== 3-4. 上位レベルのTrace例 ===")
    
    agent = create_main_agent()
    user_context = UserContext(
        user_name="田中太郎", 
        user_id=123,
        preferences={"language": "ja"}
    )
    
    # 3-4&3-5. 複数の処理を1つのトレースでまとめる
    with trace("Weather Analysis Workflow", group_id="session_001", metadata={
        "user_id": user_context.user_id,
        "session_type": "weather_consultation"
    }) as main_trace:
        print(f"📋 Main trace started: {main_trace.trace_id}")
        
        # 最初のエージェント実行
        first_result = await Runner.run(
            starting_agent=agent,
            input="東京の天気を教えて",
            context=user_context
        )
        
        # カスタムスパンで中間処理
        with custom_span("weather_processing", data={"step": "analysis"}) as analysis_span:
            await asyncio.sleep(0.1)
            analysis_span.span_data.data["result"] = "weather_processed"
            print("  🔍 Weather analysis completed")
        
        # 2番目のエージェント実行
        second_result = await Runner.run(
            starting_agent=agent,
            input=f"この天気について感想を分析して: {first_result.final_output}",
            context=user_context
        )
        
        print(f"🌤️ 1回目の結果: {first_result.final_output}")
        print(f"😊 2回目の結果: {second_result.final_output}")

# 3-6. Handoff Spanの例  
async def handoff_example():
    """エージェント間のHandoffの例"""
    print("\n=== 3-6. Handoff Span例 ===")
    
    main_agent = create_main_agent()
    specialized_agent = create_specialized_agent()
    
    with trace("Agent Handoff Workflow") as handoff_trace:
        # Handoffスパンの作成
        with handoff_span(
            from_agent="MainAssistant",
            to_agent="SpecializedAgent"
        ) as h_span:
            print("  🔄 Handoff from MainAssistant to SpecializedAgent")
            await asyncio.sleep(0.1)
            
        # 実際のエージェント処理をシミュレート
        with agent_span(
            name="SpecializedAgent",
            tools=["specialized_tool"],
            output_type="analysis_result"
        ) as a_span:
            print("  🤖 SpecializedAgent processing...")
            await asyncio.sleep(0.2)

# メイン処理
async def main():
    """メイン実行関数"""
    try:
        # 環境変数の検証
        validate_environment()
        
        print("🚀 OpenAI Agents SDK - Tracing Sample Started")
        print("=" * 60)
        
        # 3-8. カスタムTraceプロセッサの設定
        print("\n=== 3-8. カスタムTraceプロセッサの設定 ===")
        custom_processor = CustomTraceProcessor("MyCustomLogger")
        json_processor = JSONExportProcessor("agents_trace_log.json")
        
        # プロセッサを追加（既存のOpenAIプロセッサに加えて）
        add_trace_processor(custom_processor)
        add_trace_processor(json_processor)
        
        print("✅ カスタムプロセッサが追加されました")
        
        # 3-3. デフォルトのTrace例（単一エージェント実行）
        print("\n=== 3-3. デフォルトのTrace例 ===")
        agent = create_main_agent()
        user_context = UserContext("山田花子", 456, {"theme": "casual"})
        
        result = await Runner.run(
            starting_agent=agent,
            input="大阪の天気を教えて、セキュリティチェックもお願いします",
            context=user_context
        )
        print(f"🎯 結果: {result.final_output}")
        
        # 上位レベルのトレース例
        await high_level_trace_example()
        
        # Handoffの例
        await handoff_example()
        
        # 機密データの処理例
        await handle_sensitive_data_example()
        
        # 3-2. TraceとSpanの情報表示
        print("\n=== 3-2. 現在のTraceとSpan情報 ===")
        current_trace = get_current_trace()
        current_span = get_current_span()
        
        if current_trace:
            print(f"📋 Current Trace: {current_trace.trace_id}")
        if current_span:
            print(f"📊 Current Span: {current_span.span_id}")
        
        # プロセッサのシャットダウン
        custom_processor.shutdown()
        json_processor.shutdown()
        
        print("\n✅ すべてのTracing要素のデモが完了しました！")
        print("=" * 60)
        
    except ValueError as e:
        print(f"❌ 設定エラー: {e}")
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        print("詳細なエラー情報:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())