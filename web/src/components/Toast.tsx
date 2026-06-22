// Bottom-center toast pill, 2.2s auto-hide (matches old #toast behavior).
import { useEffect, useState } from 'react'
import { useToast } from '../store'

export function Toast() {
  const t = useToast()
  const [show, setShow] = useState(false)
  useEffect(() => {
    if (!t) return
    setShow(true)
    const timer = setTimeout(() => setShow(false), 2200)
    return () => clearTimeout(timer)
  }, [t])
  return (
    <div id="toast" className={show ? 'show' : ''}>
      {t?.msg ?? ''}
    </div>
  )
}
