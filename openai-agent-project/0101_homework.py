from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner
from pydantic import BaseModel
import asyncio

# 数学家庭教師Agentの定義
math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="数学の質問に特化したAgent",
    instructions="あなたは数学の問題を手助けします。各ステップで論理的な説明を行い、例を含めてください。",
)

# 歴史家庭教師Agentの定義
history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="歴史の質問に特化したAgent",
    instructions="あなたは歴史に関する質問を手助けします。重要な出来事や背景を明確に説明してください。",
)

# 宿題に関する質問かどうかを判断するモデル
class HomeworkOutput(BaseModel):
    is_homework: bool  # 宿題に関する質問かどうか
    reasoning: str  # その判断の理由

# Guardrail Agentの定義
guardrail_agent = Agent(
    name="Guardrail check",
    instructions="ユーザーが宿題について質問しているか確認してください。",
    output_type=HomeworkOutput,
)

# Guardrail関数の定義
async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(HomeworkOutput)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.is_homework,
    )

# トリアージAgentの定義
triage_agent = Agent(
    name="Triage Agent",
    instructions="ユーザーの質問が宿題に関するものかを判断し、適切なAgentを選択してください。",
    handoffs=[history_tutor_agent, math_tutor_agent], # ハンドオフ
    input_guardrails=[
        InputGuardrail(guardrail_function=homework_guardrail),
    ],
)

# メイン
async def main():
    # 「アメリカの最初の大統領は誰ですか？」の質問を処理
    try:
        result = await Runner.run(triage_agent, "歴史の宿題で、アメリカの初代大統領は誰ですか？」")
        print(result.final_output)
    except Exception as e:
        print("エラー:", e)

    # 「人生とは何か？」の質問を処理
    try:
        result = await Runner.run(triage_agent, "人生の宿題とは何か")
        print(result.final_output)
    except Exception as e:
        print("エラー:", e)

# メインの実行
if __name__ == "__main__":
    asyncio.run(main())