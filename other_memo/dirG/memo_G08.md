# DynamoDB クロスアカウント同期ツール 使い方マニュアル

このツールは、**AWSアカウントA**のDynamoDBテーブルデータを**AWSアカウントB**のDynamoDBにコピー（同期）するためのPythonスクリプトです。

---

## 目次

1. [このツールでできること](#1-このツールでできること)
2. [必要な前提条件](#2-必要な前提条件)
3. [セットアップ手順](#3-セットアップ手順)
4. [CSVファイルの準備](#4-csvファイルの準備)
5. [ダウンロード同期の実行](#5-ダウンロード同期の実行)
6. [アップロード同期の実行](#6-アップロード同期の実行)
7. [ディレクトリ構成の説明](#7-ディレクトリ構成の説明)
8. [差分同期の仕組み](#8-差分同期の仕組み)
9. [コマンドオプション一覧](#9-コマンドオプション一覧)
10. [よくあるエラーと対処法](#10-よくあるエラーと対処法)
11. [注意事項・制限事項](#11-注意事項制限事項)

---

## 1. このツールでできること

```
アカウントA (DynamoDB)
       │
       ▼  dynamodb_download_sync.py（ダウンロード）
  あなたのPC (JSONファイルとしてローカル保存)
       │
       ▼  dynamodb_upload_sync.py（アップロード）
アカウントB (DynamoDB)
```

- **ダウンロードスクリプト**: アカウントAのDynamoDBテーブルを丸ごとローカルPCにJSON形式で保存します。2回目以降は**差分だけ**を検出し、変更がないテーブルはスキップします。
- **アップロードスクリプト**: ローカルに保存したJSONデータを、アカウントBのDynamoDBに書き込みます。書き込み前に**既存データの自動バックアップ**を取得し、**差分だけ**を反映します。

---

## 2. 必要な前提条件

以下が揃っていることを確認してください。

### パソコン環境

| 項目 | 条件 |
|------|------|
| OS | Windows 11 または macOS |
| Python | 3.10 以上 |
| pip | Pythonと一緒にインストール済み |

### AWS環境

| 項目 | 条件 |
|------|------|
| AWS CLI | インストール・設定済み |
| AWSプロファイル | アカウントA用・B用の2つの名前付きプロファイル |
| IAM権限 | 後述の権限が付与されていること |
| DynamoDBテーブル | アカウントBにもテーブルが**事前に作成済み**であること |

### 必要なIAM権限

ダウンロード元（アカウントA）のIAMユーザー/ロールに必要な権限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

アップロード先（アカウントB）のIAMユーザー/ロールに必要な権限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

> **💡 ヒント**: セキュリティのため、`Resource` にはワイルドカード(`*`)ではなく、対象テーブルのARNを個別指定することをお勧めします。

---

## 3. セットアップ手順

### 3-1. AWS CLIプロファイルの設定

まだプロファイルを設定していない場合、以下のコマンドで設定します。

```bash
# アカウントA用のプロファイルを作成
aws configure --profile account-a

# 以下の情報を入力:
#   AWS Access Key ID: （アカウントAのアクセスキー）
#   AWS Secret Access Key: （アカウントAのシークレットキー）
#   Default region name: ap-northeast-1
#   Default output format: json

# アカウントB用のプロファイルを作成
aws configure --profile account-b

# 同様にアカウントBの情報を入力
```

設定されたプロファイルは以下のファイルに保存されます:

- **Windows**: `C:\Users\（ユーザー名）\.aws\credentials`
- **macOS**: `~/.aws/credentials`

プロファイルが正しく設定されたか確認:

```bash
aws sts get-caller-identity --profile account-a
aws sts get-caller-identity --profile account-b
```

### 3-2. Pythonパッケージのインストール

```bash
# スクリプトのあるディレクトリに移動
cd /path/to/dynamodb-sync-tool

# 必要パッケージをインストール
pip install -r requirements.txt
```

> **📝 補足**: `pip install boto3` だけでもOKです。

---

## 4. CSVファイルの準備

同期したいDynamoDBテーブル名を `config.csv` に記述します。

### CSVファイルの書き方

```csv
users
orders
products
```

**ルール:**
- 1行に1つのテーブル名を記載
- ヘッダー行は**不要**
- テーブル名の前後に余分なスペースがあっても自動で除去されます
- 空行は無視されます

### 入力例

同期したいテーブルが `customer_data` と `transaction_log` の2つだけの場合:

```csv
customer_data
transaction_log
```

---

## 5. ダウンロード同期の実行

アカウントAのDynamoDBテーブルをローカルにダウンロードします。

### 基本コマンド

```bash
python dynamodb_download_sync.py --profile account-a --region ap-northeast-1 --csv config.csv
```

### 実行例と出力

```
============================================================
  DynamoDB ダウンロード同期ツール
============================================================
  プロファイル: account-a
  リージョン:   ap-northeast-1
  CSVファイル:  config.csv
  対象テーブル: 2 個
    - users
    - orders

  AWS接続成功 ✓
  保存先: /path/to/dynamo_sync_data

============================================================
  テーブル: users
============================================================
  キー構成: user_id
  リモートデータをスキャン中...
  リモートアイテム数: 150
  既存ローカルファイルなし（初回ダウンロード）
  → 保存完了: users_20260326_143000.json (45.2 KB)

============================================================
  テーブル: orders
============================================================
  キー構成: order_id, created_at
  リモートデータをスキャン中...
  リモートアイテム数: 500
  既存ローカルファイル: orders_20260325_100000.json
  --- 差分結果 ---
    追加:   12 件
    変更:   3 件
    削除:   1 件
    変更なし: 484 件
  → 保存完了: orders_20260326_143000.json (180.5 KB)

============================================================
  ダウンロード同期 完了サマリ
============================================================
  users: 追加=150 変更=0 削除=0 変更なし=0
  orders: 追加=12 変更=3 削除=1 変更なし=484

完了しました。
```

### 2回目以降の挙動

2回目以降は差分同期が動作します。前回ダウンロードしたJSONと比較して:

- **差分あり** → 最新データを新しいタイムスタンプ付きJSONとして保存
- **差分なし** → 「差分なし。ダウンロードをスキップします。」と表示し、新しいファイルは作成しません

---

## 6. アップロード同期の実行

ローカルのJSONデータをアカウントBのDynamoDBにアップロードします。

### 基本コマンド

```bash
python dynamodb_upload_sync.py --profile account-b --region ap-northeast-1 --csv config.csv
```

### 実行の流れ

1. ローカルの `dynamo_sync_data/` から最新のJSONを読み込み
2. アカウントBのテーブルにデータがある場合は自動バックアップ
3. ローカルデータとアカウントBのデータをハッシュ比較
4. 差分（追加・変更・削除）のみを反映
5. 実行前に確認プロンプト（`yes`で続行、`no`で中止）

### 実行例

```
  ⚠ アカウントBのDynamoDBテーブルにデータを書き込みます。
  続行しますか？ (yes/no): yes
```

> **⚠ 重要**: `yes` を入力するまでデータの書き込みは行われません。

---

## 7. ディレクトリ構成の説明

ツール実行後、以下のようなディレクトリが自動作成されます。

```
your-project/
├── dynamodb_download_sync.py   ← ダウンロードスクリプト
├── dynamodb_upload_sync.py     ← アップロードスクリプト
├── config.csv                  ← テーブル名一覧
├── requirements.txt            ← 依存パッケージ
│
├── dynamo_sync_data/           ← 【自動作成】ダウンロードデータの保存先
│   ├── users/
│   │   ├── users_20260325_100000.json    ← 1回目のスナップショット
│   │   └── users_20260326_143000.json    ← 2回目のスナップショット
│   └── orders/
│       └── orders_20260326_143000.json
│
└── dynamo_backup_data/         ← 【自動作成】アップロード前のバックアップ先
    ├── users/
    │   └── users_backup_20260326_150000.json
    └── orders/
        └── orders_backup_20260326_150000.json
```

### JSONファイルの中身（例）

```json
{
  "table_name": "users",
  "key_schema": [
    { "AttributeName": "user_id", "KeyType": "HASH" }
  ],
  "downloaded_at": "2026-03-26T14:30:00.123456",
  "item_count": 150,
  "items": [
    {
      "user_id": "u-001",
      "name": "田中太郎",
      "email": "tanaka@example.com"
    },
    ...
  ]
}
```

---

## 8. 差分同期の仕組み

このツールは**全アイテムのハッシュ比較**で差分を検出します。

### 仕組みの詳細

1. テーブルの全アイテムを取得
2. 各アイテムに対して SHA256 ハッシュを計算（アイテム全体のJSON文字列から算出）
3. プライマリキーの値をキーとして「ハッシュマップ」を作成
4. ローカル側とリモート側のハッシュマップを比較

### 差分の分類

| 状態 | 判定条件 | 処理 |
|------|----------|------|
| **追加** | ソース側にあり、ターゲット側にない | put_item で追加 |
| **変更** | 両方にあるがハッシュ値が異なる | put_item で上書き |
| **削除** | ターゲット側にあり、ソース側にない | delete_item で削除 |
| **変更なし** | 両方にあり、ハッシュ値が同一 | 何もしない |

> **📝 注意**: この方式はアイテム数が多い場合（数万件以上）、全件スキャンに時間がかかります。データ量が非常に大きい場合は、DynamoDB Streamsなど別の方式を検討してください。

---

## 9. コマンドオプション一覧

### dynamodb_download_sync.py

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--profile` | ✅ | — | ダウンロード元のAWSプロファイル名 |
| `--region` | — | `ap-northeast-1` | AWSリージョン |
| `--csv` | — | `config.csv` | テーブル名一覧CSVファイルのパス |

### dynamodb_upload_sync.py

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--profile` | ✅ | — | アップロード先のAWSプロファイル名 |
| `--region` | — | `ap-northeast-1` | AWSリージョン |
| `--csv` | — | `config.csv` | テーブル名一覧CSVファイルのパス |

### 実行例の一覧

```bash
# 基本的な使い方
python dynamodb_download_sync.py --profile account-a
python dynamodb_upload_sync.py --profile account-b

# リージョンとCSVを明示指定
python dynamodb_download_sync.py --profile account-a --region ap-northeast-1 --csv my_tables.csv

# 東京リージョン以外を使う場合
python dynamodb_download_sync.py --profile account-a --region us-east-1
```

---

## 10. よくあるエラーと対処法

### AWSプロファイルが見つからない

```
[エラー] AWSプロファイル 'account-a' が見つかりません。
```

**対処法**: `aws configure --profile account-a` でプロファイルを作成してください。

---

### テーブルが見つからない

```
[警告] テーブル 'users' が見つかりません。スキップします。
```

**対処法**: CSVに記載したテーブル名がDynamoDBに実際に存在するか確認してください。テーブル名は**大文字・小文字を区別**します。

---

### 権限エラー

```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException)
```

**対処法**: IAMユーザー/ロールに「2. 必要な前提条件」に記載した権限が付与されているか確認してください。

---

### ローカルデータが見つからない（アップロード時）

```
[警告] ローカルデータが見つかりません
→ 先にダウンロード同期を実行してください。
```

**対処法**: アップロード前に、必ずダウンロードスクリプトを先に実行してください。

---

### boto3がインストールされていない

```
ModuleNotFoundError: No module named 'boto3'
```

**対処法**: `pip install boto3` を実行してください。

---

## 11. 注意事項・制限事項

### 重要な注意事項

- **アカウントBのテーブルは事前に作成してください**: このツールはテーブルの自動作成は行いません。テーブル構成（キースキーマ、キャパシティ設定）はAWSコンソールやCLIで事前に作成する必要があります。
- **大量データに注意**: 全件スキャンを行うため、数万件以上のデータがある場合は時間がかかります。DynamoDBの読み取りキャパシティを事前に確認してください。
- **本番環境への適用は慎重に**: アップロードスクリプトは `delete_item` を実行する可能性があります。本番環境に適用する前に、必ずテスト環境で動作確認してください。
- **バックアップの確認**: アップロード前のバックアップは `dynamo_backup_data/` に保存されます。万が一のために、バックアップファイルの内容を確認してから作業を進めてください。

### 制限事項

- DynamoDBの1テーブルあたりのアイテムサイズ上限（400KB）を超えるアイテムは扱えません。
- DynamoDB Streams や Global Tables との連携は対象外です。
- テーブルのインデックス（GSI/LSI）の設定は同期されません（データのみ）。
- 同時に複数人がこのツールを実行した場合、データの整合性は保証されません。

---

## クイックスタート（まとめ）

初めて使う場合は、以下の5ステップだけで実行できます。

```bash
# Step 1: パッケージインストール
pip install boto3

# Step 2: CSVにテーブル名を記述
echo "my_table_name" > config.csv

# Step 3: アカウントAからダウンロード
python dynamodb_download_sync.py --profile account-a

# Step 4: ダウンロードしたデータを確認
ls dynamo_sync_data/

# Step 5: アカウントBにアップロード
python dynamodb_upload_sync.py --profile account-b
```


Requirements.txt
boto3>=1.34.0
