// ⑥ 成品预览缩略图 → 点开进圈选 overlay. Driven by phase-6 image artifacts from `state`.
import { useChannel, openPreview } from '../store'
import { artUrl } from '../lib'
import type { StateChannel } from '../types'

export function PreviewSection() {
  const state = useChannel<StateChannel>('state')
  const ph = state?.phases.find((p) => p.id === 6)
  const imgs = ph ? ph.artifacts.filter((a) => a.type === 'image') : []
  if (!imgs.length) return null
  return (
    <div className="card">
      <h2>
        成品预览 <span className="hint">圈选有问题的区域提意见</span>
      </h2>
      <div className="wz-hint2" style={{ margin: '0 0 12px' }}>
        点开成品截图，拖拽框选有问题的区域并写一句，发给 Agent——它会知道「哪张图、哪块区域、什么问题」，比纯文字描述精准。
      </div>
      <div className="pv-thumbs">
        {imgs.map((a, i) => (
          <div key={i} className="pv-thumb" onClick={() => openPreview(a.file, a.title)}>
            <img src={artUrl(a.file)} loading="lazy" />
            <div className="cap">{a.title}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
