# Tribal Knowledge Mapper for Claude Code

Meta engineering blog 「How Meta Used AI to Map Tribal Knowledge in Large-Scale Data Pipelines」 (2026/04/06) の構造を Claude Code 上に高い忠実度で再現するための完成版テンプレートです。

このパッケージは以下を提供します。

- 9 種類の subagent（repo-explorer / module-analyst / context-writer / context-critic / context-fixer / dependency-indexer / coverage-auditor / routing-upgrader / prompt-tester）
- 2 つの skill（tribal-mapper / tribal-router）
- 4 つの slash command（/tribal-init / /tribal-refresh / /tribal-route / /tribal-validate）
- 4 つの hook 連動スクリプト（Hook stdin 仕様に準拠、UserPromptSubmit で router を強制起動）
- GitHub Actions による 2 週ごとの自動リコンサイル + 品質回帰ゲート
- 全成果物の JSON Schema 定義

---

## 設計の3層（厳守）

| 層 | 役割 | ここでやってはいけないこと |
|---|---|---|
| Pre-compute | コードベース全体を先読みし、モジュール単位の compass 形式 context を生成 | 後付けの即興分析 |
| Runtime | ユーザーの自然言語タスクから関連 context を 3〜5 枚だけ動的ロード | `.claude/context/*.md` を一括 import すること |
| Maintenance | 定期的に再批評・再生成・パス検証・カバレッジ補完 | 失敗を握り潰して PR を出すこと |

「常時オン」設計は Meta 論文が引用した [arxiv 2602.11988](https://arxiv.org/abs/2602.11988) の失敗モードに合流するため、強制機構（hook）で物理的に opt-in を担保しています。

---

## ディレクトリ全体像

```
your-monorepo/
├── CLAUDE.md
├── .gitignore
├── .claude/
│   ├── settings.json
│   ├── scripts/
│   │   ├── validate_context_file.py     # PostToolUse hook 本体
│   │   ├── inject_router_directive.py   # UserPromptSubmit hook 本体
│   │   ├── detect_changed_modules.py    # refresh の差分検出
│   │   ├── check_quality_regression.py  # CI の品質ゲート
│   │   └── flatten_module_path.py       # モジュール名→ファイル名（共通ユーティリティ）
│   ├── skills/
│   │   ├── tribal-mapper/SKILL.md
│   │   └── tribal-router/SKILL.md
│   ├── agents/
│   │   ├── repo-explorer.md
│   │   ├── module-analyst.md
│   │   ├── context-writer.md
│   │   ├── context-critic.md
│   │   ├── context-fixer.md
│   │   ├── dependency-indexer.md
│   │   ├── coverage-auditor.md
│   │   ├── routing-upgrader.md
│   │   └── prompt-tester.md
│   ├── commands/
│   │   ├── tribal-init.md
│   │   ├── tribal-refresh.md
│   │   ├── tribal-route.md
│   │   └── tribal-validate.md
│   ├── schemas/
│   │   ├── analyst.schema.json
│   │   ├── critic.schema.json
│   │   ├── coverage.schema.json
│   │   ├── dep-graph.schema.json
│   │   ├── quality-log.schema.json
│   │   └── routing-table.schema.json
│   ├── critic-workspace/                # critic 専用の隔離ディレクトリ（physical isolation）
│   ├── .session-state/                  # router 起動状態の追跡（hook 用）
│   ├── artifacts/                       # gitignore 対象（最新のみ commit する運用も可）
│   │   ├── analyst/
│   │   ├── critic/
│   │   └── tests/
│   └── context/                         # 生成物（人手で編集しない）
│       ├── _repo-map.json
│       ├── _routing-table.json
│       ├── _dep-graph.json
│       ├── _coverage.json
│       └── _quality-log.jsonl
└── .github/workflows/
    └── tribal-refresh.yml
```

---

## セットアップ手順

### 0. 前提

- Claude Code 最新版がインストール済み（`claude --version` で確認）
- Python 3.10 以上
- Git
- （任意）Serena MCP がプロジェクトに接続済み。なくても動くが analyst の精度は落ちる

### 1. このパッケージをプロジェクトに展開

```bash
# プロジェクトのルートで
tar -xzf tribal-knowledge-mapper.tar.gz
mv tribal/CLAUDE.md ./CLAUDE.md   # 既存の CLAUDE.md がある場合はマージ
mv tribal/.claude ./.claude
mv tribal/.github ./.github
mv tribal/.gitignore ./.gitignore  # 既存と差分マージ推奨
rm -rf tribal
```

### 2. CLI フラグの確認（重要）

GitHub Actions と手元 CI で使う Claude Code の headless モードのフラグを **必ず手元で先に確認** してください。

```bash
claude --help | grep -E "print|headless|message|prompt"
```

`.github/workflows/tribal-refresh.yml` 内の `claude -p "..."` の部分は、上で確認したフラグに合わせて調整します。バージョンによって `--print` と `-p` の差や、stdin 経由が必須なケースがあります。

### 3. Hook の動作確認

```bash
# context ファイルがあったとして、validation hook を手動で起動できるか確認
echo '{"tool_input": {"file_path": ".claude/context/sample.md"}}' \
  | python .claude/scripts/validate_context_file.py
echo "exit: $?"
```

`exit: 0` または `exit: 1`（バリデーション失敗時）が返れば正常。`Traceback` が出るなら Python パスや権限を確認。

### 4. 初回フル構築

Claude Code を起動して以下を実行:

```
/tribal-init
```

完了後、以下が揃っていることを確認:

```bash
ls .claude/context/         # *.md が module 数だけ + _*.json が 5 個
cat .claude/context/_coverage.json | python -m json.tool
cat .claude/context/_quality-log.jsonl | tail -1
```

### 5. CI シークレット設定

GitHub リポジトリの Settings → Secrets and variables → Actions に以下を登録:

- `ANTHROPIC_API_KEY` — あなたの Anthropic API キー

---

## 普段の運用

### 開発タスクを投げる

そのまま自然言語で投げるだけです。`UserPromptSubmit` hook が router を起動するように指示を注入するので、`tribal-router` skill が必ず先に走ります。

```
新しいデータフィールドを pipeline に追加したい。validation と codegen との整合性も保ちたい。
```

期待動作:

1. router が `schema-change` と分類
2. registry / config / validation / codegen 系の context を 3〜5 枚提示
3. ユーザーに承認確認
4. 承認後、その context だけをロードして開発タスクに進む

### 差分更新（コード変更後）

```
/tribal-refresh
```

`detect_changed_modules.py` が直近差分を検出し、影響モジュールだけ analyst→writer→critic を再実行します。

### 品質確認だけ

```
/tribal-validate
```

context の生成は行わず、path validity / critic / prompt tests だけを再実行します。

### 自動更新

GitHub Actions が **2 週ごと** に走り、変更検出→再分析→品質ゲート→PR を自動で行います。PR は `tribal-knowledge` `automated` ラベル付きで届くので、レビューマージしてください。

品質スコアが main ブランチ平均から **0.3 以上劣化** していると CI が fail するため、auto-refresh による静かな品質劣化は防がれます。

---

## トラブルシューティング

### Q. Hook が走っていない気がする

`echo '{"tool_input":{"file_path":"x"}}' | python .claude/scripts/validate_context_file.py` で手動実行できるか確認。`.claude/settings.json` の matcher が現行の Claude Code 仕様と合っているか確認。

### Q. context が必ず 25 行で打ち切られて情報が落ちる

`validate_context_file.py` は **実体行（空行・コードフェンス除外）** で 25-40 を許容しています。それでも落ちる場合は writer が冗長記述しているので、context-writer.md の制約をさらに絞ってください。

### Q. critic のスコアが甘い気がする

critic は `.claude/critic-workspace/` 配下でしか作業できないように tools が制限されています。それでも甘い場合、`context-critic.md` の判定基準で「path_accuracy < 5.0 → 即 FIX」を「いずれかの軸が 3.0 未満で FIX」など強める方向で調整します。

### Q. router が呼ばれずに全 context が読まれている

`UserPromptSubmit` hook が動いていません。`.claude/scripts/inject_router_directive.py` を手動実行して JSON が出力されることを確認。`.claude/settings.json` の hook 登録を再確認。

### Q. `/tribal-refresh` が「変更なし」しか返さない

`detect_changed_modules.py` が `git log` を使うので、`fetch-depth: 0` でチェックアウトされていないと差分が取れません。CI 側の actions/checkout 設定を確認。

### Q. CI で品質ゲートが常に fail する

main ブランチに baseline がない初期状態では `check_quality_regression.py` は skip されます。それでも fail する場合は `--threshold` を一時的に `0.5` に緩めて段階的に運用に乗せてください。

---

## 再現度評価の 5 基準（self-check）

`/tribal-validate` 実行後、以下を満たせば Meta 論文の構造的同型が達成されています。

1. **構造同型**: Pre-compute / Runtime / Maintenance の3層が揃って動いている
2. **5問忠実**: `.claude/artifacts/analyst/*.json` の Q1〜Q5 が全件埋まっており、Q3 と Q5 が空でない
3. **Compass遵守**: 全 context が 25-40 実体行、全パス有効、形容詞排除
4. **Reconciliation収束**: critic→fixer ループが平均 3 ラウンド以内で全件 PASS
5. **opt-in原則**: prompt-tester で router 経由のロードが 3〜5 枚に収まる

---

## ライセンス・免責

このテンプレートは設計参考として配布するものです。本番投入前に各組織のセキュリティ要件、API キー管理、`--dangerously-skip-permissions` の利用可否を必ず確認してください。

######簡単なセットアップ
# 1. プロジェクトルートで展開
tar -xzf tribal-knowledge-mapper.tar.gz
mv tribal/CLAUDE.md ./CLAUDE.md      # 既存があればマージ
mv tribal/.claude ./.claude
mv tribal/.github ./.github
mv tribal/.gitignore ./.gitignore    # 既存があればマージ
rm -rf tribal

# 2. CLI フラグを必ず確認 (バージョン差吸収)
claude --help | grep -E "print|headless"

# 3. Hook 動作確認
echo '{"tool_input":{"file_path":"x"}}' | python .claude/scripts/validate_context_file.py
echo "exit: $?"  # 0 が返れば OK

# 4. Claude Code で初回構築
/tribal-init


##ちなみに、初心者みたいなことを聞くけど、これはエンジニアとして、どういうふうに活用すればいいかな？
全く初心者の質問じゃない。これは設計を作ったあとに必ず立ち止まるべき問いで、ここで止まらない人ほど「凄いものを作ったが誰も使わない」になりやすい。

あなたのキャリア状況（SES で頻繁に環境が変わる、現場ごとにキャッチアップが必要、Claude Code Skills エコシステムを既に育てている）を踏まえて、活用シナリオを **効果が大きい順** に整理する。

---

## シナリオ1: SES 新規参画時のオンボーディング高速化（最大のリターン）

これがあなたにとって**最も効くユースケース**。理由は、あなたの仕事が「短期間で他人のコードベースを把握して結果を出す」ことの繰り返しだから。

**通常の SES 参画（tribal-mapper なし）:**
- 1週目: ディレクトリ構造の把握、READMEと IaC の写経
- 2週目: 既存コードを grep しながら何となく理解
- 3週目: 既存メンバーに「これ何ですか?」を 20 回聞く
- 1か月後: ようやく1人で変更が打てる
- 残るリスク: 暗黙のルール（「この enum は削除厳禁」「この環境変数は本番だけ違う」）を踏み抜いて事故る

**tribal-mapper を入れた場合:**
- 初日午後: `/tribal-init` を流して晩に放置（自分の作業時間を消費しない）
- 2日目朝: `_quality-log.jsonl` と Q3 ばかり集めた non-obvious patterns を読む（**これが既存メンバーが3か月かけて教える内容そのもの**）
- 3日目: 簡単なチケットを取って、`/tribal-route` で関連 context を 3-5 枚ロードしながら作業
- 1週間後: 既存メンバーに「これ何ですか?」を聞く回数が 1/5 になる

**現場での売り方**: 「自分用のオンボーディング補助ツールです。リポにコミットせず .gitignore に入れて使います」と説明すれば、誰の許可も要らず導入できる。効果が出てから「チームに展開しませんか?」を提案できる。これは政治的にも安全な順序。

---

## シナリオ2: 「自分が書いたコードを 3 か月後に忘れる問題」の解決

エンジニアあるあるだが、自分で書いたコードでも 3 か月経つと他人のコードと変わらない。特にあなたのように複数現場を渡り歩くと、過去現場のコードを呼び出される（「あの時の DynamoDB sync ツール、不具合出てるけど見てくれない?」）ケースで詰む。

`/tribal-init` で生成された `.claude/context/*.md` は、**未来の自分への置き手紙**として機能する。Q5（tribal_knowledge_from_comments）が特にこれで、git blame と隣接コミットメッセージを掘ってくれるので、「なぜこう書いたか」が context に残る。

実用ポイント: 案件終了時に `.claude/context/` だけを zip で個人保管しておくと、再呼び出しされた時に一瞬で context を取り戻せる。コードベース本体は client のものでも、生成 context は知識資産として手元に残せる（NDA に注意）。

---

## シナリオ3: コードレビューでの「言語化できない違和感」の事前検出

経験者がレビューで感じる「なんか嫌な感じがする」の正体は、ほぼ全て tribal knowledge との衝突。`/tribal-route` で関連 context をロードしてから差分を見ると、Q3（Non-Obvious Patterns）と差分を機械的に突き合わせられる。

例:
- 差分で deprecated enum を消している → Q3 の「append-only」ルールに違反 → 即指摘できる
- 差分で field 名を変えている → Q3 の「naming drift」ルールに該当 → ripple_index で影響先を全部洗える

これは**自分のレビュー精度を底上げ**するし、レビュー時間も短くなる。シニアエンジニアの暗黙知を Q3 に集約しておけば、ジュニアにレビューを任せても品質が落ちにくい。

---

## シナリオ4: Claude Code を「もっと役に立つ」状態に変える

率直に言って、Claude Code の素の性能は「context を渡す質と量で完全に決まる」。あなたが既に Skills を作り込んでいる理由はまさにここで、tribal-mapper はその系譜の最終形に近い。

具体的に何が変わるか:
- **Before**: 「このバグ直して」→ Claude が grep を 30 回打って探索 → 半分間違える
- **After**: `/tribal-route` で 3-5 枚 context ロード → 「このバグ直して」→ Claude が一発で正しい場所を直す

Meta 論文の 40% fewer AI agent tool calls per task はこれが定量化されたもの。要するに **Claude が試行錯誤する時間とトークンが減る**。あなたが Claude Code に毎月いくら払っているか分からないが、効きは確実に体感できる。

---

## シナリオ5: 個人プロジェクトでの「設計負債の可視化」

副業や個人プロジェクト（あなたで言えば ImageFlow / ServerlessTaskHub のような学習プロジェクト、もしくは BoC のような実用プロジェクト）に入れると、面白い副作用がある。

`coverage-auditor` が orphan_contexts を出してきたり、`Q3_search_log` で「Q3 が見つかりませんでした」が連発するモジュールがあったら、**そのモジュールは責務が曖昧か過剰に単純**だというシグナル。逆に Q3 が 10 件以上出るモジュールは**設計負債が溜まっている**。

これは普通のメトリクス（cyclomatic complexity 等）では拾えない「人間の暗黙ルール量」を可視化していて、リファクタの優先順位付けに使える。

---

## どこから始めるかの推奨

あなたの状況だと、私の推奨はこの順:

1. **今週**: 個人プロジェクト1つ（小さめ、5-10モジュール程度）で `/tribal-init` を試す。所要時間と生成物の質を体感する。ここで「どう動くか」を腹落ちさせる。
2. **今月**: 過去の SES 案件の中で「あの時もっと早くキャッチアップしたかった」と思ったプロジェクトで、コードが手元にあるなら試してみる。生成 context を読んで「自分の当時の理解と一致しているか」を確認する。これは tribal-mapper の信頼性キャリブレーション。
3. **次の現場参画時**: 初日の午後に `/tribal-init` を流して放置。翌朝の通勤中に Q3 を読む。**これだけで参画速度は別物になる**。
4. **半年後**: チームに「自分が使ってるツールがあるんですが」と紹介して、希望者から導入。

---

## 期待しすぎない方が良い点

正直に言っておく:

- **小規模プロジェクト（1-2モジュール）には過剰**。CLAUDE.md に直接書く方が早い。tribal-mapper は 10モジュール以上の規模で本領発揮する。
- **ドメイン知識が外部にある場合は弱い**。例えば「金融商品の規制要件」のような、コードに書かれていない知識は Q5 でも拾えない。これは別途ドキュメントで補う必要がある。
- **初回 `/tribal-init` は時間と API トークンを食う**。10モジュールで 1-2 時間、100モジュールで一晩くらい見ておく。コスト感覚は最初の1回で掴める。
- **生成 context を盲信しない**。critic スコアが 4.0 でも、Q3 が 100% 正しいわけではない。最初のうちは生成された Q3 を実際のコードと突き合わせる癖をつける（**そして間違いを見つけたら analyst のプロンプトを改善するネタになる**）。

---

## 一言で言うと

これは「**Claude Code を SES エンジニアの相棒として最大化するための土台**」です。あなたがこれまで Skills エコシステムで個別に解いてきた問題（PAML、WoF、code-commenter など）を、**プロジェクト固有の知識**という最後のピースで補完する位置づけ。

最初の現場で1回試してみて、効果を体感したら、それがあなたの差別化要因になる。SES 業界で「3週間でキャッチアップする人」は普通だが、「3日でキャッチアップする人」は希少。