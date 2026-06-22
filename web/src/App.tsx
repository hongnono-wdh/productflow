import { useEffect } from 'react'
import { IS_PROJECT } from './lib'
import { startBus } from './bus'
import { Sidebar } from './components/Sidebar'
import { Toast } from './components/Toast'
import { UpdateBar } from './components/UpdateBar'
import { Modal } from './components/Modal'
import { PreviewOverlay } from './components/PreviewOverlay'
import { NewProjectModal } from './components/NewProjectModal'
import { DeleteModal } from './components/DeleteModal'
import { Home } from './screens/Home'
import { Project } from './components/Project'

export function App() {
  useEffect(() => {
    document.title = IS_PROJECT ? 'ProductFlow · 操作台' : 'ProductFlow · 总览'
    startBus()
  }, [])
  return (
    <>
      <Sidebar />
      <div id="main">
        <UpdateBar />
        {IS_PROJECT ? <Project /> : <Home />}
      </div>
      <Modal />
      <PreviewOverlay />
      <NewProjectModal />
      <DeleteModal />
      <Toast />
    </>
  )
}
