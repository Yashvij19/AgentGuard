import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Activity,
  Timer,
  Wallet,
  Sliders,
  CheckCircle,
  SlidersHorizontal,
  ArrowRightLeft,
  ShieldCheck,
  Sparkles,
  Layers,
  KeyRound,
} from 'lucide-react';
import { ProviderCard } from '../components/common/ProviderCard';
import { api } from '../services/api';
import { ProviderHealth, LLMProvidersConfig, ProviderConfigItem, StatsSummary } from '../types';

export const LLMProvidersPage: React.FC = () => {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [llmConfig, setLlmConfig] = useState<LLMProvidersConfig | null>(null);
  const [defaultPrimary, setDefaultPrimary] = useState<string>('gemini');
  const [defaultFallback, setDefaultFallback] = useState<string>('groq');
  const [providerRoles, setProviderRoles] = useState<Record<string, string>>({});
  const [providerModels, setProviderModels] = useState<Record<string, string>>({});
  const [providerTasks, setProviderTasks] = useState<Record<string, string[]>>({});
  const [isSavingRoles, setIsSavingRoles] = useState<boolean>(false);

  const [selectedPreset, setSelectedPreset] = useState('Standard Production Mesh');
  const [consecutiveFailures, setConsecutiveFailures] = useState(3);
  const [probeIntervalSeconds, setProbeIntervalSeconds] = useState(60);
  const [recoveryThreshold, setRecoveryThreshold] = useState(5);
  const [notification, setNotification] = useState<string | null>(null);

  const loadConfig = async () => {
    try {
      const config = await api.getProvidersConfig();
      setLlmConfig(config);

      const activeProviders = config.providers.filter((p) => p.is_active);
      const activePrimary = activeProviders.find((p) => p.name === config.default_primary)
        ? config.default_primary
        : activeProviders[0]?.name || config.default_primary;

      const activeFallback = activeProviders.find((p) => p.name === config.default_fallback && p.name !== activePrimary)
        ? config.default_fallback
        : activeProviders.find((p) => p.name !== activePrimary)?.name || config.default_fallback;

      setDefaultPrimary(activePrimary);
      setDefaultFallback(activeFallback);

      const roles: Record<string, string> = {};
      const models: Record<string, string> = {};
      const tasks: Record<string, string[]> = {};
      config.providers.forEach((p) => {
        roles[p.name] = p.name === activePrimary ? 'primary' : p.name === activeFallback ? 'fallback' : p.role || 'specialist';
        models[p.name] = p.selected_model || p.models[0] || '';
        tasks[p.name] = p.task_types || [];
      });
      setProviderRoles(roles);
      setProviderModels(models);
      setProviderTasks(tasks);
    } catch (err) {
      console.error('Failed to load LLM providers config:', err);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        const [data, s] = await Promise.all([
          api.getProvidersHealth(),
          api.getStats(),
        ]);
        setProviders(data);
        setStats(s);
        await loadConfig();
      } catch (err) {
        console.error('Failed to load telemetry in LLM providers page:', err);
      }
    };
    loadData();
  }, []);

  const handleTripProvider = async (id: string) => {
    const prov = providers.find((p: ProviderHealth) => p.id === id);
    if (!prov) return;
    try {
      const res = await api.tripProvider(prov.provider_name);
      const updated = await api.getProvidersHealth();
      setProviders(updated);
      setNotification(res.message);
    } catch (err) {
      console.error('Failed to trip provider circuit:', err);
      setNotification(`Failed to trip circuit for ${prov.provider_name}.`);
    }
    setTimeout(() => setNotification(null), 3500);
  };

  const handleResetProvider = async (id: string) => {
    const prov = providers.find((p: ProviderHealth) => p.id === id);
    if (!prov) return;
    try {
      const res = await api.resetProvider(prov.provider_name);
      const updated = await api.getProvidersHealth();
      setProviders(updated);
      setNotification(res.message);
    } catch (err) {
      console.error('Failed to reset provider circuit:', err);
      setNotification(`Failed to reset circuit for ${prov.provider_name}.`);
    }
    setTimeout(() => setNotification(null), 3500);
  };

  const handleSaveTuning = async () => {
    try {
      await api.saveCircuitTuning({
        failure_threshold_pct: 10.0,
        consecutive_timeouts: consecutiveFailures,
        cooldown_period_seconds: probeIntervalSeconds,
        probes_required: recoveryThreshold,
        auto_fallback_enabled: true,
      });
      setNotification('Circuit breaker policy tuning parameters saved to governance engine.');
    } catch (err) {
      console.error('Failed to tune circuit parameters:', err);
      setNotification('Failed to save tuning parameters to backend.');
    }
    setTimeout(() => setNotification(null), 3500);
  };

  const handleApplyPreset = (preset: string) => {
    setSelectedPreset(preset);
    if (preset === 'Local-Only') {
      setProviders((prev: ProviderHealth[]) =>
        prev.map((p: ProviderHealth) => ({
          ...p,
          circuit_state: p.id.includes('local') ? 'CLOSED' : 'OPEN',
        }))
      );
      setNotification('Mesh isolated to on-prem air-gapped vLLM fallback.');
    } else {
      api.getProvidersHealth().then(setProviders);
      setNotification(`Preset '${preset}' applied across reasoning cluster.`);
    }
    setTimeout(() => setNotification(null), 3500);
  };

  const handleRoleChange = (providerName: string, role: string) => {
    const prov = llmConfig?.providers.find((p) => p.name === providerName);
    if (prov && !prov.is_active) return;

    setProviderRoles((prev: Record<string, string>) => {
      const updated = { ...prev };
      if (role === 'primary') {
        Object.keys(updated).forEach((k) => {
          if (updated[k] === 'primary' && k !== providerName) {
            updated[k] = defaultFallback === k ? 'fallback' : 'specialist';
          }
        });
        updated[providerName] = 'primary';
      } else if (role === 'fallback') {
        Object.keys(updated).forEach((k) => {
          if (updated[k] === 'fallback' && k !== providerName) {
            updated[k] = 'specialist';
          }
        });
        updated[providerName] = 'fallback';
      } else {
        updated[providerName] = 'specialist';
      }
      return updated;
    });

    if (role === 'primary') {
      setDefaultPrimary(providerName);
    } else if (role === 'fallback') {
      setDefaultFallback(providerName);
    }
  };

  const handleModelChange = (providerName: string, model: string) => {
    setProviderModels((prev: Record<string, string>) => ({
      ...prev,
      [providerName]: model,
    }));
  };

  const handleToggleTask = (providerName: string, taskType: string) => {
    const prov = llmConfig?.providers.find((p: ProviderConfigItem) => p.name === providerName);
    if (prov && !prov.is_active) return;
    setProviderTasks((prev: Record<string, string[]>) => {
      const current = prev[providerName] || [];
      const next = current.includes(taskType)
        ? current.filter((t: string) => t !== taskType)
        : [...current, taskType];
      return { ...prev, [providerName]: next };
    });
  };

  const handleSaveRoles = async () => {
    setIsSavingRoles(true);
    try {
      const res = await api.updateProviderRoles({
        default_primary: defaultPrimary,
        default_fallback: defaultFallback,
        provider_roles: providerRoles,
        provider_models: providerModels,
        provider_task_types: providerTasks,
      });
      setNotification(res.message || 'LLM provider roles and routing updated in runtime gateway.');
      window.dispatchEvent(new CustomEvent('llm_provider_changed'));
      await Promise.all([
        loadConfig(),
        api.getProvidersHealth().then(setProviders),
      ]);
    } catch (err) {
      console.error('Failed to update LLM provider roles:', err);
      setNotification('Failed to update LLM provider roles. Check backend logs.');
    } finally {
      setIsSavingRoles(false);
      setTimeout(() => setNotification(null), 4000);
    }
  };

  // Dynamic Fleet Metric Calculations from live API & DB
  const activeProvidersCount = llmConfig?.providers.filter((p) => p.is_active).length || 0;
  const totalConfigured = llmConfig?.providers.length || 0;
  const restingProvidersCount = Math.max(0, totalConfigured - activeProvidersCount);
  const capacityPct = totalConfigured > 0 ? Math.round((activeProvidersCount / totalConfigured) * 100) : 0;

  const totalProvidersMonitored = providers.length;
  const avgErrorRate =
    totalProvidersMonitored > 0
      ? providers.reduce((acc, p) => acc + (p.error_rate_pct || 0), 0) / totalProvidersMonitored
      : 0;

  const avgLatency =
    totalProvidersMonitored > 0
      ? Math.round(providers.reduce((acc, p) => acc + (p.latency_ms || 0), 0) / totalProvidersMonitored)
      : 0;

  const dailySpend = stats?.compute_expenditure_usd ?? 0;
  const dailyTokensK = stats?.compute_tokens_k ?? 0;
  const budgetBurnPct = stats?.budget_burn_pct ?? 0;

  return (
    <div className="flex flex-col gap-8">
      {/* Folio Header */}
      <div className="flex flex-col gap-2 border-b border-[#D9CFBF] pb-5">
        <div className="flex items-center gap-2 text-[11px] text-[#5F664F]">
          <span className="label-caps">Archival Folio 05 // Inference Mesh & Circuit Breakers</span>
          <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
          <span className="font-mono text-[#8A8E7C]">Self-Healing Telemetry Bus</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-1">
          <div>
            <h1 className="font-serif text-[40px] text-[#2E3325] leading-none font-medium tracking-tight">
              Language Model Providers & Failover Mesh
            </h1>
            <p className="text-[15px] text-[#5F664F] mt-2 max-w-2xl leading-relaxed">
              Circuit breaker trip thresholds, fallback cascades, and real-time inference telemetry for model providers.
            </p>
          </div>

          {/* Preset Selector */}
          <div className="flex items-center gap-2">
            <span className="label-caps text-[#8A8E7C] text-[10px]">Mesh Preset:</span>
            <select
              value={selectedPreset}
              onChange={(e) => handleApplyPreset(e.target.value)}
              className="bg-[#FBF8F3] border border-[#D9CFBF] text-[#2E3325] px-3 py-1.5 rounded text-[13px] focus:outline-none focus:border-[#55633C] cursor-pointer"
            >
              <option>Standard Production Mesh</option>
              <option>High-Throughput LPU Priority</option>
              <option value="Local-Only">Force Local Air-Gap (vLLM Only)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className="p-3 bg-[#E3E8D6] text-[#2E3325] border border-[#BDCD9D] rounded text-[13px] font-medium flex items-center justify-between animate-rise-in">
          <span>{notification}</span>
          <button onClick={() => setNotification(null)} className="text-[#55633C]">
            ✕
          </button>
        </div>
      )}

      {/* 4 Summary Fleet Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 */}
        <div className="card-archival p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#5F664F]">Active Mesh Status</span>
            <Cpu className="w-4 h-4 text-[#55633C]" />
          </div>
          <div className="my-2">
            <div className="font-serif text-[26px] font-medium text-[#2E3325]">
              {activeProvidersCount} Active{' '}
              <span className="text-[14px] text-[#8A8E7C] font-normal">
                / {restingProvidersCount} Resting
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-1 font-mono text-[11px] text-[#55633C]">
              <span className="w-2 h-2 rounded-full bg-[#55633C]" />
              <span>{capacityPct}% Available Capacity</span>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="card-archival p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#5F664F]">Fleet Error Rate (15m)</span>
            <Activity className="w-4 h-4 text-[#5F664F]" />
          </div>
          <div className="my-2">
            <div className="font-serif text-[26px] font-medium text-[#2E3325]">
              {avgErrorRate.toFixed(2)}%{' '}
              {totalProvidersMonitored > 0 ? (
                <span className="font-mono text-[11px] text-[#55633C]">
                  {avgErrorRate === 0 ? '✓ Nominal' : 'Active'}
                </span>
              ) : (
                <span className="font-mono text-[11px] text-[#8A8E7C]">0 req</span>
              )}
            </div>
            <span className="text-[12px] text-[#8A8E7C] mt-1 block">
              {totalProvidersMonitored === 0
                ? 'No calls recorded in window'
                : avgErrorRate <= 2.0
                ? 'Well below 2.00% safe threshold'
                : 'Elevated error threshold'}
            </span>
          </div>
        </div>

        {/* Card 3 */}
        <div className="card-archival p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#5F664F]">Fleet Avg Latency</span>
            <Timer className="w-4 h-4 text-[#5F664F]" />
          </div>
          <div className="my-2">
            <div className="font-serif text-[26px] font-medium text-[#2E3325]">
              {avgLatency > 0 ? `${avgLatency} ms` : '0 ms'}{' '}
              <span className="font-mono text-[11px] text-[#8A8E7C]">
                {totalProvidersMonitored > 0 ? `p50: ${avgLatency}ms` : 'Idle'}
              </span>
            </div>
            <span className="text-[12px] text-[#8A8E7C] mt-1 block">
              {totalProvidersMonitored === 0
                ? 'Awaiting pipeline execution'
                : `${totalProvidersMonitored} provider nodes monitored`}
            </span>
          </div>
        </div>

        {/* Card 4 */}
        <div className="card-archival p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#5F664F]">Daily Ledger Spend</span>
            <Wallet className="w-4 h-4 text-[#5F664F]" />
          </div>
          <div className="my-2">
            <div className="font-serif text-[26px] font-medium text-[#2E3325]">
              ${dailySpend.toFixed(2)}{' '}
              <span className="font-mono text-[11px] text-[#8A8E7C]">
                {dailyTokensK}k tok
              </span>
            </div>
            <div className="w-full bg-[#EAE2D6] rounded-full h-1 mt-2 overflow-hidden">
              <div
                className="bg-[#55633C] h-1 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, budgetBurnPct))}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Model Routing & Role Assignment Matrix */}
      <div className="card-archival p-6 flex flex-col gap-6 border-l-4 border-l-[#55633C]">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#D9CFBF] gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#55633C]/10 rounded-md text-[#55633C]">
              <ArrowRightLeft className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-serif text-[22px] font-medium text-[#2E3325]">
                Model Routing & Dynamic Role Assignment
              </h2>
              <p className="text-[13px] text-[#5F664F] mt-0.5">
                Assign primary vs fallback model providers directly from the UI. API keys & available models originate in <code className="font-mono text-[11px] bg-[#EAE2D6] px-1 py-0.5 rounded">.env</code>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#E3E8D6] text-[#434F30] font-mono text-[11px]">
              <span className="w-2 h-2 rounded-full bg-[#55633C] animate-pulse" />
              Strategy: Primary ➔ Fallback Failover
            </span>
          </div>
        </div>

        {/* Global Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#F5EFE6]/60 p-4 rounded border border-[#D9CFBF]">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-[#2E3325] flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#55633C]" />
              Default Primary Provider (Main Reasoning Engine)
            </label>
            <select
              value={defaultPrimary}
              onChange={(e) => {
                const val = e.target.value;
                setDefaultPrimary(val);
                handleRoleChange(val, 'primary');
              }}
              className="bg-[#FBF8F3] border border-[#D9CFBF] text-[#2E3325] px-3 py-2 rounded text-[13px] font-medium focus:outline-none focus:border-[#55633C] cursor-pointer"
            >
              {(llmConfig?.providers || []).map((p: ProviderConfigItem) => (
                <option key={p.name} value={p.name} disabled={!p.is_active}>
                  {p.display_name} ({p.name}) {p.is_active ? '✓ Active' : '(Disabled — No API Key in .env)'}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-[#8A8E7C]">
              Executes all agent plan, code generation, and verify reasoning steps by default.
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-[#2E3325] flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#A6633C]" />
              Default Fallback Provider (Zero-Downtime Resilience)
            </label>
            <select
              value={defaultFallback}
              onChange={(e) => {
                const val = e.target.value;
                setDefaultFallback(val);
                handleRoleChange(val, 'fallback');
              }}
              className="bg-[#FBF8F3] border border-[#D9CFBF] text-[#2E3325] px-3 py-2 rounded text-[13px] font-medium focus:outline-none focus:border-[#55633C] cursor-pointer"
            >
              {(llmConfig?.providers || []).map((p: ProviderConfigItem) => (
                <option key={p.name} value={p.name} disabled={!p.is_active}>
                  {p.display_name} ({p.name}) {p.is_active ? '✓ Active' : '(Disabled — No API Key in .env)'}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-[#8A8E7C]">
              Instantly receives failover traffic when primary trips circuit breaker or rate limits.
            </span>
          </div>
        </div>

        {/* Per-Provider Role & Model Table */}
        <div className="flex flex-col gap-3">
          <div className="text-[12px] font-semibold text-[#2E3325]">
            Provider Mesh Nodes & Role Configuration
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px] border-collapse">
              <thead>
                <tr className="border-b border-[#D9CFBF] text-[11px] text-[#5F664F] label-caps">
                  <th className="py-2 px-3">Provider Node</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Role Assignment</th>
                  <th className="py-2 px-3">Active Model</th>
                  <th className="py-2 px-3">Declared Capabilities</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#D9CFBF]/50">
                {(llmConfig?.providers || []).map((p: ProviderConfigItem) => {
                  const currentRole = providerRoles[p.name] || p.role;
                  const currentModel = providerModels[p.name] || p.selected_model || p.models[0] || '';
                  return (
                    <tr key={p.name} className="hover:bg-[#F5EFE6]/40 transition-colors">
                      <td className="py-3 px-3">
                        <div className="font-medium text-[#2E3325]">{p.display_name}</div>
                        <div className="font-mono text-[11px] text-[#8A8E7C]">{p.name}</div>
                      </td>
                      <td className="py-3 px-3">
                        {p.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#E3E8D6] text-[#434F30] font-mono text-[11px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#55633C]" />
                            Ready
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#EAE2D6] text-[#8A8E7C] font-mono text-[11px]">
                            <KeyRound className="w-3 h-3 text-[#8A8E7C]" />
                            No Key
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <div className="inline-flex rounded-md border border-[#D9CFBF] p-0.5 bg-[#FBF8F3]">
                          {(['primary', 'fallback', 'specialist'] as const).map((r) => (
                            <button
                              key={r}
                              type="button"
                              disabled={!p.is_active}
                              title={!p.is_active ? `Configure API key in backend/.env to activate ${p.display_name}` : undefined}
                              onClick={() => handleRoleChange(p.name, r)}
                              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all capitalize ${
                                !p.is_active
                                  ? 'opacity-35 cursor-not-allowed text-[#8A8E7C]'
                                  : currentRole === r
                                  ? r === 'primary'
                                    ? 'bg-[#55633C] text-[#F7F2EB] shadow-xs cursor-pointer'
                                    : r === 'fallback'
                                    ? 'bg-[#A6633C] text-[#F7F2EB] shadow-xs cursor-pointer'
                                    : 'bg-[#5F664F] text-[#F7F2EB] shadow-xs cursor-pointer'
                                  : 'text-[#5F664F] hover:text-[#2E3325] cursor-pointer'
                              }`}
                            >
                              {r}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        {p.models.length > 1 ? (
                          <select
                            value={currentModel}
                            disabled={!p.is_active}
                            onChange={(e) => handleModelChange(p.name, e.target.value)}
                            className={`bg-[#FBF8F3] border border-[#D9CFBF] text-[#2E3325] px-2 py-1 rounded text-[12px] font-mono focus:outline-none focus:border-[#55633C] ${
                              !p.is_active ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
                            }`}
                          >
                            {p.models.map((m: string) => (
                              <option key={m} value={m}>
                                {m}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className={`font-mono text-[12px] ${!p.is_active ? 'text-[#8A8E7C]' : 'text-[#2E3325]'}`}>
                            {currentModel || 'default'}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex flex-wrap gap-1">
                          {['reasoning', 'code_generation', 'classification', 'formatting'].map((tt: string) => {
                            const currentTasks = providerTasks[p.name] ?? p.task_types ?? [];
                            const isAssigned = currentTasks.includes(tt);
                            return (
                              <button
                                key={tt}
                                type="button"
                                disabled={!p.is_active}
                                onClick={() => handleToggleTask(p.name, tt)}
                                title={
                                  !p.is_active
                                    ? `API key required in .env to activate ${p.display_name}`
                                    : isAssigned
                                    ? `Assigned: click to unassign ${tt}`
                                    : `Click to assign ${tt} to ${p.display_name}`
                                }
                                className={`px-2 py-0.5 rounded font-mono text-[10px] transition-all ${
                                  !p.is_active
                                    ? 'opacity-30 cursor-not-allowed bg-[#EAE2D6] text-[#8A8E7C]'
                                    : isAssigned
                                    ? 'bg-[#55633C] text-[#F7F2EB] shadow-xs cursor-pointer'
                                    : 'border border-dashed border-[#D9CFBF] text-[#8A8E7C] hover:border-[#55633C] hover:text-[#2E3325] cursor-pointer'
                                }`}
                              >
                                {isAssigned ? `✓ ${tt}` : `+ ${tt}`}
                              </button>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Save Dynamic Roles Button */}
        <div className="flex items-center justify-between pt-3 border-t border-[#D9CFBF]">
          <span className="text-[12px] text-[#8A8E7C] italic">
            Changes are applied immediately to runtime LLM gateway and provider circuit breakers.
          </span>
          <button
            type="button"
            onClick={handleSaveRoles}
            disabled={isSavingRoles}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#55633C] text-[#F7F2EB] hover:bg-[#434F30] disabled:opacity-50 rounded text-[13px] font-medium shadow-xs transition-colors cursor-pointer"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{isSavingRoles ? 'Applying Routing Roles...' : 'Apply Dynamic Routing & Roles'}</span>
          </button>
        </div>
      </div>

      {/* Registered Inference Nodes Grid (Detailed) */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between pb-2 border-b border-[#D9CFBF]/70">
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-[24px] font-medium text-[#2E3325]">
              Registered Inference Nodes
            </h2>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#EAE2D6] text-[#5F664F]">
              4 Managed Slots
            </span>
          </div>
          <span className="text-[12px] text-[#8A8E7C] italic">
            Failover order: Primary ➔ LPU Classifier ➔ NIM Code ➔ Local Host
          </span>
        </div>

        {providers.length === 0 ? (
          <div className="card-archival p-12 text-center text-[#5F664F] font-mono text-[13px]">
            No Data is present
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {providers.map((p: ProviderHealth, idx: number) => (
              <ProviderCard
                key={p.id}
                provider={p}
                detailed={true}
                onTrip={handleTripProvider}
                onReset={handleResetProvider}
                delayMs={idx * 60}
              />
            ))}
          </div>
        )}
      </div>

      {/* Circuit Breaker Tuning Controls & Threshold Matrix */}
      <div className="card-archival p-6 flex flex-col gap-5">
        <div className="flex items-center gap-2 pb-2 border-b border-[#D9CFBF]">
          <SlidersHorizontal className="w-4 h-4 text-[#55633C]" />
          <h2 className="font-serif text-[22px] font-medium text-[#2E3325]">
            Circuit Breaker Dynamic Policy Tuning
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-[13px]">
          {/* Control 1 */}
          <div className="flex flex-col gap-2 p-4 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-[#2E3325]">Consecutive Faults Trip</label>
              <span className="font-mono font-bold text-[#55633C]">{consecutiveFailures} faults</span>
            </div>
            <p className="text-[12px] text-[#5F664F]">
              Consecutive timeout or 5xx responses before switching node from CLOSED to OPEN.
            </p>
            <input
              type="range"
              min="1"
              max="10"
              value={consecutiveFailures}
              onChange={(e) => setConsecutiveFailures(Number(e.target.value))}
              className="accent-[#55633C] cursor-pointer mt-1"
            />
          </div>

          {/* Control 2 */}
          <div className="flex flex-col gap-2 p-4 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-[#2E3325]">Half-Open Probe Interval</label>
              <span className="font-mono font-bold text-[#55633C]">{probeIntervalSeconds}s</span>
            </div>
            <p className="text-[12px] text-[#5F664F]">
              Quarantine resting duration before sending test inference probe to check recovery.
            </p>
            <input
              type="range"
              min="15"
              max="180"
              step="15"
              value={probeIntervalSeconds}
              onChange={(e) => setProbeIntervalSeconds(Number(e.target.value))}
              className="accent-[#55633C] cursor-pointer mt-1"
            />
          </div>

          {/* Control 3 */}
          <div className="flex flex-col gap-2 p-4 rounded bg-[#EAE2D6]/40 border border-[#D9CFBF]">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-[#2E3325]">Recovery Success Threshold</label>
              <span className="font-mono font-bold text-[#55633C]">{recoveryThreshold} probes</span>
            </div>
            <p className="text-[12px] text-[#5F664F]">
              Required consecutive successful responses in HALF-OPEN state to restore to CLOSED.
            </p>
            <input
              type="range"
              min="1"
              max="10"
              value={recoveryThreshold}
              onChange={(e) => setRecoveryThreshold(Number(e.target.value))}
              className="accent-[#55633C] cursor-pointer mt-1"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={handleSaveTuning}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#55633C] text-[#F7F2EB] hover:bg-[#434F30] rounded text-[13px] font-medium shadow-xs transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Commit Policy Thresholds to Mesh</span>
          </button>
        </div>
      </div>
    </div>
  );
};
