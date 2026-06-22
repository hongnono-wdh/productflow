// Cross-stage 留言 drawer. Slide-in; Enter=send / Shift+Enter=newline; scroll-stick within 30px.
import { useEffect, useRef, useState } from 'react'
import { useChannel } from '../store'
import { post } from '../lib'
import { IcX } from '../icons'
import type { InboxPayload, InboxMessage } from '../types'

function MsgBody({ m }: { m: InboxMessage }) {
  if (m.type === 'canvas-feedback') {
    const nl = (m.liked || []).length
    const nc = (m.comments || []).length
    return (
      <>
        <div className="fb">
          📌 画布反馈：❤{nl} 张 · {nc} 条针对意见
        </div>
        {m.text.split('\n').map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </>
    )
  }
  if (m.type === 'preview-feedback') {
    return (
      <>
        <div className="fb">🖼 成品预览圈选：{(m.regions || []).length} 处意见</div>
        {m.text.split('\n').map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </>
    )
  }
  return <>{m.text}</>
}

export function ChatDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const inbox = useChannel<InboxPayload>('inbox')
  const messages = inbox?.messages || []
  const boxRef = useRef<HTMLDivElement>(null)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    const box = boxRef.current
    if (!box) return
    const stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 30
    if (stick) box.scrollTop = box.scrollHeight
  }, [messages])

  const send = () => {
    const text = draft.trim()
    if (!text) return
    post('/api/inbox', { text })
    setDraft('')
  }

  return (
    <div id="chat-drawer" className={open ? 'open' : ''}>
      <div className="card chat" style={{ height: '100%', border: 0, boxShadow: 'none', padding: 0 }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          给 Agent 留言
          <span style={{ marginLeft: 'auto', cursor: 'pointer', color: 'var(--dim)', fontSize: 13 }} onClick={onClose}>
            <IcX /> 收起
          </span>
        </h2>
        <div className="msgs" id="msgs" ref={boxRef}>
          {messages.length ? (
            messages.map((m, i) => (
              <div key={i} className={'msg ' + (m.from === 'agent' ? 'agent' : 'me')}>
                <MsgBody m={m} />
                <div className="ts">{m.ts}</div>
              </div>
            ))
          ) : (
            <div className="empty">还没有留言。</div>
          )}
        </div>
        <form
          id="chat-form"
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
        >
          <textarea
            id="chat-input"
            placeholder={'写下你的想法 / 修改意见…\nEnter 发送，Shift+Enter 换行'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
          />
          <button type="submit">发送</button>
        </form>
        <div className="note-txt">消息进入 Agent 收件箱，Agent 在每个检查点读取并回应。也可直接在 CLI 对话，两边状态同步。</div>
      </div>
    </div>
  )
}
