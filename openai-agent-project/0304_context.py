import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

# 必要に応じてimportを調整してください
from agents import Agent, RunContextWrapper, Runner, function_tool

# .envファイルから環境変数を読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """ローカルコンテキスト: ユーザー情報と実行時データを管理"""
    # ユーザー基本情報
    user_id: int
    username: str
    email: str
    
    # 実行時コンテキスト
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    
    # 依存関係とヘルパー
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # 実行状態の追跡
    tool_calls_count: int = 0
    
    def log_tool_call(self, tool_name: str) -> None:
        """ツール呼び出しをログに記録"""
        self.tool_calls_count += 1
        self.logger.info(f"Tool '{tool_name}' called (#{self.tool_calls_count}) for user {self.username}")


# ローカルコンテキストを使用するFunction Tools
@function_tool
async def get_user_profile(ctx: RunContextWrapper[UserContext]) -> str:
    """ユーザープロファイル情報を取得します。
    
    Args:
        ctx: ユーザーコンテキストのラッパー
        
    Returns:
        ユーザープロファイル情報の文字列
    """
    ctx.context.log_tool_call("get_user_profile")
    
    # ローカルコンテキストからユーザー情報を取得
    user = ctx.context
    profile_info = f"""
    ユーザープロファイル:
    - ユーザー名: {user.username}
    - メール: {user.email}
    - セッション開始: {user.start_time.strftime('%Y-%m-%d %H:%M:%S')}
    - 設定: {user.user_preferences}
    """
    
    return profile_info


@function_tool
async def update_user_preferences(
    ctx: RunContextWrapper[UserContext], 
    preference_key: str, 
    preference_value: str
) -> str:
    """ユーザーの設定を更新します。
    
    Args:
        ctx: ユーザーコンテキストのラッパー
        preference_key: 設定のキー
        preference_value: 設定の値
        
    Returns:
        更新結果のメッセージ
    """
    ctx.context.log_tool_call("update_user_preferences")
    
    # ローカルコンテキストのデータを更新
    ctx.context.user_preferences[preference_key] = preference_value
    
    return f"設定 '{preference_key}' を '{preference_value}' に更新しました。"


@function_tool
async def get_session_stats(ctx: RunContextWrapper[UserContext]) -> str:
    """現在のセッションの統計情報を取得します。
    
    Args:
        ctx: ユーザーコンテキストのラッパー
        
    Returns:
        セッション統計情報
    """
    ctx.context.log_tool_call("get_session_stats")
    
    user = ctx.context
    current_time = datetime.now()
    session_duration = current_time - user.start_time
    
    stats = f"""
    セッション統計:
    - セッションID: {user.session_id}
    - 経過時間: {session_duration.total_seconds():.1f}秒
    - ツール呼び出し回数: {user.tool_calls_count}
    - 現在時刻: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    return stats


def create_dynamic_instructions(ctx: UserContext) -> str:
    """Agent/LLMコンテキスト: 動的なシステムプロンプトを生成"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    instructions = f"""
あなたは親切なアシスタントです。以下の情報を念頭に置いて対応してください。

【現在のコンテキスト情報】
- 現在の日時: {current_time}
- ユーザー名: {ctx.username}
- セッション開始: {ctx.start_time.strftime('%Y-%m-%d %H:%M:%S')}

【利用可能な機能】
- get_user_profile: ユーザープロファイル情報の取得
- update_user_preferences: ユーザー設定の更新
- get_session_stats: セッション統計の確認

【対応方針】
1. ユーザーの名前を使って親しみやすく対応する
2. 必要に応じてツールを使用してコンテキスト情報を活用する
3. ユーザーの設定や状態を考慮した回答を提供する
"""
    
    return instructions


async def main():
    """メイン関数: コンテキスト管理のデモンストレーション"""
    
    # 環境変数の確認
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("OPENAI_API_KEY環境変数が設定されていません。")
        print("エラー: .envファイルにOPENAI_API_KEYを設定してください。")
        return
    
    if not api_key.startswith('sk-'):
        logger.error("OPENAI_API_KEYの形式が正しくありません。")
        print("エラー: OPENAI_API_KEYの形式が正しくありません。")
        return
    
    try:
        # ローカルコンテキストの作成
        user_context = UserContext(
            user_id=12345,
            username="田中太郎",
            email="tanaka@example.com",
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_preferences={
                "language": "japanese",
                "theme": "light",
                "notifications": "enabled"
            }
        )
        
        logger.info(f"ユーザーコンテキストを作成: {user_context.username}")
        
        # Agent作成 - Agent/LLMコンテキスト（動的なシステムプロンプト）
        agent = Agent[UserContext](
            name="ContextAwareAssistant",
            instructions=create_dynamic_instructions(user_context),  # 動的な指示
            tools=[
                get_user_profile,
                update_user_preferences,
                get_session_stats
            ]
        )
        
        print("=== OpenAI Agents SDK コンテキスト管理デモ ===")
        print(f"ユーザー: {user_context.username}")
        print(f"セッション: {user_context.session_id}")
        print()
        
        # 複数のインタラクションを実行
        interactions = [
            "こんにちは！私の情報を教えてください。",
            "通知設定をdisabledに変更してください。",
            "現在のセッション情報を確認したいです。",
            "私の現在の設定を再度確認してください。"
        ]
        
        for i, user_input in enumerate(interactions, 1):
            print(f"--- インタラクション {i} ---")
            print(f"ユーザー: {user_input}")
            
            # Agent/LLMコンテキスト: 追加情報を入力として渡す
            enhanced_input = f"{user_input}\n\n[追加コンテキスト] 現在のツール呼び出し回数: {user_context.tool_calls_count}"
            
            # Agentの実行（ローカルコンテキストを渡す）
            result = await Runner.run(
                starting_agent=agent,
                input=enhanced_input,
                context=user_context  # ローカルコンテキストを渡す
            )
            
            print(f"アシスタント: {result.final_output}")
            print()
        
        # 最終状態の確認
        print("=== 最終状態 ===")
        print(f"合計ツール呼び出し回数: {user_context.tool_calls_count}")
        print(f"更新された設定: {user_context.user_preferences}")
        
        logger.info("デモンストレーション完了")
        
    except Exception as e:
        logger.error(f"実行エラー: {str(e)}")
        print(f"エラーが発生しました: {str(e)}")
        print("APIキーが正しく設定されているか、ネットワーク接続を確認してください。")


if __name__ == "__main__":
    asyncio.run(main())