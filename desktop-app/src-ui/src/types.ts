/**
 * Shared TypeScript types for the Hcode Desktop App.
 * Protocol types for IPC between React UI ↔ Tauri main ↔ Python daemon.
 */

// ── File System ────────────────────────────────────────────────────────────

export interface FileEntry {
    name: string;
    path: string;
    isDirectory: boolean;
    children?: FileEntry[];
}

// ── Agent Phase System ────────────────────────────────────────────────────────

export type AgentPhase = 'idle' | 'thinking' | 'planning' | 'executing' | 'verifying' | 'done' | 'error';

export interface PhaseConfig {
    label: string;
    color: string;
    cssVar: string;
    emoji: string;
}

export const PHASE_CONFIGS: Record<AgentPhase, PhaseConfig> = {
    idle: { label: 'Idle', color: 'muted', cssVar: '--hcode-fg-muted', emoji: '○' },
    thinking: { label: 'Thinking', color: 'purple', cssVar: '--phase-thinking', emoji: '🟣' },
    planning: { label: 'Planning', color: 'blue', cssVar: '--phase-planning', emoji: '🔵' },
    executing: { label: 'Executing', color: 'amber', cssVar: '--phase-executing', emoji: '🟡' },
    verifying: { label: 'Verifying', color: 'green', cssVar: '--phase-verifying', emoji: '🟢' },
    done: { label: 'Done', color: 'green', cssVar: '--hcode-success', emoji: '✅' },
    error: { label: 'Error', color: 'red', cssVar: '--hcode-error', emoji: '❌' },
};

// ── IPC Message Types ─────────────────────────────────────────────────────────

export interface PlanPayload { markdown: string }
export interface TaskUpdatePayload { markdown: string }
export interface FilePatchPayload {
    path: string;
    diff: string;
    backup: string;
    originalContent: string;
    newContent: string;
    aiExplanation?: string;
}
export interface VerificationPayload { markdown: string; passed: boolean; testResults?: string }
export interface ErrorPayload { message: string; suggestion: string }
export interface CircuitBreakPayload { reason: string }
export interface LogPayload { line: string; stream: 'stdout' | 'stderr' }

export type HcodeMessage =
    | { type: 'plan'; payload: PlanPayload }
    | { type: 'task_update'; payload: TaskUpdatePayload }
    | { type: 'file_patch'; payload: FilePatchPayload }
    | { type: 'verification'; payload: VerificationPayload }
    | { type: 'error'; payload: ErrorPayload }
    | { type: 'circuit_break'; payload: CircuitBreakPayload }
    | { type: 'log'; payload: LogPayload }
    | { type: 'agent_phase'; phase: AgentPhase }
    | { type: 'ready' }
    | { type: 'done' };

// ── Context Options ───────────────────────────────────────────────────────────

export interface ContextOptions {
    activeFile: boolean;
    selection: boolean;
    folder: boolean;
    gitDiff: boolean;
}

export const DEFAULT_CONTEXT_OPTIONS: ContextOptions = {
    activeFile: true,
    selection: true,
    folder: false,
    gitDiff: false,
};

// ── Task History ──────────────────────────────────────────────────────────────

export interface TaskEntry {
    id: string;
    timestamp: string;
    task: string;
    mode: 'planning' | 'fast';
    phasesReached: AgentPhase[];
    modifiedFiles: string[];
    outcome: 'success' | 'error' | 'aborted';
}

// ── Chat Messages ─────────────────────────────────────────────────────────────

export type ChatMessageType = 'user' | 'agent_thought' | 'agent_phase' | 'agent_output' | 'system';

export interface ChatMessage {
    id: string;
    type: ChatMessageType;
    phase?: AgentPhase;
    content: string;
    timestamp: string;
    isStreaming?: boolean;
}

// ── Daemon Status ─────────────────────────────────────────────────────────────

export type DaemonStatus = 'stopped' | 'starting' | 'running' | 'error' | 'restarting';

export interface DaemonInfo {
    status: DaemonStatus;
    uptime?: number;
    pid?: number;
    version?: string;
}

// ── App State ────────────────────────────────────────────────────────────────

export interface AppState {
    phase: AgentPhase;
    daemonStatus: DaemonStatus;
    workDir: string;
    fileTree: FileEntry[];
    openFilePath: string | null;
    openFileContent: string;
    chatMessages: ChatMessage[];
    planMarkdown: string;
    patches: FilePatchPayload[];
    verificationResult: VerificationPayload | null;
    taskHistory: TaskEntry[];
    logs: LogPayload[];
    error: ErrorPayload | null;
    activeTab: 'chat' | 'plan' | 'tasks' | 'diff' | 'verify' | 'settings';

    // Phase 2 additions
    currentTask: string | null;
    appliedPatches: string[];
    streamingContent: string;
    circuitBreakActive: boolean;
    lastError: string | null;
}

export const INITIAL_STATE: AppState = {
    phase: 'idle',
    daemonStatus: 'stopped',
    workDir: '',
    fileTree: [],
    openFilePath: null,
    openFileContent: '',
    chatMessages: [],
    planMarkdown: '',
    patches: [],
    verificationResult: null,
    taskHistory: [],
    logs: [],
    error: null,
    activeTab: 'chat',

    // Phase 2 additions
    currentTask: null,
    appliedPatches: [],
    streamingContent: '',
    circuitBreakActive: false,
    lastError: null,
};
