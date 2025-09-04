#!/usr/bin/env python3
"""
OpenAI Agents SDK Guardrail サンプルプログラム
Input Guardrail、Output Guardrail、Tripwiresの実装例
"""

import os
import asyncio
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

# OpenAI Agents SDKのインポート
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
    set_tracing_disabled,
)


# ========== モデル定義 ==========

class MathHomeworkDetection(BaseModel):
    """数学の宿題検出用のモデル"""
    is_math_homework: bool
    reasoning: str
    confidence_score: float


class InappropriateContentDetection(BaseModel):
    """不適切なコンテンツ検出用のモデル"""
    is_inappropriate: bool
    reasoning: str
    severity: str  # "low", "medium", "high"


class CustomerSupportResponse(BaseModel):
    """カスタマーサポートの応答モデル"""
    response: str
    category: str
    helpful: bool


# ========== Guardrailエージェント定義 ==========

# 数学宿題検出用のガードレールエージェント
math_homework_guardrail_agent = Agent(
    name="Math Homework Detector",
    instructions="""
    ユーザーの入力が数学の宿題に関する質問かどうかを判定してください。
    以下の要素を確認してください：
    - 数学の問題（方程式、計算、幾何学など）
    - 「宿題を手伝って」「答えを教えて」などの表現
    - 学校の課題らしい内容
    
    confidence_scoreは0.0-1.0の範囲で設定してください。
    """,
    output_type=MathHomeworkDetection,
)

# 不適切なコンテンツ検出用のガードレールエージェント
inappropriate_content_guardrail_agent = Agent(
    name="Inappropriate Content Detector", 
    instructions="""
    出力内容が不適切でないかを判定してください。
    以下の要素をチェックしてください：
    - 攻撃的な言語や侮辱的な内容
    - 差別的な表現
    - 誤った情報や危険な助言
    - プライバシーを侵害する可能性のある内容
    
    severityは以下のように設定してください：
    - low: 軽微な問題
    - medium: 中程度の問題  
    - high: 深刻な問題
    """,
    output_type=InappropriateContentDetection,
)


# ========== Guardrail関数定義 ==========

@input_guardrail
async def math_homework_input_guardrail(
    ctx: RunContextWrapper[None], 
    agent: Agent, 
    input: str | List[TResponseInputItem]
) -> GuardrailFunctionOutput:
    """
    Input Guardrail: 数学の宿題検出
    ユーザーの入力が数学の宿題かどうかをチェックする
    """
    print("🔍 Input Guardrail: 数学宿題チェックを実行中...")
    
    try:
        # ガードレールエージェントで入力を分析
        result = await Runner.run(
            math_homework_guardrail_agent, 
            input, 
            context=ctx.context
        )
        
        detection_result = result.final_output
        print(f"   判定結果: {'数学宿題' if detection_result.is_math_homework else '正常な質問'}")
        print(f"   理由: {detection_result.reasoning}")
        print(f"   信頼度: {detection_result.confidence_score:.2f}")
        
        # confidence_scoreが0.7以上かつ数学宿題と判定された場合にtripwireを発動
        tripwire_should_trigger = (
            detection_result.is_math_homework and 
            detection_result.confidence_score >= 0.7
        )
        
        return GuardrailFunctionOutput(
            output_info={
                "detection_type": "math_homework",
                "result": detection_result,
                "tripwire_triggered": tripwire_should_trigger
            },
            tripwire_triggered=tripwire_should_trigger,
        )
    
    except Exception as e:
        print(f"❌ Input Guardrailでエラーが発生: {e}")
        # エラー時は安全側に倒してtripwireを発動
        return GuardrailFunctionOutput(
            output_info={"error": str(e)},
            tripwire_triggered=True,
        )


@output_guardrail  
async def inappropriate_content_output_guardrail(
    ctx: RunContextWrapper,
    agent: Agent, 
    output: CustomerSupportResponse
) -> GuardrailFunctionOutput:
    """
    Output Guardrail: 不適切なコンテンツ検出
    エージェントの出力が不適切でないかをチェックする
    """
    print("🔍 Output Guardrail: 不適切コンテンツチェックを実行中...")
    
    try:
        # ガードレールエージェントで出力を分析
        result = await Runner.run(
            inappropriate_content_guardrail_agent, 
            output.response, 
            context=ctx.context
        )
        
        detection_result = result.final_output
        print(f"   判定結果: {'不適切' if detection_result.is_inappropriate else '適切'}")
        print(f"   理由: {detection_result.reasoning}")
        print(f"   重要度: {detection_result.severity}")
        
        # 不適切と判定され、重要度がmedium以上の場合にtripwireを発動
        tripwire_should_trigger = (
            detection_result.is_inappropriate and 
            detection_result.severity in ["medium", "high"]
        )
        
        return GuardrailFunctionOutput(
            output_info={
                "detection_type": "inappropriate_content", 
                "result": detection_result,
                "tripwire_triggered": tripwire_should_trigger
            },
            tripwire_triggered=tripwire_should_trigger,
        )
        
    except Exception as e:
        print(f"❌ Output Guardrailでエラーが発生: {e}")
        # エラー時は安全側に倒してtripwireを発動
        return GuardrailFunctionOutput(
            output_info={"error": str(e)},
            tripwire_triggered=True,
        )


# ========== メインエージェント定義 ==========

customer_support_agent = Agent(
    name="Customer Support Agent",
    instructions="""
    あなたは親切で知識豊富なカスタマーサポートエージェントです。
    お客様の質問に丁寧に回答し、問題解決をサポートしてください。
    
    以下のガイドラインに従ってください：
    - 常に礼儀正しく、専門的な対応を心がける
    - 分からないことは正直に伝える
    - 適切な解決策を提供する
    - お客様の満足を最優先に考える
    """,
    input_guardrails=[math_homework_input_guardrail],
    output_guardrails=[inappropriate_content_output_guardrail],
    output_type=CustomerSupportResponse,
)


# ========== ユーティリティ関数 ==========

def load_environment():
    """環境変数を読み込み、必要なチェックを行う"""
    # .envファイルを読み込み
    load_dotenv()
    
    # OPENAI_API_KEYの存在確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEYが設定されていません。\n"
            ".envファイルに以下の形式で設定してください：\n"
            "OPENAI_API_KEY=your_api_key_here"
        )
    
    print("✅ 環境変数の読み込みが完了しました")
    return api_key


async def test_guardrails():
    """Guardrailの動作をテストする"""
    
    test_cases = [
        {
            "name": "正常な質問",
            "input": "製品の返品方法を教えてください。",
            "should_trigger_input": False,
        },
        {
            "name": "数学の宿題（Input Guardrailがトリガーされるはず）",
            "input": "宿題の数学の問題を手伝ってください。2x + 3 = 11のxを求めてください。",
            "should_trigger_input": True,
        },
        {
            "name": "技術的な質問",
            "input": "アプリのログイン方法がわかりません。",
            "should_trigger_input": False,
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}: {test_case['name']}")
        print(f"入力: {test_case['input']}")
        print("="*60)
        
        try:
            # エージェントを実行
            result = await Runner.run(customer_support_agent, test_case["input"])
            
            print("✅ 実行成功")
            print(f"応答: {result.final_output.response}")
            print(f"カテゴリ: {result.final_output.category}")
            print(f"有用性: {'はい' if result.final_output.helpful else 'いいえ'}")
            
        except InputGuardrailTripwireTriggered as e:
            print("🚨 Input Guardrail Tripwireが発動されました！")
            print(f"理由: 不適切な入力が検出されました")
            print("これは期待される動作です。") if test_case["should_trigger_input"] else print("予期しない動作です。")
            
        except OutputGuardrailTripwireTriggered as e:
            print("🚨 Output Guardrail Tripwireが発動されました！")
            print(f"理由: 不適切な出力が検出されました")
            
        except Exception as e:
            print(f"❌ 予期しないエラーが発生しました: {e}")
            print(f"エラータイプ: {type(e).__name__}")


async def main():
    """メイン関数"""
    print("🚀 OpenAI Agents SDK Guardrail サンプルプログラム開始")
    print("="*60)
    
    try:
        # 環境変数の読み込みとチェック
        load_environment()
        
        # トレーシングを無効化（OpenAI APIキーが不要）
        set_tracing_disabled(True)
        print("✅ トレーシングを無効化しました")
        
        # Guardrailのテスト実行
        await test_guardrails()
        
        print(f"\n{'='*60}")
        print("🎉 全てのテストが完了しました")
        
    except ValueError as e:
        print(f"❌ 環境設定エラー: {e}")
        return 1
        
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        print(f"エラータイプ: {type(e).__name__}")
        return 1
    
    return 0


if __name__ == "__main__":
    # プログラムの実行
    exit_code = asyncio.run(main())
    exit(exit_code)