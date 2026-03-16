■要点まとめ
流れは「Plan → 保存 → 議論 → 実装 → レビュー → 次のPlan」の繰り返し。キーポイントは3つだ。
第一に、計画は必ずファイルに書き出す。docs/migration-plan.md と docs/tasks.md がコンテキスト切れの保険になる。
第二に、Plan Modeでの分析時にMCPサーバーをフル活用する。読み取り専用でもMCPサーバーへのクエリは実行されるので、Serenaでのコード構造解析やterraform MCPでのスキーマ確認はPlan Modeの段階でやっておく。
第三に、スタック単位でPlan-Actを回す。150ファイルを一気に計画→実装するのではなく、スタック単位の小さなループで進める方が計画の精度も実装の品質も上がる。


■プロンプト_移行計画の実装。（Planモードで実行）
ultrathink

対象スタック: $ARGUMENTS


CDKコードベース（/home/hoge/28_claudecode_test2/projects/aws-lambda-handler-cookbook）とserenaのコードベース俯瞰図(/home/hoge/28_claudecode_test2/projects/.serena/memories/aws-lambda-handler-cookbook/codebase_overview.md)、そしてcdk synthテンプレート（/home/hoge/28_claudecode_test2/projects/aws-lambda-handler-cookbook/cdk.out/hoge-main-Orders-dev.template.json）を
徹底的に分析して、Terraform移行の詳細な実装計画を立案してほしい。

分析すべき内容:

1. CDKスタックの全体構成（スタック数、各スタックのリソース構成）
2. Serenaで対象スタックのCDKコードを解析
3. awslabs-cfn-mcp-serverで対応するtemplate.yamlセクションを確認
4. terraform MCPで各リソースの最新Terraform定義を確認
5. aws-docsでAWSサービス固有の仕様を確認
6. template.yaml内の全AWSリソースの棚卸し
7. CDKが暗黙的に生成しているリソース（IAMロール、LogGroup、暗号化設定等）
8. スタック間のクロスリファレンス（Fn::ImportValue等）

出力形式:
- Terraformモジュール構成案（ディレクトリツリー）
- 各モジュールに含めるリソースの対応表（CFn Type → TF Resource）
- 実装順序（依存関係を考慮したフェーズ分け
- リスク・懸念事項のリスト

出力ファイル:
- この計画を migration-plan.md に保存して。
- また、実装タスクを tasks.md にチェックリスト形式で保存して。

補足:
-  Terraformモジュール構成案を考えること。
- tfstateファイルは、S3バケットにして。バージョニングすること。それから、DynamoDB ロックテーブルもつけて。

■計画実行
./migration-plan.md と ./tasks.md を読み込んで、
その計画に厳密に従って実装を開始してほしい。

■ 実行範囲
Phase 1（基盤モジュール）のみ実行すること。Phase 2以降には手を出さないこと。

■ 実行ルール
- /cdk-to-tf スキルの変換ルールに従うこと
- 1モジュール完了ごとに terraform fmt && terraform validate を実行すること
- 検証でエラーが出たら自力で修正してから次に進むこと
- 各モジュールの完了時に docs/tasks.md のチェックボックスを更新すること
- 判断に迷う箇所があれば実装を止めて質問すること

■ 参照リソース
- CDKソースコード: /home/hoge/28_claudecode_test2/projects/aws-lambda-handler-cookbook
- CDKソースコード全体:/home/hoge/28_claudecode_test2/projects/.serena/memories/aws-lambda-handler-cookbook/codebase_overview.md
- CloudFormationテンプレート: /home/hoge/28_claudecode_test2/projects/aws-lambda-handler-cookbook/cdk.out/hoge-main-Orders-dev.template.json
- Terraform出力先: /home/hoge/28_claudecode_test2/Terraform/test003

- MCPサーバーを積極的に使うこと
  - terraform MCP でリソーススキーマを確認
  - awslabs-cfn-mcp-server でCFnリソース仕様を確認
  - context7 で最新のTerraformパターンを確認
  - aws-docs でAWSサービス仕様を確認
  - Serena でCDKコードのシンボル解析
  
■Phase2以降  
migration-plan.mdとtasks.md を参照して、
Phase 2（Lambda & StepFunctions）の実装に進んでほしい。
前のPhaseと同じルールで進めること。

