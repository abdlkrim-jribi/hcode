import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './app';
import './styles/tokens.css';
import './styles/global.css';

const root = document.getElementById('root')!;
const mode = root.getAttribute('data-mode') ?? 'run';

createRoot(root).render(<App mode={mode as 'run' | 'chat' | 'settings' | 'sidebar' | 'history'} />);
