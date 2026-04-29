/**
 * HcodeBridge — IPC layer between the VS Code extension and the Hcode CLI.
 *
 * The hcode CLI outputs Rich-formatted text on stdout/stderr.
 * We capture all output as log lines and forward them to the webview.
 * The extension monitors output for key patterns (plan markers, file edits, etc.)
 * to drive the UI state machine.
 */
import * as cp from 'child_process';
import * as readline from 'readline';
import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { SecretStorageManager } from './secretStorage';

// ── Message Types ────────────────────────────────────────────────────────────

export interface PlanPayload { markdown: string }
export interface TaskUpdatePayload { markdown: string }
export interface FilePatchPayload { path: string; diff: string; backup: string; originalContent: string; newContent: string }
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
    | { type: 'progress'; payload: { label: string; increment?: number } }
    | { type: 'ready' }
    | { type: 'done' };

// ── Bridge ───────────────────────────────────────────────────────────────────

const PROGRESS_MARKERS = [
    { pattern: /Hcode is searching/i, label: 'Searching files...' },
    { pattern: /Hcode is planning/i, label: 'Planning...' },
    { pattern: /Hcode is applying/i, label: 'Applying changes...' },
    { pattern: /Hcode is verifying/i, label: 'Verifying...' },
    { pattern: /Hcode is thinking/i, label: 'Thinking...' },
];

// Phase transition markers emitted by the Python core
const PHASE_MARKERS: { pattern: RegExp; phase: string }[] = [
    { pattern: />\s*Phase:\s*Planning/i, phase: 'planning' },
    { pattern: />\s*Phase:\s*Execution/i, phase: 'executing' },
    { pattern: />\s*Phase:\s*Verification/i, phase: 'verifying' },
    { pattern: /Fast Mode:\s*Understand/i, phase: 'executing' },
    { pattern: /Hcode is thinking/i, phase: 'thinking' },
    { pattern: /Hcode is planning/i, phase: 'planning' },
    { pattern: /Hcode is verifying/i, phase: 'verifying' },
    { pattern: /Task completed successfully/i, phase: 'done' },
];

export class HcodeBridge extends EventEmitter {
    private proc: cp.ChildProcess | undefined;
    private rl: readline.Interface | undefined;
    private outputChannel: vscode.OutputChannel;
    private secretStorage: SecretStorageManager;

    constructor(secretStorage: SecretStorageManager) {
        super();
        this.secretStorage = secretStorage;
        this.outputChannel = vscode.window.createOutputChannel('Hcode');
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    async runTask(task: string, autonomous: boolean = false): Promise<void> {
        // Kill previous process if still running
        if (this.proc) { this.kill(); }

        const cliPath = vscode.workspace.getConfiguration('hcode').get<string>('cliPath', 'hcode');
        const provider = vscode.workspace.getConfiguration('hcode').get<string>('provider', 'auto');
        const workDir = this.getWorkDir();

        // Build args using actual hcode CLI flags
        // Task must be quoted — shell: true splits unquoted strings on spaces
        const quotedTask = `"${task.replace(/"/g, '\\"')}"`;
        const args = ['run', quotedTask, '--verbose'];
        if (autonomous) { args.push('--autonomous'); }
        if (provider && provider !== 'auto') { args.push('--provider', provider); }

        // Inject API keys as env vars
        const env = await this.buildEnv();

        this.outputChannel.appendLine(`[Hcode] Spawning: ${cliPath} ${args.join(' ')}`);
        this.outputChannel.show(true);

        this.proc = cp.spawn(cliPath, args, {
            cwd: workDir,
            env,
            shell: process.platform === 'win32',
        });

        this.rl = readline.createInterface({ input: this.proc.stdout! });

        this.rl.on('line', (line: string) => {
            this.outputChannel.appendLine(`[stdout] ${line}`);
            this.parseLine(line);
        });

        this.proc.stderr?.on('data', (data: Buffer) => {
            const text = data.toString().trim();
            if (!text) { return; }
            this.outputChannel.appendLine(`[stderr] ${text}`);
            // Forward stderr lines individually
            for (const line of text.split('\n')) {
                this.emit('message', { type: 'log', payload: { line: line.trim(), stream: 'stderr' } } as HcodeMessage);
            }
        });

        this.proc.on('close', (code) => {
            this.outputChannel.appendLine(`[Hcode] Process exited with code ${code}`);
            if (code !== 0 && code !== null) {
                this.emit('message', {
                    type: 'error',
                    payload: {
                        message: `Hcode exited with code ${code}`,
                        suggestion: 'Check the Output panel (Hcode) for details.',
                    },
                } as HcodeMessage);
            }
            this.emit('message', { type: 'done' } as HcodeMessage);
            this.proc = undefined;
            this.rl = undefined;
        });

        this.proc.on('error', (err) => {
            const msg: HcodeMessage = {
                type: 'error',
                payload: {
                    message: `Failed to start hcode: ${err.message}`,
                    suggestion: 'Check that hcode is installed (pip install hcode) and the cliPath setting is correct.',
                },
            };
            this.emit('message', msg);
        });
    }

    sendApproval(): void {
        this.sendToProcess('A\n');
    }

    sendRejection(comment: string): void {
        this.sendToProcess('C\n');
    }

    sendRollback(): void {
        this.kill();
    }

    sendFileDecision(filePath: string, accepted: boolean): void {
        this.sendToProcess(accepted ? 'A\n' : 'C\n');
    }

    kill(): void {
        this.proc?.kill();
        this.rl?.close();
        this.proc = undefined;
        this.rl = undefined;
    }

    dispose(): void {
        this.kill();
        this.outputChannel.dispose();
    }

    // ── Private ────────────────────────────────────────────────────────────────

    private parseLine(line: string): void {
        const trimmed = line.trim();
        if (!trimmed) { return; }

        // Try to parse as JSON first (in case hcode outputs JSON in the future)
        if (trimmed.startsWith('{')) {
            try {
                const msg: HcodeMessage = JSON.parse(trimmed);
                this.emit('message', msg);
                return;
            } catch {
                // Not JSON, fall through to text handling
            }
        }

        // Check for progress markers
        for (const marker of PROGRESS_MARKERS) {
            if (marker.pattern.test(trimmed)) {
                this.emit('message', { type: 'progress', payload: { label: marker.label } } as HcodeMessage);
                // Don't return, we still want to log the line
            }
        }

        // Check for agent phase transition markers
        for (const marker of PHASE_MARKERS) {
            if (marker.pattern.test(trimmed)) {
                this.emit('message', { type: 'agent_phase', phase: marker.phase } as unknown as HcodeMessage);
                break; // Only emit the first matching phase per line
            }
        }

        // All text output is forwarded as log lines
        this.emit('message', { type: 'log', payload: { line: trimmed, stream: 'stdout' } } as HcodeMessage);
    }

    private sendToProcess(text: string): void {
        if (!this.proc?.stdin) {
            vscode.window.showErrorMessage('[Hcode] No active process to send to.');
            return;
        }
        this.proc.stdin.write(text);
    }

    private customCwd: string | undefined;

    setWorkDir(path: string): void {
        this.customCwd = path;
    }

    private getWorkDir(): string {
        if (this.customCwd) { return this.customCwd; }
        const configured = vscode.workspace.getConfiguration('hcode').get<string>('workingDirectory', '');
        if (configured) { return configured; }
        const folders = vscode.workspace.workspaceFolders;
        return folders?.[0]?.uri.fsPath ?? process.cwd();
    }

    private async buildEnv(): Promise<NodeJS.ProcessEnv> {
        const env: NodeJS.ProcessEnv = { ...process.env };
        const provider = vscode.workspace.getConfiguration('hcode').get<string>('provider', 'auto');

        const openaiKey = await this.secretStorage.getKey('openai');
        const anthropicKey = await this.secretStorage.getKey('anthropic');
        const cerebrasKey = await this.secretStorage.getKey('cerebras');

        if (openaiKey) { env['OPENAI_API_KEY'] = openaiKey; }
        if (anthropicKey) { env['ANTHROPIC_API_KEY'] = anthropicKey; }
        if (cerebrasKey) { env['CEREBRAS_API_KEY'] = cerebrasKey; }

        if (provider === 'cerebras') {
            env['OPENAI_BASE_URL'] = 'https://api.cerebras.ai/v1';
            env['OPENAI_MODEL'] = 'gpt-oss-120b';
            if (cerebrasKey) { env['OPENAI_API_KEY'] = cerebrasKey; }
        }

        // Force clean text output — prevents Rich Unicode crash on Windows cp1252
        env['TERM'] = 'dumb';
        env['NO_COLOR'] = '1';
        env['FORCE_COLOR'] = '0';
        env['PYTHONUNBUFFERED'] = '1';
        env['PYTHONIOENCODING'] = 'utf-8';
        env['COLUMNS'] = '200';  // Wide terminal so Rich doesn't wrap

        return env;
    }
}
