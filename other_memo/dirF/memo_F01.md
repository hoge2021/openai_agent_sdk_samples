1. HashiCorp Terraform MCP Server（最重要・必須）
2. awslabs.cfn-mcp-server（CloudFormation MCP Server）

■前提条件
おそらく、dockerとuvをインストールする必要あり。


■MAC OSでのインストール

# または Homebrew
  brew install uv

# 確認
uv --version
uvx --version

# Docker Desktop（GUI込み、推奨）
brew install --cask docker

# インストール後、Docker Desktopを起動してからデーモン確認
docker --version
docker run hello-world
※▎ Docker Desktopは起動しておかないとdaemonが動かないので注意。

4. Node.js / npm / npx

# nodenvかnvmで管理するのが無難
brew install nodenv

# シェル設定に追加（bash/zsh）
echo 'eval "$(nodenv init -)"' >> ~/.zshrc
source ~/.zshrc

# LTS版インストール
nodenv install 22.14.0
nodenv global 22.14.0

# 確認
node --version
npx --version

■serena
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code --project $(pwd)


■Context7 MCP Server
 Context7 MCPは、バージョン固有のドキュメントとコード例をソースリポジトリから直接取得し、LLMのコンテキストに注入する ClaudeLog。Terraformのaws_lambda_function、aws_dynamodb_table、aws_sfn_state_machineといったリソースの最新のベストプラクティスを、Claude Codeが古い学習データに頼らずに参照できるようになる。

claude mcp add context7 -- npx -y @upstash/context7-mcp

■ HashiCorp Terraform MCP Server
Terraform MCP Serverは、AIモデルにTerraformレジストリからのリアルタイムなプロバイダードキュメント、モジュール、ポリシー情報へのアクセスを提供する HashiCorp Developer。CDKからの変換時に最も深刻な問題は、Claude Codeの学習データに含まれるTerraformのプロバイダースキーマが古くなっている可能性があることだ。このMCPサーバーがあれば、常に最新のAWSプロバイダーのリソース定義・引数仕様を参照しながらコード生成ができる。

claude mcp add terraform -- docker run -i --rm hashicorp/terraform-mcp-server

■ AWS Documentation MCP Server
 AWSがホストするリモートMCPサーバーで、最新のAWSドキュメント、APIリファレンス、What's Newポスト、Getting Started情報、Well-Architectedガイダンスにアクセスできる 

claude mcp add aws-docs -s project \
  -e AWS_DOCUMENTATION_PARTITION=aws \
  -- uvx awslabs.aws-documentation-mcp-server@latest

■CloudFormation MCP Server
 CloudFormation MCPサーバーは、AWS CLIのクレデンシャルを使ってCloudFormationリソースを直接管理できる Sati Technology。あなたの作業環境はアカウントBだが、template.yamlというCloudFormationテンプレートを資料として持っている。このMCPサーバーを使えば、template.yamlの各リソース定義の妥当性検証やドキュメント参照を自動化できる。
※AWS CLIのプロファイル名は適宜編集してください。
claude mcp add awslabs-cfn-mcp-server -s project \
  -e FASTMCP_LOG_LEVEL=ERROR \
  -e AWS_PROFILE=default \
  -e AWS_REGION=ap-northeast-1 \
  -- uvx awslabs.cfn-mcp-server@latest


■他に使えそうなMCPサーバ
AWS API MCP Server
Amazon CloudWatch MCP Server
