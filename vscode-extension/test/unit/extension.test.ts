/**
 * Unit tests for extension activation and command registration.
 */
import * as vscode from 'vscode';

jest.mock('vscode', () => ({
    commands: {
        registerCommand: jest.fn(),
        executeCommand: jest.fn(),
    },
    window: {
        registerWebviewViewProvider: jest.fn().mockReturnValue({ dispose: jest.fn() }),
        showInformationMessage: jest.fn(),
        showErrorMessage: jest.fn(),
        showWarningMessage: jest.fn(),
        createOutputChannel: jest.fn().mockReturnValue({
            appendLine: jest.fn(),
            show: jest.fn(),
            dispose: jest.fn(),
        }),
        activeTextEditor: undefined,
    },
    workspace: {
        getConfiguration: jest.fn().mockReturnValue({
            get: jest.fn((key: string, def: any) => def),
        }),
        workspaceFolders: [{ uri: { fsPath: '/mock/workspace' } }],
    },
    ProgressLocation: {
        Notification: 15,
    },
}));

// Mock the backend modules to avoid spawning real processes
jest.mock('../../src/backend/hcodeBridge', () => ({
    HcodeBridge: jest.fn().mockImplementation(() => ({
        on: jest.fn(),
        off: jest.fn(),
        runTask: jest.fn(),
        sendApproval: jest.fn(),
        sendRejection: jest.fn(),
        sendRollback: jest.fn(),
        sendFileDecision: jest.fn(),
        kill: jest.fn(),
        dispose: jest.fn(),
    })),
}));

jest.mock('../../src/backend/secretStorage', () => ({
    SecretStorageManager: jest.fn().mockImplementation(() => ({
        getKey: jest.fn().mockResolvedValue(undefined),
        setKey: jest.fn().mockResolvedValue(undefined),
        deleteKey: jest.fn().mockResolvedValue(undefined),
        hasKey: jest.fn().mockResolvedValue(false),
    })),
}));

jest.mock('../../src/backend/gitIntegration', () => ({
    GitIntegration: jest.fn().mockImplementation(() => ({
        getBranchName: jest.fn().mockResolvedValue('main'),
        getStatus: jest.fn().mockResolvedValue(null),
        getStagingPreview: jest.fn().mockResolvedValue('(no staged changes)'),
        commitWithMessage: jest.fn().mockResolvedValue(true),
        stageAll: jest.fn().mockResolvedValue(undefined),
    })),
}));

jest.mock('../../src/backend/assetManager', () => ({
    AssetManager: jest.fn().mockImplementation(() => ({
        validateSetup: jest.fn().mockResolvedValue({ isInstalled: true }),
        promptSetupIfMissing: jest.fn().mockResolvedValue(undefined),
    })),
}));

jest.mock('../../src/backend/sidebarProvider', () => ({
    SidebarProvider: jest.fn().mockImplementation(() => ({
        resolveWebviewView: jest.fn(),
    })),
}));

jest.mock('../../src/webviewPanelManager', () => ({
    WebviewPanelManager: jest.fn().mockImplementation(() => ({
        openRunTaskPanel: jest.fn().mockResolvedValue(undefined),
        openChatPanel: jest.fn().mockResolvedValue(undefined),
        openSettingsPanel: jest.fn().mockResolvedValue(undefined),
    })),
}));

describe('Extension Activation', () => {
    let context: any;

    beforeEach(() => {
        jest.clearAllMocks();
        context = {
            subscriptions: [],
            secrets: {
                get: jest.fn().mockResolvedValue(undefined),
                store: jest.fn().mockResolvedValue(undefined),
                delete: jest.fn().mockResolvedValue(undefined),
            },
            extensionUri: { fsPath: '/mock/extension' },
        };
        // Mock vscode.window.registerWebviewViewProvider to prevent errors
        (vscode.window.registerWebviewViewProvider as jest.Mock).mockReturnValue({ dispose: jest.fn() });
    });

    it('should activate without throwing', async () => {
        const { activate } = await import('../../src/extension');
        await expect(activate(context)).resolves.toBeUndefined();
    });

    it('should register hcode.runTask command', async () => {
        const { activate } = await import('../../src/extension');
        await activate(context);
        const calls = (vscode.commands.registerCommand as jest.Mock).mock.calls;
        const commandNames = calls.map((c: any[]) => c[0]);
        expect(commandNames).toContain('hcode.runTask');
    });

    it('should register hcode.openChat command', async () => {
        const { activate } = await import('../../src/extension');
        await activate(context);
        const calls = (vscode.commands.registerCommand as jest.Mock).mock.calls;
        const commandNames = calls.map((c: any[]) => c[0]);
        expect(commandNames).toContain('hcode.openChat');
    });

    it('should register hcode.openSettings command', async () => {
        const { activate } = await import('../../src/extension');
        await activate(context);
        const calls = (vscode.commands.registerCommand as jest.Mock).mock.calls;
        const commandNames = calls.map((c: any[]) => c[0]);
        expect(commandNames).toContain('hcode.openSettings');
    });

    it('should register sidebar providers', async () => {
        const { activate } = await import('../../src/extension');
        await activate(context);
        const calls = (vscode.window.registerWebviewViewProvider as jest.Mock).mock.calls;
        const viewIds = calls.map((c: any[]) => c[0]);
        expect(viewIds).toContain('hcode.sidebar');
        expect(viewIds).toContain('hcode.history');
    });

    it('should add subscriptions to context', async () => {
        const { activate } = await import('../../src/extension');
        await activate(context);
        expect(context.subscriptions.length).toBeGreaterThan(0);
    });

    it('should deactivate cleanly', async () => {
        const { activate, deactivate } = await import('../../src/extension');
        await activate(context);
        expect(() => deactivate()).not.toThrow();
    });
});
