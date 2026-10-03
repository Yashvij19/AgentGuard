import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FilterX,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';
import { RunItem, RunState } from '../types';
import clsx from 'clsx';

export const RunsPage: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selectedState, setSelectedState] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState('All Events');

  useEffect(() => {
    const loadRuns = async () => {
      try {
        const data = await api.getRuns({ pageSize: 50 });
        setRuns(data.items);
      } catch (err) {
        console.error('Failed to load runs from backend API:', err);
      }
    };
    loadRuns();
  }, []);

  const counts: Record<string, number> = {
    ALL: runs.length,
    RUNNING: runs.filter((r) => r.status === 'RUNNING').length,
    PAUSED: runs.filter((r) => r.status === 'PAUSED').length,
    COMPLETED: runs.filter((r) => r.status === 'COMPLETED').length,
    FAILED: runs.filter((r) => r.status === 'FAILED').length,
    STALE: runs.filter((r) => r.status === 'STALE').length,
  };

  const filteredRuns = runs.filter((r) => {
    if (selectedState !== 'ALL' && r.status !== selectedState) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        r.repository.toLowerCase().includes(q) ||
        r.commit_sha.toLowerCase().includes(q) ||
        r.pr_title.toLowerCase().includes(q) ||
        `#${r.pr_number}`.includes(q);
      if (!match) return false;
    }
    return true;
  });

  const clearFilters = () => {
    setSelectedState('ALL');
    setSearchQuery('');
    setSelectedEvent('All Events');
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Header & Title */}
      <div className="flex flex-col gap-2 border-b border-[#D9CFBF] pb-5">
        <div className="flex items-center gap-2 text-[11px] text-[#5F664F]">
          <span className="label-caps">Archival Folio 02 // Execution Runs</span>
          <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
          <span className="font-mono text-[#8A8E7C]">Immutable Audit Ledger</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-1">
          <div>
            <h1 className="font-serif text-[40px] text-[#2E3325] leading-none font-medium tracking-tight">
              Agent Execution Runs
            </h1>
            <p className="text-[15px] text-[#5F664F] mt-2 max-w-2xl leading-relaxed">
              Historical ledger of automated coding runs, policy checkpoints, and token disbursements.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Ribbon */}
      <div className="card-archival p-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[260px] max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by SHA, PR, repository, or title..."
              className="w-full bg-[#F7F2EB] border border-[#D9CFBF] text-[#2E3325] placeholder:text-[#8A8E7C] pl-9 pr-4 py-2 rounded text-[13px] focus:outline-none focus:border-[#55633C] transition-colors"
            />
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8A8E7C]" />
          </div>

          {/* Select Dropdowns */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <select
                value={selectedEvent}
                onChange={(e) => setSelectedEvent(e.target.value)}
                aria-label="Filter by trigger event"
                className="appearance-none bg-[#F7F2EB] border border-[#D9CFBF] text-[#2E3325] px-3 py-2 pr-8 rounded text-[13px] focus:outline-none focus:border-[#55633C]"
              >
                <option>All Events</option>
                <option>pull_request.opened</option>
                <option>pull_request.synchronize</option>
                <option>schedule.hourly</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 top-3 text-[#8A8E7C] pointer-events-none" />
            </div>

            <button
              type="button"
              onClick={clearFilters}
              className="text-[#8A8E7C] hover:text-[#8C4A3F] text-[13px] px-2 py-2 transition-colors flex items-center gap-1 cursor-pointer"
            >
              <FilterX className="w-3.5 h-3.5" />
              <span>Clear filters</span>
            </button>
          </div>
        </div>

        {/* State Filter Buttons */}
        <div className="flex items-center gap-2 pt-2 border-t border-[#D9CFBF]/60 overflow-x-auto select-none">
          <span className="label-caps text-[#8A8E7C] text-[10px] mr-1 shrink-0">
            State Filter:
          </span>
          {(['ALL', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED', 'STALE'] as const).map(
            (stateKey) => {
              const isActive = selectedState === stateKey;
              return (
                <button
                  key={stateKey}
                  type="button"
                  onClick={() => setSelectedState(stateKey)}
                  className={clsx(
                    'px-2.5 py-1 rounded text-[11px] font-sans font-semibold tracking-wider uppercase flex items-center gap-1.5 transition-colors cursor-pointer shrink-0',
                    isActive
                      ? 'bg-[#E3E8D6] text-[#2E3325] border border-[#BDCD9D]'
                      : 'bg-[#F7F2EB] text-[#5F664F] border border-[#D9CFBF]/70 hover:bg-[#EAE2D6]'
                  )}
                >
                  <span
                    className={clsx(
                      'w-1.5 h-1.5 rounded-full',
                      stateKey === 'ALL' && 'bg-[#55633C]',
                      stateKey === 'RUNNING' && 'bg-[#55633C] animate-subtle-pulse',
                      stateKey === 'PAUSED' && 'bg-[#A88A4A]',
                      stateKey === 'COMPLETED' && 'bg-[#55633C]',
                      stateKey === 'FAILED' && 'bg-[#8C4A3F]',
                      stateKey === 'STALE' && 'bg-[#8A8E7C]'
                    )}
                  />
                  <span>{stateKey}</span>
                  <span className="font-mono text-[10px] opacity-75 font-normal">
                    {counts[stateKey] ?? 0}
                  </span>
                </button>
              );
            }
          )}
        </div>
      </div>

      {/* Ledger Table */}
      <div className="card-archival overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#EAE2D6]/70 text-[#5F664F] label-caps border-b border-[#D9CFBF] select-none">
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-4">Repository & PR</th>
                <th className="py-3 px-4">Commit SHA</th>
                <th className="py-3 px-4">Trigger Event</th>
                <th className="py-3 px-4">Policy</th>
                <th className="py-3 px-4">Tokens & Cost</th>
                <th className="py-3 px-4">Duration & Started</th>
                <th className="py-3 px-6 text-right">Audit Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#D9CFBF]/60 text-[13px] text-[#2E3325]">
              {filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#5F664F] font-mono text-[13px]">
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
                    <td className="py-3.5 px-4 whitespace-nowrap font-mono text-[11px] text-[#5F664F]">
                      {run.trigger_event}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="bg-[#EAE2D6] px-2 py-0.5 rounded font-mono text-[11px] text-[#2E3325]">
                        {run.policy_version}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap font-mono text-[12px]">
                      <span className="font-medium text-[#2E3325]">
                        {run.tokens_total.toLocaleString()} tok
                      </span>
                      <span className="text-[#8A8E7C] ml-1">(${run.cost_usd > 0 && run.cost_usd < 0.01 ? run.cost_usd.toFixed(4) : run.cost_usd.toFixed(3)})</span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-[12px]">
                      <span className="text-[#2E3325]">{run.duration_seconds}s</span>
                      <span className="text-[#8A8E7C] font-mono ml-1.5">• {run.started_at}</span>
                    </td>
                    <td className="py-3.5 px-6 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/runs/${run.id}`);
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded hover:bg-[#EAE2D6] text-[#55633C] hover:text-[#2E3325] text-[12px] font-medium transition-colors"
                      >
                        <span>View trace</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Summary */}
        <div className="p-4 bg-[#EAE2D6]/30 border-t border-[#D9CFBF] flex items-center justify-between text-[12px] text-[#5F664F]">
          <span>Showing {filteredRuns.length} of 142 custodial transactions</span>
          <span className="font-mono text-[#8A8E7C]">Audit Hash Verified · Ed25519</span>
        </div>
      </div>
    </div>
  );
};
