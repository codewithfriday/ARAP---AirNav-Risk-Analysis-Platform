import { Card, Col, Row, Steps, Tag, Typography } from 'antd'
import { useMethods } from '../hooks'
import { PageHeader } from '../components/common'
import { METHOD_COLORS } from '../risk'

export default function Guide() {
  const { data: methods } = useMethods()
  return (
    <div>
      <PageHeader title="Quick guide" sub="The full user guide is in docs/USER_GUIDE.md (and USER_GUIDE.pdf) in the ARAP repository." />
      <Card title="Typical workflow" style={{ marginBottom: 16 }}>
        <Steps orientation="vertical" size="small" current={-1} items={[
          { title: 'Create a project for the change', content: 'Projects & assessments → New project. Record type of change, units and sponsor.' },
          { title: 'Create a safety assessment', content: 'Define scope, environment and assumptions (Manual §2.3).' },
          { title: 'Add method studies', content: 'ARAP suggests methods for the change type (Manual §4.1). Run each study in a workshop; the worksheet or diagram is the record.' },
          { title: 'Send hazards to the hazard log', content: 'Select worksheet rows (or the bowtie) and use “Send to hazard log”. Rate initial and residual risk with the matrix.' },
          { title: 'Raise actions', content: 'Actions have owners and due dates; closing requires evidence.' },
          { title: 'Submit, review, endorse, accept', content: 'Reviewer endorses; the authority for the worst residual risk region accepts. Accepted assessments are locked.' },
          { title: 'Export the Safety Assessment Report', content: 'Report (.docx) on the assessment page; keep monitoring through the dashboard.' },
        ]} />
      </Card>
      <Row gutter={[12, 12]}>
        {methods && Object.entries(methods).map(([k, m]: any) => (
          <Col xs={24} md={12} xl={8} key={k}>
            <Card size="small" title={<><Tag color={METHOD_COLORS[k]}>{m.kind}</Tag>{m.name}</>} extra={<span className="muted small">Manual ch. {m.chapter}</span>}>
              <Typography.Text>{m.summary}</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
