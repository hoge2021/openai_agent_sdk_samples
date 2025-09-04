"""
OpenAI Agents SDK - Handoff機能のサンプルプログラム
複数のエージェント間でタスクを引き継ぐシンプルな例
"""

import os
import sys
import asyncio
from typing import Optional
from agents import Agent, Runner, handoff
from agents.exceptions import AgentsException, MaxTurnsExceeded


# 環境変数のチェック
def check_api_key() -> bool:
    """OpenAI APIキーが環境変数に設定されているか確認"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 'OPENAI_API_KEY' が設定されていません。")
        print("設定方法: export OPENAI_API_KEY='your-api-key-here'")
        return False
    if api_key.startswith("sk-") and len(api_key) > 10:
        return True
    else:
        print("警告: APIキーの形式が正しくない可能性があります。")
        return True


def create_agents():
    """各専門エージェントの作成"""
    
    # 1. 技術サポートエージェント
    tech_agent = Agent(
        name="技術サポート",
        instructions="""
        あなたは技術サポート担当のエージェントです。
        プログラミング、ソフトウェア、ハードウェアに関する質問に答えてください。
        簡潔で分かりやすい説明を心がけてください。
        """
    )
    
    # 2. 請求・料金エージェント
    billing_agent = Agent(
        name="請求担当",
        instructions="""
        あなたは請求・料金担当のエージェントです。
        料金プラン、支払い方法、請求書に関する質問に答えてください。
        丁寧で親切な対応を心がけてください。
        """
    )
    
    # 3. 一般サポートエージェント
    general_agent = Agent(
        name="一般サポート",
        instructions="""
        あなたは一般的な質問を担当するエージェントです。
        技術的でも請求関連でもない一般的な質問に答えてください。
        フレンドリーで親しみやすい対応を心がけてください。
        """
    )
    
    # 4. トリアージエージェント（最初の受付・振り分け担当）
    triage_agent = Agent(
        name="受付担当",
        instructions="""
        あなたは最初の受付を担当するエージェントです。
        ユーザーの質問を分析して、適切な専門エージェントに引き継いでください。
        
        振り分けルール：
        - プログラミング、ソフトウェア、技術的な問題 → 技術サポートに引き継ぐ
        - 料金、支払い、請求書に関する問題 → 請求担当に引き継ぐ
        - その他の一般的な質問 → 一般サポートに引き継ぐ
        
        必ず適切なエージェントに引き継いでください。
        """,
        handoffs=[
            handoff(tech_agent),
            handoff(billing_agent),
            handoff(general_agent)
        ]
    )
    
    return triage_agent


async def handle_user_query(agent: Agent, query: str):
    """ユーザーのクエリを処理"""
    try:
        print(f"\n質問: {query}")
        print("-" * 50)
        
        # エージェントを実行
        result = await Runner.run(
            starting_agent=agent,
            input=query,
            max_turns=5  # 最大5回のエージェント間引き継ぎを許可
        )
        
        # 結果を表示
        print(f"回答: {result.final_output}")
        print(f"担当エージェント: {result.last_agent.name}")
        
        return result
        
    except MaxTurnsExceeded:
        print("エラー: エージェント間の引き継ぎ回数が上限に達しました。")
    except AgentsException as e:
        print(f"エージェントエラー: {e}")
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """メイン処理"""
    
    # APIキーの確認
    if not check_api_key():
        sys.exit(1)
    
    print("OpenAI Agents SDK - Handoffサンプル")
    print("=" * 50)
    
    try:
        # エージェントの作成
        triage_agent = create_agents()
        print("エージェントの初期化が完了しました。")
        
        # サンプル質問のリスト
        sample_queries = [
            "Pythonでリストをソートする方法を教えてください",
            "月額料金プランについて教えてください",
            "営業時間を教えてください",
            "APIのエラー処理について質問があります"
        ]
        
        # 各質問を処理
        for query in sample_queries:
            await handle_user_query(triage_agent, query)
            print("\n" + "=" * 50)
            await asyncio.sleep(1)  # レート制限対策
            
    except KeyboardInterrupt:
        print("\n\n処理を中断しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 非同期処理の実行
    asyncio.run(main())