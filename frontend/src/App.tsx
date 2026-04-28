import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import StrategyConfig from './pages/StrategyConfig';
import ScreeningResults from './pages/ScreeningResults';
import SignalDetail from './pages/SignalDetail';
import StockAdvisor from './pages/StockAdvisor';
import FactorManager from './pages/FactorManager';
import DataManagement from './pages/DataManagement';
import SignalsRedirect from './pages/SignalsRedirect';

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/strategies" element={<StrategyConfig />} />
        <Route path="/strategies/:id/signals" element={<ScreeningResults />} />
        <Route path="/signals" element={<SignalsRedirect />} />
        <Route path="/signal/:tsCode" element={<SignalDetail />} />
        <Route path="/factors" element={<FactorManager />} />
        <Route path="/data" element={<DataManagement />} />
        <Route path="/advisor" element={<StockAdvisor />} />
      </Routes>
    </AppLayout>
  );
}
