■ロールバックについて
AWS CDKは、その実態はCloudFormationなので、cdk deployを実行した後、Stack作成あるいは更新に失敗した場合、自動的にロールバックする。
Terraformはterraform applyを実行した後、途中で失敗した場合、作成済みリソースは残り、stateに反映される
手動修正が必要となる。

移行・運用の対策:
・CI/CDパイプラインにterraform planの出力レビューを必ず組み込む（plan → 承認 → apply のワークフロー・大規模変更は小さなチャンクに分割してapplyする運用ルールを設ける
・万が一の手動ロールバックに備え、直前のstateファイルをバージョニング付きS3に保管する（後述のremote state）

■IAM権限の自動補完について
AWS CDKは、.grantRead()や.grantInvoke()のようなメソッドで、必要なIAMポリシーを自動生成してくれます。
Terraformにはこの仕組みがなく、aws_iam_role、aws_iam_policy、aws_iam_role_policy_attachmentなどをすべて自分で明示的に定義する必要がある。

移行・運用の対策:

移行前に、CDKが生成した既存CloudFormationテンプレートからIAMリソースを全て洗い出す（cdk synthの出力が最も正確）
Terraformモジュールとして共通IAMパターンをまとめ、チーム内で再利用する
最小権限の原則を徹底するため、IAM Access Analyzerと併用する

■State管理という概念の根本的な違い
CDKはCloudFormationにstateを委任しているので、意識する必要はないが、
Terraformではstateファイル（.tfstate）が命です。このファイルが壊れたり消えたりすると、Terraformは既存リソースとの対応関係を見失います。

対応策：
　初日からS3 + DynamoDBによるremote state backendを構成する（ローカルstateは絶対に使わない）
　state lockingを有効にし、複数人の同時applyを防ぐ
　terraform importコマンドで既存リソースをstateに取り込む移行作業が発生する。


■抽象度の違い（L2 Construct vs Resource）
CDKのL2/L3 Constructは、1つのクラスで複数のAWSリソース（セキュリティグループ、ロール、ログ設定など）をまとめて生成します。Terraformではこれらが個別リソースとして1つずつ定義が必要です。例えばCDKでnew lambda.Function()と書くと裏でロググループ、実行ロール、ポリシーが暗黙的に作られますが、Terraformではaws_lambda_function、aws_cloudwatch_log_group、aws_iam_role、aws_iam_role_policy_attachmentを全て明記します。

自社の頻出パターンをTerraform modulesとして作成し、CDKのConstructに近い再利用性を確保する
Terraform Registryの公開モジュール（例：terraform-aws-modules/lambda/aws）を活用すると記述量を減らせる

■マルチスタック構成の違い
CDKではAppの中に複数のStackを定義してスタック間参照ができます。Terraformではterraform_remote_stateデータソースや、output/variableを使ったモジュール間連携で同様のことを実現しますが、設計の仕方が異なります。
対応策：
ディレクトリ構造でenvironment（dev/stg/prod）とcomponent（network/app/dbなど）を分離する
remote stateのoutputを使ったゆるい結合にし、依存関係を明確にする

3. 移行計画の推奨アプローチ
移行は段階的に行うのがベストです。
フェーズ1（準備） として、cdk synthで現在のCloudFormationテンプレートを全て出力し、リソースの完全なインベントリを作成します。同時にremote state backendのインフラを先に構築します。
フェーズ2（並行運用） では、新規リソースはTerraformで作成し始め、既存リソースはまだCDK管理のまま残します。チームがHCLに慣れる期間でもあります。
フェーズ3（段階的移行） で、リスクの低いリソース（S3バケット、DynamoDBテーブルなど）からterraform importで取り込み、CloudFormationスタックからの切り離し（DeletionPolicy: Retainを設定してからスタック削除）を行います。
フェーズ4（完全移行） として、全リソースがTerraform管理になったらCDKコードベースを廃止します。
特に注意すべきは、CloudFormationスタックからリソースを「引き剥がす」作業です。手順を間違えるとリソースが削除されるリスクがあるため、必ずステージング環境でリハーサルしてから本番に適用してください。
何か特定のリソース（例えばECS、Lambda、RDSなど）について具体的な移行手順が必要であれば、掘り下げて説明できます。


■デプロイ
AWS CDKでは共通関数のLambda Layerは事前にモジュールをインストールした上でcdk deployし、その際にZIP圧縮して、構築していた。
これをTerraformに移行する時はどうするのだろうか？


AWS CDKは裏側で依存モジュールのインストール・ZIP圧縮・S3アップロード・Layer作成まで一気にやってくれます。
Terraformにはbundlingのような組み込み機能がないため、「ビルド」と「デプロイ」を分離して考える必要があります。そのためには、Terraformの中でビルドも行う（シンプル構成向き）か、CI/CDでビルドし、Terraformはデプロイを行う必要がある。
