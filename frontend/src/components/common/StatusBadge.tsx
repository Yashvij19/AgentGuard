import React from 'react';
import clsx from 'clsx';
import { CircuitState, RunState } from '../../types';

interface StatusBadgeProps {
  status: RunState | CircuitState | 'PENDING' | 'ALLOWED' | 'DENIED' | 'NOMINAL';
  size?: 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  pulse = false,
  className,
}) => {
  const norm = status.toUpperCase();

  // Color mapping strictly per design-prompt.md and Stitch HTML
  let bgClass = 'bg-[#E3E8D6]';
  let textClass = 'text-[#2E3325]';
  let borderClass = 'border-[#BDCD9D]';
  let dotClass = 'bg-[#55633C]';
  let isBreathing = false;
  let isPulsing = false;

  if (norm === 'COMPLETED' || norm === 'CLOSED' || norm === 'ALLOWED' || norm === 'NOMINAL') {
    // Moss on light moss
    bgClass = 'bg-[#E3E8D6]';
    textClass = 'text-[#2E3325]';
    borderClass = 'border-[#BDCD9D]';
    dotClass = 'bg-[#55633C]';
  } else if (norm === 'PAUSED' || norm === 'HALF-OPEN' || norm === 'PENDING') {
    // Antique brass on parchment
    bgClass = 'bg-[#F0E6CF]';
    textClass = 'text-[#5A4308]';
    borderClass = 'border-[#E4C27C]';
    dotClass = 'bg-[#A88A4A]';
    if (norm === 'HALF-OPEN') {
      isBreathing = true; // 2.4s slow breath per animation-spec.md
    }
  } else if (norm === 'FAILED' || norm === 'OPEN' || norm === 'DENIED') {
    // Oxblood on soft blush
    bgClass = 'bg-[#EFDCD6]';
    textClass = 'text-[#8C4A3F]';
    borderClass = 'border-[#D9AFA6]';
    dotClass = 'bg-[#8C4A3F]';
  } else if (norm === 'RUNNING') {
    // Deep sage on sage light
    bgClass = 'bg-[#DDE3D0]';
    textClass = 'text-[#25310F]';
    borderClass = 'border-[#BDCD9D]';
    dotClass = 'bg-[#55633C]';
    isPulsing = true;
  } else if (norm === 'STALE') {
    bgClass = 'bg-[#EEEEEE]';
    textClass = 'text-[#8A8E7C]';
    borderClass = 'border-[#D9CFBF]';
    dotClass = 'bg-[#8A8E7C]';
  }

  const displayText = norm === 'HALF-OPEN' ? 'HALF-OPEN · PROBING' : norm === 'CLOSED' ? 'CLOSED · HEALTHY' : norm === 'OPEN' ? 'OPEN · RESTING' : norm;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-sans font-semibold uppercase tracking-wider rounded select-none border transition-colors duration-200',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px] leading-tight' : 'px-2 py-0.5 text-[11px] leading-4',
        bgClass,
        textClass,
        borderClass,
        className
      )}
    >
      <span
        className={clsx(
          'w-1.5 h-1.5 rounded-full shrink-0',
          dotClass,
          (pulse || isPulsing) && 'animate-subtle-pulse',
          isBreathing && 'animate-slow-breath'
        )}
      />
      <span>{displayText}</span>
    </span>
  );
};
