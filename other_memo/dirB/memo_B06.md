
■OpenSpecの使い方
https://www.youtube.com/watch?v=F25_p0QzV6w
https://github.com/Fission-AI/OpenSpec/?tab=readme-ov-file

■コマンド
npm install -g @fission-ai/openspec@latest

openspec --help
openspec init   #初期設定

Commands:
コマンド:
  init [options] [path]            Initialize OpenSpec in your project
  init [options] [path]            プロジェクトでOpenSpecを初期化
  update [path]                    Update OpenSpec instruction files
  update [path]                    OpenSpecの指示ファイルを更新
  list [options]                   List items (changes by default). Use --specs to list specs.
  list [options]                   アイテムを一覧表示 (デフォルトは変更点)。 --specs で仕様を一覧表示。
  view                             Display an interactive dashboard of specs and changes
  view                             仕様と変更点のインタラクティブなダッシュボードを表示
  change                           Manage OpenSpec change proposals
  change                           OpenSpecの変更提案を管理
  archive [options] [change-name]  Archive a completed change and update main specs
  archive [options] [change-name]  完了した変更をアーカイブし、メインの仕様を更新
  spec        _                    Manage and view OpenSpec specifications
  spec                             OpenSpecの仕様を管理・表示
  validate [options] [item-name]   Validate changes and specs
  validate [options] [item-name]   変更点と仕様を検証
  show [options] [item-name]       Show a change or spec
  show [options] [item-name]       変更点または仕様を表示
  help [command]                   display help for command
  help [command]                   コマンドのヘルプを表示



■出現するプロンプト
openspec-proposal.prompt.md
openspec-apply.prompt.md    　　タスクを開始し始める
openspec-archive.prompt.md　　　完了したら打つ。

■基本的な使い方
1. Draft a change proposal that captures the spec updates you want.
あなたが望む仕様の更新を取り込む変更提案書を作成します。
2. Review the proposal with your AI assistant until everyone agrees.
全員が合意するまで、あなたのAIアシスタントと一緒に提案書をレビューします。
3. Implement tasks that reference the agreed specs.
合意された仕様を参照するタスクを実行します。
4. Archive the change to merge the approved updates back into the source-of-truth specs.
承認された更新を「信頼できる唯一の情報源」である仕様にマージするために、その変更をアーカイブします。




■初期設定したら以下の下準備を行う。

1. Populate your project context:
訳、既存プロジェクトの概要や技術スタックの情報を、教えてください。
※サンプルプロンプト
   "Please read openspec/project.md and help me fill it out
    with details about my project, tech stack, and conventions"
※openspec/project.mdに記述してください。
※おそらくserenaのMCPサーバからsavanを使ったほうが良いと思われ。

2. Create your first change proposal:
訳、変更したい機能について、計画案を作成してください。
※サンプルプロンプト
   "I want to add [YOUR FEATURE HERE]. Please create an
    OpenSpec change proposal for this feature"
※プロジェクト/openspec/changes/配下に
※サンプル編集例
   "I want to リファクタリング. Please create an
    OpenSpec change proposal for this feature"

3. Learn the OpenSpec workflow:
訳: OpenSpecワークフローを学ぶための、説明してください。
   "Please explain the OpenSpec workflow from openspec/AGENTS.md
    and how I should work with you on this project"

※その情報を参考に後続の作業をすすめてください。



