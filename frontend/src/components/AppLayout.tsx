import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  SettingOutlined,
  TableOutlined,
  FundOutlined,
  DatabaseOutlined,
  SearchOutlined,
} from '@ant-design/icons';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '数据看板' },
  { key: '/strategies', icon: <SettingOutlined />, label: '策略配置' },
  { key: '/strategies/demo/signals', icon: <TableOutlined />, label: '选股结果' },
  { key: '/factors', icon: <FundOutlined />, label: '因子管理' },
  { key: '/data', icon: <DatabaseOutlined />, label: '数据管理' },
  { key: '/advisor', icon: <SearchOutlined />, label: '智能选股' },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems.find((item) => {
    if (item.key === '/') return location.pathname === '/';
    return location.pathname.startsWith(item.key);
  })?.key || '/';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
        <div style={{ height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography.Title level={5} style={{ color: '#fff', margin: 0, whiteSpace: 'nowrap' }}>
            {collapsed ? 'QU' : '量化选股系统'}
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Typography.Title level={4} style={{ margin: '16px 0' }}>
            {menuItems.find((m) => m.key === selectedKey)?.label || ''}
          </Typography.Title>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
