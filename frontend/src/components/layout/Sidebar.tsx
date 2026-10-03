import React, { useState, useEffect, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BookOpen,
  History,
  ShieldCheck,
  Scale,
  Cpu,
  RefreshCw,
  Zap,
  Terminal,
  FileText,
} from 'lucide-react';
import clsx from 'clsx';
import { api } from '../../services/api';

interface SidebarProps {
  pendingApprovalsCount?: number;
  onRefresh?: () => Promise<void>;
}

export const Sidebar: React.FC<SidebarProps> = ({
  pendingApprovalsCount = 2,
  onRefresh,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshLabel, setRefreshLabel] = useState('2m ago');
  const [activeModelName, setActiveModelName] = useState('Gemini 2.5 Flash');

  const fetchActiveModel = useCallback(async () => {
    try {
      const cfg = await api.getProvidersConfig();
      const primary = cfg.providers?.find(
        (p) => p.name === cfg.default_primary || p.role === 'primary'
      );
      if (primary) {
        const rawModel = primary.selected_model || primary.models[0] || primary.display_name;
        // User-friendly label formatting
        let formatted = primary.display_name;
        if (rawModel.includes('gemini-2.5')) formatted = 'Gemini 2.5 Flash';
        else if (rawModel.includes('gemini-2.0')) formatted = 'Gemini 2.0 Flash';
        else if (rawModel.includes('gpt-oss')) formatted = 'GPT-OSS-20B';
        else if (rawModel.includes('qwen')) formatted = 'Qwen 3.8-27B';
        else if (rawModel.includes('deepseek')) formatted = 'DeepSeek V4.1';
        else if (rawModel.includes('nemotron')) formatted = 'Nemotron Ultra';
        else if (rawModel.includes('glm')) formatted = 'GLM 5.3 Flash';
        else if (primary.display_name) formatted = primary.display_name;
        else formatted = rawModel;

        setActiveModelName(formatted);
      }
    } catch {
      // Keep existing active model on error
    }
  }, []);

  useEffect(() => {
    fetchActiveModel();
    const handleProviderChange = () => {
      fetchActiveModel();
    };
    window.addEventListener('llm_provider_changed', handleProviderChange);
    return () => window.removeEventListener('llm_provider_changed', handleProviderChange);
  }, [fetchActiveModel]);

  const handleRefreshClick = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    setRefreshLabel('Refreshing...');

    try {
      await fetchActiveModel();
      if (onRefresh) {
        await onRefresh();
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800));
      }
      setRefreshLabel('Just now');
    } finally {
      setTimeout(() => {
        setIsRefreshing(false);
      }, 700);
    }
  };

  const navItems = [
    { to: '/', label: 'Overview', icon: BookOpen },
    { to: '/runs', label: 'Runs', icon: History },
    {
      to: '/approvals',
      label: 'Approvals',
      icon: ShieldCheck,
      badge: pendingApprovalsCount,
    },
    { to: '/policies', label: 'Policy Studio', icon: Scale },
    { to: '/providers', label: 'LLM Providers', icon: Cpu },
    { to: '/logs', label: 'Developer Logs', icon: Terminal },
    { to: '/docs', label: 'Documentation', icon: FileText },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-[#FBF8F3] border-r border-[#D9CFBF] z-50 flex flex-col justify-between select-none">
      <div className="flex flex-col">
        {/* Wordmark Header with Engraved Monogram Logo */}
        <div className="px-5 pt-6 pb-4 border-b border-[#D9CFBF]">
          <div className="flex items-center gap-3">
            <img
              src="/logo.svg"
              alt="The Ledger Monogram Logo"
              className="h-8 w-8 object-contain shrink-0"
            />
            <div className="flex flex-col">
              <span className="font-serif text-[22px] font-semibold text-[#2E3325] leading-none tracking-tight">
                The Ledger
              </span>
              <span className="label-caps text-[#8A8E7C] text-[10px] tracking-widest mt-1">
                Agent Governance
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col py-3 px-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center justify-between px-3 py-2 rounded text-[14px] font-medium transition-all duration-200 relative',
                  isActive
                    ? 'bg-[#EAE2D6]/80 text-[#2E3325] font-semibold border-r-2 border-[#55633C]'
                    : 'text-[#5F664F] hover:bg-[#EAE2D6]/40 hover:text-[#2E3325]'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center gap-2.5">
                    <item.icon
                      className={clsx(
                        'w-4 h-4 stroke-[1.8] transition-colors',
                        isActive ? 'text-[#55633C]' : 'text-[#8A8E7C] group-hover:text-[#2E3325]'
                      )}
                    />
                    <span>{item.label}</span>
                  </div>

                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full bg-[#F0E6CF] text-[#5A4308] border border-[#E4C27C] font-mono text-[11px] font-bold">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* System Status & Refresh Footer */}
      <div className="p-4 border-t border-[#D9CFBF] flex flex-col gap-2.5 bg-[#F7F2EB]">
        {/* Nominal daemon indicator */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#55633C]" />
          <span className="font-mono text-[11px] text-[#5F664F]">
            System Nominal · OPA Connected
          </span>
        </div>

        {/* Active Model Snapshot */}
        <div className="flex items-center justify-between bg-[#FBF8F3] px-2.5 py-1.5 rounded border border-[#D9CFBF]/80 text-[12px]">
          <span className="font-mono text-[11px] text-[#2E3325] truncate max-w-[155px]" title={`${activeModelName} active`}>
            {activeModelName} active
          </span>
          <Zap className="w-3.5 h-3.5 text-[#55633C] shrink-0" />
        </div>

        {/* Refresh Control */}
        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={handleRefreshClick}
            className="flex items-center gap-1.5 text-[12px] text-[#5F664F] hover:text-[#2E3325] transition-colors group cursor-pointer"
          >
            <RefreshCw
              className={clsx(
                'w-3.5 h-3.5 text-[#8A8E7C] group-hover:text-[#55633C] transition-transform duration-700',
                isRefreshing && 'rotate-360 animate-spin'
              )}
            />
            <span>Poll updates</span>
          </button>
          <span className="font-mono text-[11px] text-[#8A8E7C]">
            {refreshLabel}
          </span>
        </div>
      </div>
    </aside>
  );
};
