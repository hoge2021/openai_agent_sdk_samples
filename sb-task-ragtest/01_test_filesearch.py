import asyncio
import os
from typing import Any, List
from dataclasses import dataclass
from openai import OpenAI
from agents import Agent, Runner, RunContextWrapper, FileSearchTool, function_tool
from agents.models import OpenAIResponsesModel

# ========================================
# 1. ベクトルストアの設定とファイルアップロード
# ========================================

def setup_vector_store(api_key: str) -> str:
    """
    ベクトルストアを作成し、ドキュメントをアップロードする
    
    Returns:
        str: 作成されたベクトルストアのID
    """
    client = OpenAI(api_key=api_key)
    
    # ベクトルストアの作成
    vector_store = client.beta.vector_stores.create(
        name="技術ドキュメントストア",
        description="技術文書やマニュアルを保存するベクトルストア"
    )
    
    # ファイルをアップロード（実際の使用時は適切なファイルパスに変更）
    file_paths = [
        "documents/technical_manual.pdf",
        "documents/api_reference.md",
        "documents/user_guide.txt"
    ]
    
    file_ids = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                uploaded_file = client.files.create(
                    file=file,
                    purpose="assistants"
                )
                file_ids.append(uploaded_file.id)
    
    # ファイルをベクトルストアに追加
    if file_ids:
        client.beta.vector_stores.files.create_batch(
            vector_store_id=vector_store.id,
            file_ids=file_ids
        )
    
    # ベクトルストアの処理が完了するまで待機
    import time
    while True:
        vector_store_status = client.beta.vector_stores.retrieve(vector_store.id)
        if vector_store_status.status == "completed":
            break
        time.sleep(1)
    
    return vector_store.id


# ========================================
# 2. コンテキスト管理用のデータクラス
# ========================================

@dataclass
class RAGContext:
    """RAGシステムのコンテキスト情報を保持"""
    user_id: str
    session_id: str
    vector_store_ids: List[str]
    search_history: List[dict] = None
    
    def __post_init__(self):
        if self.search_history is None:
            self.search_history = []


# ========================================
# 3. カスタムツール関数の定義
# ========================================

@function_tool
async def analyze_search_results(
    ctx: RunContextWrapper[RAGContext],
    query: str,
    results: str
) -> str:
    """
    検索結果を分析し、構造化された回答を生成する
    
    Args:
        ctx: 実行コンテキスト
        query: ユーザーのクエリ
        results: 検索結果
    
    Returns:
        str: 構造化された分析結果
    """
    # 検索履歴に追加
    ctx.context.search_history.append({
        "query": query,
        "results": results,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    })
    
    # 結果を分析（実際の実装では、より高度な分析を行う）
    analysis = f"""
    ## 検索クエリ: {query}
    
    ### 検索結果の分析:
    - 関連文書が見つかりました
    - セッションID: {ctx.context.session_id}
    - ユーザーID: {ctx.context.user_id}
    
    ### 詳細情報:
    {results}
    """
    
    return analysis


@function_tool
async def get_additional_context(
    ctx: RunContextWrapper[RAGContext],
    topic: str
) -> str:
    """
    特定のトピックに関する追加コンテキストを取得
    
    Args:
        ctx: 実行コンテキスト
        topic: 検索するトピック
    
    Returns:
        str: 追加コンテキスト情報
    """
    # 実際の実装では外部APIや別のデータソースから情報を取得
    additional_info = f"""
    トピック「{topic}」に関する追加情報:
    - 最終更新: 2024年12月
    - 関連トピック: API設計、システムアーキテクチャ
    - 参照ドキュメント数: {len(ctx.context.vector_store_ids)}
    """
    
    return additional_info


# ========================================
# 4. RAG Agentの実装
# ========================================

def create_rag_agent(
    vector_store_ids: List[str],
    context: RAGContext
) -> Agent[RAGContext]:
    """
    FileSearchToolを使用したRAG Agentを作成
    
    Args:
        vector_store_ids: 検索対象のベクトルストアID
        context: RAGコンテキスト
    
    Returns:
        Agent: 設定済みのRAG Agent
    """
    
    # 動的な指示を生成する関数
    def dynamic_instructions(ctx: RunContextWrapper[RAGContext]) -> str:
        return f"""
        あなたは高度なRAGシステムアシスタントです。
        
        ## あなたの役割:
        1. ユーザーの質問を理解し、関連情報をベクトルストアから検索する
        2. 検索結果を分析し、正確で有用な回答を提供する
        3. 必要に応じて追加のコンテキストを取得する
        
        ## 現在のセッション情報:
        - ユーザーID: {ctx.context.user_id}
        - セッションID: {ctx.context.session_id}
        - 検索履歴数: {len(ctx.context.search_history)}
        
        ## 回答方針:
        - 検索結果に基づいて正確に回答する
        - 情報が不足している場合は、その旨を明確に伝える
        - 技術的な内容は分かりやすく説明する
        """
    
    # FileSearchToolの設定
    file_search_tool = FileSearchTool(
        vector_store_ids=vector_store_ids,
        max_num_results=5,  # 最大5件の結果を取得
        include_search_results=True,  # LLMの出力に検索結果を含める
        ranking_options={
            "ranker": "default_2024_08_21",  # ランキングアルゴリズム
            "score_threshold": 0.0  # スコアしきい値
        }
    )
    
    # Agentの作成
    agent = Agent[RAGContext](
        name="RAG Assistant",
        instructions=dynamic_instructions,
        tools=[
            file_search_tool,
            analyze_search_results,
            get_additional_context
        ],
        model=OpenAIResponsesModel(model="gpt-4o-mini")
    )
    
    return agent


# ========================================
# 5. 高度なRAGパイプライン
# ========================================

class AdvancedRAGPipeline:
    """高度なRAG処理パイプライン"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.vector_store_ids = []
    
    async def initialize(self, documents: List[str] = None):
        """
        パイプラインの初期化
        
        Args:
            documents: アップロードするドキュメントのリスト
        """
        if documents:
            # ドキュメントをベクトルストアにアップロード
            vector_store_id = setup_vector_store(self.api_key)
            self.vector_store_ids.append(vector_store_id)
    
    async def search_and_respond(
        self,
        query: str,
        user_id: str = "default_user",
        session_id: str = None
    ) -> str:
        """
        クエリを処理し、RAGを使用して応答を生成
        
        Args:
            query: ユーザーのクエリ
            user_id: ユーザーID
            session_id: セッションID
        
        Returns:
            str: 生成された応答
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        # コンテキストの作成
        context = RAGContext(
            user_id=user_id,
            session_id=session_id,
            vector_store_ids=self.vector_store_ids
        )
        
        # Agentの作成
        agent = create_rag_agent(self.vector_store_ids, context)
        
        # クエリの実行
        result = await Runner.run(
            starting_agent=agent,
            input=query,
            context=context
        )
        
        return result.final_output
    
    async def multi_turn_conversation(
        self,
        queries: List[str],
        user_id: str = "default_user"
    ):
        """
        マルチターンの会話を処理
        
        Args:
            queries: クエリのリスト
            user_id: ユーザーID
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        context = RAGContext(
            user_id=user_id,
            session_id=session_id,
            vector_store_ids=self.vector_store_ids
        )
        
        agent = create_rag_agent(self.vector_store_ids, context)
        
        conversation_history = []
        
        for query in queries:
            print(f"\n👤 User: {query}")
            
            # 前回の会話履歴を含めてクエリを構築
            if conversation_history:
                full_query = f"以前の会話を考慮して回答してください:\n{query}"
            else:
                full_query = query
            
            result = await Runner.run(
                starting_agent=agent,
                input=full_query,
                context=context
            )
            
            response = result.final_output
            print(f"🤖 Assistant: {response}")
            
            conversation_history.append({
                "query": query,
                "response": response
            })
        
        return conversation_history


# ========================================
# 6. メイン実行部分
# ========================================

async def main():
    """メイン実行関数"""
    
    # API キーの設定（環境変数から取得）
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY環境変数が設定されていません")
        return
    
    # RAGパイプラインの初期化
    pipeline = AdvancedRAGPipeline(api_key)
    
    # ベクトルストアの初期化（実際のファイルがある場合）
    # await pipeline.initialize(documents=["path/to/doc1.pdf", "path/to/doc2.md"])
    
    # 単一クエリの実行例
    print("=" * 50)
    print("📚 RAGシステムデモ - 単一クエリ")
    print("=" * 50)
    
    single_query = "APIのレート制限について教えてください"
    response = await pipeline.search_and_respond(single_query)
    print(f"\n質問: {single_query}")
    print(f"回答: {response}")
    
    # マルチターン会話の例
    print("\n" + "=" * 50)
    print("💬 RAGシステムデモ - マルチターン会話")
    print("=" * 50)
    
    queries = [
        "システムアーキテクチャの概要を教えてください",
        "そのアーキテクチャでのセキュリティ対策は？",
        "パフォーマンスの最適化方法についても教えてください"
    ]
    
    await pipeline.multi_turn_conversation(queries)
    
    print("\n✅ デモ完了")


# ========================================
# 7. エラーハンドリング付き実行
# ========================================

async def run_with_error_handling():
    """エラーハンドリングを含む実行"""
    try:
        await main()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # イベントループの実行
    asyncio.run(run_with_error_handling())