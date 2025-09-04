#!/usr/bin/env python3
"""
OpenAI Agents SDK - Dynamic Instructions サンプルプログラム
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any

# OpenAI Agents SDK のインポート
try:
    from agents import Agent, Runner, RunContextWrapper, function_tool
except ImportError:
    print("エラー: OpenAI Agents SDKがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install openai-agents")
    sys.exit(1)


# ユーザーコンテキストの定義
@dataclass
class UserContext:
    name: str
    language: str
    level: str  # beginner, intermediate, advanced


# ツール関数の定義
@function_tool
def get_current_time() -> str:
    """現在の時刻を取得する"""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Dynamic Instructions関数
def dynamic_instructions(
    context: RunContextWrapper[UserContext], 
    agent: Agent[UserContext]
) -> str:
    """
    コンテキストに基づいて動的に指示を生成する関数
    """
    user = context.context
    
    # ユーザーの情報に基づいて指示をカスタマイズ
    instructions = f"""
あなたは{user.name}さん専用のアシスタントです。

ユーザー情報:
- 名前: {user.name}
- 使用言語: {user.language}
- レベル: {user.level}

以下の指示に従って回答してください:
1. {user.language}で回答してください
2. {user.level}レベルに合わせた説明をしてください
3. 常に丁寧で親しみやすい口調で話してください
4. 必要に応じて現在時刻ツールを使用してください
"""
    
    return instructions.strip()


def check_api_key():
    """OpenAI API キーの存在確認"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 OPENAI_API_KEY が設定されていません。")
        print("以下の方法で設定してください:")
        print("  Linux/Mac: export OPENAI_API_KEY='your-api-key-here'")
        print("  Windows: set OPENAI_API_KEY=your-api-key-here")
        return False
    
    if not api_key.startswith("sk-"):
        print("警告: API キーの形式が正しくない可能性があります。")
        print("OpenAI API キーは通常 'sk-' で始まります。")
    
    return True


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            name="田中さん",
            language="日本語",
            level="初心者"
        )
        
        # Dynamic Instructionを使用したAgentの作成
        agent = Agent[UserContext](
            name="Dynamic Assistant",
            instructions=dynamic_instructions,  # 関数を直接指定
            model="gpt-4o-mini",  # より安価なモデルを使用
            tools=[get_current_time],
        )
        
        print("=== OpenAI Agents SDK - Dynamic Instructions デモ ===")
        print(f"ユーザー: {user_context.name}")
        print(f"言語: {user_context.language}")
        print(f"レベル: {user_context.level}")
        print("-" * 50)
        
        # テスト用の質問リスト
        questions = [
            "こんにちは！今日の調子はどうですか？",
            "現在の時刻を教えてください",
            "プログラミングについて簡単に教えてください"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n質問 {i}: {question}")
            print("回答:")
            
            try:
                # Agentの実行
                result = await Runner.run(
                    agent, 
                    question, 
                    context=user_context
                )
                
                print(result.final_output)
                
            except Exception as e:
                print(f"エラーが発生しました: {str(e)}")
                print("詳細:", type(e).__name__)
        
        print("\n=== デモ終了 ===")
        
    except KeyboardInterrupt:
        print("\n\nプログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n予期しないエラーが発生しました: {str(e)}")
        print("詳細:", type(e).__name__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())