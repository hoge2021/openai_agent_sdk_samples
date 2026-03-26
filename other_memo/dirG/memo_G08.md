#!/usr/bin/env python3
"""
DynamoDB ダウンロード同期スクリプト
====================================
アカウントAのDynamoDBテーブルデータをローカルにJSON形式でダウンロードします。
既存のローカルデータがある場合はハッシュ比較による差分同期を行います。

使い方:
    python dynamodb_download_sync.py --profile account-a --region ap-northeast-1 --csv config.csv
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import glob
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, ProfileNotFound, NoCredentialsError


# =============================================================================
# 定数
# =============================================================================
SYNC_DATA_DIR = "dynamo_sync_data"


# =============================================================================
# ユーティリティ関数
# =============================================================================
class DecimalEncoder(json.JSONEncoder):
    """DynamoDBのDecimal型をJSON変換するためのエンコーダー"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # 整数ならintに、小数ならfloatに変換
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super().default(obj)


def load_csv_table_names(csv_path: str) -> list[str]:
    """CSVファイルからテーブル名リストを読み込む"""
    if not os.path.exists(csv_path):
        print(f"[エラー] CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    table_names = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip():
                table_names.append(row[0].strip())

    if not table_names:
        print("[エラー] CSVファイルにテーブル名が記載されていません。")
        sys.exit(1)

    return table_names


def create_dynamodb_client(profile_name: str, region: str):
    """AWS名前付きプロファイルでDynamoDBクライアントを作成"""
    try:
        session = boto3.Session(profile_name=profile_name, region_name=region)
        client = session.resource("dynamodb")
        # 接続テスト
        session.client("sts").get_caller_identity()
        return client, session
    except ProfileNotFound:
        print(f"[エラー] AWSプロファイル '{profile_name}' が見つかりません。")
        print("  ~/.aws/credentials に設定されているか確認してください。")
        sys.exit(1)
    except NoCredentialsError:
        print(f"[エラー] AWSプロファイル '{profile_name}' の認証情報が不正です。")
        sys.exit(1)
    except ClientError as e:
        print(f"[エラー] AWS接続に失敗しました: {e}")
        sys.exit(1)


def get_table_key_schema(session, table_name: str, region: str) -> list[dict]:
    """テーブルのキースキーマ（パーティションキー・ソートキー）を自動取得"""
    client = session.client("dynamodb", region_name=region)
    try:
        response = client.describe_table(TableName=table_name)
        return response["Table"]["KeySchema"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"  [警告] テーブル '{table_name}' が見つかりません。スキップします。")
            return None
        raise


def scan_all_items(dynamodb_resource, table_name: str) -> list[dict]:
    """テーブルの全アイテムをスキャン（ページネーション対応）"""
    table = dynamodb_resource.Table(table_name)
    items = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        # ページネーション: LastEvaluatedKeyがあれば次ページ
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def compute_item_hash(item: dict) -> str:
    """アイテム全体のSHA256ハッシュを計算（差分検出用）"""
    # キーの順序を統一してハッシュ化
    item_str = json.dumps(item, sort_keys=True, cls=DecimalEncoder)
    return hashlib.sha256(item_str.encode("utf-8")).hexdigest()


def build_item_key(item: dict, key_schema: list[dict]) -> str:
    """アイテムのプライマリキー値を文字列化（辞書キーとして使用）"""
    key_parts = []
    for key_def in sorted(key_schema, key=lambda x: x["KeyType"]):
        attr_name = key_def["AttributeName"]
        value = item.get(attr_name, "")
        key_parts.append(f"{attr_name}={value}")
    return "|".join(key_parts)


def find_latest_local_file(table_dir: str, table_name: str) -> str | None:
    """テーブルディレクトリ内の最新JSONファイルを検索"""
    pattern = os.path.join(table_dir, f"{table_name}_*.json")
    files = sorted(glob.glob(pattern))
    if files:
        return files[-1]
    return None


def load_local_items(file_path: str) -> list[dict]:
    """ローカルJSONファイルからアイテムリストを読み込み"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])


# =============================================================================
# メイン同期処理
# =============================================================================
def sync_download_table(
    dynamodb_resource,
    session,
    table_name: str,
    region: str,
    base_dir: str,
) -> dict:
    """
    1つのテーブルに対してダウンロード同期を実行する。

    Returns:
        同期結果の辞書 {"added": int, "modified": int, "deleted": int, "unchanged": int}
    """
    print(f"\n{'='*60}")
    print(f"  テーブル: {table_name}")
    print(f"{'='*60}")

    # --- キースキーマ取得 ---
    key_schema = get_table_key_schema(session, table_name, region)
    if key_schema is None:
        return None

    key_names = [k["AttributeName"] for k in key_schema]
    print(f"  キー構成: {', '.join(key_names)}")

    # --- リモート全アイテム取得 ---
    print(f"  リモートデータをスキャン中...")
    remote_items = scan_all_items(dynamodb_resource, table_name)
    print(f"  リモートアイテム数: {len(remote_items)}")

    # --- リモートのハッシュマップ作成 ---
    remote_hash_map = {}
    for item in remote_items:
        item_key = build_item_key(item, key_schema)
        item_hash = compute_item_hash(item)
        remote_hash_map[item_key] = item_hash

    # --- ローカル既存データとの差分比較 ---
    table_dir = os.path.join(base_dir, table_name)
    os.makedirs(table_dir, exist_ok=True)

    latest_file = find_latest_local_file(table_dir, table_name)

    added = 0
    modified = 0
    deleted = 0
    unchanged = 0

    if latest_file:
        print(f"  既存ローカルファイル: {os.path.basename(latest_file)}")
        local_items = load_local_items(latest_file)

        # ローカルのハッシュマップ作成
        local_hash_map = {}
        for item in local_items:
            item_key = build_item_key(item, key_schema)
            item_hash = compute_item_hash(item)
            local_hash_map[item_key] = item_hash

        # 差分検出
        all_keys = set(remote_hash_map.keys()) | set(local_hash_map.keys())
        for key in all_keys:
            in_remote = key in remote_hash_map
            in_local = key in local_hash_map

            if in_remote and not in_local:
                added += 1
            elif not in_remote and in_local:
                deleted += 1
            elif remote_hash_map[key] != local_hash_map[key]:
                modified += 1
            else:
                unchanged += 1

        print(f"  --- 差分結果 ---")
        print(f"    追加:   {added} 件")
        print(f"    変更:   {modified} 件")
        print(f"    削除:   {deleted} 件")
        print(f"    変更なし: {unchanged} 件")

        if added == 0 and modified == 0 and deleted == 0:
            print(f"  → 差分なし。ダウンロードをスキップします。")
            return {"added": 0, "modified": 0, "deleted": 0, "unchanged": unchanged}
    else:
        print(f"  既存ローカルファイルなし（初回ダウンロード）")
        added = len(remote_items)

    # --- JSONファイルとして保存 ---
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table_name}_{now_str}.json"
    file_path = os.path.join(table_dir, filename)

    save_data = {
        "table_name": table_name,
        "key_schema": key_schema,
        "downloaded_at": datetime.now().isoformat(),
        "item_count": len(remote_items),
        "items": remote_items,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)

    file_size_kb = os.path.getsize(file_path) / 1024
    print(f"  → 保存完了: {filename} ({file_size_kb:.1f} KB)")

    return {"added": added, "modified": modified, "deleted": deleted, "unchanged": unchanged}


# =============================================================================
# エントリポイント
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="DynamoDB ダウンロード同期スクリプト（アカウントA → ローカル）"
    )
    parser.add_argument(
        "--profile", required=True,
        help="AWS CLIプロファイル名（ダウンロード元アカウント）"
    )
    parser.add_argument(
        "--region", default="ap-northeast-1",
        help="AWSリージョン（デフォルト: ap-northeast-1）"
    )
    parser.add_argument(
        "--csv", default="config.csv",
        help="テーブル名一覧CSVファイルのパス（デフォルト: config.csv）"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  DynamoDB ダウンロード同期ツール")
    print("=" * 60)
    print(f"  プロファイル: {args.profile}")
    print(f"  リージョン:   {args.region}")
    print(f"  CSVファイル:  {args.csv}")

    # --- CSVからテーブル名読み込み ---
    table_names = load_csv_table_names(args.csv)
    print(f"  対象テーブル: {len(table_names)} 個")
    for name in table_names:
        print(f"    - {name}")

    # --- DynamoDBクライアント作成 ---
    dynamodb_resource, session = create_dynamodb_client(args.profile, args.region)
    print(f"\n  AWS接続成功 ✓")

    # --- 保存先ディレクトリ作成 ---
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), SYNC_DATA_DIR)
    os.makedirs(base_dir, exist_ok=True)
    print(f"  保存先: {base_dir}")

    # --- 各テーブルの同期実行 ---
    results = {}
    for table_name in table_names:
        result = sync_download_table(
            dynamodb_resource, session, table_name, args.region, base_dir
        )
        results[table_name] = result

    # --- 結果サマリ ---
    print(f"\n{'='*60}")
    print("  ダウンロード同期 完了サマリ")
    print(f"{'='*60}")
    for table_name, result in results.items():
        if result is None:
            print(f"  {table_name}: スキップ（テーブル不存在）")
        else:
            total_changes = result["added"] + result["modified"] + result["deleted"]
            if total_changes == 0:
                print(f"  {table_name}: 差分なし（{result['unchanged']} 件）")
            else:
                print(
                    f"  {table_name}: "
                    f"追加={result['added']} 変更={result['modified']} "
                    f"削除={result['deleted']} 変更なし={result['unchanged']}"
                )

    print(f"\n完了しました。")


if __name__ == "__main__":
    main()
