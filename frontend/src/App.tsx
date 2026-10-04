import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { RunsPage } from './pages/RunsPage';
import { RunDetailPage } from './pages/RunDetailPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { PolicyStudioPage } from './pages/PolicyStudioPage';
import { LLMProvidersPage } from './pages/LLMProvidersPage';
import { LogsPage } from './pages/LogsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { api } from './services/api';

export const App: React.FC = () => {
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);

  const fetchPendingApprovals = async () => {
    try {
      const data = await api.getApprovals();
      setPendingApprovalsCount(data.length);
    } catch {
      setPendingApprovalsCount(0);
    }
  };

  useEffect(() => {
    fetchPendingApprovals();
    const handleUpdate = () => fetchPendingApprovals();
    window.addEventListener('approvals_updated', handleUpdate);
    const interval = setInterval(fetchPendingApprovals, 15000);
    return () => {
      window.removeEventListener('approvals_updated', handleUpdate);
      clearInterval(interval);
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <Layout
              pendingApprovalsCount={pendingApprovalsCount}
              onRefresh={fetchPendingApprovals}
            />
          }
        >
          <Route path="/" element={<OverviewPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/policies" element={<PolicyStudioPage />} />
          <Route path="/providers" element={<LLMProvidersPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/docs" element={<DocumentationPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
