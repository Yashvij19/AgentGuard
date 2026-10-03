# Design Prompt: AI Agent Governance Dashboard

Paste this whole document into your AI UI design builder. A separate file, `animation-spec.md`, describes all motion. Use both together.

---

## 1. What you are building

A web dashboard where a team watches an AI coding agent work on GitHub pull requests, approves or rejects risky actions, edits safety policies, and monitors the health of the language model providers behind it.

Six areas: Overview, Runs, Run Detail, Approvals, Policy Studio, LLM Providers.

The feeling should be that of a private library or an old bank ledger room: calm, quiet, trustworthy, handcrafted. It must not look like a typical AI or SaaS template.

---

## 2. Design style

**Keywords:** classic, elegant, old money, editorial, warm, restrained, handcrafted, quietly confident.

**Inspiration to draw from:** printed annual reports, fine stationery, heritage law-firm and private-bank websites, literary magazines, museum catalogues, ledger books, letterpress cards.

**Must feel:**
- Human-made and considered, with small imperfections of taste (fine rules, small caps, thoughtful spacing), not machine-generated.
- Spacious and calm. Generous whitespace. Nothing shouting.
- Interactive but gentle. Everything responds, nothing flashes.

**Must never include:**
- Neon, glowing, gradient-glow, or electric colors
- Glassmorphism with heavy blur, purple/blue AI gradients, sparkle motifs
- Emoji anywhere (UI, toasts, empty states, buttons)
- Heavy drop shadows, thick colored borders, harsh pure black or pure white

---

## 3. Color theme (light only)

**Core palette (given):**

| Role | Hex |
|---|---|
| Sage (primary accent) | `#8B9A6E` |
| Cream (page background) | `#F7F2EB` |
| Beige / parchment (cards, panels, dividers) | `#EAE2D6` |
| Soft grey (inputs, table stripes, disabled) | `#EEEEEE` |

**Supporting tones (derived, keep muted and earthy):**

| Role | Suggested value |
|---|---|
| Primary text (deep olive-charcoal) | `#2E3325` |
| Secondary text | `#5F664F` |
| Muted / caption text | `#8A8E7C` |
| Sage dark (hover, pressed, focus ring) | `#6F7D55` |
| Sage light (soft fills, selected rows) | `#DDE3D0` |
| Hairline border | `#D9CFBF` |
| Card surface | `#FBF8F3` (slightly lighter than cream so cards lift softly) |

**Status colors (all desaturated, vintage-toned, no bright hues):**

| Meaning | Color | Used for |
|---|---|---|
| Good / Allowed / Completed / Closed | Moss `#6F7D55` on `#E3E8D6` | Completed, Allowed, CLOSED |
| Waiting / Paused / Half-open | Antique brass `#A88A4A` on `#F0E6CF` | Paused, HALF-OPEN, pending |
| Problem / Denied / Failed / Open | Oxblood `#8C4A3F` on `#EFDCD6` | Failed, Denied, OPEN |
| Running / Active | Deep sage `#5F6E4A` on `#DDE3D0` | Running |
| Stale / Inactive | Warm grey `#8A8E7C` on `#EEEEEE` | Stale |

**Rules:**
- Sage is the only accent. Use it for primary buttons, active navigation, links, focus, chart primary series.
- Body text must always reach readable contrast against cream. Never set body text in sage.
- Shadows, if used, are extremely soft, warm, and low opacity (for example `0 1px 2px rgba(46,51,37,0.06)`).

---

## 4. Typography

- **Headings and big numbers:** an elegant serif. First choice Cormorant Garamond, alternative Playfair Display or Libre Caslon. Regular or medium weight, never heavy bold.
- **Interface text (nav, labels, tables, buttons):** a clean humanist sans. First choice Source Sans 3, alternative DM Sans or Inter.
- **Code, diffs, JSON, YAML, SHA, Rego:** a refined monospace such as IBM Plex Mono or JetBrains Mono, sized slightly smaller than body.
- **Small labels and column headers:** small caps or uppercase with generous letter-spacing (0.08em), muted color.
- **Metric numbers:** large serif numerals, ideally oldstyle or tabular figures so they align.
- Comfortable line height (1.6 for prose). Sentence case for headings and buttons, not all caps.

---

## 5. Layout

- **Shell:** left sidebar (about 240px) on cream with a hairline right border, main content on cream with a maximum width of about 1280px, generous padding (40 to 56px).
- **Sidebar:** small wordmark at top set in serif with a thin ornamental rule beneath it. Below, links: Overview, Runs, Approvals (with a small count badge), Policies, LLM Providers. At the bottom a refresh control showing "Last updated 2 minutes ago".
- **Cards:** card surface color, 1px hairline border, radius 6 to 8px (subtle, not pill-like), inner padding 24px. Optionally a thin double-rule or inset border on featured cards for a stationery feel.
- **Section headers:** serif title, a one-line friendly description underneath in muted text, thin horizontal rule below.
- **Tables:** no heavy grid. Horizontal hairlines only, generous row height, subtle alternating tone using `#EEEEEE` at low opacity, sticky header on beige.
- **Responsive:** sidebar collapses into a top bar with a menu drawer on small screens; card grids reflow from 4 to 2 to 1 columns.

---

## 6. Iconography

- SVG only, from a thin-stroke line set (Lucide, Phosphor Light, or Tabler at 1.5px stroke). Consistent size (16, 18, 20px), color inherits text.
- No emoji, no filled cartoon icons, no icon backgrounds in bright colors.
- Status is communicated with small SVG marks plus text, not color alone.

---

## 7. Buttons and controls

- **Primary:** sage fill `#8B9A6E`, cream text, radius 6px, hover darkens to `#6F7D55`.
- **Secondary:** transparent with a 1px sage-dark border and olive-charcoal text, hover fills with sage light.
- **Quiet / text:** underlined on hover only, sage-dark text.
- **Destructive (Reject, Revert, Trip circuit):** transparent with oxblood text and border, hover fills oxblood at very low opacity. Never bright red.
- **Inputs, selects, textareas:** grey `#EEEEEE` or card surface, hairline border, sage-dark focus ring (2px, soft, not glowing).
- Include small SVG icons inside buttons where helpful, aligned left of the label.

---

## 8. Writing style for all text

Friendly, calm, plain language. Talk like a helpful assistant, not a system log. Short sentences. No jargon in labels where a simpler word works. No exclamation marks. No emoji.

Examples of tone:
- Empty approvals: "Nothing is waiting for you. The agent is working within its limits."
- Loading: "Gathering the latest runs..."
- Approve modal: "Are you sure you want to allow this change to `config/prod/app.yaml`?"
- Reject modal placeholder: "Tell the agent what went wrong. Your note is shared with it and kept in the audit record."
- Validate success toast: "Your policy looks good. No problems found."
- Validate error: "There is a mistake on line 14. A rule is missing its name."
- Save success: "Policy saved as version 4 and is now active."
- Provider probe success: "Gemini responded in 320 ms. Everything looks healthy."
- Circuit open helper text: "This provider is resting after repeated errors. Requests are being sent to the next provider."
- Live banner: "The agent is working on this run..." and "This run is paused and waiting for your decision."

Status wording: use Running, Paused, Completed, Failed, Stale; Allowed, Needs approval, Denied; Healthy (CLOSED), Testing (HALF-OPEN), Resting (OPEN) with the technical state in small text beside it.

---

## 9. Screens and every component

### 9.1 Global shell
- Sidebar navigation with links: Overview, Runs, Approvals (badge showing pending count), Policies, LLM Providers.
- Refresh button with a small "last updated" label to manually re-poll data.

### 9.2 Overview (`/`)
1. **Four metric cards:**
   - Total runs (e.g. 142)
   - Success rate (e.g. 97.2%)
   - Pending approvals (e.g. 2)
   - Tokens and cost (e.g. 340,000 tokens / $1.42)
   Each: small caps label, large serif number, small trend arrow SVG with muted caption.
2. **LLM providers status section:** a row of cards or pills for Gemini, Groq, NVIDIA NIM, OpenAI Compat. Each shows provider name, active model, circuit breaker state (health pill), error rate %, average latency (ms).
3. **Runs over time chart:** bar or area chart, runs per day split into Completed, Paused, Failed using the muted status colors. Thin axes, hairline gridlines, serif axis title, tooltip styled as a small parchment card.
4. **Recent runs table (5 to 10 rows):** columns Status, Repository and PR #, Commit SHA, Steps completed, Cost, Timestamp. Clicking a row opens that run's detail page.

### 9.3 Runs list (`/runs`)
1. **Filters:** search input (repo name like `octocat/Hello-World` or PR like `#42`), status dropdown (All, Running, Paused, Completed, Failed, Stale; multi-select allowed), pagination (Previous, Next, page size 10 / 25 / 50).
2. **Runs table columns:** status badge, repo and PR #, head commit SHA, trigger event (pull_request, check_suite), policy version (v1, v2), tokens used and cost, started at and duration. Each row has a "View trace" button linking to `/runs/:id`.
3. Friendly empty state when nothing matches: "No runs match your search. Try a different repository or clear the filters."

### 9.4 Run detail (`/runs/:id`)
1. **Live banner (only when Running or Paused):** "The agent is working on this run..." or "This run is paused and waiting for your decision." with a "Jump to approval" button when paused.
2. **Header summary card:** repo name, PR number, commit SHA link, overall status badge, total latency, tokens, cost in USD, policy version used.
3. **Decision trace timeline (vertical):** nodes for Plan, Investigate, Reproduce, Patch, Verify, Report. Each step contains:
   - Title and execution status (Allowed, Paused, Denied)
   - Duration and latency
   - **Action intent collapsible:** target file or command, capability requested (e.g. `github.create_commit`, `commands.exec`), the agent's rationale, and a "Show raw JSON" toggle using the JSON viewer
   - **Policy and risk box:** matched rule (e.g. `sensitive_paths`), risk score 0 to 100 shown as a slim bar, list of risk reasons in plain language
   - **LLM call collapsible (if used):** provider, model, prompt tokens vs completion tokens, cost of that call
   - **Tool outcome collapsible:** exit code, stdout, stderr, or GitHub comment ID

### 9.5 Approvals (`/approvals`)
1. **Queue of approval cards.** Each contains: request ID and relative time ("Requested 5 minutes ago"), repo, PR number, branch, proposed action (FILE_WRITE, COMMAND_EXEC, etc.), target, risk score and contributing factors, the policy reason approval is needed, and a **diff viewer** with line numbers, additions in soft moss tint and deletions in soft oxblood tint.
2. **Buttons per card:** Approve (primary), Reject (destructive outline).
3. **Approve modal:** "Are you sure you want to allow this change to `<target>`?" with a checkbox "Run it right away through the Tool Gateway" (checked by default), and buttons Confirm approval / Cancel.
4. **Reject modal:** title "Reject this action", textarea labelled "Why are you rejecting it?" with placeholder "Your note is shared with the agent and kept in the audit record.", buttons Confirm rejection / Cancel.

### 9.6 Policy Studio (`/policies`)
1. **Repository selector** dropdown (`octocat/Hello-World`, `octocat/backend`).
2. **Split view:**
   - Left: YAML policy editor with syntax highlighting in muted tones. Editable capability lists (allow, approval, deny), filesystem globs (read, write), command regex (allow, deny), risk weights and thresholds, token and dollar budgets.
   - Right: two tabs. **Compiled Rego** (read-only code) and **OPA status** (connection status, port, health check response, loaded rule bundles).
3. **Action bar:** Validate syntax, Save and deploy policy, Revert changes.
4. **Policy history drawer:** collapsible list of versions (v1, v2, v3) with timestamps.

### 9.7 LLM Providers (`/providers`)
1. **Provider cards grid** (Gemini, Groq, NVIDIA NIM, OpenAI Compat). Each card: model name, role (Primary, Fallback, Specialist), supported task types as small tag chips (Reasoning, Classification, Code generation), circuit breaker badge, 5-minute error rate %, average latency, total tokens and cost.
2. **Testing controls on each card:** Run health probe, Simulate failover (trip circuit), Reset circuit breaker.

---

## 10. Reusable components (build once, reuse everywhere)

1. **MetricCard**: label, serif number, trend icon
2. **StatusBadge**: soft-tinted pill with tiny SVG mark and text for run status and policy decisions
3. **TraceTimeline**: vertical line with numbered or dotted nodes
4. **JsonViewer**: collapsible tree, mono font
5. **DiffViewer**: line numbers, muted add/remove tints
6. **ApprovalCard**: metadata, risk factors, diff, action buttons
7. **ConfirmModal / PromptModal**: parchment dialog with soft cream overlay (not dark black)
8. **CodeEditor**: YAML editor with line numbers
9. **HealthPill**: small dot plus label for CLOSED, HALF-OPEN, OPEN
10. Also: Toast, Tabs, Drawer/Collapsible, Skeleton loader, RiskBar, Tag chip, EmptyState.

---

## 11. Motion

Motion is defined in the separate `animation-spec.md`. Summary: one shared motion language (same easing, same durations, staggered entrances), subtle and classic, everything synchronized, respects reduced-motion settings.

---

## 12. Final checklist for the builder

- Only the four given colors plus the muted supporting tones above
- Serif for headings and numbers, sans for UI, mono for code
- No emoji, no neon, no glow, no bright red or blue
- SVG line icons only
- Friendly, human, plain-language text everywhere including toasts and modals
- Every screen and component in sections 9 and 10 exists
- Feels like a private library or heritage bank, not a generic AI dashboard
