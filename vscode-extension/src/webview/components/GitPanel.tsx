import React, { useEffect, useState } from 'react';

interface Props {
    branch: string;
    staging: string;
    post: (msg: object) => void;
}

export default function GitPanel({ branch, staging, post }: Props) {
    const [showStaging, setShowStaging] = useState(false);
    const [commitMsg, setCommitMsg] = useState('');
    const [committing, setCommitting] = useState(false);

    useEffect(() => {
        post({ type: 'get_git_info' });
    }, []);

    const handleCommit = () => {
        if (!commitMsg.trim()) return;
        setCommitting(true);
        post({ type: 'git_commit', message: commitMsg });
        setCommitMsg('');
        setTimeout(() => setCommitting(false), 2000);
    };

    return (
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
            <span
                style={{
                    fontSize: 'var(--text-2xs)',
                    color: 'var(--fg-secondary)',
                    cursor: 'pointer',
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    userSelect: 'none'
                }}
                onClick={() => setShowStaging(!showStaging)}
            >
                {branch || 'no-branch'}
            </span>
            {showStaging && (
                <div style={{
                    position: 'absolute',
                    right: 0,
                    top: '24px',
                    width: '320px',
                    background: 'var(--surface-2)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-3)',
                    zIndex: 100,
                    boxShadow: 'var(--shadow-lg)'
                }}>
                    <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--fg-secondary)', marginBottom: 'var(--space-2)' }}>MODIFIED FILES</div>
                    <pre style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--text-xs)',
                        color: 'var(--fg-secondary)',
                        whiteSpace: 'pre-wrap',
                        maxHeight: '150px',
                        overflowY: 'auto',
                        marginBottom: 'var(--space-3)',
                        padding: 'var(--space-2)',
                        background: 'var(--surface-0)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)'
                    }}>{staging || 'Working tree clean'}</pre>
                    <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <input
                            className="hcode-input"
                            placeholder="Commit message..."
                            value={commitMsg}
                            onChange={(e) => setCommitMsg(e.target.value)}
                        />
                        <button
                            className="hcode-btn hcode-btn--secondary"
                            onClick={handleCommit}
                            disabled={committing || !commitMsg.trim()}
                        >
                            {committing ? '...' : 'Commit'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
