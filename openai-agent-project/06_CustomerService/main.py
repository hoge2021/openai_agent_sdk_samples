# 型ヒントのためのアノテーションを将来のバージョンでも使えるようにする
from __future__ import annotations as _annotations

# 非同期処理を行うための標準ライブラリ
import asyncio

# ランダムな値を生成するための標準ライブラリ
import random

# 一意なID（UUID）を生成するための標準ライブラリ
import uuid

# データ構造を簡単に定義できるpydanticのBaseModelをインポート
from pydantic import BaseModel

# エージェント関連のクラスや関数をまとめてインポート
from agents import (
    Agent,                  # エージェント本体のクラス
    HandoffOutputItem,      # ハンドオフ（人への引き継ぎ）時の出力アイテム
    ItemHelpers,            # アイテム操作の補助関数
    MessageOutputItem,      # メッセージ出力用のアイテム
    RunContextWrapper,      # 実行時のコンテキストをラップするクラス
    Runner,                 # エージェントの実行管理クラス
    ToolCallItem,           # ツール呼び出し用のアイテム
    ToolCallOutputItem,     # ツール呼び出しの出力アイテム
    TResponseInputItem,     # レスポンス入力用のアイテム
    function_tool,          # 関数をツールとして登録するためのデコレータ
    handoff,                # ハンドオフ処理用の関数
    trace,                  # トレース（実行履歴）用の関数
)

# ハンドオフ時の推奨プロンプトのプレフィックスをインポート
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# 航空会社Agentのコンテキスト
class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None  # 乗客名
    confirmation_number: str | None = None  # 確認番号
    seat_number: str | None = None  # 座席番号
    flight_number: str | None = None  # フライト番号

# FAQツール
@function_tool(
    name_override="faq_lookup_tool", 
    description_override="FAQに関する質問の回答を提供します。"
)
async def faq_lookup_tool(question: str) -> str:
    if "バック" in question or "荷物" in question:
        return (
            "飛行機にはバッグを1つ持ち込むことができます。"
            "重量は50ポンド以下、サイズは22インチ x 14インチ x 9インチである必要があります。"
        )
    elif "席" in question or "飛行機" in question:
        return (
            "飛行機には120席あります。"
            "ビジネスクラスの座席は22席、エコノミークラスの座席は98席あります。"
            "非常口は4列目と16列目です。"
            "5列目から8列目はエコノミープラスで、足元に余裕があります。"
        )
    elif "WiFi" in question or "Wi-Fi" in question:
        return "飛行機には無料Wi-Fiがあります。Airline-Wifiにご参加ください"
    return "申し訳ありませんが、その質問の答えは分かりません。"

# 座席更新ツール
@function_tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext], confirmation_number: str, new_seat: str
) -> str:
    """
    指定された確認番号の座席を更新します。

    Args:
        confirmation_number: フライトの確認番号
        new_seat: 更新する新しいシート
    """
    # 顧客の入力に基づいてコンテキストを更新
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat

    # incoming handoffによってフライト番号が設定されていることを確認
    assert context.context.flight_number is not None, "フライト番号は必須です。"
    return f"確認番号 {confirmation_number} の座席を {new_seat} に更新しました。"

# Triage Agent から Seat Booking Agent へのHandoffの際に呼ばれるHook
async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    flight_number = f"FLT-{random.randint(100, 999)}"
    context.context.flight_number = flight_number


# FAQ Agentの準備
faq_agent = Agent[AirlineAgentContext](
    name="FAQ Agent",
    handoff_description="航空会社に関する質問に答えてくれる親切なAgentです。",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    あなたは FAQ Agentです。顧客と話しているときは、Triage Agentから転送された可能性があります。
    次の手順に従って顧客をサポートします。
    # 手順
    1. 顧客が最後に尋ねた質問を特定します。
    2. faq_lookup_toolを使用して質問に答えます。自分の知識に頼らないでください。
    3. 質問に答えられない場合は、Triage Agentに転送します。""",
    tools=[faq_lookup_tool],
)

# Seat Booking Agentの準備
seat_booking_agent = Agent[AirlineAgentContext](
    name="Seat Booking Agent",
    handoff_description="フライトの座席を更新できる便利なAgentです。",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    あなたはSeat Booking Agentです。顧客と話しているときは、Triage Agentから転送された可能性があります。
    次の手順に従って顧客をサポートします。
    # 手順
    1. 確認番号を尋ねます。
    2. お客様に希望の座席番号を尋ねます。
    3. update_seatを使用して、フライトの座席を更新します。
    お客様が手順に関係のない質問をした場合は、Triage Agentに転送します。 """,
    tools=[update_seat],
)

# Triage Agentの準備
triage_agent = Agent[AirlineAgentContext](
    name="Triage Agent",
    handoff_description="顧客のリクエストを適切なAgentに委任できるTriage Agentです。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "あなたは役に立つTriage Agentです。質問を他の適切なAgentに委任できます。"
    ),
    handoffs=[
        faq_agent,
        handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff),
    ],
)

# 相互Handoff
faq_agent.handoffs.append(triage_agent)
seat_booking_agent.handoffs.append(triage_agent)

# メインの定義
async def main():
    current_agent: Agent[AirlineAgentContext] = triage_agent # 最初はTriage Agent
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()

    # 会話IDにランダムなUUIDを使用
    conversation_id = uuid.uuid4().hex[:16]

    while True:
        # メッセージの入力
        user_input = input("メッセージを入力: ")
        with trace("Customer service", group_id=conversation_id):
            # Agentの実行
            input_items.append({"role": "user", "content": user_input})
            result = await Runner.run(current_agent, input_items, context=context)

            # 出力
            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent

# メインの実行
if __name__ == "__main__":
    asyncio.run(main())
