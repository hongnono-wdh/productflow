// 0-dependency external store. One Slice per WS channel → components subscribing
// to a channel only re-render when THAT channel pushes (= 局部渲染). Fed by the WS bus.
import { useSyncExternalStore } from 'react'

type Listener = () => void

class Slice<T> {
  private v: T
  private ls = new Set<Listener>()
  constructor(init: T) {
    this.v = init
  }
  get = (): T => this.v
  set = (nv: T): void => {
    this.v = nv
    this.ls.forEach((f) => f())
  }
  subscribe = (f: Listener): (() => void) => {
    this.ls.add(f)
    return () => {
      this.ls.delete(f)
    }
  }
}

const slices = new Map<string, Slice<unknown>>()
function slice(name: string): Slice<unknown> {
  let s = slices.get(name)
  if (!s) {
    s = new Slice<unknown>(null)
    slices.set(name, s)
  }
  return s
}

// Called by the WS bus on each {channel,data} frame.
export function dispatch(channel: string, data: unknown): void {
  slice(channel).set(data)
}

// Subscribe a component to one channel's latest payload (null until first push).
export function useChannel<T>(name: string): T | null {
  const s = slice(name)
  return useSyncExternalStore(s.subscribe, s.get) as T | null
}

// ── Toast (local UI state, not a WS channel) ──
interface ToastState {
  msg: string
  id: number
}
let _toastId = 0
const toastSlice = new Slice<ToastState | null>(null)
export function toast(msg: string): void {
  toastSlice.set({ msg, id: ++_toastId })
}
export function useToast(): ToastState | null {
  return useSyncExternalStore(toastSlice.subscribe, toastSlice.get)
}

// ── Modal (artifact preview / overview) ──
export type ModalState =
  | { kind: 'artifact'; url: string; title: string; type: string }
  | { kind: 'overview' }
  | null
const modalSlice = new Slice<ModalState>(null)
export function openArtifact(url: string, title: string, type: string): void {
  if (type === 'html') {
    window.open(url, '_blank')
    return
  }
  modalSlice.set({ kind: 'artifact', url, title, type })
}
export function openOverview(): void {
  modalSlice.set({ kind: 'overview' })
}
export function closeModal(): void {
  modalSlice.set(null)
}
export function useModal(): ModalState {
  return useSyncExternalStore(modalSlice.subscribe, modalSlice.get)
}

// ── Preview / redraw 圈选 overlay ──
export type PreviewState =
  | { mode: 'feedback'; file: string; title: string; designFile?: string; designTitle?: string }
  | { mode: 'redraw'; file: string; title: string; stage: number | null; pageId: string | null; platform: string }
  | null
const previewSlice = new Slice<PreviewState>(null)
// designFile/designTitle：④ 设计稿（只读对照）——传了则弹窗左右双栏「设计图 ↔ 实现图」放大对比，右侧实现图仍可圈选。
export function openPreview(file: string, title: string, designFile?: string, designTitle?: string): void {
  previewSlice.set({ mode: 'feedback', file, title: title || '成品预览', designFile, designTitle })
}
export function openRedraw(file: string, title: string, stage: number | null, pageId: string | null, platform: string): void {
  previewSlice.set({ mode: 'redraw', file, title: title || '设计稿', stage, pageId: pageId || null, platform: platform || '' })
}
export function closePreview(): void {
  previewSlice.set(null)
}
export function usePreview(): PreviewState {
  return useSyncExternalStore(previewSlice.subscribe, previewSlice.get)
}

// ── home modals: new-project wizard + delete ──
const newModalSlice = new Slice<boolean>(false)
export function openNewModal(): void {
  newModalSlice.set(true)
}
export function closeNewModal(): void {
  newModalSlice.set(false)
}
export function useNewModalOpen(): boolean {
  return !!useSyncExternalStore(newModalSlice.subscribe, newModalSlice.get)
}

export interface DelTarget {
  id: string
  name: string
  dir: string
}
const delSlice = new Slice<DelTarget | null>(null)
export function openDelete(t: DelTarget): void {
  delSlice.set(t)
}
export function closeDelete(): void {
  delSlice.set(null)
}
export function useDelTarget(): DelTarget | null {
  return useSyncExternalStore(delSlice.subscribe, delSlice.get)
}
