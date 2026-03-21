#!/usr/bin/env python3
"""
S3 Download Script (Sync Mode)
CSVの1列目に記載された複数のS3バケットからローカルにダウンロードする。
既にダウンロード済みのファイルはETag/MD5比較でスキップする。
"""

import argparse
import csv
import hashlib
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# ── 定数 ─────────────────────────────────────────────
LOCAL_BASE_DIR = "s3_migration_data"

# ── ログ設定 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── ユーティリティ ────────────────────────────────────
def compute_md5(filepath: Path) -> str:
    """ローカルファイルのMD5ハッシュを計算し、S3のETagと比較可能な形式で返す。"""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return f'"{md5.hexdigest()}"'  # S3 ETag は "..." で囲まれている


def needs_download(s3_client, bucket: str, key: str, local_path: Path) -> bool:
    """
    ローカルファイルが存在し、かつ ETag が一致する場合は False（スキップ）。
    それ以外は True（ダウンロード必要）。
    注意: マルチパートアップロードされたオブジェクトの ETag は単純な MD5 ではないため、
          その場合は常にダウンロード対象とする。
    """
    if not local_path.exists():
        return True

    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError:
        return True

    etag = head.get("ETag", "")

    # マルチパートアップロードの ETag は "-" を含む（例: "abc123-5"）
    if "-" in etag:
        logger.debug("  マルチパートETag検出 -> ダウンロード対象: %s", key)
        return True

    local_md5 = compute_md5(local_path)
    return local_md5 != etag


# ── CSV 読み込み ──────────────────────────────────────
def read_source_buckets(csv_path: str) -> list[str]:
    """CSVの1列目（ダウンロード元バケット名）をリストで返す。"""
    buckets = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダー行スキップ
        for row_num, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                logger.warning("行 %d: 1列目が空のためスキップ", row_num)
                continue
            buckets.append(row[0].strip())
    return buckets


# ── メイン処理 ────────────────────────────────────────
def sync_download(s3_client, bucket: str, base_dir: Path, dry_run: bool) -> dict:
    """
    指定バケットの全オブジェクトをローカルにsyncダウンロードする。
    Returns: {"downloaded": int, "skipped": int, "errors": int}
    """
    stats = {"downloaded": 0, "skipped": 0, "errors": 0}
    bucket_dir = base_dir / bucket

    paginator = s3_client.get_paginator("list_objects_v2")

    try:
        page_iterator = paginator.paginate(Bucket=bucket)
    except ClientError as e:
        logger.error("バケット '%s' の一覧取得に失敗: %s", bucket, e)
        stats["errors"] += 1
        return stats

    for page in page_iterator:
        if "Contents" not in page:
            logger.info("バケット '%s' にオブジェクトがありません。", bucket)
            break

        for obj in page["Contents"]:
            key = obj["Key"]

            # ディレクトリマーカー（末尾 / のキー）はスキップ
            if key.endswith("/"):
                continue

            local_path = bucket_dir / key

            try:
                if not needs_download(s3_client, bucket, key, local_path):
                    logger.info("  SKIP (同一): %s", key)
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    logger.info("  [DRY-RUN] DOWNLOAD: %s", key)
                    stats["downloaded"] += 1
                    continue

                # ディレクトリ作成（フォルダ構造維持）
                local_path.parent.mkdir(parents=True, exist_ok=True)

                logger.info("  DOWNLOAD: %s -> %s", key, local_path)
                s3_client.download_file(bucket, key, str(local_path))
                stats["downloaded"] += 1

            except (BotoCoreError, ClientError) as e:
                logger.error("  ERROR: %s -> %s", key, e)
                stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="S3バケットからローカルへの同期ダウンロード"
    )
    parser.add_argument(
        "--csv", required=True, help="バケット情報CSVファイルのパス"
    )
    parser.add_argument(
        "--profile", required=True, help="AWS CLIプロファイル名（ダウンロード元アカウント）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のダウンロードを行わず、対象ファイルの確認のみ",
    )
    args = parser.parse_args()

    # CSV 存在チェック
    if not os.path.isfile(args.csv):
        logger.error("CSVファイルが見つかりません: %s", args.csv)
        sys.exit(1)

    # AWS セッション作成
    try:
        session = boto3.Session(profile_name=args.profile)
        s3_client = session.client("s3")
    except Exception as e:
        logger.error("AWSセッションの作成に失敗しました（profile=%s）: %s", args.profile, e)
        sys.exit(1)

    # CSV からバケットリスト取得
    source_buckets = read_source_buckets(args.csv)
    if not source_buckets:
        logger.error("CSVにダウンロード対象のバケットがありません。")
        sys.exit(1)

    # 保存先ベースディレクトリ作成
    base_dir = Path.cwd() / LOCAL_BASE_DIR
    base_dir.mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("S3 Sync Download 開始")
    logger.info("  CSV       : %s", args.csv)
    logger.info("  Profile   : %s", args.profile)
    logger.info("  保存先    : %s", base_dir)
    logger.info("  Dry-run   : %s", args.dry_run)
    logger.info("  対象バケット数: %d", len(source_buckets))
    logger.info("=" * 60)

    total_stats = {"downloaded": 0, "skipped": 0, "errors": 0}

    for bucket in source_buckets:
        logger.info("-" * 40)
        logger.info("バケット: %s", bucket)
        stats = sync_download(s3_client, bucket, base_dir, args.dry_run)
        for k in total_stats:
            total_stats[k] += stats[k]
        logger.info(
            "  結果 -> ダウンロード: %d, スキップ: %d, エラー: %d",
            stats["downloaded"],
            stats["skipped"],
            stats["errors"],
        )

    logger.info("=" * 60)
    logger.info("全体結果")
    logger.info("  ダウンロード: %d", total_stats["downloaded"])
    logger.info("  スキップ    : %d", total_stats["skipped"])
    logger.info("  エラー      : %d", total_stats["errors"])
    logger.info("=" * 60)

    if total_stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
