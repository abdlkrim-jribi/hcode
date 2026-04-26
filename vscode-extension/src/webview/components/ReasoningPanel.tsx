import React, { useState, useRef, useEffect } from 'react';
import { AgentPhase } from '../types';

interface Props {
    thoughts: string;
    agentPhase: AgentPhase;
    renderedHtml: string | null;
}

export default function ReasoningPanel({ thoughts, agentPhase, renderedHtml }: Props) {
    // Default: collapsed in fast/executing, open when actively thinking/planning
    const [isOpen, setIsOpen] = useState(false);
    const contentRef = useRef<HTMLDivElement>(null);

    // Auto-open during thinking/planning
    useEffect(() => {
        if (agentPhase === 'thinking' || agentPhase === 'planning') {
            setIsOpen(true);
        }
    }, [agentPhase]);

    if (!thoughts) return null;

    const preview = thoughts.replace(/[#*`]/g, '').slice(0, 80) + (thoughts.length > 80 ? '…' : '');

    return (
        <div className={`hcode-reasoning-panel ${isOpen ? 'hcode-reasoning-panel--open' : ''}`}>
            <button
                className="hcode-reasoning-header"
                onClick={() => setIsOpen(o => !o)}
                aria-expanded={isOpen}
            >
                <div className="hcode-reasoning-header__left">
                    <span className="hcode-spinner-mini hcode-reasoning-spinner" />
                    <span className="hcode-reasoning-title">Agent Reasoning</span>
                </div>
                <div className="hcode-reasoning-header__right">
                    {!isOpen && <span className="hcode-reasoning-preview">{preview}</span>}
                    <span className="hcode-reasoning-chevron">{isOpen ? '▲' : '▼'}</span>
                </div>
            </button>
            <div
                className="hcode-reasoning-body"
                ref={contentRef}
                style={{ maxHeight: isOpen ? '360px' : '0' }}
            >
                {renderedHtml && (
                    <div
                        className="hcode-thoughts-content hcode-markdown"
                        dangerouslySetInnerHTML={{ __html: renderedHtml }}
                    />
                )}
            </div>
        </div>
    );
}
