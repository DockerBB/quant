import { useState } from 'react';
import { Card, Table, Tag, Select, Row, Col, Typography, Spin, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useFactorList, useFactorValues } from '@/hooks/useFactorApi';
import type { FactorMeta, FactorValue } from '@/types';

const categoryColors: Record<string, string> = {
  value: 'blue', momentum: 'orange', quality: 'green', growth: 'cyan',
  sentiment: 'purple', technical: 'magenta', risk: 'red',
};

export default function FactorManager() {
  const { data: factors, isLoading } = useFactorList();
  const [selected, setSelected] = useState<string>('');
  const { data: values, isLoading: vLoading } = useFactorValues(selected);

  const selectedFactor = factors?.find((f: FactorMeta) => f.name === selected);

  const chartOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: (values || []).slice(0, 30).map((v: FactorValue) => v.ts_code) },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: (values || []).slice(0, 30).map((v: FactorValue) => ({
        value: v.value,
        itemStyle: { color: v.value >= 0 ? '#cf1322' : '#3f8600' },
      })),
    }],
    grid: { left: '5%', right: '5%', bottom: '20%' },
    dataZoom: [{ type: 'inside' }],
  };

  return (
    <div>
      <Row gutter={16}>
        <Col xs={24} md={10}>
          <Card title="因子列表" size="small">
            <Table
              dataSource={factors || []}
              rowKey="name"
              loading={isLoading}
              size="small"
              pagination={false}
              scroll={{ y: 400 }}
              onRow={(record) => ({ onClick: () => setSelected(record.name), style: { cursor: 'pointer', background: selected === record.name ? '#e6f4ff' : undefined } })}
              columns={[
                { title: '因子名', dataIndex: 'name', width: 140 },
                {
                  title: '类别', dataIndex: 'category', width: 80,
                  render: (v: string) => <Tag color={categoryColors[v] || 'default'}>{v}</Tag>,
                },
                {
                  title: '方向', dataIndex: 'direction', width: 60,
                  render: (v: string) => v === 'positive' ? '↑' : '↓',
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title={selected ? `${selected} — ${selectedFactor?.description || ''}` : '选择一个因子'} size="small">
            {!selected ? <Empty description="点击左侧因子查看详情" /> :
              vLoading ? <Spin /> : (
                <>
                  <Typography.Paragraph type="secondary">
                    方向: {selectedFactor?.direction === 'positive' ? '正向(越高越好)' : '负向(越低越好)'}
                  </Typography.Paragraph>
                  <ReactECharts style={{ height: 300 }} option={chartOption} />
                  <Table
                    dataSource={values?.slice(0, 10) || []}
                    rowKey="ts_code"
                    size="small"
                    pagination={false}
                    style={{ marginTop: 12 }}
                    columns={[
                      { title: '代码', dataIndex: 'ts_code', width: 100 },
                      { title: '因子值', dataIndex: 'value', render: (v: number) => v?.toFixed(4) },
                    ]}
                  />
                </>
              )
            }
          </Card>
        </Col>
      </Row>
    </div>
  );
}
