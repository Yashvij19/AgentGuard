import React from 'react';
import { ProviderHealth } from '../../types';
import { StatusBadge } from './StatusBadge';
import clsx from 'clsx';

interface ProviderCardProps {
  provider: ProviderHealth;
  detailed?: boolean;
  onTrip?: (id: string) => void;
  onReset?: (id: string) => void;
  delayMs?: number;
}

export const ProviderCard: React.FC<ProviderCardProps> = ({
  provider,
  detailed = false,
  onTrip,
  onReset,
  delayMs = 0,
}) => {
  return (
    <article
      className="card-archival p-4 flex flex-col justify-between relative group animate-rise-in"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      <div className="flex flex-col gap-2">
        {/* Slot & Status Pill */}
        <div className="flex items-center justify-between pb-1 border-b border-[#D9CFBF]/60">
          <StatusBadge status={provider.circuit_state} size="sm" />
          <span className="font-mono text-[11px] text-[#8A8E7C]">Slot #{provider.slot_number}</span>
        </div>

        {/* Title & Role */}
        <div className="mt-1">
          <h3 className="font-serif text-[19px] leading-snug font-medium text-[#2E3325]">
            {provider.provider_name}
          </h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="label-caps text-[#5F664F]">{provider.role}</span>
            <span className="text-[#8A8E7C] text-[10px]">•</span>
            <span className="font-mono text-[11px] text-[#8A8E7C]">{provider.model_id}</span>
          </div>
        </div>

        {/* Description & Tags (if detailed) */}
        {detailed && (
          <div className="mt-1">
            <p className="text-[13px] text-[#5F664F] leading-relaxed">
              {provider.description}
            </p>
            <div className="flex flex-wrap gap-1 mt-2">
              {provider.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 rounded bg-[#EAE2D6]/70 border border-[#D9CFBF]/60 font-mono text-[10px] text-[#2E3325]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Recessed Telemetry Well */}
      <div className="mt-3 bg-[#EAE2D6]/50 border border-[#D9CFBF]/80 rounded p-2.5 flex flex-col gap-1.5">
        <div className="flex justify-between items-center font-mono text-[11px]">
          <span className="text-[#5F664F]">Latency</span>
          <span className={clsx('font-medium', provider.latency_ms > 500 ? 'text-[#8C4A3F]' : provider.latency_ms > 350 ? 'text-[#A88A4A]' : 'text-[#2E3325]')}>
            {provider.latency_ms} ms
          </span>
        </div>
        <div className="flex justify-between items-center font-mono text-[11px]">
          <span className="text-[#5F664F]">Error Rate</span>
          <span className={clsx('font-medium', provider.error_rate_pct > 5 ? 'text-[#8C4A3F]' : provider.error_rate_pct > 1 ? 'text-[#A88A4A]' : 'text-[#55633C]')}>
            {provider.error_rate_pct.toFixed(2)}%
          </span>
        </div>
        <div className="flex justify-between items-center font-mono text-[11px]">
          <span className="text-[#5F664F]">Token Volume</span>
          <span className="font-medium text-[#2E3325]">{provider.token_volume.toLocaleString()}</span>
        </div>
      </div>

      {/* Action Buttons for Tuning/Trip if Detailed */}
      {detailed && (
        <div className="mt-3 pt-2 border-t border-[#D9CFBF]/60 flex items-center justify-end gap-2">
          {provider.circuit_state === 'OPEN' ? (
            <button
              onClick={() => onReset?.(provider.id)}
              className="px-2.5 py-1 rounded bg-[#E3E8D6] text-[#2E3325] border border-[#BDCD9D] hover:bg-[#DDE3D0] text-[11px] font-sans font-semibold tracking-wider uppercase transition-colors"
            >
              Reset Circuit
            </button>
          ) : (
            <button
              onClick={() => onTrip?.(provider.id)}
              className="px-2.5 py-1 rounded bg-transparent text-[#8C4A3F] border border-[#D9AFA6] hover:bg-[#EFDCD6] text-[11px] font-sans font-semibold tracking-wider uppercase transition-colors"
            >
              Trip Circuit
            </button>
          )}
        </div>
      )}
    </article>
  );
};
