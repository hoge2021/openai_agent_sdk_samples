from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

# 指示
INSTRUCTIONS = (
    "あなたは研究助手です。検索語句が与えられたら、その語句で Webを検索し、結果の簡潔な要約を作成します。"
    "要約は2～3段落、300語未満でなければなりません。"
    "要点を押さえてください。簡潔に書きます。完全な文や正しい文法である必要はありません。"
    "これはレポートをまとめる人が読むものなので、要点を押さえ、余分な部分は無視することが重要です。"
    "要約自体以外のコメントは含めないでください。"
)

# SearchAgentの準備
search_agent = Agent(
    name="SearchAgent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool()],
    model_settings=ModelSettings(tool_choice="required"),
)