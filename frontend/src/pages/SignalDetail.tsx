import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Spin, Statistic, Row, Col, Typography, Segmented } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useDailyData } from '@/hooks/useDataApi';
import { useStockNameMap } from '@/hooks/useStockNames';
import { calcVolume, calcRSI, calcMACD } from '@/utils/indicators';

type IndicatorType = 'volume' | 'rsi' | 'macd';

export default function SignalDetail() {
  const { tsCode } = useParams<{ tsCode: string }>();
  const navigate = useNavigate();
  // Only fetch last 2 years of data for faster loading
  const startDate = `${new Date().getFullYear() - 1}0101`;
  const { data: dailyData, isLoading } = useDailyData(tsCode || '', startDate);
  const nameMap = useStockNameMap();
  const [indicator, setIndicator] = useState<IndicatorType>('volume');

  const stockName = tsCode ? nameMap[tsCode] || '' : '';

  const ohlc = useMemo(() => {
    if (!dailyData || dailyData.length === 0) return [];
    return (dailyData as Record<string, unknown>[]).map((d) => ({
      trade_date: (d.trade_date as string).slice(4),
      trade_date_full: d.trade_date as string,
      open: d.open as number,
      high: d.high as number,
      low: d.low as number,
      close: d.close as number,
      vol: (d.vol as number) || 0,
      amount: (d.amount as number) || 0,
    }));
  }, [dailyData]);

  const chartOption = useMemo(() => {
    if (ohlc.length === 0) return {};

    const dates = ohlc.map((d) => d.trade_date);
    const ohlcData = ohlc.map((d) => [d.open, d.close, d.low, d.high]);

    // Candlestick series
    const series: Record<string, unknown>[] = [{
      name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
      data: ohlcData,
      itemStyle: { color: '#cf1322', color0: '#3f8600', borderColor: '#cf1322', borderColor0: '#3f8600' },
    }];

    // Indicator series (below candlestick)
    if (indicator === 'volume') {
      const prevClose = ohlc.map((d, i) => i > 0 ? ohlc[i - 1].close : d.close);
      const volUp = ohlc.map((d, i) => d.close >= prevClose[i] ? d.vol : '-');
      const volDown = ohlc.map((d, i) => d.close < prevClose[i] ? d.vol : '-');
      series.push(
        { name: '成交量↑', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volUp, itemStyle: { color: '#cf1322' } },
        { name: '成交量↓', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volDown, itemStyle: { color: '#3f8600' } },
      );
    } else if (indicator === 'rsi') {
      const rsiData = calcRSI(ohlc.map((d) => ({ ...d, trade_date: d.trade_date_full, amount: 0 }))).values;
      series.push({
        name: 'RSI(14)', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
        data: rsiData.map((v) => v[0]),
        itemStyle: { color: '#7c4dff' }, lineStyle: { width: 1.5 }, symbol: 'none', smooth: true,
      });
    } else if (indicator === 'macd') {
      const macdRes = calcMACD(ohlc.map((d) => ({ ...d, trade_date: d.trade_date_full, amount: 0 })));
      series.push(
        { name: 'DIF', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: macdRes.dif, itemStyle: { color: '#2196f3' }, lineStyle: { width: 1 }, symbol: 'none' },
        { name: 'DEA', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: macdRes.dea, itemStyle: { color: '#ff9800' }, lineStyle: { width: 1 }, symbol: 'none' },
        { name: 'MACD', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: macdRes.macd, itemStyle: { color: '#e91e63' } },
      );
    }

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [
        { left: '8%', right: '2%', top: 20, height: '60%' },
        { left: '8%', right: '2%', top: '75%', height: '18%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#ccc' } }, splitLine: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { rotate: 0, fontSize: 10 }, axisLine: { lineStyle: { color: '#ccc' } }, splitLine: { show: false } },
      ],
      yAxis: [
        { type: 'value', scale: true, gridIndex: 0, position: 'left', axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
        { type: 'value', gridIndex: 1, position: 'left', axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
      ],
      series,
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1] },
        { type: 'slider', xAxisIndex: [0, 1], bottom: 0, height: 20 },
      ],
      legend: { bottom: 24, data: series.map((s) => s.name) },
      animation: false,
    };
  }, [ohlc, indicator]);

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (ohlc.length === 0) return <Typography.Text type="danger">未找到 {tsCode} 的数据</Typography.Text>;

  const latest = ohlc[ohlc.length - 1];

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>返回</Button>

      <Row gutter={16} style={{ marginBottom: 8 }}>
        <Col span={6}><Statistic title="股票" value={`${tsCode} ${stockName}`} /></Col>
        <Col span={6}><Statistic title="最新价" value={latest.close} precision={2} /></Col>
        <Col span={6}><Statistic title="涨跌幅" value={ohlc.length > 1 ? ((latest.close / ohlc[ohlc.length - 2].close - 1) * 100) : 0} precision={2} suffix="%" valueStyle={{ color: latest.close >= (ohlc.length > 1 ? ohlc[ohlc.length - 2].close : latest.close) ? '#cf1322' : '#3f8600' }} /></Col>
        <Col span={6}>
          <Segmented
            options={[
              { label: '成交量', value: 'volume' },
              { label: 'RSI', value: 'rsi' },
              { label: 'MACD', value: 'macd' },
            ]}
            value={indicator}
            onChange={(v) => setIndicator(v as IndicatorType)}
          />
        </Col>
      </Row>

      <Card>
        <ReactECharts style={{ height: 480 }} option={chartOption} notMerge />
      </Card>

      <Card title="基本信息" style={{ marginTop: 16 }}>
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label="代码">{tsCode}</Descriptions.Item>
          <Descriptions.Item label="名称">{stockName || '-'}</Descriptions.Item>
          <Descriptions.Item label="最新日期">{latest.trade_date_full}</Descriptions.Item>
          <Descriptions.Item label="成交量">{(latest.vol || 0).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="成交额">{(latest.amount || 0).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="开盘">{latest.open}</Descriptions.Item>
          <Descriptions.Item label="最高">{latest.high}</Descriptions.Item>
          <Descriptions.Item label="最低">{latest.low}</Descriptions.Item>
          <Descriptions.Item label="收盘">{latest.close}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
