import { useState, useMemo } from 'react';
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
  { key: '/advisor', icon: <SearchOutlined />, label: '智能选股' },
  { key: '/factors', icon: <FundOutlined />, label: '因子管理' },
  { key: '/data', icon: <DatabaseOutlined />, label: '数据管理' },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Match the most specific (longest) menu key to the current path
  const selectedKey = useMemo(() => {
    const path = location.pathname;
    if (path === '/' || path === '/signals') return path;
    if (path.startsWith('/strategies/') && path.endsWith('/signals')) return '/signals';
    if (path.startsWith('/signal/')) return '/signals';
    // Find longest matching key
    let best = '/';
    for (const item of menuItems) {
      if (item.key === '/') continue;
      if (path.startsWith(item.key) && item.key.length > best.length) {
        best = item.key;
      }
    }
    return best;
  }, [location.pathname]);

  // Build dynamic menu items (include virtual 选股结果 entry)
  const displayMenuItems = useMemo(() => [
    ...menuItems.slice(0, 2),
    { key: '/signals', icon: <TableOutlined />, label: '选股结果' },
    ...menuItems.slice(2),
  ], []);

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
          items={displayMenuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Typography.Title level={4} style={{ margin: '16px 0' }}>
            {displayMenuItems.find((m) => m.key === selectedKey)?.label || ''}
          </Typography.Title>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
