import React, { useState } from 'react';
import {
  Terminal,
  BookOpen,
  Workflow,
  Copy,
  Check,
  ShieldCheck,
  Key,
  Layers,
  Cpu,
  Play,
  Lock,
  FileCode2,
  CheckCircle2,
  AlertTriangle,
  Server,
  ArrowRight,
  Database,
  History,
  Scale,
  Activity,
  Sliders,
  Zap,
  Code2,
  Eye,
  GitPullRequest,
  RefreshCw,
  GitCommit,
  Radio,
  FileText,
  Search,
} from 'lucide-react';
import clsx from 'clsx';

type DocMainTab = 'setup' | 'project' | 'developer';
type ProjectSubTab = 'overview' | 'runs' | 'trace' | 'approvals' | 'policies' | 'providers' | 'logs';
type DevSubTab = 'gitflow' | 'langgraph' | 'circuitbreaker' | 'llmrouter' | 'opaengine' | 'security';

export const DocumentationPage: React.FC = () => {
  const [activeMainTab, setActiveMainTab] = useState<DocMainTab>('setup');
  const [activeProjectSubTab, setActiveProjectSubTab] = useState<ProjectSubTab>('overview');
  const [activeDevSubTab, setActiveDevSubTab] = useState<DevSubTab>('gitflow');
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  const copyToClipboard = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(key);
    setTimeout(() => setCopiedSnippet(null), 2500);
  };

  return (
    <div className="flex flex-col gap-8 pb-20 animate-rise-in max-w-6xl mx-auto">
      {/* Header & Title */}
      <div className="flex flex-col gap-2 border-b border-[#D9CFBF] pb-5">
        <div className="flex items-center gap-2 text-[11px] text-[#5F664F]">
          <span className="label-caps">Archival Folio 07 // Engineering Specification</span>
          <span className="w-1 h-1 rounded-full bg-[#8A8E7C]" />
          <span className="font-mono text-[#8A8E7C]">AgentGuard Open-Source Architecture Manual</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-1">
          <div>
            <h1 className="font-serif text-[42px] text-[#2E3325] leading-none font-medium tracking-tight">
              AgentGuard Architecture & Operations Manual
            </h1>
            <p className="text-[15px] text-[#5F664F] mt-2 max-w-3xl leading-relaxed">
              Comprehensive open-source documentation covering local deployment, GitHub App dual-custody permissions, dashboard screen mechanics, and the underlying LangGraph distributed state engine.
            </p>
          </div>
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-[#D9CFBF] pb-px overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveMainTab('setup')}
          className={clsx(
            'flex items-center gap-2 px-5 py-3 font-sans text-[13px] font-medium transition-all duration-200 border-b-2 -mb-px cursor-pointer shrink-0',
            activeMainTab === 'setup'
              ? 'border-[#55633C] text-[#2E3325] font-semibold bg-[#EAE2D6]/40'
              : 'border-transparent text-[#5F664F] hover:text-[#2E3325] hover:bg-[#EAE2D6]/20'
          )}
        >
          <Terminal className="w-4 h-4 text-[#55633C]" />
          <span>1. Setup & Installation Guide</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveMainTab('project')}
          className={clsx(
            'flex items-center gap-2 px-5 py-3 font-sans text-[13px] font-medium transition-all duration-200 border-b-2 -mb-px cursor-pointer shrink-0',
            activeMainTab === 'project'
              ? 'border-[#55633C] text-[#2E3325] font-semibold bg-[#EAE2D6]/40'
              : 'border-transparent text-[#5F664F] hover:text-[#2E3325] hover:bg-[#EAE2D6]/20'
          )}
        >
          <BookOpen className="w-4 h-4 text-[#55633C]" />
          <span>2. Dashboard & Screen Details</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveMainTab('developer')}
          className={clsx(
            'flex items-center gap-2 px-5 py-3 font-sans text-[13px] font-medium transition-all duration-200 border-b-2 -mb-px cursor-pointer shrink-0',
            activeMainTab === 'developer'
              ? 'border-[#55633C] text-[#2E3325] font-semibold bg-[#EAE2D6]/40'
              : 'border-transparent text-[#5F664F] hover:text-[#2E3325] hover:bg-[#EAE2D6]/20'
          )}
        >
          <Workflow className="w-4 h-4 text-[#55633C]" />
          <span>3. Senior Developer & Engine Architecture</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 1: SETUP & OPERATIONS                                             */}
      {/* ========================================================================= */}
      {activeMainTab === 'setup' && (
        <div className="flex flex-col gap-8 animate-rise-in">
          {/* Prerequisites */}
          <div className="card-archival p-6">
            <div className="flex items-center gap-2.5 border-b border-[#D9CFBF] pb-3 mb-4">
              <Server className="w-4 h-4 text-[#55633C]" />
              <h2 className="font-serif text-[22px] text-[#2E3325] font-medium">
                Prerequisites & System Requirements
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans text-[13px]">
              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-bold text-[#2E3325] block mb-1">Python 3.11+</span>
                <span className="text-[#5F664F] leading-relaxed">
                  FastAPI asynchronous backend, LangGraph state engine, SQLAlchemy 2.0 ORM, and asyncpg PostgreSQL driver.
                </span>
              </div>
              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-bold text-[#2E3325] block mb-1">Node.js 18+ & npm</span>
                <span className="text-[#5F664F] leading-relaxed">
                  Vite React TypeScript dashboard, TailwindCSS styling engine, and Smee.io webhook delivery forwarder.
                </span>
              </div>
              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-bold text-[#2E3325] block mb-1">Docker & Compose</span>
                <span className="text-[#5F664F] leading-relaxed">
                  Orchestrates PostgreSQL 16 on port 5432 and the Open Policy Agent (OPA) sidecar daemon on port 8181.
                </span>
              </div>
            </div>
          </div>

          {/* Environment Variables Configuration */}
          <div className="card-archival p-6">
            <div className="flex items-center justify-between border-b border-[#D9CFBF] pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <Key className="w-4 h-4 text-[#55633C]" />
                <h2 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Environment Configuration (`backend/.env`)
                </h2>
              </div>
              <button
                type="button"
                onClick={() =>
                  copyToClipboard(
                    'env_template',
                    `APP_ENV=development\nLOG_LEVEL=INFO\nHOST=0.0.0.0\nPORT=8000\nDATABASE_URL=postgresql+asyncpg://postgres:Yash1234@localhost:5432/agentguard\nOPA_URL=http://localhost:8181\nGEMINI_API_KEY=your_gemini_api_key\nGEMINI_MODELS=gemini-2.5-flash\nGROQ_API_KEY=your_groq_api_key\nGROQ_MODELS=openai/gpt-oss-20b,qwen/qwen3.8-27b\nNVIDIA_NIM_API_KEY=your_nvidia_api_key\nNVIDIA_NIM_MODELS=deepseek-ai/deepseek-v4.1-flash,z-ai/glm-5.3-flash\nE2B_API_KEY=your_e2b_api_key\nGITHUB_APP_ID=5148576\nGITHUB_WEBHOOK_SECRET=your_webhook_hmac_secret\nGITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\\n..."`
                  )
                }
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono text-[#55633C] hover:bg-[#EAE2D6] rounded border border-[#D9CFBF] transition-colors cursor-pointer"
              >
                {copiedSnippet === 'env_template' ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#55633C]" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy .env Template</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-[13px] text-[#5F664F] mb-4">
              Save these settings into <code className="font-mono px-1 py-0.5 bg-[#EAE2D6] rounded text-[#2E3325]">backend/.env</code>:
            </p>
            <div className="bg-[#2E3325] text-[#FBF8F3] p-4 rounded-lg font-mono text-[12px] leading-relaxed overflow-x-auto border border-[#55633C]/40">
              <span className="text-[#A88A4A]"># 1. Database & Policy Sidecar</span>
              <br />
              DATABASE_URL=postgresql+asyncpg://postgres:Yash1234@localhost:5432/agentguard
              <br />
              OPA_URL=http://localhost:8181
              <br />
              <br />
              <span className="text-[#A88A4A]"># 2. Multi-Provider LLM Keys</span>
              <br />
              GEMINI_API_KEY=AIzaSy... (Primary Reasoning & Fix Synthesis)
              <br />
              GEMINI_MODELS=gemini-2.5-flash
              <br />
              GROQ_API_KEY=gsk_... (Fast Classification & Formatting)
              <br />
              NVIDIA_NIM_API_KEY=nvapi-... (DeepSeek & Nemotron Fallback)
              <br />
              <br />
              <span className="text-[#A88A4A]"># 3. Isolated MicroVM Sandbox Engine</span>
              <br />
              E2B_API_KEY=e2b_...
              <br />
              <br />
              <span className="text-[#A88A4A]"># 4. GitHub App Integration</span>
              <br />
              GITHUB_APP_ID=5148576
              <br />
              GITHUB_WEBHOOK_SECRET=your_hmac_secret
              <br />
              GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."
            </div>
          </div>

          {/* GitHub App Setup & Permissions */}
          <div className="card-archival p-6">
            <div className="flex items-center gap-2.5 border-b border-[#D9CFBF] pb-3 mb-4">
              <ShieldCheck className="w-4 h-4 text-[#55633C]" />
              <h2 className="font-serif text-[22px] text-[#2E3325] font-medium">
                GitHub App Setup & Permission Scopes
              </h2>
            </div>
            <div className="space-y-4 text-[13px] text-[#2E3325]">
              <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-semibold block text-[#2E3325] mb-1">
                  Step 1: Create GitHub App
                </span>
                <span className="text-[#5F664F]">
                  Open <strong>GitHub &rarr; Settings &rarr; Developer Settings &rarr; GitHub Apps &rarr; New GitHub App</strong>.
                </span>
              </div>

              <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-semibold block text-[#2E3325] mb-1">
                  Step 2: Webhook Endpoint via Smee.io
                </span>
                <span className="text-[#5F664F]">
                  Create a forwarding URL on <a href="https://smee.io" target="_blank" rel="noreferrer" className="underline text-[#55633C]">smee.io</a>. Set the GitHub App Webhook URL to your Smee link and define a secure webhook secret.
                </span>
              </div>

              <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-semibold block text-[#2E3325] mb-1">
                  Step 3: Mandated Permissions Table
                </span>
                <div className="mt-2 space-y-1.5 font-mono text-[11px]">
                  <div className="flex items-center justify-between p-2.5 bg-[#FBF8F3] rounded border border-[#D9CFBF]">
                    <span>Repository permissions &rarr; <strong>Contents</strong>:</span>
                    <span className="px-2 py-0.5 bg-[#E3E8D6] text-[#55633C] rounded font-bold">Read and write</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-[#FBF8F3] rounded border border-[#D9CFBF]">
                    <span>Repository permissions &rarr; <strong>Pull requests</strong>:</span>
                    <span className="px-2 py-0.5 bg-[#E3E8D6] text-[#55633C] rounded font-bold">Read and write</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 bg-[#FBF8F3] rounded border border-[#D9CFBF]">
                    <span>Repository permissions &rarr; <strong>Metadata</strong>:</span>
                    <span className="px-2 py-0.5 bg-[#EAE2D6] text-[#2E3325] rounded">Read-only</span>
                  </div>
                </div>
                <p className="text-[11px] text-[#8C4A3F] mt-2 font-sans">
                  * Mandatory: `Contents: Read and write` allows AgentGuard to push commits to the PR branch after dual-custody human sign-off.
                </p>
              </div>

              <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]/70">
                <span className="font-semibold block text-[#2E3325] mb-1">
                  Step 4: Subscribe to Events & Install
                </span>
                <span className="text-[#5F664F]">
                  Under "Subscribe to events", check <strong>Pull request</strong>. Generate a private key (.pem), download it, and install the App on your repository (e.g. <code className="font-mono text-[#2E3325]">Yashvij19/agentguard-tester</code>).
                </span>
              </div>
            </div>
          </div>

          {/* Running Locally: 4 Step Process */}
          <div className="card-archival p-6">
            <div className="flex items-center gap-2.5 border-b border-[#D9CFBF] pb-3 mb-4">
              <Play className="w-4 h-4 text-[#55633C]" />
              <h2 className="font-serif text-[22px] text-[#2E3325] font-medium">
                Local Execution Guide (4 Terminal Commands)
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-[12px] text-[#2E3325]">Terminal 1: Docker Containers</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard('term_docker', 'docker-compose up -d')}
                    className="p-1 hover:bg-[#EAE2D6] rounded text-[#55633C] cursor-pointer"
                  >
                    {copiedSnippet === 'term_docker' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[11px] text-[#5F664F] mb-2">Spawns PostgreSQL 16 and OPA policy sidecar:</p>
                <code className="block bg-[#2E3325] text-[#FBF8F3] p-2.5 rounded text-[11px] font-mono">
                  docker-compose up -d
                </code>
              </div>

              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-[12px] text-[#2E3325]">Terminal 2: FastAPI Backend</span>
                  <button
                    type="button"
                    onClick={() =>
                      copyToClipboard(
                        'term_backend',
                        'cd backend\nuvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
                      )
                    }
                    className="p-1 hover:bg-[#EAE2D6] rounded text-[#55633C] cursor-pointer"
                  >
                    {copiedSnippet === 'term_backend' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[11px] text-[#5F664F] mb-2">Runs REST API & LangGraph runner on port 8000:</p>
                <code className="block bg-[#2E3325] text-[#FBF8F3] p-2.5 rounded text-[11px] font-mono">
                  uvicorn app.main:app --reload --port 8000
                </code>
              </div>

              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-[12px] text-[#2E3325]">Terminal 3: Webhook Tunnel</span>
                  <button
                    type="button"
                    onClick={() =>
                      copyToClipboard(
                        'term_smee',
                        'npx smee-client -u https://smee.io/pelvhkj61rMRRrBz -t http://127.0.0.1:8000/api/webhooks/github'
                      )
                    }
                    className="p-1 hover:bg-[#EAE2D6] rounded text-[#55633C] cursor-pointer"
                  >
                    {copiedSnippet === 'term_smee' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[11px] text-[#5F664F] mb-2">Forwards live GitHub webhook deliveries locally:</p>
                <code className="block bg-[#2E3325] text-[#FBF8F3] p-2.5 rounded text-[11px] font-mono truncate">
                  npx smee-client -u https://smee.io/... -t http://127.0.0.1:8000/api/webhooks/github
                </code>
              </div>

              <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-[12px] text-[#2E3325]">Terminal 4: React Dashboard</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard('term_front', 'cd frontend\nnpm run dev')}
                    className="p-1 hover:bg-[#EAE2D6] rounded text-[#55633C] cursor-pointer"
                  >
                    {copiedSnippet === 'term_front' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[11px] text-[#5F664F] mb-2">Vite dev server with HMR on port 5173:</p>
                <code className="block bg-[#2E3325] text-[#FBF8F3] p-2.5 rounded text-[11px] font-mono">
                  npm run dev
                </code>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 2: PROJECT DETAILS & COMPONENT WALKTHROUGH                        */}
      {/* ========================================================================= */}
      {activeMainTab === 'project' && (
        <div className="flex flex-col gap-6 animate-rise-in">
          {/* Sub-tab Navigation */}
          <div className="flex items-center gap-1.5 p-1 bg-[#EAE2D6]/50 rounded-lg overflow-x-auto border border-[#D9CFBF]">
            {[
              { id: 'overview', label: 'Overview (`/`)', icon: Layers },
              { id: 'runs', label: 'Runs (`/runs`)', icon: History },
              { id: 'trace', label: 'Cognitive Trace (`/runs/:id`)', icon: Workflow },
              { id: 'approvals', label: 'Approvals (`/approvals`)', icon: ShieldCheck },
              { id: 'policies', label: 'Policy Studio (`/policies`)', icon: Scale },
              { id: 'providers', label: 'LLM Providers (`/providers`)', icon: Cpu },
              { id: 'logs', label: 'Developer Logs (`/logs`)', icon: Terminal },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveProjectSubTab(tab.id as ProjectSubTab)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium transition-colors cursor-pointer shrink-0',
                    activeProjectSubTab === tab.id
                      ? 'bg-[#FBF8F3] text-[#2E3325] shadow-xs font-semibold'
                      : 'text-[#5F664F] hover:text-[#2E3325]'
                  )}
                >
                  <Icon className="w-3.5 h-3.5 text-[#55633C]" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* 1. Overview Screen */}
          {activeProjectSubTab === 'overview' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Overview Screen Components (`/`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  High-level dashboard providing executive operational metrics and real-time mesh health.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">1. KPI Metrics Banner (4 Cards)</span>
                  <ul className="list-disc list-inside space-y-1 text-[#5F664F] text-[12px]">
                    <li><strong>Verified Compliance Rate (%)</strong>: Ratio of runs evaluated without policy violations.</li>
                    <li><strong>Autonomous Cycles</strong>: Total number of execution runs registered across all monitored repositories.</li>
                    <li><strong>Pending Sign-offs</strong>: Actions paused by the Dual-Custody Gate requiring human review.</li>
                    <li><strong>Compute Expenditure & Tokens</strong>: Real-time token volume and micro-cost consumption.</li>
                  </ul>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">2. Provider Health Matrix</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Live telemetry strip indicating circuit breaker status (<code className="font-mono text-[#6F7D55]">CLOSED</code>, <code className="font-mono text-[#A88A4A]">HALF-OPEN</code>, <code className="font-mono text-[#8C4A3F]">OPEN</code>), upstream latency in milliseconds, and active models.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">3. Execution Throughput Chart</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Visual area/bar chart displaying daily run volume categorized by state (Completed, Paused, Failed).
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">4. Recent Runs Table</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Latest executions with repository link, commit SHA badge, status pills, and direct "Inspect trace &rarr;" deep-links.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 2. Runs Screen */}
          {activeProjectSubTab === 'runs' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Runs Ledger Screen Components (`/runs`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  Complete historical registry of all governed automated executions.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Filter Ribbon</span>
                  <p className="text-[#5F664F] text-[12px] mb-2 leading-relaxed">
                    Search by PR number, commit SHA, or repository name. Filter by lifecycle states:
                  </p>
                  <div className="flex flex-wrap gap-2 text-[11px] font-mono">
                    <span className="px-2 py-0.5 rounded bg-[#E3E8D6] text-[#55633C]">ALL</span>
                    <span className="px-2 py-0.5 rounded bg-[#DDE3D0] text-[#5F6E4A]">RUNNING</span>
                    <span className="px-2 py-0.5 rounded bg-[#F0E6CF] text-[#A88A4A]">PAUSED</span>
                    <span className="px-2 py-0.5 rounded bg-[#E3E8D6] text-[#6F7D55]">COMPLETED</span>
                    <span className="px-2 py-0.5 rounded bg-[#EFDCD6] text-[#8C4A3F]">FAILED</span>
                    <span className="px-2 py-0.5 rounded bg-[#EEEEEE] text-[#8A8E7C]">STALE</span>
                  </div>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Tokens & Cost Accounting Column</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Displays exact token usage (prompt + candidate output tokens from LLM API) alongside 4-decimal precision monetary cost (e.g. <code className="font-mono text-[#2E3325]">1,030 tok ($0.0005)</code>).
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 3. Run Detail & Trace */}
          {activeProjectSubTab === 'trace' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Cognitive Trace & Incept View (`/runs/:id`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  The forensic audit trail breaking down every intent, policy check, sandbox test, and commit event.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Timeline Milestone Cards (12+ Steps)</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Each card displays step number, phase badge (<code className="font-mono text-[#55633C]">INGESTION</code>, <code className="font-mono text-[#55633C]">POLICY_CHECK</code>, <code className="font-mono text-[#55633C]">APPROVAL</code>, <code className="font-mono text-[#55633C]">EXECUTION</code>), duration, risk score, and an expandable JSON drawer showing raw audit payloads.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Subsystem Architecture Tooltips (i)</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Hovering over any step's info icon reveals the executing subsystem (e.g. <em>Run Coordinator</em>, <em>OPA Invariant Engine</em>, <em>E2B Cloud Sandbox</em>) and its explicit governance role.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Unified Git Diff Viewer</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Syntax-highlighted diff viewer displaying additions in moss green and deletions in soft oxblood red.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Sandboxed Pytest Output</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Raw stdout and stderr logs from isolated cloud microVM executions showing baseline failure vs. post-patch pass assertions.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 4. Approvals Screen */}
          {activeProjectSubTab === 'approvals' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Dual-Custody Approvals Screen (`/approvals`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  The human-in-the-loop authorization center for high-risk write operations.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Why Dual-Custody Exists</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Under AgentGuard policy, autonomous agents are strictly forbidden from writing code to GitHub directly without human sign-off. When an agent creates a fix, execution halts in <code className="font-mono text-[#A88A4A]">PAUSED</code> state until an authorized operator reviews the blast radius.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                    <span className="font-bold text-[#2E3325] block mb-1">Blast Radius Inspection</span>
                    <ul className="list-disc list-inside text-[#5F664F] text-[12px] space-y-1">
                      <li>Target repository and target file path</li>
                      <li>Calculated Risk Score (0 to 100)</li>
                      <li>Requested Capability token (<code className="font-mono text-[#2E3325]">github.create_commit</code>)</li>
                      <li>Unified Git patch preview</li>
                    </ul>
                  </div>

                  <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                    <span className="font-bold text-[#2E3325] block mb-1">Operator Actions</span>
                    <ul className="list-disc list-inside text-[#5F664F] text-[12px] space-y-1">
                      <li><strong>Authorize & Apply Patch</strong>: Signs the action cryptographically, dispatches ToolGateway to commit the code to GitHub, and resumes the workflow.</li>
                      <li><strong>Reject Action</strong>: Records rejection in audit ledger and aborts without touching code.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 5. Policy Studio Screen */}
          {activeProjectSubTab === 'policies' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Policy Studio & Rego Synthesis (`/policies`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  Codified governance editor bridging human-readable YAML specifications with compiled Open Policy Agent rules.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">1. Declarative YAML Editor</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed mb-2">
                    Edits <code className="font-mono text-[#2E3325]">.agentguard/policy.yaml</code> with live AST parsing:
                  </p>
                  <ul className="list-disc list-inside text-[#5F664F] text-[12px] space-y-1">
                    <li><code className="font-mono text-[#55633C]">capabilities</code>: allow, approval, deny lists</li>
                    <li><code className="font-mono text-[#55633C]">filesystem</code>: permitted read/write glob patterns</li>
                    <li><code className="font-mono text-[#55633C]">commands</code>: regex whitelist & blacklist</li>
                    <li><code className="font-mono text-[#55633C]">budget</code>: token and dollar limits per run</li>
                  </ul>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">2. Compiled Rego Tab</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Inspects how the RegoCompiler transforms your declarative YAML into OPA document objects and compiles them into active rules in <code className="font-mono text-[#2E3325]">agentguard.policy</code>.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">3. Invariant Tests Tab</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Executes automated unit tests against your security policy (e.g. testing whether <code className="font-mono text-[#8C4A3F]">rm -rf /</code> or <code className="font-mono text-[#8C4A3F]">os.system()</code> is successfully denied).
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">4. OPA Daemon Health</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Real-time status of the OPA REST engine on port 8181, showing in-memory bundle count and sub-millisecond evaluation latency.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 6. LLM Providers Screen */}
          {activeProjectSubTab === 'providers' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  LLM Providers & Multi-Provider Mesh (`/providers`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  Runtime model gateway with dynamic role assignment and circuit breaker resiliency.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">1. Dynamic Provider Roles</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed mb-2">
                    Assign providers dynamically from the UI without restarting the backend:
                  </p>
                  <ul className="list-disc list-inside text-[#5F664F] text-[12px] space-y-1">
                    <li><strong>Primary</strong>: First-priority model (Google Gemini 2.5 Flash).</li>
                    <li><strong>Fallback</strong>: Immediate failover candidate (Groq / NVIDIA NIM).</li>
                    <li><strong>Specialist</strong>: Assigned to specific task types (Reasoning, Code Generation, Formatting).</li>
                  </ul>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">2. Circuit Breaker Simulation</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Manually "Trip" a provider's circuit to simulate an upstream outage and watch AgentGuard automatically fail over to the secondary provider without dropping PR requests.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">3. Circuit Policy Tuning</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Adjust failure threshold percentage (e.g. trip after 10% errors), probe intervals (60s), and recovery thresholds (5 consecutive successes to close).
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">4. Live Dynamic Sidebar Badge</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    The sidebar footer dynamically reflects the active primary provider (e.g. <em>Gemini 2.5 Flash active</em>) and updates instantly when roles are saved.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 7. Developer Logs Screen */}
          {activeProjectSubTab === 'logs' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Developer Logs & Structured Telemetry (`/logs`)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  High-frequency event stream providing complete observability into background daemons and internal state transitions.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Structured JSON Log Stream</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Captures structured log records emitted by <code className="font-mono text-[#2E3325]">structlog</code> containing timestamp, log level (<code className="font-mono text-[#55633C]">INFO</code>, <code className="font-mono text-[#A88A4A]">WARN</code>, <code className="font-mono text-[#8C4A3F]">ERROR</code>), subsystem name, run ID, and detailed metadata.
                  </p>
                </div>
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Log Level Filtering & Live Polling</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Filter by component (<code className="font-mono text-[#55633C]">run_coordinator</code>, <code className="font-mono text-[#55633C]">policy_gateway</code>, <code className="font-mono text-[#55633C]">tool_gateway</code>, <code className="font-mono text-[#55633C]">llm_gateway</code>) to isolate issues in real time.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 3: SENIOR DEVELOPER & ENGINE ARCHITECTURE                         */}
      {/* ========================================================================= */}
      {activeMainTab === 'developer' && (
        <div className="flex flex-col gap-6 animate-rise-in">
          {/* Sub-tab Navigation */}
          <div className="flex items-center gap-1.5 p-1 bg-[#EAE2D6]/50 rounded-lg overflow-x-auto border border-[#D9CFBF]">
            {[
              { id: 'gitflow', label: '1. Git & Webhook Lifecycle', icon: GitCommit },
              { id: 'langgraph', label: '2. LangGraph State Machine', icon: Workflow },
              { id: 'circuitbreaker', label: '3. Circuit Breaker FSM', icon: Activity },
              { id: 'llmrouter', label: '4. Multi-Provider Router', icon: Cpu },
              { id: 'opaengine', label: '5. OPA Rego Compiler', icon: Scale },
              { id: 'security', label: '6. Security Invariants', icon: Lock },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveDevSubTab(tab.id as DevSubTab)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium transition-colors cursor-pointer shrink-0',
                    activeDevSubTab === tab.id
                      ? 'bg-[#FBF8F3] text-[#2E3325] shadow-xs font-semibold'
                      : 'text-[#5F664F] hover:text-[#2E3325]'
                  )}
                >
                  <Icon className="w-3.5 h-3.5 text-[#55633C]" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* 1. Git & Webhook Lifecycle */}
          {activeDevSubTab === 'gitflow' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Complete Git & Webhook Ingestion Pipeline
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  How a developer commit on GitHub travels through cryptographic validation down to physical git patch application.
                </p>
              </div>

              {/* ASCII / Visual Flow Diagram */}
              <div className="p-4 bg-[#2E3325] text-[#FBF8F3] rounded-lg font-mono text-[11px] leading-relaxed overflow-x-auto border border-[#55633C]/40">
                <span className="text-[#A88A4A]">GitHub Developer Push</span> &rarr; <span className="text-[#BDCD9D]">Webhook Delivery</span>
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Webhook Gateway]</strong>: Verify HMAC-SHA256(payload, secret) == X-Hub-Signature-256
                <br />
                &nbsp;&nbsp;&darr; (Pass: 200 OK | Fail: 401 Unauthorized)
                <br />
                <strong>[Deduplication]</strong>: INSERT github_delivery_id &rarr; PostgreSQL UNIQUE constraint
                <br />
                &nbsp;&nbsp;&darr; (Pass: Process | Duplicate: Acknowledge & Skip)
                <br />
                <strong>[Loop Prevention]</strong>: Check sender.login. If "[bot]" or "agentguard" &rarr; Abort immediately
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Run Coordinator]</strong>: Compute lock_id = hash64(repo#pr_number) &rarr; SELECT pg_try_advisory_xact_lock(:lock_id)
                <br />
                &nbsp;&nbsp;&darr; (Lock Held: ConcurrentRunError | Acquired: Continue)
                <br />
                <strong>[Staleness Check]</strong>: Compare head_sha with latest GitHub PR SHA &rarr; Mark STALE if superseded
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[LangGraph StateGraph]</strong>: Plan &rarr; Investigate &rarr; Reproduce &rarr; Patch
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Dual-Custody Gate]</strong>: OPA mandates REQUIRE_APPROVAL &rarr; Run PAUSED &rarr; Pending Approval ID
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Operator Sign-Off]</strong>: Human reviews diff on UI &rarr; Clicks Approve &rarr; POST /api/approvals/:id/approve
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Governed Tool Gateway]</strong>: Uses GitHub App RSA Private Key &rarr; Commits fix to PR branch
                <br />
                &nbsp;&nbsp;&darr;
                <br />
                <strong>[Verify & Report]</strong>: MicroVM re-runs pytest tests/ &rarr; Posts PR review comment &rarr; Seals Ledger!
              </div>

              <div className="space-y-3 text-[13px] text-[#2E3325]">
                <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold block mb-1">Cryptographic Webhook Verification</span>
                  <span className="text-[#5F664F] text-[12px]">
                    In <code className="font-mono text-[#2E3325]">webhook_service.py</code>, AgentGuard uses <code className="font-mono text-[#55633C]">hmac.compare_digest</code> for constant-time byte string comparison, completely eliminating timing attack vulnerabilities.
                  </span>
                </div>
                <div className="p-3 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold block mb-1">Loop Prevention Guard</span>
                  <span className="text-[#5F664F] text-[12px]">
                    When AgentGuard commits an approved patch, GitHub emits a <code className="font-mono text-[#2E3325]">pull_request.synchronize</code> event. Without loop prevention, AgentGuard would trigger itself endlessly. AgentGuard inspects <code className="font-mono text-[#55633C]">payload.sender.login</code>. If it ends with <code className="font-mono text-[#2E3325]">[bot]</code>, it drops the event instantly (<code className="font-mono text-[#55633C]">return None</code>).
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 2. LangGraph State Machine */}
          {activeDevSubTab === 'langgraph' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  LangGraph 6-Node Governed State Machine
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  How AgentState flows deterministically through nodes in `backend/app/agent/workflow.py`.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-2">AgentState Data Structure (`state.py`)</span>
                  <pre className="bg-[#2E3325] text-[#FBF8F3] p-3 rounded font-mono text-[11px] leading-relaxed overflow-x-auto">
{`class AgentState(TypedDict):
    run_id: UUID
    repo: str
    pr_number: int
    head_sha: str
    plan: str
    pr_diff: str
    changed_files: list[str]
    investigation: str
    reproduced: bool
    reproduce_details: str
    patch: str | None
    patch_file: str | None
    verified: bool
    verification_details: str
    summary_report: str
    action_intents: list[dict[str, Any]]
    policy_decisions: list[dict[str, Any]]
    halted: bool
    halt_reason: str
    paused: bool
    pending_approval_id: str | None
    total_tokens: int
    total_cost: float`}
                  </pre>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-2">Conditional Graph Routing</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Between each node (Plan &rarr; Investigate &rarr; Reproduce &rarr; Patch &rarr; Verify), a conditional edge router checks <code className="font-mono text-[#55633C]">state.get("halted")</code>. If an OPA rule denies an action or mandates approval, the graph safely bypasses remaining execution nodes and jumps directly to <code className="font-mono text-[#2E3325]">report</code> to record findings and seal the audit ledger.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 3. Circuit Breaker FSM */}
          {activeDevSubTab === 'circuitbreaker' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Circuit Breaker Finite State Machine (FSM)
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  How AgentGuard isolates failing LLM providers and automatically self-heals in `backend/app/infrastructure/llm/circuit_breaker.py`.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#6F7D55]/50">
                  <div className="flex items-center gap-2 font-bold text-[#6F7D55] mb-1">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>CLOSED (Normal)</span>
                  </div>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    All LLM completion calls are admitted. Successful invocations and failures are tracked in a sliding time window (default 60s).
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#8C4A3F]/50">
                  <div className="flex items-center gap-2 font-bold text-[#8C4A3F] mb-1">
                    <AlertTriangle className="w-4 h-4" />
                    <span>OPEN (Tripped)</span>
                  </div>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    Triggered when consecutive failures or error rate exceeds threshold. All requests to this provider are blocked immediately without network delay; traffic fails over to fallback.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#A88A4A]/50">
                  <div className="flex items-center gap-2 font-bold text-[#A88A4A] mb-1">
                    <RefreshCw className="w-4 h-4" />
                    <span>HALF-OPEN (Probe)</span>
                  </div>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    After recovery cooldown (default 30s), a single probe request is permitted. If probe succeeds, state transitions back to CLOSED. If probe fails, state returns to OPEN.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 4. Multi-Provider Router */}
          {activeDevSubTab === 'llmrouter' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Multi-Provider LLM Gateway & Failover Resolution
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  How `LLMGateway` dynamically routes requests and handles upstream timeouts in `backend/app/services/llm_gateway.py`.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-2">Candidate Prioritization Algorithm</span>
                  <ol className="list-decimal list-inside text-[#5F664F] text-[12px] space-y-1.5 leading-relaxed">
                    <li><strong>Task Specialists</strong>: Providers explicitly assigned to this task (e.g. Groq for formatting, Gemini for reasoning).</li>
                    <li><strong>Configured Default Primary</strong>: The globally selected primary provider.</li>
                    <li><strong>Configured Default Fallback</strong>: Secondary resilience provider.</li>
                    <li><strong>Emergency Backups</strong>: Any remaining active registered providers in the registry.</li>
                  </ol>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Zero-Drop Failover Loop</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    When candidate 1 fails with an HTTP 500, rate limit (429), or timeout, the circuit breaker records a failure, and the execution loop immediately attempts candidate 2 without failing the user run or dropping the GitHub PR review.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 5. OPA Rego Compiler */}
          {activeDevSubTab === 'opaengine' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Policy Specification & OPA Rego Compiler
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  How human-readable `policy.yaml` compiles into Open Policy Agent `data.json` documents in `backend/app/infrastructure/policy/rego_compiler.py`.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-2">1. The RegoCompiler Translation</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed mb-2">
                    Translates Pydantic-validated <code className="font-mono text-[#2E3325]">PolicyConfig</code> into OPA data structure:
                  </p>
                  <pre className="bg-[#2E3325] text-[#FBF8F3] p-3 rounded font-mono text-[10px] leading-relaxed overflow-x-auto">
{`data = {
  "policy": {
    "capabilities": {
      "allow": ["github.read_file", "github.comment_pr"],
      "approval": ["github.create_commit"],
      "deny": ["github.delete_repository"]
    },
    "commands": {
      "allow": ["^pytest.*", "^npm test.*"],
      "deny": [".*rm -rf.*", ".*curl.*|.*sh"]
    }
  }
}`}
                  </pre>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-2">2. Evaluation Logic (`main.rego`)</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed mb-2">
                    Enforces strict hierarchical decision precedence:
                  </p>
                  <div className="p-2.5 bg-[#FBF8F3] rounded border border-[#D9CFBF] font-mono text-[11px] space-y-1">
                    <div className="text-[#8C4A3F] font-bold">1. DENY (Highest Precedence)</div>
                    <div className="text-[#A88A4A] font-bold">2. REQUIRE_APPROVAL (Dual-Custody)</div>
                    <div className="text-[#6F7D55] font-bold">3. ALLOW (Clearance Granted)</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 6. Security Invariants */}
          {activeDevSubTab === 'security' && (
            <div className="card-archival p-6 space-y-6">
              <div className="border-b border-[#D9CFBF] pb-3">
                <h3 className="font-serif text-[22px] text-[#2E3325] font-medium">
                  Core Security & Concurrency Invariants
                </h3>
                <p className="text-[13px] text-[#5F664F] mt-1">
                  Non-negotiable architectural invariants enforcing fail-closed security and mathematical determinism.
                </p>
              </div>

              <div className="space-y-4 text-[13px]">
                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">PostgreSQL 64-bit Advisory Locks</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed mb-2">
                    In <code className="font-mono text-[#2E3325]">run_coordinator.py</code>, AgentGuard serializes operations per pull request using transaction-scoped advisory locks:
                  </p>
                  <code className="block bg-[#2E3325] text-[#FBF8F3] p-2.5 rounded font-mono text-[11px]">
                    SELECT pg_try_advisory_xact_lock(:lock_id)
                  </code>
                  <p className="text-[#5F664F] text-[12px] mt-2 leading-relaxed">
                    The lock key is deterministically generated by taking SHA256 of <code className="font-mono text-[#2E3325]">repo#pr_number</code> and unpacking the first 8 bytes as a signed 64-bit bigint. If another worker is already processing the PR, the lock acquisition fails instantly without blocking, preventing race conditions.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Fail-Closed Guarantee</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    In <code className="font-mono text-[#2E3325]">opa_evaluator.py</code>, if the OPA container crashes, times out, or fails to respond, AgentGuard logs a critical alert and explicitly returns <code className="font-mono text-[#8C4A3F]">Decision.DENY</code>. The system never falls back to permissive behavior under failure conditions.
                  </p>
                </div>

                <div className="p-4 bg-[#F7F2EB] rounded border border-[#D9CFBF]">
                  <span className="font-bold text-[#2E3325] block mb-1">Credential Isolation Choke Point</span>
                  <p className="text-[#5F664F] text-[12px] leading-relaxed">
                    AI agent nodes (Plan, Investigate, Patch) have zero access to GitHub credentials or cloud microVM tokens. All write operations must pass through <code className="font-mono text-[#55633C]">ToolGateway.execute()</code>, which re-verifies policy and checks for human sign-off before utilizing scoped credentials.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
