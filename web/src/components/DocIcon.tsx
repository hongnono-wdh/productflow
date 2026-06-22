// Artifact doc-type icon (ported verbatim from console.html docIco).
const FILE = (
  <>
    <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
    <path d="M14 2v5h5" />
  </>
)
const PATHS: Record<string, React.ReactNode> = {
  md: (
    <>
      {FILE}
      <path d="M8.5 13h7M8.5 16.5h4" />
    </>
  ),
  html: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
    </>
  ),
  code: <path d="m9 8-4 4 4 4M15 8l4 4-4 4" />,
  json: FILE,
  mindmap: (
    <>
      <circle cx="12" cy="5" r="2.4" />
      <circle cx="5.5" cy="18" r="2.4" />
      <circle cx="18.5" cy="18" r="2.4" />
      <path d="M12 7.4v3.6M12 11 6.5 15.8M12 11l5.5 4.8" />
    </>
  ),
}
export function DocIcon({ type }: { type: string }) {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
      {PATHS[type] || FILE}
    </svg>
  )
}
