"""
ResearchBot Package Main Entry Point
"""

import asyncio
from .manager import ResearchManager

async def main() -> None:
    """メイン関数"""
    try:
        query = input("何を研究したいですか? ")
        if not query.strip():
            print("クエリが入力されていません。")
            return
        
        await ResearchManager().run(query)
    except KeyboardInterrupt:
        print("\n\nプログラムが中断されました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
