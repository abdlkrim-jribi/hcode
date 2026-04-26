import React from 'react';
import { ContextOptions } from '../types';

interface Props {
    options: ContextOptions;
    onChange: (options: ContextOptions) => void;
    disabled?: boolean;
}

const TOGGLES: { key: keyof ContextOptions; label: string; icon: string }[] = [
    { key: 'activeFile', label: 'File', icon: '📄' },
    { key: 'selection', label: 'Selection', icon: '✂️' },
    { key: 'folder', label: 'Folder', icon: '📁' },
    { key: 'gitDiff', label: 'Git diff', icon: '±' },
];

export default function ContextSelector({ options, onChange, disabled }: Props) {
    const toggle = (key: keyof ContextOptions) => {
        if (disabled) return;
        onChange({ ...options, [key]: !options[key] });
    };

    return (
        <div className="hcode-context-selector">
            <span className="hcode-context-label">ctx:</span>
            {TOGGLES.map(t => (
                <button
                    key={t.key}
                    className={`hcode-context-pill ${options[t.key] ? 'hcode-context-pill--on' : ''}`}
                    onClick={() => toggle(t.key)}
                    disabled={disabled}
                    title={`Include ${t.label} in context`}
                >
                    <span>{t.icon}</span>
                    {t.label}
                </button>
            ))}
        </div>
    );
}
