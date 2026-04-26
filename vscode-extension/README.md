# Hcode VS Code Extension

> **AI-powered coding agent inside VS Code** — Plan, Execute, Verify with full human oversight.

[![VS Code](https://img.shields.io/badge/VS%20Code-%5E1.85.0-blue)](https://code.visualstudio.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)

---

## Features

| Feature | Description |
|---|---|
| **Run Task** | Submit a natural-language task → Hcode plans, executes, and verifies |
| **Chat** | Interactive session with persistent context |
| **Plan Viewer** | Review `implementation_plan.md` before any code is written |
| **Diff Reviewer** | Accept/Reject each file change with Monaco diff editor |
| **Live Checklist** | Real-time `task.md` progress updates |
| **Verification Panel** | `walkthrough.md` + rollback button |
| **Settings** | Provider selector, secure API key storage, autonomous mode toggle |
| **Git Integration** | Branch name, staging preview, auto-commit |

---

## Safety Defaults

> ⚠️ **Interactive mode is ON by default.** Hcode will never write files without your explicit approval.

- Autonomous mode is **disabled** by default — enable it in Settings with a clear warning banner
- All file modifications are backed up to `.hcode/backups/` before changes
- Rollback is available at every stage
- API keys are stored in VS Code's encrypted **SecretStorage** (OS keychain) — never in plain text
- Circuit breakers surface infinite-loop detection in the UI

---

## Installation

### From Source (Development)

```bash
# 1. Clone the repo
git clone https://github.com/Mohamed-jarboui/hcode.git
cd hcode/vscode-extension

# 2. Install dependencies
npm install

# 3. Build
npm run build

# 4. Launch in VS Code
# Press F5 in VS Code to open the Extension Development Host
```

### Prerequisites

- **Node.js** 18+
- **VS Code** 1.85+
- **Hcode CLI** installed and on PATH:
  ```bash
  pip install hcode
  # or from source:
  pip install -e /path/to/hcode
  ```

---

## Usage

### Run Task

1. Open Command Palette (`Ctrl+Shift+P`)
2. Type `Hcode: Run Task`
3. Enter your task in natural language, e.g.:
   > *"Add input validation to the login form"*
4. Review the **Implementation Plan** → click **Approve**
5. Watch the live checklist as Hcode executes
6. Review file diffs → Accept/Reject each file
7. See the **Verification Panel** with `walkthrough.md`

### Chat

1. `Ctrl+Shift+P` → `Hcode: Open Chat`
2. Interactive session with full context memory

### Settings

1. `Ctrl+Shift+P` → `Hcode: Settings`
2. Configure:
   - **Provider**: Auto / OpenAI / Anthropic / Cerebras
   - **API Keys**: Stored securely in OS keychain
   - **Autonomous Mode**: Off by default

---

## Architecture

```
vscode-extension/
├── src/
│   ├── extension.ts              # Activation, command registration
│   ├── webviewPanelManager.ts    # Panel lifecycle + message routing
│   ├── backend/
│   │   ├── hcodeBridge.ts        # IPC: JSON line-protocol to Hcode CLI
│   │   ├── secretStorage.ts      # Secure API key storage
│   │   └── gitIntegration.ts     # Branch, staging, commit
│   └── webview/                  # React app (built with Vite)
│       ├── app.tsx               # Root + state machine
│       ├── types.ts              # Shared message types
│       ├── components/
│       │   ├── TaskComposer.tsx
│       │   ├── PlanViewer.tsx
│       │   ├── TaskChecklist.tsx
│       │   ├── DiffReviewer.tsx  # Monaco diff editor
│       │   ├── LogConsole.tsx
│       │   ├── VerificationPanel.tsx
│       │   ├── SettingsPanel.tsx
│       │   └── GitPanel.tsx
│       └── styles/
│           ├── tokens.css        # Design tokens (from Hcode theme)
│           └── global.css        # Component styles
├── test/
│   ├── __mocks__/vscode.ts       # VS Code API mock for Jest
│   ├── unit/
│   │   ├── extension.test.ts
│   │   └── hcodeBridge.test.ts
│   └── e2e/
│       ├── runTests.js
│       └── suite/
│           ├── index.ts
│           └── smoke.test.ts
└── webview_build/                # Built webview bundle (generated)
```

### IPC Protocol

Messages between the extension host and Hcode CLI are **newline-delimited JSON**:

```jsonc
// Hcode → Extension
{ "type": "plan",         "payload": { "markdown": "# Plan..." } }
{ "type": "task_update",  "payload": { "markdown": "- [x] Step 1" } }
{ "type": "file_patch",   "payload": { "path": "src/foo.ts", "diff": "...", "originalContent": "...", "newContent": "..." } }
{ "type": "verification", "payload": { "markdown": "# Walkthrough...", "passed": true } }
{ "type": "error",        "payload": { "message": "...", "suggestion": "..." } }
{ "type": "circuit_break","payload": { "reason": "Infinite loop detected" } }

// Extension → Hcode (stdin)
{ "action": "approve" }
{ "action": "reject", "comment": "Please also add tests" }
{ "action": "rollback" }
{ "action": "accept_file", "path": "src/foo.ts" }
{ "action": "reject_file", "path": "src/bar.ts" }
```

---

## Development

```bash
# Compile TypeScript (extension host)
npm run compile

# Watch mode
npm run watch

# Build webview (React + Vite)
npm run build:webview

# Full build
npm run build

# Unit tests
npm test

# E2E tests (requires VS Code)
npm run test:e2e

# Package as .vsix
npm run package
```

---

## Publishing

```json
// In package.json — update before publishing:
{
  "publisher": "your-publisher-id",
  "repository": {
    "type": "git",
    "url": "https://github.com/Mohamed-jarboui/hcode"
  }
}
```

```bash
# Login to VS Code Marketplace
npx @vscode/vsce login your-publisher-id

# Publish
npx @vscode/vsce publish
```

---

## License

MIT © Hcode Contributors
