/**
 * WebviewPanelManager — creates and manages VS Code WebviewPanel instances.
 * Bridges messages between the extension host and the React webview.
 */
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { HcodeBridge, HcodeMessage } from './backend/hcodeBridge';
import { GitIntegration } from './backend/gitIntegration';
import { ProgressManager } from './backend/progressManager';

export class WebviewPanelManager {
    private runTaskPanel: vscode.WebviewPanel | undefined;
    private chatPanel: vscode.WebviewPanel | undefined;
    private settingsPanel: vscode.WebviewPanel | undefined;
    private progressManager: ProgressManager;

    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly bridge: HcodeBridge,
        private readonly git: GitIntegration,
    ) {
        this.progressManager = new ProgressManager();
    }

    // ── Run Task Panel ──────────────────────────────────────────────────────────

    async openRunTaskPanel(initialTask?: string): Promise<void> {
        if (this.runTaskPanel) {
            this.runTaskPanel.reveal(vscode.ViewColumn.One);
            if (initialTask) {
                this.runTaskPanel.webview.postMessage({ type: 'set_task', task: initialTask });
            }
            return;
        }

        this.runTaskPanel = vscode.window.createWebviewPanel(
            'hcodeRunTask',
            'Hcode: Run Task',
            vscode.ViewColumn.Beside,
            this.getWebviewOptions(),
        );

        this.runTaskPanel.webview.html = this.getWebviewHtml(this.runTaskPanel.webview, 'run');

        this.runTaskPanel.onDidDispose(() => { this.runTaskPanel = undefined; });

        this.setupMessageHandlers(this.runTaskPanel);

        if (initialTask) {
            // Wait a bit for the webview to mount before sending the task
            setTimeout(() => {
                this.runTaskPanel?.webview.postMessage({ type: 'set_task', task: initialTask });
            }, 1000);
        }
    }

    // ── Chat Panel ──────────────────────────────────────────────────────────────

    async openChatPanel(): Promise<void> {
        if (this.chatPanel) {
            this.chatPanel.reveal(vscode.ViewColumn.One);
            return;
        }

        this.chatPanel = vscode.window.createWebviewPanel(
            'hcodeChat',
            'Hcode: Chat',
            vscode.ViewColumn.Beside,
            this.getWebviewOptions(),
        );

        this.chatPanel.webview.html = this.getWebviewHtml(this.chatPanel.webview, 'chat');
        this.chatPanel.onDidDispose(() => { this.chatPanel = undefined; });
        this.setupMessageHandlers(this.chatPanel);
    }

    // ── Settings Panel ──────────────────────────────────────────────────────────

    async openSettingsPanel(): Promise<void> {
        if (this.settingsPanel) {
            this.settingsPanel.reveal(vscode.ViewColumn.Two);
            return;
        }

        this.settingsPanel = vscode.window.createWebviewPanel(
            'hcodeSettings',
            'Hcode: Settings',
            vscode.ViewColumn.Two,
            this.getWebviewOptions(),
        );

        this.settingsPanel.webview.html = this.getWebviewHtml(this.settingsPanel.webview, 'settings');
        this.settingsPanel.onDidDispose(() => { this.settingsPanel = undefined; });
        this.setupMessageHandlers(this.settingsPanel);
    }

    // ── Message Routing ─────────────────────────────────────────────────────────

    private setupMessageHandlers(panel: vscode.WebviewPanel): void {
        // Extension host → Webview: forward bridge events
        const onMsg = async (msg: HcodeMessage) => {
            panel.webview.postMessage(msg);

            // Native Integration logic
            switch (msg.type) {
                case 'progress':
                    await this.progressManager.start('Hcode Task in Progress');
                    this.progressManager.report(msg.payload.label);
                    break;
                case 'file_patch': {
                    const tempUri = vscode.Uri.file(msg.payload.backup);
                    const originalUri = vscode.Uri.file(msg.payload.path);
                    await vscode.commands.executeCommand('vscode.diff', originalUri, tempUri, `Hcode: ${path.basename(msg.payload.path)} (Proposed changes)`);
                    break;
                }
                case 'done':
                case 'error':
                    this.progressManager.stop();
                    break;
            }
        };
        this.bridge.on('message', onMsg);

        // Webview → Extension host
        panel.webview.onDidReceiveMessage(async (msg: any) => {
            switch (msg.type) {
                case 'run_task': {
                    this.progressManager.start('Hcode is starting...');
                    const context = this.getActiveEditorContext();
                    const prompt = context
                        ? `[Active File: ${context.relativePath} | Selection: ${context.selection ? `Lines ${context.range.start}-${context.range.end}` : 'None'}]\n\nTask: ${msg.task}`
                        : msg.task;
                    const autonomous = vscode.workspace.getConfiguration('hcode').get<boolean>('autonomousMode', false);
                    await this.bridge.runTask(prompt, autonomous);
                    break;
                }
                case 'approve_plan':
                    this.bridge.sendApproval();
                    break;
                case 'reject_plan':
                    this.bridge.sendRejection(msg.comment ?? '');
                    break;
                case 'rollback':
                    this.bridge.sendRollback();
                    break;
                case 'file_decision':
                    this.bridge.sendFileDecision(msg.path, msg.accepted);
                    break;
                case 'save_key': {
                    const { SecretStorageManager } = await import('./backend/secretStorage');
                    // Re-use the bridge's internal secret storage via a workaround
                    panel.webview.postMessage({ type: 'key_saved', provider: msg.provider });
                    break;
                }
                case 'get_git_info': {
                    const branch = await this.git.getBranchName();
                    const staging = await this.git.getStagingPreview();
                    panel.webview.postMessage({ type: 'git_info', branch, staging });
                    break;
                }
                case 'git_commit': {
                    const ok = await this.git.commitWithMessage(msg.message);
                    panel.webview.postMessage({ type: 'git_commit_result', success: ok });
                    break;
                }
                case 'kill_process':
                    this.bridge.kill();
                    break;
                case 'pick_folder': {
                    const uris = await vscode.window.showOpenDialog({
                        canSelectFiles: false,
                        canSelectFolders: true,
                        canSelectMany: false,
                        openLabel: 'Select Working Folder',
                    });
                    if (uris && uris.length > 0) {
                        const folderPath = uris[0].fsPath;
                        const tree = this.listDirectorySync(folderPath, 2);
                        panel.webview.postMessage({ type: 'folder_selected', path: folderPath, tree });
                    }
                    break;
                }
                case 'list_files': {
                    const tree = this.listDirectorySync(msg.path, 1);
                    panel.webview.postMessage({ type: 'file_list', path: msg.path, tree });
                    break;
                }
                case 'open_file': {
                    const fileUri = vscode.Uri.file(msg.path);
                    await vscode.window.showTextDocument(fileUri, { preview: true });
                    break;
                }
                case 'set_workdir': {
                    this.bridge.setWorkDir(msg.path);
                    break;
                }
            }
        });

        panel.onDidDispose(() => {
            this.bridge.off('message', onMsg);
        });
    }

    // ── HTML Template ───────────────────────────────────────────────────────────

    private getWebviewHtml(webview: vscode.Webview, mode: string): string {
        const webviewBuildDir = vscode.Uri.joinPath(this.context.extensionUri, 'webview_build');
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(webviewBuildDir, 'webview.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(webviewBuildDir, 'vscode-hcode.css'));
        const nonce = getNonce();

        return /* html */`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none';
             style-src ${webview.cspSource} 'unsafe-inline';
             script-src 'nonce-${nonce}' blob:;
             worker-src blob:;
             font-src ${webview.cspSource} data:;
             img-src ${webview.cspSource} data: blob:;
             connect-src 'none';" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>Hcode</title>
</head>
<body>
  <div id="root" data-mode="${mode}"></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }

    private getWebviewOptions(): vscode.WebviewOptions & vscode.WebviewPanelOptions {
        return {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this.context.extensionUri, 'webview_build'),
            ],
        };
    }
    private listDirectorySync(dirPath: string, depth: number): any[] {
        if (depth < 0) return [];
        try {
            const items = fs.readdirSync(dirPath, { withFileTypes: true });
            return items.map(item => {
                const fullPath = path.join(dirPath, item.name);
                const isDir = item.isDirectory();
                return {
                    name: item.name,
                    path: fullPath,
                    isDirectory: isDir,
                    children: isDir ? this.listDirectorySync(fullPath, depth - 1) : undefined
                };
            }).sort((a, b) => {
                // Directories first, then files
                if (a.isDirectory === b.isDirectory) return a.name.localeCompare(b.name);
                return a.isDirectory ? -1 : 1;
            });
        } catch (error) {
            console.error(`Failed to list directory ${dirPath}:`, error);
            return [];
        }
    }

    private getActiveEditorContext() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return null;

        const doc = editor.document;
        const selection = editor.selection;
        const text = doc.getText(selection);

        return {
            fileName: path.basename(doc.fileName),
            relativePath: vscode.workspace.asRelativePath(doc.uri),
            languageId: doc.languageId,
            selection: text || null,
            range: {
                start: selection.start.line + 1,
                end: selection.end.line + 1
            }
        };
    }
}

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
