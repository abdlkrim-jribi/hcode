import React from 'react';
import { ChatMessage, PHASE_CONFIGS, AgentPhase } from '../types';

interface Props {
    messages: ChatMessage[];
    agentPhase: AgentPhase;
}

export default function AgentChat({ messages, agentPhase }: Props) {
    const bottomRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    if (messages.length === 0) {
        return (
            <div className="hcode-chat-empty">
                <div className="hcode-chat-empty__icon">⚡</div>
                <p>How can Hcode help you today?</p>
                <p className="hcode-chat-empty__sub">Configure context below and describe your task.</p>
            </div>
        );
    }

    return (
        <div className="hcode-agent-chat">
            {messages.map(msg => {
                const phaseConfig = msg.phase ? PHASE_CONFIGS[msg.phase] : null;
                return (
                    <div
                        key={msg.id}
                        className={`hcode-chat-msg hcode-chat-msg--${msg.type}`}
                        data-phase={msg.phase}
                    >
                        {msg.type === 'agent_phase' && phaseConfig && (
                            <div className="hcode-chat-phase-banner" style={{ '--phase-color': `var(${phaseConfig.cssVar})` } as React.CSSProperties}>
                                <span className="hcode-chat-phase-emoji">{phaseConfig.emoji}</span>
                                <span className="hcode-chat-phase-label">{phaseConfig.label}</span>
                                <div className="hcode-chat-phase-line" />
                            </div>
                        )}
                        {msg.type !== 'agent_phase' && (
                            <div className="hcode-chat-bubble">
                                {msg.type === 'user' && (
                                    <div className="hcode-chat-bubble__user">
                                        <span className="hcode-chat-bubble__content">{msg.content}</span>
                                        <span className="hcode-chat-bubble__time">{msg.timestamp}</span>
                                    </div>
                                )}
                                {(msg.type === 'agent_thought' || msg.type === 'agent_output' || msg.type === 'system') && (
                                    <div className={`hcode-chat-bubble__agent hcode-chat-bubble__agent--${msg.type}`}>
                                        {phaseConfig && (
                                            <span className="hcode-chat-bubble__phase-dot" style={{ background: `var(${phaseConfig.cssVar})` }} />
                                        )}
                                        <span className="hcode-chat-bubble__content hcode-markdown"
                                            dangerouslySetInnerHTML={{ __html: msg.content }}
                                        />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
            <div ref={bottomRef} />
        </div>
    );
}
