// Persistent left sidebar (232 ⇄ 64). Collapse toggles body.collapsed class
// (CSS keys many selectors off it — same mechanism as the old console).
import { useChannel, toast } from '../store'
import type { SystemPayload } from '../types'
import { IcExpand, IcCollapse, IcGrid, IcAsset, IcSettings } from '../icons'

function toggleSidebar() {
  document.body.classList.toggle('collapsed')
}
function onLogoClick(e: React.MouseEvent) {
  // collapsed: click logo = expand (block nav to /); expanded: navigate home
  if (document.body.classList.contains('collapsed')) {
    e.preventDefault()
    toggleSidebar()
  }
}

async function checkUpdate() {
  try {
    const u = (await (await fetch('/api/update-check?refresh=1')).json()) as SystemPayload
    if (u.update_available) {
      if (u.git) {
        if (confirm(`有新版本 v${u.latest}（当前 v${u.current}）。现在更新？\n（git pull + 数据迁移；更新后需重启操作台生效。你的项目数据在 skill 之外、不受影响。）`)) {
          fetch('/api/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
            .then((r) => r.json())
            .then((j) => toast(j.ok ? `✓ 已更新到 v${j.version}，重启操作台后生效` : '更新失败：' + (j.hint || j.error || '未知错误')))
            .catch(() => toast('更新失败：网络错误'))
        }
      } else {
        alert(`有新版本 v${u.latest}（当前 v${u.current}）。\n当前不是 git 安装，不支持一键更新——请重装最新包，或在 CLI 跑 /productflow-update。`)
      }
    } else {
      toast(`已是最新 v${u.current}`)
    }
  } catch {
    toast('检查更新失败')
  }
}

export function Sidebar() {
  const sys = useChannel<SystemPayload>('system')
  const ver = sys?.current ? 'v' + sys.current : 'v…'
  return (
    <aside id="sidebar">
      <div className="sb-head">
        <a className="sb-logo" href="/" onClick={onLogoClick} title="ProductFlow 首页（收起时点此展开）">
          <span className="mark">
            <span className="mk-logo">P</span>
            <IcExpand />
          </span>
          <span className="name">
            ProductFlow<small>操作台</small>
          </span>
        </a>
        <button className="sb-collapse" onClick={toggleSidebar} title="收起侧边栏" aria-label="收起侧边栏">
          <IcCollapse />
        </button>
      </div>
      <nav className="sb-nav">
        <a href="/" id="nav-proj" className="on">
          <span className="ico">
            <IcGrid />
          </span>
          <span className="lbl">项目</span>
        </a>
        <a onClick={() => toast('资产库即将上线')}>
          <span className="ico">
            <IcAsset />
          </span>
          <span className="lbl">资产</span>
        </a>
        <a onClick={() => toast('设置即将上线')}>
          <span className="ico">
            <IcSettings />
          </span>
          <span className="lbl">设置</span>
        </a>
      </nav>
      <div className="sb-acct">
        <span className="av">P</span>
        <span className="meta">
          <b>ProductFlow</b>
          <br />
          <small>
            本地工作站 ·{' '}
            <span id="sb-ver" onClick={checkUpdate} title="点击检查更新" style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}>
              {ver}
            </span>
          </small>
        </span>
      </div>
    </aside>
  )
}
