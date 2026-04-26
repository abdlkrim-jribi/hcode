/**
 * E2E Smoke Test — validates the hcode.runTask workflow end-to-end.
 *
 * This script launches VS Code in extension test mode using @vscode/test-electron.
 * If the real hcode CLI is unavailable, it falls back to a mock process.
 */
const path = require('path');
const { runTests } = require('@vscode/test-electron');

async function main() {
    try {
        const extensionDevelopmentPath = path.resolve(__dirname, '../../');
        const extensionTestsPath = path.resolve(__dirname, './suite/index');

        await runTests({
            extensionDevelopmentPath,
            extensionTestsPath,
            launchArgs: [
                '--disable-extensions',
                path.resolve(__dirname, '../../test/fixtures/workspace'),
            ],
        });
    } catch (err) {
        console.error('E2E test failed:', err);
        process.exit(1);
    }
}

main();
