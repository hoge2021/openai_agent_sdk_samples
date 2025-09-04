#!/usr/bin/env python3
"""
OpenAI Agents SDK - Agent Clone/Copy サンプルプログラム
"""

import asyncio
import os
import sys
import datetime
from dataclasses import dataclass
from typing import List

# OpenAI Agents SDK のインポート
try:
    from pydantic import BaseModel
    from agents import (
        Agent,
        Runner,
        RunContextWrapper,
        function_tool,
        handoff
    )
except ImportError:
    print("❌ エラー: 必要なライブラリがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install openai-agents pydantic")
    sys.exit(1)


# ユーザーコンテキストの定義
@dataclass
class UserContext:
    name: str
    preferred_language: str
    topic_interest: str


# 出力データモデルの定義
class StandardResponse(BaseModel):
    """標準応答モデル"""
    content: str
    tone: str
    confidence: float


class CreativeResponse(BaseModel):
    """クリエイティブ応答モデル"""
    content: str
    creativity_level: str
    inspiration_source: str
    metaphors: List[str]


class TechnicalResponse(BaseModel):
    """技術的応答モデル"""
    content: str
    complexity_level: str
    code_examples: List[str]
    references: List[str]


# 共通ツール関数の定義
@function_tool
def get_current_time() -> str:
    """現在の時刻を取得する"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@function_tool
def get_weather(city: str = "東京") -> str:
    """天気情報を取得する（模擬）"""
    import random
    weathers = ["晴れ", "曇り", "雨", "雪"]
    temp = random.randint(15, 30)
    weather = random.choice(weathers)
    return f"{city}の天気: {weather}, 気温: {temp}度"


# 特殊ツール関数
@function_tool
def generate_creative_idea(topic: str) -> str:
    """クリエイティブなアイデアを生成する"""
    ideas = [
        f"{topic}に関する詩を書く",
        f"{topic}をテーマにした短編小説",
        f"{topic}の斬新な活用方法",
        f"{topic}を使ったアート作品"
    ]
    import random
    return f"アイデア: {random.choice(ideas)}"


@function_tool
def get_technical_specs(technology: str) -> str:
    """技術仕様を取得する（模擬）"""
    specs = {
        "Python": "バージョン: 3.12, パフォーマンス: 高速, 用途: 汎用プログラミング",
        "JavaScript": "バージョン: ES2023, エンジン: V8, 用途: Web開発",
        "React": "バージョン: 18.0, タイプ: UIライブラリ, エコシステム: 豊富"
    }
    return specs.get(technology, f"{technology}の詳細仕様情報")


def check_api_key():
    """OpenAI API キーの存在確認"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ エラー: 環境変数 OPENAI_API_KEY が設定されていません。")
        print("以下の方法で設定してください:")
        print("  Linux/Mac: export OPENAI_API_KEY='your-api-key-here'")
        print("  Windows: set OPENAI_API_KEY=your-api-key-here")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️  警告: API キーの形式が正しくない可能性があります。")
        print("OpenAI API キーは通常 'sk-' で始まります。")
    
    print("✅ API キーが正常に設定されています")
    return True


async def demonstrate_agent_cloning(user_context: UserContext):
    """Agent Clone/Copyのデモンストレーション"""
    
    # ===== 1. ベースAgentの作成 =====
    print("🏗️  ベースAgentを作成中...")
    base_agent = Agent[UserContext](
        name="Base Assistant",
        instructions=(
            f"{user_context.name}さんのアシスタントです。"
            "質問に対して helpful で丁寧な回答をします。"
            f"言語設定: {user_context.preferred_language}"
        ),
        model="gpt-4o-mini",
        tools=[get_current_time, get_weather],
        output_type=StandardResponse,
    )
    print(f"✅ ベースAgent '{base_agent.name}' を作成完了")
    
    # ===== 2. Clone 1: クリエイティブAgent =====
    print("\n🎨 クリエイティブAgentをclone中...")
    creative_agent = base_agent.clone(
        name="Creative Assistant",
        instructions=(
            f"{user_context.name}さん専用のクリエイティブアシスタントです。"
            "想像力豊かで、詩的で、比喩を多用した回答をします。"
            "アートや文学からインスピレーションを得て回答します。"
            f"興味分野: {user_context.topic_interest}"
        ),
        tools=[get_current_time, get_weather, generate_creative_idea],
        output_type=CreativeResponse,
    )
    print(f"✅ クリエイティブAgent '{creative_agent.name}' をclone完了")
    
    # ===== 3. Clone 2: 技術専門Agent =====
    print("\n🔧 技術専門Agentをclone中...")
    technical_agent = base_agent.clone(
        name="Technical Specialist",
        instructions=(
            f"{user_context.name}さんの技術専門アシスタントです。"
            "正確で詳細な技術情報を提供し、コード例や参考資料を含めます。"
            "複雑な概念をわかりやすく説明し、実践的なアドバイスを提供します。"
        ),
        tools=[get_current_time, get_technical_specs],  # 技術系ツールのみ
        output_type=TechnicalResponse,
    )
    print(f"✅ 技術専門Agent '{technical_agent.name}' をclone完了")
    
    # ===== 4. Clone 3: 簡潔回答Agent =====
    print("\n⚡ 簡潔回答Agentをclone中...")
    concise_agent = base_agent.clone(
        name="Concise Assistant",
        instructions=(
            f"{user_context.name}さん向けの簡潔なアシスタントです。"
            "要点を絞った短い回答を提供します。"
            "無駄な説明を避け、核心を突いた情報のみ提供します。"
        ),
        tools=[get_current_time],  # 最小限のツールのみ
        # output_typeをデフォルト（str）に戻す
        output_type=None,
    )
    print(f"✅ 簡潔回答Agent '{concise_agent.name}' をclone完了")
    
    # ===== 5. ハンドオフの設定 =====
    print("\n🔄 マスターAgentにハンドオフ設定中...")
    master_agent = Agent[UserContext](
        name="Master Coordinator",
        instructions=(
            f"{user_context.name}さんのマスターコーディネーターです。"
            "質問の内容に応じて最適な専門Agentにハンドオフします：\n"
            "- クリエイティブな質問 → Creative Assistant\n"
            "- 技術的な質問 → Technical Specialist\n"
            "- 簡単な質問 → Concise Assistant\n"
            "- 一般的な質問は自分で回答します"
        ),
        model="gpt-4o-mini",
        tools=[get_current_time],
        handoffs=[
            handoff(creative_agent, tool_description_override="クリエイティブで芸術的な回答が必要な場合に使用"),
            handoff(technical_agent, tool_description_override="技術的で詳細な情報が必要な場合に使用"),  
            handoff(concise_agent, tool_description_override="簡潔で要点を絞った回答が必要な場合に使用"),
        ],
    )
    print(f"✅ マスターAgent '{master_agent.name}' を設定完了")
    
    # ===== 6. 各Agentのテスト実行 =====
    test_question = "今日の天気はどうですか？"
    agents_to_test = [
        ("ベースAgent", base_agent),
        ("クリエイティブAgent", creative_agent),
        ("技術専門Agent", technical_agent),
        ("簡潔回答Agent", concise_agent),
    ]
    
    print(f"\n" + "="*80)
    print(f"🧪 各Agentのテスト実行: 「{test_question}」")
    print("="*80)
    
    for agent_name, agent in agents_to_test:
        print(f"\n📝 {agent_name}の応答:")
        print("-" * 40)
        
        try:
            result = await Runner.run(agent, test_question, context=user_context)
            
            if hasattr(result.final_output, 'content'):
                # Pydanticモデルの場合
                output = result.final_output
                print(f"💬 内容: {output.content}")
                
                if hasattr(output, 'tone'):
                    print(f"🎵 トーン: {output.tone}")
                    print(f"🎯 信頼度: {output.confidence}")
                elif hasattr(output, 'creativity_level'):
                    print(f"🎨 創造性レベル: {output.creativity_level}")
                    print(f"💡 インスピレーション: {output.inspiration_source}")
                    print(f"🔮 比喩: {', '.join(output.metaphors)}")
                elif hasattr(output, 'complexity_level'):
                    print(f"🔧 複雑性レベル: {output.complexity_level}")
                    print(f"📝 コード例: {', '.join(output.code_examples)}")
                    print(f"📚 参考文献: {', '.join(output.references)}")
                    
            else:
                # 文字列出力の場合
                print(f"💬 応答: {result.final_output}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            print(f"詳細: {type(e).__name__}")
    
    # ===== 7. マスターAgentのハンドオフテスト =====
    print(f"\n" + "="*80)
    print("🔄 マスターAgentのハンドオフテスト")
    print("="*80)
    
    handoff_questions = [
        "プログラミングについて詳しく教えて",
        "恋について詩を書いて",
        "今何時？",
    ]
    
    for question in handoff_questions:
        print(f"\n❓ 質問: 「{question}」")
        print("-" * 50)
        
        try:
            result = await Runner.run(master_agent, question, context=user_context)
            
            # 最後に実行されたAgentを確認
            print(f"🎯 実行Agent: {result.last_agent.name}")
            
            # 応答内容
            if hasattr(result.final_output, 'content'):
                print(f"💬 応答: {result.final_output.content}")
            else:
                print(f"💬 応答: {result.final_output}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            name="山田太郎",
            preferred_language="日本語",
            topic_interest="テクノロジーとアート"
        )
        
        print("🎪 OpenAI Agents SDK - Agent Clone/Copy デモ")
        print("="*60)
        print(f"👤 ユーザー: {user_context.name}")
        print(f"🌐 言語: {user_context.preferred_language}")
        print(f"🎯 興味分野: {user_context.topic_interest}")
        print("="*60)
        
        # Agent Clone/Copyのデモンストレーション
        await demonstrate_agent_cloning(user_context)
        
        print(f"\n🎉 Agent Clone/Copy デモンストレーション完了！")
        print("="*80)
        print("📊 今回のデモで学べたこと:")
        print("✅ ベースAgentの作成")
        print("✅ clone()メソッドによるAgent複製")
        print("✅ 各Agentの個別カスタマイズ")
        print("✅ 異なる出力タイプの使用")
        print("✅ ツールセットの変更")
        print("✅ ハンドオフによるAgent間連携")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  プログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        print(f"エラー詳細: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())