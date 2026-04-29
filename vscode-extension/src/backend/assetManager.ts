import * as cp from 'child_process';
import * as vscode from 'vscode';

export interface AssetDiagnostics {
    isInstalled: boolean;
    version?: string;
    error?: string;
    suggestion?: string;
}

export class AssetManager {
    /**
     * Validate the Hcode Python core installation.
     */
    public async validateSetup(): Promise<AssetDiagnostics> {
        const cliPath = vscode.workspace.getConfiguration('hcode').get<string>('cliPath', 'hcode');

        return new Promise((resolve) => {
            cp.exec(`${cliPath} --version`, (err, stdout) => {
                if (err) {
                    resolve({
                        isInstalled: false,
                        error: 'Hcode core not found',
                        suggestion: 'Please install the Hcode Python core using: pip install hcode-agent'
                    });
                } else {
                    resolve({
                        isInstalled: true,
                        version: stdout.trim()
                    });
                }
            });
        });
    }

    /**
     * Prompt user to install if missing.
     */
    public async promptSetupIfMissing(): Promise<void> {
        const diag = await this.validateSetup();
        if (!diag.isInstalled) {
            const choice = await vscode.window.showWarningMessage(
                `Hcode core is not installed or not found at "${vscode.workspace.getConfiguration('hcode').get('cliPath')}".`,
                'Install via Pip',
                'Configure Path'
            );

            if (choice === 'Install via Pip') {
                const terminal = vscode.window.createTerminal('Hcode Setup');
                terminal.sendText('pip install hcode-agent');
                terminal.show();
            } else if (choice === 'Configure Path') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'hcode.cliPath');
            }
        }
    }
}
