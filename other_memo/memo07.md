// app/page.tsx
import { Card, CardContent } from "@/components/ui/card"

type Device = {
  msn: string
  supplier: string
  destination: string
}

const devices: Device[] = [
  { msn: "C8D-1234-0001", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0002", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0003", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0004", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0005", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0006", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0007", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0008", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0009", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
  { msn: "C8D-1234-0010", supplier: "株式会社ダミー", destination: "株式会社ダミー - 請求部" },
]

export default function Page() {
  return (
    <main className="p-6 space-y-6">
      <Card className="p-4">
        <h1 className="text-2xl font-bold mb-2">検出情報</h1>
        <p className="text-gray-700">検査実施日: <span className="font-semibold">2025/9/12</span></p>
        <p className="text-gray-700">レンタル品型番キャスト検出: <span className="text-red-600 font-bold">未検出</span></p>
      </Card>

      <Card>
        <CardContent>
          <h2 className="text-xl font-bold mb-4">モバイル機器一覧</h2>
          <table className="min-w-full border border-gray-300 rounded-lg">
            <thead className="bg-gray-100">
              <tr>
                <th className="border px-4 py-2 text-left">MSN</th>
                <th className="border px-4 py-2 text-left">製造者</th>
                <th className="border px-4 py-2 text-left">設置先</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="border px-4 py-2">{device.msn}</td>
                  <td className="border px-4 py-2">{device.supplier}</td>
                  <td className="border px-4 py-2">{device.destination}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </main>
  )
}