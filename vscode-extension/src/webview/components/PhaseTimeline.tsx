import React from 'react';
import { AgentPhase } from '../types';

interface Props {
    agentPhase: AgentPhase;
}

const PHASES: { key: AgentPhase; label: string }[] = [
    { key: 'planning', label: 'Plan' },
    { key: 'executing', label: 'Execute' },
    { key: 'verifying', label: 'Verify' },
];

const PHASE_ORDER: AgentPhase[] = ['thinking', 'planning', 'executing', 'verifying', 'done'];

function getPhaseIndex(p: AgentPhase): number {
    return PHASE_ORDER.indexOf(p);
}

export default function PhaseTimeline({ agentPhase }: Props) {
    if (agentPhase === 'idle' || agentPhase === 'error') return null;

    const currentIdx = getPhaseIndex(agentPhase);

    return (
        <div className="hcode-phase-timeline" data-phase={agentPhase}>
            {PHASES.map((step, i) => {
                const stepIdx = getPhaseIndex(step.key);
                const isActive = agentPhase === step.key;
                const isDone = currentIdx > stepIdx || agentPhase === 'done';
                const status = isDone ? 'done' : isActive ? 'active' : 'pending';
                return (
                    <React.Fragment key={step.key}>
                        <div className={`hcode-phase-step hcode-phase-step--${status}`}>
                            <div className="hcode-phase-dot">
                                {isDone ? '✓' : isActive ? <span className="hcode-phase-pulse" /> : null}
                            </div>
                            <span className="hcode-phase-label">{step.label}</span>
                        </div>
                        {i < PHASES.length - 1 && (
                            <div className={`hcode-phase-connector ${isDone ? 'hcode-phase-connector--done' : ''}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}
