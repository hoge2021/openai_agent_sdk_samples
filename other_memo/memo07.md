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

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gray-50">
      <div className="w-full max-w-3xl">
        <h1 className="text-2xl font-bold mb-4">不足情報案内メール</h1>
        <textarea
          value={mailText}
          onChange={(e) => setMailText(e.target.value)}
          className="w-full h-96 border rounded-lg p-4 text-gray-800 bg-white shadow-sm resize-none overflow-y-scroll"
        />
      </div>
    </main>
  )
}