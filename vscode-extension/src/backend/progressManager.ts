import * as vscode from 'vscode';

export class ProgressManager {
    private _progress?: vscode.Progress<{ message?: string; increment?: number }>;
    private _resolve?: (value: void | PromiseLike<void>) => void;

    /**
     * Start showing a progress notification in VS Code.
     * @param title The title of the progress notification (e.g., "Hcode is working")
     */
    public async start(title: string): Promise<void> {
        if (this._progress) {
            this.stop();
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: title,
            cancellable: true
        }, (progress, token) => {
            this._progress = progress;

            token.onCancellationRequested(() => {
                vscode.commands.executeCommand('hcode.stop'); // Logic to kill process
            });

            return new Promise<void>((resolve) => {
                this._resolve = resolve;
            });
        });
    }

    /**
     * Update the progress message.
     * @param message The new status message
     * @param increment Optional percentage increment
     */
    public report(message: string, increment?: number): void {
        this._progress?.report({ message, increment });
    }

    /**
     * Stop and hide the progress notification.
     */
    public stop(): void {
        if (this._resolve) {
            this._resolve();
            this._resolve = undefined;
        }
        this._progress = undefined;
    }
}
