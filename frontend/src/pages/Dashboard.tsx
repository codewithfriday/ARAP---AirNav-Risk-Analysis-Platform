import { useQuery } from '@tanstack/react-query'
import { Card, Col, Row, Statistic, Tag, Spin, Empty } from 'antd'
import ReactECharts from 'echarts-for-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { useScheme, useMethods } from '../hooks'
import { RiskMatrix } from '../components/Risk'
import { PageHeader } from '../components/common'
import { METHOD_COLORS } from '../risk'

const EFF_COLORS: Record<string, string> = { 'very good': '#1F7A4D', good: '#3C8D5A', poor: '#D98E04', 'very poor': '#B23A3A', unknown: '#9CA3AF' }

export default function Dashboard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get('/dashboard') })
  const { data: scheme } = useScheme()
  const { data: methods } = useMethods()
  if (isLoading || !data) return <Spin />

  const regionBar = {
    grid: { left: 130, right: 30, top: 10, bottom: 24 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: data.regions.map((r: any) => r.name), inverse: true },
    series: [{ type: 'bar', barWidth: 18, data: data.regions.map((r: any) => ({ value: data.by_region[r.key], itemStyle: { color: r.color } })), label: { show: true, position: 'right' } }],
    tooltip: {},
  }
  const mKeys = Object.keys(data.studies_by_method)
  const methodBar = {
    grid: { left: 40, right: 16, top: 16, bottom: 60 },
    xAxis: { type: 'category', data: mKeys.map((k) => methods?.[k]?.name ?? k), axisLabel: { rotate: 35, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', data: mKeys.map((k) => ({ value: data.studies_by_method[k], itemStyle: { color: METHOD_COLORS[k] } })) }],
    tooltip: {},
  }
  const st = Object.entries(data.assessments_by_status).filter(([, v]) => (v as number) > 0)
  const statusPie = {
    tooltip: { trigger: 'item' }, legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{ type: 'pie', radius: ['45%', '70%'], center: ['50%', '42%'], label: { show: false }, data: st.map(([k, v]) => ({ name: k.replace('_', ' '), value: v })) }],
  }
  const eff = Object.entries(data.controls_by_effectiveness)
  const effPie = {
    tooltip: { trigger: 'item' }, legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{ type: 'pie', radius: ['45%', '70%'], center: ['50%', '42%'], label: { show: false },
      data: eff.map(([k, v]) => ({ name: k, value: v, itemStyle: { color: EFF_COLORS[k] ?? '#9CA3AF' } })) }],
  }

  return (
    <div>
      <PageHeader title={t('nav.dashboard')} sub="Organisation-wide safety risk picture from the NAVRAP hazard log." />
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card className="kpi"><Statistic title={t('dash.hazards')} value={data.hazards_total} /></Card></Col>
        <Col xs={12} lg={6}><Card className="kpi"><Statistic title={t('dash.overdue')} value={data.overdue_actions.length} styles={{ content: { color: data.overdue_actions.length ? '#B23A3A' : undefined } }} /></Card></Col>
        <Col xs={12} lg={6}><Card className="kpi"><Statistic title={t('dash.reviews')} value={data.reviews_due.length} /></Card></Col>
        <Col xs={12} lg={6}><Card className="kpi"><Statistic title={t('dash.inReview')} value={data.assessments_by_status.in_review ?? 0} /></Card></Col>

        <Col xs={24} xl={10}>
          <Card title={t('dash.matrix')} extra={<span className="muted small">count of hazards by current risk</span>}>
            <div style={{ overflowX: 'auto' }}><RiskMatrix scheme={scheme?.data} counts={data.matrix} size={52} /></div>
          </Card>
        </Col>
        <Col xs={24} xl={14}>
          <Card title={t('dash.byRegion')}><ReactECharts option={regionBar} style={{ height: 250 }} /></Card>
        </Col>
        <Col xs={24} lg={8}><Card title={t('dash.byStatus')}><ReactECharts option={statusPie} style={{ height: 260 }} /></Card></Col>
        <Col xs={24} lg={8}><Card title={t('dash.barriers')}><ReactECharts option={effPie} style={{ height: 260 }} /></Card></Col>
        <Col xs={24} lg={8}><Card title={t('dash.byMethod')}><ReactECharts option={methodBar} style={{ height: 260 }} /></Card></Col>

        <Col xs={24} lg={12}>
          <Card title={t('dash.overdue')}>
            {data.overdue_actions.length ? (
              data.overdue_actions.map((a: any) => (
                <div key={a.id} className="row-item">
                  <div><Link to="/actions"><b>{a.ref}</b> · {a.text}</Link><div className="muted small">{a.owner}</div></div>
                  <Tag color="red">due {a.due_date}</Tag>
                </div>))
            ) : <Empty description="No overdue actions" />}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('dash.reviews')}>
            {data.reviews_due.length ? (
              data.reviews_due.map((h: any) => (
                <div key={h.id} className="row-item">
                  <Link to={`/hazards?open=${h.id}`}>{h.ref} · {h.title}</Link>
                  <Tag color={new Date(h.review_date) < new Date() ? 'red' : 'gold'}>{h.review_date}</Tag>
                </div>))
            ) : <Empty description="No reviews due" />}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
