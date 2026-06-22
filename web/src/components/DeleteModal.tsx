// Delete modal: two-tier — soft remove (keeps disk files) vs hard delete (gated on exact-name typing).
import { useState } from 'react'
import { useDelTarget, closeDelete, toast } from '../store'
import { IcX } from '../icons'

export function DeleteModal() {
  const t = useDelTarget()
  const [confirm, setConfirm] = useState('')
  if (!t) return null
  const close = () => {
    setConfirm('')
    closeDelete()
  }
  const removeProject = async () => {
    try {
      await fetch('/api/project-remove', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: t.id }) })
    } catch {
      /* noop */
    }
    toast('已从操作台移除（文件保留）')
    close()
  }
  const hardDelete = async () => {
    if (confirm.trim() !== t.name) return
    try {
      const r = await fetch('/api/project-delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: t.id }) })
      const d = await r.json()
      toast(d.ok ? '项目已彻底删除' : '删除失败：' + (d.error || '未知'))
    } catch {
      toast('删除失败')
    }
    close()
  }
  const ok = confirm.trim() === t.name
  return (
    <div className="modal show" id="del-modal" onClick={(e) => { if (e.target === e.currentTarget) close() }}>
      <div className="box" style={{ maxWidth: 500 }}>
        <div className="bar">
          <span className="mt">删除项目</span>
          <span className="x" onClick={close}>
            <IcX /> 关闭
          </span>
        </div>
        <div id="del-body" style={{ overflow: 'auto', padding: '22px 24px 24px' }}>
          <div style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: 18 }}>
            项目「<b>{t.name}</b>」 <span className="mono" style={{ color: 'var(--dim)', fontSize: 12 }}>{t.dir}</span>
          </div>
          <div style={{ background: 'var(--fill)', borderRadius: 12, padding: 16, marginBottom: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>从操作台移除</div>
            <div className="wz-hint2" style={{ margin: '4px 0 12px' }}>只把卡片从这里移除，<b>磁盘文件保留</b>（之后重新 init 可找回）。</div>
            <button className="btn ghost" onClick={removeProject}>从操作台移除</button>
          </div>
          <div style={{ border: '1px solid #f0d2d2', borderRadius: 12, padding: 16, background: '#fdf6f6' }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: '#c0392b' }}>彻底删除（不可恢复）</div>
            <div className="wz-hint2" style={{ margin: '4px 0 12px' }}>连同磁盘文件夹一起删，<b>含你的产品代码</b>。请输入项目名「{t.name}」确认：</div>
            <input className="wz-input" id="del-confirm" placeholder="输入项目名确认" value={confirm} onChange={(e) => setConfirm(e.target.value)} style={{ marginBottom: 12 }} />
            <button className="btn" id="del-hard-btn" disabled={!ok} style={{ background: ok ? '#c0392b' : 'var(--dash)', cursor: ok ? 'pointer' : 'not-allowed' }} onClick={hardDelete}>
              彻底删除
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
