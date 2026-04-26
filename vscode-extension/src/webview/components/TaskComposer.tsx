import React, { useState, useRef, useEffect } from 'react';
import { ContextOptions, DEFAULT_CONTEXT_OPTIONS } from '../types';

interface Props {
    onSubmit: (task: string, context: ContextOptions) => void;
    disabled?: boolean;
    initialTask?: string;
}

export default function TaskComposer({ onSubmit, disabled, initialTask }: Props) {
    const [task, setTask] = useState(initialTask || '');
    const [mode, setMode] = useState<'planning' | 'fast'>('planning');
    // Context option keeping logic for future usage, defaulting for now
    const [context, setContext] = useState<ContextOptions>(DEFAULT_CONTEXT_OPTIONS);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [task]);

    useEffect(() => {
        if (initialTask) setTask(initialTask);
    }, [initialTask]);

    const handleSubmit = () => {
        const trimmed = task.trim();
        if (!trimmed || disabled) return;
        const prefix = mode === 'planning' ? '/plan ' : '/fast ';
        onSubmit(prefix + trimmed, context);
        setTask('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Support Ctrl+Enter or Cmd+Enter for submit
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="hcode-composer" data-disabled={disabled}>
            <div className="hcode-composer__input-wrapper">
                <textarea
                    ref={textareaRef}
                    className="hcode-composer__input"
                    value={task}
                    onChange={(e) => setTask(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe your task..."
                    disabled={disabled}
                    rows={1}
                />
            </div>

            <div className="hcode-composer-controls" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-2)' }}>
                <div className="hcode-composer-mode" style={{ display: 'flex', gap: '2px', background: 'var(--surface-2)', padding: '2px', borderRadius: 'var(--radius-xs)' }}>
                    <button
                        className={`hcode-mode-btn ${mode === 'planning' ? 'is-active' : ''}`}
                        onClick={() => setMode('planning')}
                        disabled={disabled}
                    >
                        Plan
                    </button>
                    <button
                        className={`hcode-mode-btn ${mode === 'fast' ? 'is-active' : ''}`}
                        onClick={() => setMode('fast')}
                        disabled={disabled}
                    >
                        Fast
                    </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--fg-tertiary)' }}>
                        Ctrl+Enter to send
                    </div>
                </div>
            </div>
        </div>
    );
}
