/**
 * Unit tests for HcodeBridge message parsing and IPC logic.
 */
import { EventEmitter } from 'events';

// Mock child_process and readline
const mockStdin = { write: jest.fn() };
const mockStdout = new EventEmitter();
const mockStderr = new EventEmitter();
const mockProc = {
    stdin: mockStdin,
    stdout: mockStdout,
    stderr: mockStderr,
    on: jest.fn(),
    kill: jest.fn(),
};

jest.mock('child_process', () => ({
    spawn: jest.fn().mockReturnValue(mockProc),
}));

jest.mock('readline', () => ({
    createInterface: jest.fn().mockReturnValue({
        on: jest.fn((event: string, cb: Function) => {
            if (event === 'line') {
                // Store the callback for manual triggering in tests
                (global as any).__rlLineCallback = cb;
            }
        }),
        close: jest.fn(),
    }),
}));

jest.mock('vscode', () => ({
    window: {
        createOutputChannel: jest.fn().mockReturnValue({
            appendLine: jest.fn(),
            show: jest.fn(),
            dispose: jest.fn(),
        }),
        showErrorMessage: jest.fn(),
    },
    workspace: {
        getConfiguration: jest.fn().mockReturnValue({
            get: jest.fn((_key: string, def: any) => def),
        }),
        workspaceFolders: [{ uri: { fsPath: '/mock/workspace' } }],
    },
}));

import { HcodeBridge } from '../../src/backend/hcodeBridge';
import { SecretStorageManager } from '../../src/backend/secretStorage';

describe('HcodeBridge', () => {
    let bridge: HcodeBridge;
    let mockSecrets: any;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSecrets = {
            getKey: jest.fn().mockResolvedValue(undefined),
            setKey: jest.fn(),
            deleteKey: jest.fn(),
            hasKey: jest.fn().mockResolvedValue(false),
        };
        bridge = new HcodeBridge(mockSecrets as any);
    });

    afterEach(() => {
        bridge.dispose();
    });

    it('should instantiate without error', () => {
        expect(bridge).toBeDefined();
    });

    it('should emit "plan" message when JSON plan line received', async () => {
        const received: any[] = [];
        bridge.on('message', (msg) => received.push(msg));

        await bridge.runTask('test task');

        // Simulate a JSON line from the process
        const planMsg = JSON.stringify({ type: 'plan', payload: { markdown: '# Plan\nDo stuff' } });
        (global as any).__rlLineCallback?.(planMsg);

        expect(received).toHaveLength(1);
        expect(received[0].type).toBe('plan');
        expect(received[0].payload.markdown).toContain('# Plan');
    });

    it('should emit "log" message for plain text lines', async () => {
        const received: any[] = [];
        bridge.on('message', (msg) => received.push(msg));

        await bridge.runTask('test task');

        (global as any).__rlLineCallback?.('plain text output');

        expect(received[0].type).toBe('log');
        expect(received[0].payload.line).toBe('plain text output');
    });

    it('should emit "error" message for error JSON', async () => {
        const received: any[] = [];
        bridge.on('message', (msg) => received.push(msg));

        await bridge.runTask('test task');

        const errMsg = JSON.stringify({ type: 'error', payload: { message: 'Something failed', suggestion: 'Try again' } });
        (global as any).__rlLineCallback?.(errMsg);

        expect(received[0].type).toBe('error');
        expect(received[0].payload.message).toBe('Something failed');
    });

    it('should send approval trigger to stdin', async () => {
        await bridge.runTask('test task');
        bridge.sendApproval();
        expect(mockStdin.write).toHaveBeenCalledWith('A\n');
    });

    it('should send rejection trigger to stdin', async () => {
        await bridge.runTask('test task');
        bridge.sendRejection('needs more detail');
        expect(mockStdin.write).toHaveBeenCalledWith('C\n');
    });

    it('should emit "progress" message when progress marker detected', async () => {
        const received: any[] = [];
        bridge.on('message', (msg) => received.push(msg));

        await bridge.runTask('test task');

        (global as any).__rlLineCallback?.('Hcode is planning the changes...');

        const progressMsg = received.find(m => m.type === 'progress');
        expect(progressMsg).toBeDefined();
        expect(progressMsg.payload.label).toBe('Planning...');

        // Also verify it still emits the log message
        const logMsg = received.find(m => m.type === 'log' && m.payload.line.includes('Hcode is planning'));
        expect(logMsg).toBeDefined();
    });

    it('should kill process on dispose', async () => {
        await bridge.runTask('test task');
        bridge.dispose();
        expect(mockProc.kill).toHaveBeenCalled();
    });
});
