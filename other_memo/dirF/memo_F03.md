
■CDKコマンド、特定のスタックだけ出力
cdk synth ＜スタック名＞ > service-stack.yaml

cdk.out/hoge-main-Orders-dev.template.json  

■Serenaのプロンプト
aws-lambda-handler-cookbookにあるコードベースの内容をserenaのMCPサーバを用いて、そのまとめて
.serenaディレクトリの適度な場所に出力して。




AWS CDKからTerraformに移行する際に、Claude Codeを使用するよう言われている。
では、移行業務に有効なMCPサーバー、Skillsの機能を教えて。その理由と使い道も併せて。
有効なAgetnt Teamsの使い方があれば教えて。

補足:なお使い道としては、MCPサーバやSkillsやAgent Teamsなど他のClaude Codeの機能も併用しても構わない。

補足:なお移行作業は詳細は以下の通りである。

###詳細
・AWS CDKのスタックは複数ある。
・CDKがデプロイされたアカウントAとTerraformで構築する新規アカウントBは別である。
・Claude CodeはアカウントBのみ使用可能である。アカウントAでは使えない。
・作業環境はアカウントBである、資料としてはアカウントAで使用していたコードベースと、cdk synthで取得したtemplate.yamlだけである。
・CDKではLambda、DynamoDB、StepFuntion、S3、Cloudwatch、VPC、API Gatewayなどが使われている。
・VPCはアカウントBに既に用意されたものを使えと言われている。
・DynamoDB、S3のデータはアカウントBに移行する必要がある。
・Lambdaはデプロイする前にZip圧縮で事前にライブラリをインストールする必要がある。
・Secrets ManagerのKMSキーをアカウントAでは使っているので、これもアカウントBに移行する必要がある。
・AWS CLIはAWS SSOである
・とりあえずSerenaのMCPサーバを使うのか確定済み。他のMCPサーバやSkillsがあれば頼む。
