import { useState, useMemo } from 'react';
import { Card, AutoComplete, Input, Row, Col, Statistic, Tag, Spin, Descriptions, Typography, Empty, Alert, Select } from 'antd';
import { SearchOutlined, RiseOutlined, FallOutlined, MinusOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useStockList } from '@/hooks/useDataApi';
import { useDailyData } from '@/hooks/useDataApi';
import { useStockNameMap } from '@/hooks/useStockNames';
import { useCurrentSignals } from '@/hooks/useStrategyApi';
import { useStrategyList } from '@/hooks/useStrategyApi';

function calcRSI14(closes: number[]): number | null {
  if (closes.length < 15) return null;
  const period = 14;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gain += diff; else loss -= diff;
  }
  let avgGain = gain / period;
  let avgLoss = loss / period;
  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
    avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;
  }
  return avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
}

function getAdvice(signalType: string, score: number, percentile: number): { text: string; color: string; details: string[] } {
  if (signalType === 'buy') {
    const pct = (percentile * 100).toFixed(1);
    return {
      text: '强烈推荐买入',
      color: '#cf1322',
      details: [
        `综合得分排名全市场前 ${pct}%`,
        `策略综合评分 ${score.toFixed(2)}，显著优于市场平均水平`,
        '建议关注该股，结合仓位管理逐步建仓',
      ],
    };
  }
  if (signalType === 'sell') {
    return {
      text: '建议卖出/规避',
      color: '#3f8600',
      details: [
        `综合得分排名全市场后 ${((1 - percentile) * 100).toFixed(1)}%`,
        `策略综合评分 ${score.toFixed(2)}，基本面或技术面偏弱`,
        '建议减仓或暂时规避，等待基本面改善',
      ],
    };
  }
  return {
    text: '中性持有',
    color: '#faad14',
    details: [
      `综合得分处于市场中位数附近 (${(percentile * 100).toFixed(1)}%)`,
      `策略综合评分 ${score.toFixed(2)}`,
      '可继续持有观察，等待信号明确',
    ],
  };
}

export default function StockAdvisor() {
  const [search, setSearch] = useState('');
  const [tsCode, setTsCode] = useState('');
  const nameMap = useStockNameMap();
  const { data: strategies } = useStrategyList();
  const allActive = (strategies as Record<string, unknown>[])?.filter((s) => s.is_active) || [];
  const [strategyId, setStrategyId] = useState<string>(
    (allActive[0]?.id as string) || ''
  );
  const { data: signalData } = useCurrentSignals(strategyId);
  const { data: stocks } = useStockList();
  const { data: dailyData, isLoading: dLoading } = useDailyData(tsCode, '20240101');

  // Build search options
  const options = useMemo(() => {
    if (!stocks || !search) return [];
    const s = search.toLowerCase();
    return (stocks as Record<string, unknown>[])
      .filter((r) => {
        const code = (r.ts_code as string).toLowerCase();
        const name = ((r.name as string) || '').toLowerCase();
        return code.includes(s) || name.includes(s);
      })
      .slice(0, 20)
      .map((r) => ({
        value: `${r.ts_code} ${r.name}`,
        label: (
          <span>
            <Tag style={{ fontFamily: 'monospace' }}>{r.ts_code as string}</Tag>
            {r.name as string}
          </span>
        ),
        code: r.ts_code as string,
      }));
  }, [stocks, search]);

  // Find signal for this stock
  const signal = useMemo(() => {
    if (!signalData || !tsCode) return null;
    const all = [
      ...((signalData as Record<string, unknown>).buys as Record<string, unknown>[] || []),
      ...((signalData as Record<string, unknown>).sells as Record<string, unknown>[] || []),
      ...((signalData as Record<string, unknown>).holds as Record<string, unknown>[] || []),
    ];
    return all.find((s) => s.ts_code === tsCode) || null;
  }, [signalData, tsCode]);

  // Compute metrics from daily data
  const metrics = useMemo(() => {
    if (!dailyData || (dailyData as Record<string, unknown>[]).length < 20) return null;
    const d = dailyData as Record<string, unknown>[];
    const closes = d.map((r) => r.close as number);
    const vols = d.map((r) => (r.vol as number) || 0);
    const latest = d[d.length - 1];
    const rsi14 = calcRSI14(closes);

    // Momentum
    const mom1m = closes.length > 21 ? (closes[closes.length - 1] / closes[closes.length - 22] - 1) * 100 : null;
    const mom3m = closes.length > 63 ? (closes[closes.length - 1] / closes[closes.length - 64] - 1) * 100 : null;
    const mom6m = closes.length > 126 ? (closes[closes.length - 1] / closes[closes.length - 127] - 1) * 100 : null;

    // Avg volume last 5 days vs 20 days
    const vol5 = vols.slice(-5).reduce((a, b) => a + b, 0) / 5;
    const vol20 = vols.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const volRatio = vol20 > 0 ? vol5 / vol20 : 1;

    // Max drawdown in last 60 days
    let maxDD = 0, peak = closes[Math.max(0, closes.length - 60)];
    for (let i = Math.max(0, closes.length - 60); i < closes.length; i++) {
      if (closes[i] > peak) peak = closes[i];
      const dd = (peak - closes[i]) / peak;
      if (dd > maxDD) maxDD = dd;
    }

    return { latest, rsi14, mom1m, mom3m, mom6m, volRatio, maxDD, closes, vols };
  }, [dailyData]);

  const strategyName = useMemo(() => {
    const s = allActive.find((s: Record<string, unknown>) => s.id === strategyId);
    return (s?.name as string) || '';
  }, [allActive, strategyId]);

  const advice = useMemo(() => {
    if (!signal) return null;
    return getAdvice(
      signal.signal_type as string,
      signal.score as number,
      signal.percentile as number,
    );
  }, [signal]);

  const klineOption = useMemo(() => {
    if (!metrics || metrics.closes.length < 10) return {};
    const dates = (dailyData as Record<string, unknown>[]).slice(-120).map((d) => (d.trade_date as string).slice(4));
    const ohlc = (dailyData as Record<string, unknown>[]).slice(-120).map((d) => [d.open, d.close, d.low, d.high]);
    const vols = (dailyData as Record<string, unknown>[]).slice(-120).map((d, i) => {
      const prevClose = i > 0 ? (dailyData as Record<string, unknown>[]).slice(-120)[i - 1].close as number : (d.close as number);
      return { value: d.vol || 0, itemStyle: { color: (d.close as number) >= prevClose ? '#cf1322' : '#3f8600' } };
    });

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: [
        { left: '8%', right: '2%', top: 10, height: '55%' },
        { left: '8%', right: '2%', top: '72%', height: '15%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, splitLine: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { fontSize: 9, rotate: 0 }, splitLine: { show: false } },
      ],
      yAxis: [
        { type: 'value', scale: true, gridIndex: 0, splitLine: { lineStyle: { color: '#f5f5f5' } } },
        { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
      ],
      series: [
        {
          type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0, data: ohlc,
          itemStyle: { color: '#cf1322', color0: '#3f8600', borderColor: '#cf1322', borderColor0: '#3f8600' },
        },
        { type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: vols, name: '成交量' },
      ],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }],
    };
  }, [dailyData, metrics]);

  return (
    <div>
      <Select
        style={{ width: 280, marginBottom: 12, marginRight: 12 }}
        value={strategyId}
        onChange={setStrategyId}
        options={allActive.map((s: Record<string, unknown>) => ({
          label: s.name as string,
          value: s.id as string,
        }))}
      />
      <AutoComplete
        style={{ width: 400, marginBottom: 24 }}
        options={options}
        onSearch={setSearch}
        onSelect={(_, option) => {
          setTsCode((option as { code: string }).code);
          setSearch((option as { value: string }).value);
        }}
        value={search}
      >
        <Input prefix={<SearchOutlined />} placeholder="输入股票代码或名称，如 平安银行 或 000001" size="large" />
      </AutoComplete>

      {!tsCode && <Empty description="搜索股票查看投资建议" />}

      {tsCode && dLoading && <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />}

      {tsCode && signal && advice && metrics && (
        <>
          <Alert
            type={signal.signal_type === 'buy' ? 'success' : signal.signal_type === 'sell' ? 'error' : 'warning'}
            message={
              <span style={{ fontSize: 18, fontWeight: 'bold' }}>
                [{strategyName}] {advice.text}
                {signal.signal_type === 'buy' ? <RiseOutlined /> : signal.signal_type === 'sell' ? <FallOutlined /> : <MinusOutlined />}
              </span>
            }
            description={
              <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                {advice.details.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            }
            style={{ marginBottom: 16 }}
          />

          <Row gutter={[16, 16]}>
            <Col span={4}>
              <Card size="small"><Statistic title="最新价" value={metrics.latest.close as number} precision={2} /></Card>
            </Col>
            <Col span={4}>
              <Card size="small">
                <Statistic
                  title="综合得分" value={signal.score as number} precision={2}
                  valueStyle={{ color: (signal.score as number) > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small">
                <Statistic title="全市场排名" value={`${((signal.percentile as number) * 100).toFixed(1)}%`} />
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small"><Statistic title="RSI(14)" value={metrics.rsi14?.toFixed(1) || '-'} /></Card>
            </Col>
            <Col span={4}>
              <Card size="small">
                <Statistic
                  title="1月动量" value={metrics.mom1m != null ? `${metrics.mom1m.toFixed(1)}%` : '-'}
                  valueStyle={{ color: (metrics.mom1m || 0) > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small">
                <Statistic
                  title="3月动量" value={metrics.mom3m != null ? `${metrics.mom3m.toFixed(1)}%` : '-'}
                  valueStyle={{ color: (metrics.mom3m || 0) > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}>
              <Statistic title="6月动量" value={metrics.mom6m != null ? `${metrics.mom6m.toFixed(1)}%` : '-'}
                valueStyle={{ color: (metrics.mom6m || 0) > 0 ? '#cf1322' : '#3f8600' }} />
            </Col>
            <Col span={6}>
              <Statistic title="量比(5/20日)" value={metrics.volRatio.toFixed(2)}
                valueStyle={{ color: metrics.volRatio > 1.2 ? '#cf1322' : metrics.volRatio < 0.8 ? '#3f8600' : undefined }} />
            </Col>
            <Col span={6}>
              <Statistic title="60日最大回撤" value={`${(metrics.maxDD * 100).toFixed(1)}%`}
                valueStyle={{ color: metrics.maxDD > 0.2 ? '#cf1322' : '#3f8600' }} />
            </Col>
          </Row>

          <Card title="近期走势" style={{ marginTop: 16 }}>
            <ReactECharts style={{ height: 350 }} option={klineOption} />
          </Card>

          <Card title="股票信息" style={{ marginTop: 16 }}>
            <Descriptions column={3} size="small" bordered>
              <Descriptions.Item label="代码">{tsCode}</Descriptions.Item>
              <Descriptions.Item label="名称">{nameMap[tsCode] || '-'}</Descriptions.Item>
              <Descriptions.Item label="信号类型">
                <Tag color={signal.signal_type === 'buy' ? 'red' : signal.signal_type === 'sell' ? 'green' : 'default'}>
                  {signal.signal_type === 'buy' ? '买入' : signal.signal_type === 'sell' ? '卖出' : '持有'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="最新价">{metrics.latest.close as number}</Descriptions.Item>
              <Descriptions.Item label="成交额">{(metrics.latest.amount as number || 0).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="换手率">{metrics.latest.turnover_rate != null ? `${(metrics.latest.turnover_rate as number).toFixed(2)}%` : '-'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )}

      {tsCode && !signal && !dLoading && (
        <Alert type="info" message="该股票暂未纳入当前策略信号范围，可尝试运行策略后再查看" />
      )}
    </div>
  );
}
