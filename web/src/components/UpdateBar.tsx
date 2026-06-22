// Top update banner on both pages, driven by the `system` channel (update-check shape).
import { useState } from 'react'
import { useChannel } from '../store'
import type { SystemPayload } from '../types'

export function UpdateBar() {
  const sys = useChannel<SystemPayload>('system')
  const [msg, setMsg] = useState('')
  if (!sys || !sys.update_available) return null
  const doUpdate = () => {
    setMsg('更新中…（git pull + 数据迁移）')
    fetch('/api/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then((r) => r.json())
      .then((j) => {
        setMsg(j.ok ? `✓ 已更新到 v${j.version}，重启操作台后生效（重跑 /productflow-start）` : '更新失败：' + (j.hint || j.error || '未知错误'))
      })
      .catch(() => setMsg('更新失败：网络错误'))
  }
  return (
    <div id="update-bar">
      🆕 有新版本 <b>v{sys.latest}</b>（当前 v{sys.current}）
      {sys.git ? (
        <button className="btn sm" onClick={doUpdate}>
          立即更新
        </button>
      ) : (
        <span style={{ opacity: 0.85 }}>（git clone 安装才支持一键更新；或重装最新包）</span>
      )}
      <span id="update-msg">{msg}</span>
    </div>
  )
}
