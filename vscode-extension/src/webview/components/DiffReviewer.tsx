import React, { useEffect, useRef, useState } from 'react';
import * as monaco from 'monaco-editor';
import { FilePatchPayload } from '../types';

interface Props {
    patches: FilePatchPayload[];
    onFileDecision: (path: string, accepted: boolean) => void;
    onRollback: () => void;
}

export default function DiffReviewer({ patches, onFileDecision, onRollback }: Props) {
    const [selected, setSelected] = useState<number>(0);
    const [decisions, setDecisions] = useState<Record<string, boolean | null>>({});
    const editorRef = useRef<HTMLDivElement>(null);
    const diffEditorRef = useRef<monaco.editor.IStandaloneDiffEditor | null>(null);

    const patch = patches[selected];

    useEffect(() => {
        if (!editorRef.current || !patch) return;

        if (diffEditorRef.current) {
            diffEditorRef.current.dispose();
        }

        diffEditorRef.current = monaco.editor.createDiffEditor(editorRef.current, {
            readOnly: true,
            theme: document.body.classList.contains('vscode-dark') ? 'vs-dark' : 'vs',
            renderSideBySide: true,
            automaticLayout: true,
            minimap: { enabled: false },
        });

        const originalModel = monaco.editor.createModel(patch.originalContent || '', undefined, monaco.Uri.parse(`original://${patch.path}`));
        const modifiedModel = monaco.editor.createModel(patch.newContent || '', undefined, monaco.Uri.parse(`modified://${patch.path}`));

        diffEditorRef.current.setModel({ original: originalModel, modified: modifiedModel });

        return () => {
            originalModel.dispose();
            modifiedModel.dispose();
        };
    }, [patch]);

    const decide = (path: string, accepted: boolean) => {
        setDecisions((prev) => ({ ...prev, [path]: accepted }));
        onFileDecision(path, accepted);
    };

    const allDecided = patches.every((p) => decisions[p.path] !== undefined);

    return (
        <section className="hcode-card hcode-diff-reviewer">
            <h2 className="hcode-card-title">🔍 File Changes</h2>

            {/* File list */}
            <div className="hcode-file-list">
                {patches.map((p, i) => {
                    const d = decisions[p.path];
                    return (
                        <button
                            key={p.path}
                            className={`hcode-file-tab ${i === selected ? 'hcode-file-tab--active' : ''} ${d === true ? 'hcode-file-tab--accepted' : d === false ? 'hcode-file-tab--rejected' : ''}`}
                            onClick={() => setSelected(i)}
                        >
                            {d === true ? '✅' : d === false ? '❌' : '📄'} {p.path.split('/').pop()}
                        </button>
                    );
                })}
            </div>

            {/* Monaco diff editor */}
            <div ref={editorRef} className="hcode-diff-editor" style={{ height: 400 }} />

            {/* Per-file actions */}
            {patch && decisions[patch.path] === undefined && (
                <div className="hcode-diff-actions">
                    <button className="hcode-btn hcode-btn--success" onClick={() => decide(patch.path, true)}>✅ Accept</button>
                    <button className="hcode-btn hcode-btn--danger" onClick={() => decide(patch.path, false)}>❌ Reject</button>
                </div>
            )}

            {/* Rollback */}
            <div className="hcode-diff-footer">
                <button className="hcode-btn hcode-btn--secondary" onClick={onRollback}>🔄 Rollback All</button>
                {allDecided && <span className="hcode-hint">All files reviewed.</span>}
            </div>
        </section>
    );
}
