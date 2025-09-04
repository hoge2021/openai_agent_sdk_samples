"""
OpenAI Agents SDK - Output Type を使用したサンプルプログラム

Output Typeを使うことで、エージェントの出力を構造化された形式で取得できます。
このサンプルでは、3つの実用的な例を示します。
"""

import asyncio
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from agents import Agent, Runner

# ============================================
# 例1: タスク管理システム - タスク情報の抽出
# ============================================

class Task(BaseModel):
    """タスクの構造化された情報"""
    title: str = Field(description="タスクのタイトル")
    priority: str = Field(description="優先度: high/medium/low")
    due_date: Optional[str] = Field(description="期限（YYYY-MM-DD形式）", default=None)
    assignee: Optional[str] = Field(description="担当者", default=None)
    description: str = Field(description="タスクの詳細説明")
    tags: List[str] = Field(description="関連するタグのリスト", default_factory=list)

async def extract_task_info():
    """テキストからタスク情報を抽出する例"""
    
    # タスク抽出エージェントの作成
    task_agent = Agent(
        name="Task Extractor",
        instructions=(
            "与えられたテキストからタスク情報を抽出してください。"
            "優先度は high, medium, low のいずれかで判断してください。"
            "日付はYYYY-MM-DD形式で出力してください。"
        ),
        model="o3-mini",
        output_type=Task  # Taskモデルの形式で出力
    )
    
    # サンプルテキスト
    input_text = """
    明日までに山田さんに新しいプレゼン資料を作成してもらう必要があります。
    これは重要なクライアント向けの提案資料で、デザインとコンテンツの両方を
    含める必要があります。マーケティングチームと連携してください。
    """
    
    # エージェントの実行
    result = await Runner.run(task_agent, input_text)
    
    print("=== タスク情報抽出 ===")
    print(f"タイトル: {result.final_output.title}")
    print(f"優先度: {result.final_output.priority}")
    print(f"期限: {result.final_output.due_date}")
    print(f"担当者: {result.final_output.assignee}")
    print(f"説明: {result.final_output.description}")
    print(f"タグ: {', '.join(result.final_output.tags)}")
    print()

# ============================================
# 例2: レストラン予約システム - 予約情報の構造化
# ============================================

class RestaurantReservation(BaseModel):
    """レストラン予約の構造化された情報"""
    customer_name: str = Field(description="予約者名")
    date: str = Field(description="予約日（YYYY-MM-DD形式）")
    time: str = Field(description="予約時間（HH:MM形式）")
    party_size: int = Field(description="人数")
    special_requests: List[str] = Field(
        description="特別なリクエスト（アレルギー、記念日など）",
        default_factory=list
    )
    contact_phone: Optional[str] = Field(description="連絡先電話番号", default=None)
    
async def process_reservation():
    """予約リクエストを構造化する例"""
    
    # 予約処理エージェントの作成
    reservation_agent = Agent(
        name="Reservation Processor",
        instructions=(
            "お客様の予約リクエストから予約情報を抽出してください。"
            "日付と時間は正確な形式で出力してください。"
            "特別なリクエストがあれば必ず記録してください。"
        ),
        model="o3-mini",
        output_type=RestaurantReservation
    )
    
    # サンプル予約リクエスト
    reservation_request = """
    来週の土曜日の夜7時に4人で予約したいです。田中と申します。
    妻が小麦アレルギーなので、グルテンフリーのメニューをお願いします。
    また、結婚記念日なので、デザートプレートもお願いできますか？
    連絡先は090-1234-5678です。
    """
    
    # エージェントの実行
    result = await Runner.run(reservation_agent, reservation_request)
    
    print("=== レストラン予約情報 ===")
    print(f"予約者名: {result.final_output.customer_name}")
    print(f"予約日: {result.final_output.date}")
    print(f"予約時間: {result.final_output.time}")
    print(f"人数: {result.final_output.party_size}名")
    print(f"特別リクエスト: {', '.join(result.final_output.special_requests)}")
    print(f"連絡先: {result.final_output.contact_phone}")
    print()

# ============================================
# 例3: 製品レビュー分析システム
# ============================================

class ProductReview(BaseModel):
    """製品レビューの構造化された分析結果"""
    overall_sentiment: str = Field(
        description="全体的な感情（positive/neutral/negative）"
    )
    rating: float = Field(
        description="推定評価（1.0-5.0）",
        ge=1.0,
        le=5.0
    )
    pros: List[str] = Field(
        description="良い点のリスト",
        default_factory=list
    )
    cons: List[str] = Field(
        description="改善点のリスト",
        default_factory=list
    )
    summary: str = Field(description="レビューの要約（50文字以内）")
    recommended: bool = Field(description="推奨するかどうか")

async def analyze_review():
    """製品レビューを分析する例"""
    
    # レビュー分析エージェントの作成
    review_agent = Agent(
        name="Review Analyzer",
        instructions=(
            "製品レビューを分析して、構造化された情報を抽出してください。"
            "感情分析を行い、良い点と改善点を明確に分けてください。"
            "評価は1.0から5.0の範囲で推定してください。"
            "要約は簡潔に50文字以内でまとめてください。"
        ),
        model="o3-mini",
        output_type=ProductReview
    )
    
    # サンプルレビュー
    product_review = """
    このワイヤレスイヤホンを1ヶ月使ってみました。
    音質は価格を考えると素晴らしく、特に低音がしっかりしています。
    バッテリー持続時間も公称通り8時間は持ちます。
    ただ、装着感が少し緩く、運動中は外れそうになることがあります。
    また、ケースが少し大きめでポケットに入れると膨らみます。
    総合的には満足していて、コスパは良いと思います。
    """
    
    # エージェントの実行
    result = await Runner.run(review_agent, product_review)
    
    print("=== 製品レビュー分析 ===")
    print(f"全体的な感情: {result.final_output.overall_sentiment}")
    print(f"評価: {result.final_output.rating}/5.0")
    print(f"良い点: {', '.join(result.final_output.pros)}")
    print(f"改善点: {', '.join(result.final_output.cons)}")
    print(f"要約: {result.final_output.summary}")
    print(f"推奨: {'はい' if result.final_output.recommended else 'いいえ'}")
    print()

# ============================================
# 例4: 複数の出力タイプを使った会話型エージェント
# ============================================

class MeetingInfo(BaseModel):
    """会議情報の構造"""
    title: str
    date: str
    participants: List[str]
    agenda: List[str]
    duration_minutes: int

class EmailDraft(BaseModel):
    """メールの下書き構造"""
    to: List[str]
    cc: List[str] = Field(default_factory=list)
    subject: str
    body: str
    priority: str = Field(default="normal")

async def multi_output_example():
    """異なる出力タイプを持つエージェントの例"""
    
    # 会議情報抽出エージェント
    meeting_agent = Agent(
        name="Meeting Organizer",
        instructions="会議の詳細を構造化された形式で整理してください。",
        model="o3-mini",
        output_type=MeetingInfo
    )
    
    # メール作成エージェント
    email_agent = Agent(
        name="Email Composer",
        instructions="ビジネスメールの下書きを作成してください。",
        model="o3-mini",
        output_type=EmailDraft
    )
    
    # 会議情報の抽出
    meeting_text = """
    来週月曜日の午後2時から営業戦略会議を行います。
    参加者は山田部長、佐藤さん、鈴木さんです。
    議題は第3四半期の売上レビューと新商品のマーケティング戦略です。
    約90分を予定しています。
    """
    
    meeting_result = await Runner.run(meeting_agent, meeting_text)
    
    print("=== 会議情報 ===")
    print(f"タイトル: {meeting_result.final_output.title}")
    print(f"日付: {meeting_result.final_output.date}")
    print(f"参加者: {', '.join(meeting_result.final_output.participants)}")
    print(f"議題: ")
    for item in meeting_result.final_output.agenda:
        print(f"  - {item}")
    print(f"所要時間: {meeting_result.final_output.duration_minutes}分")
    print()
    
    # メール作成
    email_request = """
    田中様と佐藤様に、明日の打ち合わせの確認メールを送ってください。
    CCに山田部長も入れてください。緊急度は高いです。
    """
    
    email_result = await Runner.run(email_agent, email_request)
    
    print("=== メール下書き ===")
    print(f"宛先: {', '.join(email_result.final_output.to)}")
    print(f"CC: {', '.join(email_result.final_output.cc)}")
    print(f"件名: {email_result.final_output.subject}")
    print(f"優先度: {email_result.final_output.priority}")
    print(f"本文:\n{email_result.final_output.body}")
    print()

# ============================================
# メイン実行関数
# ============================================

async def main():
    """すべての例を実行"""
    print("OpenAI Agents SDK - Output Type サンプルプログラム")
    print("=" * 50)
    print()
    
    # 各例を順番に実行
    await extract_task_info()
    await process_reservation()
    await analyze_review()
    await multi_output_example()
    
    print("=" * 50)
    print("すべてのサンプルの実行が完了しました！")

# プログラムの実行
if __name__ == "__main__":
    asyncio.run(main())