上記がワークフロー全体図です。以下、このワークフローに基づいた実行結果を出力します。

---

## CDK差分（ブランチA→B）をTerraformに反映する完全実行ガイド

### 根本的な問題構造の整理

この状況を正確に捉えると、こういうことになる。

「CDKブランチA」は既にTerraformに変換済みで、別AWSアカウントにデプロイ済み。つまり現在のTerraformコードとtfstateは「ブランチAの世界」を表現している。一方「CDKブランチB」はAの上に積み重なった更新であり、この**差分だけ**を正確にTerraformへ反映する必要がある。ここで最も危険なのは、CDKの高レベル抽象（L2/L3 Construct）が裏で生成するリソースの変化を見落とすことだ。CDKのコード上は数行の変更でも、CloudFormation（CFn）レベルでは数十リソースが変わっている可能性がある。

### 推奨戦略：「CFn差分ガイド方式」

3つの方式を比較検討した結果、最も安全かつ正確なのは以下の方式だ。

**差分逐次変換方式**（CDKのgit diffだけを見てTerraformを書き換える）は、CDK抽象が隠す暗黙的リソースを見落とすリスクが高い。**全面再生成方式**（ブランチBから丸ごとTerraformを再生成してマージ）は正確だが、既存のTerraform構造やモジュール設計を破壊するリスクがある。

推奨するのは**CFn差分ガイド方式**で、CDKのコードdiffで「意図」を把握し、CFnテンプレートのdiffで「実際のリソース変更」を確認し、その両方をガイドにしてTerraformを修正する三層検証アプローチだ。

---

### 具体的な実行手順

#### ステップ1：CDKコードレベルの差分を取得し、変更の「意図」を把握する

```bash
# CDKリポジトリで差分を取得
cd /path/to/cdk-repo
git diff branchA..branchB -- lib/ bin/ > cdk_code_diff.patch

# 変更ファイル一覧（構造把握用）
git diff --stat branchA..branchB -- lib/ bin/
```

この段階では「何を変えたかったのか」というビジネス意図・設計意図を読み取ることに集中する。CDKのL2 Constructが変わったのか、新しいスタックが追加されたのか、パラメータが変わっただけなのか。Claude Codeに渡す際も、まずこのdiffを読ませて変更意図のサマリーを作らせるとよい。

#### ステップ2：CloudFormationテンプレートの差分で「実リソース変更」を特定する

```bash
# ブランチAでCFnテンプレートを生成
git checkout branchA
cdk synth --output=cdk.out.branchA

# ブランチBでCFnテンプレートを生成
git checkout branchB
cdk synth --output=cdk.out.branchB

# 各スタックのテンプレートを比較
diff -r cdk.out.branchA/ cdk.out.branchB/ > cfn_diff.txt
```

CFnテンプレートはJSON/YAMLなので、より精密に比較したい場合は `cfn-diff` ツールや、単純にjqで正規化してからdiffを取る方法もある。

```bash
# JSON正規化して比較（スタックごとに実行）
cat cdk.out.branchA/MyStack.template.json | jq -S . > a_normalized.json
cat cdk.out.branchB/MyStack.template.json | jq -S . > b_normalized.json
diff a_normalized.json b_normalized.json
```

**ここが最重要ステップ。** CFnテンプレートの差分が「真実」であり、Terraformに反映すべき変更の正確なリストになる。変更を以下の3カテゴリに分類する。

| カテゴリ | 例 | Terraformでの対応 |
|---|---|---|
| リソース追加 | 新しいLambda、SQSキューなど | 新規 `resource` ブロック追加 |
| リソース変更 | セキュリティグループのルール変更、Lambda設定変更 | 既存ブロックの属性修正 |
| リソース削除 | 不要になったリソース | `resource` ブロック削除 + `terraform state rm`（必要に応じて） |

#### ステップ3：変更単位の依存関係を整理し、適用順序を決定する

分類した変更を依存関係に従って並べる。たとえば「新しいIAMロール → 新しいLambda → 新しいAPI Gatewayルート」のように、Terraformの `depends_on` や参照関係を意識した順序で作業する。

Claude Codeへの指示としては、以下のようなプロンプト構造が有効だ。

```
以下はCDKブランチA→Bの差分です。

【CDKコードdiff】
{cdk_code_diff.patchの内容}

【CloudFormationテンプレートdiff】
{cfn_diff.txtの内容}

【現在のTerraformコード】
{既存のTerraformディレクトリ構造と主要ファイル}

上記に基づき、以下を実行してください：
1. CFn差分から、追加/変更/削除されたリソースを一覧化
2. 各リソースの依存関係を整理
3. 既存Terraformのモジュール構造に合わせて、変更を反映
4. 変更ごとに terraform plan で差分を確認できるよう、段階的に適用
```

#### ステップ4：Terraform変更の実装と段階的検証

ここが実作業の核心部分だ。以下の原則を守る。

**原則1：一度に全部変えない。** 変更をグループ単位（たとえばスタック単位、機能単位）で分けて、それぞれ `terraform plan` で検証してから次に進む。

**原則2：planの `destroy` に注目する。** `terraform plan` で意図しない `destroy` や `replace`（`forces replacement`）が出た場合、それはリソース再作成を意味する。本番データが消えるリスクがあるため、必ず立ち止まって確認する。

**原則3：既存リソースのimportが必要な場合がある。** CDKのブランチBで追加されたリソースが、既にAWS上に別の経路で存在している場合（手動作成など）、`terraform import` でstateに取り込む必要がある。ただし今回は「別アカウントにTerraformでデプロイ」した構成なので、基本的にはリソース追加＝新規作成になるはずだ。

**原則4：terraform MCPで最新プロバイダー仕様を確認する。** AWS Provider v5ではS3バケットの設定が分離されているなど、CDKのCFnテンプレートとTerraformのリソース定義が1対1対応しないケースがある。変換前に `hashicorp/terraform-mcp-server` で現行の引数仕様を確認すること。

#### ステップ5：検証とロールバック準備

```bash
# 全変更適用前に、現在のstateをバックアップ
terraform state pull > terraform.tfstate.backup_$(date +%Y%m%d)

# plan実行（変更グループごと）
terraform plan -var-file=env/prod.tfvars -out=plan.out

# planの内容を人間が確認した上でapply
terraform apply plan.out
```

万が一問題が起きた場合のロールバック手順も事前に決めておく。stateバックアップからの復元と、Git上のTerraformコードのrevertの両方が必要になる。

---

### 落とし穴と対策（プレモーテム分析）

**落とし穴1：CDKのContext値やFeature Flagの差異。** CDKは `cdk.json` の `context` や Feature Flagによって生成されるCFnが大きく変わる。ブランチA→Bで `cdk.json` も変わっていないか必ず確認する。見落とすとCFn差分の前提が崩れる。

**落とし穴2：CDKのL2 Constructが暗黙的に生成するリソースの見落とし。** たとえば `Function` Constructにイベントソースを追加すると、裏でIAMポリシー、EventSourceMapping、LogGroupなどが自動生成される。CDKコードdiffだけ見ると1行の追加だが、CFnでは5〜6リソースが増えている。だからこそCFn差分を「真実」として使う。

**落とし穴3：Terraformの `lifecycle` による意図しない挙動。** 既存Terraformに `ignore_changes` を設定しているリソースがある場合、plan上は差分なしと出るが実際のAWSリソースは古いままになる。変更対象リソースの `lifecycle` ブロックを確認すること。

**落とし穴4：CDKのOutputやExportの変更。** CDKスタック間のクロススタック参照が変わっている場合、Terraformでは `data` ソースや変数の参照構造を修正する必要がある。

---

### Claude Codeでの実践的なワークフロー

実際にClaude Codeで作業する際の推奨フローは次のとおり。

**第一段階：差分分析フェーズ。** CDKリポジトリをクローンし、上記のステップ1〜2をClaude Codeに実行させる。CFn差分の解析結果をmarkdownファイルとして出力させ、変更リソース一覧表を作る。この段階ではTerraformには一切触れない。

**第二段階：変換設計フェーズ。** 変更リソース一覧をもとに、既存Terraformのどのファイル・モジュールに変更を入れるかの設計書を作らせる。terraform MCPで最新の引数仕様も確認させる。設計書を人間がレビューする。

**第三段階：実装フェーズ。** 設計書に基づいてTerraformコードを修正させる。変更グループごとに `terraform plan` を実行し、期待どおりの差分が出ているか確認する。`destroy` や `replace` が出たら必ず一旦停止。

**第四段階：適用フェーズ。** planが問題なければ `terraform apply`。適用後に `terraform state list` でリソース一覧を確認し、期待どおりの状態になっているかを検証する。

---

### まとめ

核心は「CDKのコードdiffだけを信じない」ということに尽きる。CDKの抽象層は便利だが、裏で生成されるリソースの全容はCFnテンプレートにしか現れない。だからCFnテンプレートのdiffを「真実のソース」として使い、それをガイドにTerraformを修正する。この三層検証（CDKコード→CFnテンプレート→Terraform plan）を守れば、差分の見落としを最小限に抑えられる。

段階的に、検証しながら進めることが最大の安全策だ。一括変換の誘惑に負けず、変更グループごとにplan→確認→applyのサイクルを回してほしい。