"""
OpenAI Agents SDK - コンテキストを使用したサンプルプログラム

このプログラムでは、ユーザーのコンテキスト情報（プロフィールや設定）を
エージェントやツールで共有して利用する方法を示します。
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from agents import Agent, Runner, function_tool, ModelSettings
from agents import RunContextWrapper

# ========================================
# 1. コンテキストの定義
# ========================================
@dataclass
class UserContext:
    """ユーザーのコンテキスト情報を保持するクラス"""
    name: str                    # ユーザー名
    user_id: str                 # ユーザーID
    language: str                # 優先言語
    is_premium_user: bool        # プレミアムユーザーかどうか
    location: str                # 現在地
    preferences: dict            # その他の設定
    purchase_history: List[str] = None  # 購入履歴
    
    def __post_init__(self):
        if self.purchase_history is None:
            self.purchase_history = []


# ========================================
# 2. コンテキストを使用するツールの定義
# ========================================
@function_tool
def get_personalized_recommendation(
    context: RunContextWrapper[UserContext],
    category: str
) -> str:
    """
    ユーザーのコンテキストを使用して、パーソナライズされたレコメンドを生成
    """
    user = context.context
    
    # プレミアムユーザーには特別なレコメンドを提供
    if user.is_premium_user:
        recommendations = {
            "food": f"{user.name}様、{user.location}近くの高級レストランをお勧めします",
            "shopping": f"プレミアム会員限定の特別セールがあります",
            "entertainment": f"VIPイベントへのアクセスが可能です"
        }
    else:
        recommendations = {
            "food": f"{user.location}エリアの人気レストランをご紹介",
            "shopping": f"今週のお得な商品情報",
            "entertainment": f"無料で楽しめるイベント情報"
        }
    
    return recommendations.get(category, "該当するレコメンドが見つかりません")


@function_tool
def check_purchase_history(
    context: RunContextWrapper[UserContext]
) -> str:
    """ユーザーの購入履歴を確認"""
    user = context.context
    
    if not user.purchase_history:
        return f"{user.name}様の購入履歴はまだありません"
    
    history_text = ", ".join(user.purchase_history[:5])  # 最新5件
    return f"{user.name}様の最近の購入: {history_text}"


@function_tool
def get_user_status(
    context: RunContextWrapper[UserContext]
) -> str:
    """ユーザーのステータス情報を取得"""
    user = context.context
    
    status = f"""
    ユーザー情報:
    - 名前: {user.name}
    - ID: {user.user_id}
    - ステータス: {'プレミアム' if user.is_premium_user else 'スタンダード'}
    - 言語設定: {user.language}
    - 現在地: {user.location}
    """
    return status.strip()


# ========================================
# 3. 動的なinstructionsの定義
# ========================================
def dynamic_instructions(
    context: RunContextWrapper[UserContext], 
    agent: Agent[UserContext]
) -> str:
    """コンテキストに基づいて動的にinstructionsを生成"""
    user = context.context
    
    # ユーザーの言語設定に基づいてinstructionsを調整
    base_instructions = f"""
    あなたは{user.name}様専用のパーソナルアシスタントです。
    
    ユーザー情報:
    - 現在地: {user.location}
    - 会員ステータス: {'プレミアム' if user.is_premium_user else 'スタンダード'}
    - 優先言語: {user.language}
    
    以下の点に注意してください:
    1. {user.language}で応答してください
    2. {user.name}様の好みや履歴を考慮した提案を行ってください
    3. {'プレミアム会員特典を積極的に活用してください' if user.is_premium_user else '無料で利用できるサービスを中心に提案してください'}
    """
    
    return base_instructions


# ========================================
# 4. エージェントの作成
# ========================================
def create_personalized_agent() -> Agent[UserContext]:
    """パーソナライズされたエージェントを作成"""
    
    agent = Agent[UserContext](
        name="Personal Assistant",
        instructions=dynamic_instructions,  # 動的instructions
        model="gpt-4o-mini",  # または "o3-mini"
        model_settings=ModelSettings(
            temperature=0.7,
            max_tokens=1000
        ),
        tools=[
            get_personalized_recommendation,
            check_purchase_history,
            get_user_status
        ]
    )
    
    return agent


# ========================================
# 5. メイン実行関数
# ========================================
async def run_example():
    """サンプルの実行"""
    
    # ユーザーコンテキストの作成
    user_context = UserContext(
        name="田中太郎",
        user_id="user_12345",
        language="日本語",
        is_premium_user=True,
        location="東京",
        preferences={
            "cuisine": "和食",
            "shopping": "エレクトロニクス"
        },
        purchase_history=["ノートPC", "ワイヤレスイヤホン", "スマートウォッチ"]
    )
    
    # エージェントの作成
    agent = create_personalized_agent()
    
    # 複数の質問でエージェントをテスト
    questions = [
        "私のステータスを教えてください",
        "食事のレコメンドをお願いします",
        "私の購入履歴を確認してください",
        "ショッピングのおすすめはありますか？"
    ]
    
    print("=" * 50)
    print("OpenAI Agents SDK - コンテキスト使用デモ")
    print("=" * 50)
    
    for question in questions:
        print(f"\n質問: {question}")
        print("-" * 30)
        
        # エージェントの実行（コンテキストを渡す）
        result = await Runner.run(
            agent, 
            question,
            context=user_context  # ここでコンテキストを渡す
        )
        
        print(f"回答: {result.final_output}")
        
        # 使用されたツールの表示
        if result.new_items:
            tool_calls = [item for item in result.new_items 
                         if hasattr(item, 'type') and 'tool' in item.type]
            if tool_calls:
                print(f"使用ツール: {len(tool_calls)}個")


# ========================================
# 6. 複数ユーザーのシミュレーション
# ========================================
async def multi_user_example():
    """複数のユーザーコンテキストでの実行例"""
    
    # 異なるユーザーコンテキストを作成
    users = [
        UserContext(
            name="山田花子",
            user_id="user_11111",
            language="日本語",
            is_premium_user=False,
            location="大阪",
            preferences={"cuisine": "イタリアン"},
            purchase_history=["書籍", "文房具"]
        ),
        UserContext(
            name="John Smith",
            user_id="user_22222", 
            language="English",
            is_premium_user=True,
            location="Tokyo",
            preferences={"cuisine": "Sushi"},
            purchase_history=["Camera", "Laptop", "Headphones"]
        )
    ]
    
    agent = create_personalized_agent()
    
    print("\n" + "=" * 50)
    print("複数ユーザーでのコンテキスト切り替えデモ")
    print("=" * 50)
    
    for user in users:
        print(f"\n【ユーザー: {user.name}】")
        
        # 各ユーザーのコンテキストでエージェントを実行
        result = await Runner.run(
            agent,
            "私に合ったレコメンドをください",
            context=user
        )
        
        print(f"回答: {result.final_output}")


# ========================================
# 7. プログラムのエントリーポイント
# ========================================
async def main():
    """メインプログラム"""
    
    try:
        # 基本的な例を実行
        await run_example()

        # 複数ユーザーの例を実行
        await multi_user_example()

    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    # 非同期プログラムの実行
    asyncio.run(main())