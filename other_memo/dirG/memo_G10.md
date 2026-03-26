#!/usr/bin/env python3
"""
DynamoDB アップロード同期スクリプト
====================================
ローカルにダウンロードしたJSONデータをアカウントBのDynamoDBにアップロードします。
アップロード前に既存データのバックアップを作成し、ハッシュ比較による差分同期を行います。

使い方:
    python dynamodb_upload_sync.py --profile account-b --region ap-northeast-1 --csv config.csv
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import glob
import time
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, ProfileNotFound, NoCredentialsError


# =============================================================================
# 定数
# =============================================================================
SYNC_DATA_DIR = "dynamo_sync_data"
BACKUP_DATA_DIR = "dynamo_backup_data"

# batch_write_item のバッチサイズ上限
BATCH_WRITE_MAX = 25


# =============================================================================
# ユーティリティ関数
# =============================================================================
class DecimalEncoder(json.JSONEncoder):
    """DynamoDBのDecimal型をJSON変換するためのエンコーダー"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super().default(obj)


def convert_floats_to_decimal(obj):
    """JSONから読み込んだfloat値をDynamoDB用のDecimalに変換する（再帰的）"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    return obj


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


def get_table_key_schema(session, table_name: str, region: str) -> list[dict] | None:
    """テーブルのキースキーマを自動取得"""
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
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def compute_item_hash(item: dict) -> str:
    """アイテム全体のSHA256ハッシュを計算"""
    item_str = json.dumps(item, sort_keys=True, cls=DecimalEncoder)
    return hashlib.sha256(item_str.encode("utf-8")).hexdigest()


def build_item_key(item: dict, key_schema: list[dict]) -> str:
    """アイテムのプライマリキー値を文字列化"""
    key_parts = []
    for key_def in sorted(key_schema, key=lambda x: x["KeyType"]):
        attr_name = key_def["AttributeName"]
        value = item.get(attr_name, "")
        key_parts.append(f"{attr_name}={value}")
    return "|".join(key_parts)


def extract_key_from_item(item: dict, key_schema: list[dict]) -> dict:
    """アイテムからプライマリキー部分だけを抽出"""
    key = {}
    for key_def in key_schema:
        attr_name = key_def["AttributeName"]
        key[attr_name] = item[attr_name]
    return key


def find_latest_local_file(table_dir: str, table_name: str) -> str | None:
    """テーブルディレクトリ内の最新JSONファイルを検索"""
    pattern = os.path.join(table_dir, f"{table_name}_*.json")
    files = sorted(glob.glob(pattern))
    if files:
        return files[-1]
    return None


def load_local_data(file_path: str) -> dict:
    """ローカルJSONファイルを読み込む"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# バックアップ処理
# =============================================================================
def backup_remote_table(
    dynamodb_resource,
    table_name: str,
    key_schema: list[dict],
    backup_base_dir: str,
) -> str | None:
    """
    アップロード先テーブルの既存データをバックアップする。
    データがない場合はNoneを返す。
    """
    print(f"  アップロード先のデータを確認中...")
    remote_items = scan_all_items(dynamodb_resource, table_name)

    if not remote_items:
        print(f"  → アップロード先にデータなし。バックアップ不要。")
        return None

    print(f"  → 既存データ {len(remote_items)} 件を発見。バックアップします...")

    # バックアップディレクトリ作成
    backup_table_dir = os.path.join(backup_base_dir, table_name)
    os.makedirs(backup_table_dir, exist_ok=True)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{table_name}_backup_{now_str}.json"
    backup_path = os.path.join(backup_table_dir, backup_filename)

    backup_data = {
        "table_name": table_name,
        "key_schema": key_schema,
        "backed_up_at": datetime.now().isoformat(),
        "item_count": len(remote_items),
        "items": remote_items,
    }

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)

    file_size_kb = os.path.getsize(backup_path) / 1024
    print(f"  → バックアップ完了: {backup_filename} ({file_size_kb:.1f} KB)")
    return backup_path


# =============================================================================
# 同期書き込み処理
# =============================================================================
def put_items_batch(dynamodb_resource, table_name: str, items: list[dict]):
    """複数アイテムを batch_write_item で書き込み（25件ずつ）"""
    table = dynamodb_resource.Table(table_name)

    for i in range(0, len(items), BATCH_WRITE_MAX):
        batch = items[i : i + BATCH_WRITE_MAX]
        with table.batch_writer() as writer:
            for item in batch:
                # float/int を Decimal に変換
                converted_item = convert_floats_to_decimal(item)
                writer.put_item(Item=converted_item)
        # スロットリング対策: バッチ間に少し待機
        if i + BATCH_WRITE_MAX < len(items):
            time.sleep(0.5)


def delete_items_batch(
    dynamodb_resource,
    table_name: str,
    items: list[dict],
    key_schema: list[dict],
):
    """複数アイテムを batch_write_item で削除（25件ずつ）"""
    table = dynamodb_resource.Table(table_name)

    for i in range(0, len(items), BATCH_WRITE_MAX):
        batch = items[i : i + BATCH_WRITE_MAX]
        with table.batch_writer() as writer:
            for item in batch:
                key = extract_key_from_item(item, key_schema)
                converted_key = convert_floats_to_decimal(key)
                writer.delete_item(Key=converted_key)
        if i + BATCH_WRITE_MAX < len(items):
            time.sleep(0.5)


# =============================================================================
# メイン同期処理
# =============================================================================
def sync_upload_table(
    dynamodb_resource,
    session,
    table_name: str,
    region: str,
    sync_base_dir: str,
    backup_base_dir: str,
) -> dict | None:
    """
    1つのテーブルに対してアップロード同期を実行する。

    Returns:
        同期結果の辞書、またはNone（スキップ時）
    """
    print(f"\n{'='*60}")
    print(f"  テーブル: {table_name}")
    print(f"{'='*60}")

    # --- ローカルの同期データを検索 ---
    table_dir = os.path.join(sync_base_dir, table_name)
    if not os.path.exists(table_dir):
        print(f"  [警告] ローカルデータが見つかりません: {table_dir}")
        print(f"  → 先にダウンロード同期を実行してください。スキップします。")
        return None

    latest_file = find_latest_local_file(table_dir, table_name)
    if not latest_file:
        print(f"  [警告] JSONファイルが見つかりません。スキップします。")
        return None

    print(f"  ローカルデータ: {os.path.basename(latest_file)}")

    # --- ローカルデータ読み込み ---
    local_data = load_local_data(latest_file)
    local_items = local_data.get("items", [])
    key_schema = local_data.get("key_schema", [])

    if not key_schema:
        # ローカルJSONにキースキーマが保存されていない場合、リモートから取得
        key_schema = get_table_key_schema(session, table_name, region)
        if key_schema is None:
            return None

    key_names = [k["AttributeName"] for k in key_schema]
    print(f"  キー構成: {', '.join(key_names)}")
    print(f"  ローカルアイテム数: {len(local_items)}")

    # --- アップロード先のキースキーマを確認（テーブル存在チェック兼用）---
    remote_key_schema = get_table_key_schema(session, table_name, region)
    if remote_key_schema is None:
        print(f"  [エラー] アップロード先にテーブル '{table_name}' が存在しません。")
        print(f"  → テーブルを先に作成してください。スキップします。")
        return None

    # --- バックアップ ---
    backup_remote_table(dynamodb_resource, table_name, key_schema, backup_base_dir)

    # --- リモートの現在のデータをスキャン ---
    print(f"  アップロード先データをスキャン中...")
    remote_items = scan_all_items(dynamodb_resource, table_name)
    print(f"  アップロード先アイテム数: {len(remote_items)}")

    # --- ハッシュ比較で差分検出 ---
    local_hash_map = {}
    local_item_map = {}
    for item in local_items:
        item_key = build_item_key(item, key_schema)
        local_hash_map[item_key] = compute_item_hash(item)
        local_item_map[item_key] = item

    remote_hash_map = {}
    remote_item_map = {}
    for item in remote_items:
        item_key = build_item_key(item, key_schema)
        remote_hash_map[item_key] = compute_item_hash(item)
        remote_item_map[item_key] = item

    # 差分分類
    items_to_add = []       # ローカルにあってリモートにない
    items_to_modify = []    # 両方にあるがハッシュが違う
    items_to_delete = []    # リモートにあってローカルにない
    unchanged = 0

    all_keys = set(local_hash_map.keys()) | set(remote_hash_map.keys())
    for key in all_keys:
        in_local = key in local_hash_map
        in_remote = key in remote_hash_map

        if in_local and not in_remote:
            items_to_add.append(local_item_map[key])
        elif not in_local and in_remote:
            items_to_delete.append(remote_item_map[key])
        elif local_hash_map[key] != remote_hash_map[key]:
            items_to_modify.append(local_item_map[key])
        else:
            unchanged += 1

    print(f"  --- 差分結果 ---")
    print(f"    追加:   {len(items_to_add)} 件")
    print(f"    変更:   {len(items_to_modify)} 件")
    print(f"    削除:   {len(items_to_delete)} 件")
    print(f"    変更なし: {unchanged} 件")

    if not items_to_add and not items_to_modify and not items_to_delete:
        print(f"  → 差分なし。アップロードをスキップします。")
        return {
            "added": 0, "modified": 0, "deleted": 0, "unchanged": unchanged,
            "backup": False,
        }

    # --- 差分をアップロード ---
    if items_to_add:
        print(f"  追加アイテムを書き込み中... ({len(items_to_add)} 件)")
        put_items_batch(dynamodb_resource, table_name, items_to_add)

    if items_to_modify:
        print(f"  変更アイテムを上書き中... ({len(items_to_modify)} 件)")
        put_items_batch(dynamodb_resource, table_name, items_to_modify)

    if items_to_delete:
        print(f"  削除アイテムを削除中... ({len(items_to_delete)} 件)")
        delete_items_batch(dynamodb_resource, table_name, items_to_delete, key_schema)

    print(f"  → 同期完了 ✓")

    return {
        "added": len(items_to_add),
        "modified": len(items_to_modify),
        "deleted": len(items_to_delete),
        "unchanged": unchanged,
        "backup": True,
    }


# =============================================================================
# エントリポイント
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="DynamoDB アップロード同期スクリプト（ローカル → アカウントB）"
    )
    parser.add_argument(
        "--profile", required=True,
        help="AWS CLIプロファイル名（アップロード先アカウント）"
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
    print("  DynamoDB アップロード同期ツール")
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

    # --- ディレクトリパス ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sync_base_dir = os.path.join(script_dir, SYNC_DATA_DIR)
    backup_base_dir = os.path.join(script_dir, BACKUP_DATA_DIR)
    os.makedirs(backup_base_dir, exist_ok=True)

    print(f"  同期データ元:   {sync_base_dir}")
    print(f"  バックアップ先: {backup_base_dir}")

    # --- 確認プロンプト ---
    print(f"\n  ⚠ アカウントBのDynamoDBテーブルにデータを書き込みます。")
    confirm = input("  続行しますか？ (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  中止しました。")
        sys.exit(0)

    # --- 各テーブルの同期実行 ---
    results = {}
    for table_name in table_names:
        result = sync_upload_table(
            dynamodb_resource, session, table_name, args.region,
            sync_base_dir, backup_base_dir,
        )
        results[table_name] = result

    # --- 結果サマリ ---
    print(f"\n{'='*60}")
    print("  アップロード同期 完了サマリ")
    print(f"{'='*60}")
    for table_name, result in results.items():
        if result is None:
            print(f"  {table_name}: スキップ")
        else:
            total = result["added"] + result["modified"] + result["deleted"]
            if total == 0:
                print(f"  {table_name}: 差分なし（{result['unchanged']} 件）")
            else:
                backup_mark = " [バックアップ済]" if result.get("backup") else ""
                print(
                    f"  {table_name}: "
                    f"追加={result['added']} 変更={result['modified']} "
                    f"削除={result['deleted']} 変更なし={result['unchanged']}"
                    f"{backup_mark}"
                )

    print(f"\n完了しました。")


if __name__ == "__main__":
    main()
