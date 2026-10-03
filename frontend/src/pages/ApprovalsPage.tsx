import React, { useState, useEffect } from 'react';
import {
  Gavel,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Lock,
  AlertTriangle,
  Coins,
  Bot,
  GitBranch,
} from 'lucide-react';
import { DiffViewer } from '../components/common/DiffViewer';
import { Modal } from '../components/common/Modal';
import { api } from '../services/api';
import { ApprovalRequest } from '../types';
import clsx from 'clsx';

export const ApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [isApproveOpen, setIsApproveOpen] = useState(false);
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [custodianComment, setCustodianComment] = useState('');
  const [rejectReason, setRejectReason] = useState('Protected scope write violated');
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [statusNotification, setStatusNotification] = useState<string | null>(null);

  useEffect(() => {
    const loadApprovals = async () => {
      const data = await api.getApprovals();
      setApprovals(data);
    };
    loadApprovals();
  }, []);

  const handleOpenApprove = (req: ApprovalRequest) => {
    setSelectedApproval(req);
    setIsApproveOpen(true);
  };

  const handleOpenReject = (req: ApprovalRequest) => {
    setSelectedApproval(req);
    setIsRejectOpen(true);
  };

  const handleConfirmApprove = async () => {
    if (!selectedApproval) return;
    const res = await api.approveRequest(selectedApproval.id, custodianComment);
    setIsApproveOpen(false);
    setCustodianComment('');
    setApprovals((prev) => prev.filter((a) => a.id !== selectedApproval.id));
    setStatusNotification(res.message);
    setTimeout(() => setStatusNotification(null), 4000);
  };

  const handleConfirmReject = async () => {
    if (!selectedApproval) return;
    const res = await api.rejectRequest(selectedApproval.id, `${rejectReason}: ${rejectFeedback}`);
    setIsRejectOpen(false);
    setRejectFeedback('');
    setApprovals((prev) => prev.filter((a) => a.id !== selectedApproval.id));
    setStatusNotification(res.message);
    setTimeout(() => setStatusNotification(null), 4000);
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-[#D9CFBF] pb-5">
        <div className="flex items-center gap-2 text-[11px] text-[#5F664F]">
          <span className="label-caps">Archival Folio 03 // Human Custody Interventions</span>
          <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
          <span className="font-mono text-[#8A8E7C]">Dual-Custody Quarantine</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-1">
          <div>
            <h1 className="font-serif text-[40px] text-[#2E3325] leading-none font-medium tracking-tight">
              Dual-Custody Approvals Queue
            </h1>
            <p className="text-[15px] text-[#5F664F] mt-2 max-w-2xl leading-relaxed">
              Live triage of sensitive autonomous actions quarantined by OPA Rego policy invariants.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded bg-[#F0E6CF] text-[#5A4308] border border-[#E4C27C] font-mono text-[11px] font-bold">
              {approvals.length} Pending Actions
            </span>
            <span className="font-mono text-[11px] text-[#8A8E7C]">
              Live polling: 30s cadence
            </span>
          </div>
        </div>
      </div>

      {/* Notification Toast if action executed */}
      {statusNotification && (
        <div className="p-3 bg-[#E3E8D6] text-[#2E3325] border border-[#BDCD9D] rounded text-[13px] font-medium flex items-center justify-between animate-rise-in">
          <span>{statusNotification}</span>
          <button
            onClick={() => setStatusNotification(null)}
            className="text-[#55633C] hover:text-[#2E3325]"
          >
            ✕
          </button>
        </div>
      )}

      {/* Empty State */}
      {approvals.length === 0 ? (
        <div className="card-archival p-12 text-center flex flex-col items-center justify-center">
          <CheckCircle className="w-10 h-10 text-[#55633C] mb-3" />
          <h3 className="font-serif text-[22px] font-medium text-[#2E3325]">
            No Data is present
          </h3>
          <p className="text-[14px] text-[#5F664F] mt-1 max-w-md">
            All quarantined actions have been reviewed or no pending dual-custody approval requests exist.
          </p>
        </div>
      ) : (
        approvals.map((req) => (
          <article
            key={req.id}
            className="card-archival p-6 flex flex-col gap-6 animate-rise-in"
          >
            {/* Top Identity Block */}
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 pb-4 border-b border-[#D9CFBF]/70">
              <div className="flex flex-col gap-1.5">
                <div className="flex flex-wrap items-center gap-2 text-[13px]">
                  <span className="font-mono text-[13px] font-semibold text-[#55633C]">
                    {req.display_id || req.id}
                  </span>
                  <span className="text-[#8A8E7C]">•</span>
                  <span className="text-[#5F664F]">Requested {req.requested_at} by</span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#EAE2D6] font-mono text-[11px] text-[#2E3325]">
                    <Bot className="w-3.5 h-3.5 text-[#55633C]" />
                    {req.agent_name}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1 text-[#2E3325]">
                  <span className="font-serif text-[20px] font-medium">
                    {req.target_file}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#EAE2D6] text-[#2E3325] border border-[#D9CFBF] label-caps text-[10px]">
                    {req.action_type} ({req.action_description})
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono text-[11px] text-[#8A8E7C] pt-0.5 flex-wrap">
                  {req.repository && (
                    <span className="flex items-center gap-1 text-[#5F664F]">
                      <GitBranch className="w-3.5 h-3.5" />
                      {req.repository}
                    </span>
                  )}
                  {req.pr_number ? (
                    <>
                      <span>•</span>
                      <span>PR #{req.pr_number}</span>
                    </>
                  ) : null}
                  {req.branch ? (
                    <>
                      <span>•</span>
                      <span className="text-[#55633C] font-semibold">branch: {req.branch}</span>
                    </>
                  ) : null}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-start shrink-0">
                <button
                  type="button"
                  onClick={() => handleOpenApprove(req)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded bg-[#55633C] text-[#F7F2EB] text-[13px] hover:bg-[#2E3325] transition-colors shadow-xs font-medium cursor-pointer"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Approve Action</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleOpenReject(req)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded bg-transparent text-[#8C4A3F] border border-[#D9AFA6] hover:bg-[#EFDCD6] text-[13px] transition-colors font-medium cursor-pointer"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Reject & Provide Feedback</span>
                </button>
              </div>
            </div>

            {/* Policy Invariant Trigger & Risk Assessment Box */}
            <div className="rounded bg-[#EAE2D6]/40 border border-[#D9CFBF] p-4 flex flex-col gap-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2 border-b border-[#D9CFBF]/60">
                <div className="flex items-center gap-2">
                  <Gavel className="w-4 h-4 text-[#A88A4A]" />
                  <span className="font-serif text-[18px] font-medium text-[#2E3325]">
                    Policy Invariant Trigger & Risk Assessment
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5 font-mono text-[11px]">
                    <span className="text-[#5F664F]">Evaluation Result:</span>
                    <span className={clsx('font-bold', req.evaluation_result === 'CRITICAL_STOP' ? 'text-[#8C4A3F]' : 'text-[#A88A4A]')}>
                      {req.evaluation_result}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] font-semibold text-[#2E3325]">
                      Risk Score: {req.risk_score} / 100
                    </span>
                    <div className="w-20 h-2 bg-[#EAE2D6] rounded-full overflow-hidden border border-[#D9CFBF]">
                      <div
                        className={clsx(
                          'h-full rounded-full',
                          req.risk_score > 70 ? 'bg-[#8C4A3F]' : 'bg-[#A88A4A]'
                        )}
                        style={{ width: `${req.risk_score}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Triggered Invariant Code String */}
              <div className="p-2.5 rounded bg-[#FBF8F3] border border-[#D9CFBF] font-mono text-[11px] text-[#2E3325] flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-[#A88A4A] mt-0.5 shrink-0" />
                <div className="leading-relaxed">
                  <span className="font-bold text-[#55633C]">Triggered Invariant: </span>
                  <code>{req.triggered_invariant}</code>{' '}
                  <span className="text-[#8A8E7C]">activated because</span>{' '}
                  <code className="bg-[#EAE2D6] px-1 py-0.5 rounded text-[#2E3325]">
                    {req.invariant_condition}
                  </code>
                </div>
              </div>

              {/* Contributing Risk Factors (3 Columns) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                <div className="p-3 rounded bg-[#FBF8F3] border border-[#D9CFBF]/70 flex flex-col justify-between">
                  <div className="flex items-center gap-1.5 text-[#2E3325] font-semibold text-[13px] pb-1">
                    <Lock className="w-3.5 h-3.5 text-[#8C4A3F]" />
                    <span>Protected Scope Violation</span>
                  </div>
                  <p className="text-[12px] text-[#5F664F] leading-relaxed">
                    Touches financial transaction path matching glob{' '}
                    <code className="font-mono text-[11px] bg-[#EAE2D6] px-1 rounded">
                      {req.target_file}
                    </code>
                  </p>
                </div>

                <div className="p-3 rounded bg-[#FBF8F3] border border-[#D9CFBF]/70 flex flex-col justify-between">
                  <div className="flex items-center gap-1.5 text-[#2E3325] font-semibold text-[13px] pb-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#A88A4A]" />
                    <span>High Blast Radius</span>
                  </div>
                  <p className="text-[12px] text-[#5F664F] leading-relaxed">
                    {req.blast_radius_desc}
                  </p>
                </div>

                <div className="p-3 rounded bg-[#FBF8F3] border border-[#D9CFBF]/70 flex flex-col justify-between">
                  <div className="flex items-center gap-1.5 text-[#2E3325] font-semibold text-[13px] pb-1">
                    <Coins className="w-3.5 h-3.5 text-[#55633C]" />
                    <span>Cost & Token Anomaly</span>
                  </div>
                  <p className="text-[12px] text-[#5F664F] leading-relaxed">
                    {req.token_anomaly_desc}
                  </p>
                </div>
              </div>
            </div>

            {/* Interactive Diff Viewer */}
            <DiffViewer
              filename={req.target_file}
              additions={req.diff_additions}
              deletions={req.diff_deletions}
              lines={req.diff_lines}
            />
          </article>
        ))
      )}

      {/* APPROVE MODAL */}
      <Modal
        isOpen={isApproveOpen}
        onClose={() => setIsApproveOpen(false)}
        title="Authorize Autonomous Action"
        subtitle={`Request ${selectedApproval?.id} • Target: ${selectedApproval?.target_file}`}
      >
        <div className="flex flex-col gap-4 text-[13px]">
          <div className="p-3 rounded bg-[#E3E8D6]/60 border border-[#BDCD9D] text-[#2E3325]">
            <p>
              By signing off, you affirm that you have reviewed the proposed patch diff and authorize the agent to execute this file system write operation under institutional custodial policy.
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="font-semibold text-[#2E3325]">
              Custodian Signature & Audit Comment (Optional)
            </label>
            <textarea
              rows={3}
              value={custodianComment}
              onChange={(e) => setCustodianComment(e.target.value)}
              placeholder="e.g., Reviewed idempotency keys and retry bounds. Approved for release."
              className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded p-2.5 text-[13px] focus:outline-none focus:border-[#55633C]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#D9CFBF]">
            <button
              type="button"
              onClick={() => setIsApproveOpen(false)}
              className="px-4 py-2 rounded text-[#5F664F] hover:text-[#2E3325]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmApprove}
              className="px-5 py-2 rounded bg-[#55633C] hover:bg-[#2E3325] text-[#F7F2EB] font-medium transition-colors shadow-xs"
            >
              Sign & Execute Patch
            </button>
          </div>
        </div>
      </Modal>

      {/* REJECT MODAL */}
      <Modal
        isOpen={isRejectOpen}
        onClose={() => setIsRejectOpen(false)}
        title="Reject Autonomous Action"
        subtitle={`Provide corrective feedback to ${selectedApproval?.agent_name}`}
      >
        <div className="flex flex-col gap-4 text-[13px]">
          <div className="p-3 rounded bg-[#EFDCD6]/60 border border-[#D9AFA6] text-[#8C4A3F]">
            <p>
              The proposed patch will be aborted and purged from the staging branch. Corrective guidance will be piped back to the agent session trace to reformulate.
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="font-semibold text-[#2E3325]">Reason for Rejection</label>
            <select
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="bg-[#F7F2EB] border border-[#D9CFBF] rounded p-2 text-[13px] focus:outline-none focus:border-[#55633C]"
            >
              <option>Protected scope write violated</option>
              <option>High blast radius logic requires manual refactor</option>
              <option>Flawed idempotency or retry backoff schedule</option>
              <option>Security policy violation detected</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="font-semibold text-[#2E3325]">
              Instructional Feedback for Agent
            </label>
            <textarea
              rows={3}
              value={rejectFeedback}
              onChange={(e) => setRejectFeedback(e.target.value)}
              placeholder="e.g., Do not alter charge retry handles directly. Move reconciliation logic to the event worker queue."
              className="w-full bg-[#F7F2EB] border border-[#D9CFBF] rounded p-2.5 text-[13px] focus:outline-none focus:border-[#55633C]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#D9CFBF]">
            <button
              type="button"
              onClick={() => setIsRejectOpen(false)}
              className="px-4 py-2 rounded text-[#5F664F] hover:text-[#2E3325]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmReject}
              className="px-5 py-2 rounded bg-[#8C4A3F] hover:bg-[#682F26] text-[#F7F2EB] font-medium transition-colors shadow-xs"
            >
              Reject & Dispatch Feedback
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
