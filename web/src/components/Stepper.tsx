// Top 8-stage stepper (数据驱动，随 state.phases 渲染). `.sel` (currently-viewed) is DECOUPLED from `.done`.
// Selected pill auto-scrolls into view (narrow screens). Responsive collapse is CSS (@1180px).
import { Fragment, useEffect, useRef } from 'react'
import type { StatePhase } from '../types'
import { IcCheck } from '../icons'

export function Stepper({ phases, selected, onSelect }: { phases: StatePhase[]; selected: number | null; onSelect: (id: number) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current?.querySelector('.step-pill.sel') as HTMLElement | null
    if (el) el.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [selected, phases])
  return (
    <div className="steps-bar" id="stepper" ref={ref}>
      {phases.map((p, i) => {
        const cls = 'step-pill' + (p.status === 'done' ? ' done' : '') + (p.id === selected ? ' sel' : '')
        return (
          <Fragment key={p.id}>
            <div className={cls} onClick={() => onSelect(p.id)}>
              <span className="num">{p.status === 'done' ? <IcCheck /> : i + 1}</span>
              <span className="lbl">{p.name}</span>
            </div>
            {i < phases.length - 1 && <span className="step-sep" />}
          </Fragment>
        )
      })}
    </div>
  )
}
