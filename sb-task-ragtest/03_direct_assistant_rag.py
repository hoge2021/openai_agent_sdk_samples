import asyncio
import os
from openai import OpenAI
import time

# ========================================
# 1. ファイルアップロードとAssistant作成
# ========================================

def upload_files_and_create_assistant(file_paths: list[str]) -> tuple[str, list[str]]:
    """ファイルをアップロードしてAssistantを作成（直接Assistant API使用）"""
    
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
# 2. 直接Assistant APIを使用したRAG実行
# ========================================

def run_rag_query(assistant_id: str, file_ids: list[str], query: str) -> str:
    """Assistant APIを直接使用してRAGクエリを実行"""
    
    client = OpenAI()
    
    # スレッドを作成
    thread = client.beta.threads.create()
    
    # メッセージを作成（ファイルを添付）
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query,
        attachments=[
            {"file_id": file_id, "tools": [{"type": "file_search"}]}
            for file_id in file_ids
        ]
    )
    
    # Assistantを実行
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    
    # 実行完了まで待機
    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
    
    if run.status == 'completed':
        # メッセージを取得
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[0].content[0].text.value
    else:
        return f"エラーが発生しました: {run.status} - {run.last_error}"


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
        
        try:
            # RAGクエリを実行
            answer = run_rag_query(assistant_id, file_ids, question)
            print(f"🤖 回答: {answer}")
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")


# ========================================
# 実行
# ========================================

if __name__ == "__main__":
    # OpenAI APIキーを環境変数から取得または設定
    if not os.getenv("OPENAI_API_KEY"):
        print("🔑 APIキーを設定中...")
        os.environ["OPENAI_API_KEY"] = "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"
        print("✅ APIキー設定完了")
    
    # 実行
    main()
