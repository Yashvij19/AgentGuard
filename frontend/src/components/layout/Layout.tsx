import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface LayoutProps {
  pendingApprovalsCount?: number;
  onRefresh?: () => Promise<void>;
}

export const Layout: React.FC<LayoutProps> = ({
  pendingApprovalsCount,
  onRefresh,
}) => {
  return (
    <div className="min-h-screen bg-[#F7F2EB] text-[#2E3325]">
      <Sidebar
        pendingApprovalsCount={pendingApprovalsCount}
        onRefresh={onRefresh}
      />
      <div className="pl-64 flex flex-col min-h-screen">
        <Header />
        <main className="w-full pt-20 px-8 pb-16 max-w-7xl mx-auto flex-1 animate-rise-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
