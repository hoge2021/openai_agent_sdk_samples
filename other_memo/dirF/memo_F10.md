---
name: run-preflight-check
description: Terraform apply やレビュー前に、 前Accountの固有値の残存、既存VPC参照漏れ、未整理のTODO、危険な再作成候補などを点検する最終ゲートSkill。
---

# Purpose
このSkillは、Terraformコードや移行設計に対する事前点検を行い、apply前の事故を防ぐためのものです。

# When to use
- Terraform骨格生成後
- レビュー依頼前
- plan/apply前
- 変更差分を安全確認したいとき

# Instructions
以下を点検してください。

1. ハードコード検出
   - 前Account の account ID
   - 前Account起源の ARN
   - VPC ID / subnet ID / security group ID
   - bucket/table 名
   - region 固定値
   - 旧スタック由来の残骸

2. TODO / FIXME / placeholder 検出
   - 未確定事項が apply blocker か
   - 単なるメモか

3. import / recreate リスク
   - import検討対象が未整理のまま new resource になっていないか
   - 再作成で破壊的影響が出ないか

4. 既存VPC整合性
   - VPC新規作成が紛れていないか
   - `data` 参照または変数化が適切か

5. provider/backend/version
   - required versions があるか
   - backend未定義/曖昧がないか
   - lockやstate前提が曖昧でないか

6. データ移行分離
   - S3/DynamoDBデータ移行がIaC本体に混入していないか
   - cutover条件が未整理でないか

7. ドキュメント整合性
   - 実装とRunbookの矛盾
   - 設計方針との差分

# Output format
以下で出力してください。

## 1. Overall Result
`PASS` / `PASS WITH WARNINGS` / `BLOCKED`

## 2. Findings
表形式:
- Check area
- Status (`pass` / `warning` / `blocked`)
- Evidence
- Why it matters
- Required fix

## 3. Apply Blockers
## 4. Warnings
## 5. Safe Next Action

# Rules
- blocker は blocker として明確に出す
- 「多分大丈夫」は禁止
- TODOを見つけたら、そのTODOが致命かどうか判断する
- 推測レビューではなく、現物ベースで判定する
