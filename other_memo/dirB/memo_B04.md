## 配置ツリー（更新後）

```
.
├─ .github/
│  ├─ copilot-instructions.md
│  └─ prompts/
│     ├─ w1-onboard.prompt.md        ← 手順1: 事前準備＋オンボーディング
│     ├─ w2-requirements.prompt.md   ← 手順2: 要件定義(requirements.md)
│     ├─ w3-design.prompt.md         ← 手順3: 設計文書(design.md)
│     ├─ w4-tasks.prompt.md          ← 手順4: 実装計画(tasks.md)
│     └─ w5-impl.prompt.md           ← 手順5: タスク実施（Vibe相当）
├─ .waro/
│  ├─ specs/                         ← SDD 成果物（requirements/design/tasks）
│  └─ steering/                      ← オンボーディング知識（project/checklist）
└─ README.md
```

> 参考：cc-sdd のワークフロー（要件→設計→タスク→実装）の抽象化と、`.github/prompts` 配置の流儀。今回の命名・出力先は要望に合わせて `.waro` へ調整。([GitHub][5])

---

# A) `.github/copilot-instructions.md`（改訂版）

> **ポイント**：
>
> * **単一ファイル**でリポジトリ全体の既定方針を規定（Copilot の仕様）。
> * **参照優先順位**を厳密化：`workspace/.rulesync/rules/**` → `workspace/.github/prompts/refactor.prompt.md` → 既存設定ファイル → SDD 文書（`.waro`）。
> * **serena MCP** を 2〜4 で必ず参照。
> * **小さな安全な差分**・**承認ゲート**・**観点テスト**の明記。([GitHub Docs][1])

```md
# Repository Copilot Instructions — Kiro互換 SDD（waro 版）

本リポジトリでは、Spec-Driven Development（SDD: 要件→設計→タスク→実装）を **既存リポの改善中心**で実施する。  
**Copilot は常に以下の優先順で根拠を参照**せよ（上位が下位に優先）：

1. **作業環境の正本**：`workspace/.rulesync/rules/**`  
   - ビルド/実行/テスト/静的解析/CI/DevContainer/言語バージョン等の**現用ルール**をここから取得する。
2. **コーディング規約の正本**：`workspace/.github/prompts/refactor.prompt.md`  
   - 命名・レイヤリング・スタイル・リファクタ方針・PR規約などの**規約テキスト**。Chat では常に **Add context > Files** で添付する。
3. 既存の設定・規約ファイル：  
   - パッケージ/ビルド：`package.json` の `scripts`、`tsconfig*.json`、`vite.config.*`、`webpack.*` 等  
   - Lint/Format：`.eslintrc*`、`.prettierrc*`、`.editorconfig`、`.markdownlint*`、`.ruff.toml`、`.golangci.yml` 等  
   - 言語/ツール：`.tool-versions`、`.nvmrc`、`pyproject.toml`、`go.mod`、`Cargo.toml` 等  
   - CI/コンテナ：`.github/workflows`、`.devcontainer/devcontainer.json`、`Dockerfile`、`CODEOWNERS`
4. **SDD 文書**（`.waro/`）：  
   - `./.waro/specs/<slug>/{requirements,design,tasks}.md`  
   - `./.waro/steering/{project,checklist}.md`

## SDD 原則
- **仕様先行**：実装着手前に `requirements.md → design.md → tasks.md` を更新・承認。  
- **差分最小**：既存スタックを尊重。代替案が複数ある場合は**最小変更**で要件を満たす案を優先。  
- **品質ゲート**：各フェーズの成果物に対し、人間による `APPROVE: yes|no` を必須。  
- **観点テスト**：既存動作保持（回帰防止）の観点を常に明記し、機能テストと両立。  

## serena MCP（手順2〜4で必須参照）
- VS Code の Agent モードで `serena` MCP を有効化し、**ツール/リソース**から組織規約・ドメイン知識・API 正本を添付/呼出する。  
- 参照した根拠は SDD 文書に**出典（serena リソース名/ツール名）**として記載。  
  *（MCP の導入/選択は VS Code/Copilot の公式手順に従う）*

## 実装（Edit mode / Copilot Edits）
- `tasks.md` の順に**小さな変更単位**で適用し、**マルチファイル編集**はプレビューで確認してから反映する。  
- 各変更には「意図／パッチ（diff）／Lint・型・テスト手順／観点テスト／ドキュメント更新」を必ず付す。

## 注意
- このファイル（`.github/copilot-instructions.md`）は**リポジトリにつき1つのみ有効**。コマンド化は `.github/prompts/*.prompt.md` を使用する。
```

> 仕様根拠：**Repository Instructions は1つ**、**Prompt Files は `/` で実行**、**MCP は Copilot Chat Agent モードでツール/リソースとして利用**、**Edit mode / Copilot Edits** はマルチファイル編集に対応。([GitHub Docs][1])

---

# B) Prompt Files（5ファイル・改訂版）

> すべて **`.waro/`** に合わせて出力先を変更し、**workspace/.rulesync/rules/** と **workspace/.github/prompts/refactor.prompt.md** の厳密参照を追記。**serena MCP** は **手順2〜4**で必須参照にしました。実行は `/w1-onboard` などの**スラッシュコマンド**です。([GitHub Docs][2])

---

### `.github/prompts/w1-onboard.prompt.md`

```md
---
description: "Step1: 事前準備＋オンボーディング（コード把握 & steering 更新）"
mode: ask
---

あなたは本リポジトリのAI開発パートナー。**既存コードの短時間オンボーディング**を行い、以後の SDD を円滑化する。

## 入力
- 依頼概要（任意）: ${input:subject:この改善/調査の目的は？}

## 参照の優先順位（厳守）
1) `workspace/.rulesync/rules/**`（作業環境の正本）  
2) `workspace/.github/prompts/refactor.prompt.md`（コーディング規約の正本）  
3) 既存の設定/規約ファイル（package.json, tsconfig*, .eslintrc*, .prettierrc*, .editorconfig, .github/workflows, Dockerfile, .devcontainer など）

## 実施要領
1) 上記 1)〜3) を読み取り、**現用のビルド/実行/テスト/静的解析/CI**の手順を抽出。  
2) 主要モジュール・層構造・依存関係・エントリポイントを**鳥瞰**。  
3) **観点テスト**（既存動作保持）候補・技術的負債・リスクを列挙。  
4) 以下を**新規/更新**する（cc-sdd流に準拠しつつ waro へ適用）：  
   - `.waro/steering/project.md`：スタック、構成図（Mermaid可）、実行/テスト/ビルド、規約要点、観点テスト、リスク、未解決事項  
   - `.waro/steering/checklist.md`：開発チェックリスト（Lint/型/テスト/フォーマット/セキュリティ/パフォーマンス）  
5) 生成物には**根拠の出典**を明記：`workspace/.rulesync/rules/…`、`workspace/.github/prompts/refactor.prompt.md`、リポ内設定ファイルのパス。

## 出力（Markdown）
- 変更対象ファイルと差分プラン
- `.waro/steering/project.md` の完全内容
- `.waro/steering/checklist.md` の完全内容

## 承認
- 人間の承認語彙：`APPROVE: yes|no`（差戻し理由を明記）
```

---

### `.github/prompts/w2-requirements.prompt.md`

```md
---
description: "Step2: ユーザープロンプトから要件定義（requirements.md）を生成"
mode: ask
---

## 入力
- subject（必須）: ${input:subject:どの機能/改善？}
- slug（任意。未指定なら推定）: ${input:slug:英小文字-ハイフン区切りの識別子}

## 前提と根拠
- 改善主体。**既存スタック/規約を尊重**し、差分最小で満たす案を優先。  
- **serena MCP が有効なら必須参照**：組織規約・ドメイン知識・API 正本をツール/リソースから添付・引用する。  
- **正本**：`workspace/.rulesync/rules/**`、`workspace/.github/prompts/refactor.prompt.md`、既存設定/規約ファイル。

## 手順
1) `slug` を決定し、`.waro/specs/<slug>/` を作成。  
2) `requirements.md` を作成（推奨構成）：  
   - 背景/目的、スコープ（含む/含まない）  
   - **制約**（既存設計/運用/非機能、互換性、デプロイ/CI）  
   - 用語定義、ユースケース/シナリオ  
   - **受け入れ基準**（Gherkin 可）  
   - 既存コードへの影響（ファイル/モジュール/CI）  
   - セキュリティ/パフォーマンス/可観測性、リスク、オープンクエスチョン  
3) 根拠リンクを**必ず記載**：`workspace/.rulesync/rules/…`、`workspace/.github/prompts/refactor.prompt.md`、serena リソース名/ツール名、リポ内設定。  
4) `APPROVE: yes|no` による承認待ち。

## 出力（Markdown）
- `.waro/specs/<slug>/requirements.md` の完全内容
- 重要論点のチェックリスト
- 参考リンク（serena/リポ内/workspace）
```

---

### `.github/prompts/w3-design.prompt.md`

```md
---
description: "Step3: 要件から設計文書（design.md）を作成"
mode: ask
---

## 入力
- slug（必須）: ${input:slug}

## 前提
- `.waro/specs/<slug>/requirements.md` を正とし、設計で**仕様を変えない**。  
- **serena MCP を必須参照**し、設計原則/内製ライブラリ/API 正本との整合を確認。  
- **正本**：`workspace/.rulesync/rules/**`、`workspace/.github/prompts/refactor.prompt.md`、既存設定。

## 設計ドキュメント構成（例）
- 全体アーキテクチャと既存への組み込み方、影響領域  
- モジュール設計（責務、公開API、入出力、例外、エラー整合）  
- データモデル/スキーマ/移行  
- 外部/内部API（リクエスト/レスポンス/エラー/バージョン）  
- **フロー図/シーケンス図（Mermaid）**  
- パフォーマンス/セキュリティ/可観測性（ログ/メトリクス/トレース）  
- テスト戦略（観点テスト＋機能テストのカバレッジ方針）  
- ロールバック/フェイルセーフ  
- 既存規約（Lint/Format/構成/命名）との整合チェック  
- **代替案**（採用/却下理由）

## 出力（Markdown）
- `.waro/specs/<slug>/design.md` の完全内容
- 影響が想定される既存ファイル一覧と理由
- 根拠リンク（workspace/serena/リポ内）

## 承認
- `APPROVE: yes|no`
```

---

### `.github/prompts/w4-tasks.prompt.md`

```md
---
description: "Step4: 設計から実装計画（tasks.md）を作る（番号付きTodo）"
mode: ask
---

## 入力
- slug（必須）: ${input:slug}

## 指針
- タスクは**小さく直列化**してリスク前倒し排除。  
- ID は `1.1, 1.2, ...` の章節番号。  
- 各タスクに**完了条件**（Lint/型/テスト/フォーマット/CI 成功）を明記。  
- **観点テスト**（既存動作保持）と**機能テスト**（新要件）の双方を組み込む。  
- 参照の正本：`workspace/.rulesync/rules/**`、`workspace/.github/prompts/refactor.prompt.md`、serena リソース。

## 出力（Markdown）
- `.waro/specs/<slug>/tasks.md` の完全内容（編集対象/期待結果/完了条件/根拠リンク付き）  
- `APPROVE: yes|no`
```

---

### `.github/prompts/w5-impl.prompt.md`

```md
---
description: "Step5: tasks.md の順にタスクを実施（最小差分・Edit mode/Copilot Edits）"
mode: edit
---

## 入力
- slug（必須）: ${input:slug}
- tasks（任意。未指定なら先頭から）: ${input:tasks:"1.1,1.2" のようにカンマ区切り}

## 実施要領
- `.waro/specs/<slug>/tasks.md` を読み、指定のタスクID順に**最小差分**で変更を提案→適用する。  
- VS Code の **Edit mode / Copilot Edits** を使用して**マルチファイル編集**をプレビュー確認後に適用する。  
- 各タスクごとに以下を必ず出力：  
  1) 変更意図（タスクID/参照設計/影響範囲）  
  2) **パッチ（diff）**（新規/変更/削除ファイルを含む）  
  3) 実行コマンド（既存 scripts / rules 由来）：ビルド・Lint・型・テスト・フォーマット  
  4) 確認観点（観点テスト＋機能テスト）  
  5) ドキュメント更新（README/CHANGELOG/仕様リンク）

## 参照の正本
- `workspace/.rulesync/rules/**`（実行・テスト・CI の手順）  
- `workspace/.github/prompts/refactor.prompt.md`（コーディング規約）  

## 出力
- 適用予定のパッチ、実行コマンド、テスト結果要約、コミット/PR メッセージ案
```

> Prompt Files の実行・定義方法、**Edit mode / Copilot Edits** の使い分けは公式ドキュメント準拠です。([GitHub Docs][2])

---

# C) `README.md`（更新版）

```md
# Kiro互換 SDD（waro 版）for GitHub Copilot

本リポジトリは、Kiro互換の Spec-Driven Development（要件→設計→タスク→実装）を **GitHub Copilot** の公式機構（Repository Instructions + Prompt Files）で再現します。

## セットアップ
1. VS Code で GitHub Copilot Chat を有効化。  
2. このリポジトリに以下を配置：  
   - `.github/copilot-instructions.md`（本方針。**1つだけ**有効）  
   - `.github/prompts/w1..w5.prompt.md`（**5つのコマンド**）  
   - `.waro/specs/`（SDD 成果物）、`.waro/steering/`（オンボーディング知識）
3. 参照の正本（必ず存在する前提で扱う）：  
   - **作業環境**：`workspace/.rulesync/rules/**`  
   - **コーディング規約**：`workspace/.github/prompts/refactor.prompt.md`（Chat で **Add context > Files** から添付推奨）
4. （推奨）**serena MCP** を Agent モードで有効化し、手順2〜4で**必須参照**とする。

> 参考：Repository Instructions は 1ファイル、Prompt Files は `.github/prompts` に配置し `/w1-...` で実行、MCP は Agent モードのツール/リソースとして追加・選択。:contentReference[oaicite:9]{index=9}

## 使い方（既存リポ改善向け）
1. **オンボーディング**：`/w1-onboard subject="○○の改善方針"`  
   - `./.waro/steering/*.md` をレビュー → `APPROVE: yes`  
2. **要件定義**：`/w2-requirements subject="△△を追加" slug="search-feature"`  
   - `./.waro/specs/search-feature/requirements.md`（根拠：workspace/serena/既存設定）  
3. **設計**：`/w3-design slug="search-feature"` → `design.md`  
4. **タスク化**：`/w4-tasks slug="search-feature"` → `tasks.md`（1.1, 1.2, …）  
5. **実装**：`/w5-impl slug="search-feature" tasks="1.1,1.2"`  
   - **Edit mode / Copilot Edits** で小さな差分を適用、Lint/型/テスト/フォーマットは `workspace/.rulesync/rules/**` と既存 scripts に従う。

## 運用ガイド
- 変更は**差分最小**で段階的に。**観点テスト**（回帰防止）を常に明記。  
- 各フェーズで**APPROVE**ゲート。  
- 仕様や規約の**根拠リンク**（workspace/serena/既存設定）を必ず残す。

## 参考
- GitHub Docs（Repository Instructions / Prompt Files / MCP / Edit mode）  
- cc-sdd（Kiro互換の SDD テンプレ/運用例）
```

---

## 追加の精度向上（見直しポイント）

* **命名・パス整合性**：すべて `.kiro` → **`.waro`**、`sdd-*` → **`w*-*`** に統一。
* **参照の正本定義**：`workspace/.rulesync/rules/**` と `workspace/.github/prompts/refactor.prompt.md` を「最優先根拠」として全ファイルに明記。
* **serena MCP の位置付け**：手順2〜4は**必須参照**（Agent モードでツール/リソースを添付・使用）。([GitHub Docs][3])
* **実装フェーズの運用**：**Edit mode / Copilot Edits** と**マルチファイル編集**の安全運用（プレビュー→適用、最小差分、コミット分割）を明記。([Visual Studio Code][4])
* **承認ゲート**：`APPROVE: yes|no` を全プロンプトの出力・合意フローに組込み。
* **cc-sdd 準拠**：SDD の5フェーズ・ガードレールを抽象化（今回 `.waro` へ適用）。([GitHub][5])

---

## 備考：仕様上の正確性（誤解防止）

* **`.github/copilot-instructions.md` は1つ**のみ解釈されます。5つに分割しても Copilot は読みません。コマンドは **Prompt Files** で定義してください。([GitHub Docs][1])
* Prompt Files は **`.github/prompts/*.prompt.md`** に置き、**`/ファイル名`** で実行できます。([GitHub Docs][2])

---

## 参考URL（一次情報）

* **Repository Instructions（単一ファイル）**：`.github/copilot-instructions.md` の作成と適用。([GitHub Docs][1])
* **Prompt Files**：`.prompt.md` を `/` で実行、`.github/prompts` 配置。([GitHub Docs][2])
* **MCP**（serena等の追加/使用—Agentモードのツール/リソース）：([GitHub Docs][3])
* **Edit mode / Copilot Edits（マルチファイル編集）**：([Visual Studio Code][4])
* **cc-sdd（最重要リポ）**：Kiro互換 SDD／コマンド群と運用の流儀。([GitHub][5])

---

必要があれば、**既存リポに対する自動移行用のパッチ（`sdd-*` → `w*`／`.kiro` → `.waro`）**や、`workspace/.rulesync/rules/**` の見落とし検知（ルール未参照の差分をブロックする GitHub Actions）もすぐ用意できます。

[1]: https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot?utm_source=chatgpt.com "Adding repository custom instructions for GitHub Copilot"
[2]: https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/your-first-prompt-file?utm_source=chatgpt.com "Your first prompt file - GitHub Copilot"
[3]: https://docs.github.com/copilot/customizing-copilot/using-model-context-protocol/extending-copilot-chat-with-mcp?utm_source=chatgpt.com "Extending GitHub Copilot Chat with the Model Context Protocol (MCP)"
[4]: https://code.visualstudio.com/docs/copilot/chat/copilot-edits?utm_source=chatgpt.com "Use edit mode in VS Code"
[5]: https://github.com/gotalab/cc-sdd?utm_source=chatgpt.com "gotalab/cc-sdd: High quality Spec-Driven Development ..."
