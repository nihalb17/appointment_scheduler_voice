import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import InternalDashboard from './components/InternalDashboard'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <InternalDashboard />
  </StrictMode>,
)
