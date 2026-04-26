import * as vscode from 'vscode';
import * as path from 'path';
import { HcodeBridge } from './hcodeBridge';
import { GitIntegration } from './gitIntegration';

export class SidebarProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _bridge: HcodeBridge,
        private readonly _git: GitIntegration,
        private readonly _viewType: string
    ) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'run_task': {
                    const context = this.getActiveEditorContext();
                    const prompt = context
                        ? `[Active File: ${context.relativePath} | Selection: ${context.selection ? `Lines ${context.range.start}-${context.range.end}` : 'None'}]\n\nTask: ${data.task}`
                        : data.task;
                    vscode.commands.executeCommand('hcode.runTask', prompt);
                    break;
                }
                case 'pick_folder':
                    const folders = await vscode.window.showOpenDialog({
                        canSelectFolders: true,
                        canSelectFiles: false,
                        canSelectMany: false
                    });
                    if (folders && folders[0]) {
                        this._bridge.setWorkDir(folders[0].fsPath);
                        webviewView.webview.postMessage({ type: 'folder_selected', path: folders[0].fsPath });
                    }
                    break;
                case 'open_file':
                    const uri = vscode.Uri.file(data.path);
                    await vscode.window.showTextDocument(uri);
                    break;
            }
        });
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

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'webview_build', 'webview.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'webview_build', 'vscode-hcode.css'));
        const nonce = getNonce();

        // Pass 'mode' to the React app to render the correct view
        const mode = this._viewType === 'hcode.sidebar' ? 'sidebar' : 'history';

        return `<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} https:;">
                <link href="${styleUri}" rel="stylesheet">
                <title>Hcode</title>
            </head>
            <body>
                <div id="root" data-mode="${mode}"></div>
                <script nonce="${nonce}" src="${scriptUri}"></script>
            </body>
            </html>`;
    }
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
