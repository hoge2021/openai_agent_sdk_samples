// app/page.tsx
"use client"

import { useState } from "react"

export default function Page() {
  const [mailText, setMailText] = useState(`不足情報案内メール

お世話になっております。
ソフトバンク株式会社の田中でございます。

昨日、解約依頼のメールを確かに受領いたしました。
恐れ入りますが、以下の情報が不足しておりましたため、改めてご教示いただけますでしょうか。

【不足情報】
- レンタル返却キット送付先住所

お手数をおかけいたしますが、ご確認のほどよろしくお願い申し上げます。
`)

  const handleCopy = () => {
    navigator.clipboard.writeText(mailText)
    alert("コピーしました！")
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gray-50">
      <div className="w-full max-w-3xl">
        <div className="flex justify-between items-center mb-2">
          <h1 className="text-2xl font-bold">不足情報案内メール</h1>
          <button
            onClick={handleCopy}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md shadow"
          >
            コピー
          </button>
        </div>
        <textarea
          value={mailText}
          onChange={(e) => setMailText(e.target.value)}
          className="w-full h-96 border rounded-lg p-4 text-gray-800 bg-white shadow-sm resize-none overflow-y-scroll"
        />
      </div>
    </main>
  )
}