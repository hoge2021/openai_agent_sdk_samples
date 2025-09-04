#!/usr/bin/env python3
"""
OpenAI Agents SDK - Guardrails サンプルプログラム
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any, List, Union

# OpenAI Agents SDK のインポート
try:
    from pydantic import BaseModel
    from agents import (
        Agent,
        Runner,
        RunContextWrapper,
        function_tool,
        input_guardrail,
        output_guardrail,
        GuardrailFunctionOutput,
        InputGuardrailTripwireTriggered,
        OutputGuardrailTripwireTriggered,
        TResponseInputItem,
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
    user_type: str  # "customer", "admin", "guest"


# Pydantic モデルの定義
class InappropriateContentOutput(BaseModel):
    """不適切コンテンツ検出の結果"""
    is_inappropriate: bool
    reason: str
    confidence_score: float


class ProfessionalityOutput(BaseModel):
    """プロフェッショナリティチェックの結果"""
    is_professional: bool
    issues: List[str]
    severity: str  # "low", "medium", "high"


class CustomerResponse(BaseModel):
    """カスタマーサポートエージェントの応答"""
    response: str
    category: str
    confidence: float


# ツール関数の定義
@function_tool
def get_company_policy(topic: str) -> str:
    """会社のポリシーを取得する"""
    policies = {
        "refund": "30日以内の未使用商品は全額返金可能です。",
        "shipping": "通常配送は3-5営業日、お急ぎ便は翌日配送です。",
        "support": "平日9:00-18:00にサポートを提供しています。"
    }
    return policies.get(topic, "該当するポリシーが見つかりません。")


# Input Guardrail の実装
@input_guardrail
async def inappropriate_content_guardrail(
    ctx: RunContextWrapper[UserContext], 
    agent: Agent, 
    input_data: Union[str, List[TResponseInputItem]]
) -> GuardrailFunctionOutput:
    """不適切なコンテンツをチェックするInput Guardrail"""
    
    # Guardrail用のAgent
    guardrail_agent = Agent(
        name="Content Moderator",
        instructions=(
            "ユーザーの入力が不適切でないかチェックしてください。"
            "以下を不適切と判断します："
            "1. 攻撃的・侮辱的な言葉"
            "2. 差別的な内容"
            "3. 個人情報の要求"
            "4. 業務に関係のない質問（数学の宿題など）"
            "confidence_scoreは0-1の範囲で設定してください。"
        ),
        model="gpt-4o-mini",
        output_type=InappropriateContentOutput,
    )
    
    try:
        # 入力を文字列に変換
        if isinstance(input_data, list):
            text_input = " ".join([str(item) for item in input_data])
        else:
            text_input = str(input_data)
        
        result = await Runner.run(guardrail_agent, text_input, context=ctx.context)
        output = result.final_output
        
        print(f"🛡️  [Input Guardrail] 不適切コンテンツチェック結果:")
        print(f"   判定: {'⚠️ 不適切' if output.is_inappropriate else '✅ 適切'}")
        print(f"   理由: {output.reason}")
        print(f"   信頼度: {output.confidence_score:.2f}")
        
        return GuardrailFunctionOutput(
            output_info=output,
            tripwire_triggered=output.is_inappropriate and output.confidence_score > 0.7
        )
        
    except Exception as e:
        print(f"❌ Input Guardrailでエラー: {e}")
        # エラー時はtripwireをトリガーしない（安全側に倒す）
        return GuardrailFunctionOutput(
            output_info={"error": str(e)},
            tripwire_triggered=False
        )


# Output Guardrail の実装
@output_guardrail
async def professionality_guardrail(
    ctx: RunContextWrapper[UserContext],
    agent: Agent,
    output: CustomerResponse
) -> GuardrailFunctionOutput:
    """応答のプロフェッショナリティをチェックするOutput Guardrail"""
    
    # Guardrail用のAgent
    guardrail_agent = Agent(
        name="Professionality Checker",
        instructions=(
            "カスタマーサポートの応答がプロフェッショナルかチェックしてください。"
            "以下をチェックします："
            "1. 丁寧な言葉遣い"
            "2. 適切な敬語の使用"
            "3. 感情的でない客観的な内容"
            "4. 会社の方針に沿った回答"
            "問題があれば具体的にissuesリストに記載し、"
            "severity を low/medium/high で設定してください。"
        ),
        model="gpt-4o-mini",
        output_type=ProfessionalityOutput,
    )
    
    try:
        result = await Runner.run(guardrail_agent, output.response, context=ctx.context)
        check_result = result.final_output
        
        print(f"🛡️  [Output Guardrail] プロフェッショナリティチェック結果:")
        print(f"   判定: {'✅ 適切' if check_result.is_professional else '⚠️ 問題あり'}")
        print(f"   重要度: {check_result.severity}")
        if check_result.issues:
            print(f"   問題点: {', '.join(check_result.issues)}")
        
        # 高重要度の問題がある場合はtripwireをトリガー
        should_trigger = (not check_result.is_professional and 
                         check_result.severity == "high")
        
        return GuardrailFunctionOutput(
            output_info=check_result,
            tripwire_triggered=should_trigger
        )
        
    except Exception as e:
        print(f"❌ Output Guardrailでエラー: {e}")
        # エラー時はtripwireをトリガーしない
        return GuardrailFunctionOutput(
            output_info={"error": str(e)},
            tripwire_triggered=False
        )


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


async def test_agent_with_guardrails(user_context: UserContext):
    """Guardrailsを使用したAgentのテスト"""
    
    # メインのカスタマーサポートAgent
    customer_support_agent = Agent[UserContext](
        name="Customer Support Agent",
        instructions=(
            f"あなたは{user_context.name}さんをサポートする"
            "プロフェッショナルなカスタマーサポート担当者です。"
            "丁寧で親切に、会社のポリシーに基づいて回答してください。"
            "必要に応じてツールを使用してポリシー情報を取得してください。"
        ),
        model="gpt-4o-mini",
        tools=[get_company_policy],
        input_guardrails=[inappropriate_content_guardrail],
        output_guardrails=[professionality_guardrail],
        output_type=CustomerResponse,
    )
    
    # テストケース
    test_cases = [
        {
            "input": "返金ポリシーについて教えてください",
            "description": "適切な質問（Guardrailは通過する）"
        },
        {
            "input": "おい、サポート！速く答えろ！",
            "description": "不適切な質問（Input Guardrailでブロックされる可能性）"
        },
        {
            "input": "数学の宿題を手伝ってください: 2x + 3 = 11 の x を求めてください",
            "description": "業務外の質問（Input Guardrailでブロックされる可能性）"
        }
    ]
    
    print("=" * 80)
    print("🛡️  Guardrails デモンストレーション")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 テストケース {i}: {test_case['description']}")
        print(f"入力: 「{test_case['input']}」")
        print("-" * 60)
        
        try:
            result = await Runner.run(
                customer_support_agent, 
                test_case['input'], 
                context=user_context
            )
            
            print(f"✅ 実行成功")
            print(f"💬 応答: {result.final_output.response}")
            print(f"📊 カテゴリ: {result.final_output.category}")
            print(f"🎯 信頼度: {result.final_output.confidence:.2f}")
            
        except InputGuardrailTripwireTriggered as e:
            print(f"🚨 Input Guardrail がトリガーされました")
            print(f"理由: 不適切な入力が検出されました")
            # Guardrailの結果から詳細情報を取得
            if hasattr(e, 'guardrail_results') and e.guardrail_results:
                for result in e.guardrail_results:
                    if hasattr(result, 'output_info'):
                        info = result.output_info
                        if hasattr(info, 'reason'):
                            print(f"詳細: {info.reason}")
            
        except OutputGuardrailTripwireTriggered as e:
            print(f"🚨 Output Guardrail がトリガーされました")
            print(f"理由: 不適切な応答が検出されました")
            # Guardrailの結果から詳細情報を取得
            if hasattr(e, 'guardrail_results') and e.guardrail_results:
                for result in e.guardrail_results:
                    if hasattr(result, 'output_info'):
                        info = result.output_info
                        if hasattr(info, 'issues'):
                            print(f"問題点: {', '.join(info.issues)}")
            
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            print(f"エラータイプ: {type(e).__name__}")
        
        print("-" * 60)


async def main():
    """メイン関数"""
    
    # API キーの確認
    if not check_api_key():
        sys.exit(1)
    
    try:
        # ユーザーコンテキストの作成
        user_context = UserContext(
            name="田中様",
            user_type="customer"
        )
        
        print("🎪 OpenAI Agents SDK - Guardrails デモ")
        print(f"ユーザー: {user_context.name} ({user_context.user_type})")
        
        # GuardrailsデモをC実行
        await test_agent_with_guardrails(user_context)
        
        print("\n🎉 すべてのテストが完了しました！")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  プログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        print(f"エラー詳細: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())