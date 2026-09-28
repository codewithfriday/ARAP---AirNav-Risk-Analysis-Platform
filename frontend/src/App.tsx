import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom'
import { Layout, Menu, Dropdown, Avatar, Space, Segmented, Spin, Typography } from 'antd'
import {
  DashboardOutlined, FolderOpenOutlined, WarningOutlined, CheckSquareOutlined, TableOutlined, TeamOutlined,
  AuditOutlined, LogoutOutlined, UserOutlined, BookOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useAuth, isAdmin } from './store'
import { api } from './api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import AssessmentDetail from './pages/AssessmentDetail'
import StudyPage from './pages/StudyPage'
import HazardLog from './pages/HazardLog'
import Actions from './pages/Actions'
import RiskSchemePage from './pages/RiskScheme'
import Users from './pages/Users'
import Audit from './pages/Audit'
import Guide from './pages/Guide'

const { Sider, Header, Content } = Layout

export default function App() {
  const { token, user, setUser, logout } = useAuth()
  const [loading, setLoading] = useState(false)
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const loc = useLocation()

  useEffect(() => {
    if (token && !user) {
      setLoading(true)
      api.get('/auth/me').then(setUser).catch(() => logout()).finally(() => setLoading(false))
    }
  }, [token, user, setUser, logout])

  if (!token) return <Login />
  if (!user || loading) return <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}><Spin size="large" /></div>

  const items = [
    { key: '/', icon: <DashboardOutlined />, label: t('nav.dashboard') },
    { key: '/projects', icon: <FolderOpenOutlined />, label: t('nav.projects') },
    { key: '/hazards', icon: <WarningOutlined />, label: t('nav.hazards') },
    { key: '/actions', icon: <CheckSquareOutlined />, label: t('nav.actions') },
    { key: '/scheme', icon: <TableOutlined />, label: t('nav.scheme') },
    ...(isAdmin(user) ? [{ key: '/users', icon: <TeamOutlined />, label: t('nav.users') }] : []),
    ...(['admin', 'reviewer'].includes(user.role) ? [{ key: '/audit', icon: <AuditOutlined />, label: t('nav.audit') }] : []),
    { key: '/guide', icon: <BookOutlined />, label: t('nav.guide') },
  ]
  const sel = items.map((i) => i.key).filter((k) => (k === '/' ? loc.pathname === '/' : loc.pathname.startsWith(k)))
  const selected = sel.length ? [sel[sel.length - 1]] : loc.pathname.startsWith('/assessments') || loc.pathname.startsWith('/studies') ? ['/projects'] : []

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={236} breakpoint="lg" collapsedWidth={64}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '18px 18px 14px', color: '#fff' }}>
          <img src="/favicon.svg" width={30} height={30} alt="" />
          <div style={{ lineHeight: 1.15 }}>
            <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: 0.5 }}>ARAP</div>
            <div style={{ fontSize: 10.5, opacity: 0.75 }}>AirNav Risk Analysis Platform</div>
          </div>
        </Link>
        <Menu theme="dark" mode="inline" selectedKeys={selected} items={items} onClick={(e) => nav(e.key)} />
      </Sider>
      <Layout>
        <Header style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16, borderBottom: '1px solid #e5e7eb', paddingInline: 20 }}>
          <Segmented size="small" value={i18n.language} options={[{ label: 'EN', value: 'en' }, { label: 'ID', value: 'id' }]}
            onChange={(v) => { i18n.changeLanguage(String(v)); try { localStorage.setItem('arap_lang', String(v)) } catch { /* ignore */ } }} />
          <Dropdown menu={{ items: [{ key: 'out', icon: <LogoutOutlined />, label: t('common.logout'), onClick: () => { logout(); nav('/') } }] }}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ background: '#2A7F8E' }} />
              <span>{user.full_name || user.username}</span>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{user.role}</Typography.Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/assessments/:id" element={<AssessmentDetail />} />
            <Route path="/studies/:id" element={<StudyPage />} />
            <Route path="/hazards" element={<HazardLog />} />
            <Route path="/actions" element={<Actions />} />
            <Route path="/scheme" element={<RiskSchemePage />} />
            <Route path="/users" element={<Users />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/guide" element={<Guide />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}
