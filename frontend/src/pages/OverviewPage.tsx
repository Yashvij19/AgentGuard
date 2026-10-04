import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Terminal,
  ShieldCheck,
  Gavel,
  Wallet,
  Calendar,
  Download,
  Search,
  ArrowRight,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { MetricCard } from '../components/common/MetricCard';
import { ProviderCard } from '../components/common/ProviderCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { StatsSummary, ProviderHealth, RunItem, HourlyAnalyticsItem } from '../types';
import clsx from 'clsx';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [hourlyData, setHourlyData] = useState<HourlyAnalyticsItem[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState('Last 24 Hours');
  const [isTimelineOpen, setIsTimelineOpen] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [activeTooltip, setActiveTooltip] = useState<{
    time: string;
    completed: number;
    paused: number;
    failed: number;
  }>({
    time: 'Live Audit Window',
    completed: 18,
    paused: 1,
    failed: 0,
  });

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [s, p, rData, h] = await Promise.all([
          api.getStats(),
          api.getProvidersHealth(),
          api.getRuns({ pageSize: 15 }),
          api.getHourlyAnalytics(),
        ]);
        setStats(s);
        setProviders(p);
        setRuns(rData.items);
        setHourlyData(h);
        if (h && h.length > 0) {
          const activeOrLast = h.find((item) => item.active) || h[h.length - 1];
          setActiveTooltip({
            time: `Today, ${activeOrLast.time}`,
            completed: activeOrLast.completed,
            paused: activeOrLast.paused,
            failed: activeOrLast.failed,
          });
        }
      } catch (err) {
        console.error('Failed to load live overview telemetry:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-8 animate-fade-in">
        <div className="flex flex-col gap-2 border-b border-[#D9CFBF] pb-5">
          <div className="flex items-center gap-2 text-[11px] text-[#5F664F]">
            <span className="label-caps">Folio 01 // Operations Ledger</span>
            <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
            <span className="font-mono text-[#8A8E7C]">Loading Telemetry</span>
          </div>
          <h1 className="font-serif text-[40px] text-[#2E3325] leading-none font-medium tracking-tight mt-1">
            Governance & Execution Ledger
          </h1>
        </div>

        <div className="card-archival p-16 flex flex-col items-center justify-center gap-4 text-center">
          <RefreshCw className="w-10 h-10 animate-spin text-[#55633C]" />
          <h3 className="font-serif text-[24px] font-medium text-[#2E3325]">
            Retrieving Governance Telemetry...
          </h3>
          <p className="text-[14px] text-[#5F664F] max-w-md">
            Querying active execution states, token expenditures, LLM health probes, and audit logs from Neon Postgres.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span className="w-2 h-2 rounded-full bg-[#55633C] animate-pulse" />
            <span className="font-mono text-[12px] text-[#8A8E7C]">Synchronizing live audit metrics...</span>
          </div>
        </div>
      </div>
    );
  }

  const handleExportCSV = () => {
    window.location.href = api.exportRunsCsvUrl();
  };

  const filteredRuns = runs.filter(
    (r) =>
      r.repository.toLowerCase().includes(searchFilter.toLowerCase()) ||
      r.commit_sha.toLowerCase().includes(searchFilter.toLowerCase()) ||
      r.pr_title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-10">
      {/* Top Archival Folio Header */}
      <div className="flex flex-col gap-2 pt-2 border-b border-[#D9CFBF] pb-6">
        <div className="flex items-center justify-between text-[11px] text-[#5F664F] flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="label-caps text-[#5F664F]">
              Archival Folio 01 // Executive Ledger
            </span>
            <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
            <span className="font-mono text-[#8A8E7C]">
              Synchronized with OPA Audit Daemon
            </span>
          </div>
          <span className="font-mono text-[#8A8E7C]">
            Stationery Seal #LG-8942-01A
          </span>
        </div>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-2">
          <div>
            <h1 className="font-serif text-[40px] text-[#2E3325] leading-none font-medium tracking-tight">
              Executive Ledger & Overview
            </h1>
            <p className="text-[15px] text-[#5F664F] mt-2 max-w-2xl leading-relaxed">
              Real-time governance record of autonomous coding agents across monitored repositories.
            </p>
          </div>

          {/* Actions: Timeline Dropdown & CSV Export */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsTimelineOpen(!isTimelineOpen)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-[#FBF8F3] border border-[#D9CFBF] text-[#2E3325] rounded text-[13px] hover:bg-[#EAE2D6]/40 transition-colors shadow-xs"
              >
                <Calendar className="w-3.5 h-3.5 text-[#5F664F]" />
                <span>Timeline: {selectedTimeline}</span>
                <ChevronDown className="w-3.5 h-3.5 text-[#8A8E7C]" />
              </button>

              {isTimelineOpen && (
                <div className="absolute right-0 mt-1 w-52 rounded bg-[#FBF8F3] border border-[#D9CFBF] shadow-lg z-50 py-1 font-sans text-[13px]">
                  {['Last 6 Hours', 'Last 24 Hours', 'Last 7 Days', 'Fiscal Quarter to Date'].map(
                    (opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setSelectedTimeline(opt);
                          setIsTimelineOpen(false);
                        }}
                        className="w-full text-left px-4 py-1.5 text-[#2E3325] hover:bg-[#EAE2D6]/60 transition-colors"
                      >
                        {opt}
                      </button>
                    )
                  )}
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={handleExportCSV}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-[#EAE2D6]/70 border border-[#D9CFBF] hover:bg-[#EAE2D6] text-[#2E3325] rounded text-[13px] transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-[#5F664F]" />
              <span>Export Audit Ledger (CSV)</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Primary Metric Cards */}
      {stats ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total Sessions"
            value={stats.total_sessions}
            icon={Terminal}
            trendDirection="up"
            trendText={`${stats.sessions_trend_pct}%`}
            subtitle="from previous cycle"
            accentColor="neutral"
            delayMs={0}
          />
          <MetricCard
            label="Verified Compliance"
            value={stats.verified_compliance_pct}
            suffix="%"
            decimals={1}
            icon={ShieldCheck}
            trendDirection="neutral"
            subtitle={`${stats.verified_cycles_count} cycles · 0 escapes`}
            accentColor="sage"
            delayMs={60}
          />
          <MetricCard
            label="Action Required"
            value={stats.action_required_count}
            decimals={0}
            icon={Gavel}
            trendDirection="neutral"
            trendText={`${stats.action_required_count} Pending`}
            subtitle="Awaiting human sign-off"
            accentColor="brass"
            delayMs={120}
          />
          <MetricCard
            label="Compute Expenditure"
            value={stats.compute_expenditure_usd}
            prefix="$"
            decimals={2}
            icon={Wallet}
            progressBarPct={stats.budget_burn_pct}
            accentColor="neutral"
            delayMs={180}
          />
        </div>
      ) : (
        <div className="card-archival p-8 text-center text-[#5F664F] font-mono text-[13px]">
          No Data is present
        </div>
      )}

      {/* LLM Providers Health Status Section */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-baseline justify-between gap-1 pb-1 border-b border-[#D9CFBF]/70">
          <div>
            <h2 className="font-serif text-[24px] font-medium text-[#2E3325]">
              Language Model Providers & Circuit States
            </h2>
            <p className="text-[13px] text-[#5F664F]">
              Autonomous failover thresholding and live telemetry across configured reasoning clusters.
            </p>
          </div>
          <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#5F664F]">
            <span className="w-2 h-2 rounded-full bg-[#55633C]" />
            <span>Mesh nominal ({providers.length} monitored)</span>
          </div>
        </div>

        {providers.length === 0 ? (
          <div className="card-archival p-8 text-center text-[#5F664F] font-mono text-[13px]">
            No Data is present
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {providers.map((p, idx) => (
              <ProviderCard key={p.id} provider={p} delayMs={idx * 60} />
            ))}
          </div>
        )}
      </div>

      {/* Dispatched Runs by Verification Outcome (Interactive SVG Chart) */}
      <div className="card-archival p-6 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-serif text-[22px] font-medium text-[#2E3325]">
                Dispatched Runs by Verification Outcome
              </h2>
              <span className="font-mono text-[11px] text-[#8A8E7C]">(Hourly distribution)</span>
            </div>
            <p className="text-[13px] text-[#5F664F]">
              Monitored pipeline results categorized by execution completion state.
            </p>
          </div>

          {/* Chart Legend */}
          <div className="flex items-center gap-4 text-[12px] font-sans">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs bg-[#55633C]" />
              <span className="text-[#2E3325]">Completed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs bg-[#A88A4A]" />
              <span className="text-[#2E3325]">Paused (Review)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs bg-[#8C4A3F]" />
              <span className="text-[#2E3325]">Failed</span>
            </div>
          </div>
        </div>

        {/* Chart Viewbox with Active Tooltip */}
        {hourlyData.length === 0 ? (
          <div className="w-full bg-[#EAE2D6]/40 border border-[#D9CFBF] rounded p-12 text-center text-[#5F664F] font-mono text-[13px]">
            No Data is present
          </div>
        ) : (
          <div className="relative w-full bg-[#EAE2D6]/40 border border-[#D9CFBF] rounded p-4 select-none">
            {/* Active Tooltip Pill */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 pointer-events-none bg-[#2E3325] text-[#F7F2EB] px-3.5 py-1 rounded shadow-md flex items-center gap-2 font-mono text-[11px] z-20">
              <span className="font-semibold">{activeTooltip.time}</span>
              <span className="opacity-40">·</span>
              <span className="text-[#DDE3D0]">{activeTooltip.completed} Completed</span>
              <span className="opacity-40">·</span>
              <span className="text-[#F0E6CF]">{activeTooltip.paused} Paused</span>
              <span className="opacity-40">·</span>
              <span className="text-[#EFDCD6]">{activeTooltip.failed} Failed</span>
            </div>

            <svg
              className="w-full h-52 text-[#8A8E7C] overflow-visible"
              fill="none"
              viewBox="0 0 920 220"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Grid lines */}
              <line stroke="#D9CFBF" strokeDasharray="3 3" x1="30" x2="900" y1="20" y2="20" />
              <text className="text-[10px] font-mono fill-[#8A8E7C]" textAnchor="end" x="20" y="24">20</text>
              <line stroke="#D9CFBF" strokeDasharray="3 3" x1="30" x2="900" y1="70" y2="70" />
              <text className="text-[10px] font-mono fill-[#8A8E7C]" textAnchor="end" x="20" y="74">15</text>
              <line stroke="#D9CFBF" strokeDasharray="3 3" x1="30" x2="900" y1="120" y2="120" />
              <text className="text-[10px] font-mono fill-[#8A8E7C]" textAnchor="end" x="20" y="124">10</text>
              <line stroke="#D9CFBF" strokeDasharray="3 3" x1="30" x2="900" y1="170" y2="170" />
              <text className="text-[10px] font-mono fill-[#8A8E7C]" textAnchor="end" x="20" y="174">5</text>
              <line stroke="#D9CFBF" x1="30" x2="900" y1="195" y2="195" />

              {/* Dynamic Real-Time Hourly Columns */}
              {hourlyData.map((item, idx) => {
                const x = 55 + idx * 71;
                const unitPx = 8.75;
                const hComp = Math.round(item.completed * unitPx);
                const hPause = Math.round(item.paused * unitPx);
                const hFail = Math.round(item.failed * unitPx);
                const yComp = 195 - hComp;
                const yPause = yComp - hPause;
                const yFail = yPause - hFail;

                return (
                  <g
                    key={idx}
                    className="cursor-pointer transition-opacity hover:opacity-80"
                    onMouseEnter={() =>
                      setActiveTooltip({
                        time: `Audit Window ${item.time}`,
                        completed: item.completed,
                        paused: item.paused,
                        failed: item.failed,
                      })
                    }
                  >
                    {item.active && (
                      <rect
                        fill="#2E3325"
                        fillOpacity="0.06"
                        height="185"
                        rx="2"
                        width="32"
                        x={x - 5}
                        y="10"
                      />
                    )}
                    {hComp > 0 && (
                      <rect
                        fill="#55633C"
                        height={hComp}
                        rx="1"
                        width="22"
                        x={x}
                        y={yComp}
                      />
                    )}
                    {hPause > 0 && (
                      <rect
                        fill="#A88A4A"
                        height={hPause}
                        rx="1"
                        width="22"
                        x={x}
                        y={yPause}
                      />
                    )}
                    {hFail > 0 && (
                      <rect
                        fill="#8C4A3F"
                        height={hFail}
                        rx="1"
                        width="22"
                        x={x}
                        y={yFail}
                      />
                    )}
                    <text
                      className="text-[11px] font-mono fill-[#5F664F]"
                      textAnchor="middle"
                      x={x + 11}
                      y="210"
                    >
                      {item.time}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        )}
      </div>

      {/* Recent Runs Ledger Table */}
      <div className="card-archival overflow-hidden flex flex-col">
        <div className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#D9CFBF]">
          <div>
            <h2 className="font-serif text-[22px] font-medium text-[#2E3325]">
              Recent Runs Ledger
            </h2>
            <p className="text-[13px] text-[#5F664F]">
              Sequential transaction journal of automated patch proposals and agent verifications.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter ledger by SHA or repo..."
                className="bg-[#F7F2EB] border border-[#D9CFBF] text-[#2E3325] placeholder:text-[#8A8E7C] pl-8 pr-3 py-1.5 rounded text-[13px] focus:outline-none focus:border-[#55633C] transition-colors w-64"
              />
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#8A8E7C]" />
            </div>
          </div>
        </div>

        {/* Table Container */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#EAE2D6]/60 text-[#5F664F] label-caps border-b border-[#D9CFBF]">
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-4">Repository & PR</th>
                <th className="py-3 px-4">Commit SHA</th>
                <th className="py-3 px-4">Steps Completed</th>
                <th className="py-3 px-4">Cost</th>
                <th className="py-3 px-4">Recorded At</th>
                <th className="py-3 px-6 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#D9CFBF]/60 text-[13px] text-[#2E3325]">
              {filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#5F664F] font-mono text-[13px]">
                    No Data is present
                  </td>
                </tr>
              ) : (
                filteredRuns.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => navigate(`/runs/${run.id}`)}
                  className="hover:bg-[#EAE2D6]/40 transition-colors cursor-pointer"
                >
                  <td className="py-3.5 px-6 whitespace-nowrap">
                    <StatusBadge status={run.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex flex-col">
                      <span className="font-semibold text-[#2E3325]">
                        {run.repository}{' '}
                        <span className="text-[#8A8E7C] font-normal">#{run.pr_number}</span>
                      </span>
                      <span className="text-[12px] text-[#5F664F] truncate max-w-xs">
                        {run.pr_title}
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className="font-mono text-[11px] px-1.5 py-0.5 bg-[#EAE2D6]/70 rounded border border-[#D9CFBF]/70 text-[#2E3325]">
                      {run.commit_sha}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-medium text-[#2E3325]">
                        {run.steps_completed} / {run.total_steps}
                      </span>
                      <div className="w-16 bg-[#EAE2D6] rounded-full h-1.5 overflow-hidden">
                        <div
                          className={clsx(
                            'h-1.5 rounded-full transition-all duration-300',
                            run.status === 'FAILED' && 'bg-[#8C4A3F]',
                            run.status === 'PAUSED' && 'bg-[#A88A4A]',
                            run.status === 'RUNNING' && 'bg-[#55633C] animate-pulse',
                            run.status === 'COMPLETED' && 'bg-[#55633C]',
                            run.status === 'STALE' && 'bg-[#8A8E7C]'
                          )}
                          style={{ width: `${(run.steps_completed / run.total_steps) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-[#8A8E7C]">
                        ({run.status === 'FAILED' ? 'Failed' : run.status === 'PAUSED' ? 'Sign-off' : run.status === 'COMPLETED' ? 'Done' : run.status === 'QUEUED' ? 'Queued' : 'Running'})
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap font-mono text-[12px]">
                    ${run.cost_usd > 0 && run.cost_usd < 0.01 ? run.cost_usd.toFixed(4) : run.cost_usd.toFixed(3)}
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap text-[#8A8E7C] text-[12px]">
                    {run.recorded_at_relative}
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/runs/${run.id}`);
                      }}
                      className="inline-flex items-center gap-1 text-[12px] text-[#55633C] hover:text-[#2E3325] font-medium transition-colors"
                    >
                      <span>Inspect trace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
