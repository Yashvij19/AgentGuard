import React, { useEffect, useState } from 'react';
import clsx from 'clsx';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  icon: LucideIcon;
  trendText?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  accentColor?: 'sage' | 'brass' | 'neutral';
  progressBarPct?: number;
  subtitle?: string;
  delayMs?: number;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  icon: Icon,
  trendText,
  trendDirection = 'neutral',
  accentColor = 'neutral',
  progressBarPct,
  subtitle,
  delayMs = 0,
}) => {
  const [displayValue, setDisplayValue] = useState(0);

  // Count-up animation over 1000ms adhering to animation-spec.md
  useEffect(() => {
    let startTimestamp: number | null = null;
    const duration = 1000;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const elapsed = timestamp - startTimestamp;
      const progress = Math.min(elapsed / duration, 1);
      // cubic-bezier(0.22, 0.61, 0.36, 1) ease-out approximation: 1 - Math.pow(1 - progress, 3)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = easeOut * value;
      setDisplayValue(current);

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setDisplayValue(value);
      }
    };

    const timeout = setTimeout(() => {
      window.requestAnimationFrame(step);
    }, delayMs);

    return () => clearTimeout(timeout);
  }, [value, delayMs]);

  const formattedNum = decimals > 0 
    ? displayValue.toFixed(decimals) 
    : Math.round(displayValue).toLocaleString();

  let accentBarClass = 'bg-[#D9CFBF]';
  if (accentColor === 'sage') accentBarClass = 'bg-[#8B9A6E]';
  if (accentColor === 'brass') accentBarClass = 'bg-[#A88A4A]';

  return (
    <div
      className="card-archival p-5 flex flex-col justify-between relative overflow-hidden select-none animate-rise-in"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      {/* Top 2px stationary edge indicator */}
      <div className={clsx('absolute top-0 left-0 right-0 h-[2px]', accentBarClass)} />

      {/* Header with Small Caps & Icon */}
      <div className="flex items-center justify-between pb-1">
        <span className="label-caps text-[#5F664F]">{label}</span>
        <Icon className="w-4 h-4 text-[#8A8E7C] stroke-[1.5]" />
      </div>

      {/* Main Large Serif Numeral */}
      <div className="my-3">
        <div className="font-serif text-[38px] leading-tight font-medium text-[#2E3325] tracking-tight tabular-nums">
          {prefix}{formattedNum}{suffix}
        </div>
      </div>

      {/* Bottom Trend or Progress Bar */}
      {progressBarPct !== undefined ? (
        <div className="flex flex-col gap-1.5 mt-1">
          <div className="flex justify-between font-mono text-[11px] text-[#5F664F]">
            <span>Budget Burn</span>
            <span className="font-semibold text-[#2E3325]">{progressBarPct.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-[#EAE2D6] rounded-full h-1 overflow-hidden">
            <div
              className="bg-[#55633C] h-1 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${Math.min(progressBarPct, 100)}%` }}
            />
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-[13px] text-[#5F664F]">
          {trendDirection === 'up' && (
            <span className="font-serif text-[#55633C] font-semibold text-[16px] leading-none">↑</span>
          )}
          {trendDirection === 'down' && (
            <span className="font-serif text-[#8C4A3F] font-semibold text-[16px] leading-none">↓</span>
          )}
          {trendText && (
            <span className={clsx(trendDirection === 'up' ? 'text-[#55633C] font-semibold' : 'text-[#5F664F]')}>
              {trendText}
            </span>
          )}
          {subtitle && <span className="text-[#8A8E7C]">{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
