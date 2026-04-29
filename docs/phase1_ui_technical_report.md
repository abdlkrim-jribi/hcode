# Hcode Phase 1 — UI/UX Technical Report & Architecture Audit

**Target Model:** Claude Opus 4.6 (Antigravity) / Gemini 3.1 Pro (High)
**Phase:** 1 (Completed)
**Date:** 2026-04-13

---

## 1. SYSTEM OVERVIEW

The Hcode UI system is an IDE-grade interface designed to mediate complex interactions between a developer and an autonomous AI coding agent. It is built to run across two distinct surfaces:
1. **Desktop App:** Built with React, TypeScript, and Vite, wrapped in a Tauri shell to provide a standalone, highly performant native-feeling experience.
2. **VS Code Extension:** Built using a React Webview to integrate directly into the developer's existing environment.

**Core Design Philosophy:**
The philosophy is "IDE-like, Agent-driven." The UI avoids feeling like a generic "chat wrapper." Instead, it treats the AI as an active participant in the coding loop. Information is structured hierarchically—plans, file diffs, and executions are treated as primary artifacts, while raw text streaming acts as a supplementary thinking process. It aims for the quiet confidence and restrained depth of premium developer tools like Cursor or Windsurf.

---

## 2. UI ARCHITECTURE

### 2.1 Folder Structure

The desktop application UI is structured as follows under `desktop-app/src-ui/src/`:

*   **`components/`**: Contains all reusable structural elements.
    *   `AgentPanel.tsx`: The primary interaction surface housing the timeline, stream, and task input.
    *   `DiffReviewer.tsx`: Specialized component for granular viewing of before/after code states.
    *   `FileExplorer.tsx`, `MonacoEditor.tsx`, `SettingsPanel.tsx`, `StatusBar.tsx`, `StreamingDisplay.tsx`, `ErrorPanel.tsx`.
*   **`styles/`**: Centralized styling.
    *   `tokens.css`: The source of truth for all design variables (colors, spacing, typography).
    *   `global.css`: Base resets, utility classes, and layout scaffolding.
*   **`types/`**: Enforces strict TypeScript contracts.
    *   `agent-events.ts`: Defines the unified event stream union (`AgentEvent`), ensuring type safety between the daemon and UI.
*   **`ipc/`**: Handles communication with the Tauri backend.
    *   `bridge.ts`: Tauri command invocations.
    *   `mock-events.ts`: Local daemon simulation for isolated UI testing.

**Layer Responsibilities:**
The architecture strictly separates concerns. Components are strictly presentational (views). `App.tsx` acts as the global controller and state orchestrator. The `ipc/` layer abstracts all backend bindings, ensuring components remain unaware of Tauri's existence.

### 2.2 Rendering Flow

The data flow is strictly unidirectional, following the React/Flux paradigm:

1.  **Event Source:** `App.tsx` receives events from either user interaction (clicks, typing) or IPC callbacks (daemon messages).
2.  **State Updator (Reducer):** All events are mapped to heavily typed actions (e.g., `HANDLE_AGENT_EVENT`) and digested by the `reducer` function in `App.tsx`.
3.  **Propagation:** The newly derived `AppState` is passed down to child components (`AgentPanel`, `DiffReviewer`, `StatusBar`) via props.
4.  **Render:** Components deterministically re-render based purely on their props.

`App.tsx` is the sole bearer of mutable state, preventing "state tearing" and ensuring the UI always accurately reflects the agent's actual phase.

---

## 3. DESIGN SYSTEM

### 3.1 Tokens

Located in `tokens.css`, the token system drives visual consistency:
*   **Colors:** Uses a cohesive 5-layer surface system with a baseline 228-degree hue (cool dark blue/gray), reducing eye strain. Semantic colors (Success, Warning, Error) and Phase colors (Thinking, Planning, Executing, Verifying) are explicitly defined.
*   **Spacing:** A rigid 4px base grid (`--space-1` to `--space-10`) prevents arbitrary layouts.
*   **Typography:** Defaults to system fonts (Inter/Segoe) and specialized monospace (`JetBrains Mono`/`Fira Code`), with a distinct scale (`text-2xs` to `text-xl`).
*   **Transitions:** Standardized easing (`--ease-default`) and durations (`fast`, `normal`, `slow`) ensure consistent kinetic feel.

**Why it's good:** It eliminates "magic numbers." A developer can instantly build a new component that feels native to Hcode by exclusively relying on `var(--token-name)`.
**Where it's violated:** Occasional legacy inline styles in deeply nested components (e.g., computed depth margins in FileExplorer).

### 3.2 Consistency Analysis

Following Phase 1 refactoring, consistency is high:
*   **Hardcoded values:** Eradicated from major components (`StatusBar`, `AgentPanel`). Replaced with `var(--space-*)`.
*   **Icons:** Emoji usage (❌, 📁) has been largely replaced with text glyphs (▸, ◉), significantly elevating the professional tone.
*   **Color Discipline:** Semantic colors are used strictly for their intended purposes (e.g., `var(--semantic-error)` only used for circuit breaks and test failures).

---

## 4. LAYOUT SYSTEM

### 4.1 Structure

The layout is a classic horizontal 3-panel IDE design:
1.  **Left Panel (Explorer):** Fixed/resizable width, handles project navigation.
2.  **Center Panel (Editor):** The dominant flex element. Holds the active code context via regular expression, driving the primary developer focus.
3.  **Right Panel (Agent):** The command center. Displays agent history, plans, and input.

The hierarchy correctly prioritizes the code editor, while giving the Agent Panel enough presence to act as a co-pilot without obscuring code.

### 4.2 Behavior

*   **Resizable:** Panels utilize a robust resizer system.
*   **Collapsible:** The Explorer and Agent panels can collapse into narrow sidebar strips to maximize editor real estate.
*   **Persistence:** Layout dimensions are stored, maintaining developer preference across sessions.

### 4.3 UX Evaluation

*   **Does it feel like an IDE?** Yes. It mimics the familiar muscle-memory of VS Code, mapping seamlessly to developer expectations.
*   **Is hierarchy clear?** Yes. The title bar and status bar cap the experience top and bottom, while the 3 columns hold distinct operational domains.
*   **Friction points:** Transitioning focus between the Editor and the Agent's Task Composer still requires mouse interaction rather than dedicated hotkeys (e.g., `Ctrl+L` in Cursor).

---

## 5. COMPONENT SYSTEM

### 5.1 AgentPanel
*   **Structure:** Composed of a header, timeline, stream track, specialized artifact cards (Plan, Verification, Diff Pending), and a Task Composer pinned to the bottom.
*   **Timeline:** Implements a dynamic, CSS-animated `Plan → Execute → Verify` spinner system. Highly successful at orienting the user to the agent's current macro-state.
*   **Strengths:** Effectively unifies chat with structured data. It prevents the UI from becoming a wall of text.
*   **Weaknesses:** As the artifact cards stack up, scrolling can become disjointed.

### 5.2 DiffReviewer
*   **Structure:** File tabs for selecting a file, and a specialized split-pane or inline diff viewer.
*   **UX Quality:** Strong. Actions (`Accept`, `Reject`) are localized perfectly to the file in question, forcing targeted code review.

### 5.3 TaskComposer
*   **Structure:** Auto-growing textarea with Mode selection (`Plan` vs `Fast`).
*   **Usability:** Clear affordances (`Ctrl+Enter` to send). Disabling the input while the agent is `executing` prevents queue-flooding and UX desync.

### 5.4 Explorer
*   **Structure:** Standard recursive directory tree.
*   **Consistency:** Adheres well to token spacing, replacing legacy emojis with proper arrow carets.

### 5.5 StatusBar
*   **Structure:** Left (Phase indicator), Center (Pending patches warning), Right (Daemon health, Circuit Breaker).
*   **UX:** Excellent. The pulsating Phase Indicator and static Daemon connection dots provide high-signal, low-noise telemetry.

---

## 6. INTERACTION SYSTEM

*   **Hover states:** Implemented via standardized `.interactive` CSS transitions, utilizing `--surface-4` backgrounds.
*   **Focus states:** Utilizing `:focus-visible` to draw borders on focused inputs, heavily relying on `--accent`.
*   **Loading states:** Implemented via keyframe animations (`hcode-spin` for timeline, `hcode-pulse` for status bar dots, `hcode-stream-dots` for streaming).
*   **Empty states:** Present, but currently basic (e.g., empty agent panel before first prompt).

**Evaluation:** Smooth and purposeful. The interactions feel lightweight. The removal of heavy blocking modals (like the old Settings overlay) vastly improves the kinetic flow.

---

## 7. STATE INTEGRATION (UI SIDE)

The UI's reaction to state is incredibly tight due to the `handleAgentEvent` mapping in `App.tsx`.

*   **Reaction to Phase:** When `appState.phase` transitions from `planning` to `executing`, multiple isolated components react instantly. The StatusBar text changes, the StatusBar dot begins pulsing, the AgentPanel timeline lights up the `Execute` step and begins spinning, and the TaskComposer lock activates.
*   **Streaming representation:** Handled expertly via the `StreamingDisplay` component. It implements an auto-scroll lock that respects manual user intervention (pausing auto-scroll if the user looks upward), preventing the jarring "scroll-hijack" common in naive LLM wrappers.
*   **Error handling:** Errors immediately mount the `ErrorPanel` at the top of the stream, locking the phase to `error` and providing explicit `Abort` and `Clear` recovery routines.

---

## 8. VISUAL QUALITY ASSESSMENT

| Area | Rating (1–10) | Notes |
|------|--------------|------|
| **Typography & Spacing** | 9 | Excellent token discipline. Rigid alignment. |
| **Color Palette** | 8 | Sophisticated dark theme. Semantic colors pop nicely. |
| **Micro-Interactions**| 7 | Good use of pulsing and spinning. Lacks robust drag/drop. |
| **Information Density**| 8 | Strikes a great balance between readability and screen economy. |
| **Compared to VS Code**| 8 | Matches standard extensions, slightly cleaner default aesthetics. |
| **Compared to Cursor** | 7 | Cursor has slightly more refined inline-editor ghost text, but Hcode's panel is comparable. |

---

## 9. PROBLEMS & LIMITATIONS

*   **UX Confusion:** The transition from `AgentPanel` diff cards to opening the full `DiffReviewer` can feel abrupt.
*   **Missing Affordances:** No visible keyboard shortcut mappings outside of tooltips. Needs a command palette (e.g., `Cmd+K` / `Cmd+Shift+P`).
*   **Under-designed areas:** The initial empty state of the application lacks onboarding or quick-start prompts in the agent panel.
*   **Over-complex areas:** Managing local component state alongside the global reducer for diff decisions (before accepting/rejecting) requires careful sync.

---

## 10. TECHNICAL DEBT

*   **Inline styles remaining:** A few inline layout styles exist for dynamic constraints (like recursive nesting indents).
*   **Component Size:** `AgentPanel.tsx` is becoming a "God Component", handling streaming, task composition, error boundaries, and timeline logic. It will need sub-component extraction.
*   **Scalability:** As the agent generates massive streams of text or hundreds of diffs, the pure React re-rendering cycle in `App.tsx` (modifying massive arrays) might hit performance bottlenecks without virtualization.

---

## 11. RISK ANALYSIS

**R1: State coupling too tight.**
Because `App.tsx` handles every single event, an excessively fast stream of events (e.g., rapid real-time multi-file streaming) could cause UI thread blocking in the browser view. (Mitigation needed: Debouncing or React concurrent mode features).

**R2: File Path Identity collisions.**
The UI relies heavily on absolute file paths as primary identifiers for patches. If the OS alters paths or daemon sends relative vs absolute inconsistently, patch decisions (`accept`/`reject`) will fail silently.

**R3: Unbounded Memory Growth.**
The `chatMessages` and `streamingContent` states append infinitely. Over a long multi-hour debugging session, the React DOM will become massive.

---

## 12. STRENGTHS

*   **Strict IPC Abstraction.** The UI does not care if the backend is Rust, Python, or Mock. `handleAgentEvent` proves the API contract is airtight.
*   **Visual Professionalism.** Removing emojis and full-screen modals instantly transformed the app from a hobby project to an enterprise-tier tool.
*   **Resiliency UX.** Circuit breakers, daemon health tracking, and graceful error recovery are treated as first-class UI citizens, not afterthoughts. This builds immense user trust.

---

## 13. READINESS VERDICT

**✅ READY**

**Explanation:** Phase 1 achieved its goal. The design system is established and enforced. The layout is stable. The state reducer accurately charts the complex lifecycle of an AI agent (Plan, Execute, Verify). The UI is highly capable of receiving the real IPC integrations of Phase 2 because the mock event architecture proved the React rendering loop is deterministic and solid. It is architecturally sound and visually cohesive.

---

## 14. RECOMMENDED MINOR FIXES (OPTIONAL)

*   **Agent Panel Refactoring:** Split `AgentPanel.tsx` into `TaskComposer`, `Timeline`, and `ArtifactStream` to reduce file size.
*   **Virtualize Streams:** Begin looking at `react-window` for the chat message rendering to future-proof against memory starvation.
*   **Hotkey Overlay:** Add a subtle hints bar or `?` overlay detailing keyboard shortcuts to reduce mouse usage.
