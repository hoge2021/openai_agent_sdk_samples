## Step 2: 戦略的ワークフロー（Mermaid図）---

## Step 3: 手順書（完成版）

---

# 📘 CDK差分をTerraformに反映する手順書

**対象読者:** Terraform・Claude Code初心者の方
**環境:** Windows 11 / PowerShell
**所要時間の目安:** 2〜4時間（差分の規模による）

---

## 🗺️ 全体の流れ（これを頭に入れてから作業してください）

```
ブランチA（元のCDK）
        ↓
ブランチB（更新後のCDK）との差分を確認
        ↓
差分を3種類に仕分け
 ├─ ① CDKインフラ定義の変更  → Terraform HCLを書き換える
 ├─ ② Lambdaの関数コードの変更 → ソースファイルを差し替える
 └─ ③ Lambdaレイヤーの変更   → レイヤーのソースを差し替える
        ↓
terraform plan で変更内容を確認
        ↓
terraform apply でAWSに反映
        ↓
動作確認・完了
```

---

## 📋 第0章：作業前の準備確認

作業を始める前に、以下がすべて揃っているか確認してください。

### 0-1. 必要なツールの確認

PowerShellを開いて、以下を1行ずつ実行してください。

```powershell
# Gitが使えるか確認
git --version
# 例: git version 2.xx.x が表示されればOK

# Terraformが使えるか確認
terraform --version
# 例: Terraform v1.x.x が表示されればOK

# Claude Codeが使えるか確認
claude --version
# 例: バージョン番号が表示されればOK

# AWS CLIが使えるか確認
aws --version
# 例: aws-cli/2.x.x が表示されればOK
```

> ⚠️ **もしエラーが出たら:** インストールされていないツールがあります。先にインストールを完了させてから戻ってきてください。

### 0-2. AWSの認証情報の確認

```powershell
# AWSに正しくログインできているか確認（SSOを使っている場合）
aws sso login --profile <あなたのプロファイル名>

# ログインできているか確認
aws sts get-caller-identity --profile <あなたのプロファイル名>
# 「Account」「UserId」が表示されればOK
```

### 0-3. 作業フォルダの確認

今回の作業で使うフォルダ構成をあらかじめ把握しておきます。

```powershell
# CDKリポジトリのフォルダに移動（パスは自分の環境に合わせて変更）
cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>

# Terraformのフォルダに移動（パスは自分の環境に合わせて変更）
cd C:\Users\<あなたのユーザー名>\<TerraformのフォルダのパスF>
```

---

## 📋 第1章：差分を確認する

まず「ブランチAとブランチBで何が変わったのか」を正確に把握します。

### 1-1. CDKリポジトリへ移動してブランチを準備する

```powershell
# CDKリポジトリのフォルダへ移動
cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>

# リモートの最新情報を取得
git fetch origin

# 現在のブランチを確認（今どこにいるか分かります）
git branch -a
```

### 1-2. 変更されたファイルの一覧を確認する

```powershell
# ブランチAとブランチBで変わったファイルの一覧を表示
git diff origin/ブランチA origin/ブランチB --name-only
```

実行すると、以下のようにファイル名の一覧が表示されます。

```
lib/my-stack.ts               ← CDKインフラ定義ファイル
src/lambda/handler.py         ← Lambda関数のコード
layers/my-layer/requirements.txt  ← Lambdaレイヤーの定義
```

> 💡 `--name-only` は「ファイル名だけを表示する」オプションです。まずは何が変わったかを一覧で把握しましょう。

### 1-3. 差分の詳細内容を確認する

```powershell
# 変更内容の詳細を表示（追加は「+」、削除は「-」で表示されます）
git diff origin/ブランチA origin/ブランチB
```

> 💡 表示が長い場合は、`q` キーを押すと終了できます。

### 1-4. 変更ファイルを3種類に仕分けるメモを作る

確認した差分を、以下の3種類に分類してメモしておきます（後の作業で使います）。

| 種類 | 特徴 | 例 |
|------|------|----|
| ① CDKインフラ定義 | `lib/` フォルダ内の `.ts` や `.py` ファイル | `lib/my-stack.ts` |
| ② Lambda関数コード | `src/lambda/` などのハンドラーファイル | `handler.py`, `index.js` |
| ③ Lambdaレイヤー | `layers/` フォルダ内のファイル | `requirements.txt`, `package.json` |

---

## 📋 第2章：Claude Codeで差分を分析する

差分の内容をそのまま読み解くのは難しいため、Claude Codeに分析を依頼します。

### 2-1. Claude Codeを起動する

```powershell
# CDKリポジトリのフォルダで Claude Code を起動
cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>
claude
```

### 2-2. 差分ファイルをClaude Codeに渡して分析依頼する

Claude Codeが起動したら、以下のプロンプトを貼り付けて送信します。

```
以下のコマンドを実行して、ブランチAとブランチBの差分を取得してください。
そして、各変更がTerraformのどのリソース・どのファイルに影響するかを
初心者にもわかるよう箇条書きで説明してください。

git diff origin/ブランチA origin/ブランチB

出力形式：
- 変更ファイル名
  - 何が変わったか（1〜2行で）
  - Terraformで対応が必要な箇所（ファイル名と変更内容）
  - 対応の優先度（高/中/低）
```

### 2-3. 分析結果を確認・保存する

Claude Codeの出力を確認し、内容をテキストファイルに保存しておきます。

```powershell
# 分析結果を保存するファイルを作成（Claude Codeを一度終了してから実行）
# Claude Code内で以下のようなコマンドも使えます
# /save analysis_result.txt  （Claude Codeのsaveコマンドを使う場合）
```

> ✅ **確認ポイント:** Claude Codeの分析で「このCDKの変更は Terraform のどのファイルの何行目に影響するか」が明確になっていれば、次の章に進んでください。

---

## 📋 第3章：Terraformに反映する

分析結果をもとに、実際にTerraformのコードを更新します。種類ごとに順番に対応します。

---

### 3-1. Lambda関数コードの更新（② に該当するファイル）

Lambda関数のコード（Pythonなら `.py`、Node.jsなら `.js`/`.ts` ファイルなど）が変わった場合の対応です。

#### ステップA: 変更されたコードを確認する

```powershell
# CDKリポジトリでブランチBに切り替えて、最新のコードを取得
cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>
git checkout origin/ブランチB -- src/lambda/handler.py
# ↑ 「src/lambda/handler.py」は実際のパスに変えてください
```

#### ステップB: TerraformのLambdaソースフォルダへコピーする

```powershell
# コピー元（CDKのコード）のパス例
$source = "C:\Users\<あなたのユーザー名>\<CDKのリポジトリ>\src\lambda\handler.py"

# コピー先（TerraformのLambdaソースフォルダ）のパス例
$dest = "C:\Users\<あなたのユーザー名>\<Terraformフォルダ>\modules\lambda\src\"

# コピー実行
Copy-Item -Path $source -Destination $dest -Force

# コピーされたか確認
Get-ChildItem $dest
```

> 💡 **Terraformのフォルダ構成例:**
> ```
> terraform/
>   ├─ modules/
>   │   └─ lambda/
>   │       └─ src/         ← ここにLambdaのコードを置く
>   ├─ main.tf
>   └─ variables.tf
> ```

> ⚠️ **注意:** Terraformの `aws_lambda_function` リソースで `source_code_hash` を使っている場合は、コードを差し替えると自動的に再デプロイされます。これが正しい動作です。

---

### 3-2. Lambdaレイヤーの更新（③ に該当するファイル）

`requirements.txt` や `package.json` などのレイヤー定義ファイルが変わった場合の対応です。

#### ステップA: ブランチBのレイヤーファイルを取得する

```powershell
# CDKリポジトリでブランチBのレイヤーファイルを取得
cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>
git checkout origin/ブランチB -- layers/my-layer/requirements.txt
# ↑ 「layers/my-layer/requirements.txt」は実際のパスに変えてください
```

#### ステップB: レイヤーをビルドする（Pythonの場合の例）

```powershell
# TerraformのLambdaレイヤーのビルドフォルダへ移動
cd C:\Users\<あなたのユーザー名>\<Terraformフォルダ>\modules\lambda_layer\

# 既存のビルド済みフォルダを削除（クリーンビルドのため）
Remove-Item -Recurse -Force .\python\ -ErrorAction SilentlyContinue

# 新しいrequirements.txtをコピー
Copy-Item "C:\...\layers\my-layer\requirements.txt" .\ -Force

# Dockerを使ってAmazon Linux互換でビルド（推奨）
docker run --rm -v "${PWD}:/var/task" public.ecr.aws/sam/build-python3.12:latest `
  pip install -r requirements.txt -t python/

# もしDockerが使えない場合（Pythonバージョンが一致している場合のみ）
pip install -r requirements.txt -t python/ --platform manylinux2014_x86_64 --only-binary :all:
```

> 💡 **なぜDockerを使うのか?**
> AWSのLambdaはAmazon Linux上で動いています。Windowsで直接ビルドすると、ライブラリがLinuxと互換性のない形式でインストールされることがあります。Dockerを使うとLinux環境でビルドできるため安全です。

#### ステップC: zipファイルにまとめる

TerraformはLambdaレイヤーをzipファイルとしてアップロードします。

```powershell
# ビルドしたフォルダをzipに圧縮
Compress-Archive -Path .\python\ -DestinationPath .\layer.zip -Force

# zipが作成されたか確認
Get-ChildItem .\layer.zip
```

> 💡 **Terraformのレイヤー定義がある場合、自動でzipを作成する設定になっていることもあります。**
> Terraformの `aws_lambda_layer_version` リソースに `source_dir` が設定されていれば、`terraform apply` 時に自動でzip化されます。その場合このステップは不要です。Claude Codeに確認してもらいましょう。

---

### 3-3. CDKインフラ定義の変更をTerraform HCLに反映する（① に該当するファイル）

これが最も重要かつ慎重な作業です。CDKのコードはTypeScript/Pythonで書かれていますが、TerraformはHCL（独自言語）で書かれています。Claude Codeに翻訳を依頼します。

#### ステップA: 変更されたCDKファイルの差分をClaude Codeに見せる

```powershell
# TerraformのフォルダでClaude Codeを起動
cd C:\Users\<あなたのユーザー名>\<Terraformフォルダ>
claude
```

Claude Codeに以下のプロンプトを送信します。

```
以下の作業を順番にお願いします。

1. まず、CDKリポジトリの以下のコマンドを実行して差分を確認してください:
   cd C:\Users\<あなたのユーザー名>\<CDKのリポジトリフォルダ>
   git diff origin/ブランチA origin/ブランチB -- lib/my-stack.ts

2. 現在のTerraformフォルダの構成を確認してください:
   Get-ChildItem -Recurse *.tf

3. CDKの変更内容を分析して、Terraformのどのファイルをどのように変更すべきか教えてください。
   変更案を提示する前に、必ず既存のTerraformコードの内容を確認してから提案してください。

4. 私の確認を取った上で、Terraformファイルを実際に書き換えてください。
```

> ⚠️ **重要:** 「私の確認を取った上で」というフレーズを必ず含めてください。Claude Codeが自動で書き換えを始める前に、変更内容を確認する機会を設けるためです。

#### ステップB: Claude Codeの提案内容を確認する

Claude Codeが提案した内容を確認します。以下の点をチェックしてください。

```
チェックリスト:
□ リソースタイプが正しいか（例: aws_lambda_function, aws_iam_role など）
□ 既存のリソース名・変数名と整合しているか
□ 環境変数（prod/staging）が正しく設定されているか
□ 削除が必要なリソースはないか（CDKで削除されたものがあれば、Terraformからも削除が必要）
```

> 💡 **不安な場合は:** 「この変更で影響を受けるAWSリソースを全て列挙してください」とClaude Codeに追加で聞きましょう。

#### ステップC: 承認してClaude Codeに実際の変更を依頼する

内容を確認したら、Claude Codeに変更の実施を依頼します。

```
内容を確認しました。提案された変更をTerraformファイルに反映してください。
変更後は diff を見せてください（git diff や 変更前後の比較）。
```

---

## 📋 第4章：Terraformでデプロイする

Terraformファイルの更新が完了したら、実際にAWSへ反映します。

### 4-1. 構文チェック（文法エラーがないか確認）

```powershell
# TerraformフォルダでPowerShellを開く
cd C:\Users\<あなたのユーザー名>\<Terraformフォルダ>

# 構文チェック（エラーがなければ "Success!" と表示されます）
terraform validate
```

> ⚠️ **エラーが出た場合:** エラーメッセージをコピーしてClaude Codeに貼り付けると修正方法を教えてくれます。

### 4-2. terraform plan（変更内容のプレビュー）

```powershell
# まずstagingで確認する場合
terraform plan -var-file="staging.tfvars"

# 本番で確認する場合
terraform plan -var-file="prod.tfvars"
```

実行すると以下のような出力が表示されます。意味を理解してから次のステップに進みましょう。

```
# aws_lambda_function.my_function will be updated in-place
~ resource "aws_lambda_function" "my_function" {
    ...
    ~ source_code_hash = "xxxx" -> "yyyy"   ← コードが変わります
  }

# aws_lambda_layer_version.my_layer will be created
+ resource "aws_lambda_layer_version" "my_layer" {  ← 新しいバージョンが作られます
    ...
  }

Plan: 1 to add, 1 to change, 0 to destroy.
```

| 記号 | 意味 | 安全性 |
|------|------|--------|
| `+` | 新しく作成される | 通常は安全 |
| `~` | 既存のリソースを変更 | 内容をよく確認する |
| `-` | 削除される | **必ず意図した削除か確認する** |
| `-/+` | 一度削除して再作成 | **ダウンタイムが発生することがある** |

> ⚠️ **`-`（削除）や `-/+`（再作成）が意図していないリソースに出た場合は、必ずClaude Codeに相談してから進めてください。**

### 4-3. terraform apply（実際にAWSへ反映）

planの内容を確認して問題なければ、applyを実行します。

```powershell
# stagingへ適用する場合
terraform apply -var-file="staging.tfvars"

# 実行確認のメッセージが出るので「yes」と入力してEnter
# Do you want to perform these actions?
#   Enter a value: yes
```

```powershell
# 本番へ適用する場合（先にstagingで確認してから！）
terraform apply -var-file="prod.tfvars"
```

実行が完了すると以下のように表示されます。

```
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
```

---

## 📋 第5章：動作確認

デプロイが完了したら、正しく反映されているか確認します。

### 5-1. AWSコンソールで確認する

```powershell
# AWSコンソールを開くコマンド（デフォルトブラウザで開きます）
Start-Process "https://console.aws.amazon.com/lambda/"
```

確認する項目：
- Lambda関数のコードが最新バージョンになっているか
- レイヤーが新しいバージョン番号になっているか
- 環境変数が正しく設定されているか

### 5-2. Lambda関数をテスト実行する

```powershell
# Lambda関数のテスト実行（関数名・プロファイルは実際のものに変更）
aws lambda invoke `
  --function-name <Lambda関数名> `
  --payload '{"key": "value"}' `
  --profile <あなたのプロファイル名> `
  response.json

# レスポンスを確認
Get-Content response.json
```

### 5-3. ログを確認する

```powershell
# 直近のログを確認
aws logs tail /aws/lambda/<Lambda関数名> `
  --since 10m `
  --profile <あなたのプロファイル名>
```

> ✅ **エラーが出ずに期待した結果が返ってくれば作業完了です！**

---

## 🚨 トラブルシューティング（よくあるエラーと対処法）

### エラー1: `Error: Error acquiring the state lock`

```
原因: 前回のterraform実行が異常終了し、ロックが残っている
対処:
```

```powershell
terraform force-unlock <LOCK_ID>
# LOCK_IDはエラーメッセージに記載されています
```

### エラー2: `Error: Provider configuration not present`

```
原因: AWSの認証情報が正しく設定されていない
対処:
```

```powershell
aws sso login --profile <プロファイル名>
# ログイン後、再度terraform planを実行
```

### エラー3: Lambda関数のランタイムエラー

```
原因: レイヤーのライブラリが正しくインストールされていない
対処: CloudWatch Logsでエラー内容を確認し、requirements.txtを見直す
```

```powershell
# ログを確認
aws logs tail /aws/lambda/<関数名> --since 5m --profile <プロファイル名>
```

### エラー4: `Error: error creating Lambda Layer Version`

```
原因: zipファイルのサイズが大きすぎる、またはパスが間違っている
対処: Claude Codeにエラーメッセージを貼り付けて確認を依頼する
```

---

## 📝 作業完了チェックリスト

作業が終わったら、以下を確認してください。

```
□ git diff で確認した全ての変更ファイルに対応した
□ terraform plan で意図しない削除（-）がなかった
□ terraform apply が "Apply complete!" で終了した
□ Lambda関数のテスト実行が成功した
□ CloudWatch Logsにエラーが出ていない
□ staging環境で確認してから本番に適用した
```

---

## 💡 作業全体を通じたClaude Codeの活用ポイント

| 場面 | Claude Codeへの依頼例 |
|------|----------------------|
| 差分の意味が分からない | 「このgit diffの変更がTerraformに何をもたらすか教えて」 |
| HCLへの翻訳が不安 | 「このCDKコードに相当するTerraform HCLを書いて。既存コードと整合性を取ること」 |
| planの結果が不安 | 「このterraform planの出力で影響が大きいリソースはどれか」 |
| エラーが出た | エラーメッセージをそのままコピーして貼り付ける |
| リカバリが必要 | 「apply前の状態に戻すにはどうすればいいか」 |

> 💡 **最後に一言:** CDKとTerraformの差分反映は、慣れるまで複雑に感じますが、「何が変わったか把握 → Claude Codeで翻訳 → planで確認 → applyで適用」という4ステップを守れば、安全に進められます。不明な点はその都度Claude Codeに質問しながら進めましょう。
