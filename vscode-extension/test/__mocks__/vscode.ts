/**
 * VS Code API mock for Jest unit tests.
 * Provides stub implementations of the vscode module.
 */

const vscode = {
    window: {
        createWebviewPanel: jest.fn().mockReturnValue({
            webview: {
                html: '',
                onDidReceiveMessage: jest.fn(),
                postMessage: jest.fn(),
                asWebviewUri: jest.fn((uri: any) => uri),
                cspSource: 'mock-csp-source',
            },
            onDidDispose: jest.fn(),
            reveal: jest.fn(),
            dispose: jest.fn(),
        }),
        createOutputChannel: jest.fn().mockReturnValue({
            appendLine: jest.fn(),
            show: jest.fn(),
            dispose: jest.fn(),
        }),
        showErrorMessage: jest.fn(),
        showInformationMessage: jest.fn(),
    },
    commands: {
        registerCommand: jest.fn().mockReturnValue({ dispose: jest.fn() }),
        executeCommand: jest.fn(),
    },
    workspace: {
        getConfiguration: jest.fn().mockReturnValue({
            get: jest.fn((key: string, def: any) => def),
        }),
        workspaceFolders: [{ uri: { fsPath: '/mock/workspace' } }],
    },
    Uri: {
        joinPath: jest.fn((...args: any[]) => ({ fsPath: args.join('/'), toString: () => args.join('/') })),
        parse: jest.fn((s: string) => ({ fsPath: s, toString: () => s })),
        file: jest.fn((s: string) => ({ fsPath: s })),
    },
    ViewColumn: { One: 1, Two: 2, Three: 3 },
    SecretStorage: jest.fn(),
    EventEmitter: jest.fn(),
    Disposable: { from: jest.fn() },
};

module.exports = vscode;
