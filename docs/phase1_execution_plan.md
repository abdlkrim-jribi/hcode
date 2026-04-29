# Phase 1 UI Enhancement — Execution Plan

**Date**: 2026-04-02
**Based on**: Code inspection of all 12 desktop components, 14 VS Code components, tokens.css, global.css
**Method**: Static analysis + `tsc --noEmit` verification + grep for hardcoded values

---

## Priority Classification

### 🔴 CRITICAL Issues

**1. Settings overlay blocks entire app**
- **WHY critical**: When Settings opens, the *entire 3-column IDE layout is replaced* with a full-screen settings page (App.tsx L247-261). This is the most aggressive UX regression — one click and the user loses all context: editor, agent panel, file tree. No real IDE does this.
- **Complexity**: Low (change conditional render to side panel or in-place panel)
- **UX Impact**: High
- **Risk**: Low (self-contained render branch, no shared state mutation)

**2. AgentPanel lacks structured phase timeline**
- **WHY critical**: The AgentPanel is the primary surface where users understand what the AI is doing. Currently it's a flat text stream with divider lines for phases (lines like `── Planning ──`). There is no visual *timeline* — no filled/hollow circles, no hierarchy, no progress indication. This is the single biggest contributor to "prototype feel" because every competitor (Cursor, Windsurf) has a clear phase timeline.
- **Complexity**: Medium (requires new PhaseStep data model and timeline CSS)
- **UX Impact**: High
- **Risk**: Medium (AgentPanel is tightly coupled to AppState; must preserve all existing message rendering)

**3. Inline styles with hardcoded px values (active components only)**
- **WHY critical**: 25+ hardcoded `px` values scattered in inline styles across DiffReviewer (6px, 1px), FileExplorer (10px, 16px, 12px, 8px), StatusBar (10px), TaskComposer (4px), SettingsPanel (4px, 16px, 8px), and App.tsx (2px, 4px). These create visual inconsistency and make the design system meaningless. When a developer sees `gap: '8px'` next to `gap: 'var(--space-2)'` doing the same thing, it signals carelessness.
- **Complexity**: Low (mechanical replacement of px → var(--space-*))
- **UX Impact**: Medium (not visible individually, but collectively defines fit-and-finish)
- **Risk**: Low (values map 1:1 to existing tokens; no behavior change)

**4. Emoji icons throughout components**
- **WHY critical**: Six components use emoji for icons: 📁 (FileExplorer, StatusBar), ⚙️ (AgentPanel, SettingsPanel), 📄 (FileExplorer), ❌/✅ (AgentPanel, SettingsPanel), 📋/⚡ (TaskComposer), ⏳/▶ (TaskComposer). Emoji render inconsistently across OS versions and fonts (different sizes, different chromas, different alignment). They break the monochrome sophistication of the token system. This is the most immediately visible "prototype" signal — real IDEs use SVGs or text icons.
- **Complexity**: Low (replace emoji strings with plain-text glyphs or CSS pseudo-elements)
- **UX Impact**: High (instantly visible improvement to professionalism)
- **Risk**: Low (string replacement, no logic change)

---

### 🟠 IMPORTANT Issues

**5. DiffReviewer file tabs are inline-styled**
- **WHY important**: DiffReviewer.tsx has 15 inline style blocks (L78-152). The tab buttons are fully styled inline (L95-106) with 12 CSS properties each. This makes the tabs look correct but makes maintenance impossible and guarantees drift from the design system. Moving to CSS classes improves consistency and enables hover states.
- **Complexity**: Medium (extract ~15 inline style blocks to named CSS classes)
- **UX Impact**: Low (visually identical → slightly better with hover transitions)
- **Risk**: Low (pure styling extraction)

**6. No hover/focus-visible classes in global.css**
- **WHY important**: The existing token system has `--duration-fast: 100ms` and `--ease-default` defined but no reusable interaction classes. Every interactive element must re-implement hover transitions inline. Adding `.interactive` and `.clickable` utility classes in global.css would let all components inherit consistent hover behavior.
- **Complexity**: Low (add 15 lines of CSS)
- **UX Impact**: Medium (uniform interaction feel across all surfaces)
- **Risk**: Low (additive CSS, doesn't break existing styles)

**7. Collapsed panel strips use inline styles**
- **WHY important**: App.tsx L314-323 (Explorer collapsed strip) and L376-384 (Agent collapsed strip) are fully inline-styled with hardcoded values. These work but look inconsistent — the vertical rotated text label is clever but the implementation is fragile.
- **Complexity**: Low (extract to CSS classes)
- **UX Impact**: Low (small UI element, rarely visible)
- **Risk**: Low

**8. VS Code extension tokens.css drift risk**
- **WHY important**: Desktop `tokens.css` (97L) has layout variables (`--explorer-width`, `--agent-width`, `--titlebar-height`, `--tab-height`, `--statusbar-height`) that VS Code `tokens.css` (90L) doesn't include. The semantic tokens are currently identical, but without explicit sync discipline they'll drift over time.
- **Complexity**: Low (add missing variables to VS Code tokens.css)
- **UX Impact**: None (VS Code doesn't use these layout tokens)
- **Risk**: Low

**9. SettingsPanel references non-existent token names**
- **WHY important**: SettingsPanel.tsx line 63 uses `fontSize: 'var(--font-size-xs)'` — but the actual token is `--text-xs`. This is a silent CSS failure (the property falls back to inherited size). Same component also lacks proper CSS classes for section layout.
- **Complexity**: Low (fix variable name)
- **UX Impact**: Low (barely visible — subtitle text)
- **Risk**: Low

---

### 🟡 NICE-TO-HAVE Issues

**10. Dead components in desktop-app**
- **WHY nice-to-have**: AgentChat.tsx, PlanViewer.tsx, LogConsole.tsx, PhaseTimeline.tsx, VerificationPanel.tsx exist in the components directory but are NOT imported by App.tsx. They reference old token names (`--hcode-fg-dim`, `--sp-3`, `--font-size-xs`) that don't exist in the current tokens.css. This is dead code with zero UX impact.
- **Complexity**: Low (delete 5 files)
- **UX Impact**: None (not rendered)

**11. localStorage persistence for layout widths**
- **WHY nice-to-have**: The layout is resizable (drag handles work), but panel widths reset on reload. This is a convenience improvement, not a UX blocker.
- **Complexity**: Low (add 10 lines of localStorage read/write)
- **UX Impact**: Low (only matters on reload)

**12. VS Code extension components have inline styles**
- **WHY nice-to-have**: Similar to desktop, the VS Code webview components use inline styles. However, the VS Code extension is a secondary surface and the styles mostly reference tokens correctly (the inline styles use `var(--*)` values).
- **Complexity**: Medium (14 component files to audit)
- **UX Impact**: Low (secondary surface, webview already looks consistent)

**13. Missing SettingsPanel CSS classes in global.css**
- **WHY nice-to-have**: SettingsPanel uses classes like `.hcode-settings`, `.hcode-settings-title`, `.hcode-settings-section`, `.hcode-key-row`, `.hcode-key-input-row`, `.hcode-hint`, `.hcode-toggle-label`, `.hcode-banner`, `.hcode-label` — but most of these are NOT defined in global.css. They rely on inherited styles and inline overrides. This works but is messy.
- **Complexity**: Medium (define ~10 new CSS classes)
- **UX Impact**: Low (Settings is rarely used)

---

## Execution Order

### PHASE 1 — CRITICAL FIXES

**Step 1: Replace emoji icons with text glyphs**
- **WHY first**: Highest visibility-to-effort ratio. Takes 15 minutes, instantly removes the most obvious "prototype" signal across every surface. Every screenshot and first impression improves.
- **Expected outcome**: All 📁📄⚙️❌✅📋⚡⏳▶ replaced with consistent text characters from the monospace/UI font. FileExplorer uses `▸` arrows and text labels (`js`, `py`, `doc`). StatusBar uses `◉` instead of 📁. AgentPanel uses text labels. TaskComposer uses `Plan`/`Fast` text instead of emoji+text.
- **Dependencies**: None
- **Estimated time**: 20 minutes

**Step 2: Fix hardcoded px values in active components**
- **WHY second**: Quick mechanical fixes that bring discipline to the design system. Makes all subsequent component work cleaner because every value references tokens.
- **Expected outcome**: All `'4px'` → `'var(--space-1)'`, `'8px'` → `'var(--space-2)'`, `'10px'` → `'var(--text-2xs)'` (for font sizes), `'12px'` → `'var(--space-3)'`, `'16px'` → `'var(--space-4)'`, `'32px'` → `'var(--space-8)'` in inline styles. Also fix `'6px'` → `'var(--space-2)'` (closest token).
- **Dependencies**: None
- **Files**: StatusBar.tsx, TaskComposer.tsx, SettingsPanel.tsx, FileExplorer.tsx, DiffReviewer.tsx, App.tsx
- **Estimated time**: 30 minutes

**Step 3: Convert Settings from full-screen overlay to side panel**
- **WHY third**: Eliminates the worst UX regression. After this fix, opening Settings doesn't destroy the user's context.
- **Expected outcome**: Settings renders inside the Agent Panel area (right column) instead of replacing the entire app shell. Titlebar, editor, and explorer remain visible. Close button returns to the Agent Panel view.
- **Dependencies**: Step 2 (clean inline styles first)
- **Files**: App.tsx (remove L247-261 conditional branch, add Settings as agent panel content variant)
- **Estimated time**: 30 minutes

**Step 4: Add structured phase timeline to AgentPanel**
- **WHY fourth**: Core product differentiator. This is the visual signature of the product — the thing that makes it feel like a real AI IDE rather than a chat window. Requires most thought and has most risk, so it comes after the easier fixes are done.
- **Expected outcome**: AgentPanel header shows a 3-step horizontal progress indicator: `● Planning → ● Executing → ● Verifying`. Each step has semantic color, active state animation (subtle pulse), and completed checkmark. Below the progress indicator, the existing card-based stream continues (plan card, diff card, verification card). The stream becomes the *detail view* of the active phase.
- **Dependencies**: Step 2 (clean inline styles), Step 1 (clean icons)
- **Files**: AgentPanel.tsx (restructure), global.css (add `.hcode-phase-timeline` classes)
- **Estimated time**: 60 minutes

### PHASE 2 — IMPORTANT FIXES

**Step 5: Extract DiffReviewer inline styles to CSS classes**
- **WHY here**: After CRITICAL fixes, DiffReviewer is the component with the most inline style debt (15 blocks). Extracting these enables proper hover states on file tabs and consistent transitions.
- **Expected outcome**: DiffReviewer.tsx drops from 15 inline style blocks to 0. New CSS classes: `.hcode-diff-tabs`, `.hcode-diff-tab`, `.hcode-diff-tab--active`, `.hcode-diff-status-dot`, `.hcode-diff-actions`, `.hcode-diff-container`.
- **Dependencies**: Step 2
- **Estimated time**: 30 minutes

**Step 6: Add interaction utility classes to global.css**
- **WHY here**: Foundation for all components to have consistent hover/focus behavior. Adding `.interactive` and focus-visible patterns.
- **Expected outcome**: New CSS classes in global.css: `.interactive` (cursor:pointer + hover bg transition), `.interactive:hover` (--surface-4 bg), `.interactive:active` (scale 0.98), `:focus-visible` already exists. Also add `.spinner` keyframe animation.
- **Dependencies**: None
- **Estimated time**: 15 minutes

**Step 7: Extract collapsed panel strips to CSS classes**
- **WHY here**: App.tsx lines 314-323 and 376-384 have fully inline-styled collapsed strips. Extract to `.hcode-collapsed-strip` class.
- **Expected outcome**: Two inline style blocks (8 properties each) replaced with one CSS class. Vertical text label properly styled.
- **Dependencies**: None
- **Estimated time**: 15 minutes

**Step 8: Fix SettingsPanel broken token references**
- **WHY here**: `var(--font-size-xs)` doesn't exist; should be `var(--text-xs)`. Silent CSS failure.
- **Expected outcome**: SettingsPanel subtitle text renders at correct 11px size instead of inheriting parent size.
- **Dependencies**: None
- **Estimated time**: 5 minutes

**Step 9: Sync VS Code extension tokens.css**
- **WHY here**: Add the 5 layout variables from desktop tokens.css to VS Code tokens.css to prevent drift.
- **Expected outcome**: Both tokens.css files are identical except for VS Code `var(--vscode-*)` fallbacks.
- **Dependencies**: None
- **Estimated time**: 5 minutes

### PHASE 3 — NICE-TO-HAVE

**Step 10: Delete dead components**
- **WHY last**: Zero UX impact. Pure cleanup.
- **Expected outcome**: Remove AgentChat.tsx, PlanViewer.tsx, LogConsole.tsx, PhaseTimeline.tsx (desktop), VerificationPanel.tsx (desktop). These reference old token names and are not imported anywhere.
- **Dependencies**: Verify no imports reference them
- **Estimated time**: 10 minutes

**Step 11: Add localStorage layout persistence**
- **WHY last**: Convenience feature, not a UX fix.
- **Expected outcome**: Panel widths persist across page reloads. `localStorage.setItem('hcode-layout', ...)` on drag end, restore on mount.
- **Dependencies**: Step 7 (collapsed strips should be CSS-based first)
- **Estimated time**: 15 minutes

**Step 12: Add SettingsPanel CSS classes**
- **WHY last**: Settings is rarely used, appearance is adequate.
- **Expected outcome**: New CSS classes for `.hcode-settings-section`, `.hcode-key-row`, `.hcode-banner--warning`, etc.
- **Dependencies**: None
- **Estimated time**: 20 minutes

**Step 13: Audit VS Code extension inline styles**
- **WHY last**: Secondary surface. Already uses token references in most inline styles.
- **Expected outcome**: VS Code components use CSS classes instead of inline styles where possible.
- **Dependencies**: Steps 5-6 (patterns established in desktop first)
- **Estimated time**: 45 minutes

---

## Risk Analysis

### Visual Regression Risks

**R1: AgentPanel timeline may break message rendering**
- **Step**: Step 4
- **Description**: AgentPanel currently renders `chatMessages` as a flat stream with phase dividers. Adding a timeline header changes the visual structure. If the timeline state doesn't sync with the existing `appState.phase`, the UI could show conflicting states (e.g., timeline shows "Planning" but stream shows "Executing" cards).
- **Mitigation**: Keep the existing chat message rendering **exactly as-is** below the timeline. The timeline reads from the same `appState.phase` value. No new state required — the timeline is purely a *visual representation* of the existing phase.

**R2: Settings panel conversion may lose scroll behavior**
- **Step**: Step 3
- **Description**: Current Settings has `overflowY: auto` on a full-viewport container. Moving it inside the Agent Panel column (360px wide) may cause overflow issues with form fields.
- **Mitigation**: SettingsPanel already uses `.hcode-input` which has `width: 100%`. Test form layout at 360px width before committing.

**R3: DiffReviewer tab styling extraction may change appearance**
- **Step**: Step 5
- **Description**: DiffReviewer tabs use detailed inline styles (12 properties). Converting to CSS classes *must* produce pixel-identical output or the diff review experience regresses.
- **Mitigation**: Extract inline styles 1:1 to CSS classes. Do not "redesign" — just move the same property values to named classes. Verify with `tsc --noEmit` after changes.

### Refactoring Risks

**R4: FileExplorer computed indentation**
- **Component**: FileExplorer.tsx L51
- **Description**: `paddingLeft: \`${8 + depth * 12}px\`` is a computed value that can't be replaced with a single token. Depth-based indentation is inherently dynamic.
- **Safe approach**: Keep the computed padding but use token arithmetic: `calc(var(--space-2) + ${depth} * var(--space-3))`. This preserves the same 8+12n pattern (8=space-2, 12=space-3) while using tokens.

**R5: AgentPanel is tightly coupled to AppState**
- **Component**: AgentPanel.tsx
- **Description**: AgentPanel receives the entire `appState` object and makes rendering decisions based on `phase`, `planMarkdown`, `patches`, `verificationResult`, and `chatMessages`. Adding a timeline component means this coupling gets deeper.
- **Safe approach**: Don't decompose AppState. Add the timeline as a *view-only* component that derives its state from the existing `appState.phase`. No new state, no new props, no new data flow.

### Integration Risks (Phase 2 Backend)

**R6: Settings panel position affects IPC command flow**
- **Phase 2 impact**: Settings panel currently intercepts the entire render tree. When DaemonSupervisor.send() is implemented in Phase 2, Settings needs to remain accessible while the agent is running (e.g., to change API keys mid-task).
- **Avoidance**: Step 3 solves this by moving Settings into the Agent Panel area. The editor and daemon communication remain unaffected because Settings is now scoped to one panel, not the whole app.

**R7: AgentPanel timeline must accept streaming messages**
- **Phase 2 impact**: When spawn_output_reader() sends real-time JSONL from the Python daemon, the timeline must update incrementally. If the timeline is designed with static state in mind, streaming will break it.
- **Avoidance**: Design the timeline to read from `appState.phase` which already updates via the reducer on each `SET_PHASE` action. The existing reducer pattern supports streaming natively — each daemon message dispatches an action, reducer updates phase, React re-renders timeline.

**R8: DiffReviewer CSS classes must not conflict with Monaco**
- **Phase 2 impact**: Monaco editor injects its own CSS classes into the DOM. Custom class names must not collide.
- **Avoidance**: All custom classes use the `hcode-diff-*` prefix. Monaco uses `monaco-*` prefix. No collision risk with namespaced prefixes.

---

## Quality Validation

### 1. Will CRITICAL fixes achieve VS Code/Cursor quality?

**Partial.**

CRITICAL fixes address the *most obvious* gaps:
- Settings overlay → fixed (no more app-destroying modal)
- Emoji icons → replaced (monochrome consistency)
- Phase timeline → added (clear agent state)
- Design token discipline → enforced (no hardcoded values)

Still missing after CRITICAL:
- No command palette (Ctrl+Shift+P) — not a Phase 1 scope item
- No breadcrumbs — not a Phase 1 scope item
- No multi-tab editor — existing limitation
- No streaming display — depends on Phase 2 backend

**Honest assessment**: After CRITICAL fixes, Hcode will feel like a *well-designed alpha* rather than a prototype. It won't match VS Code's polish (that requires years of iteration), but it will no longer have obvious amateur signals.

### 2. Will developers immediately see the difference?

**Yes.**

Three changes will be immediately visible:
1. Emoji → text icons (every surface)
2. Phase timeline (AgentPanel header)
3. Settings no longer breaks the layout

These are "first 5 seconds" improvements that define the product's perceived quality.

### 3. Does this address "prototype feel"?

**Yes, for the main surfaces.**

"Prototype feel" comes from:
- ~~Emoji icons~~ → Fixed in Step 1
- ~~No agent state clarity~~ → Fixed in Step 4
- ~~Settings destroying layout~~ → Fixed in Step 3
- ~~Inconsistent spacing~~ → Fixed in Step 2

Remaining prototype signals (multi-tab, breadcrumbs, command palette) are feature gaps, not design gaps. Phase 1 is specifically about design polish.

### 4. Can we ship after CRITICAL fixes?

**Yes, for internal use and demos.**

CRITICAL fixes produce a coherent, professional-looking IDE that can be shown to stakeholders. The IMPORTANT fixes (hover states, DiffReviewer cleanup, token sync) improve internal code quality but don't change what users see significantly.

**Recommendation**: Ship after CRITICAL. Do IMPORTANT in a separate PR for clean review.

---

## Summary

| Category | Count | Estimated Time |
|:---|:---|:---|
| 🔴 CRITICAL | 4 issues | ~2.5 hours |
| 🟠 IMPORTANT | 5 issues | ~1.5 hours |
| 🟡 NICE-TO-HAVE | 4 issues | ~1.5 hours |
| **Total** | **13 issues** | **~5.5 hours** |

**Recommended approach**:

1. Execute CRITICAL (Steps 1-4) as one batch
2. Run `tsc --noEmit` after each step to verify no regressions
3. Stop after Step 4 for review
4. Execute IMPORTANT (Steps 5-9) as second batch
5. NICE-TO-HAVE only if time budget allows

**Risk level**: LOW. All changes are CSS/JSX-only. No state management changes. No IPC changes. No new dependencies. Every change is independently verifiable with `tsc --noEmit`.
