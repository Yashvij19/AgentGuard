import React, { useState } from 'react';
import { DecisionTraceStep } from '../../types';
import { StatusBadge } from './StatusBadge';
import {
  Check,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  FileCode,
  Shield,
  Info,
  Terminal,
  Copy,
  CheckCheck,
  ExternalLink,
} from 'lucide-react';
import clsx from 'clsx';

interface DecisionTimelineProps {
  steps: DecisionTraceStep[];
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({ steps }) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({
    4: true, // Step 4 expansion by default
  });
  const [copiedStep, setCopiedStep] = useState<number | null>(null);

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepNumber]: !prev[stepNumber],
    }));
  };

  const copyPayload = (stepNumber: number, payload: any) => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedStep(stepNumber);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  if (!steps || steps.length === 0) {
    return (
      <div className="card-archival p-12 text-center text-[#5F664F] font-mono text-[13px]">
        No Data is present
      </div>
    );
  }

  return (
    <div className="relative pl-8 sm:pl-10 space-y-6 before:content-[''] before:absolute before:left-3.5 sm:before:left-4 before:top-4 before:bottom-4 before:w-[2px] before:bg-[#D9CFBF]">
      {steps.map((step) => {
        const isExpanded = !!expandedSteps[step.step_number];

        let iconNode = <Check className="w-3.5 h-3.5 text-[#55633C] stroke-[2.5]" />;
        let nodeBg = 'bg-[#E3E8D6] border-[#BDCD9D]';

        if (step.status === 'PAUSED') {
          iconNode = <AlertCircle className="w-3.5 h-3.5 text-[#A88A4A] stroke-[2.5]" />;
          nodeBg = 'bg-[#F0E6CF] border-[#E4C27C]';
        } else if (step.status === 'FAILED') {
          iconNode = <AlertCircle className="w-3.5 h-3.5 text-[#8C4A3F] stroke-[2.5]" />;
          nodeBg = 'bg-[#EFDCD6] border-[#D9AFA6]';
        } else if (step.status === 'PENDING') {
          iconNode = <Clock className="w-3.5 h-3.5 text-[#8A8E7C] stroke-[2]" />;
          nodeBg = 'bg-[#EEEEEE] border-[#D9CFBF]';
        }

        const details = step.details || {};
        const isForbiddenError = details.error && details.error.includes('403');

        return (
          <div key={step.step_number} className="relative group">
            {/* Absolute Node Indicator on connecting vertical line */}
            <div
              className={clsx(
                'absolute -left-8 sm:-left-10 top-2 w-7 h-7 rounded-full border flex items-center justify-center shadow-xs transition-transform duration-200 group-hover:scale-105',
                nodeBg
              )}
            >
              {iconNode}
            </div>

            {/* Step Card */}
            <div className="card-archival p-4">
              <div
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer select-none"
                onClick={() => toggleStep(step.step_number)}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-[11px] font-semibold text-[#55633C]">
                    STEP {String(step.step_number).padStart(3, '0')}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-[#EAE2D6] font-mono text-[10px] text-[#2E3325] uppercase font-bold">
                    {step.phase}
                  </span>
                  <h3 className="font-serif text-[18px] text-[#2E3325] font-medium leading-snug">
                    {step.title}
                  </h3>

                  {/* Info (i) Icon with rich Hover Tooltip */}
                  <div className="relative group/info inline-block" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      aria-label="Step Architecture and Governance Info"
                      className="p-1 rounded-full text-[#8A8E7C] hover:text-[#55633C] hover:bg-[#EAE2D6] transition-colors cursor-pointer"
                    >
                      <Info className="w-3.5 h-3.5" />
                    </button>

                    {/* Popover Card */}
                    <div className="absolute left-1/2 -translate-x-1/2 sm:left-0 sm:translate-x-0 bottom-full mb-2 hidden group-hover/info:block z-50 w-72 sm:w-84 p-3 bg-[#2E3325] text-[#FBF8F3] rounded-lg shadow-xl text-left font-sans text-xs pointer-events-none transition-all animate-fade-in border border-[#55633C]/50">
                      <div className="flex items-center justify-between border-b border-[#5F664F] pb-1.5 mb-2 font-mono text-[10px] text-[#A88A4A]">
                        <span className="font-bold uppercase tracking-wider">Subsystem Architecture</span>
                        <span className="text-[#BDCD9D] font-mono truncate max-w-[140px]">
                          {step.explanation?.subsystem || 'AgentGuard Core'}
                        </span>
                      </div>
                      <p className="text-[12px] text-[#FBF8F3] font-medium leading-relaxed mb-2.5">
                        {step.explanation?.task || step.summary}
                      </p>
                      <div className="text-[11px] text-[#D9CFBF]/90 bg-[#3C4231] p-2 rounded border border-[#55633C]/40">
                        <span className="font-bold text-[#BDCD9D]">Governance Role: </span>
                        {step.explanation?.governance_role || 'Enforces repository dual-custody policies and cryptographic integrity.'}
                      </div>
                      <div className="w-2.5 h-2.5 bg-[#2E3325] border-r border-b border-[#55633C]/50 rotate-45 absolute left-4 -bottom-1.5"></div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {step.risk_score > 0 && (
                    <div className="flex items-center gap-1 font-mono text-[11px] text-[#5F664F]">
                      <span>Risk:</span>
                      <span className={clsx('font-semibold', step.risk_score > 60 ? 'text-[#8C4A3F]' : step.risk_score > 30 ? 'text-[#A88A4A]' : 'text-[#55633C]')}>
                        {step.risk_score}/100
                      </span>
                    </div>
                  )}
                  {step.duration_ms > 0 && (
                    <span className="font-mono text-[11px] text-[#8A8E7C]">
                      {step.duration_ms}ms
                    </span>
                  )}
                  <StatusBadge status={step.status} size="sm" />
                  <button className="text-[#8A8E7C] hover:text-[#2E3325] transition-colors p-0.5">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Step Summary */}
              <p className="text-[14px] text-[#5F664F] mt-2 leading-relaxed">
                {step.summary}
              </p>

              {/* Expandable Technical Details */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-[#D9CFBF]/60 bg-[#EAE2D6]/40 p-3.5 rounded flex flex-col gap-3 font-mono text-[11px]">
                  
                  {/* High Visibility Error Box */}
                  {details.error && (
                    <div className="p-3 bg-[#EFDCD6] border border-[#D9AFA6] rounded text-[#8C4A3F] font-sans">
                      <div className="flex items-center gap-2 font-bold font-mono text-[12px] mb-1">
                        <AlertCircle className="w-4 h-4 text-[#8C4A3F] shrink-0" />
                        <span>Execution Error in Subsystem</span>
                      </div>
                      <div className="font-mono text-[11px] whitespace-pre-wrap break-all bg-[#FBF8F3] p-2.5 rounded border border-[#D9AFA6]/70 mt-1.5 text-[#2E3325]">
                        {details.error}
                      </div>

                      {/* Explicit Guidance for 403 Forbidden */}
                      {isForbiddenError && (
                        <div className="mt-2.5 text-[12px] text-[#2E3325] bg-[#F0E6CF] p-3 rounded border border-[#E4C27C]">
                          <strong className="text-[#5A4308] block mb-1">GitHub Permission Update Required:</strong>
                          <span>You have changed the permissions in Developer Settings, but GitHub strictly requires you to <strong>accept the new permissions on your installation</strong> before GitHub issues an updated token:</span>
                          <ol className="list-decimal list-inside mt-2 space-y-1 text-[#5F664F]">
                            <li>
                              Open your GitHub App Installation:{' '}
                              <a
                                href="https://github.com/settings/installations/166849367"
                                target="_blank"
                                rel="noreferrer"
                                className="font-mono text-[#55633C] underline font-semibold hover:text-[#2E3325]"
                              >
                                https://github.com/settings/installations/166849367
                              </a>
                            </li>
                            <li>
                              Look for the banner: <strong>&ldquo;Review permissions request&rdquo;</strong> and click <strong>&ldquo;Accept updated permissions&rdquo;</strong>.
                            </li>
                            <li>
                              <em>(Alternative if no banner appears):</em> Scroll to the bottom, click <strong>Uninstall</strong>, then reinstall in 1 click at{' '}
                              <a
                                href="https://github.com/apps/agentguard-local-tester/installations/new"
                                target="_blank"
                                rel="noreferrer"
                                className="font-mono text-[#55633C] underline font-semibold hover:text-[#2E3325]"
                              >
                                github.com/apps/agentguard-local-tester/installations/new
                              </a>.
                            </li>
                          </ol>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Policy Rule Enforced */}
                  {step.policy_rule && (
                    <div className="flex items-start gap-1.5 text-[#5A4308]">
                      <Shield className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#A88A4A]" />
                      <div>
                        <span className="font-bold">Invariant Enforced: </span>
                        <code className="bg-[#FBF8F3] px-1.5 py-0.5 rounded border border-[#D9CFBF]">
                          {step.policy_rule}
                        </code>
                      </div>
                    </div>
                  )}

                  {/* Metadata Chips: Action, Capability, Target */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {details.action && (
                      <span className="bg-[#FBF8F3] px-2 py-0.5 rounded border border-[#D9CFBF] text-[#2E3325]">
                        Action: <strong>{details.action}</strong>
                      </span>
                    )}
                    {details.capability && (
                      <span className="bg-[#E3E8D6] px-2 py-0.5 rounded border border-[#BDCD9D] text-[#55633C]">
                        Capability: <strong>{details.capability}</strong>
                      </span>
                    )}
                    {details.target_path && (
                      <div className="flex items-center gap-1 bg-[#FBF8F3] px-2 py-0.5 rounded border border-[#D9CFBF] text-[#2E3325]">
                        <FileCode className="w-3 h-3 text-[#5F664F]" />
                        <span>Target: <strong>{details.target_path}</strong></span>
                      </div>
                    )}
                    {details.ast_nodes_scanned && (
                      <span className="text-[#5F664F]">
                        AST Nodes: <strong className="text-[#2E3325]">{details.ast_nodes_scanned}</strong>
                      </span>
                    )}
                  </div>

                  {/* Scoped Files */}
                  {details.files_checked && details.files_checked.length > 0 && (
                    <div className="text-[#5F664F]">
                      <span>Scope Files: </span>
                      <span className="text-[#2E3325]">{details.files_checked.join(', ')}</span>
                    </div>
                  )}

                  {/* Diff Viewer */}
                  {(details.proposed_diff || details.diff_unified) && (
                    <div className="flex flex-col gap-1 mt-1">
                      <span className="text-[#5F664F] font-semibold text-[11px]">Proposed Unified Diff:</span>
                      <pre className="p-2.5 bg-[#2E3325] text-[#FBF8F3] rounded font-mono text-[11px] overflow-x-auto max-h-48 whitespace-pre border border-[#55633C]/40">
                        {details.proposed_diff || details.diff_unified}
                      </pre>
                    </div>
                  )}

                  {/* Reason Text */}
                  {details.reason && (
                    <div className="text-[#8C4A3F] font-sans text-[12px] bg-[#FBF8F3] p-2 rounded border border-[#D9CFBF]">
                      {details.reason}
                    </div>
                  )}

                  {/* Complete Developer Event Payload (Never Hide Anything) */}
                  <div className="mt-1 pt-2 border-t border-[#D9CFBF]/40">
                    <details className="group/payload">
                      <summary className="cursor-pointer text-[10px] text-[#8A8E7C] hover:text-[#2E3325] font-sans font-semibold flex items-center justify-between select-none">
                        <span className="flex items-center gap-1.5">
                          <Terminal className="w-3 h-3" />
                          Audit Event Raw Payload (JSON)
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            copyPayload(step.step_number, details.raw_payload || details);
                          }}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#FBF8F3] border border-[#D9CFBF] text-[10px] text-[#55633C] hover:bg-[#EAE2D6] transition-colors"
                        >
                          {copiedStep === step.step_number ? (
                            <>
                              <CheckCheck className="w-3 h-3 text-[#55633C]" />
                              <span>Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3 text-[#8A8E7C]" />
                              <span>Copy JSON</span>
                            </>
                          )}
                        </button>
                      </summary>
                      <pre className="mt-2 p-2.5 bg-[#2E3325] text-[#FBF8F3] rounded font-mono text-[10px] overflow-x-auto max-h-48 whitespace-pre border border-[#55633C]/40 leading-relaxed">
                        {JSON.stringify(details.raw_payload || details, null, 2)}
                      </pre>
                    </details>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
