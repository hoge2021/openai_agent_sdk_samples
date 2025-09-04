from agents import Agent, Runner

# Agentの作成
agent = Agent(name="Assistant", instructions="あなたは役に立つアシスタントです")

# Agentの実行
result = Runner.run_sync(agent, "プログラミングにおける再帰について俳句を書いてください。")
print(result.final_output)