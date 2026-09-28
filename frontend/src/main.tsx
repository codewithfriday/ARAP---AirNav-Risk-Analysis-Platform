import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, App as AntApp } from 'antd'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import '@xyflow/react/dist/style.css'
import './i18n'
import './index.css'
import App from './App'

ModuleRegistry.registerModules([AllCommunityModule])

const router = createBrowserRouter([{ path: '*', element: <App /> }])

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <ConfigProvider
        theme={{
          token: { colorPrimary: '#1F3A5F', colorInfo: '#2A7F8E', borderRadius: 6, fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif" },
          components: { Layout: { siderBg: '#16324A', headerBg: '#ffffff' }, Menu: { darkItemBg: '#16324A', darkSubMenuItemBg: '#16324A' } },
        }}
      >
        <AntApp>
          <RouterProvider router={router} />
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  </StrictMode>,
)
