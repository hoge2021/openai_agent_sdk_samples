"""
OpenAI Agents SDK - Tools 各要素のサンプルプログラム
このプログラムは、OpenAI Agents SDKのToolsの主要な機能を包括的に示します。
"""

import os
import sys
import json
import asyncio
from typing import Any, TypedDict, Optional
from pydantic import BaseModel
from agents import (
    Agent, 
    Runner, 
    FunctionTool, 
    WebSearchTool,
    RunContextWrapper,
    function_tool
)
from agents.tool import default_tool_error_function


# ========================================
# 環境変数チェック
# ========================================
def check_environment():
    """環境変数にOPENAI_API_KEYが設定されているか確認"""
    if not os.environ.get("OPENAI_API_KEY"):
        print("エラー: 環境変数 'OPENAI_API_KEY' が設定されていません。")
        print("設定方法:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    print("✓ OPENAI_API_KEY が設定されています\n")


# ========================================
# 1. Function Tools (基本的な関数ツール)
# ========================================

# TypedDictを使用した型定義
class Location(TypedDict):
    lat: float
    long: float


@function_tool
async def fetch_weather(location: Location) -> str:
    """指定された場所の天気を取得します。
    
    Args:
        location: 緯度と経度を含む位置情報
    """
    try:
        # 実際にはAPIを呼び出しますが、ここではダミーデータを返します
        return f"晴れ、気温25℃、湿度60% (緯度: {location['lat']}, 経度: {location['long']})"
    except Exception as e:
        return f"天気情報の取得に失敗しました: {str(e)}"


# ========================================
# 2. Custom Function Tools (カスタム関数ツール)
# ========================================

# Pydanticモデルを使用したスキーマ定義
class UserDataArgs(BaseModel):
    username: str
    age: int
    email: Optional[str] = None


async def process_user_data(ctx: RunContextWrapper[Any], args: str) -> str:
    """ユーザーデータを処理する関数"""
    try:
        parsed = UserDataArgs.model_validate_json(args)
        # 実際の処理をここに記述
        result = f"ユーザー '{parsed.username}' (年齢: {parsed.age}) のデータを処理しました"
        if parsed.email:
            result += f" - Email: {parsed.email}"
        return result
    except Exception as e:
        return f"データ処理エラー: {str(e)}"


# カスタムFunctionToolの作成
custom_tool = FunctionTool(
    name="process_user",
    description="ユーザーデータを処理して検証します",
    params_json_schema=UserDataArgs.model_json_schema(),
    on_invoke_tool=process_user_data,
    strict_json_schema=True  # strictモードで正確なJSON入力を確保
)


# ========================================
# 3. エラーハンドリング付きツール
# ========================================

def custom_error_handler(ctx: RunContextWrapper[Any], error: Exception) -> str:
    """カスタムエラーハンドラー"""
    error_msg = f"エラーが発生しました: {type(error).__name__} - {str(error)}"
    print(f"[エラーログ] {error_msg}")
    return f"申し訳ございません。処理中にエラーが発生しました。別の方法をお試しください。"


@function_tool(
    name_override="calculate_with_error_handling",
    failure_error_function=custom_error_handler
)
def calculate(operation: str, a: float, b: float) -> str:
    """数値計算を実行します（エラーハンドリング付き）
    
    Args:
        operation: 実行する演算 (add, subtract, multiply, divide)
        a: 第一数値
        b: 第二数値
    """
    try:
        if operation == "add":
            return str(a + b)
        elif operation == "subtract":
            return str(a - b)
        elif operation == "multiply":
            return str(a * b)
        elif operation == "divide":
            if b == 0:
                raise ValueError("ゼロ除算エラー")
            return str(a / b)
        else:
            raise ValueError(f"未知の演算: {operation}")
    except Exception as e:
        raise  # エラーハンドラーに処理を委譲


# ========================================
# 4. コンテキスト付きツール
# ========================================

# コンテキストデータの定義
class AppContext(BaseModel):
    user_name: str
    session_id: str
    permissions: list[str]


@function_tool(use_docstring_info=True)
async def get_user_info(ctx: RunContextWrapper[AppContext]) -> str:
    """現在のユーザー情報を取得します
    
    このツールはコンテキストからユーザー情報を読み取ります
    """
    context = ctx.context
    permissions_str = ", ".join(context.permissions)
    return (f"ユーザー名: {context.user_name}\n"
            f"セッションID: {context.session_id}\n"
            f"権限: {permissions_str}")


# ========================================
# 5. 動的に有効/無効を切り替えるツール
# ========================================

def check_tool_enabled(ctx: RunContextWrapper[AppContext], agent: Agent) -> bool:
    """管理者権限がある場合のみツールを有効化"""
    return "admin" in ctx.context.permissions


@function_tool(is_enabled=check_tool_enabled)
async def admin_operation(action: str) -> str:
    """管理者専用の操作を実行します
    
    Args:
        action: 実行する管理操作
    """
    return f"管理操作 '{action}' を実行しました"


# ========================================
# 6. Agents as Tools (エージェントをツールとして使用)
# ========================================

# 専門エージェントの作成
translation_agent = Agent(
    name="翻訳エージェント",
    instructions="与えられたテキストを日本語から英語に翻訳してください。"
)

summary_agent = Agent(
    name="要約エージェント", 
    instructions="与えられたテキストを簡潔に要約してください。"
)


# ========================================
# メインエージェントの設定と実行
# ========================================

async def main():
    """メイン実行関数"""
    
    print("=" * 50)
    print("OpenAI Agents SDK - Tools サンプルプログラム")
    print("=" * 50 + "\n")
    
    # 環境変数チェック
    check_environment()
    
    try:
        # コンテキストの準備
        app_context = AppContext(
            user_name="田中太郎",
            session_id="session_123",
            permissions=["read", "write", "admin"]
        )
        
        # 1. Hosted Tools（WebSearchTool）を含むエージェント
        print("1. Hosted Tools の例:")
        print("-" * 30)
        search_agent = Agent(
            name="検索アシスタント",
            instructions="ユーザーの質問に対してWeb検索を活用して回答してください。",
            tools=[WebSearchTool()]
        )
        
        # 2. Function Tools を使用するエージェント
        print("\n2. Function Tools の例:")
        print("-" * 30)
        
        main_agent = Agent[AppContext](
            name="メインアシスタント",
            instructions=(
                "あなたは万能アシスタントです。"
                "利用可能なツールを活用してユーザーの要求に対応してください。"
            ),
            tools=[
                fetch_weather,      # 基本的な関数ツール
                custom_tool,        # カスタム関数ツール
                calculate,          # エラーハンドリング付きツール
                get_user_info,      # コンテキスト付きツール
                admin_operation,    # 条件付き有効化ツール
                # エージェントをツールとして追加
                translation_agent.as_tool(
                    tool_name="translate_to_english",
                    tool_description="テキストを英語に翻訳する"
                ),
                summary_agent.as_tool(
                    tool_name="summarize_text",
                    tool_description="テキストを要約する"
                )
            ]
        )
        
        # ツール情報の表示
        print("利用可能なツール一覧:")
        for tool in main_agent.tools:
            if isinstance(tool, FunctionTool):
                print(f"  - {tool.name}: {tool.description}")
                if hasattr(tool, 'params_json_schema'):
                    print(f"    パラメータスキーマ:")
                    print(f"    {json.dumps(tool.params_json_schema, indent=6, ensure_ascii=False)}")
        
        print("\n" + "=" * 50)
        print("テスト実行:")
        print("=" * 50 + "\n")
        
        # テスト1: 天気情報の取得
        print("テスト1: 天気情報の取得")
        result1 = await Runner.run(
            starting_agent=main_agent,
            input="東京（緯度35.6762、経度139.6503）の天気を教えてください",
            context=app_context
        )
        print(f"結果: {result1.final_output}\n")
        
        # テスト2: 計算（エラーハンドリングのテスト）
        print("テスト2: 計算機能")
        result2 = await Runner.run(
            starting_agent=main_agent,
            input="10を3で割った値を計算してください",
            context=app_context
        )
        print(f"結果: {result2.final_output}\n")
        
        # テスト3: ユーザー情報の取得
        print("テスト3: コンテキストからの情報取得")
        result3 = await Runner.run(
            starting_agent=main_agent,
            input="現在のユーザー情報を教えてください",
            context=app_context
        )
        print(f"結果: {result3.final_output}\n")
        
        # テスト4: 翻訳機能（エージェントをツールとして使用）
        print("テスト4: 翻訳機能")
        result4 = await Runner.run(
            starting_agent=main_agent,
            input="「こんにちは、今日は良い天気ですね」を英語に翻訳してください",
            context=app_context
        )
        print(f"結果: {result4.final_output}\n")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {type(e).__name__}")
        print(f"詳細: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # イベントループの実行
    asyncio.run(main())