import asyncio
import os
from openai import OpenAI

# ========================================
# 1. ファイルアップロードとAssistant作成
# ========================================

def upload_files_and_create_assistant(file_paths: list[str]) -> tuple[str, list[str]]:
    """ファイルをアップロードしてAssistantを作成（シンプル版）"""
    
    client = OpenAI()
    
    # ファイルをアップロード
    file_ids = []
    for path in file_paths:
        if os.path.exists(path):
            with open(path, "rb") as file:
                uploaded = client.files.create(
                    file=file,
                    purpose="assistants"
                )
                file_ids.append(uploaded.id)
                print(f"✅ ファイルアップロード完了: {path} (ID: {uploaded.id})")
        else:
            print(f"⚠️ ファイルが見つかりません: {path}")
    
    # Assistantを作成（ファイル検索機能付き）
    assistant = client.beta.assistants.create(
        name="RAG Assistant",
        instructions="""
        あなたはドキュメント検索アシスタントです。
        ユーザーの質問に対して、アップロードされたファイルから関連情報を検索し、
        正確で役立つ回答を提供してください。
        
        回答時は以下の点に注意してください：
        - ファイルの内容に基づいた正確な情報を提供する
        - 不明な点は「ファイルに記載されていない」と明記する
        - 情報の出典となるファイル名も併せて示す
        """,
        model="gpt-4o",
        tools=[{"type": "file_search"}]
    )
    
    print(f"✅ Assistant作成完了: {assistant.id}")
    return assistant.id, file_ids


# ========================================
# 2. シンプルなRAGクエリ実行
# ========================================

def simple_rag_query(assistant_id: str, query: str) -> str:
    """最もシンプルなRAGクエリの実行"""
    
    client = OpenAI()
    
    # 新しいスレッドを作成
    thread = client.beta.threads.create()
    
    # メッセージを追加
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )
    
    # Assistantを実行
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    
    # 実行完了を待つ
    while run.status in ['queued', 'in_progress', 'cancelling']:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run.status == 'completed':
            break
    
    # 結果を取得
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    
    # 最新のアシスタントメッセージを取得
    for message in messages.data:
        if message.role == "assistant":
            return message.content[0].text.value
    
    return "回答を取得できませんでした。"


# ========================================
# 3. メイン実行
# ========================================

def main():
    """RAGシステムの実行例"""
    
    # 1. ファイルアップロードとAssistant作成
    print("🚀 RAGシステムを初期化中...")
    assistant_id, file_ids = upload_files_and_create_assistant([
        "documents/VectorembeddingsOpenAI.pdf",
        "documents/VectorembeddingsOpenAI.txt"
    ])
    
    print(f"✅ アップロードされたファイル数: {len(file_ids)}")
    
    # 2. 質問応答の実行
    questions = [
        "APIの認証方法について教えてください",
        "エラーハンドリングのベストプラクティスは？",
        "パフォーマンス最適化の方法を教えてください"
    ]
    
    for question in questions:
        print(f"\n📝 質問: {question}")
        
        # RAGクエリを実行
        answer = simple_rag_query(assistant_id, question)
        
        print(f"🤖 回答: {answer}")


# ========================================
# 実行
# ========================================

if __name__ == "__main__":
    # OpenAI APIキーを環境変数から取得
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ エラー: OPENAI_API_KEY環境変数が設定されていません")
        print("以下のコマンドでAPIキーを設定してください:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        exit(1)
    
    # 実行
    main()