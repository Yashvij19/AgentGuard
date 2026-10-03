# Animation Spec: AI Agent Governance Dashboard

Give this file to the AI builder together with `design-prompt.md`. It says which motion to use, where it applies, how it looks, and what it should make the user feel.

---

## 1. Motion philosophy

**Feeling:** turning the pages of a fine book, opening a drawer in a wooden desk, a ledger being filled in by hand. Slow, soft, deliberate. Never bouncy, flashy, or techy.

**The rule of synchronization:** every animation on the site speaks one language. Same easing, same small set of durations, same direction of travel (things rise gently from below and settle; things leave by fading and sinking slightly). If two things animate at once, they share timing or are staggered by a fixed step, so the screen always moves as one composed piece.

**Never use:** glow or pulse-glow effects, neon trails, bouncing or elastic springs, spinning loaders, shaking, confetti, flashing colors, parallax that makes people dizzy, sound.

---

## 2. Shared motion tokens (use everywhere)

| Token | Value | Use |
|---|---|---|
| Easing standard | `cubic-bezier(0.22, 0.61, 0.36, 1)` | Almost everything (soft ease-out) |
| Easing gentle in-out | `cubic-bezier(0.45, 0, 0.25, 1)` | Drawers, modals, tab sliders |
| Duration fast | 160ms | Hover, press, color changes |
| Duration base | 280ms | Buttons, badges, tooltips, toggles |
| Duration slow | 480ms | Cards entering, drawers, modals |
| Duration graceful | 900 to 1200ms | Number counting, chart drawing, timeline line drawing |
| Stagger step | 60ms | Delay between siblings entering (cap at 8 items, then enter together) |
| Rise distance | 12px | Standard entrance offset (translateY) |
| Hover lift | 2px | Card lift on hover |

Only animate `opacity`, `transform`, `clip-path`, `stroke-dashoffset`, and soft color changes. Avoid animating layout properties where possible.

**Reduced motion:** if the user prefers reduced motion, remove all movement and counting, keep only quick opacity fades (120ms), and show final values immediately.

---

## 3. Page-level choreography

### 3.1 Page load and route change
- **Where:** every screen.
- **What:** the content area fades from 0 to 1 while rising 12px over 480ms. Children then enter in a fixed order: page title, subtitle, and the thin rule (rule draws left to right over 600ms), then the first row of cards, then tables and charts, each staggered by 60ms.
- **Route leaving:** current page fades out and sinks 6px over 200ms before the next enters, so transitions feel like turning a page.
- **User feels:** the page is being laid out neatly, unhurried.

### 3.2 Sidebar
- **On first load:** links fade in from the left with 60ms stagger, the wordmark first, its ornamental rule drawing beneath it.
- **Active link indicator:** a thin sage bar on the left edge slides vertically to the newly active link (280ms, gentle in-out) instead of jumping. The active link's text color eases to sage-dark.
- **Hover on link:** text shifts 3px to the right and a soft beige background fades in (160ms).
- **Approvals badge:** when the pending count changes, the old number slides up and fades while the new one rises in (280ms). The badge scales from 0.9 to 1 once. No repeated pulsing.

### 3.3 Refresh control
- **Where:** sidebar bottom.
- **Click:** the refresh SVG rotates a single smooth 360 degrees (700ms). While data loads, the "Last updated" label cross-fades to "Refreshing...", then to "Just now".
- **Data arriving:** updated cards and rows fade their content briefly (opacity 0.6 to 1, 280ms) rather than reloading abruptly.

---

## 4. Overview screen

### 4.1 Metric cards (4)
- **Entrance:** rise 12px and fade in, staggered 60ms left to right.
- **Numbers:** count up from zero over 1000ms with the standard easing, all four finishing together so the row settles as one. Percentages and dollar values count with their decimals. Use tabular figures so digits do not jitter.
- **Trend icon:** the small arrow draws itself (stroke draw, 500ms) after the number finishes.
- **Hover:** card lifts 2px, its hairline border deepens slightly toward sage, and a very soft shadow fades in (280ms).
- **When value changes on refresh:** digits roll or cross-fade in place (280ms), no counting from zero again.

### 4.2 Provider status cards or pills
- **Entrance:** same stagger as metric cards, following them.
- **Health pill dot:** CLOSED shows a still dot. HALF-OPEN shows a very slow, faint breathing (opacity 0.6 to 1 over 2.4s, looped). OPEN is still and slightly muted. No glow, no ripple.
- **State change:** when a breaker changes state, the dot color cross-fades over 480ms and the label text slides up and swaps (280ms).
- **Hover:** card lifts 2px; the error rate and latency values underline briefly with a hairline that draws left to right.

### 4.3 Runs over time chart
- **Entrance:** bars grow upward from the baseline (600ms, staggered 40ms per bar) or the area line draws left to right using stroke draw (1200ms) then the fill fades in (400ms).
- **Hover on a bar or point:** the hovered series brightens slightly while others fade to 60% opacity (160ms). A small parchment-colored tooltip fades in and follows the pointer with light easing (a little lag, like ink settling).
- **Legend toggle:** clicking a legend item fades that series out and the remaining bars smoothly re-flow (480ms).

### 4.4 Recent runs table
- **Entrance:** rows fade and rise, staggered 40ms (cap at 10 rows).
- **Row hover:** background gently tints beige from left to right (a soft wipe, 280ms), and a small chevron SVG slides 4px in from the right edge.
- **Row click:** the row briefly deepens (120ms), then the page transition begins (see 3.1), with the clicked row's status badge appearing to carry into the detail page header by cross-fading.
- **Status badges:** fade their tint in with the row, no bouncing.

---

## 5. Runs list

### 5.1 Search input
- **Focus:** border color eases to sage-dark, and a soft 2px focus ring fades in (160ms). The magnifier SVG slides 2px left and its stroke darkens.
- **Typing:** the table filters live. Removed rows fade out and collapse in height (280ms), remaining rows glide into place (480ms). New matches fade in with stagger.
- **Clear:** an X icon fades in once text exists and fades out when empty.

### 5.2 Status dropdown and page-size select
- **Open:** menu unfolds downward with a soft clip-path reveal and fade (280ms). Options stagger in by 30ms.
- **Selected chip (multi-select):** chips scale from 0.92 to 1 and fade in; removing a chip fades and shrinks it.
- **Close:** reverse of open, faster (160ms).

### 5.3 Pagination
- **Buttons:** hover fills softly; press sinks 1px.
- **Page change:** current rows fade out (160ms), then the next page rows enter with the standard stagger. Page number cross-fades.

### 5.4 View trace button
- **Hover:** underline draws left to right beneath the label and an arrow SVG slides 4px right (160ms).

---

## 6. Run detail

### 6.1 Live banner (Running or Paused)
- **Entrance:** slides down from above the header and fades in (480ms).
- **Running state:** three small dots or a thin line beneath the text move in a slow, calm wave (2s loop, low contrast). No spinner. Text: "The agent is working on this run..."
- **Paused state:** the wave stops and settles into a still brass line. The "Jump to approval" button fades in (280ms).
- **Jump to approval click:** page scrolls smoothly (700ms, gentle in-out) to the approval and the target card gets a soft one-time outline flash in sage (600ms, then gone).
- **Leaving:** when the run finishes, the banner fades and collapses upward (480ms).

### 6.2 Header summary card
- Entrance with the standard rise. Numbers (latency, tokens, cost) count up together over 900ms. Status badge fades in last with a small scale from 0.94 to 1.

### 6.3 Decision trace timeline
- **The line:** the vertical timeline line draws downward from the first node to the last over 1200ms.
- **Nodes:** each node appears just as the line reaches it (dot scales from 0 to 1, 280ms), then its step card fades and rises beside it. Steps therefore appear in sequence like entries being written in a ledger.
- **Step status marks:** Allowed shows a check drawn stroke by stroke (400ms). Denied shows a small cross drawn the same way. Paused shows two short bars fading in. All in muted status colors.
- **Step hover:** the node ring softly expands (scale 1 to 1.15, 280ms) and the card's left edge shows a thin sage rule that grows from top to bottom.
- **Live update:** when a new step arrives during a running run, the line extends and the new node appears with the same sequence, and the page does not jump.

### 6.4 Collapsibles and drawers (Action intent, LLM call, Sandbox outcome, Policy box)
- **Open:** height expands smoothly (480ms, gentle in-out) while contents fade in with a 60ms delay after the expansion starts. The chevron SVG rotates 90 degrees (280ms).
- **Close:** contents fade first (160ms), then height collapses (280ms).
- **Raw JSON toggle:** the pretty view cross-fades to the raw view (280ms), and the toggle's sliding knob glides with the standard easing.
- **JSON viewer tree nodes:** expand and collapse like the drawers above but faster (200ms), children staggered 20ms.

### 6.5 Risk bar (0 to 100)
- Fills from left to right over 900ms to its value, color set by level using muted moss, brass, or oxblood. The number counts up in sync with the bar. On hover, small tick marks for the thresholds fade in.

### 6.6 Risk reasons list
- Items fade and rise with 60ms stagger when the Policy box opens.

---

## 7. Approvals

### 7.1 Approval cards
- **Entrance:** rise and fade with stagger (60ms).
- **Hover:** lift 2px with a very soft shadow.
- **Diff viewer:** line numbers and lines reveal top to bottom in blocks of a few lines (a quick 400ms cascade), added lines fading in with a moss tint, removed lines with an oxblood tint. Hovering a line lightens the whole row (120ms).
- **Risk factors:** small chips fade in one after another.

### 7.2 Approve and Reject buttons
- **Hover:** Approve deepens to sage-dark; Reject fills with a very faint oxblood tint.
- **Press:** sinks 1px and scales to 0.98 (120ms), releases back softly.

### 7.3 Modals (Approve confirmation, Reject reason)
- **Open:** the overlay fades to a soft warm cream-brown veil (not black, 280ms). The dialog rises 16px and fades in with a very slight scale from 0.98 to 1 (480ms, gentle in-out). Its contents stagger in by 40ms (title, text, checkbox or textarea, buttons).
- **Close or cancel:** dialog fades and sinks 8px (200ms), overlay follows.
- **Checkbox:** the tick draws itself with a short stroke animation (200ms).
- **Textarea focus:** border eases to sage-dark and label lifts slightly.
- **Confirm approval:** button label swaps to "Approving..." with a slim line loader under it; on success the dialog closes and the toast appears.
- **Empty rejection reason submit:** the textarea border briefly tints oxblood with a very small, slow horizontal nudge (2px, once, 300ms) and a friendly helper line fades in: "Please add a short note so the agent can learn from it."

### 7.4 After a decision (card leaves the queue)
- **Approved:** card's border eases to moss, a check draws in the corner, then the card fades and slides out to the right while its height collapses (600ms). Remaining cards glide up to fill the gap (480ms).
- **Rejected:** same, with a muted oxblood tint and the card sliding out to the left.
- **Sidebar badge and Pending metric:** counts change in sync with the card leaving (slide-swap numbers, section 3.2).
- **Empty queue:** when the last card leaves, the empty state fades in (quiet illustration drawn from thin SVG lines, stroke-drawn over 1200ms).

### 7.5 Toasts
- **Enter:** slide in from the bottom-right by 16px and fade (280ms). A thin progress hairline along the bottom shrinks over the toast's visible time (4s).
- **Exit:** fade and drift down 8px (200ms). Toasts stack with gentle repositioning (280ms).

---

## 8. Policy Studio

### 8.1 Repository selector
- Same dropdown unfold as 5.2. On change, both panels cross-fade to the new policy (280ms out, 480ms in) so the swap feels like exchanging a page.

### 8.2 Split view
- **Entrance:** left editor rises first, right panel follows 100ms later.
- **Divider hover:** if resizable, the divider's hairline thickens softly and the cursor changes; dragging is 1:1 without lag.

### 8.3 Code editor
- **Focus:** editor border eases to sage-dark. Current line gets a soft beige highlight that follows the caret smoothly (120ms).
- **Unsaved changes:** a small dot fades in next to the file title, and the "Revert changes" and "Save" buttons become fully opaque from a resting 60% state (280ms).
- **Syntax error:** the offending line gets a thin oxblood underline that draws across (200ms) with a quiet gutter mark.

### 8.4 Tabs (Compiled Rego / OPA status)
- The active-tab underline slides between tabs (280ms, gentle in-out). Panel content cross-fades with a 6px vertical shift.
- **OPA status:** the health check response lines type in line by line (40ms per line) once, when first opened.

### 8.5 Action bar buttons
- **Validate syntax:** while running, the label becomes "Checking..." with a slim line loader. On success a check draws inside the button for a moment and a friendly toast appears. On error, the editor scrolls to the line (smooth) and the line's underline draws.
- **Save and deploy:** on success, the version number in the history drawer header counts up by one (slide-swap), a new history row appears at the top with a soft highlight that fades out over 1.5s, and the unsaved dot fades away.
- **Revert changes:** editor text cross-fades back to the saved version (280ms).

### 8.6 Policy history drawer
- Opens like the standard collapsible. Rows stagger in by 40ms. Hovering a row tints it beige and shows a small "View" arrow sliding in.

---

## 9. LLM Providers

### 9.1 Provider cards grid
- **Entrance:** stagger left to right, top to bottom (60ms).
- **Numbers:** error rate, latency, tokens, and cost count up together (900ms).
- **Hover:** lift 2px; task type chips gently brighten one after another (40ms stagger).

### 9.2 Circuit breaker badge
- **CLOSED to OPEN (after Simulate failover):** badge color cross-fades from moss to oxblood over 480ms; the card's top hairline accent changes color in sync; the helper text "This provider is resting after repeated errors. Requests are being sent to the next provider." fades in below.
- **Fallback indication:** the fallback provider's card briefly shows a soft sage outline (600ms) and a tag "Now handling requests" fades in, to show where traffic moved. Both changes happen at the same moment so the cause and effect read as one event.
- **OPEN to HALF-OPEN to CLOSED (after Reset):** badge steps through each color with a 480ms cross-fade; the breathing dot appears during HALF-OPEN then stills.

### 9.3 Testing buttons
- **Run health probe:** button label becomes "Checking..." with a slim line loader sliding along its bottom edge. On result, a small latency figure fades in beside the button ("320 ms") and a toast confirms.
- **Simulate failover:** press shows a small confirmation popover (unfolds with the standard reveal). After confirming, the sequence in 9.2 plays.
- **Reset circuit breaker:** hover fills with faint sage; press plays the reverse sequence in 9.2.

---

## 10. Global component behavior

### 10.1 Buttons
- **Hover:** background color eases (160ms); icon shifts 2px in its direction of meaning.
- **Press:** sink 1px, scale 0.98 (120ms).
- **Loading:** label swaps, thin line loader slides across the bottom edge; never spinners.
- **Focus (keyboard):** a soft 2px sage-dark ring fades in (160ms).

### 10.2 Status badges
- Fade their tint in with their parent. When status changes, the old text slides up and out while the new text slides up in, and the tint cross-fades (280ms).

### 10.3 Tooltips
- Appear after 300ms hover delay, fade and rise 4px (160ms), styled as a small parchment card.

### 10.4 Skeleton loading
- Placeholder blocks in beige and grey with a very slow, faint light sweep (2.4s loop, low contrast). When real content is ready, it cross-fades over the skeleton (280ms) with the same layout, so nothing jumps.

### 10.5 Links and text
- Underlines draw from left to right on hover (160ms). Never color flashes.

### 10.6 Scroll reveals
- On long pages (Run Detail, Policies), sections below the fold fade and rise 12px as they enter the viewport, once only, with the standard stagger.

### 10.7 Ornamental details (handmade feel)
- Thin rules beneath section titles draw left to right on entrance (600ms).
- Small ornamental dividers and stationery-style corner lines on featured cards draw themselves once (stroke-dashoffset, 900ms) when the card first appears.
- Keep these to a few places so they feel special rather than repetitive.

---

## 11. Quick reference: where each effect applies

| Effect | Applied to |
|---|---|
| Fade and rise entrance (12px, stagger 60ms) | All pages, metric cards, provider cards, approval cards, table rows, sections on scroll |
| Count-up numbers (900 to 1000ms) | Metric cards, header summary, provider stats, risk score |
| Stroke draw | Timeline line, chart lines, check and cross marks, empty-state illustration, ornamental rules |
| Sliding indicator | Sidebar active link, Policy tabs |
| Soft hover lift (2px) | Cards of every type |
| Beige wipe on hover | Table rows, history rows |
| Smooth expand and collapse | Timeline drawers, JSON tree, policy history, dropdowns |
| Cross-fade swap | Status badges, health pills, repository policy change, Refresh label, JSON raw toggle |
| Modal rise with soft veil | Approve and Reject modals, failover confirmation |
| Slide-out with gap closing | Approval cards after decision, dismissed toasts |
| Slim line loader (no spinner) | Buttons in loading state, Validate, Save, Probe, Approve |
| Slow breathing dot (2.4s) | HALF-OPEN health pill, running banner wave |
| Skeleton light sweep | Any loading state |
| Smooth scroll with one-time outline flash | Jump to approval |

---

## 12. Final checklist for the builder

- All motion uses the shared tokens in section 2
- Related animations start together or in fixed stagger so the whole screen feels choreographed
- No glow, neon, bounce, spin, or flashing
- Motion never blocks the user; every animation is skippable by interaction
- Reduced-motion users get fades only
- Motion always explains something: what arrived, what changed, or where traffic went
