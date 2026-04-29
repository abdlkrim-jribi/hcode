/**
 * GitIntegration — lightweight git helpers using simple-git.
 */
import simpleGit, { SimpleGit, StatusResult } from 'simple-git';
import * as vscode from 'vscode';

export class GitIntegration {
    private git: SimpleGit | undefined;

    private getGit(): SimpleGit {
        if (!this.git) {
            const workDir = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
            this.git = simpleGit(workDir);
        }
        return this.git;
    }

    async getBranchName(): Promise<string> {
        try {
            const result = await this.getGit().revparse(['--abbrev-ref', 'HEAD']);
            return result.trim();
        } catch {
            return 'unknown';
        }
    }

    async getStatus(): Promise<StatusResult | null> {
        try {
            return await this.getGit().status();
        } catch {
            return null;
        }
    }

    async getStagingPreview(): Promise<string> {
        try {
            const diff = await this.getGit().diff(['--cached', '--stat']);
            return diff || '(no staged changes)';
        } catch {
            return '(git unavailable)';
        }
    }

    async commitWithMessage(message: string): Promise<boolean> {
        try {
            await this.getGit().commit(message);
            return true;
        } catch (err) {
            vscode.window.showErrorMessage(`[Hcode] Git commit failed: ${err}`);
            return false;
        }
    }

    async stageAll(): Promise<void> {
        await this.getGit().add('.');
    }
}
