import { useState } from 'react';
import { Card, Table, Tag, Button, Select, message, Statistic, Row, Col, Space, Spin } from 'antd';
import { ReloadOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import { useDataStatus, useDataRefresh } from '@/hooks/useDataApi';
import type { DataRefreshStatus } from '@/types';

export default function DataManagement() {
  const { data: statusData, isLoading, refetch } = useDataStatus();
  const refreshMut = useDataRefresh();
  const [refreshType, setRefreshType] = useState('all');

  const handleRefresh = async () => {
    await refreshMut.mutateAsync(refreshType);
    message.success('数据刷新完成');
    refetch();
  };

  const statusList: DataRefreshStatus[] = statusData ? Object.values(statusData) : [];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col><Statistic title="数据类别" value={statusList.length} /></Col>
        <Col><Statistic title="健康状态" value={statusList.filter((s: DataRefreshStatus) => s.status === 'healthy').length} suffix={`/ ${statusList.length}`} /></Col>
      </Row>

      <Card
        title="数据刷新"
        extra={
          <Space>
            <Select value={refreshType} onChange={setRefreshType} style={{ width: 150 }}
              options={[
                { label: '全部', value: 'all' },
                { label: '日线行情', value: 'daily' },
                { label: '股票列表', value: 'stock_list' },
                { label: '交易日历', value: 'calendar' },
                { label: '财务数据', value: 'financial' },
              ]}
            />
            <Button type="primary" icon={<CloudDownloadOutlined />} loading={refreshMut.isPending} onClick={handleRefresh}>
              刷新数据
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新状态</Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          dataSource={statusList}
          rowKey="data_type"
          loading={isLoading}
          pagination={false}
          columns={[
            { title: '数据类型', dataIndex: 'data_type', width: 150 },
            {
              title: '状态', dataIndex: 'status', width: 100,
              render: (v: string) => <Tag color={v === 'healthy' ? 'green' : v === 'empty' ? 'orange' : 'red'}>{v === 'healthy' ? '正常' : v === 'empty' ? '空' : '异常'}</Tag>,
            },
            { title: '最后更新', dataIndex: 'last_updated', width: 160 },
            { title: '记录数', dataIndex: 'record_count', width: 100, render: (v: number) => v?.toLocaleString() },
          ]}
        />
      </Card>
    </div>
  );
}
