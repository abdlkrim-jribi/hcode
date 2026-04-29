/**
 * E2E test suite — smoke test for hcode.runTask workflow.
 */
import * as vscode from 'vscode';
import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';

suite('Hcode Extension E2E Smoke Test', () => {
    test('Extension should be present and active', async () => {
        const ext = vscode.extensions.getExtension('hcode-dev.vscode-hcode');
        assert.ok(ext, 'Extension not found');
        await ext!.activate();
        assert.ok(ext!.isActive, 'Extension did not activate');
    });

    test('hcode.runTask command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('hcode.runTask'), 'hcode.runTask not registered');
    });

    test('hcode.openChat command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('hcode.openChat'), 'hcode.openChat not registered');
    });

    test('hcode.openSettings command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('hcode.openSettings'), 'hcode.openSettings not registered');
    });
});
