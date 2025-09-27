#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
コードファイルに日本語コメントを自動追加するツール
対象ファイル: .py, .tsx, .ts
空のファイルは自動的にスキップ
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Set

# 対象となるファイル拡張子
TARGET_EXTENSIONS = {'.py', '.tsx', '.ts'}


def parse_arguments() -> List[str]:
    """
    コマンドライン引数を解析してディレクトリパスのリストを返す
    
    Returns:
        List[str]: 指定されたディレクトリパスのリスト
    """
    parser = argparse.ArgumentParser(
        description='指定ディレクトリ内のコードファイルに日本語コメントを追加'
    )
    parser.add_argument(
        'directories',
        nargs='+',  # 1つ以上の引数を必須とする
        help='検索対象のディレクトリパス（複数指定可能）'
    )
    
    args = parser.parse_args()
    return args.directories


def validate_directories(directories: List[str]) -> List[Path]:
    """
    指定されたディレクトリパスの妥当性を検証
    
    Args:
        directories: 検証するディレクトリパスのリスト
    
    Returns:
        List[Path]: 有効なディレクトリのPathオブジェクトリスト
    
    Raises:
        SystemExit: 無効なディレクトリが存在する場合
    """
    valid_paths = []
    errors = []
    
    for dir_path in directories:
        # 相対パス・絶対パスの両方に対応
        path = Path(dir_path).resolve()
        
        if not path.exists():
            errors.append(f"  ✗ {dir_path}: 存在しません")
        elif not path.is_dir():
            errors.append(f"  ✗ {dir_path}: ディレクトリではありません")
        else:
            valid_paths.append(path)
            print(f"  ✓ {path}")
    
    if errors:
        print("\n以下のエラーが見つかりました:")
        for error in errors:
            print(error)
        print("\n処理を中断します。")
        sys.exit(1)
    
    return valid_paths


def confirm_execution(directories: List[Path]) -> bool:
    """
    ユーザーに実行確認を求める
    
    Args:
        directories: 処理対象のディレクトリリスト
    
    Returns:
        bool: 続行する場合True、中断する場合False
    """
    print("\n" + "="*60)
    print("【実行確認】")
    print("以下のディレクトリを処理対象とします:")
    for path in directories:
        print(f"  • {path}")
    print("\n対象ファイル拡張子: " + ", ".join(TARGET_EXTENSIONS))
    print("※空のファイルは自動的にスキップされます")
    print("="*60)
    
    while True:
        response = input("\n続行しますか？ (はい/いいえ): ").strip().lower()
        
        if response in ['はい', 'yes', 'y']:
            return True
        elif response in ['いいえ', 'no', 'n']:
            print("処理を中断しました。")
            return False
        else:
            print("「はい」または「いいえ」で答えてください。")


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


def process_file(file_path: Path) -> bool:
    """
    指定ファイルに対してcodex execコマンドを実行
    
    Args:
        file_path: 処理対象ファイルの絶対パス
    
    Returns:
        bool: 処理成功時True、失敗時False
    """
    # コマンドの構築
    command = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        f"{file_path}について、まずserenaのMCPサーバを用いて、コードベースを把握して。"
        f"次に高校生初心者でも理解できるよう、各ソースコードの随所に日本語のコメントを挿入して。"
        f"※ライブラリの説明(非常に重要)、関数やクラスの概要、難しい箇所の補足、とにかくコメントは多めに。"
        f"※補足:英語のコメントは全て日本語に翻訳して。"
        f"※補足:ソースコードの処理内容はそのままで。"
    ]
    
    print(f"\n処理中: {file_path}")
    print(f"  拡張子: {file_path.suffix}")
    print(f"  サイズ: {file_path.stat().st_size:,} bytes")
    
    try:
        # コマンドを実行
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"  ✓ 処理完了")
        
        # 標準出力があれば表示（デバッグ用）
        if result.stdout.strip():
            print(f"  出力: {result.stdout[:100]}...")  # 最初の100文字のみ表示
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ✗ エラーが発生しました:")
        print(f"    終了コード: {e.returncode}")
        if e.stderr:
            print(f"    エラー内容: {e.stderr[:200]}...")  # エラーメッセージの一部を表示
        return False
        
    except FileNotFoundError:
        print(f"  ✗ エラー: 'codex'コマンドが見つかりません。")
        print(f"    codexがインストールされているか確認してください。")
        return False
        
    except Exception as e:
        print(f"  ✗ 予期しないエラー: {str(e)}")
        return False


def main():
    """
    メイン処理
    """
    print("=" * 60)
    print("コードファイル日本語コメント追加ツール")
    print("=" * 60)
    
    # コマンドライン引数の解析
    try:
        directories = parse_arguments()
    except SystemExit as e:
        if e.code != 0:
            print("\nエラー: ディレクトリパスが指定されていません。")
            print("使用方法: python script.py <ディレクトリパス1> [ディレクトリパス2] ...")
        sys.exit(e.code)
    
    # ディレクトリの検証
    print("\n指定されたディレクトリを確認中...")
    valid_directories = validate_directories(directories)
    
    # ユーザー確認
    if not confirm_execution(valid_directories):
        sys.exit(0)
    
    # 各ディレクトリを処理
    all_files = []
    empty_files = []
    print("\n" + "=" * 60)
    print("ファイル検索中...")
    print("=" * 60)
    
    for directory in valid_directories:
        print(f"\n検索中: {directory}")
        files = find_target_files(directory)
        
        if files:
            valid_files = []
            skipped_files = []
            
            for f in files:
                if is_empty_file(f):
                    skipped_files.append(f)
                    empty_files.append(f)
                else:
                    valid_files.append(f)
            
            print(f"  → {len(files)}個のファイルが見つかりました")
            
            if valid_files:
                print(f"    処理対象: {len(valid_files)}個")
                for f in valid_files[:5]:  # 最初の5個まで表示
                    try:
                        rel_path = f.relative_to(directory)
                        print(f"      • {rel_path}")
                    except ValueError:
                        print(f"      • {f}")
                if len(valid_files) > 5:
                    print(f"      ... 他{len(valid_files) - 5}個")
            
            if skipped_files:
                print(f"    空ファイル（スキップ）: {len(skipped_files)}個")
                for f in skipped_files[:3]:  # 最初の3個まで表示
                    try:
                        rel_path = f.relative_to(directory)
                        print(f"      ○ {rel_path} (空)")
                    except ValueError:
                        print(f"      ○ {f.name} (空)")
                if len(skipped_files) > 3:
                    print(f"      ... 他{len(skipped_files) - 3}個")
            
            all_files.extend(valid_files)
        else:
            print(f"  → 対象ファイルが見つかりませんでした")
    
    if not all_files:
        if empty_files:
            print(f"\n{len(empty_files)}個の空ファイルが見つかりましたが、すべてスキップされました。")
        else:
            print("\n処理対象のファイルが見つかりませんでした。")
        sys.exit(0)
    
    # ファイル処理のサマリー
    print("\n" + "=" * 60)
    print("処理サマリー")
    print("=" * 60)
    print(f"  処理対象: {len(all_files)} ファイル")
    if empty_files:
        print(f"  スキップ: {len(empty_files)} ファイル（空ファイル）")
    print(f"  合計検出: {len(all_files) + len(empty_files)} ファイル")
    
    # ファイル処理
    print("\n" + "=" * 60)
    print(f"{len(all_files)} 個のファイルを処理します")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for i, file_path in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}]", end="")
        
        if process_file(file_path):
            success_count += 1
        else:
            error_count += 1
    
    # 処理結果のサマリー
    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)
    print(f"  成功: {success_count} ファイル")
    print(f"  失敗: {error_count} ファイル")
    print(f"  スキップ: {len(empty_files)} ファイル（空ファイル）")
    print(f"  処理対象合計: {len(all_files)} ファイル")
    print(f"  検出ファイル総数: {len(all_files) + len(empty_files)} ファイル")
    
    # 終了コードの設定
    if error_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
