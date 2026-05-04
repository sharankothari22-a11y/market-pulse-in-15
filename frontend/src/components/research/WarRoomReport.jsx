import React from 'react'

export default function WarRoomReport({ data }) {
  if (!data || !data.final_report) return null
  const isBuy = data.vote === 'YES'
  return (
    <div className="bg-gradient-to-br from-teal-50 to-amber-50 border border-teal-200 rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-teal-900">Final Investment Verdict (War Room)</h2>
        <div
          className={`px-3 py-1 rounded-full text-sm font-bold ${
            isBuy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {isBuy ? 'BUY' : 'HOLD/AVOID'} · {data.confidence}% confidence
        </div>
      </div>
      <div className="prose prose-sm max-w-none">
        <p className="whitespace-pre-wrap text-gray-800 text-sm leading-relaxed">{data.final_report}</p>
      </div>
      {data.debate_summary && (
        <details className="mt-4">
          <summary className="text-sm font-semibold text-teal-700 cursor-pointer hover:text-teal-900">
            View Debate Summary
          </summary>
          <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{data.debate_summary}</p>
        </details>
      )}
      {data.citations && data.citations.length > 0 && (
        <div className="mt-4 text-xs text-gray-500 border-t border-teal-100 pt-3">
          Sources: {data.citations.join(' · ')}
        </div>
      )}
    </div>
  )
}
