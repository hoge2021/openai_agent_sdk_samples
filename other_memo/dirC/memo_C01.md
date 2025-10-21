了解。**方式A（Chrome DevTools Protocol; CDP）をmacOSで動かす具体手順**を、ゼロから“そのまま実行できる形”でまとめます。アプリ本体は一切改修不要です。

# 手順の全体像

1. Chromeを「リモートデバッグポート付き」で起動
2. ポートが開いたことを確認
3. Nodeスクリプト（Puppeteer Core）でCDPに接続 → `console`/`pageerror`/`requestfailed`を収集
4. VSCodeのデバッグ実行（任意）

---

# 0. 事前: 既存のChromeを全部終了

macでは既存のChromeが動いているとプロファイルがロックされ、CDP起動が詰まります。

* 右上のChromeを**完全終了**（⌘Q）
* 念のためプロセス確認:

```bash
ps aux | grep "Google Chrome" | grep -v grep
```

残っていれば `kill -9 <PID>` で殺してOKです。

---

# 1. ChromeをCDP付きで起動（macOS）

以下を**ターミナル（zsh）**で実行。`--user-data-dir`は一時プロファイル用に空ディレクトリを指定。

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-dev \
  --no-first-run --no-default-browser-check
```

> 補足
>
> * Canaryを使うなら`/Applications/Google Chrome Canary.app/...`に置き換え可
> * 9222は慣例。埋まっていれば他ポートでもOK

---

# 2. ポートが開いたか確認

別ターミナルで:

```bash
curl -s http://127.0.0.1:9222/json/version | jq .
```

`"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."` が返ればOK。`jq`が無いなら`curl`の生出力でOKです。

---

# 3. Nodeプロジェクト最小セット（Puppeteer Core）

プロジェクト用ディレクトリで:

```bash
mkdir cdp-sniffer && cd cdp-sniffer
npm init -y
npm i puppeteer-core
```

**JavaScript版（TypeScript不要）の最小スクリプト**を用意します。

```js
// log-front-errors.js
const puppeteer = require("puppeteer-core");

async function toPrintable(argHandle) {
  try { return await argHandle.jsonValue(); } catch { return String(argHandle); }
}

(async () => {
  // 既存のCDPブラウザに接続
  const browserURL = "http://127.0.0.1:9222";
  const browser = await puppeteer.connect({ browserURL });

  // 既に開いているタブから対象を探す（無ければ新規）
  const targetHost = "your-target-host.example.com"; // ←収集対象のホスト名に変更
  let pages = await browser.pages();
  let page = null;

  for (const p of pages) {
    const u = await p.url();
    if (u.includes(targetHost)) { page = p; break; }
  }
  if (!page) {
    page = await browser.newPage();
    await page.goto("https://" + targetHost, { waitUntil: "domcontentloaded" });
  }

  // コンソール出力
  page.on("console", async (msg) => {
    const vals = await Promise.all(msg.args().map(toPrintable));
    // 重要度が高いものだけ拾いたい場合は msg.type() でフィルタ (error, warning等)
    console.log(`[BROWSER:${msg.type()}]`, ...vals);
  });

  // ページ上の未捕捉例外
  page.on("pageerror", (err) => {
    console.error("[PAGEERROR]", err.message, "\n", err.stack);
  });

  // ネットワーク失敗
  page.on("requestfailed", (req) => {
    console.warn("[REQUESTFAILED]", req.method(), req.url(), req.failure()?.errorText);
  });

  // CDPのLogドメインも有効化（ブラウザ内部ログが必要な場合）
  const client = await page.target().createCDPSession();
  await client.send("Log.enable");
  client.on("Log.entryAdded", (e) => {
    console.log("[CDP:Log]", e.entry.source, e.entry.level, e.entry.text);
  });

  console.log("Connected. Open the site and reproduce the issue.");
})();
```

実行:

```bash
node log-front-errors.js
```

この状態で、CDP起動中のChrome（手元で操作しているウィンドウ）で対象サイトを触ると、**VSCodeのターミナル/デバッグコンソールに**ブラウザの`console.*`や未捕捉例外が流れます。

> 使い方のコツ
>
> * まずCDP付きChromeで対象サイトを開く
> * `targetHost`をそのドメインに設定（あるいは `.includes()` の代わりに `startsWith()` 等でもOK）
> * 既に開いたタブへ「アタッチ」するため、サイト側の改修は不要

---

# 4. VSCodeからF5で走らせる（任意）

`.vscode/launch.json` を作成:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "node",
      "request": "launch",
      "name": "Front errors via CDP",
      "program": "${workspaceFolder}/log-front-errors.js",
      "console": "integratedTerminal",
      "skipFiles": ["<node_internals>/**"]
    }
  ]
}
```

以後は **F5** 実行で、VSCodeのデバッグコンソールにログが流れます。

---

# 5. よくある詰まりポイントと対処

* **`connect ECONNREFUSED 127.0.0.1:9222`**
  → ChromeをCDPポートで起動できていない。手順1のコマンドを見直し。既存Chromeを完全終了してから再起動。
* **`Target closed`/`Protocol error` が頻発**
  → タブが自動で閉じられた/別プロファイルで起動など。`--user-data-dir`を専用に、Chromeはそのまま起動し続ける。
* **`pages()`に対象が見つからない**
  → スクリプト側で `await page.goto("https://example.com")` を明示するか、`targetHost`の文字列を正しく設定。
* **M1/M2 Macでの動作**
  → そのままでOK。`puppeteer-core`は**既存Chrome**に接続するだけなので追加設定不要。
* **セキュリティ**
  → `--remote-debugging-port` は**ローカル専用**で使うこと（SSHトンネル越し等にしない）。公開NWでリッスンさせない。

---

# 6. Playwright派の最小サンプル（代替）

Puppeteerの代わりにPlaywrightでもOK。既存ブラウザにCDP接続する場合:

```bash
npm i -D playwright
```

```js
// pw-cdp.js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const contexts = browser.contexts();
  const page = contexts[0]?.pages()[0] || (await contexts[0].newPage());

  page.on("console", (m) => console.log("[CONSOLE]", m.type(), m.text()));
  page.on("pageerror", (e) => console.error("[PAGEERROR]", e.message));
  page.on("requestfailed", (r) => console.warn("[NETFAIL]", r.url(), r.failure()?.errorText));

  console.log("Connected via Playwright. Reproduce the issue in the attached page.");
})();
```

実行:

```bash
node pw-cdp.js
```

---

# 7. 使いどころ（現場Tips）

* 本番・既存Webシステムに**手を入れず**に、実ユーザ環境に近い形で`console`やエラーを回収したい時に最短。
* 収集ログを**ファイル保存**したい場合は、Node側で`fs.createWriteStream`に吐き出すだけ。
* さらに自動化するなら、このスニファーを**Git管理**し、VSCodeのタスク/launch.jsonでワンキー起動に。

---

必要なら、このまま**あなたの実ドメイン名に合わせた完成版**（フィルタ、ファイル保存、時刻・URL・タブID付与、JSON Linesで出力、簡易ダッシュボード）まで一気に出します。
