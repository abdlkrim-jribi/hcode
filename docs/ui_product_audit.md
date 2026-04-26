# UI / Product Audit

## Desktop Application (Tauri v2 + React)

### What Feels Professional

| Area | Evidence | File |
|:---|:---|:---|
| **3-column resizable layout** | Explorer / Editor / Agent Panel with pointer-drag and keyboard shortcuts | `App.tsx` |
| **Monaco editor** | Full VS Code-grade code editing with syntax highlighting | `MonacoEditor.tsx` |
| **Design token system** | Unified `tokens.css` with hsl(228) palette, 4px grid, consistent radii | `tokens.css` |
| **Status bar** | Phase dot indicators, daemon status, working directory | `StatusBar.tsx` |
| **Keyboard shortcuts** | Ctrl+B (explorer), Ctrl+J (agent), Ctrl+1/2/3 (focus) | `App.tsx` |
| **IPC abstraction** | `bridge.ts` detects Tauri vs browser, enables standalone UI dev | `bridge.ts` |

### What Feels Rough

| Area | Issue | Severity |
|:---|:---|:---|
| **No streaming display** | Agent responses appear after full completion. User sees only phase dots. | HIGH |
| **Settings overlay** | Full-screen modal instead of side panel. Blocks workflow. | MEDIUM |
| **No command palette** | Missing Ctrl+Shift+P equivalent. Discoverability gap. | MEDIUM |
| **Abrupt panel transitions** | No animations when switching to DiffReviewer or toggling panels. | LOW |
| **Agent panel scroll** | All cards share single scroll. Should scroll independently from stream header. | MEDIUM |
| **Raw emoji in errors** | `❌` characters in system error messages. Inconsistent with icon system. | LOW |

### What Is Missing for Editor-Grade UX

| Feature | Every Professional Editor Has | Hcode Status |
|:---|:---|:---|
| Command palette | Ctrl+Shift+P fuzzy search | ❌ Missing |
| Breadcrumbs | File path + symbol navigation | ❌ Missing |
| Inline diff mode | Side-by-side AND inline toggle | ❌ Only side-by-side |
| Minimap | Code overview scrollbar | Disabled |
| Tabs | Multiple open files | ⚠️ Single file only |
| Find/replace | Ctrl+F in editor | Handled by Monaco natively |
| Token streaming | Live response display | ❌ Missing |
| Undo/redo per file | Multi-level file undo | Via Monaco |
| Git decorations | Line-level git blame/diff markers | ❌ Missing |

### Backend Status (Critical)

| Component | Status | Detail |
|:---|:---|:---|
| **DaemonSupervisor.send()** | ❌ STUB | `eprintln!` only — no data reaches Python daemon |
| **spawn_output_reader()** | ❌ STUB | Hardcoded 5s loop emitting fake status |
| **IPC bridge** | ✅ WORKS | But calls hit stubs in Rust backend |

**Bottom line**: The desktop app is a **beautifully designed shell with a non-functional backend bridge**. The UI compiles and looks professional, but cannot actually run tasks because the daemon communication is a stub.

---

## VS Code Extension

### What Feels Professional

| Area | Evidence | File |
|:---|:---|:---|
| **Consistent tokens** | Same `tokens.css` design system with VS Code variable fallbacks | `tokens.css` |
| **TaskComposer** | Clean input with Plan/Fast mode selector | `TaskComposer.tsx` |
| **Git status popover** | Non-intrusive commit dialog | `GitPanel.tsx` |
| **Sidebar providers** | Registered for `hcode.sidebar` and `hcode.history` views | `extension.ts` |
| **Refactor selection** | `hcode.refactorSelection` extracts selected code and opens task panel | `extension.ts` |

### What Feels Rough

| Area | Issue | Severity |
|:---|:---|:---|
| **Pre-block diffs** | Uses `<pre>` for diff display instead of Monaco DiffEditor | HIGH |
| **No loading indicators** | No progress bar or streaming during LLM calls | HIGH |
| **Single scrollable view** | No panel-level navigation | MEDIUM |
| **No keyboard shortcuts** | No extension-specific keybindings registered | MEDIUM |

### What Is Missing

| Feature | Status |
|:---|:---|
| Inline code actions | ❌ No CodeLens or diagnostic actions |
| Status bar item | ❌ No agent status in VS Code status bar |
| Context menu entries | ❌ No right-click "Ask Hcode" |
| Workspace trust | ❌ No trust verification |
| Tree view for tasks | ❌ Task list is flat |

---

## Duplication Between Surfaces

| Element | Desktop App | VS Code Extension | Issue |
|:---|:---|:---|:---|
| `tokens.css` | `desktop-app/src-ui/src/styles/tokens.css` | `vscode-extension/src/webview/styles/tokens.css` | **Separate copies** — no shared build |
| `global.css` | `desktop-app/src-ui/src/styles/global.css` | `vscode-extension/src/webview/styles/global.css` | **Separate copies** |
| DiffReviewer | Monaco-powered component | `<pre>` block | **Inconsistent capability** |
| Agent message types | `types.ts` (152L) | Inline in `app.tsx` | **Separate type definitions** |

---

## Inconsistencies

| Issue | Location | Impact |
|:---|:---|:---|
| `AgentPhase` lacks `waiting_approval` | `desktop-app/src-ui/src/types.ts` | StatusBar phase check was patched to remove it |
| Agent panel cards use `msg.phase` | `app.tsx` line ~352 | `msg.phase` is possibly undefined — patched with `??` fallback |
| Error messages use raw emoji | Multiple components | Design system uses `icons.py` with ASCII fallback, but UI components use hardcoded `❌` |
