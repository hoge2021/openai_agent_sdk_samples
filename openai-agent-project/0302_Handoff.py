"""
OpenAI Agents SDK - Handoff 各要素のサンプルプログラム
このプログラムは、エージェント間のタスク委譲（Handoff）機能を包括的に示します。
"""

import os
import sys
import asyncio
from typing import Optional, Any
from pydantic import BaseModel
from agents import (
    Agent, 
    Runner,
    RunContextWrapper,
    handoff,
    function_tool
)
from agents import HandoffInputData
from agents.extensions.handoff_prompt import (
    RECOMMENDED_PROMPT_PREFIX,
    prompt_with_handoff_instructions
)
from agents.extensions import handoff_filters


# ========================================
# 環境変数チェック
# ========================================
def check_environment():
    """環境変数にOPENAI_API_KEYが設定されているか確認"""
    if not os.environ.get("OPENAI_API_KEY"):
        print("エラー: 環境変数 'OPENAI_API_KEY' が設定されていません。")
        print("設定方法:")
        print("  Linux/Mac: export OPENAI_API_KEY='your-api-key-here'")
        print("  Windows: set OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    print("✓ OPENAI_API_KEY が設定されています\n")


# ========================================
# コンテキストデータの定義
# ========================================
class CustomerContext(BaseModel):
    """カスタマーサポートのコンテキスト情報"""
    customer_name: str
    customer_id: str
    subscription_tier: str  # "free", "standard", "premium"
    issue_category: Optional[str] = None


# ========================================
# 2-3. Handoff の入力データ定義
# ========================================
class EscalationData(BaseModel):
    """エスカレーション時のデータ"""
    reason: str
    priority: str  # "low", "medium", "high", "urgent"
    previous_attempts: int


class RefundRequestData(BaseModel):
    """返金リクエストのデータ"""
    order_id: str
    reason: str
    amount: float


# ========================================
# 2-2. 専門エージェントの作成
# ========================================

# FAQエージェント（基本的な質問に回答）
faq_agent = Agent(
    name="FAQエージェント",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}"  # 2-5. 推奨プロンプト使用
        "あなたはFAQ担当のサポートエージェントです。"
        "よくある質問に対して丁寧に回答してください。"
        "回答できない質問の場合は、適切なエージェントへの引き継ぎを提案してください。"
    )
)

# 注文管理エージェント
order_agent = Agent(
    name="注文管理エージェント",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}"
        "あなたは注文管理担当のエージェントです。"
        "注文の確認、変更、キャンセルなどを処理します。"
        "顧客の注文に関する問い合わせに対応してください。"
    )
)

# 返金処理エージェント（入力データ付き）
refund_agent = Agent(
    name="返金処理エージェント",
    instructions=(
        "あなたは返金処理の専門エージェントです。"
        "返金ポリシーに従って返金リクエストを処理してください。"
        "返金理由と金額を確認し、適切に対応してください。"
    )
)

# 上級サポートエージェント（エスカレーション用）
senior_support_agent = Agent(
    name="上級サポートエージェント",
    instructions=(
        "あなたは上級サポートエージェントです。"
        "複雑な問題や他のエージェントでは解決できない問題を処理します。"
        "エスカレーションの理由と優先度を確認して対応してください。"
    )
)

# 技術サポートエージェント
tech_support_agent = Agent(
    name="技術サポートエージェント",
    instructions=(
        "あなたは技術サポートの専門エージェントです。"
        "技術的な問題、バグ、製品の不具合などに対応します。"
        "詳細な技術情報を提供し、問題解決をサポートしてください。"
    )
)


# ========================================
# Handoffのコールバック関数
# ========================================

async def on_refund_handoff(
    ctx: RunContextWrapper[CustomerContext], 
    input_data: RefundRequestData
):
    """返金エージェントへの引き継ぎ時のコールバック"""
    print(f"\n[システムログ] 返金処理への引き継ぎ:")
    print(f"  - 顧客名: {ctx.context.customer_name}")
    print(f"  - 注文ID: {input_data.order_id}")
    print(f"  - 返金理由: {input_data.reason}")
    print(f"  - 金額: ¥{input_data.amount:,.0f}")
    
    # ここで実際の返金処理の初期化やログ記録を行う
    # 例: データベースへの記録、承認フローの開始など


async def on_escalation_handoff(
    ctx: RunContextWrapper[CustomerContext],
    input_data: EscalationData
):
    """エスカレーション時のコールバック"""
    print(f"\n[システムログ] エスカレーション発生:")
    print(f"  - 顧客: {ctx.context.customer_name} (ID: {ctx.context.customer_id})")
    print(f"  - 理由: {input_data.reason}")
    print(f"  - 優先度: {input_data.priority}")
    print(f"  - 過去の試行回数: {input_data.previous_attempts}")
    
    # 優先度に応じた処理
    if input_data.priority == "urgent":
        print("  ⚠️ 緊急対応が必要です！")


def on_simple_handoff(ctx: RunContextWrapper[CustomerContext]):
    """シンプルな引き継ぎ時のコールバック"""
    print(f"\n[システムログ] エージェント切り替え")
    print(f"  - 顧客: {ctx.context.customer_name}")
    print(f"  - サブスクリプション: {ctx.context.subscription_tier}")


# ========================================
# 2-4. Input Filters の定義
# ========================================

def filter_remove_sensitive_info(data: HandoffInputData) -> HandoffInputData:
    """機密情報を除去するフィルター

    注意: HandoffInputData は `messages` を持たないため、
    `input_history`/`pre_handoff_items`/`new_items` をそのまま返します。
    実際の機密情報除去を行う場合は、これらの構造体内（特に `input_history` がタプルのときの各アイテム）
    をパースして加工してください。
    """
    return HandoffInputData(
        input_history=data.input_history,
        pre_handoff_items=data.pre_handoff_items,
        new_items=data.new_items,
        run_context=data.run_context,
    )


def filter_summary_only(data: HandoffInputData) -> HandoffInputData:
    """会話の要約のみを渡すフィルター

    `input_history` がタプル（履歴アイテム列）の場合は末尾3件にトリム。
    文字列（要約テキスト等）の場合はそのまま返します。
    他の項目は変更しません。
    """
    if isinstance(data.input_history, tuple):
        trimmed_history = data.input_history[-3:]
    else:
        trimmed_history = data.input_history

    return HandoffInputData(
        input_history=trimmed_history,
        pre_handoff_items=data.pre_handoff_items,
        new_items=data.new_items,
        run_context=data.run_context,
    )


# ========================================
# メイントリアージエージェントの作成
# ========================================

triage_agent = Agent[CustomerContext](
    name="トリアージエージェント",
    instructions=prompt_with_handoff_instructions(
        """あなたはカスタマーサポートのトリアージ（振り分け）エージェントです。
        
        顧客の問い合わせを適切に判断し、専門のエージェントに引き継いでください：
        
        1. よくある質問 → FAQエージェント
        2. 注文に関する問い合わせ → 注文管理エージェント
        3. 返金リクエスト → 返金処理エージェント（注文IDと理由を添えて）
        4. 技術的な問題 → 技術サポートエージェント
        5. 複雑/緊急の問題 → 上級サポートエージェント（エスカレーション理由を添えて）
        
        顧客のサブスクリプションレベルも考慮してください：
        - Premium顧客は優先対応
        - 複数回の問い合わせは上級サポートへエスカレーション
        """
    ),
    handoffs=[
        # 2-2. 基本的なHandoff（エージェント直接指定）
        faq_agent,
        
        # 2-2. カスタマイズされたHandoff（名前とコールバック付き）
        handoff(
            agent=order_agent,
            tool_name_override="transfer_to_order_support",
            tool_description_override="注文関連の問い合わせを処理する専門エージェントに引き継ぐ",
            on_handoff=on_simple_handoff
        ),
        
        # 2-3. 入力データ付きHandoff（返金処理）
        handoff(
            agent=refund_agent,
            tool_name_override="process_refund_request",
            tool_description_override="返金リクエストを処理する（注文IDと理由が必要）",
            on_handoff=on_refund_handoff,
            input_type=RefundRequestData
        ),
        
        # 2-3. 入力データ付きHandoff（エスカレーション）
        handoff(
            agent=senior_support_agent,
            tool_name_override="escalate_to_senior",
            tool_description_override="複雑な問題を上級サポートにエスカレーション",
            on_handoff=on_escalation_handoff,
            input_type=EscalationData,
            # 2-4. Input Filter適用（要約のみ渡す）
            input_filter=filter_summary_only
        ),
        
        # 2-4. Input Filter適用（全ツール削除）
        handoff(
            agent=tech_support_agent,
            tool_name_override="transfer_to_tech_support",
            tool_description_override="技術的な問題を専門エージェントに引き継ぐ",
            on_handoff=on_simple_handoff,
            input_filter=handoff_filters.remove_all_tools  # 組み込みフィルター使用
        )
    ]
)


# ========================================
# テストシナリオ実行関数
# ========================================

async def run_scenario(scenario_name: str, customer_query: str, context: CustomerContext):
    """シナリオを実行して結果を表示"""
    print(f"\n{'='*60}")
    print(f"シナリオ: {scenario_name}")
    print(f"{'='*60}")
    print(f"顧客: {context.customer_name} ({context.subscription_tier}会員)")
    print(f"問い合わせ: {customer_query}")
    print("-" * 60)
    
    try:
        result = await Runner.run(
            starting_agent=triage_agent,
            input=customer_query,
            context=context,
            max_turns=10  # 最大ターン数を設定
        )
        
        print(f"\n回答:")
        print(result.final_output)
        
        # 使用されたエージェントの情報
        if hasattr(result, 'agent_name'):
            print(f"\n最終対応エージェント: {result.agent_name}")
            
    except Exception as e:
        print(f"\nエラーが発生しました: {type(e).__name__}")
        print(f"詳細: {str(e)}")
        return False
    
    return True


# ========================================
# メイン実行関数
# ========================================

async def main():
    """メイン実行関数"""
    
    print("=" * 60)
    print("OpenAI Agents SDK - Handoff サンプルプログラム")
    print("カスタマーサポートシステムのシミュレーション")
    print("=" * 60 + "\n")
    
    # 環境変数チェック
    check_environment()
    
    # テストシナリオの実行
    scenarios = [
        # シナリオ1: FAQへの引き継ぎ
        {
            "name": "FAQ問い合わせ",
            "query": "パスワードをリセットする方法を教えてください",
            "context": CustomerContext(
                customer_name="田中太郎",
                customer_id="CUST001",
                subscription_tier="standard"
            )
        },
        
        # シナリオ2: 注文管理への引き継ぎ
        {
            "name": "注文状況確認",
            "query": "注文番号ORD-2024-001の配送状況を確認したいです",
            "context": CustomerContext(
                customer_name="佐藤花子",
                customer_id="CUST002",
                subscription_tier="premium"
            )
        },
        
        # シナリオ3: 返金処理（入力データ付き）
        {
            "name": "返金リクエスト",
            "query": "注文番号ORD-2024-002の商品が破損していたので、5000円の返金をお願いします",
            "context": CustomerContext(
                customer_name="鈴木一郎",
                customer_id="CUST003",
                subscription_tier="standard"
            )
        },
        
        # シナリオ4: 技術サポートへの引き継ぎ
        {
            "name": "技術的な問題",
            "query": "アプリが頻繁にクラッシュします。エラーコードERR_500が表示されます",
            "context": CustomerContext(
                customer_name="高橋美咲",
                customer_id="CUST004",
                subscription_tier="premium"
            )
        },
        
        # シナリオ5: エスカレーション
        {
            "name": "緊急エスカレーション",
            "query": "3回も問い合わせているのに問題が解決しません。責任者と話したいです",
            "context": CustomerContext(
                customer_name="山田次郎",
                customer_id="CUST005",
                subscription_tier="premium",
                issue_category="unresolved"
            )
        }
    ]
    
    success_count = 0
    for scenario in scenarios:
        success = await run_scenario(
            scenario_name=scenario["name"],
            customer_query=scenario["query"],
            context=scenario["context"]
        )
        if success:
            success_count += 1
        
        # 次のシナリオまで少し待機
        await asyncio.sleep(1)
    
    # 結果サマリー
    print(f"\n{'='*60}")
    print(f"実行結果サマリー")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{len(scenarios)} シナリオ")
    
    if success_count == len(scenarios):
        print("✅ すべてのシナリオが正常に実行されました")
    else:
        print(f"⚠️ {len(scenarios) - success_count} 個のシナリオでエラーが発生しました")


if __name__ == "__main__":
    try:
        # イベントループの実行
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nプログラムが中断されました")
    except Exception as e:
        print(f"\n予期しないエラーが発生しました: {type(e).__name__}")
        print(f"詳細: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)