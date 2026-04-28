import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useStrategyList } from '@/hooks/useStrategyApi';

export default function SignalsRedirect() {
  const navigate = useNavigate();
  const { data: strategies, isLoading } = useStrategyList();

  useEffect(() => {
    if (isLoading) return;
    const active = (strategies as Record<string, unknown>[])?.find(
      (s) => s.is_active
    );
    if (active?.id) {
      navigate(`/strategies/${active.id}/signals`, { replace: true });
    } else {
      navigate('/strategies', { replace: true });
    }
  }, [strategies, isLoading, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: 48 }}>
      <Spin size="large" />
    </div>
  );
}
