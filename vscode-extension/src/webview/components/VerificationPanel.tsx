import React from 'react';
import { marked } from 'marked';

interface Props {
    markdown: string;
    passed: boolean;
    onRollback: () => void;
}

export default function VerificationPanel({ markdown, passed, onRollback }: Props) {
    const html = marked.parse(markdown) as string;

    return (
        <section className={`hcode-card hcode-verification ${passed ? 'hcode-verification--pass' : 'hcode-verification--fail'}`}>
            <h2 className="hcode-card-title">
                {passed ? '✅ Verification Passed' : '❌ Verification Failed'}
            </h2>
            <div className="hcode-markdown" dangerouslySetInnerHTML={{ __html: html }} />
            {!passed && (
                <div className="hcode-verification-actions">
                    <p className="hcode-hint">Verification failed. You can rollback all changes.</p>
                    <button className="hcode-btn hcode-btn--danger" onClick={onRollback}>🔄 Rollback</button>
                </div>
            )}
        </section>
    );
}
