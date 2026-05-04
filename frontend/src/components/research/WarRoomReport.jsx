import React from 'react'

// Splits the report body on ALL-CAPS section headers (e.g. "CORE THESIS:", "BEAR CASE:")
// Returns an array of { heading: string|null, body: string } segments.
function parseReportSections(text) {
  // Match lines that are entirely an ALL-CAPS label (with optional trailing colon/space)
  const headerRe = /^([A-Z][A-Z /()&+\-]{2,}[A-Z)])[\s:]*$/m
  const lines = text.split('\n')
  const segments = []
  let current = { heading: null, lines: [] }

  for (const line of lines) {
    if (headerRe.test(line.trim())) {
      if (current.lines.some(l => l.trim())) segments.push(current)
      current = { heading: line.trim().replace(/:$/, ''), lines: [] }
    } else {
      current.lines.push(line)
    }
  }
  if (current.lines.some(l => l.trim())) segments.push(current)

  return segments.map(s => ({ heading: s.heading, body: s.lines.join('\n').trim() }))
}

export default function WarRoomReport({ data }) {
  if (!data || !data.final_report) return null
  const isBuy = data.vote === 'YES'
  const sections = parseReportSections(data.final_report)

  return (
    <div className="bg-gradient-to-br from-teal-50 to-amber-50 border border-teal-200 rounded-lg p-6 mb-6">

      {/* Header row */}
      <div className="flex items-start justify-between mb-6">
        <h2 className="text-xl font-bold text-teal-900 leading-tight">
          Final Investment Verdict
          <span className="block text-sm font-normal text-teal-600 mt-0.5">War Room</span>
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 italic">AI-generated · cited</span>
          <div
            className={`px-4 py-2 rounded-full text-base font-bold ${
              isBuy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}
          >
            {isBuy ? 'BUY' : 'HOLD/AVOID'} · {data.confidence}%
          </div>
        </div>
      </div>

      {/* Report body — parsed into sections */}
      <div className="space-y-3">
        {sections.map((sec, i) => (
          <div key={i}>
            {sec.heading && (
              <p className="text-xs font-bold text-teal-800 uppercase tracking-wide mb-1">
                {sec.heading}
              </p>
            )}
            {sec.body && (
              <p className="text-sm text-gray-800 leading-relaxed">
                {sec.body}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Debate summary expander */}
      {data.debate_summary && (
        <details className="border-t border-teal-200 pt-4 mt-6">
          <summary className="text-sm font-semibold text-teal-700 cursor-pointer hover:text-teal-900">
            View Debate Summary
          </summary>
          <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
            {data.debate_summary}
          </p>
        </details>
      )}

      {/* Sources */}
      {data.citations && data.citations.length > 0 && (
        <div className="mt-4 border-t border-teal-100 pt-3">
          <span className="text-xs font-semibold text-teal-700 uppercase tracking-wide mr-2">
            Sources
          </span>
          <span className="text-xs text-gray-500">{data.citations.join(' · ')}</span>
        </div>
      )}
    </div>
  )
}
