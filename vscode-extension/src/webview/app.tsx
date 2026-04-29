import React, { useEffect, useReducer, useCallback, useMemo, useRef } from 'react';
import { marked } from 'marked';
import TaskComposer from './components/TaskComposer';
import LogConsole from './components/LogConsole';
import SettingsPanel from './components/SettingsPanel';
import GitPanel from './components/GitPanel';
import FileExplorer from './components/FileExplorer';
import TaskHistory from './components/TaskHistory';
import {
    HcodeMessage,
    AgentPhase, ContextOptions, TaskEntry, ChatMessage,
} from './types';

// ── VS Code API ───────────────────────────────────────────────────────────────
declare function acquireVsCodeApi(): {
    postMessage(msg: object): void;
    getState(): any;
    setState(state: any): void;
};
const vscode = acquireVsCodeApi();

const APPROVAL_PATTERNS = [
    /\[A\]ccept/i,
    /Write this file\?/i,
    /Approve this plan\?/i,
    /Do you want to proceed\?/i,
    /\[S\]ession-Accept/i,
    /Apply (these|this) change/i,
    /Execute\?/i,
];
function isApprovalPrompt(line: string): boolean {
    return APPROVAL_PATTERNS.some(p => p.test(line));
}

let _id = 0;
const uid = () => `msg-${Date.now()}-${_id++}`;
const now = () => new Date().toLocaleTimeString();

// ── State ─────────────────────────────────────────────────────────────────────
type RunPhase = 'idle' | 'running' | 'thinking' | 'waiting_approval' | 'done' | 'error';

interface AppState {
    runPhase: RunPhase;
    agentPhase: AgentPhase;
    logs: { time: string; line: string; stream: 'stdout' | 'stderr' }[];
    thoughts: string;
    chatMessages: ChatMessage[];
    taskHistory: TaskEntry[];
    currentTaskId: string | null;
    currentPhasesReached: AgentPhase[];
    currentModifiedFiles: string[];
    currentMode: 'planning' | 'fast';
    errorMessage: string;
    errorSuggestion: string;
    promptQuestion: string;
    gitBranch: string;
    gitStaging: string;
    workDir: string;
    fileTree: any[];
    replayTask: string;
}

const initialState: AppState = {
    runPhase: 'idle',
    agentPhase: 'idle',
    logs: [],
    thoughts: '',
    chatMessages: [],
    taskHistory: [],
    currentTaskId: null,
    currentPhasesReached: [],
    currentModifiedFiles: [],
    currentMode: 'planning',
    errorMessage: '',
    errorSuggestion: '',
    promptQuestion: '',
    gitBranch: '',
    gitStaging: '',
    workDir: '',
    fileTree: [],
    replayTask: '',
};

type Action =
    | { type: 'START_TASK'; task: string; mode: 'planning' | 'fast' }
    | { type: 'SET_AGENT_PHASE'; phase: AgentPhase }
    | { type: 'ADD_LOG'; line: string; stream: 'stdout' | 'stderr' }
    | { type: 'ADD_THOUGHT'; chunk: string }
    | { type: 'ADD_CHAT'; msg: ChatMessage }
    | { type: 'SET_ERROR'; message: string; suggestion: string }
    | { type: 'SET_PROMPT'; question: string }
    | { type: 'CLEAR_PROMPT' }
    | { type: 'SET_GIT'; branch: string; staging: string }
    | { type: 'SET_FOLDER'; path: string; tree: any[] }
    | { type: 'ADD_MODIFIED_FILE'; path: string }
    | { type: 'TASK_DONE'; outcome: 'success' | 'error' | 'aborted' }
    | { type: 'REPLAY_TASK'; task: string; mode: 'planning' | 'fast' }
    | { type: 'RESET' };

function reducer(state: AppState, action: Action): AppState {
    switch (action.type) {
        case 'START_TASK':
            return {
                ...state,
                runPhase: 'thinking',
                agentPhase: 'thinking',
                thoughts: '',
                chatMessages: [
                    ...state.chatMessages,
                    { id: uid(), type: 'user', content: action.task, timestamp: now() },
                ],
                currentTaskId: uid(),
                currentPhasesReached: ['thinking'],
                currentModifiedFiles: [],
                currentMode: action.mode,
                errorMessage: '',
                errorSuggestion: '',
                promptQuestion: '',
            };
        case 'SET_AGENT_PHASE': {
            const phasesReached = state.currentPhasesReached.includes(action.phase)
                ? state.currentPhasesReached
                : [...state.currentPhasesReached, action.phase];
            return {
                ...state,
                agentPhase: action.phase,
                runPhase: action.phase === 'done' ? 'done' : action.phase === 'error' ? 'error' : 'running',
                currentPhasesReached: phasesReached,
                chatMessages: [
                    ...state.chatMessages,
                    { id: uid(), type: 'agent_phase', phase: action.phase, content: `Phase: ${action.phase}`, timestamp: now() },
                ],
            };
        }
        case 'ADD_LOG': {
            const time = new Date().toLocaleTimeString();
            return { ...state, logs: [...state.logs.slice(-500), { time, line: action.line, stream: action.stream }] };
        }
        case 'ADD_THOUGHT':
            return { ...state, thoughts: state.thoughts + action.chunk, runPhase: 'thinking' };
        case 'ADD_CHAT':
            return { ...state, chatMessages: [...state.chatMessages, action.msg] };
        case 'SET_ERROR':
            return {
                ...state,
                errorMessage: action.message,
                errorSuggestion: action.suggestion,
                runPhase: 'error',
                agentPhase: 'error',
            };
        case 'SET_PROMPT':
            return { ...state, promptQuestion: action.question, runPhase: 'waiting_approval' };
        case 'CLEAR_PROMPT':
            return { ...state, promptQuestion: '', runPhase: 'running' };
        case 'SET_GIT':
            return { ...state, gitBranch: action.branch, gitStaging: action.staging };
        case 'SET_FOLDER':
            return { ...state, workDir: action.path, fileTree: action.tree };
        case 'ADD_MODIFIED_FILE':
            return {
                ...state,
                currentModifiedFiles: state.currentModifiedFiles.includes(action.path)
                    ? state.currentModifiedFiles
                    : [...state.currentModifiedFiles, action.path],
            };
        case 'TASK_DONE': {
            if (!state.currentTaskId) return state;
            const entry: TaskEntry = {
                id: state.currentTaskId,
                timestamp: new Date().toISOString(),
                task: state.chatMessages.filter(m => m.type === 'user').slice(-1)[0]?.content ?? '',
                mode: state.currentMode,
                phasesReached: state.currentPhasesReached,
                modifiedFiles: state.currentModifiedFiles,
                outcome: action.outcome,
            };
            return {
                ...state,
                runPhase: 'done',
                agentPhase: action.outcome === 'success' ? 'done' : 'error',
                taskHistory: [entry, ...state.taskHistory],
                currentTaskId: null,
            };
        }
        case 'REPLAY_TASK':
            return { ...state, replayTask: action.task };
        case 'RESET':
            return { ...initialState, workDir: state.workDir, fileTree: state.fileTree, taskHistory: state.taskHistory };
        default:
            return state;
    }
}

// ── App ───────────────────────────────────────────────────────────────────────
interface AppProps { mode: 'run' | 'chat' | 'settings' | 'sidebar' | 'history'; }

export default function App({ mode }: AppProps) {
    const [state, dispatch] = useReducer(reducer, initialState);
    const post = useCallback((msg: object) => vscode.postMessage(msg), []);
    const endOfStreamRef = useRef<HTMLDivElement>(null);

    // ── Message handler ────────────────────────────────────────────────────
    useEffect(() => {
        const handler = (event: MessageEvent) => {
            const msg: HcodeMessage | any = event.data;
            switch (msg.type) {
                case 'thought':
                    dispatch({ type: 'ADD_THOUGHT', chunk: msg.payload.chunk });
                    break;
                case 'agent_phase':
                    dispatch({ type: 'SET_AGENT_PHASE', phase: msg.phase as AgentPhase });
                    break;
                case 'log': {
                    dispatch({ type: 'ADD_LOG', line: msg.payload.line, stream: msg.payload.stream });
                    if (isApprovalPrompt(msg.payload.line)) {
                        dispatch({ type: 'SET_PROMPT', question: msg.payload.line });
                    }
                    break;
                }
                case 'file_patch':
                    dispatch({ type: 'ADD_MODIFIED_FILE', path: msg.payload.path });
                    break;
                case 'error':
                    dispatch({ type: 'SET_ERROR', message: msg.payload.message, suggestion: msg.payload.suggestion });
                    dispatch({ type: 'TASK_DONE', outcome: 'error' });
                    break;
                case 'git_info':
                    dispatch({ type: 'SET_GIT', branch: msg.branch, staging: msg.staging });
                    break;
                case 'folder_selected':
                    dispatch({ type: 'SET_FOLDER', path: msg.path, tree: msg.tree });
                    post({ type: 'set_workdir', path: msg.path });
                    break;
                case 'done':
                    dispatch({ type: 'CLEAR_PROMPT' });
                    dispatch({ type: 'TASK_DONE', outcome: 'success' });
                    dispatch({
                        type: 'ADD_CHAT',
                        msg: { id: uid(), type: 'system', content: '✅ Task completed successfully.', timestamp: now() },
                    });
                    break;
            }
        };
        window.addEventListener('message', handler);
        return () => window.removeEventListener('message', handler);
    }, []);

    // Scroll stream to bottom
    useEffect(() => {
        endOfStreamRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [state.chatMessages, state.thoughts, state.logs]);

    const handleRunTask = (task: string, context: ContextOptions) => {
        const rawMode = task.startsWith('/fast') ? 'fast' : 'planning';
        dispatch({ type: 'START_TASK', task, mode: rawMode });
        post({ type: 'run_task', task, context });
    };

    const handleApprove = () => { dispatch({ type: 'CLEAR_PROMPT' }); post({ type: 'approve_plan' }); };
    const handleReject = () => { dispatch({ type: 'CLEAR_PROMPT' }); post({ type: 'reject_plan', comment: '' }); };
    const handleKill = () => { post({ type: 'kill_process' }); dispatch({ type: 'TASK_DONE', outcome: 'aborted' }); };

    const renderedThoughts = useMemo(() => {
        if (!state.thoughts) return null;
        return marked.parse(state.thoughts) as string;
    }, [state.thoughts]);

    const isRunning = state.runPhase === 'running' || state.runPhase === 'waiting_approval' || state.runPhase === 'thinking';
    const currentMode = (window as any).hcodeMode || mode;

    // ── Mode-specific renders ──────────────────────────────────────────────
    if (currentMode === 'settings') return <SettingsPanel post={post} />;

    if (currentMode === 'sidebar') {
        return (
            <div className="hcode-sidebar-view" style={{ padding: 'var(--space-3)' }}>
                <FileExplorer
                    workDir={state.workDir}
                    fileTree={state.fileTree}
                    onSelectFolder={() => post({ type: 'pick_folder' })}
                    onBrowsePath={(path) => post({ type: 'list_files', path })}
                    onOpenFile={(path) => post({ type: 'open_file', path })}
                />
                <div style={{ marginTop: 'var(--space-4)' }}>
                    <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--fg-secondary)', marginBottom: 'var(--space-2)' }}>ACTIVE TASKS</div>
                    <div style={{ color: 'var(--fg-tertiary)', fontSize: 'var(--text-sm)', background: 'var(--surface-1)', padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)' }}>
                        {state.runPhase !== 'idle' ? `● ${state.agentPhase}…` : 'No active tasks.'}
                    </div>
                </div>
            </div>
        );
    }

    if (currentMode === 'history') {
        return (
            <div className="hcode-sidebar-view" style={{ padding: 'var(--space-3)' }}>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--fg-secondary)', marginBottom: 'var(--space-3)' }}>TASK HISTORY</div>
                <TaskHistory
                    history={state.taskHistory}
                    onReplay={(task, replayMode) => dispatch({ type: 'REPLAY_TASK', task, mode: replayMode })}
                />
            </div>
        );
    }

    const getPhaseClass = (p: AgentPhase) => {
        if (p === 'thinking') return 'is-thinking';
        if (p === 'planning') return 'is-planning';
        if (p === 'executing') return 'is-executing';
        if (p === 'verifying') return 'is-verifying';
        if (p === 'done') return 'is-done';
        if (p === 'error') return 'is-error';
        return '';
    };

    // ── Unified Task Stream UI ─────────────────────────────────────────────
    return (
        <div className="hcode-app">
            {/* Header */}
            <header className="hcode-header">
                <span className="hcode-logo">HCODE</span>

                {/* Phase Dots Indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flex: 1, justifyContent: 'center' }}>
                    <span className={`hcode-phase-dot ${getPhaseClass(state.agentPhase)}`} />
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-secondary)', textTransform: 'capitalize' }}>
                        {state.agentPhase.replace('_', ' ')}
                    </span>
                </div>

                {isRunning && (
                    <button className="hcode-btn hcode-btn--ghost hcode-btn--small" onClick={handleKill}>Stop</button>
                )}
                <GitPanel branch={state.gitBranch} staging={state.gitStaging} post={post} />
            </header>

            {/* Task Stream */}
            <main className="hcode-main">
                <div className="hcode-task-stream">
                    {state.chatMessages.map(msg => {
                        if (msg.type === 'user') {
                            return (
                                <div key={msg.id} className="hcode-stream-entry hcode-stream-user">
                                    <span className="hcode-stream-user-prefix">▹ You:</span>
                                    {msg.content}
                                </div>
                            );
                        }
                        if (msg.type === 'agent_phase' && msg.phase) {
                            return (
                                <div key={msg.id} className="hcode-stream-phase-divider">
                                    {msg.phase.charAt(0).toUpperCase() + msg.phase.slice(1)}
                                </div>
                            );
                        }
                        if (msg.type === 'system') {
                            const isError = msg.content.includes('❌') || msg.content.includes('Error');
                            return (
                                <div key={msg.id} className={`hcode-stream-entry ${isError ? 'hcode-stream-error' : 'hcode-stream-system'}`}>
                                    {msg.content}
                                </div>
                            );
                        }
                        // regular agent chat (fallback if any exist)
                        return (
                            <div key={msg.id} className="hcode-stream-entry" style={{ color: 'var(--fg-secondary)' }}>
                                {msg.content}
                            </div>
                        );
                    })}

                    {/* Reasoning Panel (Inline Collapsible) */}
                    {state.thoughts && (
                        <div className="hcode-stream-action">
                            <details open={state.agentPhase === 'thinking'}>
                                <summary className="hcode-stream-action-header">
                                    <span className="hcode-tree-arrow" style={{ display: 'inline-block', width: '16px' }}>▶</span>
                                    Internal Reasoning
                                </summary>
                                <div className="hcode-stream-action-details hcode-markdown"
                                    dangerouslySetInnerHTML={{ __html: renderedThoughts || '' }} />
                            </details>
                        </div>
                    )}

                    {/* Pending Approval Inline Card */}
                    {state.runPhase === 'waiting_approval' && (
                        <div className="hcode-inline-card">
                            <div className="hcode-card-header" style={{ color: 'var(--semantic-warning)' }}>
                                Approval Required
                            </div>
                            <div className="hcode-card-body">
                                {state.promptQuestion || "The agent is waiting for your approval to proceed."}
                            </div>
                            <div className="hcode-card-actions">
                                <button className="hcode-btn hcode-btn--primary" onClick={handleApprove}>Approve</button>
                                <button className="hcode-btn hcode-btn--secondary" onClick={handleReject}>Reject</button>
                            </div>
                        </div>
                    )}

                    {/* Error Card */}
                    {state.runPhase === 'error' && state.errorMessage && (
                        <div className="hcode-error-panel">
                            <div style={{ fontWeight: 600, marginBottom: 'var(--space-2)' }}>Task Failed</div>
                            <div>{state.errorMessage}</div>
                            {state.errorSuggestion && <div style={{ marginTop: 'var(--space-2)', color: 'var(--fg-secondary)' }}>{state.errorSuggestion}</div>}
                        </div>
                    )}

                    {/* Bottom padding for scroll */}
                    <div ref={endOfStreamRef} style={{ height: 'var(--space-4)' }} />
                </div>
            </main>

            {/* Task Composer */}
            {(currentMode === 'run' || currentMode === 'chat') && (
                <TaskComposer
                    onSubmit={handleRunTask}
                    disabled={isRunning}
                    initialTask={state.replayTask}
                />
            )}
        </div>
    );
}
