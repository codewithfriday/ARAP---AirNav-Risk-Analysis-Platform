import { useState } from 'react'
import { Button, Card, Form, Input, Alert, Typography } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { useAuth } from '../store'

export default function Login() {
  const { t } = useTranslation()
  const setToken = useAuth((s) => s.setToken)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (v: { username: string; password: string }) => {
    setBusy(true)
    setErr(null)
    try {
      const r = await api.login(v.username, v.password)
      setToken(r.access_token)
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100%', display: 'grid', placeItems: 'center', background: 'linear-gradient(135deg,#16324A 0%,#1F3A5F 55%,#2A7F8E 100%)', padding: 16 }}>
      <Card style={{ width: 380, maxWidth: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <img src="/favicon.svg" width={48} height={48} alt="" />
          <Typography.Title level={3} style={{ margin: '8px 0 0', color: '#1F3A5F' }}>{t('login.title')}</Typography.Title>
          <Typography.Text type="secondary">{t('login.subtitle')}</Typography.Text>
        </div>
        {err && <Alert type="error" title={err} style={{ marginBottom: 12 }} />}
        <Form layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item name="username" label={t('login.username')} rules={[{ required: true }]}>
            <Input prefix={<UserOutlined />} autoFocus autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label={t('login.password')} rules={[{ required: true }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>{t('login.submit')}</Button>
        </Form>
      </Card>
    </div>
  )
}
