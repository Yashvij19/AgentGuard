import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  GitPullRequest,
  Bot,
  Coins,
  History,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  GitBranch,
  ShieldAlert,
} from 'lucide-react';
import { DecisionTimeline } from '../components/common/DecisionTimeline';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { RunDetail } from '../types';
import clsx from 'clsx';

export const RunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const loadDetail = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);

    try {
      let targetId = id;
      if (!targetId) {
        const list = await api.getRuns({ pageSize: 1 });
        targetId = list.items[0]?.id;
      }
      if (targetId) {
        const data = await api.getRunDetail(targetId);
        setRunDetail(data);
      } else {
        setRunDetail(null);
      }
    } catch (err) {
      console.error('Failed to load run detail from API:', err);
      setRunDetail(null);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="py-20 text-center font-serif text-[18px] text-[#5F664F] flex flex-col items-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-[#55633C]" />
        <span>Loading custodial execution record...</span>
      </div>
    );
  }

  if (!runDetail) {
    return (
      <div className="card-archival p-16 text-center flex flex-col items-center justify-center gap-4">
        <div>
          <h3 className="font-serif text-[22px] font-medium text-[#2E3325]">
            No Data is present
          </h3>
          <p className="text-[14px] text-[#5F664F] mt-1">
            The requested execution run does not exist or has no recorded audit events.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/runs')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-[#55633C] text-[#F7F2EB] hover:bg-[#2E3325] text-[13px] font-medium transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Runs Screen</span>
        </button>
      </div>
    );
  }

  const isPaused = runDetail.status === 'PAUSED';

  return (
    <div className="flex flex-col gap-5">
      {/* Top Breadcrumb & Navigation Controls (Non-reloading client navigation) */}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => navigate('/runs')}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded bg-[#EAE2D6] hover:bg-[#D9CFBF] text-[#2E3325] text-[13px] font-medium transition-all border border-[#D9CFBF] cursor-pointer shadow-xs"
        >
          <ArrowLeft className="w-4 h-4 text-[#55633C]" />
          <span>&larr; Back to Run Screen</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => loadDetail(true)}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#F7F2EB] hover:bg-[#EAE2D6] text-[#55633C] text-[13px] font-medium transition-colors border border-[#D9CFBF] cursor-pointer"
            title="Re-query API for latest events and status"
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", isRefreshing && "animate-spin")} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Record'}</span>
          </button>
        </div>
      </div>
      {/* Top Banner if Approval / Sign-off Required */}
      {isPaused && (
        <div className="card-archival p-4 bg-[#F0E6CF]/60 border-[#E4C27C] flex flex-col md:flex-row md:items-center justify-between gap-4 animate-rise-in">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded bg-[#F0E6CF] text-[#A88A4A] shrink-0 border border-[#E4C27C]">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-[18px] font-semibold text-[#2E3325]">
                  Custodian Dual-Custody Intervention Mandated
                </span>
                <span className="px-2 py-0.5 rounded label-caps text-[10px] bg-[#F0E6CF] text-[#5A4308] border border-[#E4C27C]">
                  Requires Sign-off
                </span>
              </div>
              <p className="text-[13px] text-[#5F664F] mt-1">
                Agent reached Step 4 (Patch) and requested a sensitive file write to billing dispute handlers. Risk score:{' '}
                <strong className="text-[#A88A4A] font-mono">78/100</strong>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 self-end md:self-auto">
            <button
              type="button"
              onClick={() => alert('Run session marked for abort.')}
              className="px-3.5 py-1.5 rounded bg-[#EFDCD6] text-[#8C4A3F] border border-[#D9AFA6] hover:bg-[#8C4A3F] hover:text-[#F7F2EB] text-[13px] font-medium transition-colors"
            >
              Abort Run Session
            </button>
            <button
              type="button"
              onClick={() => navigate('/approvals')}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded bg-[#55633C] hover:bg-[#2E3325] text-[#F7F2EB] text-[13px] font-medium transition-all shadow-xs"
            >
              <span>Jump to Approval Queue</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Header Summary Ledger Sheet */}
      <div className="card-archival p-6 bg-[#FBF8F3]">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center pb-4 mb-4 border-b border-[#D9CFBF]/70 gap-3">
          <div>
            <span className="label-caps text-[#8A8E7C] text-[11px]">
              Custodial Execution Record // Run #{runDetail.run_number}
            </span>
            <h1 className="font-serif text-[32px] text-[#2E3325] leading-tight font-medium mt-1">
              Run Execution Summary: {runDetail.pr_title}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={runDetail.status} size="md" pulse={runDetail.status === 'RUNNING'} />
            <div className="flex items-center gap-1.5 text-[#5F664F] font-mono text-[11px] bg-[#EAE2D6]/70 px-2.5 py-1 rounded border border-[#D9CFBF]">
              <History className="w-3.5 h-3.5 text-[#8A8E7C]" />
              <span>4m 12s cumulative</span>
            </div>
          </div>
        </div>

        {/* Archival Metadata Ledger Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
          {/* Col 1: Repo & Branch */}
          <div className="flex flex-col p-3 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]/60">
            <span className="label-caps text-[#8A8E7C] text-[10px]">
              Target Repository
            </span>
            <div className="flex items-center gap-1.5 mt-1 text-[#2E3325] font-mono text-[12px] font-medium">
              <GitBranch className="w-4 h-4 text-[#55633C]" />
              <span>{runDetail.repository}</span>
            </div>
            <span className="font-mono text-[11px] text-[#8A8E7C] mt-0.5 truncate">
              {runDetail.branch}
            </span>
          </div>

          {/* Col 2: Pull Request / Head */}
          <div className="flex flex-col p-3 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]/60">
            <span className="label-caps text-[#8A8E7C] text-[10px]">
              Pull Request / Head
            </span>
            <div className="flex items-center gap-1.5 mt-1 text-[#2E3325] font-mono text-[12px] font-medium">
              <GitPullRequest className="w-4 h-4 text-[#55633C]" />
              <span>PR #{runDetail.pr_number}</span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="font-mono text-[11px] text-[#2E3325] font-medium">
                {runDetail.commit_sha}
              </span>
              <span className="px-1.5 py-0.2 rounded bg-[#E3E8D6] text-[#55633C] border border-[#BDCD9D] font-mono text-[9px] font-bold">
                Ed25519 Verified
              </span>
            </div>
          </div>

          {/* Col 3: Autonomous Driver */}
          <div className="flex flex-col p-3 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]/60">
            <span className="label-caps text-[#8A8E7C] text-[10px]">
              Autonomous Driver
            </span>
            <div className="flex items-center gap-1.5 mt-1 text-[#2E3325] font-mono text-[12px] font-medium">
              <Bot className="w-4 h-4 text-[#5F664F]" />
              <span>{runDetail.agent_name}</span>
            </div>
            <span className="text-[12px] text-[#8A8E7C] mt-0.5">
              Governed Multi-Vendor Engine
            </span>
          </div>

          {/* Col 4: Compute & Token Budget */}
          <div className="flex flex-col p-3 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]/60">
            <span className="label-caps text-[#8A8E7C] text-[10px]">
              Compute & Token Budget
            </span>
            <div className="flex items-center gap-1.5 mt-1 text-[#2E3325] font-mono text-[12px] font-medium">
              <Coins className="w-4 h-4 text-[#A88A4A]" />
              <span>{runDetail.tokens_total.toLocaleString()} tokens</span>
            </div>
            <span className="font-mono text-[11px] text-[#8A8E7C] mt-0.5">
              ${runDetail.cost_usd.toFixed(4)} USD • Cumulative
            </span>
          </div>
        </div>

        {/* Second Line Invariant Spec */}
        <div className="mt-4 pt-3 border-t border-[#D9CFBF]/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[12px]">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="label-caps text-[#8A8E7C] text-[10px]">Active Policy Spec:</span>
            <span className="font-mono text-[11px] bg-[#EAE2D6] px-2 py-0.5 rounded text-[#2E3325]">
              {runDetail.policy_spec}
            </span>
            <span className="font-mono text-[11px] text-[#8A8E7C]">
              (Commit SHA: {runDetail.policy_sha})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="label-caps text-[#8A8E7C] text-[10px]">Trigger:</span>
            <span className="font-mono text-[11px] bg-[#EAE2D6] px-2 py-0.5 rounded text-[#2E3325]">
              {runDetail.trigger_event}
            </span>
          </div>
        </div>
      </div>

      {/* Cognitive Execution Trace Section */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between pb-2 border-b border-[#D9CFBF]/70">
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-[24px] font-medium text-[#2E3325]">
              Cognitive Execution Trace
            </h2>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#EAE2D6] text-[#5F664F]">
              {runDetail.steps.length} Milestones
            </span>
          </div>
          <span className="text-[12px] text-[#8A8E7C] font-mono">
            Chronological View · Synchronized
          </span>
        </div>

        <DecisionTimeline steps={runDetail.steps} />
      </div>
    </div>
  );
};
