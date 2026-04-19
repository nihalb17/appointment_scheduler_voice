import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

/* StrictMode intentionally omitted: double mount/unmount breaks the voice WebSocket during CONNECTING
   ("closed before the connection is established") and confuses DevTools. */

createRoot(document.getElementById('root')).render(<App />)
