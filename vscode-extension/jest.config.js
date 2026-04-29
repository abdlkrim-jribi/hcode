/** @type {import('jest').Config} */
module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'node',
    roots: ['<rootDir>/test/unit'],
    testMatch: ['**/*.test.ts'],
    transform: {
        '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.test.json' }],
    },
    moduleNameMapper: {
        '^vscode$': '<rootDir>/test/__mocks__/vscode.ts',
    },
    collectCoverageFrom: ['src/**/*.ts', '!src/webview/**'],
};
