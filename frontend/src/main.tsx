import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// 开发环境不使用 StrictMode：ECharts 与 React 19 双挂载会导致 DOM 节点错位
createRoot(document.getElementById('root')!).render(<App />)
