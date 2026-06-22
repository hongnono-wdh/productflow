// Floating "Agent 待确认问题" cards (any stage). Option chips + free-text reply.
// Local input state = typing never interrupted by channel pushes (focus-guard solved by React).
import { useState } from 'react'
import { useChannel, toast } from '../store'
import { post } from '../lib'
import type { Choice, ChoicesPayload } from '../types'

function ChoiceCard({ c, onAnswer }: { c: Choice; onAnswer: (id: string, ans: string) => void }) {
  const [reply, setReply] = useState('')
  return (
    <div className="choice-card">
      <div className="cq">
        💬 Agent 在问你
        {c.stage ? (
          <span style={{ marginLeft: 'auto', fontWeight: 500, color: 'var(--dim)', fontSize: 12 }}>阶段 {c.stage}</span>
        ) : null}
      </div>
      <div className="cqt">{c.question}</div>
      <div className="copts">
        {(c.options || []).map((o) => (
          <span key={o} className="copt" onClick={() => onAnswer(c.id, o)}>
            {o}
          </span>
        ))}
      </div>
      <div className="crow">
        <input
          className="wz-input"
          placeholder="都不合适？这里填你的答复"
          style={{ maxWidth: 'none' }}
          value={reply}
          onChange={(e) => setReply(e.target.value)}
        />
        <button
          className="btn ghost"
          style={{ whiteSpace: 'nowrap' }}
          onClick={() => {
            const v = reply.trim()
            if (!v) {
              toast('填一下你的答复')
              return
            }
            onAnswer(c.id, v)
          }}
        >
          回复
        </button>
      </div>
    </div>
  )
}

export function ChoicesBar() {
  const data = useChannel<ChoicesPayload>('choices')
  const [answered, setAnswered] = useState<Set<string>>(new Set())
  const choices = (data?.choices || []).filter((c) => c.answer == null && !answered.has(c.id))
  const answer = (id: string, ans: string) => {
    setAnswered((s) => new Set(s).add(id)) // optimistic removal
    post('/api/choice', { id, answer: ans })
    toast('已回复 Agent：' + ans)
  }
  return (
    <div id="choices-bar" className={choices.length ? 'show' : ''}>
      {choices.map((c) => (
        <ChoiceCard key={c.id} c={c} onAnswer={answer} />
      ))}
    </div>
  )
}
