import { Card, Col, Row, Statistic, Table, Tag, Spin, Alert } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useStrategyList, useCurrentSignals, useSignalSummary } from '@/hooks/useStrategyApi';
import { useDataStatus } from '@/hooks/useDataApi';
import { useFactorList } from '@/hooks/useFactorApi';
import { useStockNameMap } from '@/hooks/useStockNames';
import type { Signal } from '@/types';

export default function Dashboard() {
  const { data: strategies, isLoading: sLoading } = useStrategyList();
  const { data: dataStatus, isLoading: dLoading } = useDataStatus();
  const { data: factors, isLoading: fLoading } = useFactorList();

  const activeStrategy = strategies?.find((s: Record<string, unknown>) => s.is_active) as Record<string, unknown> | undefined;
  const strategyId = activeStrategy?.id as string | undefined;
  const { data: summary } = useSignalSummary(strategyId || '');
  const { data: currentSignals } = useCurrentSignals(strategyId || '');
  const nameMap = useStockNameMap();

  if (sLoading || dLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const buyCount = summary?.buy_count || 0;
  const sellCount = summary?.sell_count || 0;

  const categoryMap: Record<string, string> = {};
  factors?.forEach((f: Record<string, unknown>) => { categoryMap[f.name as string] = f.category as string; });

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="活跃策略数" value={strategies?.filter((s: Record<string, unknown>) => s.is_active).length || 0} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日买入信号" value={buyCount} valueStyle={{ color: '#cf1322' }} prefix={<ArrowUpOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日卖出信号" value={sellCount} valueStyle={{ color: '#3f8600' }} prefix={<ArrowDownOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="因子总数" value={factors?.length || 0} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card title="因子分布">
            {fLoading ? <Spin /> : (
              <ReactECharts
                style={{ height: 300 }}
                option={{
                  tooltip: { trigger: 'axis' },
                  legend: { bottom: 0 },
                  radar: {
                    indicator: factors?.slice(0, 8).map((f: Record<string, unknown>) => ({
                      name: f.name as string, max: 1,
                    })) || [],
                  },
                  series: [{ type: 'radar', data: [{ value: new Array(8).fill(0.5), name: '参考' }] }],
                }}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="数据状态">
            {dLoading ? <Spin /> : Object.entries(dataStatus || {}).map(([key, val]: [string, unknown]) => (
              <Tag key={key} color={(val as Record<string, unknown>).status === 'healthy' ? 'green' : 'orange'} style={{ margin: 4 }}>
                {key}: {(val as Record<string, unknown>).last_updated || '暂无'}
              </Tag>
            ))}
          </Card>
        </Col>
      </Row>

      <Card title="最近买入信号" style={{ marginTop: 16 }}>
        <Table
          dataSource={(currentSignals?.buys || []).slice(0, 10) as Signal[]}
          rowKey="ts_code"
          size="small"
          pagination={false}
          columns={[
            { title: '代码', dataIndex: 'ts_code', width: 100 },
            { title: '名称', dataIndex: 'ts_code', width: 100, render: (c: string) => nameMap[c] || c },
            { title: '类型', dataIndex: 'signal_type', width: 60, render: (t: string) => <Tag color={t === 'buy' ? 'red' : t === 'sell' ? 'green' : 'default'}>{t}</Tag> },
            { title: '得分', dataIndex: 'score', width: 100, render: (v: number) => v?.toFixed(4) },
            { title: '百分位', dataIndex: 'percentile', width: 100, render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
          ]}
        />
      </Card>
    </div>
  );
}
