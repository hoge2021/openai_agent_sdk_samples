---
name: design-target-terraform
description: CDK/CFN棚卸し結果とマッピング台帳をもとに、最終的なTerraform構成、module分割、state/backend戦略、既存VPC統合方針、環境差し替え方針を設計する。
---

# Purpose
このSkillは、Terraformの最終設計を定義するためのものです。
単なるコード変換ではなく、今後保守しやすく、事故が起きにくい構成を設計することが目的です。

# When to use
- `map-cfn-to-terraform` の完了後
- Terraformコードを書き始める前
- module境界、state分割、backend設計、変数設計を確定したいとき

# Core design principles
- Account B 向けに再設計する
- 既存VPCは新規作成しない
- 一度限りの移行作業と、継続運用するIaC本体を分離する
- TODOで残すことは許されるが、推測で穴埋めしてはならない
- 長期保守性を優先する
- Terraformの state 境界は「変更単位」と「事故影響範囲」で決める

# Instructions
以下を設計してください。

1. ディレクトリ構成
   推奨候補:
   - `modules/`
   - `live/`
   - `migration/`
   - `validation/`
   - `docs/`

2. module境界
   例:
   - lambda
   - dynamodb
   - s3
   - step_functions
   - apigw
   - iam
   ただし無理に細かく分けすぎないこと。

3. state/backend戦略
   - backend type
   - state file 分割方針
   - lock 戦略
   - workspace を使うか否か
   - environment/account 分離方針

4. provider/version方針
   - required_version
   - required_providers
   - provider alias 必要性
   - region/account 固定化の扱い

5. 既存VPC統合方針
   - data source で取得するもの
   - variablesで受け取るもの
   - 事前に人手で確定すべきもの
   - SG/subnet の境界

6. データ移行との分離
   - S3/DynamoDB のデータ移行はどこまでIaC外に出すか
   - Runbook に持たせる項目
   - cutover との関係

7. 命名・タグ・locals・variables規約

8. import 方針
   - import block 利用可否
   - import対象の選別基準
   - recreate した方が安全なもの

9. validation 方針
   - fmt
   - validate
   - plan
   - custom preflight

# Output format
以下の見出しで出力してください。

## 1. Recommended Terraform Architecture
## 2. Directory Layout
コードブロックで示すこと
## 3. Module Boundaries
## 4. State and Backend Strategy
## 5. Provider and Version Strategy
## 6. Existing VPC Integration Strategy
## 7. Variables / Locals / Naming Rules
## 8. Import vs Recreate Policy
## 9. Migration Separation Policy
## 10. Validation and Release Gates
## 11. Risks and Trade-offs
## 12. Recommended Next Step

原則として次は `generate-tf-skeleton` を提案する。

# Rules
- 「CDKの構造をそのまま再現」は基本禁止
- 既存VPCを module に閉じ込めすぎない
- 1回限りの移行処理と通常IaCを混ぜない
- state を巨大1枚にしない
- 将来の変更容易性を優先する
