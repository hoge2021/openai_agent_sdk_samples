#!/usr/bin/env python3
"""
OpenAI Agents SDK - ライフサイクルイベント（フック）サンプルプログラム
"""

import asyncio
import os
import sys
import datetime
from dataclasses import dataclass
from typing import Any, Optional, List

# OpenAI Agents SDK のインポート
try:
    from agents import (
        Agent, 
        Runner, 
        RunContextWrapper, 
        function_tool,
        AgentHooks,
        RunHooks,
        Tool,
        ModelResponse
    )
    from agents.items import TResponseInputItem
except ImportError:
    print("エラー: OpenAI Agents SDKがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install openai-agents")
    sys.exit(1)


# ユーザーコンテキストの定義
@dataclass
class UserContext:
    name: str
    session_id: str


# ツール関数の定義
@function_tool
def get_current_time() -> str:
    """現在の時刻を取得する"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def calculate_sum(a: int, b: int) -> str:
    """2つの数値の合計を計算する"""
    result = a + b
    return f"{a} + {b} = {result}"


# カスタムAgentフッククラス
class CustomAgentHooks(AgentHooks):
    """特定のAgentに対するライフサイクルイベントを監視するフック"""
    
    async def on_start(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext]
    ) -> None:
        """Agent開始時に呼び出される"""
        user = context.context
        print(f"🚀 [Agent Hook] Agent '{agent.name}' が開始されました")
        print(f"   ユーザー: {user.name} (セッション: {user.session_id})")
        
    async def on_end(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        output: Any
    ) -> None:
        """Agent終了時に呼び出される"""
        print(f"✅ [Agent Hook] Agent '{agent.name}' が終了しました")
        print(f"   出力タイプ: {type(output).__name__}")
        
    async def on_tool_start(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        tool: Tool
    ) -> None:
        """ツール実行開始時に呼び出される"""
        print(f"🔧 [Agent Hook] ツール '{tool.name}' の実行を開始")
        
    async def on_tool_end(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        tool: Tool, 
        result: str
    ) -> None:
        """ツール実行終了時に呼び出される"""
        print(f"✨ [Agent Hook] ツール '{tool.name}' の実行が完了")
        print(f"   結果: {result[:50]}{'...' if len(result) > 50 else ''}")
        
    async def on_llm_start(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        system_prompt: Optional[str], 
        input_items: List[TResponseInputItem]
    ) -> None:
        """LLM呼び出し開始時に呼び出される"""
        print(f"🤖 [Agent Hook] LLM呼び出しを開始 (入力アイテム数: {len(input_items)})")
        
    async def on_llm_end(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        response: ModelResponse
    ) -> None:
        """LLM呼び出し終了時に呼び出される"""
        print(f"💭 [Agent Hook] LLM呼び出しが完了")


# カスタムRunフッククラス
class CustomRunHooks(RunHooks):
    """全体的なRun実行に対するライフサイクルイベントを監視するフック"""
    
    async def on_agent_start(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext]
    ) -> None:
        """Agent開始時に呼び出される（Run全体の視点から）"""
        print(f"🎯 [Run Hook] Run実行: Agent '{agent.name}' を開始")
        
    async def on_agent_end(
        self, 
        context: RunContextWrapper[UserContext], 
        agent: Agent[UserContext], 
        output: Any
    ) -> None:
        """Agent終了時に呼び出される（Run全体の視点から）"""
        print(f"🏁 [Run Hook] Run実行: Agent '{agent.name}' を終了")
        
    async def on_handoff(
        self, 
        context: RunContextWrapper[UserContext], 
        from_agent: Agent[UserContext], 
        to_agent: Agent[UserContext]
    ) -> None:
        """ハンドオフ発生時に呼び出される"""
        print(f"🔄 [Run Hook] ハンドオフ: '{from_agent.name}' → '{to_agent.name}'")


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


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            name="山田太郎",
            session_id="session_12345"
        )
        
        # カスタムフックの作成
        agent_hooks = CustomAgentHooks()
        run_hooks = CustomRunHooks()
        
        # ライフサイクルフックを使用したAgentの作成
        agent = Agent[UserContext](
            name="LifecycleDemo Agent",
            instructions=(
                "あなたは親切なアシスタントです。"
                "質問に答え、必要に応じてツールを使用してください。"
                "日本語で丁寧に回答してください。"
            ),
            model="gpt-4o-mini",
            tools=[get_current_time, calculate_sum],
            hooks=agent_hooks,  # Agent固有のフックを設定
        )
        
        print("=" * 60)
        print("🎪 OpenAI Agents SDK - ライフサイクルイベント（フック）デモ")
        print("=" * 60)
        print(f"ユーザー: {user_context.name}")
        print(f"セッション: {user_context.session_id}")
        print("-" * 60)
        
        # テスト用の質問リスト
        questions = [
            "こんにちは！よろしくお願いします",
            "現在の時刻を教えてください",
            "5 + 3 の計算をしてください"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n📝 質問 {i}: {question}")
            print("=" * 40)
            
            try:
                # Agentの実行（Run Hooksも同時に適用）
                result = await Runner.run(
                    agent,
                    question,
                    context=user_context,
                    hooks=run_hooks  # Run全体のフックを直接指定
                )
                
                print("=" * 40)
                print(f"💬 回答: {result.final_output}")
                print("=" * 40)
                
            except Exception as e:
                print(f"❌ エラーが発生しました: {str(e)}")
                print(f"エラー詳細: {type(e).__name__}")
                continue
        
        print("\n🎉 すべてのデモが完了しました！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  プログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {str(e)}")
        print(f"エラー詳細: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())