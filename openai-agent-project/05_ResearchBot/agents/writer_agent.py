from pydantic import BaseModel
from agents import Agent

# 指示
INSTRUCTIONS = (
    "あなたは、リサーチ クエリに対するまとまりのあるレポートを書くことを任された上級研究者です。"
    "元のクエリと、リサーチアシスタントが行った初期リサーチが提供されます。"
    "まず、レポートの構造と流れを説明するレポートのアウトラインを作成します。"
    "次に、レポートを生成して、最終出力として返します。"
    "最終出力はマークダウン形式で、長くて詳細なものにする必要があります。"
    "5～10 ページ、少なくとも 1,000語のコンテンツを目指します。"
)

# レポート
class ReportData(BaseModel):
    short_summary: str
    """調査結果を2～3文で短く要約"""

    markdown_report: str
    """最終報告書"""

    follow_up_questions: list[str]
    """さらに研究するための提案トピック"""

# WriterAgentの準備
writer_agent = Agent(
    name="WriterAgent",
    instructions=INSTRUCTIONS,
    model="o3-mini",
    output_type=ReportData,
)