// ⑥ 成品预览。两种呈现：
//  ① 当 ⑥ 截图带 pageId（P6-5 生产端已按 ④ 页面逐页截图）→「设计图 ↔ 实现图」按页并排对比 UI 还原度；
//     左＝④设计稿（只读参考，只能看、不能圈选/重绘），右＝⑥真实实现截图（可圈选提意见）。
//  ② 未关联页面的旧截图 / 尚无配对数据 → 沿用平铺缩略图（点开圈选）。
import { useChannel, openPreview, openArtifact } from '../store'
import { artUrl } from '../lib'
import type { StateChannel, PagesPayload, Artifact, Page } from '../types'

const IMG_RE = /\.(png|jpe?g|webp|gif|avif)$/i

// 设计图侧：只读——本身不圈选/重绘；点开进「设计↔实现」对比弹窗（或无实现图时单看设计大图）。
function DesignSide({ file, label, onClick }: { file?: string; label: string; onClick?: () => void }) {
  if (!file) return <div className="pv-ph">无设计稿</div>
  const isImg = IMG_RE.test(file)
  return (
    <div className="pv-side" onClick={onClick}>
      {isImg ? <img src={artUrl(file)} loading="lazy" /> : <div className="pv-ph pv-doc">🖹 打开设计稿</div>}
      <div className="cap">
        <span>{label}</span>
        <span className="pv-ro">只读</span>
      </div>
    </div>
  )
}

// 实现图侧：真实实现截图，点开进对比弹窗（左设计只读 + 右实现可圈选提意见）。
// 缺实现时区分：已显式豁免(implSkip) → 灰「本阶段不实现」；否则 → 红「未实现·待补」（提示漏页）。
function ImplSide({ art, label, onClick, skipReason }: { art?: Artifact; label: string; onClick?: () => void; skipReason?: string }) {
  if (!art) {
    return skipReason
      ? <div className="pv-ph" title={skipReason}>⏭ 本阶段不实现</div>
      : <div className="pv-ph pv-miss">未截图 / 未实现·待补</div>
  }
  return (
    <div className="pv-side" onClick={onClick}>
      <img src={artUrl(art.file, art.ts)} loading="lazy" />
      <div className="cap">
        <span>{art.title || label}</span>
      </div>
    </div>
  )
}

export function PreviewSection() {
  const state = useChannel<StateChannel>('state')
  const pagesP = useChannel<PagesPayload>('pages')
  const ph = state?.phases.find((p) => p.id === 6)
  const imgs: Artifact[] = ph ? ph.artifacts.filter((a) => a.type === 'image') : []
  if (!imgs.length) return null

  const pages: Page[] = pagesP?.pages || []
  const paired = imgs.filter((a) => a.pageId) // 带页面关联的实现图
  const loose = imgs.filter((a) => !a.pageId) // 未关联页面的旧截图

  // 配对分组：仅当 ⑥ 已有带 pageId 的实现截图（生产端升级后）才走对比视图，
  // 否则旧项目会满屏空占位——回退到平铺。
  const groups: { page: Page; rows: { platform: string; design?: string; impl?: Artifact }[] }[] = []
  if (paired.length) {
    for (const pg of pages) {
      const impls = paired.filter((a) => a.pageId === pg.id)
      const vers = (pg.versions || []).filter((v) => v.file)
      if (!impls.length && !vers.length) continue // 该页既无设计稿也无实现图
      // 每张实现图各出一行（不漏图，且同平台多实现——如 APP 下 iOS+Android——都露出），
      // 各自配同平台的 ④ 设计稿；有设计稿但该平台还没实现图 → 占位行（提示漏页）。
      const rows: { platform: string; design?: string; impl?: Artifact }[] = []
      const covered = new Set<string>()
      for (const a of impls) {
        const platform = a.platform || ''
        rows.push({ platform, design: vers.find((v) => (v.platform || '') === platform)?.file, impl: a })
        covered.add(platform)
      }
      for (const v of vers) {
        const platform = v.platform || ''
        if (!covered.has(platform)) rows.push({ platform, design: v.file, impl: undefined })
      }
      groups.push({ page: pg, rows })
    }
  }

  // 回退：无配对数据 → 现状平铺缩略图。
  if (!groups.length) {
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
              <img src={artUrl(a.file, a.ts)} loading="lazy" />
              <div className="cap">{a.title}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // 对比视图：设计图 ↔ 实现图，按 ④ 每个页面逐页并排。
  return (
    <div className="card">
      <h2>
        成品预览 <span className="hint">设计稿 ↔ 真实实现，按页面对比 UI 还原度</span>
      </h2>
      <div className="wz-hint2" style={{ margin: '0 0 12px' }}>
        左为 ④ 设计稿（只读参考，仅供对照），右为 ⑥ 真实实现截图。点实现图可拖拽框选有问题的区域提意见——Agent 会知道「哪页、哪块、什么问题」。
      </div>
      {groups.map((g) => (
        <div key={g.page.id} className="pv-group">
          <div className="pv-group-h">
            {g.page.name}
            {g.page.group ? <span className="pv-grp-tag"> · {g.page.group}</span> : null}
          </div>
          {g.rows.map((r, i) => {
            const suffix = r.platform ? `·${r.platform}` : ''
            const designTitle = `${g.page.name} 设计稿${suffix}`
            const implTitle = r.impl?.title || `${g.page.name} 实现${suffix}`
            const designIsImg = r.design ? IMG_RE.test(r.design) : false
            // 点开对比弹窗：有实现图 → 左设计（只读）↔ 右实现（可圈选）；无实现图 → 只看设计大图
            const open = () => {
              if (r.impl) openPreview(r.impl.file, implTitle, designIsImg ? r.design : undefined, designTitle)
              else if (r.design) openArtifact(artUrl(r.design), designTitle, designIsImg ? 'image' : 'html')
            }
            return (
              <div key={i} className="pv-pair">
                <DesignSide file={r.design} label={`设计稿${suffix}`} onClick={r.design ? open : undefined} />
                <div className="pv-vs">↔</div>
                <ImplSide art={r.impl} label={`实现${suffix}`} onClick={r.impl ? open : undefined} skipReason={g.page.implSkip} />
              </div>
            )
          })}
        </div>
      ))}
      {loose.length > 0 && (
        <>
          <div className="pv-group-h" style={{ marginTop: 18 }}>其它成品预览</div>
          <div className="pv-thumbs">
            {loose.map((a, i) => (
              <div key={i} className="pv-thumb" onClick={() => openPreview(a.file, a.title)}>
                <img src={artUrl(a.file, a.ts)} loading="lazy" />
                <div className="cap">{a.title}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
