import { useState } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, InputNumber,
  Popconfirm, message, Space, Tag, Tooltip, Slider, Row, Col, Descriptions,
} from 'antd';
import { PlusOutlined, PlayCircleOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import {
  useStrategyList, useCreateStrategy, useDeleteStrategy, useRunStrategy, useCurrentSignals,
} from '@/hooks/useStrategyApi';
import { useFactorList } from '@/hooks/useFactorApi';
import type { FactorMeta } from '@/types';

const { TextArea } = Input;

const DEFAULT_TEMPLATE = `id: "my_strategy"
name: "我的策略"
description: ""
active: true

universe:
  exclude_ST: true
  exclude_new_stock_days: 60
  exclude_suspended: true
  min_listing_days: 120

factor_weights:
  PE_TTM: -0.15
  ROE_TTM: 0.20
  MOM_6M: 0.15

preprocessing:
  winsorize_pct: [1, 99]
  standardize_method: "zscore"

signals:
  buy_top_pct: 0.15
  sell_bottom_pct: 0.15
  max_holdings: 20
  min_holding_days: 1`;

export default function StrategyConfig() {
  const { data: strategies, isLoading } = useStrategyList();
  const { data: factors } = useFactorList();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [resultModal, setResultModal] = useState(false);
  const [runResult, setRunResult] = useState<unknown>(null);

  const createMut = useCreateStrategy();
  const deleteMut = useDeleteStrategy();
  const runMut = useRunStrategy();

  const handleCreate = () => {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ id: '', name: '', description: '', config_yaml: DEFAULT_TEMPLATE });
    setModalOpen(true);
  };

  const handleEdit = (record: Record<string, unknown>) => {
    setEditingId(record.id as string);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = { ...values, is_active: true };
    if (editingId) {
      // Update by deleting and recreating
      await deleteMut.mutateAsync(editingId);
    }
    await createMut.mutateAsync(payload);
    setModalOpen(false);
    message.success('策略已保存');
  };

  const handleRun = async (id: string) => {
    const result = await runMut.mutateAsync({ id });
    setRunResult(result);
    setResultModal(true);
  };

  const factorOptions = factors?.map((f: FactorMeta) => ({
    label: `${f.name} (${f.category})`,
    value: f.name,
  })) || [];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新建策略</Button>
      </Space>

      <Table
        dataSource={strategies as Record<string, unknown>[] || []}
        rowKey="id"
        loading={isLoading}
        columns={[
          { title: '名称', dataIndex: 'name', width: 180 },
          { title: '描述', dataIndex: 'description', ellipsis: true },
          { title: '状态', dataIndex: 'is_active', width: 80, render: (v: number) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag> },
          { title: '更新时间', dataIndex: 'updated_at', width: 180 },
          {
            title: '操作', width: 240, render: (_: unknown, record: Record<string, unknown>) => (
              <Space>
                <Tooltip title="运行策略"><Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleRun(record.id as string)} loading={runMut.isPending} /></Tooltip>
                <Tooltip title="编辑"><Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} /></Tooltip>
                <Popconfirm title="确认删除?" onConfirm={() => deleteMut.mutate(record.id as string)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      {/* Create/Edit Modal */}
      <Modal
        title={editingId ? '编辑策略' : '新建策略'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={800}
        confirmLoading={createMut.isPending}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}><Form.Item name="id" label="策略ID" rules={[{ required: true }]}><Input placeholder="strategy_01" /></Form.Item></Col>
            <Col span={8}><Form.Item name="name" label="名称" rules={[{ required: true }]}><Input placeholder="价值动量精选" /></Form.Item></Col>
            <Col span={8}><Form.Item name="description" label="描述"><Input placeholder="策略简述" /></Form.Item></Col>
          </Row>
          <Form.Item name="config_yaml" label="YAML配置" rules={[{ required: true }]} getValueFromEvent={(e) => e.target.value}>
            <TextArea rows={20} style={{ fontFamily: 'monospace', fontSize: 13 }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Run Result Modal */}
      <Modal title="运行结果" open={resultModal} onCancel={() => setResultModal(false)} footer={null}>
        <Descriptions column={1} bordered size="small">
          {runResult && Object.entries(runResult as Record<string, unknown>).map(([k, v]) => (
            <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
          ))}
        </Descriptions>
      </Modal>
    </div>
  );
}
