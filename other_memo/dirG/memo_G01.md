#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
コードファイルに日本語コメントを自動追加するツール（Claude Code版）
対象ファイル: {'.py', '.ts', '.dart', '.js'}
空のファイルは自動的にスキップ
ディレクトリとファイルの両方を指定可能
複数ファイルをまとめて処理（バッチ処理）
Claude Code CLI（claude コマンド）を使用
"""

# ===== 標準ライブラリのインポート =====
import os       # OSとのやり取り（ファイル操作など）に使う
import sys      # Pythonインタープリタや終了コードの操作に使う
import argparse # コマンドライン引数（オプション）を解析するためのライブラリ
import subprocess # 外部コマンド（claude など）を実行するためのライブラリ
import signal   # Ctrl+Cなどのシグナルを捕捉するためのライブラリ
from pathlib import Path   # ファイルパスをオブジェクトとして扱いやすくするライブラリ
from typing import List, Set, Tuple  # 型ヒント（変数の型を明示する）のためのライブラリ

# ===== 定数定義 =====

# 処理対象とするファイルの拡張子（小文字で統一）
TARGET_EXTENSIONS = {'.py', '.ts', '.dart', '.js'}

# デフォルトのバッチサイズ（一度に処理するファイル数の初期値）
DEFAULT_BATCH_SIZE = 5

# グローバル変数（プログラム全体で共有する変数）
# Ctrl+C で中断されたかどうかを記録するフラグ
interrupted = False


def signal_handler(signum, frame):
    """
    Ctrl+C（SIGINT シグナル）が押されたときに呼ばれる割り込みハンドラ

    signum: シグナル番号（どの種類のシグナルか）
    frame : シグナル発生時のスタックフレーム（通常は使わない）
    """
    global interrupted  # グローバル変数 interrupted を変更する宣言
    interrupted = True  # 中断フラグを立てる
    print("\n\n" + "=" * 60)
    print("【中断】処理を中断しています...")
    print("=" * 60)


def parse_arguments() -> Tuple[List[str], int]:
    """
    コマンドライン引数を解析してパスのリストとバッチサイズを返す

    例: python sample_claude.py ./src -b 3
        → paths=["./src"], batch_size=3

    Returns:
        Tuple[List[str], int]: (指定されたパスのリスト, バッチサイズ)
    """
    # ArgumentParser: コマンドライン引数を定義・解析するオブジェクト
    parser = argparse.ArgumentParser(
        description='指定ディレクトリ内またはファイルに日本語コメントを追加（Claude Code を使用）'
    )

    # 位置引数 'paths': 1つ以上のパスを受け取る（必須）
    parser.add_argument(
        'paths',
        nargs='+',  # 1つ以上の引数を必須とする（+は「1個以上」を意味する）
        help='検索対象のディレクトリパスまたはファイルパス（複数指定可能）'
    )

    # オプション引数 '--batch-size': 一度に処理するファイル数（省略時はデフォルト値）
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'一度に処理するファイル数（デフォルト: {DEFAULT_BATCH_SIZE}）'
    )

    # 引数を解析して args オブジェクトに格納
    args = parser.parse_args()

    # バッチサイズの検証（0以下は無効）
    if args.batch_size < 1:
        print("エラー: バッチサイズは1以上である必要があります")
        sys.exit(1)

    return args.paths, args.batch_size


def validate_and_classify_paths(paths: List[str]) -> Tuple[List[Path], List[Path]]:
    """
    指定されたパスの妥当性を検証し、ディレクトリとファイルに分類する

    存在しないパスや対応外の拡張子があればエラー表示して終了する

    Args:
        paths: 検証するパスの文字列リスト

    Returns:
        Tuple[List[Path], List[Path]]: (有効なディレクトリのリスト, 有効なファイルのリスト)

    Raises:
        SystemExit: 無効なパスが1つでも存在する場合
    """
    valid_directories = []  # 有効なディレクトリを蓄積するリスト
    valid_files = []        # 有効なファイルを蓄積するリスト
    errors = []             # エラーメッセージを蓄積するリスト

    for path_str in paths:
        # Path(...).resolve() で絶対パスに変換（相対パス・絶対パスの両方に対応）
        path = Path(path_str).resolve()

        if not path.exists():
            # パスが存在しない場合
            errors.append(f"  ✗ {path_str}: 存在しません")
        elif path.is_dir():
            # ディレクトリの場合は有効なディレクトリリストへ
            valid_directories.append(path)
            print(f"  ✓ [ディレクトリ] {path}")
        elif path.is_file():
            # ファイルの場合は拡張子をチェック
            if path.suffix.lower() in TARGET_EXTENSIONS:
                valid_files.append(path)
                print(f"  ✓ [ファイル] {path}")
            else:
                # 対象外の拡張子
                errors.append(f"  ✗ {path_str}: 対象外の拡張子です（{path.suffix}）")
        else:
            # シンボリックリンクや特殊ファイルなど
            errors.append(f"  ✗ {path_str}: ディレクトリでもファイルでもありません")

    # エラーがあれば一括表示して終了
    if errors:
        print("\n以下のエラーが見つかりました:")
        for error in errors:
            print(error)
        print("\n処理を中断します。")
        sys.exit(1)

    return valid_directories, valid_files


def is_empty_file(file_path: Path) -> bool:
    """
    ファイルが空かどうかを判定する
    空白文字（スペース、タブ、改行）のみのファイルも「空」として扱う

    Args:
        file_path: チェック対象のファイルパス

    Returns:
        bool: ファイルが空の場合 True、内容がある場合 False
    """
    try:
        # まずファイルサイズで高速チェック（サイズ0なら確実に空）
        if file_path.stat().st_size == 0:
            return True

        # ファイルを読み込んで空白文字だけかチェック
        # errors='ignore' により読み取れない文字があっても無視する
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # strip() で前後の空白・改行を除去し、何も残らなければ空とみなす
            if not content.strip():
                return True

        return False

    except Exception as e:
        # 読み取りエラーが起きた場合は「空でない」として安全に扱う
        print(f"    警告: ファイルの読み取りに失敗しました: {e}")
        return False


def find_target_files(directory: Path) -> List[Path]:
    """
    指定ディレクトリ配下から対象ファイルを再帰的に検索する

    os.walk() でサブディレクトリも含めて全ファイルを探索する

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        List[Path]: 見つかった対象ファイルの Path オブジェクトリスト
    """
    target_files = []

    # os.walk() はディレクトリを再帰的に探索する
    # root: 現在のディレクトリパス, dirs: サブディレクトリ名リスト, files: ファイル名リスト
    for root, dirs, files in os.walk(directory):
        # 隠しディレクトリ（.git, .node_modules など）をスキップする
        # dirs[:] = ... のように直接書き換えることで walk の探索対象を変更できる
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            file_path = Path(root) / file  # ディレクトリとファイル名を結合してパスを作る
            # 拡張子が対象かチェック（大文字・小文字を区別しない）
            if file_path.suffix.lower() in TARGET_EXTENSIONS:
                target_files.append(file_path.resolve())  # 絶対パスで追加

    return target_files


def collect_all_files(directories: List[Path], files: List[Path]) -> Tuple[List[Path], List[Path]]:
    """
    すべての処理対象ファイルを収集し、空ファイルと有効ファイルに分類する

    Args:
        directories: 検索対象のディレクトリリスト
        files: コマンドラインで直接指定されたファイルリスト

    Returns:
        Tuple[List[Path], List[Path]]: (処理する有効ファイルリスト, スキップする空ファイルリスト)
    """
    all_files = []    # 処理対象の有効なファイルリスト
    empty_files = []  # スキップする空ファイルリスト

    # ディレクトリから再帰検索して収集
    for directory in directories:
        found_files = find_target_files(directory)
        for f in found_files:
            if is_empty_file(f):
                empty_files.append(f)  # 空ファイルはスキップリストへ
            else:
                all_files.append(f)   # 有効ファイルは処理リストへ

    # 直接指定されたファイルを追加
    for f in files:
        if is_empty_file(f):
            empty_files.append(f)
        else:
            all_files.append(f)

    # set() で重複を除去（同じファイルが複数回指定された場合に対処）
    all_files = list(set(all_files))
    empty_files = list(set(empty_files))

    return all_files, empty_files


def create_batches(files: List[Path], batch_size: int) -> List[List[Path]]:
    """
    ファイルリストを指定サイズのバッチ（小グループ）に分割する

    例: 11ファイルをバッチサイズ5で分割すると [[5個], [5個], [1個]] になる

    Args:
        files: ファイルのリスト
        batch_size: 1バッチあたりのファイル数

    Returns:
        List[List[Path]]: バッチに分割されたファイルリスト
    """
    batches = []
    # range(0, len, step) で step ずつ進めながらスライスを取り出す
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]  # i番目から i+batch_size-1 番目までを取り出す
        batches.append(batch)
    return batches


def confirm_execution(all_files: List[Path], empty_files: List[Path], batch_size: int) -> bool:
    """
    ユーザーに実行確認を求め、「はい/いいえ」の入力を待つ

    Args:
        all_files: 処理対象のファイルリスト
        empty_files: スキップする空ファイルのリスト
        batch_size: バッチサイズ

    Returns:
        bool: 続行する場合 True、中断する場合 False
    """
    print("\n" + "="*60)
    print("【実行確認】")
    print("="*60)

    # ファイル数の集計情報を表示
    print(f"\n検出されたファイル:")
    print(f"  処理対象: {len(all_files)} ファイル")
    print(f"  空ファイル（スキップ）: {len(empty_files)} ファイル")
    print(f"  合計: {len(all_files) + len(empty_files)} ファイル")

    if all_files:
        # バッチ数を計算して表示（切り上げ除算）
        num_batches = (len(all_files) + batch_size - 1) // batch_size
        print(f"\nバッチ処理設定:")
        print(f"  バッチサイズ: {batch_size} ファイル/バッチ")
        print(f"  バッチ数: {num_batches} バッチ")

        # 拡張子ごとのファイル数を集計（辞書を使ってカウント）
        ext_count = {}
        for f in all_files:
            ext = f.suffix.lower()
            ext_count[ext] = ext_count.get(ext, 0) + 1  # キーが無ければ0から始める

        print(f"\n処理対象ファイルの詳細:")
        for ext, count in sorted(ext_count.items()):  # 拡張子をアルファベット順に表示
            print(f"  {ext}: {count} ファイル")

        # 処理対象ファイルを最初の5個だけ表示（多すぎる場合は省略）
        print(f"\n処理対象ファイル（最初の5個）:")
        for f in all_files[:5]:
            print(f"  • {f.name}")
        if len(all_files) > 5:
            print(f"  ... 他{len(all_files) - 5}個")

    # 空ファイルの一覧表示（5個以下なら全部、多ければ一部）
    if empty_files and len(empty_files) <= 5:
        print(f"\nスキップされる空ファイル:")
        for f in empty_files:
            print(f"  ○ {f.name}")
    elif empty_files:
        print(f"\nスキップされる空ファイル（最初の5個）:")
        for f in empty_files[:5]:
            print(f"  ○ {f.name}")
        print(f"  ... 他{len(empty_files) - 5}個")

    # 処理対象ファイルが0の場合は False を返して終了
    if not all_files:
        print("\n処理対象のファイルがありません。")
        return False

    print("\n" + "="*60)
    print("※ 処理中はCtrl+Cで中断可能")
    print("="*60)

    # ユーザーの入力を繰り返し待つ（正しい入力が来るまでループ）
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
    複数ファイルをまとめて Claude Code CLI（claude コマンド）に渡して処理する

    claude -p "プロンプト" --dangerously-skip-permissions を実行し、
    AIがコードベースを理解した上で各ファイルに日本語コメントを挿入させる

    Args:
        file_batch: 処理対象ファイルのバッチ（このバッチのファイルリスト）
        batch_num: 現在のバッチ番号（表示用）
        total_batches: 総バッチ数（表示用）

    Returns:
        Tuple[int, int]: (成功ファイル数, 失敗ファイル数)
    """
    global interrupted  # 中断フラグを参照

    # 既に中断されていれば何もしない
    if interrupted:
        return 0, 0

    print(f"\n" + "="*50)
    print(f"バッチ {batch_num}/{total_batches} の処理を開始")
    print(f"対象ファイル数: {len(file_batch)}個")
    print("="*50)

    # ファイルパスを改行区切りの文字列に結合（プロンプトに埋め込むため）
    file_paths_str = "\n".join([str(f) for f in file_batch])

    # 各ファイルの情報（名前・パス・サイズ）を画面に表示
    for i, file_path in enumerate(file_batch, 1):
        print(f"  [{i}] {file_path.name}")
        print(f"      パス: {file_path}")
        print(f"      サイズ: {file_path.stat().st_size:,} bytes")

    # ===== claude コマンドに渡すプロンプトを構築 =====
    # serena MCP サーバでコードベース全体を把握させてからコメントを挿入させる
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

    # ===== Claude Code CLI コマンドを組み立て =====
    # -p "プロンプト"            : 非インタラクティブモードでプロンプトを実行
    # --dangerously-skip-permissions: ツール使用の確認プロンプトをすべてスキップ（自動承認）
    command = [
        "claude",
        "-p",
        prompt,
        "--dangerously-skip-permissions"
    ]

    print(f"\n処理を実行中...")

    try:
        # subprocess.Popen でコマンドを非同期で起動する
        # stdout/stderr を PIPE にすることで出力を Python 側で受け取れる
        # text=True にすることでバイト列ではなく文字列として扱う
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # プロセスが終了するまでループで待機（Ctrl+C による中断も検知）
        while process.poll() is None:  # poll() は終了済みなら終了コードを、実行中なら None を返す
            if interrupted:
                # 中断フラグが立ったらプロセスを終了させる
                process.terminate()  # まず SIGTERM で穏やかに終了要求
                try:
                    process.wait(timeout=5)  # 5秒待つ
                except subprocess.TimeoutExpired:
                    process.kill()  # 5秒経っても終わらなければ強制終了（SIGKILL）
                return 0, len(file_batch)

        # プロセスが終了したので終了コードを確認
        if process.returncode == 0:
            # 終了コード 0 = 正常終了
            print(f"✓ バッチ処理完了")
            stdout, _ = process.communicate()  # 残りの出力を受け取る
            if stdout and stdout.strip():
                print(f"出力: {stdout[:200]}...")  # 長すぎる場合は先頭200文字だけ表示
            return len(file_batch), 0
        else:
            # 終了コード 0 以外 = エラー
            _, stderr = process.communicate()
            print(f"✗ バッチ処理でエラーが発生しました:")
            print(f"  終了コード: {process.returncode}")
            if stderr:
                print(f"  エラー内容: {stderr[:300]}...")
            # 一部ファイルが処理された可能性があるが、保守的に全て失敗として扱う
            return 0, len(file_batch)

    except FileNotFoundError:
        # 'claude' コマンドがシステムにインストールされていない場合
        print(f"✗ エラー: 'claude'コマンドが見つかりません。")
        print(f"  Claude Code がインストールされているか確認してください。")
        print(f"  インストール: npm install -g @anthropic-ai/claude-code")
        return 0, len(file_batch)

    except KeyboardInterrupt:
        # Ctrl+C が押された場合の処理
        interrupted = True
        if 'process' in locals():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        return 0, len(file_batch)

    except Exception as e:
        # その他の予期しないエラー
        print(f"✗ 予期しないエラー: {str(e)}")
        return 0, len(file_batch)


def main():
    """
    メイン処理: プログラムのエントリーポイント

    処理の流れ:
    1. シグナルハンドラ登録（Ctrl+C 対応）
    2. コマンドライン引数の解析
    3. パスの検証と分類
    4. 対象ファイルの収集
    5. ユーザーへの実行確認
    6. バッチ処理の実行
    7. 結果サマリーの表示
    """
    global interrupted

    # SIGINT（Ctrl+C）シグナルを signal_handler 関数で捕捉するよう登録
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("コードファイル日本語コメント追加ツール")
    print("（Claude Code + バッチ処理対応版）")
    print("=" * 60)

    # コマンドライン引数を解析してパスリストとバッチサイズを取得
    try:
        paths, batch_size = parse_arguments()
    except SystemExit as e:
        if e.code != 0:
            print("\nエラー: パスが指定されていません。")
            print("使用方法: python sample_claude.py <パス1> [パス2] ... [--batch-size N]")
            print("※パスにはディレクトリとファイルの両方を指定できます")
            print(f"※--batch-size: 一度に処理するファイル数（デフォルト: {DEFAULT_BATCH_SIZE}）")
            print("※Claude Code（claude コマンド）がインストールされている必要があります")
        sys.exit(e.code)

    # 指定されたパスをチェックし、ディレクトリとファイルに分類する
    print("\n指定されたパスを確認中...")
    directories, files = validate_and_classify_paths(paths)

    # ディレクトリを再帰検索して処理対象ファイルをすべて収集する
    print("\n" + "=" * 60)
    print("ファイル検索中...")
    print("=" * 60)

    all_files, empty_files = collect_all_files(directories, files)

    # 検索結果の概要を表示
    if directories:
        print(f"\n検索対象ディレクトリ: {len(directories)}個")
    if files:
        print(f"直接指定ファイル: {len(files)}個")

    # ユーザーに実行確認（ファイル数・バッチ情報を表示して Yes/No を聞く）
    if not confirm_execution(all_files, empty_files, batch_size):
        sys.exit(0)

    # 全ファイルをバッチ（小グループ）に分割する
    batches = create_batches(all_files, batch_size)

    # バッチ処理の開始
    print("\n" + "=" * 60)
    print(f"処理開始（Ctrl+Cで中断可能）")
    print(f"総バッチ数: {len(batches)}")
    print("=" * 60)

    total_success = 0    # 成功したファイルの合計数
    total_error = 0      # 失敗したファイルの合計数
    processed_batches = 0  # 処理が完了したバッチ数

    # 各バッチを順番に処理する
    for batch_num, batch in enumerate(batches, 1):
        # 中断フラグが立っていたら残りのバッチをスキップ
        if interrupted:
            break

        # バッチを処理して成功数・失敗数を受け取る
        success_count, error_count = process_files_batch(batch, batch_num, len(batches))

        total_success += success_count
        total_error += error_count
        processed_batches += 1

        # バッチ完了メッセージ（中断でない場合のみ表示）
        if not interrupted:
            print(f"\nバッチ {batch_num}/{len(batches)} 完了:")
            print(f"  成功: {success_count}/{len(batch)} ファイル")
            if error_count > 0:
                print(f"  失敗: {error_count}/{len(batch)} ファイル")

    # 中断によって未処理になったファイル数を計算
    unprocessed_count = sum(len(b) for b in batches[processed_batches:])

    # ===== 処理結果のサマリーを表示 =====
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

    # 終了コードを設定してプログラムを終了する
    # 130: Ctrl+C による中断（Unix の慣習）
    # 1: エラーあり
    # 0: 正常終了
    if interrupted:
        sys.exit(130)
    elif total_error > 0:
        sys.exit(1)
    else:
        sys.exit(0)


# このファイルが直接実行された場合のみ main() を呼び出す
# （他のファイルから import された場合は実行しない）
if __name__ == "__main__":
    main()
