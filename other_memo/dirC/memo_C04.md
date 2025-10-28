チーム開発していると、他の人が書いたソースコードを理解して把握すること作業も併用して行う必要があるが、
私はNext.js初心者な上に、理解が難しく。また自らのコーディングにも時間がかかって、他の人が作ったコードの把握に時間が取れていない。
Webシステムの規模によって把握するコード量もかなり多い。（Next.jsのソースコードはわかりにくい）

しかも、昨今ではAIを利用したコーディングによって効率化が進んでいるが、それは人が作るコード量も増えるということで、
時間を多く取らなければならないのだ。

さて、こんな状況の中、ソースコードを理解できるようになるにはどうしたらよいだろうか？　最適解を答えよ。

補足:平日は残業多めで休息を最優先しています。



了解。時間と体力が限られる前提で、「読む量を極小化して理解の質を最大化」する最適解を提示します。結論は“構造→挙動→詳細”の順で、変更点と主要動線だけをAIとツールに外注して潰すことです。

# 最短経路（TL;DR）

1. 全体像は**自動可視化**で一気に掴む（ルートマップ・依存関係・ホットスポット）。2) **1ユーザージャーニー**だけ挙動で理解（Story/テスト/ログ）。3) 読むのは**差分と契約（I/O・副作用）だけ**。4) まとめは**AIに要約**させて手元に「Codebook.md」を育てる。5) 平日は**10〜12分のマイクロループ**、週末に**90分の深掘り**。これで“わかるまで読む”をやめ、“わかる所だけを確実に掴む”。

---

## 0. 読む順番（Next.js特化の最低限）

1. `package.json`（Next/React/主要ライブラリ、scripts）→ `next.config.(js|mjs|ts)`（`basePath`,`rewrites`,`experimental`）→ `tsconfig.json`（`paths`のエイリアス）
2. `app/`（App Router前提）: `layout.tsx`→`page.tsx`→`(group)`→動的セグメント`[slug]`→`route.ts`(API)→`middleware.ts`
3. `src/providers`/`components`/`lib`/`hooks`/`store`（Context/Zustand/React Queryなど“状態の入口”だけ）
   読む基準は「入口だけ」。詳細実装は後回し。

---

## 1. まず“見える化”で全体像を一撃理解（30〜40分）

### A. ルートマップ（App Routerの実体を列挙）

`scripts/route-map.ts`を作成し、`app/`配下の`page.tsx`/`route.ts`を一覧化します。

```ts
// scripts/route-map.ts
import fg from "fast-glob";
import path from "node:path";
import fs from "node:fs";

const APP_DIR = path.resolve(process.cwd(), "app");

function toRoute(p: string) {
  let rel = path.relative(APP_DIR, p).replace(/\\/g, "/");
  rel = rel.replace(/\/(page|route)\.(tsx|ts|jsx|js)$/, "");
  // (group)除去、動的セグメントは :id と表記
  rel = rel
    .split("/")
    .filter(seg => !seg.startsWith("(") || !seg.endsWith(")"))
    .join("/")
    .replace(/\[\.\.\.(.+?)\]/g, ":$1*")
    .replace(/\[(.+?)\]/g, ":$1");
  return "/" + (rel === "" ? "" : rel);
}

(async () => {
  const pages = await fg(["app/**/page.{ts,tsx,js,jsx}"], { dot: false });
  const apis  = await fg(["app/**/route.{ts,tsx,js,jsx}"], { dot: false });
  const rows: Array<{type: string; file: string; route: string}> = [];

  for (const f of pages) rows.push({ type: "PAGE", file: f, route: toRoute(f) });
  for (const f of apis)  rows.push({ type: "API",  file: f, route: toRoute(f) });

  rows.sort((a,b)=> a.route.localeCompare(b.route) || a.type.localeCompare(b.type));
  const out = ["TYPE\tROUTE\tFILE", ...rows.map(r => `${r.type}\t${r.route}\t${path.relative(process.cwd(), r.file)}`)].join("\n");
  fs.mkdirSync("artifacts", { recursive: true });
  fs.writeFileSync("artifacts/route-map.tsv", out, "utf8");
  console.log(out);
})();
```

実行:

```
npm i -D fast-glob
npx tsx scripts/route-map.ts
```

→ `artifacts/route-map.tsv`が“読むべき画面/APIの索引”になります。まずはここから“どの画面があり、入口はどこか”だけを把握。

### B. 変更の“熱い場所”（Hotspot）を抽出（5分）

直近30日の変更頻度上位=理解優先度。

```
git log --since="30 days ago" --name-only --pretty=format: |
  grep -E '^(app|src)/' | sort | uniq -c | sort -nr | head -n 40
```

上位10〜20ファイルを「今日読む候補」にする。

### C. サーバ/クライアント境界の高速把握（5分）

```
rg -n --no-ignore -S "['\"]use client['\"]|['\"]use server['\"]" app src
rg -n --no-ignore -S "create\(|configureStore\(|atom\(|createClient\(" src app # Zustand/Redux/Jotai/DB client等の“状態入口”
rg -n --no-ignore -S "useSWR|@tanstack/react-query|axios|ky|gql|trpc" src app
```

「状態の入口」「データ取得の入口」だけに印を付ける（★）。

---

## 2. “挙動で理解”する：1ユーザージャーニーだけ（45〜60分）

1. ルートマップから**1つの主要導線**（例：ログイン→一覧→詳細→編集→保存）を選ぶ
2. 実行しながら**React DevTools**でコンポーネントツリーを確認
3. **ネットワークログ**でAPI呼び出しの順序を把握
4. その導線に関係する`PAGE`/`API`/`store`/`fetcher`だけを読む
5. 行動のスナップショットを**Story（UI）**と**Playwright（E2E）**で1つずつ作る（ふるまいの固定化=理解の固定化）

> Tips（時間がない時の最小構成）
>
> * Storybookが未導入なら、UIの“状態”が分かる最小1 Storyだけ作成（モックデータ固定）
> * Playwrightなら**1シナリオだけ**。`page.goto('/list')→検索→行クリック→詳細表示`程度でOK
> * これらは**仕様ドキュメントの代替**になり、以降の理解コストが激減

---

## 3. “読むのは契約だけ”のルール

各ファイルで拾うのは次の5点だけ（3〜5分/ファイル）。

* 目的（1行）
* 入力（props/引数/クエリ/ボディ）
* 出力（返り値/描画内容/イベント）
* 副作用（API呼出し/状態更新/ナビゲーション）
* 依存（他モジュール・コンテキスト）
  これを`docs/Codebook.md`に追記していく（テンプレ下記）。

**Codebook.md テンプレ（貼って使うだけ）**

```
## <path/to/file>
- Purpose:
- Inputs:
- Outputs:
- Side Effects:
- Depends On:
```

---

## 4. AIに“要約と索引づくり”を外注（Copilot/ChatGPTで即使える日本語プロンプト）

* 「このファイルの目的・入出力・副作用・依存を上の5項目テンプレで100〜150字×各項目に要約して。コード例は不要。」
* 「このコンポーネントの**レンダリング条件・非同期処理のトリガ・解除条件**を列挙。メモリリーク・二重呼び出しの懸念があれば指摘。」
* 「この`route.ts`（API）の**契約**（URL/メソッド/必須パラメータ/バリデーション/戻り型/エラー）を表にして。」
* 「`git diff <base>...<head>`の差分から**破壊的変更の可能性**と**テストが必要な観点**を列挙。」
* 「`app/(group)/[id]/page.tsx`の**依存関数の呼び出し順**を擬似コードで10行以内に。」

> 重要: **出力は必ずCodebook.mdにコピー**。知識を“外に出して固定”するほど、後の自分が楽になります。

---

## 5. 平日10〜12分×3回の“マイクロループ”

* ① 2分: 今日の対象を**1ファイル**に限定（Hotspot/導線に関係するものだけ）
* ② 6〜8分: AI要約→5項目テンプレを埋める
* ③ 2分: 既存Story/E2Eに**1ケースだけ**追加 or TODO化
  この小刻み積み上げが、残業多めでも続けられる現実解です。

---

## 6. 週末90分の“固定資産化”メニュー

* 0–15分: ルートマップ更新（scripts実行）＋Hotspot再抽出
* 15–45分: 主要導線の**Playwright 1シナリオ**整備（MSWなどでAPIモックでも可）
* 45–75分: 直近差分の**破壊的変更の観点**を抽出→チェックリスト化
* 75–90分: Codebook.md整理（抜けている5項目テンプレを補完）

---

## 7. “他人のコードが分かりにくい”を構造的に減らす仕掛け（提案してOKな軽量ルール）

* PRテンプレに**「目的/契約/I/O/副作用」4項目**を必須化（本文50〜120字×各項目で十分）
* コンポーネント先頭に**3行JSDoc**（Purpose/Inputs/SideEffects）
* `lib/fetcher.ts`など**API呼び出しを一箇所に集約**（型・zodバリデーションもそこへ）
* 1画面1ディレクトリ（`page.tsx`と`components/`と`actions.ts`を同居）で**局所化**
* `paths`エイリアスの**命名規約**を揃える（例：`@/ui`,`@/features/*`,`@/entities/*`）

---

## 8. すぐ使える“手元コマンド”集

```bash
# 直近の作者ヒートマップ（誰に聞けば早いか）
git shortlog -sn --since="30 days ago" -- app src | head -n 10

# 型の入口（Zod/Valibot/Yupなど）
rg -n -S "zod|valibot|yup|class-validator" src app

# ルーティングとAPI実装の一覧（先のroute-mapで十分。簡易なら）
rg -n --no-ignore -S "^export async function (GET|POST|PUT|DELETE|PATCH)" app
```

---

## 9. よくある落とし穴（Next.js）

* **Server/Clientの境界**を超えるimport（`'use client'`からサーバ専用モジュールを読む等）
* **Route Handlerの副作用**（Cookie/ヘッダ書き換え、キャッシュ）を見落としてUIだけ読む
* **`middleware.ts`のリダイレクト/認可**に気付かず「画面が出ない」と迷う
* **`paths`エイリアスの多用**で所在が分からない→最初に`tsconfig.json`で逆引き表を作る

---

## 10. 体力最優先の運用ルール（無理しない版）

* 平日は**“1ファイルだけ”**・**“5項目だけ”**・**“10分だけ”**
* 疲れている日は**AI要約だけ**でOK（自分の目では読まない日があっても積み上がる）
* 週末は**90分1セット**。セットが取れない時は**30分×3**に分割

---

### これで得られる効果

* 読む対象を**入口と差分**に限定するので、総読書量が激減
* 挙動（Story/E2E）を先に固めるので、**“分かった気”が残る**
* Codebook.mdが蓄積し、**次回以降は索引から直行**できる

必要なら、上の`route-map.ts`や`Codebook.md`の雛形をあなたのリポジトリ構成に合わせて微調整します。どの導線（画面）から始めるのが良いかも、今の案件に合わせて選定します。



いい質問！どちらも`rg`（ripgrep）で“読む場所を最短で特定する”ための索引づくりコマンドです。オプションの意味→何が拾えるか→なぜ役に立つか、の順で説明します。

# 共通オプションの意味

* `rg`: 高速全文検索（git管理下の大規模リポでも一瞬）
* `-n`: 行番号を表示（VSCodeで該当行に直行しやすい）
* `-S`: Smart Case（パターンが全部小文字なら大小無視、1文字でも大文字があれば大文字小文字を区別）
* `--no-ignore`: `.gitignore`等の無視設定を一時無効化（モノレポなどで誤って除外されるのを回避）※不要なら省いてOK

---

## 1) 型の入口を洗い出す

```
rg -n -S "zod|valibot|yup|class-validator" src app
```

### 何をしている？

`src`と`app`配下で、代表的なスキーマ/バリデーション系ライブラリ名を含む行を検索します。例:

* zod（`z.object({...})`）
* valibot
* yup
* class-validator（デコレータでDTOを定義）

### これで何が拾える？

* 入出力の**契約（スキーマ）**を定義している場所（`schema.ts`や`validators.ts`、フォームやAPI直前のバリデーション）
* APIやフォームの**必須フィールド・型・制約**（最短で“何が要るか”が分かる）

### なぜ役立つ？

* Next.jsはコンポーネントやhooksが多層に分かれがちですが、**データの形＝設計の根っこ**です。まず“型の入口”を読むと、UI/処理の細部を読まなくても大枠が掴めます（読む量を激減）。
* ここで見つけたスキーマをCodebookに「Inputs/Outputs/Side Effects」として2〜3分で要約→以後は索引から直行できます。

#### 精度をさらに上げる例（実体スキーマだけ狙う）

```
rg -n -S "z\.object\(|yup\.[A-Za-z]+\(|class-validator|valibot" src app
# ユニークなファイルだけ欲しいとき
rg -n -S "z\.object\(|yup\.[A-Za-z]+\(|class-validator|valibot" src app | cut -d: -f1 | sort -u
```

---

## 2) ルートハンドラ（API）を一覧化する

```
rg -n --no-ignore -S "^export async function (GET|POST|PUT|DELETE|PATCH)" app
```

### 何をしている？

App Routerの`route.ts`に典型的な形で書かれる

```ts
export async function GET(req: Request) { ... }
```

などを、`app`配下から行頭一致で拾います。結果は「どのパスにどのHTTPメソッドが実装されているか」のラフな索引になります。

### これで何が拾える？

* 実装されている**エンドポイントの網羅リスト**（どの画面が何を叩いていそうかが一目）
* 主要導線（例: 一覧→詳細→更新）に関わる`route.ts`を即座に開ける

### なぜ役立つ？

* “まず挙動、次に詳細”で理解するための**最短導線**を作れます。APIエンドポイントの契約を見れば、UI側で何が入力・出力されるかの当たりがつき、読む範囲が絞れます。
* AIに要約させる起点としても最適（「この`POST`の必須パラメータとバリデーションを表にして」など）。

#### 抜け漏れを減らす改良（HEAD/OPTIONSやconst形式も拾う）

Next.jsは`HEAD`/`OPTIONS`もあり、書き方も2種類（function式 or const代入）あります。必要なら2本で網羅を上げられます。

```bash
# function式
rg -n -S '^export (async )?function (GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b' app
# const式
rg -n -S '^export (const|let|var) (GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b' app
```

※古いPages Routerの`pages/api/*`なら:

```bash
rg -n -S '^export default' pages/api
```

---

## 具体イメージ（出力例）

```
app/api/users/route.ts:12:export async function GET(req: Request) {
app/api/users/route.ts:28:export async function POST(req: Request) {
src/entities/user/schema.ts:3:import { z } from "zod";
```

→ この3本だけ読めば、「ユーザ一覧取得/作成の契約」と「ユーザ型の定義」がわかる＝画面のI/O像が一気に見える。

---

## 10分での使い方（平日・省エネ版）

1. ルート一覧（②）を流して、今日触る導線に関係する`route.ts`を1つだけ開く
2. 型の入口（①）で該当スキーマを1つだけ開く
3. それぞれを「Purpose/Inputs/Outputs/SideEffects/DependsOn」でCodebookに箇条書き（各1行ずつ）
   → “読む量を最小化しつつ、次回から検索→直行”できる体制が整います

---

## 補足（よくある疑問）

* **`-S`は何のため？** 1つ目の検索語は全部小文字なので**大文字小文字を無視**して拾い漏れを防ぎ、2つ目は`GET/POST…`が大文字なので**大文字小文字を区別**してノイズを減らす、という意図です。
* **`--no-ignore`は必須？** いいえ。通常の`app/`なら不要なことが多いです。モノレポやカスタム`.gitignore`で除外される可能性があるときの保険です。
* **rgがない** → mac: `brew install ripgrep` / Windows: `choco install ripgrep`

この2コマンドは「型の入口」と「APIの入口」を一瞬で見つけ、読む範囲を“入口と契約だけ”に限定するためのショートカットです。結果として、Next.js初心者でも**理解の土台を最短で作れる**ので、残業多めでも回せます。


■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
いい質問！どちらも`rg`（ripgrep）で“読む場所を最短で特定する”ための索引づくりコマンドです。オプションの意味→何が拾えるか→なぜ役に立つか、の順で説明します。

# 共通オプションの意味

* `rg`: 高速全文検索（git管理下の大規模リポでも一瞬）
* `-n`: 行番号を表示（VSCodeで該当行に直行しやすい）
* `-S`: Smart Case（パターンが全部小文字なら大小無視、1文字でも大文字があれば大文字小文字を区別）
* `--no-ignore`: `.gitignore`等の無視設定を一時無効化（モノレポなどで誤って除外されるのを回避）※不要なら省いてOK

---

## 1) 型の入口を洗い出す

```
rg -n -S "zod|valibot|yup|class-validator" src app
```

### 何をしている？

`src`と`app`配下で、代表的なスキーマ/バリデーション系ライブラリ名を含む行を検索します。例:

* zod（`z.object({...})`）
* valibot
* yup
* class-validator（デコレータでDTOを定義）

### これで何が拾える？

* 入出力の**契約（スキーマ）**を定義している場所（`schema.ts`や`validators.ts`、フォームやAPI直前のバリデーション）
* APIやフォームの**必須フィールド・型・制約**（最短で“何が要るか”が分かる）

### なぜ役立つ？

* Next.jsはコンポーネントやhooksが多層に分かれがちですが、**データの形＝設計の根っこ**です。まず“型の入口”を読むと、UI/処理の細部を読まなくても大枠が掴めます（読む量を激減）。
* ここで見つけたスキーマをCodebookに「Inputs/Outputs/Side Effects」として2〜3分で要約→以後は索引から直行できます。

#### 精度をさらに上げる例（実体スキーマだけ狙う）

```
rg -n -S "z\.object\(|yup\.[A-Za-z]+\(|class-validator|valibot" src app
# ユニークなファイルだけ欲しいとき
rg -n -S "z\.object\(|yup\.[A-Za-z]+\(|class-validator|valibot" src app | cut -d: -f1 | sort -u
```

---

## 2) ルートハンドラ（API）を一覧化する

```
rg -n --no-ignore -S "^export async function (GET|POST|PUT|DELETE|PATCH)" app
```

### 何をしている？

App Routerの`route.ts`に典型的な形で書かれる

```ts
export async function GET(req: Request) { ... }
```

などを、`app`配下から行頭一致で拾います。結果は「どのパスにどのHTTPメソッドが実装されているか」のラフな索引になります。

### これで何が拾える？

* 実装されている**エンドポイントの網羅リスト**（どの画面が何を叩いていそうかが一目）
* 主要導線（例: 一覧→詳細→更新）に関わる`route.ts`を即座に開ける

### なぜ役立つ？

* “まず挙動、次に詳細”で理解するための**最短導線**を作れます。APIエンドポイントの契約を見れば、UI側で何が入力・出力されるかの当たりがつき、読む範囲が絞れます。
* AIに要約させる起点としても最適（「この`POST`の必須パラメータとバリデーションを表にして」など）。

#### 抜け漏れを減らす改良（HEAD/OPTIONSやconst形式も拾う）

Next.jsは`HEAD`/`OPTIONS`もあり、書き方も2種類（function式 or const代入）あります。必要なら2本で網羅を上げられます。

```bash
# function式
rg -n -S '^export (async )?function (GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b' app
# const式
rg -n -S '^export (const|let|var) (GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b' app
```

※古いPages Routerの`pages/api/*`なら:

```bash
rg -n -S '^export default' pages/api
```

---

## 具体イメージ（出力例）

```
app/api/users/route.ts:12:export async function GET(req: Request) {
app/api/users/route.ts:28:export async function POST(req: Request) {
src/entities/user/schema.ts:3:import { z } from "zod";
```

→ この3本だけ読めば、「ユーザ一覧取得/作成の契約」と「ユーザ型の定義」がわかる＝画面のI/O像が一気に見える。

---

## 10分での使い方（平日・省エネ版）

1. ルート一覧（②）を流して、今日触る導線に関係する`route.ts`を1つだけ開く
2. 型の入口（①）で該当スキーマを1つだけ開く
3. それぞれを「Purpose/Inputs/Outputs/SideEffects/DependsOn」でCodebookに箇条書き（各1行ずつ）
   → “読む量を最小化しつつ、次回から検索→直行”できる体制が整います

---

## 補足（よくある疑問）

* **`-S`は何のため？** 1つ目の検索語は全部小文字なので**大文字小文字を無視**して拾い漏れを防ぎ、2つ目は`GET/POST…`が大文字なので**大文字小文字を区別**してノイズを減らす、という意図です。
* **`--no-ignore`は必須？** いいえ。通常の`app/`なら不要なことが多いです。モノレポやカスタム`.gitignore`で除外される可能性があるときの保険です。
* **rgがない** → mac: `brew install ripgrep` / Windows: `choco install ripgrep`

この2コマンドは「型の入口」と「APIの入口」を一瞬で見つけ、読む範囲を“入口と契約だけ”に限定するためのショートカットです。結果として、Next.js初心者でも**理解の土台を最短で作れる**ので、残業多めでも回せます。

■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
追加で質問。最近Web開発でNext.jsのコーディングする時は、ほぼ100%、Claude Codeを使用している。 　背景としてスケジュールがきつく、時間も技術も足りないので、生成AIの力に頼らざるを得ないのだが、同時いくつか問題が併発している。 問題1.Claude Codeの生成したコードが、チーム開発のコーディングルールに沿っていなかったり、色々と間違いがあったりする。 　ユーザ自ら視認して、AIが生成したコードを見直しして適宜修正する他ないのだが、Next.js初心者の自分にちゃんとしたチェックもできるはずもなく、またそれを行う十分な時間もない。加えて、コード自体がClaude Codeで生成したものだから、後になってどういう意図で作られたのがユーザ自身が理解できていないケースがある。どうすれば解決できるだろうか？ 問題2.Claude Codeでコードを生成しているため、ユーザ自身のコーディング能力があまり上がっていないこと。 かと言って手動でコーディングする時間的猶予があるなら、とっくにやっているし、なんとかClaude Codeなどの生成AIを駆使しつつも、コーディング能力を向上させる方法はないものか？　最適化を教えて欲しい。


いいね、そのヘッダ（Role/Context/Checklist）は“固定プリセット”。実際のコード指示は、その下に**Taskブロック**を足して出します。つまり「ヘッダ＝出力様式のルール」「Task＝今回やる内容」。毎回この形で投げれば、Claude Codeは必ず**PLAN→DIFF→SELF-REVIEW**で返してきます。

# 使い方（最小形）

ヘッダの下に、これだけ添えればOKです。

```
Task:
- Title: ユーザー一覧に検索フィルタを追加
- Targets: app/(dashboard)/users/page.tsx, app/api/users/route.ts
- Acceptance Criteria:
  1) クエリqで部分一致検索が機能する
  2) UIに入力欄とクリアボタン。入力時にURLクエリ同期
  3) 既存CI(lint/typecheck/build)を通過
- Constraints: 依存追加禁止・差分は最小・Server Components優先
- Tests: Playwrightで「検索→結果件数が変わる」を1本追加（モック可）
- Output: 上記ヘッダの様式（PLAN/DIFF/SELF-REVIEW）。各ファイル先頭にJSDoc（Purpose/Inputs/Outputs/Side Effects/Depends On）
```

→ “何を・どこに・合格条件・制約・テスト・出力様式”の6点を短く指定するのがコツ。

# もう少し厳密に書くテンプレ（コピペして使う）

```
Task:
- Objective: <今回の変更の目的を1-2文>
- Scope (Files/Dirs): <確実に触るパス。未確定なら候補を書かせてもOK>
- Contract:
  - Inputs: <props/クエリ/ボディの要点>
  - Outputs: <返り値/描画/副作用>
  - Errors: <主要エラーとHTTPステータス>
- Acceptance Criteria:
  1) <合格条件1>  2) <合格条件2>  3) <合格条件3>
- Constraints: 依存追加禁止 / 既存APIは破壊的変更不可 / 差分<120行 など
- Tests: <E2E/Story/ユニットの最小1本。観点を1-2行で>
- Notes: 既知の周辺仕様・権限・キャッシュ・middleware注意点
- Output: PLAN / DIFF（git適用可能なパッチ or *** Begin Patch形式）/ SELF-REVIEW（Checklist照合）
```

# 具体例1（UIとAPIを同時改修する依頼の書き方）

```
Task:
- Title: ユーザー一覧に検索機能を追加（qパラメータ）
- Objective: 一覧ページで名前部分一致検索を可能にする
- Scope: 
  - app/(dashboard)/users/page.tsx（検索UIとURL同期）
  - app/api/users/route.ts（GETに?q=<string>対応）
  - src/entities/user/schema.ts（必要ならQuerySchemaを追加）
- Contract:
  - Inputs: GET /api/users?q=<string|optional>
  - Outputs: 200: User[] / 400: {message}（バリデーションエラー）
- Acceptance Criteria:
  1) q未指定で全件、q指定で部分一致フィルタ
  2) 検索UIはServer Components方針を崩さず、必要部のみclient化
  3) ESLint/Prettier/Typecheck/Buildがpass
- Constraints: 依存追加禁止 / zodでサーバ側バリデーション / 既存呼び出し互換を維持
- Tests: Playwright 1本（q='a'で件数が絞られる） / Story 1本（検索UIの見た目）
- Output: ヘッダに従い、PLAN→DIFF→SELF-REVIEWで返答。各ファイル先頭にJSDoc5項目
```

# 具体例2（APIだけ増やす依頼の書き方）

```
Task:
- Title: POST /api/todos を追加
- Objective: Todoを作成できるAPIを追加し、201で返す
- Scope: app/api/todos/route.ts（POST）, src/entities/todo/schema.ts
- Contract:
  - Inputs: { title: string(min 1..100), dueDate?: string(ISO) }
  - Outputs: 201: { id, title, dueDate } / 400: { message } / 500: { message }
- Acceptance Criteria:
  1) zodで入力検証、失敗は400
  2) NextResponse.json({...}, { status: 201 })
  3) CIパス
- Constraints: 永続層は既存のRepo/Service呼び出しを使用。依存追加禁止
- Tests: ユニット or ルートハンドラ直呼びで201/400の2ケース
- Output: PLAN / DIFF / SELF-REVIEW（Checklist照合）
```

# 具体例3（“既存の差分だけ直して”と頼むとき）

```
Task:
- Title: 直近PRのコンポーネントで未使用import・型anyを解消
- Scope: app/(dashboard)/users/UserRow.tsx, src/lib/format.ts
- Acceptance Criteria:
  1) unused-importsゼロ / any禁止（適切な型注釈に置換）
  2) 既存のスナップショットが変わらない
- Output: PLAN / DIFF / SELF-REVIEW（ESLint/Typecheck項目を明記）
```

# うまくいくコツ（短時間で精度UP）

* **Targetsをできるだけ具体的に書く**：ファイル名が分かるほど、無駄な差分が減ります。分からないときは「候補を3つ挙げてから最適を選んで作業して」と添える。
* **Acceptance Criteriaは3個まで**：多いと迷走します。UIなら「見た目」「挙動」「CI pass」の3点が鉄板。
* **Constraintsで“依存追加禁止/差分最小”を毎回固定**：レビュー負荷が激減します。
* **Outputを毎回明記**：必ず「PLAN/DIFF/SELF-REVIEWで返せ」と書く（忘れると普通の説明文になります）。
* **JSDoc5項目を義務化**：意図の可視化。読む量が減ります。

# 返ってきたDIFFの扱い

* Claude Codeなら“Apply Diff”できるはず。生のChatなら**パッチ形式**で出させて`git apply`や手動適用。推奨フォーマット：

  * `diff --git a/... b/...`の**統一diff**
  * もしくは

  ```
  *** Begin Patch
  *** Update File: app/users/page.tsx
  @@
  - 旧行
  + 新行
  *** End Patch
  ```

  どちらでも機械適用しやすいです。

この運用なら、あなたは毎回**Taskブロック**だけ書けばOK。残り（設計→差分→自己レビュー→JSDoc）はAIが自動で整えます。時間がない日は「最小版テンプレ」で十分です。
