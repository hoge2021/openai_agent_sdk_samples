---
name: discover-cdk-landscape
description: 旧AWS CDKコードベースと cdk synth の template.yaml から、Terraform移行の前提情報を抽出し、スタック構成・リソース棚卸し・未知点一覧を作成する。CDK→Terraform移行の初手で必ず使う。
---

# Purpose
このSkillは、旧AWS CDKコードベースと `cdk synth` で得られた `template.yaml` を調査し、Terraform移行に必要な事実を整理するためのものです。
このSkillの目的はコード生成ではなく、事実抽出・分類・未知点洗い出しです。

# When to use
以下のいずれかに該当する場合に使います。
- CDK→Terraform移行作業の最初の調査を始めるとき
- スタック一覧、リソース一覧、依存関係を把握したいとき
- `template.yaml` とCDKコードから、Terraform化対象の棚卸しをしたいとき
- Account A に直接アクセスできず、ソースと synth 結果だけで前提整理するとき

# Required assumptions
このSkillでは以下を絶対前提とします。
- Claude Code からアクセス可能なのは Account B のみ
- Account A の live AWS 環境にはアクセスできない
- 参照可能な情報源は、旧CDKコードベース、`cdk synth` で得られた `template.yaml`、および付随文書のみ
- VPC は Account B に既存のものを流用する
- DynamoDB と S3 のデータは Account B へ移行する必要がある
- 推測で欠損値を補完してはならない

# Instructions
以下の順番で進めてください。

1. まず、CDKコードベース全体を探索し、以下を抽出してください。
   - スタック一覧
   - Construct / Stack の境界
   - 環境変数、context、parameter 的な入力
   - cross-stack 参照
   - リソース命名規則
   - account / region / VPC / subnet / security group / bucket 名などの環境依存値

2. 次に `template.yaml` を読み、CloudFormation リソース一覧を抽出してください。
   - Logical ID
   - Resource Type
   - 主な Properties
   - DependsOn
   - Outputs
   - Parameters
   - Mappings / Conditions / Metadata の有無

3. CDKコードと `template.yaml` の対応関係を確認してください。
   - コードに存在するが synth 結果で見えづらいもの
   - synth 結果に現れるが CDK 上で抽象化されているもの
   - 自動生成されたIAMやロググループなどの副次リソース

4. すべての対象を以下に分類してください。
   - Terraformで新規 `resource` として作る候補
   - 既存環境を `data` 参照すべき候補
   - `import` を検討すべき候補
   - 手動移行や別Runbookに分離すべき候補
   - スコープ外候補

5. 既存VPC流用の観点で特に以下を探してください。
   - VPC ID 固定値
   - subnet ID 固定値
   - security group ID 固定値
   - route table / endpoint / NAT / IGW 依存
   - Lambda の VPC 接続設定
   - API Gateway / CloudFront / private connectivity に関わる設定

6. Account A に live 接続しないと確定できない事項は、推測せず `Unknowns` として明示してください。

# Output format
以下の見出しで必ず出力してください。

## 1. Executive Summary
短く全体像をまとめる。

## 2. Stack Inventory
各スタックごとに:
- Stack name
- Purpose
- Major resources
- Cross-stack dependencies
- Environment-specific assumptions

## 3. Resource Inventory
表形式で:
- Origin stack
- Logical/construct name
- AWS resource type
- Purpose
- Candidate handling (`resource` / `data` / `import` / `manual` / `out-of-scope`)
- Notes

## 4. Environment-Bound Values
- Account ID
- Region
- VPC / subnet / SG
- bucket / table / role / ARN
- その他環境依存値

## 5. Existing VPC Impact
既存VPC流用により再設計・再確認が必要な点を列挙する。

## 6. Unknowns / Human Confirmation Needed
Account A live確認が必要な項目を列挙する。

## 7. Recommended Next Step
次に実行すべき Skill を提案する。
原則として `map-cfn-to-terraform` を提案する。

# Rules
- コード生成はしない
- 欠損値を想像で埋めない
- Account A live情報が無い限り断定しない
- `Unknown` を適切に残す
- 「移行できるか」より「何が分かっていて何が未確定か」を優先する
