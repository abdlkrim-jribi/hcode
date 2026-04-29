import React from 'react';
import { marked } from 'marked';

interface Props {
    markdown: string;
}

export default function TaskChecklist({ markdown }: Props) {
    const html = marked.parse(markdown) as string;

    return (
        <section className="hcode-card hcode-task-checklist">
            <h2 className="hcode-card-title">✅ Task Progress</h2>
            <div
                className="hcode-markdown hcode-checklist"
                dangerouslySetInnerHTML={{ __html: html }}
            />
        </section>
    );
}
