---
name: map-cfn-to-terraform
description: CloudFormation/CDKで表現されている各要素を、Terraform上で resource/data/import/manual/out-of-scope のどれとして扱うか設計台帳に落とし込む。実装前のマッピング専用Skill。
---

# Purpose
このSkillは、CDKやCloudFormationの各リソースを、Terraformでどのように扱うべきかを設計台帳として定義するためのものです。
1:1変換ではなく、Terraformにおける適切な表現へ再分類することが目的です。

# When to use
- `discover-cdk-landscape` の実行後
- Terraform実装前に、resource/data/import/manual を切り分けたいとき
- 既存VPC流用やアカウント差し替えを踏まえた再表現が必要なとき

# Preconditions
- 旧CDKコードまたは `template.yaml` の棚卸し結果が存在すること
- Account A live参照不可であることを理解していること
- Account B に既存VPCを流用することが決まっていること

# Instructions
以下を実施してください。

1. 棚卸し済みの各AWS要素について、Terraformでの扱いを次のいずれかに分類してください。
   - `resource`: Account B に新規作成すべき
   - `data`: 既存のものを参照すべき
   - `import`: 既存リソースをTerraform管理下に取り込む候補
   - `manual`: Terraformの本体から分離した手動・運用手順にすべき
   - `out-of-scope`: 今回対象外

2. 各要素について、以下も判断してください。
   - なぜその分類なのか
   - 再作成リスク
   - importの妥当性
   - Account A と B の差異で注意すべき点
   - 既存VPCとの関係
   - 追加確認が必要か

3. 特に以下は慎重に扱ってください。
   - IAM Role / Policy
   - Lambda 実行ロールと周辺の自動生成権限
   - CloudWatch Logs
   - API Gateway deployment/stage
   - Step Functions role/policy
   - S3 bucket policy / notification
   - DynamoDB table settings
   - Event source mappings
   - VPC / subnet / security group / endpoint
   - CloudFront / Origin Access 周辺

4. CloudFormationで暗黙に作られている副次要素を見つけた場合は、Terraformで明示化が必要か評価してください。

5. 不足情報がある場合は、推測で分類せず、`Needs confirmation` を付けてください。

# Output format
以下の列を持つマッピング表を出力してください。

- Source stack
- Source resource / construct
- AWS type
- Terraform handling (`resource` / `data` / `import` / `manual` / `out-of-scope`)
- Terraform target candidate
- Reason
- Risks
- Existing VPC impact
- Needs confirmation? (`yes/no`)
- Notes

その後に以下を続けてください。

## Key Mapping Decisions
重要な判断だけを3〜10件程度まとめる。

## High-Risk Items
事故りやすい項目をまとめる。

## Recommended Next Step
原則として `design-target-terraform` を提案する。

# Rules
- `resource` に寄せすぎない
- 既存VPC関連は基本的に `data` を強く検討する
- データ移行を伴うものは `manual` または別Runbook 前提で考える
- 断定できないものは `Needs confirmation: yes` にする
- 「変換できそう」ではなく「運用可能か」で判定する
