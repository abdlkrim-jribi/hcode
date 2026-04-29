import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    root: path.resolve(__dirname, 'src/webview'),
    build: {
        outDir: path.resolve(__dirname, 'webview_build'),
        emptyOutDir: true,
        // Use lib mode with IIFE — VS Code webviews cannot use type="module" with CSP nonces
        lib: {
            entry: path.resolve(__dirname, 'src/webview/main.tsx'),
            name: 'HcodeWebview',
            formats: ['iife'],
            fileName: () => 'webview.js',
        },
        rollupOptions: {
            output: {
                assetFileNames: '[name].[ext]',
                // Inline all dynamic imports into the main bundle
                inlineDynamicImports: true,
            },
        },
        cssCodeSplit: false,
    },
    define: {
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    },
});
