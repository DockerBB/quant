import { useState, useMemo } from 'react';
import { Card, Table, Tag, Select, Input, Row, Col, Statistic, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { useStrategyList, useCurrentSignals } from '@/hooks/useStrategyApi';
import { useStockNameMap, useStockSectorMap } from '@/hooks/useStockNames';
import type { Signal } from '@/types';

export default function ScreeningResults() {
  const { data: strategies } = useStrategyList();
  const navigate = useNavigate();
  const activeId = (strategies?.find((s: Record<string, unknown>) => s.is_active)?.id || '') as string;
  const [strategyId, setStrategyId] = useState<string>(activeId);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const { data: signalData, isLoading } = useCurrentSignals(strategyId);
  const nameMap = useStockNameMap();
  const sectorMap = useStockSectorMap();

  const allSignals = useMemo(() => {
    if (!signalData) return [];
    const { buys, sells, holds } = signalData as { buys: Signal[]; sells: Signal[]; holds: Signal[] };
    return [...(buys || []), ...(sells || []), ...(holds || [])];
  }, [signalData]);

  const filteredSignals = useMemo(() => {
    let data = allSignals;
    if (filter !== 'all') data = data.filter((s) => s.signal_type === filter);
    if (search) data = data.filter((s) => {
      const name = nameMap[s.ts_code] || '';
      return s.ts_code.includes(search) || name.includes(search);
    });
    return data.sort((a, b) => (b.score || 0) - (a.score || 0));
  }, [allSignals, filter, search, nameMap]);

  const buys = allSignals.filter((s) => s.signal_type === 'buy');

  // Sector distribution for chart
  const sectorCounts = useMemo(() => {
    const map: Record<string, number> = {};
    buys.forEach((s) => {
      const sec = sectorMap[s.ts_code] || '其他';
      map[sec] = (map[sec] || 0) + 1;
    });
    return map;
  }, [buys, sectorMap]);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col><Statistic title="买入信号" value={buys.length} valueStyle={{ color: '#cf1322' }} /></Col>
        <Col><Statistic title="卖出信号" value={allSignals.filter((s) => s.signal_type === 'sell').length} valueStyle={{ color: '#3f8600' }} /></Col>
        <Col><Statistic title="总信号" value={allSignals.length} /></Col>
      </Row>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="选择策略"
          style={{ width: 240 }}
          value={strategyId || undefined}
          onChange={setStrategyId}
          options={strategies?.map((s: Record<string, unknown>) => ({ label: s.name as string, value: s.id as string })) || []}
        />
        <Select value={filter} onChange={setFilter} style={{ width: 120 }}
          options={[{ label: '全部', value: 'all' }, { label: '买入', value: 'buy' }, { label: '卖出', value: 'sell' }, { label: '持有', value: 'hold' }]}
        />
        <Input prefix={<SearchOutlined />} placeholder="搜索代码/名称" value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 200 }} />
      </Space>

      <Row gutter={16}>
        <Col xs={24} lg={18}>
          <Table
            dataSource={filteredSignals}
            rowKey="ts_code"
            loading={isLoading}
            size="small"
            pagination={{ pageSize: 20 }}
            onRow={(record) => ({ onClick: () => navigate(`/signal/${record.ts_code}`), style: { cursor: 'pointer' } })}
            columns={[
              {
                title: '类型', dataIndex: 'signal_type', width: 60,
                render: (t: string) => <Tag color={t === 'buy' ? 'red' : t === 'sell' ? 'green' : 'default'}>{t}</Tag>,
              },
              { title: '代码', dataIndex: 'ts_code', width: 100 },
              { title: '名称', dataIndex: 'ts_code', width: 100, render: (c: string) => nameMap[c] || '-' },
              { title: '综合得分', dataIndex: 'score', width: 110, render: (v: number) => v?.toFixed(4), sorter: (a: Signal, b: Signal) => (a.score || 0) - (b.score || 0) },
              { title: '排名', dataIndex: 'percentile', width: 90, render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
              { title: '日期', dataIndex: 'date', width: 110 },
            ]}
          />
        </Col>
        <Col xs={24} lg={6}>
          <Card title="买入信号板块分布" size="small">
            <ReactECharts
              style={{ height: 280 }}
              option={{
                tooltip: { trigger: 'item' },
                series: [{
                  type: 'pie', radius: ['40%', '70%'],
                  data: Object.entries(sectorCounts).map(([name, value]) => ({ name, value })),
                  label: { formatter: '{b}\n{d}%' },
                }],
              }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
