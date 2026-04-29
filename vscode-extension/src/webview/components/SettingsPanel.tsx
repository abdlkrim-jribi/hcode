import React, { useState, useEffect } from 'react';

interface Props {
    post: (msg: object) => void;
}

type Provider = 'openai' | 'anthropic' | 'cerebras';

export default function SettingsPanel({ post }: Props) {
    const [autonomousMode, setAutonomousMode] = useState(false);
    const [provider, setProvider] = useState<string>('auto');
    const [keys, setKeys] = useState<Record<Provider, string>>({ openai: '', anthropic: '', cerebras: '' });
    const [saved, setSaved] = useState<Record<Provider, boolean>>({ openai: false, anthropic: false, cerebras: false });

    const saveKey = (p: Provider) => {
        post({ type: 'save_key', provider: p, key: keys[p] });
        setSaved((prev) => ({ ...prev, [p]: true }));
        setTimeout(() => setSaved((prev) => ({ ...prev, [p]: false })), 2000);
    };

    return (
        <div className="hcode-settings">
            <h1 className="hcode-settings-title">⚙️ Hcode Settings</h1>

            {/* Autonomous mode */}
            <section className="hcode-settings-section">
                <h2>Safety</h2>
                <label className="hcode-toggle-label">
                    <input
                        type="checkbox"
                        checked={autonomousMode}
                        onChange={(e) => setAutonomousMode(e.target.checked)}
                    />
                    <span>Autonomous Mode</span>
                </label>
                {autonomousMode && (
                    <div className="hcode-banner hcode-banner--warning">
                        ⚠️ <strong>Autonomous mode enabled.</strong> Hcode will execute plans without waiting for your approval. Use with caution.
                    </div>
                )}
            </section>

            {/* Provider */}
            <section className="hcode-settings-section">
                <h2>AI Provider</h2>
                <select
                    className="hcode-select"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                >
                    <option value="auto">Auto (best available)</option>
                    <option value="openai">OpenAI (GPT)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                    <option value="cerebras">Cerebras</option>
                </select>
            </section>

            {/* API Keys */}
            <section className="hcode-settings-section">
                <h2>API Keys</h2>
                <p className="hcode-hint">Keys are stored securely in VS Code's encrypted secret storage (OS keychain). They are never sent anywhere except the selected AI provider.</p>
                {(['openai', 'anthropic', 'cerebras'] as Provider[]).map((p) => (
                    <div key={p} className="hcode-key-row">
                        <label className="hcode-label">{p.charAt(0).toUpperCase() + p.slice(1)} API Key</label>
                        <div className="hcode-key-input-row">
                            <input
                                type="password"
                                className="hcode-input"
                                placeholder={`Enter ${p} key...`}
                                value={keys[p]}
                                onChange={(e) => setKeys((prev) => ({ ...prev, [p]: e.target.value }))}
                            />
                            <button
                                className="hcode-btn hcode-btn--secondary"
                                onClick={() => saveKey(p)}
                                disabled={!keys[p]}
                            >
                                {saved[p] ? '✅ Saved' : 'Save'}
                            </button>
                        </div>
                    </div>
                ))}
            </section>
        </div>
    );
}
