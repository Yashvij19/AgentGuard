import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Search,
  RefreshCw,
  Trash2,
  FilterX,
  Copy,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Clock,
  Send,
  X,
  FileCode,
} from 'lucide-react';
import { api } from '../services/api';
import { SystemLogItem } from '../types';
import clsx from 'clsx';

export const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<SystemLogItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Filters
  const [selectedSha, setSelectedSha] = useState<string>('');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Expandable inspection
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [copiedLogId, setCopiedLogId] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState<string | null>(null);

  // Manual Test Log Modal
  const [showTestModal, setShowTestModal] = useState<boolean>(false);
  const [testLevel, setTestLevel] = useState<string>('INFO');
  const [testSource, setTestSource] = useState<string>('policy_gateway');
  const [testApiName, setTestApiName] = useState<string>('evaluate_intent');
  const [testMessage, setTestMessage] = useState<string>('Developer manual diagnostic probe registered');
  const [testStatus, setTestStatus] = useState<string>('PASS');
  const [testSha, setTestSha] = useState<string>('c7b2399');
  const [submittingTest, setSubmittingTest] = useState<boolean>(false);

  const autoRefreshTimerRef = useRef<any>(null);

  // Fetch logs from backend
  const fetchLogs = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);

    try {
      const data = await api.getLogs({
        commit_sha: selectedSha || undefined,
        level: selectedLevel !== 'ALL' ? selectedLevel : undefined,
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        source: selectedSource !== 'ALL' ? selectedSource : undefined,
        search: searchQuery || undefined,
        limit: 100,
      });
      setLogs(data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error('Failed to load logs:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [selectedSha, selectedLevel, selectedStatus, selectedSource, searchQuery]);

  // Live Auto-Refresh polling
  useEffect(() => {
    if (autoRefresh) {
      autoRefreshTimerRef.current = setInterval(() => {
        fetchLogs(true);
      }, 4000);
    }
    return () => {
      if (autoRefreshTimerRef.current) clearInterval(autoRefreshTimerRef.current);
    };
  }, [autoRefresh, selectedSha, selectedLevel, selectedStatus, selectedSource, searchQuery]);

  // Extract unique active SHAs for quick filter pills
  const availableShas = Array.from(
    new Set(logs.map((l) => l.commit_sha).filter(Boolean) as string[])
  ).slice(0, 6);

  // Unique sources
  const availableSources = Array.from(
    new Set(logs.map((l) => l.source).filter(Boolean) as string[])
  );

  const handleCopyJson = (log: SystemLogItem, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(log, null, 2));
    setCopiedLogId(log.id);
    setTimeout(() => setCopiedLogId(null), 2000);
  };

  const handleCopySha = (sha: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sha);
    setCopiedSha(sha);
    setTimeout(() => setCopiedSha(null), 1500);
  };

  const handleDeleteLog = async (logId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Permanently delete this individual log entry from database?')) return;
    try {
      const ok = await api.deleteLog(logId);
      if (ok) {
        setLogs((prev) => prev.filter((l) => l.id !== logId));
        setTotalCount((c) => Math.max(0, c - 1));
      }
    } catch (err) {
      alert(`Delete failed: ${err}`);
    }
  };

  const handlePurgeLogs = async () => {
    const target = selectedSha ? `logs for SHA ${selectedSha}` : 'ALL 24-hour retained system logs';
    if (!confirm(`Are you sure you want to permanently purge ${target}?`)) return;

    try {
      const res = await api.purgeLogs(selectedSha || undefined);
      alert(`Purged ${res.purged_count} log entries.`);
      fetchLogs();
    } catch (err) {
      alert(`Purge failed: ${err}`);
    }
  };

  const handleEmitTestLog = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingTest(true);
    try {
      await api.createLog({
        level: testLevel as any,
        source: testSource,
        api_name: testApiName,
        message: testMessage,
        status: testStatus as any,
        commit_sha: testSha,
        task_progress: 'Manual Developer Probe',
        latency_ms: 42,
        extra_info: {
          test_probe: true,
          emitted_by: 'web_dashboard',
          user_agent: navigator.userAgent,
          utc_timestamp: new Date().toISOString(),
        },
      });
      setShowTestModal(false);
      setTestMessage('Developer manual diagnostic probe registered');
      fetchLogs(true);
    } catch (err) {
      alert(`Failed to emit log: ${err}`);
    } finally {
      setSubmittingTest(false);
    }
  };

  const clearFilters = () => {
    setSelectedSha('');
    setSelectedLevel('ALL');
    setSelectedStatus('ALL');
    setSelectedSource('ALL');
    setSearchQuery('');
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Page Header */}
      <div className="card-archival p-6 bg-[#FBF8F3]">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center pb-4 mb-4 border-b border-[#D9CFBF]/70 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="label-caps text-[#8A8E7C] text-[11px]">
                Developer Observability // System Logs
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-[#EAE2D6] text-[#55633C] border border-[#D9CFBF]">
                PostgreSQL • 24hr Auto-Expiry TTL
              </span>
            </div>
            <h1 className="font-serif text-[32px] text-[#2E3325] leading-tight font-medium mt-1">
              Developer System Logs & Action Telemetry
            </h1>
            <p className="text-[13px] text-[#5F664F] mt-1 max-w-3xl">
              Chronological ledger of API operations, task progress, invariant evaluations, and error diagnostics.
              All records adhere to a standardized JSON schema and automatically expire after 24 hours.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 flex-wrap self-end lg:self-auto">
            {/* Auto-Refresh Toggle */}
            <button
              type="button"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={clsx(
                'inline-flex items-center gap-2 px-3 py-1.5 rounded text-[12px] font-medium transition-colors border cursor-pointer select-none',
                autoRefresh
                  ? 'bg-[#E3E8D6] text-[#2E3325] border-[#BDCD9D]'
                  : 'bg-[#F7F2EB] text-[#8A8E7C] border-[#D9CFBF]'
              )}
              title="Toggle 4-second live streaming polling"
            >
              <span
                className={clsx(
                  'w-2 h-2 rounded-full',
                  autoRefresh ? 'bg-[#55633C] animate-pulse' : 'bg-[#8A8E7C]'
                )}
              />
              <span>{autoRefresh ? 'Live Stream ON' : 'Live Stream Paused'}</span>
            </button>

            {/* Manual Refresh */}
            <button
              type="button"
              onClick={() => fetchLogs(true)}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#F7F2EB] hover:bg-[#EAE2D6] text-[#2E3325] text-[12px] font-medium transition-colors border border-[#D9CFBF] cursor-pointer"
            >
              <RefreshCw className={clsx('w-3.5 h-3.5 text-[#55633C]', isRefreshing && 'animate-spin')} />
              <span>Refresh</span>
            </button>

            {/* Emit Test Log */}
            <button
              type="button"
              onClick={() => setShowTestModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#55633C] hover:bg-[#2E3325] text-[#F7F2EB] text-[12px] font-medium transition-colors cursor-pointer shadow-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Emit Test Log</span>
            </button>

            {/* Purge Logs */}
            <button
              type="button"
              onClick={handlePurgeLogs}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#EFDCD6] hover:bg-[#8C4A3F] text-[#8C4A3F] hover:text-[#F7F2EB] text-[12px] font-medium transition-colors border border-[#D9AFA6] cursor-pointer"
              title="Purge logs manually from database"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{selectedSha ? `Purge SHA` : 'Purge All'}</span>
            </button>
          </div>
        </div>

        {/* Quick SHA Chips & Search Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-1">
          {/* Quick SHA filter pills */}
          <div className="flex items-center gap-2 flex-wrap text-[12px]">
            <span className="label-caps text-[#8A8E7C] text-[10px] shrink-0">Recent SHAs:</span>
            {availableShas.length === 0 ? (
              <span className="text-[#8A8E7C] font-mono text-[11px]">—</span>
            ) : (
              availableShas.map((sha) => (
                <button
                  key={sha}
                  type="button"
                  onClick={() => setSelectedSha(selectedSha === sha ? '' : sha)}
                  className={clsx(
                    'font-mono text-[11px] px-2 py-0.5 rounded border transition-colors cursor-pointer',
                    selectedSha === sha
                      ? 'bg-[#2E3325] text-[#FBF8F3] border-[#2E3325]'
                      : 'bg-[#EAE2D6]/70 text-[#2E3325] border-[#D9CFBF] hover:bg-[#D9CFBF]'
                  )}
                >
                  {sha.substring(0, 7)}
                </button>
              ))
            )}
            {selectedSha && (
              <button
                type="button"
                onClick={() => setSelectedSha('')}
                className="text-[11px] text-[#8C4A3F] hover:underline cursor-pointer ml-1"
              >
                Clear SHA
              </button>
            )}
          </div>

          {/* Search Input */}
          <div className="relative w-full md:w-80">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search message, API name, or payload..."
              className="w-full bg-[#F7F2EB] border border-[#D9CFBF] text-[#2E3325] placeholder:text-[#8A8E7C] pl-8 pr-3 py-1.5 rounded text-[13px] focus:outline-none focus:border-[#55633C] transition-colors"
            />
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#8A8E7C]" />
          </div>
        </div>
      </div>

      {/* Filter Matrix Card */}
      <div className="card-archival p-4 bg-[#FBF8F3] flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Level Filter Pills */}
          <div className="flex items-center gap-1.5 flex-wrap select-none">
            <span className="label-caps text-[#8A8E7C] text-[10px] mr-1">Level:</span>
            {['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG'].map((lvl) => {
              const isActive = selectedLevel === lvl;
              return (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setSelectedLevel(lvl)}
                  className={clsx(
                    'px-2.5 py-1 rounded text-[11px] font-sans font-semibold tracking-wider uppercase transition-colors cursor-pointer',
                    isActive
                      ? 'bg-[#2E3325] text-[#FBF8F3]'
                      : 'bg-[#F7F2EB] text-[#5F664F] border border-[#D9CFBF]/70 hover:bg-[#EAE2D6]'
                  )}
                >
                  {lvl}
                </button>
              );
            })}
          </div>

          {/* Status Filter Pills */}
          <div className="flex items-center gap-1.5 flex-wrap select-none">
            <span className="label-caps text-[#8A8E7C] text-[10px] mr-1">Status:</span>
            {['ALL', 'PASS', 'FAIL', 'WAITING', 'RUNNING'].map((st) => {
              const isActive = selectedStatus === st;
              return (
                <button
                  key={st}
                  type="button"
                  onClick={() => setSelectedStatus(st)}
                  className={clsx(
                    'px-2.5 py-1 rounded text-[11px] font-sans font-semibold tracking-wider uppercase transition-colors cursor-pointer',
                    isActive
                      ? st === 'FAIL'
                        ? 'bg-[#8C4A3F] text-[#FBF8F3]'
                        : st === 'PASS'
                        ? 'bg-[#55633C] text-[#FBF8F3]'
                        : 'bg-[#A88A4A] text-[#FBF8F3]'
                      : 'bg-[#F7F2EB] text-[#5F664F] border border-[#D9CFBF]/70 hover:bg-[#EAE2D6]'
                  )}
                >
                  {st}
                </button>
              );
            })}
          </div>

          {/* Subsystem Dropdown & Clear */}
          <div className="flex items-center gap-2">
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="bg-[#F7F2EB] border border-[#D9CFBF] text-[#2E3325] text-[12px] px-2.5 py-1 rounded focus:outline-none focus:border-[#55633C]"
            >
              <option value="ALL">All Subsystems</option>
              {availableSources.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            {(selectedSha || selectedLevel !== 'ALL' || selectedStatus !== 'ALL' || selectedSource !== 'ALL' || searchQuery) && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex items-center gap-1 text-[12px] text-[#8C4A3F] hover:underline cursor-pointer"
              >
                <FilterX className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card-archival overflow-hidden flex flex-col">
        <div className="p-4 bg-[#EAE2D6]/50 border-b border-[#D9CFBF] flex items-center justify-between text-[12px] text-[#5F664F] font-mono">
          <span>Showing {logs.length} of {totalCount} log records</span>
          <span>Retention: 24 Hours • Append-Only</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#EAE2D6]/70 text-[#5F664F] label-caps border-b border-[#D9CFBF] select-none text-[11px]">
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-3">Level</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Subsystem</th>
                <th className="py-3 px-4">API / Task</th>
                <th className="py-3 px-4">Message</th>
                <th className="py-3 px-3">Commit SHA</th>
                <th className="py-3 px-3 text-right">Payload</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#D9CFBF]/60 text-[12px] text-[#2E3325]">
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-[#5F664F] font-serif text-[16px]">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-[#55633C]" />
                      <span>Loading developer system logs...</span>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-[#5F664F] font-mono text-[13px]">
                    No system logs matching current query.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  const isError = log.level === 'ERROR' || log.status === 'FAIL';
                  const extraKeys = Object.keys(log.extra_info || {});

                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                        className={clsx(
                          'hover:bg-[#EAE2D6]/50 transition-colors cursor-pointer select-none',
                          isExpanded && 'bg-[#EAE2D6]/70',
                          isError && 'bg-[#EFDCD6]/30'
                        )}
                      >
                        {/* Timestamp */}
                        <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px] text-[#5F664F]">
                          <div>
                            {new Date(log.timestamp).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })}
                          </div>
                          <div className="text-[10px] text-[#8A8E7C]">
                            {new Date(log.timestamp).toISOString().substring(0, 10)}
                          </div>
                        </td>

                        {/* Level */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={clsx(
                              'px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase',
                              log.level === 'ERROR' && 'bg-[#EFDCD6] text-[#8C4A3F] border border-[#D9AFA6]',
                              log.level === 'WARNING' && 'bg-[#F0E6CF] text-[#5A4308] border border-[#E4C27C]',
                              log.level === 'INFO' && 'bg-[#E3E8D6] text-[#55633C] border border-[#BDCD9D]',
                              log.level === 'DEBUG' && 'bg-[#EAE2D6] text-[#5F664F] border border-[#D9CFBF]'
                            )}
                          >
                            {log.level}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={clsx(
                              'px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase inline-flex items-center gap-1',
                              log.status === 'PASS' && 'bg-[#E3E8D6] text-[#55633C]',
                              log.status === 'FAIL' && 'bg-[#EFDCD6] text-[#8C4A3F]',
                              log.status === 'WAITING' && 'bg-[#F0E6CF] text-[#5A4308]',
                              log.status === 'RUNNING' && 'bg-[#EAE2D6] text-[#2E3325]'
                            )}
                          >
                            {log.status === 'PASS' ? (
                              <CheckCircle2 className="w-3 h-3 text-[#55633C]" />
                            ) : log.status === 'FAIL' ? (
                              <AlertCircle className="w-3 h-3 text-[#8C4A3F]" />
                            ) : (
                              <Clock className="w-3 h-3 text-[#A88A4A]" />
                            )}
                            <span>{log.status}</span>
                          </span>
                        </td>

                        {/* Subsystem */}
                        <td className="py-3 px-3 whitespace-nowrap font-mono text-[11px] text-[#2E3325]">
                          <span className="bg-[#EAE2D6] px-1.5 py-0.5 rounded">
                            {log.source}
                          </span>
                        </td>

                        {/* API / Task Progress */}
                        <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px]">
                          <div className="font-semibold text-[#2E3325]">{log.api_name || '—'}</div>
                          {log.task_progress && (
                            <div className="text-[10px] text-[#8A8E7C] truncate max-w-[140px]">
                              {log.task_progress}
                            </div>
                          )}
                        </td>

                        {/* Message */}
                        <td className="py-3 px-4 text-[13px] text-[#2E3325] max-w-md">
                          <div className="line-clamp-2 leading-relaxed">
                            {log.message}
                          </div>
                          {log.extra_info?.error && (
                            <div className="text-[11px] text-[#8C4A3F] font-mono mt-0.5 truncate">
                              Err: {String(log.extra_info.error).split('\n')[0]}
                            </div>
                          )}
                        </td>

                        {/* Commit SHA */}
                        <td className="py-3 px-3 whitespace-nowrap font-mono text-[11px]">
                          {log.commit_sha ? (
                            <button
                              type="button"
                              onClick={(e) => handleCopySha(log.commit_sha!, e)}
                              className="px-1.5 py-0.5 rounded bg-[#EAE2D6] hover:bg-[#D9CFBF] text-[#2E3325] border border-[#D9CFBF] transition-colors cursor-pointer"
                              title="Click to copy SHA"
                            >
                              {copiedSha === log.commit_sha ? 'Copied' : log.commit_sha.substring(0, 7)}
                            </button>
                          ) : (
                            <span className="text-[#8A8E7C]">—</span>
                          )}
                        </td>

                        {/* Payload Button */}
                        <td className="py-3 px-3 whitespace-nowrap text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedLogId(isExpanded ? null : log.id);
                            }}
                            className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-1 rounded bg-[#F7F2EB] hover:bg-[#EAE2D6] border border-[#D9CFBF] text-[#55633C] cursor-pointer"
                          >
                            <Terminal className="w-3 h-3" />
                            <span>JSON ({extraKeys.length})</span>
                            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                          </button>
                        </td>

                        {/* Delete Single Log */}
                        <td className="py-3 px-3 whitespace-nowrap text-right">
                          <button
                            type="button"
                            onClick={(e) => handleDeleteLog(log.id, e)}
                            className="p-1 text-[#8A8E7C] hover:text-[#8C4A3F] transition-colors cursor-pointer rounded hover:bg-[#EFDCD6]"
                            title="Delete log entry"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>

                      {/* Expandable JSON Inspector Drawer */}
                      {isExpanded && (
                        <tr className="bg-[#2E3325] text-[#FBF8F3]">
                          <td colSpan={9} className="p-4">
                            <div className="flex flex-col gap-2">
                              <div className="flex items-center justify-between border-b border-[#55633C]/50 pb-2">
                                <div className="flex items-center gap-2 font-mono text-[12px] text-[#BDCD9D]">
                                  <FileCode className="w-4 h-4 text-[#A88A4A]" />
                                  <span>Log Record Payload // UUID: {log.id}</span>
                                  {log.latency_ms > 0 && (
                                    <span className="text-[#8A8E7C]">({log.latency_ms}ms)</span>
                                  )}
                                </div>
                                <button
                                  type="button"
                                  onClick={(e) => handleCopyJson(log, e)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#3C4231] hover:bg-[#55633C] text-[#FBF8F3] text-[11px] font-mono transition-colors cursor-pointer border border-[#55633C]"
                                >
                                  {copiedLogId === log.id ? (
                                    <>
                                      <CheckCheck className="w-3.5 h-3.5 text-[#BDCD9D]" />
                                      <span>Copied JSON</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3.5 h-3.5" />
                                      <span>Copy Complete JSON</span>
                                    </>
                                  )}
                                </button>
                              </div>

                              <pre className="p-3 bg-[#1C2018] rounded font-mono text-[11px] overflow-x-auto max-h-72 leading-relaxed text-[#D9CFBF] border border-[#55633C]/40">
                                {JSON.stringify(log, null, 2)}
                              </pre>

                              {log.extra_info?.error && (
                                <div className="p-2.5 bg-[#8C4A3F]/20 border border-[#8C4A3F] rounded text-[#EFDCD6] text-[12px] font-mono whitespace-pre-wrap">
                                  <strong>Error Output:</strong> {log.extra_info.error}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Test Log Modal */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 bg-[#2E3325]/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="card-archival w-full max-w-lg p-6 bg-[#FBF8F3] shadow-2xl animate-fade-in border border-[#D9CFBF]">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#D9CFBF]">
              <div className="flex items-center gap-2">
                <Send className="w-4 h-4 text-[#55633C]" />
                <h3 className="font-serif text-[20px] font-medium text-[#2E3325]">
                  Emit Developer System Log
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowTestModal(false)}
                className="text-[#8A8E7C] hover:text-[#2E3325] p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleEmitTestLog} className="flex flex-col gap-4 text-[13px]">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                    Log Level
                  </label>
                  <select
                    value={testLevel}
                    onChange={(e) => setTestLevel(e.target.value)}
                    className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 text-[#2E3325]"
                  >
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                    <option value="DEBUG">DEBUG</option>
                  </select>
                </div>
                <div>
                  <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                    Status
                  </label>
                  <select
                    value={testStatus}
                    onChange={(e) => setTestStatus(e.target.value)}
                    className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 text-[#2E3325]"
                  >
                    <option value="PASS">PASS</option>
                    <option value="FAIL">FAIL</option>
                    <option value="WAITING">WAITING</option>
                    <option value="RUNNING">RUNNING</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                    Subsystem / Source
                  </label>
                  <input
                    type="text"
                    value={testSource}
                    onChange={(e) => setTestSource(e.target.value)}
                    className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 font-mono text-[12px] text-[#2E3325]"
                  />
                </div>
                <div>
                  <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                    API / Operation Name
                  </label>
                  <input
                    type="text"
                    value={testApiName}
                    onChange={(e) => setTestApiName(e.target.value)}
                    className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 font-mono text-[12px] text-[#2E3325]"
                  />
                </div>
              </div>

              <div>
                <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                  Commit SHA Correlation
                </label>
                <input
                  type="text"
                  value={testSha}
                  onChange={(e) => setTestSha(e.target.value)}
                  placeholder="e.g. c7b2399"
                  className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 font-mono text-[12px] text-[#2E3325]"
                />
              </div>

              <div>
                <label className="label-caps text-[#8A8E7C] text-[10px] block mb-1">
                  Log Message
                </label>
                <textarea
                  rows={3}
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded px-3 py-1.5 text-[#2E3325]"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#D9CFBF]">
                <button
                  type="button"
                  onClick={() => setShowTestModal(false)}
                  className="px-3.5 py-1.5 rounded bg-[#F7F2EB] hover:bg-[#EAE2D6] text-[#5F664F] text-[13px] border border-[#D9CFBF] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingTest}
                  className="px-4 py-1.5 rounded bg-[#55633C] hover:bg-[#2E3325] text-[#F7F2EB] text-[13px] font-medium transition-colors cursor-pointer shadow-xs"
                >
                  {submittingTest ? 'Emitting...' : 'Emit Log'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
