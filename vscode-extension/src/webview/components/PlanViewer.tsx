import React, { useState } from 'react';
import { marked } from 'marked';

interface Props {
    markdown: string;
    onApprove: () => void;
    onReject: (comment: string) => void;
    disabled?: boolean;
}

export default function PlanViewer({ markdown, onApprove, onReject, disabled }: Props) {
    const [comment, setComment] = useState('');
    const [showReject, setShowReject] = useState(false);

    const html = marked.parse(markdown) as string;

    return (
        <section className="hcode-card hcode-plan-viewer">
            <h2 className="hcode-card-title">📋 Implementation Plan</h2>
            <div
                className="hcode-markdown"
                dangerouslySetInnerHTML={{ __html: html }}
            />
            {!disabled && (
                <div className="hcode-plan-actions">
                    <button
                        className="hcode-btn hcode-btn--success"
                        onClick={onApprove}
                    >
                        ✅ Approve Plan
                    </button>
                    <button
                        className="hcode-btn hcode-btn--secondary"
                        onClick={() => setShowReject(!showReject)}
                    >
                        ✏️ Request Changes
                    </button>
                </div>
            )}
            {showReject && (
                <div className="hcode-reject-form">
                    <textarea
                        className="hcode-textarea"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Describe what you'd like changed..."
                        rows={3}
                    />
                    <button
                        className="hcode-btn hcode-btn--warning"
                        onClick={() => { onReject(comment); setShowReject(false); setComment(''); }}
                        disabled={!comment.trim()}
                    >
                        Send Feedback
                    </button>
                </div>
            )}
        </section>
    );
}
