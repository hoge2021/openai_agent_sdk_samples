from pydantic import BaseModel
from agents import Agent

# 指示
INSTRUCTIONS = (
    "あなたは役に立つ研究アシスタントです。"
    "クエリが与えられたら、クエリに最適な回答を得るために実行するWeb検索のセットを考え出してください。"
    "クエリする5から20個の用語を出力してください。"
)

# Web検索アイテム
class WebSearchItem(BaseModel):
    reason: str
    "この検索がクエリにとって重要である理由。"

    query: str
    "Web検索に使用する検索用語。"

# Web検索プラン
class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """クエリに最適な回答を得るために実行するWeb検索のリスト。"""

# PlannerAgentの準備
planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o",
    output_type=WebSearchPlan,
)