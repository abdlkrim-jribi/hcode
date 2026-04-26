/**
 * Shared TypeScript types for the webview ↔ extension host protocol.
 */

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
    | { type: 'git_info'; branch: string; staging: string }
    | { type: 'key_saved'; provider: string }
    | { type: 'git_commit_result'; success: boolean }
    | { type: 'agent_phase'; phase: AgentPhase }
    | { type: 'ready' }
    | { type: 'done' };

// ── Agent Phase System ────────────────────────────────────────────────────────

/** Granular agent phase driving the visual timeline */
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
