# 🚀 OpenAI Agents SDK × PostgreSQL pgvector RAGシステム構築 完全ハンズオンガイド

## 📋 はじめに

このガイドでは、Mac環境でOpenAI Agents SDKとPostgreSQL pgvectorを使用したRAGシステムを、ゼロから段階的に構築していきます。各ステップで動作確認を行いながら、確実に理解を深めていきましょう。

### このガイドの特徴
- ✅ 初心者でも理解できる詳細な説明
- ✅ 各ステップでの動作確認
- ✅ エラー対処法の記載
- ✅ 段階的な実装による着実な学習

---

## 🛠 Step 0: 開発環境の準備

### 0.1 必要なツールの確認とインストール

#### Homebrewのインストール（既にある場合はスキップ）
```bash
# Homebrewがインストールされているか確認
brew --version

# インストールされていない場合
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### uvのインストール
```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# パスを通す（.zshrcまたは.bash_profileに追加）
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# インストール確認
uv --version
# 出力例: uv 0.4.18
```

#### Podman Desktopのインストール
```bash
# Podmanのインストール
brew install podman

# Podman Desktopのインストール
brew install --cask podman-desktop

# Podmanマシンの初期化
podman machine init
podman machine start

# 動作確認
podman --version
# 出力例: podman version 4.9.3
```

### 0.2 プロジェクトディレクトリの作成

```bash
# プロジェクトディレクトリを作成
mkdir ~/rag-agents-project
cd ~/rag-agents-project

# プロジェクト構造を作成
mkdir -p src/{models,services,tools,utils}
mkdir -p tests
mkdir -p data
mkdir -p config

# 基本的な設定ファイルを作成
touch .env
touch .gitignore
touch README.md
```

### 0.3 .gitignoreの設定

```bash
cat << 'EOF' > .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# uv
.python-version

# 環境変数
.env
.env.*

# データ
data/*.txt
data/*.pdf
data/*.json

# ログ
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
```

---

## 🐳 Step 1: PostgreSQL + pgvectorのセットアップ

### 1.1 PostgreSQL + pgvectorコンテナの作成

#### Containerfileの作成
```bash
# Containerfileを作成（DockerfileのPodman版）
cat << 'EOF' > Containerfile
FROM docker.io/postgres:16.4

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-16 \
    git \
    make \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# pgvectorのインストール
RUN cd /tmp && \
    git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/pgvector

# 後処理
RUN apt-get remove -y git make gcc g++ && \
    apt-get autoremove -y && \
    apt-get clean
EOF

echo "✅ Containerfileを作成しました"
```

### 1.2 コンテナイメージのビルドと起動

```bash
# イメージをビルド
podman build -t postgres-pgvector -f Containerfile .

# ビルド成功の確認
podman images | grep postgres-pgvector

# PostgreSQLコンテナを起動
podman run -d \
  --name ragdb \
  -e POSTGRES_PASSWORD=ragpassword \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_DB=ragdatabase \
  -p 5432:5432 \
  -v ragdb_data:/var/lib/postgresql/data \
  postgres-pgvector

# コンテナの起動確認
podman ps
# CONTAINER ID  IMAGE                COMMAND     CREATED         STATUS         PORTS                   NAMES
# xxxxx         postgres-pgvector    postgres    10 seconds ago  Up 10 seconds  0.0.0.0:5432->5432/tcp  ragdb

echo "✅ PostgreSQLコンテナが起動しました"
```

### 1.3 データベースの初期設定

```bash
# PostgreSQLクライアントツールのインストール
brew install postgresql@16

# データベースに接続してpgvector拡張を有効化
PGPASSWORD=ragpassword psql -h localhost -U raguser -d ragdatabase << 'EOF'
-- pgvector拡張の確認と有効化
CREATE EXTENSION IF NOT EXISTS vector;

-- 拡張が有効になったか確認
SELECT * FROM pg_extension WHERE extname = 'vector';

-- テスト用のテーブルを作成
CREATE TABLE IF NOT EXISTS test_vectors (
    id SERIAL PRIMARY KEY,
    embedding vector(3)
);

-- テストデータの挿入
INSERT INTO test_vectors (embedding) VALUES
    ('[1,2,3]'),
    ('[4,5,6]');

-- 動作確認（類似度検索のテスト）
SELECT id, embedding, embedding <-> '[1,2,3]' as distance
FROM test_vectors
ORDER BY embedding <-> '[1,2,3]'
LIMIT 5;
EOF

echo "✅ pgvectorの設定が完了しました"
```

### 1.4 動作確認スクリプト

```bash
# 動作確認用のPythonスクリプトを作成
cat << 'EOF' > test_db_connection.py
#!/usr/bin/env python3
import psycopg2

try:
    # データベースに接続
    conn = psycopg2.connect(
        host="localhost",
        database="ragdatabase",
        user="raguser",
        password="ragpassword",
        port="5432"
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"✅ PostgreSQL接続成功！")
    print(f"   バージョン: {db_version[0]}")
    
    # pgvectorの確認
    cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    vector_version = cursor.fetchone()
    print(f"✅ pgvector有効！")
    print(f"   バージョン: {vector_version[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ エラー: {e}")
EOF

# スクリプトを実行
python3 test_db_connection.py
```

---

## 🐍 Step 2: Python環境のセットアップ

### 2.1 uvでプロジェクトを初期化

```bash
# プロジェクトを初期化
uv init --python 3.11

# Pythonバージョンの確認
uv python list
uv python pin 3.11

# pyproject.tomlの確認
cat pyproject.toml
```

### 2.2 必要なパッケージのインストール

```bash
# 基本的なパッケージをインストール
uv add openai
uv add asyncpg
uv add pgvector
uv add sqlalchemy
uv add python-dotenv
uv add numpy
uv add tiktoken

# 開発用パッケージ
uv add --dev pytest
uv add --dev pytest-asyncio
uv add --dev ipython

echo "✅ パッケージのインストールが完了しました"
```

### 2.3 環境変数の設定

```bash
# .envファイルを作成
cat << 'EOF' > .env
# Database Configuration
DATABASE_URL=postgresql://raguser:ragpassword@localhost:5432/ragdatabase
ASYNC_DATABASE_URL=postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragdatabase

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
CHUNK_SIZE=512
CHUNK_OVERLAP=50
EOF

echo "⚠️  .envファイルのOPENAI_API_KEYを実際のキーに置き換えてください"
```

### 2.4 設定ローダーの作成

```bash
# 設定ローダーを作成
cat << 'EOF' > src/utils/config.py
"""設定管理モジュール"""
import os
from dotenv import load_dotenv
from typing import Optional

# .envファイルを読み込み
load_dotenv()

class Config:
    """アプリケーション設定"""
    
    # データベース設定
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    ASYNC_DATABASE_URL: str = os.getenv('ASYNC_DATABASE_URL', '')
    
    # OpenAI設定
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    EMBEDDING_DIMENSION: int = int(os.getenv('EMBEDDING_DIMENSION', '1536'))
    
    # チャンキング設定
    CHUNK_SIZE: int = int(os.getenv('CHUNK_SIZE', '512'))
    CHUNK_OVERLAP: int = int(os.getenv('CHUNK_OVERLAP', '50'))
    
    @classmethod
    def validate(cls) -> bool:
        """設定の検証"""
        if not cls.DATABASE_URL:
            print("❌ DATABASE_URLが設定されていません")
            return False
        
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == 'your_openai_api_key_here':
            print("❌ OPENAI_API_KEYが設定されていません")
            return False
        
        print("✅ 設定の検証が完了しました")
        return True

if __name__ == "__main__":
    # 設定の確認
    Config.validate()
    print(f"DATABASE_URL: {Config.DATABASE_URL[:30]}...")
    print(f"EMBEDDING_MODEL: {Config.EMBEDDING_MODEL}")
    print(f"CHUNK_SIZE: {Config.CHUNK_SIZE}")
EOF

# 動作確認
uv run python src/utils/config.py
```

---

## 📊 Step 3: データベースモデルの実装

### 3.1 SQLAlchemyモデルの作成

```bash
# データベースモデルを作成
cat << 'EOF' > src/models/database.py
"""データベースモデルの定義"""
from datetime import datetime
from typing import Optional, Dict, Any
import json

from sqlalchemy import (
    create_engine, Column, Integer, Text, 
    DateTime, JSON, Float, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)

from src.utils.config import Config

# ベースクラス
Base = declarative_base()

class Document(Base):
    """ドキュメントモデル"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(Config.EMBEDDING_DIMENSION))
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # インデックスの定義
    __table_args__ = (
        Index(
            'idx_embedding_hnsw',
            'embedding',
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 非同期エンジンの作成
async_engine = create_async_engine(
    Config.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # SQLログを表示する場合はTrue
)

# 非同期セッションファクトリ
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 同期エンジン（テーブル作成用）
sync_engine = create_engine(
    Config.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

async def init_database():
    """データベースの初期化"""
    # テーブルの作成（同期的に実行）
    Base.metadata.create_all(bind=sync_engine)
    print("✅ データベーステーブルを作成しました")

async def get_session() -> AsyncSession:
    """非同期セッションの取得"""
    async with AsyncSessionLocal() as session:
        yield session

if __name__ == "__main__":
    # テーブル作成のテスト
    import asyncio
    asyncio.run(init_database())
EOF

# データベースの初期化
uv run python -c "import asyncio; from src.models.database import init_database; asyncio.run(init_database())"
```

### 3.2 データベース接続のテスト

```bash
# 接続テストスクリプトを作成
cat << 'EOF' > test_database.py
"""データベース接続のテスト"""
import asyncio
from src.models.database import AsyncSessionLocal, Document
from sqlalchemy import select, text

async def test_connection():
    """接続テスト"""
    try:
        async with AsyncSessionLocal() as session:
            # pgvectorの動作確認
            result = await session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            version = result.scalar()
            print(f"✅ pgvectorバージョン: {version}")
            
            # ドキュメントテーブルの確認
            result = await session.execute(
                text("SELECT COUNT(*) FROM documents")
            )
            count = result.scalar()
            print(f"✅ documentsテーブルのレコード数: {count}")
            
            # テストドキュメントの挿入
            test_doc = Document(
                content="これはテストドキュメントです",
                metadata={"test": True}
            )
            session.add(test_doc)
            await session.commit()
            print("✅ テストドキュメントを挿入しました")
            
            # 検索テスト
            stmt = select(Document).limit(1)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc:
                print(f"✅ ドキュメント取得成功: {doc.content[:30]}...")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection())
EOF

# テスト実行
uv run python test_database.py
```

---

## 🧮 Step 4: エンベディングサービスの実装

### 4.1 エンベディングサービスの作成

```bash
# エンベディングサービスを作成
cat << 'EOF' > src/services/embedding_service.py
"""エンベディング生成サービス"""
import asyncio
from typing import List, Optional
import numpy as np
from openai import AsyncOpenAI
import tiktoken

from src.utils.config import Config

class EmbeddingService:
    """OpenAIエンベディング生成サービス"""
    
    def __init__(self):
        """初期化"""
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.EMBEDDING_MODEL
        self.dimension = Config.EMBEDDING_DIMENSION
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        print(f"✅ EmbeddingService初期化完了 (モデル: {self.model})")
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """単一テキストのエンベディング生成"""
        if not text:
            raise ValueError("テキストが空です")
        
        # テキストの前処理
        text = text.replace("\n", " ").strip()
        
        # トークン数の確認
        token_count = len(self.encoding.encode(text))
        if token_count > 8192:  # OpenAIの制限
            print(f"⚠️ テキストが長すぎます ({token_count} tokens)。切り詰めます。")
            tokens = self.encoding.encode(text)[:8192]
            text = self.encoding.decode(tokens)
        
        try:
            # OpenAI APIを呼び出し
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            print(f"❌ エンベディング生成エラー: {e}")
            raise
    
    async def generate_batch_embeddings(
        self, 
        texts: List[str],
        batch_size: int = 10
    ) -> List[np.ndarray]:
        """バッチでエンベディング生成"""
        embeddings = []
        
        # テキストの前処理
        processed_texts = [
            text.replace("\n", " ").strip() 
            for text in texts if text
        ]
        
        # バッチ処理
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i:i + batch_size]
            
            try:
                response = await self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                
                batch_embeddings = [
                    np.array(data.embedding, dtype=np.float32) 
                    for data in response.data
                ]
                embeddings.extend(batch_embeddings)
                
                print(f"✅ バッチ {i//batch_size + 1} 完了 ({len(batch)} texts)")
                
            except Exception as e:
                print(f"❌ バッチエンベディングエラー: {e}")
                raise
        
        return embeddings
    
    def estimate_cost(self, text_count: int, avg_tokens: int = 100) -> float:
        """コスト見積もり（参考値）"""
        # text-embedding-3-small: $0.020 / 1M tokens
        total_tokens = text_count * avg_tokens
        cost = (total_tokens / 1_000_000) * 0.020
        return cost

# テスト関数
async def test_embedding_service():
    """エンベディングサービスのテスト"""
    service = EmbeddingService()
    
    # 単一テキストのテスト
    test_text = "これはテスト用のテキストです。RAGシステムの実装を学んでいます。"
    embedding = await service.generate_embedding(test_text)
    print(f"✅ エンベディング生成成功")
    print(f"   次元数: {len(embedding)}")
    print(f"   最初の5要素: {embedding[:5]}")
    
    # バッチ処理のテスト
    test_texts = [
        "OpenAI Agents SDKは強力です",
        "PostgreSQLとpgvectorの組み合わせ",
        "RAGシステムの構築方法"
    ]
    embeddings = await service.generate_batch_embeddings(test_texts)
    print(f"✅ バッチエンベディング生成成功")
    print(f"   生成数: {len(embeddings)}")
    
    # コスト見積もり
    cost = service.estimate_cost(100, 50)
    print(f"💰 100テキスト（平均50トークン）のコスト見積: ${cost:.4f}")

if __name__ == "__main__":
    asyncio.run(test_embedding_service())
EOF

# テスト実行（OpenAI APIキーが必要）
uv run python src/services/embedding_service.py
```

### 4.2 テキストチャンカーの実装

```bash
# テキストチャンカーを作成
cat << 'EOF' > src/services/text_chunker.py
"""テキスト分割サービス"""
from typing import List, Dict, Any
import tiktoken
import re

from src.utils.config import Config

class TextChunker:
    """テキストをチャンクに分割"""
    
    def __init__(
        self,
        chunk_size: int = None,
        overlap: int = None
    ):
        """初期化"""
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.overlap = overlap or Config.CHUNK_OVERLAP
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """テキストをトークンベースで分割"""
        if not text:
            return []
        
        # トークン化
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < total_tokens:
            # チャンクの終了位置を計算
            end = min(start + self.chunk_size, total_tokens)
            
            # オーバーラップを考慮した開始位置
            if start > 0:
                actual_start = max(0, start - self.overlap)
            else:
                actual_start = start
            
            # チャンクのトークンを取得
            chunk_tokens = tokens[actual_start:end]
            
            # トークンをテキストに戻す
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append({
                'content': chunk_text,
                'metadata': {
                    'chunk_index': chunk_index,
                    'start_token': actual_start,
                    'end_token': end,
                    'token_count': len(chunk_tokens),
                    'total_chunks': None  # 後で更新
                }
            })
            
            chunk_index += 1
            
            # 次のチャンクの開始位置（オーバーラップを考慮）
            if end < total_tokens:
                start = end - self.overlap
            else:
                start = end
        
        # total_chunksを更新
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = len(chunks)
        
        return chunks
    
    def split_by_sentences(
        self, 
        text: str,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100
    ) -> List[Dict[str, Any]]:
        """文章単位での分割（セマンティックな境界を保持）"""
        # 文章の境界で分割
        sentence_pattern = r'(?<=[。！？\.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # 現在のチャンクに追加すると上限を超える場合
            if current_size + sentence_tokens > max_chunk_size and current_chunk:
                # チャンクを保存
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'chunk_index': chunk_index,
                        'token_count': current_size,
                        'sentence_count': len(current_chunk),
                        'type': 'sentence_based'
                    }
                })
                
                chunk_index += 1
                current_chunk = [sentence]
                current_size = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_size += sentence_tokens
        
        # 最後のチャンク
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if current_size >= min_chunk_size:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'chunk_index': chunk_index,
                        'token_count': current_size,
                        'sentence_count': len(current_chunk),
                        'type': 'sentence_based'
                    }
                })
            elif chunks:
                # 小さすぎる場合は前のチャンクに結合
                chunks[-1]['content'] += ' ' + chunk_text
                chunks[-1]['metadata']['token_count'] += current_size
                chunks[-1]['metadata']['sentence_count'] += len(current_chunk)
        
        return chunks

def test_chunker():
    """チャンカーのテスト"""
    chunker = TextChunker(chunk_size=100, overlap=20)
    
    # テストテキスト
    test_text = """
    OpenAI Agents SDKは、エージェントベースのAIアプリケーション構築のための
    革新的なフレームワークです。このSDKは、複数のエージェントが協調して
    複雑なタスクを実行できる環境を提供します。
    
    各エージェントは独自の役割と能力を持ち、必要に応じて他のエージェントに
    タスクを委譲することができます。これにより、高度に特化した
    エージェントのネットワークを構築することが可能になります。
    
    また、pgvectorを使用したベクトルデータベースとの統合により、
    効率的な類似度検索が可能になり、RAGシステムの構築が容易になります。
    """
    
    # トークンベースの分割
    chunks = chunker.split_text(test_text)
    print(f"✅ トークンベース分割: {len(chunks)} チャンク")
    for i, chunk in enumerate(chunks):
        print(f"\nチャンク {i + 1}:")
        print(f"  内容: {chunk['content'][:50]}...")
        print(f"  メタデータ: {chunk['metadata']}")
    
    # 文章ベースの分割
    chunks_sentence = chunker.split_by_sentences(test_text, max_chunk_size=150)
    print(f"\n✅ 文章ベース分割: {len(chunks_sentence)} チャンク")
    for i, chunk in enumerate(chunks_sentence):
        print(f"\nチャンク {i + 1}:")
        print(f"  内容: {chunk['content'][:50]}...")
        print(f"  メタデータ: {chunk['metadata']}")

if __name__ == "__main__":
    test_chunker()
EOF

# テスト実行
uv run python src/services/text_chunker.py
```

---

## 🗄️ Step 5: ベクトルストアの実装

### 5.1 ベクトルストアの作成

```bash
# ベクトルストアを作成
cat << 'EOF' > src/services/vector_store.py
"""ベクトルストアの実装"""
import asyncio
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import numpy as np
import asyncpg
from pgvector.asyncpg import register_vector

from src.models.database import AsyncSessionLocal, Document
from src.services.embedding_service import EmbeddingService
from src.services.text_chunker import TextChunker
from src.utils.config import Config
from sqlalchemy import select, text

class VectorStore:
    """pgvectorを使用したベクトルストア"""
    
    def __init__(self):
        """初期化"""
        self.pool = None
        self.embedding_service = EmbeddingService()
        self.chunker = TextChunker()
        
    async def initialize(self):
        """コネクションプールの初期化"""
        self.pool = await asyncpg.create_pool(
            Config.DATABASE_URL,
            min_size=5,
            max_size=20,
            init=self._init_connection
        )
        print("✅ VectorStoreのコネクションプールを初期化しました")
    
    async def _init_connection(self, conn):
        """pgvector拡張の登録"""
        await register_vector(conn)
    
    async def close(self):
        """コネクションプールを閉じる"""
        if self.pool:
            await self.pool.close()
            print("✅ コネクションプールを閉じました")
    
    async def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """ドキュメントを追加"""
        if not content:
            raise ValueError("コンテンツが空です")
        
        # テキストをチャンクに分割
        chunks = self.chunker.split_text(content)
        print(f"📄 {len(chunks)} チャンクに分割しました")
        
        # チャンクごとにエンベディングを生成
        chunk_texts = [chunk['content'] for chunk in chunks]
        embeddings = await self.embedding_service.generate_batch_embeddings(
            chunk_texts
        )
        
        # データベースに保存
        document_ids = []
        async with AsyncSessionLocal() as session:
            for chunk, embedding in zip(chunks, embeddings):
                # メタデータの結合
                chunk_metadata = chunk['metadata']
                if metadata:
                    chunk_metadata.update(metadata)
                
                # ドキュメントオブジェクトの作成
                doc = Document(
                    content=chunk['content'],
                    embedding=embedding.tolist(),
                    metadata=chunk_metadata
                )
                session.add(doc)
                await session.flush()
                document_ids.append(doc.id)
            
            await session.commit()
            print(f"✅ {len(document_ids)} チャンクをデータベースに保存しました")
        
        return document_ids
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """類似度検索"""
        # クエリのエンベディング生成
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        async with self.pool.acquire() as conn:
            # コサイン類似度による検索
            results = await conn.fetch(
                """
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) as similarity
                FROM documents
                WHERE 1 - (embedding <=> $1::vector) > $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                query_embedding.tolist(),
                threshold,
                k
            )
            
            # 結果を辞書形式に変換
            search_results = []
            for row in results:
                search_results.append({
                    'id': row['id'],
                    'content': row['content'],
                    'metadata': row['metadata'],
                    'similarity': float(row['similarity'])
                })
            
            print(f"🔍 {len(search_results)} 件の結果を取得しました")
            return search_results
    
    async def hybrid_search(
        self,
        query: str,
        keyword: Optional[str] = None,
        k: int = 5,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """ハイブリッド検索（ベクトル + キーワード）"""
        # ベクトル検索の準備
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # キーワードが指定されていない場合はクエリを使用
        search_keyword = keyword or query
        
        async with self.pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) as vector_similarity,
                    ts_rank(
                        to_tsvector('english', content),
                        plainto_tsquery('english', $2)
                    ) as keyword_score
                FROM documents
                WHERE 
                    to_tsvector('english', content) @@ plainto_tsquery('english', $2)
                    OR 1 - (embedding <=> $1::vector) > 0.5
                ORDER BY 
                    (1 - (embedding <=> $1::vector)) * $3 + 
                    ts_rank(
                        to_tsvector('english', content),
                        plainto_tsquery('english', $2)
                    ) * (1 - $3) DESC
                LIMIT $4
                """,
                query_embedding.tolist(),
                search_keyword,
                vector_weight,
                k
            )
            
            return [dict(row) for row in results]
    
    async def delete_document(self, document_id: int) -> bool:
        """ドキュメントの削除"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if doc:
                await session.delete(doc)
                await session.commit()
                print(f"✅ ドキュメント {document_id} を削除しました")
                return True
            
            print(f"⚠️ ドキュメント {document_id} が見つかりません")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """統計情報の取得"""
        async with self.pool.acquire() as conn:
            # 総ドキュメント数
            count_result = await conn.fetchval(
                "SELECT COUNT(*) FROM documents"
            )
            
            # インデックスサイズ
            index_result = await conn.fetchval(
                """
                SELECT pg_size_pretty(
                    pg_relation_size('idx_embedding_hnsw')
                )
                """
            )
            
            # 平均ベクトル
            avg_result = await conn.fetchval(
                "SELECT COUNT(DISTINCT metadata->>'chunk_index') FROM documents"
            )
            
            return {
                'total_documents': count_result,
                'index_size': index_result,
                'unique_chunks': avg_result
            }

# テスト関数
async def test_vector_store():
    """ベクトルストアのテスト"""
    store = VectorStore()
    
    try:
        # 初期化
        await store.initialize()
        
        # ドキュメントの追加
        test_content = """
        RAG（Retrieval-Augmented Generation）は、大規模言語モデルの能力を
        外部知識ベースで拡張する技術です。これにより、より正確で最新の
        情報に基づいた回答を生成することができます。
        
        pgvectorは、PostgreSQLでベクトル類似度検索を可能にする拡張機能で、
        高次元ベクトルデータの効率的な保存と検索を実現します。
        """
        
        doc_ids = await store.add_document(
            test_content,
            metadata={'source': 'test', 'type': 'tutorial'}
        )
        print(f"✅ ドキュメントID: {doc_ids}")
        
        # 類似度検索
        search_results = await store.similarity_search(
            "RAGとは何ですか？",
            k=3
        )
        
        print("\n🔍 検索結果:")
        for i, result in enumerate(search_results):
            print(f"\n結果 {i + 1}:")
            print(f"  類似度: {result['similarity']:.4f}")
            print(f"  内容: {result['content'][:100]}...")
        
        # 統計情報
        stats = await store.get_statistics()
        print(f"\n📊 統計情報: {stats}")
        
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(test_vector_store())
EOF

# テスト実行
uv run python src/services/vector_store.py
```

---

## 🤖 Step 6: OpenAI Agents SDKの統合

### 6.1 OpenAI Agents SDKのインストールと確認

```bash
# OpenAI Agents SDKをインストール（既にインストール済みの場合はスキップ）
uv add openai-agents

# バージョン確認
uv run python -c "import agents; print(f'OpenAI Agents SDK version: {agents.__version__ if hasattr(agents, '__version__') else 'unknown'}')"
```

### 6.2 RAGツールの実装

```bash
# RAGツールを作成
cat << 'EOF' > src/tools/rag_tools.py
"""RAG用のツール実装"""
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from agents import function_tool, RunContextWrapper

from src.services.vector_store import VectorStore
from src.services.embedding_service import EmbeddingService
from src.services.text_chunker import TextChunker

@dataclass
class RAGContext:
    """RAGシステムのコンテキスト"""
    vector_store: VectorStore
    max_results: int = 5
    similarity_threshold: float = 0.7

@function_tool
async def search_knowledge_base(
    ctx: RunContextWrapper[RAGContext],
    query: str,
    num_results: Optional[int] = None
) -> str:
    """
    知識ベースから関連情報を検索します。
    
    Args:
        query: 検索クエリ
        num_results: 取得する結果数（デフォルト: 5）
    
    Returns:
        検索結果の整形されたテキスト
    """
    try:
        # パラメータの設定
        k = num_results or ctx.context.max_results
        
        # ベクトル検索の実行
        results = await ctx.context.vector_store.similarity_search(
            query=query,
            k=k,
            threshold=ctx.context.similarity_threshold
        )
        
        if not results:
            return "申し訳ございません。関連する情報が見つかりませんでした。"
        
        # 結果の整形
        response_parts = []
        response_parts.append(f"🔍 「{query}」に関する検索結果:\n")
        
        for idx, result in enumerate(results, 1):
            similarity_percent = result['similarity'] * 100
            response_parts.append(
                f"\n【結果 {idx}】(関連度: {similarity_percent:.1f}%)\n"
                f"{result['content']}\n"
            )
            
            # メタデータがある場合は追加
            if result.get('metadata'):
                meta = result['metadata']
                if 'source' in meta:
                    response_parts.append(f"出典: {meta['source']}\n")
        
        return "\n".join(response_parts)
        
    except Exception as e:
        error_msg = f"検索中にエラーが発生しました: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg

@function_tool
async def add_to_knowledge_base(
    ctx: RunContextWrapper[RAGContext],
    content: str,
    source: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    新しい情報を知識ベースに追加します。
    
    Args:
        content: 追加するコンテンツ
        source: 情報源（オプション）
        category: カテゴリー（オプション）
    
    Returns:
        追加結果のメッセージ
    """
    try:
        if not content or len(content.strip()) < 10:
            return "❌ コンテンツが短すぎます。もっと詳細な情報を提供してください。"
        
        # メタデータの作成
        metadata = {}
        if source:
            metadata['source'] = source
        if category:
            metadata['category'] = category
        
        # ドキュメントの追加
        doc_ids = await ctx.context.vector_store.add_document(
            content=content,
            metadata=metadata
        )
        
        success_msg = (
            f"✅ 知識ベースへの追加が完了しました！\n"
            f"   - 追加されたチャンク数: {len(doc_ids)}\n"
            f"   - ドキュメントID: {doc_ids[0] if doc_ids else 'N/A'}"
        )
        
        if source:
            success_msg += f"\n   - ソース: {source}"
        if category:
            success_msg += f"\n   - カテゴリー: {category}"
        
        return success_msg
        
    except Exception as e:
        error_msg = f"追加中にエラーが発生しました: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg

@function_tool
async def analyze_knowledge_base(
    ctx: RunContextWrapper[RAGContext]
) -> str:
    """
    知識ベースの統計情報を取得します。
    
    Returns:
        統計情報の整形されたテキスト
    """
    try:
        stats = await ctx.context.vector_store.get_statistics()
        
        response = (
            "📊 知識ベースの統計情報:\n"
            f"   - 総ドキュメント数: {stats.get('total_documents', 0)}\n"
            f"   - インデックスサイズ: {stats.get('index_size', 'N/A')}\n"
            f"   - ユニークチャンク数: {stats.get('unique_chunks', 0)}"
        )
        
        return response
        
    except Exception as e:
        error_msg = f"統計情報の取得中にエラーが発生しました: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg

# テスト関数
async def test_rag_tools():
    """RAGツールのテスト"""
    # ベクトルストアの初期化
    vector_store = VectorStore()
    await vector_store.initialize()
    
    # コンテキストの作成
    context = RAGContext(
        vector_store=vector_store,
        max_results=3,
        similarity_threshold=0.6
    )
    
    # モックのRunContextWrapper
    class MockRunContext:
        def __init__(self, ctx):
            self.context = ctx
    
    mock_ctx = MockRunContext(context)
    
    try:
        # 知識ベースへの追加テスト
        print("📝 知識ベースへの追加テスト...")
        result = await add_to_knowledge_base(
            mock_ctx,
            content="OpenAI Agents SDKは、マルチエージェントワークフローを構築するための軽量フレームワークです。",
            source="公式ドキュメント",
            category="技術"
        )
        print(result)
        
        # 検索テスト
        print("\n🔍 検索テスト...")
        result = await search_knowledge_base(
            mock_ctx,
            query="OpenAI Agents SDK",
            num_results=2
        )
        print(result)
        
        # 統計情報テスト
        print("\n📊 統計情報テスト...")
        result = await analyze_knowledge_base(mock_ctx)
        print(result)
        
    finally:
        await vector_store.close()

if __name__ == "__main__":
    asyncio.run(test_rag_tools())
EOF

# テスト実行
uv run python src/tools/rag_tools.py
```

### 6.3 RAGエージェントの実装

```bash
# RAGエージェントを作成
cat << 'EOF' > src/agents/rag_agent.py
"""RAG対応エージェントの実装"""
import asyncio
from typing import Optional, Dict, Any
from agents import Agent, Runner, ModelSettings
from dataclasses import dataclass

from src.tools.rag_tools import (
    RAGContext,
    search_knowledge_base,
    add_to_knowledge_base,
    analyze_knowledge_base
)
from src.services.vector_store import VectorStore

class RAGAgent:
    """RAG機能を持つエージェント"""
    
    def __init__(self):
        """初期化"""
        self.vector_store = None
        self.agent = None
        self.context = None
        
    async def initialize(self):
        """エージェントの初期化"""
        # ベクトルストアの初期化
        self.vector_store = VectorStore()
        await self.vector_store.initialize()
        
        # RAGコンテキストの作成
        self.context = RAGContext(
            vector_store=self.vector_store,
            max_results=5,
            similarity_threshold=0.7
        )
        
        # エージェントの作成
        self.agent = self._create_agent()
        
        print("✅ RAGエージェントを初期化しました")
    
    def _create_agent(self) -> Agent:
        """エージェントの作成"""
        
        instructions = """
        あなたは知識ベースを活用して質問に答えるAIアシスタントです。
        
        ## あなたの役割
        1. ユーザーの質問に対して、知識ベースから関連情報を検索して回答する
        2. 新しい情報を知識ベースに追加する
        3. 必要に応じて知識ベースの統計情報を提供する
        
        ## 回答の原則
        - まず知識ベースを検索して、関連情報があるか確認する
        - 検索結果に基づいて、正確で詳細な回答を提供する
        - 情報が見つからない場合は、その旨を明確に伝える
        - 回答には常に根拠となる情報源を示す
        
        ## 使用可能なツール
        - search_knowledge_base: 知識ベースから情報を検索
        - add_to_knowledge_base: 新しい情報を追加
        - analyze_knowledge_base: 統計情報の取得
        """
        
        agent = Agent[RAGContext](
            name="RAG Assistant",
            instructions=instructions,
            tools=[
                search_knowledge_base,
                add_to_knowledge_base,
                analyze_knowledge_base
            ],
            model="gpt-4o-mini",  # コスト効率の良いモデル
            model_settings=ModelSettings(
                temperature=0.3,  # より確実な回答のため低めに設定
                max_tokens=1000
            )
        )
        
        return agent
    
    async def process(self, user_input: str) -> str:
        """ユーザー入力を処理"""
        try:
            # エージェントを実行
            result = await Runner.run(
                self.agent,
                user_input,
                context=self.context
            )
            
            return result.final_output
            
        except Exception as e:
            error_msg = f"処理中にエラーが発生しました: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    async def add_knowledge(self, content: str, source: str = None) -> str:
        """知識を直接追加"""
        try:
            doc_ids = await self.vector_store.add_document(
                content=content,
                metadata={'source': source} if source else {}
            )
            return f"✅ {len(doc_ids)} チャンクを追加しました"
        except Exception as e:
            return f"❌ エラー: {str(e)}"
    
    async def close(self):
        """リソースのクリーンアップ"""
        if self.vector_store:
            await self.vector_store.close()
        print("✅ RAGエージェントをクローズしました")

# インタラクティブなテスト
async def interactive_test():
    """対話型テスト"""
    agent = RAGAgent()
    
    try:
        # 初期化
        await agent.initialize()
        
        # 初期データの追加
        print("📚 初期データを追加中...")
        initial_data = [
            {
                "content": "OpenAI Agents SDKは、エージェントベースのAIアプリケーションを構築するための軽量で強力なフレームワークです。主な特徴として、エージェント（指示とツールを備えたLLM）、ハンドオフ（エージェント間のタスク委譲）、ガードレール（入出力の検証）、セッション（会話履歴の自動管理）があります。",
                "source": "OpenAI公式ドキュメント"
            },
            {
                "content": "pgvectorは、PostgreSQLでベクトル類似度検索を可能にする拡張機能です。HNSWとIVFFlatの2つのインデックス方式をサポートしており、高次元ベクトルデータの効率的な保存と検索を実現します。RAGシステムの構築において重要な役割を果たします。",
                "source": "pgvector技術資料"
            },
            {
                "content": "RAG（Retrieval-Augmented Generation）は、大規模言語モデルの応答を外部知識ベースで強化する技術です。ユーザーの質問に対して、まず関連する情報を検索し、その情報を基にLLMが回答を生成します。これにより、より正確で最新の情報に基づいた応答が可能になります。",
                "source": "AI技術解説"
            }
        ]
        
        for data in initial_data:
            await agent.add_knowledge(data["content"], data["source"])
        
        print("\n✅ 初期データの追加が完了しました！")
        print("=" * 60)
        
        # 対話ループ
        print("\n🤖 RAGアシスタントが起動しました！")
        print("質問を入力してください（終了: 'exit' または 'quit'）")
        print("=" * 60)
        
        while True:
            # ユーザー入力
            user_input = input("\n👤 You: ").strip()
            
            # 終了コマンド
            if user_input.lower() in ['exit', 'quit', '終了']:
                print("👋 終了します...")
                break
            
            if not user_input:
                continue
            
            # 処理中メッセージ
            print("🤔 考え中...")
            
            # エージェントの応答
            response = await agent.process(user_input)
            print(f"\n🤖 Assistant: {response}")
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(interactive_test())
EOF

# 対話型テストを実行
echo "🚀 RAGエージェントを起動します..."
uv run python src/agents/rag_agent.py
```

---

## 🎯 Step 7: 完全なアプリケーションの構築

### 7.1 メインアプリケーションの作成

```bash
# メインアプリケーションを作成
cat << 'EOF' > main.py
"""RAGシステムのメインアプリケーション"""
import asyncio
import sys
from typing import Optional
from pathlib import Path

from src.agents.rag_agent import RAGAgent
from src.utils.config import Config

class RAGApplication:
    """RAGアプリケーション"""
    
    def __init__(self):
        """初期化"""
        self.agent = None
        
    async def setup(self):
        """セットアップ"""
        print("🚀 RAGシステムを起動中...")
        
        # 設定の検証
        if not Config.validate():
            print("❌ 設定エラーです。.envファイルを確認してください。")
            sys.exit(1)
        
        # エージェントの初期化
        self.agent = RAGAgent()
        await self.agent.initialize()
        
        print("✅ セットアップ完了！")
    
    async def load_documents(self, file_path: str):
        """ファイルから文書を読み込み"""
        path = Path(file_path)
        
        if not path.exists():
            print(f"❌ ファイルが見つかりません: {file_path}")
            return
        
        print(f"📄 ファイルを読み込み中: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 知識ベースに追加
            result = await self.agent.add_knowledge(
                content,
                source=path.name
            )
            print(result)
            
        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")
    
    async def interactive_mode(self):
        """対話モード"""
        print("\n" + "=" * 60)
        print("💬 対話モードを開始します")
        print("コマンド:")
        print("  - 'help': ヘルプを表示")
        print("  - 'stats': 統計情報を表示")
        print("  - 'load <file>': ファイルを読み込み")
        print("  - 'exit': 終了")
        print("=" * 60)
        
        while True:
            try:
                # ユーザー入力
                user_input = input("\n👤 > ").strip()
                
                if not user_input:
                    continue
                
                # コマンド処理
                if user_input.lower() == 'exit':
                    print("👋 終了します...")
                    break
                    
                elif user_input.lower() == 'help':
                    print("""
📖 ヘルプ:
  - 通常の質問: そのまま入力してください
  - 情報の追加: 「追加:」で始めてください
  - 統計情報: 'stats'と入力
  - ファイル読み込み: 'load <ファイルパス>'
  - 終了: 'exit'
                    """)
                    
                elif user_input.lower() == 'stats':
                    response = await self.agent.process(
                        "知識ベースの統計情報を教えてください"
                    )
                    print(f"\n{response}")
                    
                elif user_input.lower().startswith('load '):
                    file_path = user_input[5:].strip()
                    await self.load_documents(file_path)
                    
                elif user_input.startswith('追加:'):
                    content = user_input[3:].strip()
                    response = await self.agent.process(
                        f"次の情報を知識ベースに追加してください: {content}"
                    )
                    print(f"\n{response}")
                    
                else:
                    # 通常の質問
                    print("🤔 処理中...")
                    response = await self.agent.process(user_input)
                    print(f"\n🤖 {response}")
                    
            except KeyboardInterrupt:
                print("\n👋 中断されました")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")
    
    async def cleanup(self):
        """クリーンアップ"""
        if self.agent:
            await self.agent.close()
        print("✅ クリーンアップ完了")
    
    async def run(self):
        """メイン実行"""
        try:
            await self.setup()
            await self.interactive_mode()
        finally:
            await self.cleanup()

async def main():
    """メイン関数"""
    app = RAGApplication()
    await app.run()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     RAG System with OpenAI Agents SDK & PostgreSQL       ║
║                    Version 1.0.0                          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 終了しました")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        sys.exit(1)
EOF

# アプリケーションを実行
uv run python main.py
```

### 7.2 テストデータの準備

```bash
# テスト用のサンプルデータを作成
cat << 'EOF' > data/sample_knowledge.txt
# RAGシステム開発ガイド

## OpenAI Agents SDKの基本概念

OpenAI Agents SDKは、2024年にリリースされた革新的なマルチエージェントフレームワークです。
このSDKの主な特徴は以下の通りです：

1. **エージェント（Agents）**: LLMに指示とツールを装備した基本単位
2. **ツール（Tools）**: エージェントが実行できる関数やアクション
3. **ハンドオフ（Handoffs）**: エージェント間でのタスク委譲メカニズム
4. **ガードレール（Guardrails）**: 入出力の検証と安全性確保
5. **セッション（Sessions）**: 会話履歴の自動管理機能

## pgvectorの技術詳細

pgvectorは、PostgreSQLに高度なベクトル演算機能を追加する拡張機能です。

### インデックス方式

1. **HNSW (Hierarchical Navigable Small Worlds)**
   - 高速な近似最近傍探索
   - グラフベースのアルゴリズム
   - パラメータ: m（接続数）、ef_construction（構築時の品質）

2. **IVFFlat (Inverted File Flat)**
   - クラスタリングベースの探索
   - メモリ効率が良い
   - パラメータ: lists（クラスタ数）

### 距離関数

- L2距離: ユークリッド距離
- 内積: ドット積による類似度
- コサイン距離: 角度による類似度

## RAGのベストプラクティス

### チャンキング戦略

1. **固定サイズチャンキング**: トークン数で均等分割
2. **セマンティックチャンキング**: 意味的な境界で分割
3. **オーバーラップチャンキング**: 文脈保持のための重複

### エンベディングモデルの選択

- **text-embedding-3-small**: コスト効率重視（1536次元）
- **text-embedding-3-large**: 精度重視（3072次元）
- **text-embedding-ada-002**: レガシーモデル（1536次元）

### 検索精度の向上

1. **ハイブリッド検索**: ベクトル検索 + キーワード検索
2. **リランキング**: 初期検索結果の再順位付け
3. **メタデータフィルタリング**: カテゴリやタグによる絞り込み
EOF

echo "✅ サンプルデータを作成しました: data/sample_knowledge.txt"
```

### 7.3 統合テストの実行

```bash
# 統合テストスクリプトを作成
cat << 'EOF' > test_integration.py
"""統合テスト"""
import asyncio
import time
from src.agents.rag_agent import RAGAgent

async def run_integration_test():
    """統合テストの実行"""
    print("🧪 統合テストを開始します...")
    
    agent = RAGAgent()
    
    try:
        # 1. 初期化テスト
        print("\n[Test 1] エージェントの初期化")
        start_time = time.time()
        await agent.initialize()
        init_time = time.time() - start_time
        print(f"✅ 初期化成功 (所要時間: {init_time:.2f}秒)")
        
        # 2. データ追加テスト
        print("\n[Test 2] データの追加")
        test_data = [
            "Pythonは汎用プログラミング言語です。",
            "機械学習にはscikit-learnがよく使われます。",
            "Docker/Podmanはコンテナ技術です。"
        ]
        
        for data in test_data:
            result = await agent.add_knowledge(data, source="test")
            print(f"  {result}")
        
        # 3. 検索テスト
        print("\n[Test 3] 検索機能")
        queries = [
            "Pythonについて教えて",
            "コンテナ技術について",
            "機械学習のライブラリ"
        ]
        
        for query in queries:
            print(f"\n  Query: {query}")
            response = await agent.process(query)
            print(f"  Response: {response[:100]}...")
        
        # 4. 統計情報テスト
        print("\n[Test 4] 統計情報の取得")
        stats_response = await agent.process("知識ベースの統計を表示")
        print(f"  {stats_response}")
        
        # 5. パフォーマンステスト
        print("\n[Test 5] パフォーマンス測定")
        start_time = time.time()
        for _ in range(3):
            await agent.process("テストクエリ")
        avg_time = (time.time() - start_time) / 3
        print(f"✅ 平均応答時間: {avg_time:.2f}秒")
        
        print("\n🎉 すべてのテストが成功しました！")
        
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        raise
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
EOF

# 統合テストを実行
uv run python test_integration.py
```

---

## 🎓 学習の確認とトラブルシューティング

### よくあるエラーと対処法

#### 1. Podmanコンテナが起動しない
```bash
# Podmanマシンの状態確認
podman machine list

# 停止している場合は再起動
podman machine stop
podman machine start

# コンテナの再起動
podman restart ragdb
```

#### 2. OpenAI APIキーエラー
```bash
# .envファイルの確認
cat .env | grep OPENAI_API_KEY

# APIキーの有効性確認
uv run python -c "
from openai import OpenAI
client = OpenAI()
try:
    client.models.list()
    print('✅ APIキー有効')
except:
    print('❌ APIキー無効')
"
```

#### 3. データベース接続エラー
```bash
# PostgreSQLの接続確認
PGPASSWORD=ragpassword psql -h localhost -U raguser -d ragdatabase -c "SELECT 1;"

# pgvectorの確認
PGPASSWORD=ragpassword psql -h localhost -U raguser -d ragdatabase -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

### 動作確認チェックリスト

```bash
# 完全な動作確認スクリプトを作成
cat << 'EOF' > check_system.py
"""システム動作確認"""
import asyncio
import subprocess
import sys
from pathlib import Path

def check_command(cmd, name):
    """コマンドの存在確認"""
    try:
        subprocess.run(cmd, capture_output=True, shell=True, check=True)
        print(f"✅ {name}: OK")
        return True
    except:
        print(f"❌ {name}: NG")
        return False

async def check_system():
    """システム全体の確認"""
    print("🔍 システム診断を開始します...\n")
    
    all_ok = True
    
    # 1. 基本コマンド
    print("【基本コマンド】")
    all_ok &= check_command("uv --version", "uv")
    all_ok &= check_command("podman --version", "Podman")
    all_ok &= check_command("python3 --version", "Python")
    
    # 2. Podmanコンテナ
    print("\n【Podmanコンテナ】")
    all_ok &= check_command("podman ps | grep ragdb", "PostgreSQLコンテナ")
    
    # 3. Python環境
    print("\n【Python環境】")
    try:
        import openai
        print("✅ openai: OK")
    except:
        print("❌ openai: NG")
        all_ok = False
    
    try:
        import asyncpg
        print("✅ asyncpg: OK")
    except:
        print("❌ asyncpg: NG")
        all_ok = False
    
    try:
        import agents
        print("✅ openai-agents: OK")
    except:
        print("❌ openai-agents: NG")
        all_ok = False
    
    # 4. 設定ファイル
    print("\n【設定ファイル】")
    if Path(".env").exists():
        print("✅ .env: OK")
    else:
        print("❌ .env: NG")
        all_ok = False
    
    # 5. データベース接続
    print("\n【データベース接続】")
    try:
        from src.utils.config import Config
        if Config.validate():
            print("✅ 設定検証: OK")
        else:
            print("❌ 設定検証: NG")
            all_ok = False
    except Exception as e:
        print(f"❌ 設定読み込み: NG ({e})")
        all_ok = False
    
    # 結果
    print("\n" + "=" * 40)
    if all_ok:
        print("✅ システム診断: すべて正常です！")
    else:
        print("❌ システム診断: 問題が見つかりました")
        print("   上記のNGの項目を確認してください")
    
    return all_ok

if __name__ == "__main__":
    result = asyncio.run(check_system())
    sys.exit(0 if result else 1)
EOF

# システム診断を実行
uv run python check_system.py
```

---

## 🎉 完成！

おめでとうございます！RAGシステムの構築が完了しました。

### 次のステップ

1. **機能拡張**
   - PDFファイルの読み込み機能追加
   - Web UIの実装（Gradio/Streamlit）
   - マルチエージェントシステムの拡張

2. **最適化**
   - インデックスパラメータのチューニング
   - キャッシュ機能の実装
   - バッチ処理の最適化

3. **本番環境への展開**
   - Docker/Kubernetes対応
   - 認証・認可の実装
   - モニタリング・ログ収集

### 学習リソース

- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

頑張って開発を続けてください！ 🚀