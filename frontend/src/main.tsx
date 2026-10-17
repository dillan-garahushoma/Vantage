import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { Toaster } from './components/ui/toast'
import { TooltipProvider } from './components/ui/tooltip'
import './index.css'

const container = document.getElementById('root')
if (!container) throw new Error('Root container #root was not found.')

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      {/* One tooltip delay for the whole product, and one place a success is
          announced. Both are mounted above the router so a route change cannot
          unmount them mid-interaction. */}
      <TooltipProvider delayDuration={200}>
        <App />
        <Toaster />
      </TooltipProvider>
    </BrowserRouter>
  </StrictMode>,
)
