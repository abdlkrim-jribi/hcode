# Hcode Desktop App

**Standalone Windows desktop application** for the Hcode AI Coding Agent.

Features a 3-column IDE layout (Explorer → Editor → Agent) with full Plan → Approve → Execute → Verify workflow.

## Stack

- **Frontend**: React 18 + TypeScript + Monaco Editor
- **Backend**: Tauri v2 (Rust)
- **AI Engine**: Hcode Python daemon (JSON-RPC over stdin/stdout)
- **Security**: Windows Credential Manager for API keys, scoped FS access

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18
- [Rust](https://rustup.rs/) (latest stable)
- [Python](https://python.org/) ≥ 3.11

### Development

```powershell
# Run the dev script (starts mock daemon + Tauri dev server)
.\scripts\dev.ps1
```

### Manual Setup

```powershell
# Install frontend deps
cd src-ui
npm install

# Start dev server
cd ../src-tauri
cargo tauri dev
```

### Build Production

```powershell
# Build Python daemon
pip install pyinstaller
pyinstaller --onefile hcode-daemon/run_daemon.py -n hcode-daemon

# Build Tauri app
cd src-ui && npm run build
cd ../src-tauri && cargo tauri build
```

## Project Structure

```
desktop-app/
├── src-ui/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/   # 11 React components (ported from VS Code extension)
│   │   ├── ipc/          # Tauri invoke/event bridge
│   │   ├── styles/       # Design tokens + global CSS
│   │   ├── App.tsx       # 3-column layout shell
│   │   └── types.ts      # Shared TypeScript types
│   └── package.json
├── src-tauri/            # Tauri Rust backend
│   ├── src/
│   │   ├── main.rs       # IPC commands + app setup
│   │   └── daemon.rs     # Python daemon supervisor
│   ├── tauri.conf.json
│   └── Cargo.toml
├── hcode-daemon/         # Python daemon wrapper
│   └── run_daemon.py     # JSON-RPC entry point
├── ci/
│   └── build-windows.yml # GitHub Actions workflow
└── scripts/
    └── dev.ps1           # Development launcher
```

## Architecture

```
React UI  ←──Tauri invoke──→  Rust Main  ←──stdin/stdout JSON-RPC──→  Python Daemon
(WebView2)                    (Process)                                (HcodeAgent)
```
