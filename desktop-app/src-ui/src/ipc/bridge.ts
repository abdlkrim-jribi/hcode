/**
 * IPC Bridge — abstracts Tauri invoke/event APIs for the React UI.
 * 
 * When running outside Tauri (plain browser for UI testing), all calls
 * return mock data so the UI can be previewed standalone.
 */
import type { HcodeMessage, FileEntry, DaemonInfo } from '../types';
import { createMockEventStream, playMockStream, agentEventToHcodeMessage } from './mock-events';

// ── Tauri detection ──────────────────────────────────────────────────────────

const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

// Lazy-loaded Tauri APIs
let tauriInvoke: ((cmd: string, args?: Record<string, unknown>) => Promise<unknown>) | null = null;
let tauriListen: ((event: string, handler: (event: { payload: unknown }) => void) => Promise<() => void>) | null = null;

async function getInvoke() {
    if (!isTauri) return mockInvoke;
    if (!tauriInvoke) {
        const { invoke } = await import('@tauri-apps/api/core');
        tauriInvoke = invoke;
    }
    return tauriInvoke;
}

async function getListen() {
    if (!isTauri) return mockListen;
    if (!tauriListen) {
        const { listen } = await import('@tauri-apps/api/event');
        tauriListen = listen as any;
    }
    return tauriListen!;
}

if (!isTauri) {
    console.warn('[IPC] Running in browser mode — using mock responses');
}

// ── Mock responses for browser-mode testing ──────────────────────────────────

const MOCK_FILE_TREE: FileEntry[] = [
    {
        name: 'src', path: '/project/src', isDirectory: true, children: [
            { name: 'main.py', path: '/project/src/main.py', isDirectory: false },
            { name: 'agent.py', path: '/project/src/agent.py', isDirectory: false },
            { name: 'utils.py', path: '/project/src/utils.py', isDirectory: false },
            {
                name: 'core', path: '/project/src/core', isDirectory: true, children: [
                    { name: 'loop.py', path: '/project/src/core/loop.py', isDirectory: false },
                    { name: 'context.py', path: '/project/src/core/context.py', isDirectory: false },
                ]
            },
        ]
    },
    {
        name: 'tests', path: '/project/tests', isDirectory: true, children: [
            { name: 'test_agent.py', path: '/project/tests/test_agent.py', isDirectory: false },
        ]
    },
    { name: 'README.md', path: '/project/README.md', isDirectory: false },
    { name: 'requirements.txt', path: '/project/requirements.txt', isDirectory: false },
    { name: 'pyproject.toml', path: '/project/pyproject.toml', isDirectory: false },
];

const MOCK_FILE_CONTENT = `"""
Hcode Agent — AI Coding Assistant
"""

import asyncio
from typing import Optional

class HcodeAgent:
    """Core agent that orchestrates planning, execution, and verification."""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.phase = "idle"
        self.task_history = []
    
    async def execute_task(self, task: str, mode: str = "planning") -> dict:
        """Execute a coding task through the PEV cycle."""
        self.phase = "thinking"
        plan = await self._generate_plan(task)
        
        self.phase = "executing"
        result = await self._execute_plan(plan)
        
        self.phase = "verifying"
        verification = await self._verify_result(result)
        
        self.phase = "done"
        return {"plan": plan, "result": result, "verification": verification}
    
    async def _generate_plan(self, task: str) -> str:
        return f"Plan for: {task}"
    
    async def _execute_plan(self, plan: str) -> str:
        return f"Executed: {plan}"
    
    async def _verify_result(self, result: str) -> bool:
        return True
`;

// Track mock daemon-message listeners so we can fire events from mockInvoke
let mockDaemonListeners: Array<(event: { payload: unknown }) => void> = [];
let mockCancelStream: (() => void) | null = null;

async function mockInvoke(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
    await new Promise(r => setTimeout(r, 100));

    switch (cmd) {
        case 'start_daemon':
        case 'daemon_health':
            return { status: 'running', uptime: 42, pid: 12345, version: '0.1.0' } satisfies DaemonInfo;
        case 'stop_daemon':
            return undefined;
        case 'open_folder_dialog':
            return '/project';
        case 'list_directory':
            return MOCK_FILE_TREE;
        case 'read_file':
            return MOCK_FILE_CONTENT;
        case 'write_file':
            return undefined;
        case 'save_api_key':
            return undefined;
        case 'get_api_key':
            return null;
        case 'run_task': {
            // Phase 2: Fire mock event stream so the UI demonstrates real-time behavior
            const task = (args?.task as string) || 'Demo task';
            const events = createMockEventStream(task);
            if (mockCancelStream) mockCancelStream();
            mockCancelStream = playMockStream(events, (event) => {
                const hcodeMsg = agentEventToHcodeMessage(event);
                if (hcodeMsg) {
                    mockDaemonListeners.forEach(fn => fn({ payload: hcodeMsg }));
                }
            }, 800);
            return undefined;
        }
        case 'abort_task':
            if (mockCancelStream) { mockCancelStream(); mockCancelStream = null; }
            return undefined;
        case 'approve_plan':
        case 'reject_plan':
        case 'accept_patch':
        case 'reject_patch':
        case 'rollback_all':
            return undefined;
        default:
            console.warn(`[Mock IPC] Unknown command: ${cmd}`);
            return undefined;
    }
}

async function mockListen(event: string, handler: (event: { payload: unknown }) => void): Promise<() => void> {
    if (event === 'daemon-message') {
        mockDaemonListeners.push(handler);
        return () => {
            mockDaemonListeners = mockDaemonListeners.filter(fn => fn !== handler);
        };
    }
    return () => { };
}

// ── Daemon Commands ───────────────────────────────────────────────────────────

export async function startDaemon(): Promise<DaemonInfo> {
    const invoke = await getInvoke();
    return invoke('start_daemon') as Promise<DaemonInfo>;
}

export async function stopDaemon(): Promise<void> {
    const invoke = await getInvoke();
    return invoke('stop_daemon') as Promise<void>;
}

export async function getDaemonHealth(): Promise<DaemonInfo> {
    const invoke = await getInvoke();
    return invoke('daemon_health') as Promise<DaemonInfo>;
}

// ── Task Commands ─────────────────────────────────────────────────────────────

export async function runTask(task: string, mode: 'planning' | 'fast', autonomous: boolean): Promise<void> {
    const invoke = await getInvoke();
    return invoke('run_task', { task, mode, autonomous }) as Promise<void>;
}

export async function abortTask(): Promise<void> {
    const invoke = await getInvoke();
    return invoke('abort_task') as Promise<void>;
}

export async function approvePlan(): Promise<void> {
    const invoke = await getInvoke();
    return invoke('approve_plan') as Promise<void>;
}

export async function rejectPlan(feedback: string): Promise<void> {
    const invoke = await getInvoke();
    return invoke('reject_plan', { feedback }) as Promise<void>;
}

export async function acceptPatch(path: string): Promise<void> {
    const invoke = await getInvoke();
    return invoke('accept_patch', { path }) as Promise<void>;
}

export async function rejectPatch(path: string): Promise<void> {
    const invoke = await getInvoke();
    return invoke('reject_patch', { path }) as Promise<void>;
}

export async function rollbackAll(): Promise<void> {
    const invoke = await getInvoke();
    return invoke('rollback_all') as Promise<void>;
}

// ── File System Commands ──────────────────────────────────────────────────────

export async function openFolder(): Promise<string | null> {
    const invoke = await getInvoke();
    return invoke('open_folder_dialog') as Promise<string | null>;
}

export async function listDirectory(path: string): Promise<FileEntry[]> {
    const invoke = await getInvoke();
    return invoke('list_directory', { path }) as Promise<FileEntry[]>;
}

export async function readFile(path: string): Promise<string> {
    const invoke = await getInvoke();
    return invoke('read_file', { path }) as Promise<string>;
}

export async function writeFile(path: string, content: string): Promise<void> {
    const invoke = await getInvoke();
    return invoke('write_file', { path, content }) as Promise<void>;
}

// ── Secret Storage ────────────────────────────────────────────────────────────

export async function saveApiKey(provider: string, key: string): Promise<void> {
    const invoke = await getInvoke();
    return invoke('save_api_key', { provider, key }) as Promise<void>;
}

export async function getApiKey(provider: string): Promise<string | null> {
    const invoke = await getInvoke();
    return invoke('get_api_key', { provider }) as Promise<string | null>;
}

// ── Event Listeners ───────────────────────────────────────────────────────────

export async function onDaemonMessage(callback: (msg: HcodeMessage) => void): Promise<() => void> {
    const listen = await getListen();
    return listen('daemon-message', (event) => {
        callback(event.payload as HcodeMessage);
    });
}

export async function onDaemonStatus(callback: (info: DaemonInfo) => void): Promise<() => void> {
    const listen = await getListen();
    return listen('daemon-status', (event) => {
        callback(event.payload as DaemonInfo);
    });
}
