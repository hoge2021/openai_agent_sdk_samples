# S3 バケット移行ツール

異なるAWSアカウント間でS3バケットのデータを移行するためのスクリプトセットです。

## 前提条件

- Python 3.9 以上
- `boto3` がインストール済み（`pip install boto3`）
- AWS CLI の named profile が設定済み
  - ダウンロード元アカウント用のプロファイル
  - アップロード先アカウント用のプロファイル

## ファイル構成

```
├── s3_download.py       # ダウンロードスクリプト
├── s3_upload.py         # アップロードスクリプト
├── buckets_sample.csv   # CSVサンプル
└── s3_migration_data/   # 自動作成される保存ディレクトリ
    ├── <source-bucket-a>/
    │   ├── file1.txt
    │   └── subdir/file2.txt
    └── <source-bucket-b>/
        └── ...
```

## CSV フォーマット

```csv
source_bucket,dest_bucket
移行元バケット名,移行先バケット名
```

- 1行目はヘッダー（スキップされます）
- 1列目: ダウンロード元のS3バケット名
- 2列目: アップロード先のS3バケット名

## 使い方

### Step 1: ダウンロード（元アカウントからローカルへ）

```bash
# dry-run で対象ファイルを確認
python s3_download.py --csv buckets.csv --profile source-account --dry-run

# 実行
python s3_download.py --csv buckets.csv --profile source-account
```

### Step 2: アップロード（ローカルから先アカウントへ）

```bash
# dry-run で対象ファイルを確認
python s3_upload.py --csv buckets.csv --profile dest-account --dry-run

# 実行
python s3_upload.py --csv buckets.csv --profile dest-account
```

## sync（同期）動作

両スクリプトとも差分転送（sync）方式で動作します。

- ファイルの ETag（MD5ハッシュ）を比較し、一致するファイルはスキップ
- 2回目以降の実行では、変更・追加されたファイルのみ転送
- マルチパートアップロードされたオブジェクト（ETagに `-` を含む）は常に転送対象

## 引数一覧

| 引数 | 必須 | 説明 |
|------|------|------|
| `--csv` | ✅ | バケット情報CSVファイルのパス |
| `--profile` | ✅ | AWS CLIプロファイル名 |
| `--dry-run` | - | 転送せず対象ファイルの確認のみ |

## エラーハンドリング

- バケット単位で try/except 処理。1つのバケットが失敗しても残りは続行します。
- エラーが1件以上ある場合、スクリプトは終了コード 1 で終了します。
