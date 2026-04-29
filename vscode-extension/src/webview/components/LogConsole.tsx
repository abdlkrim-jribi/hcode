import React, { useEffect, useRef } from 'react';

interface LogEntry {
    time: string;
    line: string;
    stream: 'stdout' | 'stderr';
}

interface Props {
    logs: LogEntry[];
}

export default function LogConsole({ logs }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <aside className="hcode-log-console">
            <div className="hcode-log-header">
                <span>📟 Output Log</span>
                <span className="hcode-hint">{logs.length} lines</span>
            </div>
            <div className="hcode-log-body">
                {logs.map((entry, i) => (
                    <div
                        key={i}
                        className={`hcode-log-line ${entry.stream === 'stderr' ? 'hcode-log-line--error' : ''}`}
                    >
                        <span className="hcode-log-time">{entry.time}</span>
                        <span className="hcode-log-text">{entry.line}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </aside>
    );
}
