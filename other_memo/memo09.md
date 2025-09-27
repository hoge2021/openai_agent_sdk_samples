■コマンド
・仮想環境構築
uv venv
・インストール
uv pip install deep-researcher
・.envを作成※内容は以下を参照

・DeepReserchを実行する
uv run deep-researcher --mode deep --query "Provide a comprehensive overview of quantum computing 日本語で出力して。" --max-iterations 3 --max-time 10 --verbose

■参考URL
https://github.com/qx-labs/agents-deep-research


パラメータ:
--query: 研究テーマまたは質問（指定されていない場合は入力を求められます）
--mode: deepDeepResearcherを使用する場合、simpleIterativeResearcherを使用する場合（デフォルト：deep）
--max-iterations: 研究反復の最大回数（デフォルト: 5）
--max-time: リサーチループが自動的に終了して最終出力を生成するまでの最大時間（分）（デフォルト: 10）
--output-length: レポートの希望出力長さ（デフォルト:「5ページ」）
--output-instructions: 最終報告書の追加の書式設定指示
ブールフラグ:

--verbose: 研究の進行状況をコンソールに出力します
--tracing: OpenAI プラットフォーム上のワークフローをトレースします (OpenAI モデルでのみ機能します)

■.envの内容
# Note: You can optionally add the prefix 'DR_' to the variable names to avoid conflicts with other variables in your app

# LLM api keys
OPENAI_API_KEY=編集せよ
DEEPSEEK_API_KEY=<your-deepseek-api-key>
OPENROUTER_API_KEY=<your-openrouter-api-key>
GEMINI_API_KEY=<your-google-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>
PERPLEXITY_API_KEY=<your-perplexity-api-key>
HUGGINGFACE_API_KEY=<your-huggingface-api-key>
LOCAL_MODEL_URL=<your-local-model-url>
AZURE_OPENAI_ENDPOINT=<your-azureopenai-endpoint-url>
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_KEY=<your-azureopenai-api-key>
AZURE_OPENAI_API_VERSION=<your-azureopenai-deployment-api-version>

# Search provider
SEARCH_PROVIDER=openai  # serper or openai
SERPER_API_KEY=<your-serper-api-key>

# Selected LLM models
# Current options for model providers: 
# azureopenai, openai, deepseek, openrouter, gemini, anthropic, perplexity, huggingface, local
REASONING_MODEL_PROVIDER=openai
REASONING_MODEL=o3-mini
MAIN_MODEL_PROVIDER=openai
MAIN_MODEL=gpt-4o
FAST_MODEL_PROVIDER=openai
FAST_MODEL=gpt-4o-mini
