#!/usr/bin/env python3
"""
S3 Upload Script (Sync Mode)
CSVの1列目バケット名に対応するローカルディレクトリのファイルを、
2列目のバケットへアップロードする。
既にアップロード済みのファイルはETag/MD5比較でスキップする。
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
    return f'"{md5.hexdigest()}"'


def needs_upload(s3_client, bucket: str, key: str, local_path: Path) -> bool:
    """
    アップロード先に同一ファイルが存在し、ETag が一致する場合は False（スキップ）。
    それ以外は True（アップロード必要）。
    """
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        # 404 = オブジェクト未存在 → アップロード必要
        if e.response["Error"]["Code"] == "404":
            return True
        raise

    etag = head.get("ETag", "")

    # マルチパートアップロードの ETag は比較不可 → アップロード対象
    if "-" in etag:
        logger.debug("  マルチパートETag検出 -> アップロード対象: %s", key)
        return True

    local_md5 = compute_md5(local_path)
    return local_md5 != etag


# ── CSV 読み込み ──────────────────────────────────────
def read_bucket_mappings(csv_path: str) -> list[tuple[str, str]]:
    """CSVから (ソースバケット名, アップロード先バケット名) のリストを返す。"""
    mappings = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダー行スキップ
        for row_num, row in enumerate(reader, start=2):
            if len(row) < 2:
                logger.warning("行 %d: 列数不足のためスキップ", row_num)
                continue
            source = row[0].strip()
            dest = row[1].strip()
            if not source or not dest:
                logger.warning("行 %d: バケット名が空のためスキップ", row_num)
                continue
            mappings.append((source, dest))
    return mappings


# ── メイン処理 ────────────────────────────────────────
def sync_upload(
    s3_client, source_bucket: str, dest_bucket: str, base_dir: Path, dry_run: bool
) -> dict:
    """
    ローカルの source_bucket ディレクトリ内ファイルを dest_bucket へ sync アップロード。
    Returns: {"uploaded": int, "skipped": int, "errors": int}
    """
    stats = {"uploaded": 0, "skipped": 0, "errors": 0}
    source_dir = base_dir / source_bucket

    if not source_dir.exists():
        logger.error(
            "ローカルディレクトリが見つかりません: %s（先にダウンロードを実行してください）",
            source_dir,
        )
        stats["errors"] += 1
        return stats

    # ローカルファイルを走査
    for local_path in source_dir.rglob("*"):
        if local_path.is_dir():
            continue

        # S3キー = ローカルディレクトリからの相対パス（常に / 区切り）
        key = local_path.relative_to(source_dir).as_posix()

        try:
            if not needs_upload(s3_client, dest_bucket, key, local_path):
                logger.info("  SKIP (同一): %s", key)
                stats["skipped"] += 1
                continue

            if dry_run:
                logger.info("  [DRY-RUN] UPLOAD: %s -> s3://%s/%s", key, dest_bucket, key)
                stats["uploaded"] += 1
                continue

            logger.info("  UPLOAD: %s -> s3://%s/%s", local_path, dest_bucket, key)
            s3_client.upload_file(str(local_path), dest_bucket, key)
            stats["uploaded"] += 1

        except (BotoCoreError, ClientError) as e:
            logger.error("  ERROR: %s -> %s", key, e)
            stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="ローカルからS3バケットへの同期アップロード"
    )
    parser.add_argument(
        "--csv", required=True, help="バケット情報CSVファイルのパス"
    )
    parser.add_argument(
        "--profile", required=True, help="AWS CLIプロファイル名（アップロード先アカウント）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のアップロードを行わず、対象ファイルの確認のみ",
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

    # CSV からマッピング取得
    mappings = read_bucket_mappings(args.csv)
    if not mappings:
        logger.error("CSVにアップロード対象のバケットマッピングがありません。")
        sys.exit(1)

    # 保存先ベースディレクトリ確認
    base_dir = Path.cwd() / LOCAL_BASE_DIR
    if not base_dir.exists():
        logger.error(
            "保存ディレクトリが見つかりません: %s（先にダウンロードを実行してください）",
            base_dir,
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("S3 Sync Upload 開始")
    logger.info("  CSV       : %s", args.csv)
    logger.info("  Profile   : %s", args.profile)
    logger.info("  データ元  : %s", base_dir)
    logger.info("  Dry-run   : %s", args.dry_run)
    logger.info("  対象マッピング数: %d", len(mappings))
    logger.info("=" * 60)

    total_stats = {"uploaded": 0, "skipped": 0, "errors": 0}

    for source_bucket, dest_bucket in mappings:
        logger.info("-" * 40)
        logger.info("マッピング: %s -> %s", source_bucket, dest_bucket)
        stats = sync_upload(s3_client, source_bucket, dest_bucket, base_dir, dry_run=args.dry_run)
        for k in total_stats:
            total_stats[k] += stats[k]
        logger.info(
            "  結果 -> アップロード: %d, スキップ: %d, エラー: %d",
            stats["uploaded"],
            stats["skipped"],
            stats["errors"],
        )

    logger.info("=" * 60)
    logger.info("全体結果")
    logger.info("  アップロード: %d", total_stats["uploaded"])
    logger.info("  スキップ    : %d", total_stats["skipped"])
    logger.info("  エラー      : %d", total_stats["errors"])
    logger.info("=" * 60)

    if total_stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
