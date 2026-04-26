import React from 'react';
import { TaskEntry } from '../types';

interface Props {
    history: TaskEntry[];
    onReplay: (task: string, mode: 'planning' | 'fast') => void;
}

function formatTime(ts: string): string {
    return new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function TaskHistory({ history, onReplay }: Props) {
    if (history.length === 0) {
        return (
            <div className="hcode-history-empty">
                <div className="hcode-history-empty__icon">🕐</div>
                <p>No task history yet.</p>
                <p className="hcode-history-empty__sub">Completed tasks will appear here.</p>
            </div>
        );
    }

    return (
        <div className="hcode-task-history">
            {history.map((entry, i) => (
                <div key={entry.id} className={`hcode-history-entry hcode-history-entry--${entry.outcome}`}>
                    <div className="hcode-history-entry__connector">
                        <div className="hcode-history-dot" />
                        {i < history.length - 1 && <div className="hcode-history-line" />}
                    </div>
                    <div className="hcode-history-card">
                        <div className="hcode-history-card__header">
                            <span className="hcode-history-outcome">
                                {entry.outcome === 'success' ? '✅' : entry.outcome === 'error' ? '❌' : '⏹'}
                            </span>
                            <span className="hcode-history-mode">{entry.mode === 'planning' ? '🔵 Plan' : '⚡ Fast'}</span>
                            <span className="hcode-history-time">{formatTime(entry.timestamp)}</span>
                        </div>
                        <p className="hcode-history-task">{entry.task}</p>
                        <div className="hcode-history-phases">
                            {entry.phasesReached.map(p => (
                                <span key={p} className={`hcode-history-phase-chip hcode-history-phase-chip--${p}`}>{p}</span>
                            ))}
                        </div>
                        {entry.modifiedFiles.length > 0 && (
                            <p className="hcode-history-files">
                                {entry.modifiedFiles.length} file{entry.modifiedFiles.length > 1 ? 's' : ''} changed
                            </p>
                        )}
                        <button
                            className="hcode-btn hcode-btn--secondary hcode-history-replay"
                            onClick={() => onReplay(entry.task, entry.mode)}
                        >
                            ↩ Replay
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
