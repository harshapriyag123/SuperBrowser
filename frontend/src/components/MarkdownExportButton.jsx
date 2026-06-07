import { useState } from 'react'
import { downloadMarkdownExport, hasMarkdownExportContent } from '../utils/exportMarkdown'

export function MarkdownExportButton({ mode, query, results }) {
const [exportError, setExportError] = useState(null)  
const canExport = hasMarkdownExportContent(mode, results)

  if (!canExport) return null

  return (
    <div className="flex flex-col items-start gap-2">
    <button
      type="button"
      onClick={() => {
        try {
          setExportError(null)
          downloadMarkdownExport({ mode, query, results })
        } catch (error) {
          console.error('Markdown export failed:', error)
          setExportError('Export failed. Please try again.')
        }
      }}
      className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] bg-white px-4 py-2 text-sm font-medium text-[var(--text-secondary)] shadow-sm transition-colors hover:border-[var(--action-primary)] hover:text-[var(--action-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--action-primary)] focus:ring-offset-2"
      aria-label={`Export ${mode === 'community' ? 'review summary' : 'AI answer'} as Markdown`}
    >
      Export Markdown
    </button>
     {exportError && (
        <p className="text-xs text-red-500 px-1" role="alert">
          {exportError}
        </p>
      )}
      </div>
  )
}
