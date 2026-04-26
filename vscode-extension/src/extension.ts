/**
 * Hcode VS Code Extension — Entry Point
 * Registers commands and manages the webview panels lifecycle.
 */
import * as vscode from 'vscode';
import * as path from 'path';
import { HcodeBridge } from './backend/hcodeBridge';
import { SecretStorageManager } from './backend/secretStorage';
import { GitIntegration } from './backend/gitIntegration';
import { WebviewPanelManager } from './webviewPanelManager';
import { SidebarProvider } from './backend/sidebarProvider';
import { AssetManager } from './backend/assetManager';

let bridge: HcodeBridge | undefined;
let panelManager: WebviewPanelManager | undefined;
let sidebarProvider: SidebarProvider | undefined;
let historyProvider: SidebarProvider | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('[Hcode] Extension activating...');

    const assetManager = new AssetManager();
    // Non-blocking setup check
    assetManager.promptSetupIfMissing();

    const secretStorage = new SecretStorageManager(context.secrets);
    const git = new GitIntegration();

    // Initialise bridge (lazy — spawns process on first use)
    bridge = new HcodeBridge(secretStorage);
    panelManager = new WebviewPanelManager(context, bridge, git);

    // Sidebar providers
    sidebarProvider = new SidebarProvider(context.extensionUri, bridge, git, 'hcode.sidebar');
    historyProvider = new SidebarProvider(context.extensionUri, bridge, git, 'hcode.history');

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('hcode.sidebar', sidebarProvider),
        vscode.window.registerWebviewViewProvider('hcode.history', historyProvider)
    );

    // ── Commands ──────────────────────────────────────────────────────────────
    context.subscriptions.push(
        vscode.commands.registerCommand('hcode.runTask', async (initialTask?: string) => {
            await panelManager!.openRunTaskPanel(initialTask);
        }),

        vscode.commands.registerCommand('hcode.openChat', async () => {
            await panelManager!.openChatPanel();
        }),

        vscode.commands.registerCommand('hcode.openSettings', async () => {
            await panelManager!.openSettingsPanel();
        }),

        vscode.commands.registerCommand('hcode.refactorSelection', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage('No active editor found.');
                return;
            }

            const selection = editor.selection;
            const text = editor.document.getText(selection);
            if (!text) {
                vscode.window.showInformationMessage('Please select some code to refactor.');
                return;
            }

            const prompt = `Refactor the following code:\n\n\`\`\`${editor.document.languageId}\n${text}\n\`\`\``;
            await panelManager!.openRunTaskPanel(prompt);
        }),
    );

    console.log('[Hcode] Extension activated. Commands registered.');
}

export function deactivate(): void {
    console.log('[Hcode] Deactivating — killing child processes...');
    bridge?.dispose();
}
