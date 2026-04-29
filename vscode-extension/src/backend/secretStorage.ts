/**
 * SecretStorageManager — thin wrapper around VS Code SecretStorage.
 * Stores API keys securely (encrypted by VS Code on the host OS keychain).
 */
import * as vscode from 'vscode';

export type ProviderKey = 'openai' | 'anthropic' | 'cerebras';

const KEY_PREFIX = 'hcode.apikey.';

export class SecretStorageManager {
    constructor(private readonly storage: vscode.SecretStorage) { }

    async getKey(provider: ProviderKey): Promise<string | undefined> {
        return this.storage.get(`${KEY_PREFIX}${provider}`);
    }

    async setKey(provider: ProviderKey, value: string): Promise<void> {
        await this.storage.store(`${KEY_PREFIX}${provider}`, value);
    }

    async deleteKey(provider: ProviderKey): Promise<void> {
        await this.storage.delete(`${KEY_PREFIX}${provider}`);
    }

    async hasKey(provider: ProviderKey): Promise<boolean> {
        const val = await this.getKey(provider);
        return val !== undefined && val.length > 0;
    }
}
