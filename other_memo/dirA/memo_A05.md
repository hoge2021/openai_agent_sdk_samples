#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
コードファイルに日本語コメントを自動追加するツール
対象ファイル: .py, .tsx, .ts
空のファイルは自動的にスキップ
ディレクトリとファイルの両方を指定可能
複数ファイルをまとめて処理（バッチ処理）
copilotコマンドを使用
"""

import os
import sys
import argparse
import subprocess
import signal
from pathlib import Path
from typing import List, Set, Tuple

# 対象となるファイル拡張子
TARGET_EXTENSIONS = {'.py', '.tsx', '.ts'}

# デフォルトのバッチサイズ
DEFAULT_BATCH_SIZE = 5

# グローバル変数（中断処理用）
interrupted = False


def signal_handler(signum, frame):
    """
    Ctrl+C割り込みハンドラ
    """
    global interrupted
    interrupted = True
    print("\n\n" + "=" * 60)
    print("【中断】処理を中断しています...")
    print("=" * 60)


def parse_arguments() -> Tuple[List[str], int]:
    """
    コマンドライン引数を解析してパスのリストとバッチサイズを返す
    
    Returns:
        Tuple[List[str], int]: (指定されたパスのリスト, バッチサイズ)
    """
    parser = argparse.ArgumentParser(
        description='指定ディレクトリ内またはファイルに日本語コメントを追加（copilotを使用）'
    )
    parser.add_argument(
        'paths',
        nargs='+',  # 1つ以上の引数を必須とする
        help='検索対象のディレクトリパスまたはファイルパス（複数指定可能）'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'一度に処理するファイル数（デフォルト: {DEFAULT_BATCH_SIZE}）'
    )
    
    args = parser.parse_args()
    
    # バッチサイズの検証
    if args.batch_size < 1:
        print("エラー: バッチサイズは1以上である必要があります")
        sys.exit(1)
    
    return args.paths, args.batch_size


def validate_and_classify_paths(paths: List[str]) -> Tuple[List[Path], List[Path]]:
    """
    指定されたパスの妥当性を検証し、ディレクトリとファイルに分類
    
    Args:
        paths: 検証するパスのリスト
    
    Returns:
        Tuple[List[Path], List[Path]]: (有効なディレクトリのリスト, 有効なファイルのリスト)
    
    Raises:
        SystemExit: 無効なパスが存在する場合
    """
    valid_directories = []
    valid_files = []
    errors = []
    
    for path_str in paths:
        # 相対パス・絶対パスの両方に対応
        path = Path(path_str).resolve()
        
        if not path.exists():
            errors.append(f"  ✗ {path_str}: 存在しません")
        elif path.is_dir():
            valid_directories.append(path)
            print(f"  ✓ [ディレクトリ] {path}")
        elif path.is_file():
            # ファイルの拡張子をチェック
            if path.suffix.lower() in TARGET_EXTENSIONS:
                valid_files.append(path)
                print(f"  ✓ [ファイル] {path}")
            else:
                errors.append(f"  ✗ {path_str}: 対象外の拡張子です（{path.suffix}）")
        else:
            errors.append(f"  ✗ {path_str}: ディレクトリでもファイルでもありません")
    
    if errors:
        print("\n以下のエラーが見つかりました:")
        for error in errors:
            print(error)
        print("\n処理を中断します。")
        sys.exit(1)
    
    return valid_directories, valid_files


def is_empty_file(file_path: Path) -> bool:
    """
    ファイルが空かどうかを判定
    空白文字（スペース、タブ、改行）のみのファイルも空として扱う
    
    Args:
        file_path: チェック対象のファイルパス
    
    Returns:
        bool: ファイルが空の場合True
    """
    try:
        # ファイルサイズが0の場合
        if file_path.stat().st_size == 0:
            return True
        
        # ファイルの内容を読み込んで、空白文字のみかチェック
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # 空白文字を除去して何も残らない場合は空とみなす
            if not content.strip():
                return True
                
        return False
        
    except Exception as e:
        # 読み取りエラーが発生した場合は、安全のため空でないとみなす
        print(f"    警告: ファイルの読み取りに失敗しました: {e}")
        return False


def find_target_files(directory: Path) -> List[Path]:
    """
    指定ディレクトリ配下から対象ファイルを再帰的に検索
    
    Args:
        directory: 検索対象のディレクトリ
    
    Returns:
        List[Path]: 見つかった対象ファイルのPathオブジェクトリスト
    """
    target_files = []
    
    # ディレクトリを再帰的に探索
    for root, dirs, files in os.walk(directory):
        # 隠しディレクトリをスキップ（オプション）
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            file_path = Path(root) / file
            # 拡張子をチェック
            if file_path.suffix.lower() in TARGET_EXTENSIONS:
                target_files.append(file_path.resolve())
    
    return target_files


def collect_all_files(directories: List[Path], files: List[Path]) -> Tuple[List[Path], List[Path]]:
    """
    すべての処理対象ファイルを収集し、空ファイルと有効ファイルに分類
    
    Args:
        directories: 検索対象のディレクトリリスト
        files: 直接指定されたファイルリスト
    
    Returns:
        Tuple[List[Path], List[Path]]: (有効なファイルのリスト, 空ファイルのリスト)
    """
    all_files = []
    empty_files = []
    
    # ディレクトリから検索
    for directory in directories:
        found_files = find_target_files(directory)
        for f in found_files:
            if is_empty_file(f):
                empty_files.append(f)
            else:
                all_files.append(f)
    
    # 直接指定されたファイル
    for f in files:
        if is_empty_file(f):
            empty_files.append(f)
        else:
            all_files.append(f)
    
    # 重複を除去
    all_files = list(set(all_files))
    empty_files = list(set(empty_files))
    
    return all_files, empty_files


def create_batches(files: List[Path], batch_size: int) -> List[List[Path]]:
    """
    ファイルリストをバッチに分割
    
    Args:
        files: ファイルのリスト
        batch_size: バッチサイズ
    
    Returns:
        List[List[Path]]: バッチに分割されたファイルリスト
    """
    batches = []
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        batches.append(batch)
    return batches


def confirm_execution(all_files: List[Path], empty_files: List[Path], batch_size: int) -> bool:
    """
    ユーザーに実行確認を求める
    
    Args:
        all_files: 処理対象のファイルリスト
        empty_files: スキップする空ファイルのリスト
        batch_size: バッチサイズ
    
    Returns:
        bool: 続行する場合True、中断する場合False
    """
    print("\n" + "="*60)
    print("【実行確認】")
    print("="*60)
    
    print(f"\n検出されたファイル:")
    print(f"  処理対象: {len(all_files)} ファイル")
    print(f"  空ファイル（スキップ）: {len(empty_files)} ファイル")
    print(f"  合計: {len(all_files) + len(empty_files)} ファイル")
    
    if all_files:
        # バッチ情報を表示
        num_batches = (len(all_files) + batch_size - 1) // batch_size
        print(f"\nバッチ処理設定:")
        print(f"  バッチサイズ: {batch_size} ファイル/バッチ")
        print(f"  バッチ数: {num_batches} バッチ")
        
        # 拡張子ごとに集計
        ext_count = {}
        for f in all_files:
            ext = f.suffix.lower()
            ext_count[ext] = ext_count.get(ext, 0) + 1
        
        print(f"\n処理対象ファイルの詳細:")
        for ext, count in sorted(ext_count.items()):
            print(f"  {ext}: {count} ファイル")
        
        # 最初の5個を表示
        print(f"\n処理対象ファイル（最初の5個）:")
        for f in all_files[:5]:
            print(f"  • {f.name}")
        if len(all_files) > 5:
            print(f"  ... 他{len(all_files) - 5}個")
    
    if empty_files and len(empty_files) <= 5:
        print(f"\nスキップされる空ファイル:")
        for f in empty_files:
            print(f"  ○ {f.name}")
    elif empty_files:
        print(f"\nスキップされる空ファイル（最初の5個）:")
        for f in empty_files[:5]:
            print(f"  ○ {f.name}")
        print(f"  ... 他{len(empty_files) - 5}個")
    
    if not all_files:
        print("\n処理対象のファイルがありません。")
        return False
    
    print("\n" + "="*60)
    print("※ 処理中はCtrl+Cで中断可能")
    print("="*60)
    
    while True:
        response = input(f"\n{len(all_files)}個のファイルを{batch_size}個ずつ処理します。続行しますか？ (はい/いいえ): ").strip().lower()
        
        if response in ['はい', 'yes', 'y']:
            return True
        elif response in ['いいえ', 'no', 'n']:
            print("処理を中断しました。")
            return False
        else:
            print("「はい」または「いいえ」で答えてください。")


def process_files_batch(file_batch: List[Path], batch_num: int, total_batches: int) -> Tuple[int, int]:
    """
    複数ファイルをまとめてcopilotコマンドを実行
    
    Args:
        file_batch: 処理対象ファイルのバッチ
        batch_num: 現在のバッチ番号
        total_batches: 総バッチ数
    
    Returns:
        Tuple[int, int]: (成功数, 失敗数)
    """
    global interrupted
    
    if interrupted:
        return 0, 0
    
    print(f"\n" + "="*50)
    print(f"バッチ {batch_num}/{total_batches} の処理を開始")
    print(f"対象ファイル数: {len(file_batch)}個")
    print("="*50)
    
    # ファイルパスを改行区切りの文字列にする
    file_paths_str = "\n".join([str(f) for f in file_batch])
    
    # 各ファイルの情報を表示
    for i, file_path in enumerate(file_batch, 1):
        print(f"  [{i}] {file_path.name}")
        print(f"      パス: {file_path}")
        print(f"      サイズ: {file_path.stat().st_size:,} bytes")
    
    # コマンドの構築
    prompt = (
        f"<メインのタスク>\n"
        f"まずserenaのmcpサーバを用いてコードベース全体を把握しなさい。\n"
        f"次に以下の{len(file_batch)}個の対象ソースコードについて、以下の処理を実行しなさい。\n"
        f"</メインのタスク>\n"
        f"<対象ソースコード>\n"
        f"{file_paths_str}\n"
        f"</対象ソースコード>\n"
        f"<処理>\n"
        f"次に高校生初心者でも理解できるよう、各ソースコードの随所に日本語のコメントを挿入して。\n"
        f"※ライブラリの説明(非常に重要)、関数やクラスの概要、難しい箇所の補足、とにかくコメントは多めに。\n"
        f"※補足:英語のコメントは全て日本語に翻訳して。\n"
        f"※補足:ソースコードの処理内容はそのままで。\n"
        f"重要:仕上げにコードベースの一部としてソースがどんな動きをしているか、ソースの一番冒頭に記述すること。\n"
        f"</処理>"
    )
    
    command = [
        "copilot",
        "-p",
        prompt,
        "--model",
        "claude-sonnet-4",
        "--allow-all-tools"
    ]
    
    print(f"\n処理を実行中...")
    
    try:
        # コマンドを実行（プロセスを起動）
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # プロセスの完了を待つ（割り込み可能）
        while process.poll() is None:
            if interrupted:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return 0, len(file_batch)
        
        # 終了コードをチェック
        if process.returncode == 0:
            print(f"✓ バッチ処理完了")
            stdout, _ = process.communicate()
            if stdout and stdout.strip():
                print(f"出力: {stdout[:200]}...")
            return len(file_batch), 0
        else:
            _, stderr = process.communicate()
            print(f"✗ バッチ処理でエラーが発生しました:")
            print(f"  終了コード: {process.returncode}")
            if stderr:
                print(f"  エラー内容: {stderr[:300]}...")
            # エラーの場合、一部のファイルが処理された可能性があるため、
            # 保守的に全て失敗として扱う
            return 0, len(file_batch)
        
    except FileNotFoundError:
        print(f"✗ エラー: 'copilot'コマンドが見つかりません。")
        print(f"  copilotがインストールされているか確認してください。")
        return 0, len(file_batch)
        
    except KeyboardInterrupt:
        # Ctrl+Cが押された
        interrupted = True
        if 'process' in locals():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        return 0, len(file_batch)
        
    except Exception as e:
        print(f"✗ 予期しないエラー: {str(e)}")
        return 0, len(file_batch)


def main():
    """
    メイン処理
    """
    global interrupted
    
    # シグナルハンドラを設定
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("コードファイル日本語コメント追加ツール")
    print("（copilot + バッチ処理対応版）")
    print("=" * 60)
    
    # コマンドライン引数の解析
    try:
        paths, batch_size = parse_arguments()
    except SystemExit as e:
        if e.code != 0:
            print("\nエラー: パスが指定されていません。")
            print("使用方法: python script.py <パス1> [パス2] ... [--batch-size N]")
            print("※パスにはディレクトリとファイルの両方を指定できます")
            print(f"※--batch-size: 一度に処理するファイル数（デフォルト: {DEFAULT_BATCH_SIZE}）")
            print("※copilotコマンドがインストールされている必要があります")
        sys.exit(e.code)
    
    # パスの検証と分類
    print("\n指定されたパスを確認中...")
    directories, files = validate_and_classify_paths(paths)
    
    # すべてのファイルを収集
    print("\n" + "=" * 60)
    print("ファイル検索中...")
    print("=" * 60)
    
    all_files, empty_files = collect_all_files(directories, files)
    
    # 検索結果を表示
    if directories:
        print(f"\n検索対象ディレクトリ: {len(directories)}個")
    if files:
        print(f"直接指定ファイル: {len(files)}個")
    
    # ユーザー確認（この時点でファイル数とバッチ情報を表示）
    if not confirm_execution(all_files, empty_files, batch_size):
        sys.exit(0)
    
    # ファイルをバッチに分割
    batches = create_batches(all_files, batch_size)
    
    # バッチ処理
    print("\n" + "=" * 60)
    print(f"処理開始（Ctrl+Cで中断可能）")
    print(f"総バッチ数: {len(batches)}")
    print("=" * 60)
    
    total_success = 0
    total_error = 0
    processed_batches = 0
    
    for batch_num, batch in enumerate(batches, 1):
        if interrupted:
            break
            
        success_count, error_count = process_files_batch(batch, batch_num, len(batches))
        
        total_success += success_count
        total_error += error_count
        processed_batches += 1
        
        if not interrupted:
            print(f"\nバッチ {batch_num}/{len(batches)} 完了:")
            print(f"  成功: {success_count}/{len(batch)} ファイル")
            if error_count > 0:
                print(f"  失敗: {error_count}/{len(batch)} ファイル")
    
    # 未処理ファイル数を計算
    unprocessed_count = sum(len(b) for b in batches[processed_batches:])
    
    # 処理結果のサマリー
    print("\n" + "=" * 60)
    if interrupted:
        print("処理中断")
    else:
        print("処理完了")
    print("=" * 60)
    
    print(f"  成功: {total_success} ファイル")
    print(f"  失敗: {total_error} ファイル")
    if unprocessed_count > 0:
        print(f"  未処理: {unprocessed_count} ファイル（中断）")
    print(f"  スキップ: {len(empty_files)} ファイル（空ファイル）")
    print(f"  処理対象合計: {len(all_files)} ファイル")
    print(f"  検出ファイル総数: {len(all_files) + len(empty_files)} ファイル")
    print(f"\nバッチ処理:")
    print(f"  完了バッチ: {processed_batches}/{len(batches)}")
    print(f"  バッチサイズ: {batch_size} ファイル/バッチ")
    
    # 終了コードの設定
    if interrupted:
        sys.exit(130)  # Ctrl+Cによる中断は通常130
    elif total_error > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
