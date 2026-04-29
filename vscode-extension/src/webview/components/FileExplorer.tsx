/**
 * FileExplorer — folder picker + file tree browser.
 * Lets the user select a working directory and browse its contents.
 */
import React, { useState, useEffect, useCallback } from 'react';

interface FileEntry {
    name: string;
    path: string;
    isDirectory: boolean;
    children?: FileEntry[];
}

interface FileExplorerProps {
    workDir: string;
    fileTree: FileEntry[];
    onSelectFolder: () => void;
    onBrowsePath: (path: string) => void;
    onOpenFile: (path: string) => void;
}

// File type → icon mapping
function getIcon(entry: FileEntry): string {
    if (entry.isDirectory) return '📁';
    const ext = entry.name.split('.').pop()?.toLowerCase() ?? '';
    const map: Record<string, string> = {
        py: '🐍', ts: '🔷', tsx: '⚛️', js: '🟡', jsx: '⚛️',
        json: '📋', md: '📝', css: '🎨', html: '🌐',
        txt: '📄', yml: '⚙️', yaml: '⚙️', toml: '⚙️',
        sh: '🔧', bat: '🔧', ps1: '🔧',
        png: '🖼️', jpg: '🖼️', svg: '🖼️', gif: '🖼️',
        gitignore: '🚫', env: '🔒',
    };
    return map[ext] || '📄';
}

function TreeNode({ entry, depth, onBrowse, onOpen }: {
    entry: FileEntry; depth: number;
    onBrowse: (path: string) => void;
    onOpen: (path: string) => void;
}) {
    const [expanded, setExpanded] = useState(false);

    const handleClick = () => {
        if (entry.isDirectory) {
            setExpanded(!expanded);
            if (!expanded) onBrowse(entry.path);
        } else {
            onOpen(entry.path);
        }
    };

    return (
        <div className="hcode-tree-node">
            <div
                className={`hcode-tree-item ${entry.isDirectory ? 'hcode-tree-item--dir' : ''}`}
                style={{ paddingLeft: `${12 + depth * 16}px` }}
                onClick={handleClick}
                title={entry.path}
            >
                {entry.isDirectory && (
                    <span className={`hcode-tree-arrow ${expanded ? 'hcode-tree-arrow--open' : ''}`}>▶</span>
                )}
                <span className="hcode-tree-icon">{getIcon(entry)}</span>
                <span className="hcode-tree-name">{entry.name}</span>
            </div>
            {expanded && entry.children && (
                <div className="hcode-tree-children">
                    {entry.children.map((child) => (
                        <TreeNode
                            key={child.path}
                            entry={child}
                            depth={depth + 1}
                            onBrowse={onBrowse}
                            onOpen={onOpen}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function FileExplorer({ workDir, fileTree, onSelectFolder, onBrowsePath, onOpenFile }: FileExplorerProps) {
    return (
        <div className="hcode-explorer">
            {/* Folder picker header */}
            <div className="hcode-explorer-header">
                <span className="hcode-explorer-title">📂 Explorer</span>
                <button className="hcode-btn hcode-btn--secondary hcode-btn--small" onClick={onSelectFolder}>
                    Open Folder
                </button>
            </div>

            {/* Current working directory */}
            {workDir && (
                <div className="hcode-explorer-workdir" title={workDir}>
                    <span className="hcode-explorer-workdir-label">Working Directory:</span>
                    <span className="hcode-explorer-workdir-path">{workDir}</span>
                </div>
            )}

            {/* File tree */}
            {fileTree.length > 0 ? (
                <div className="hcode-tree">
                    {fileTree.map((entry) => (
                        <TreeNode
                            key={entry.path}
                            entry={entry}
                            depth={0}
                            onBrowse={onBrowsePath}
                            onOpen={onOpenFile}
                        />
                    ))}
                </div>
            ) : (
                <div className="hcode-explorer-empty">
                    {workDir
                        ? 'Loading files...'
                        : 'No folder selected. Click "Open Folder" to get started.'}
                </div>
            )}
        </div>
    );
}
