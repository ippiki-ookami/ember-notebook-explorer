import * as vscode from 'vscode';
import * as path from 'path';

interface WalkthroughData {
    content: string;
    components?: Array<{
        id: string;
        name: string;
        cellIndex: number;
        lineInCell: number;
    }>;
}

export class WalkthroughPanel {
    public static currentPanel: WalkthroughPanel | undefined;
    
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _walkthroughData: WalkthroughData | undefined;
    private _notebookDocument: vscode.NotebookDocument | undefined;
    
    public static createOrShow(extensionUri: vscode.Uri, walkthroughData: WalkthroughData, notebookDocument?: vscode.NotebookDocument) {
        const column = vscode.ViewColumn.Two;
        
        if (WalkthroughPanel.currentPanel) {
            WalkthroughPanel.currentPanel._panel.reveal(column);
            WalkthroughPanel.currentPanel.update(walkthroughData, notebookDocument);
            return;
        }
        
        const panel = vscode.window.createWebviewPanel(
            'emberWalkthrough',
            'Notebook Walkthrough',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );
        
        WalkthroughPanel.currentPanel = new WalkthroughPanel(panel, extensionUri);
        WalkthroughPanel.currentPanel.initializeWalkthrough(walkthroughData, notebookDocument);
    }
    
    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'navigateToComponent':
                        this._handleComponentNavigation(message.componentId, message.cellIndex, message.lineInCell);
                        return;
                }
            },
            null,
            this._disposables
        );
    }
    
    public dispose() {
        WalkthroughPanel.currentPanel = undefined;
        
        this._panel.dispose();
        
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
    
    public update(walkthroughData: WalkthroughData, notebookDocument?: vscode.NotebookDocument) {
        this._walkthroughData = walkthroughData;
        if (notebookDocument) {
            this._notebookDocument = notebookDocument;
        }
        
        // Update the webview content
        this._panel.webview.html = this._getHtmlForWebview(this._panel.webview, walkthroughData);
    }
    
    public initializeWalkthrough(walkthroughData: WalkthroughData, notebookDocument?: vscode.NotebookDocument) {
        this._walkthroughData = walkthroughData;
        if (notebookDocument) {
            this._notebookDocument = notebookDocument;
        }
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview, walkthroughData);
    }
    
    private async _handleComponentNavigation(componentId: string, cellIndex: number, lineInCell: number) {
        if (this._notebookDocument) {
            // Use the same reveal command as the other panels for consistency
            vscode.commands.executeCommand('emberNotebookOutline.reveal', {
                id: componentId,
                cellIndex: cellIndex,
                lineInCell: lineInCell,
                name: componentId,
                type: 'component'
            });
        }
    }
    
    public getNotebookDocument(): vscode.NotebookDocument | undefined {
        return this._notebookDocument;
    }
    
    public highlightComponent(componentId: string): void {
        this._panel.webview.postMessage({
            command: 'highlightComponent',
            componentId: componentId
        });
    }
    
    private _getHtmlForWebview(webview: vscode.Webview, walkthroughData: WalkthroughData) {
        // Process the markdown content to make component links clickable
        const processedContent = this._processComponentLinks(walkthroughData.content, walkthroughData.components || []);
        
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Notebook Walkthrough</title>
            <style>
                html, body {
                    font-family: var(--vscode-font-family);
                    font-size: var(--vscode-font-size);
                    font-weight: var(--vscode-font-weight);
                    margin: 0;
                    padding: 20px;
                    background: var(--vscode-editor-background);
                    color: var(--vscode-editor-foreground);
                    line-height: 1.6;
                }
                
                h1, h2, h3, h4, h5, h6 {
                    color: var(--vscode-editor-foreground);
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    border-bottom: 1px solid var(--vscode-panel-border);
                    padding-bottom: 8px;
                }
                
                h1 {
                    font-size: 2em;
                    border-bottom: 2px solid var(--vscode-panel-border);
                }
                
                h2 {
                    font-size: 1.5em;
                    color: var(--vscode-textLink-foreground);
                }
                
                p {
                    margin-bottom: 16px;
                    line-height: 1.7;
                }
                
                .component-link {
                    color: var(--vscode-textLink-foreground);
                    text-decoration: none;
                    font-weight: 500;
                    border: 1px solid var(--vscode-textLink-foreground);
                    border-radius: 4px;
                    padding: 2px 6px;
                    margin: 0 2px;
                    display: inline-block;
                    font-size: 0.9em;
                    transition: all 0.2s ease;
                }
                
                .component-link:hover {
                    background: var(--vscode-textLink-foreground);
                    color: var(--vscode-editor-background);
                    text-decoration: none;
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                
                .component-link:active {
                    transform: translateY(0px);
                }
                
                .component-link.highlighted {
                    background: var(--vscode-editor-selectionBackground);
                    border-color: var(--vscode-focusBorder);
                    color: var(--vscode-editor-foreground);
                    box-shadow: 0 0 6px var(--vscode-focusBorder);
                    animation: pulse 1s ease-in-out;
                }
                
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                
                .block-link {
                    color: var(--vscode-textPreformat-foreground);
                    text-decoration: none;
                    font-style: italic;
                    border-bottom: 1px dotted var(--vscode-textPreformat-foreground);
                }
                
                .block-link:hover {
                    color: var(--vscode-textLink-activeForeground);
                    text-decoration: none;
                }
                
                code {
                    background: var(--vscode-textCodeBlock-background);
                    color: var(--vscode-textPreformat-foreground);
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: var(--vscode-editor-font-family);
                }
                
                pre {
                    background: var(--vscode-textCodeBlock-background);
                    padding: 16px;
                    border-radius: 6px;
                    overflow-x: auto;
                    border: 1px solid var(--vscode-panel-border);
                }
                
                pre code {
                    background: none;
                    padding: 0;
                }
                
                hr {
                    border: none;
                    border-top: 2px solid var(--vscode-panel-border);
                    margin: 32px 0;
                }
                
                .section {
                    margin-bottom: 32px;
                }
                
                .intro {
                    background: var(--vscode-textBlockQuote-background);
                    border-left: 4px solid var(--vscode-textLink-foreground);
                    padding: 16px;
                    margin: 24px 0;
                    border-radius: 0 4px 4px 0;
                }
                
                .intro p {
                    margin-bottom: 0;
                    font-style: italic;
                }
                
                /* Smooth scrolling for navigation */
                html {
                    scroll-behavior: smooth;
                }
                
                /* Highlight target sections when navigated to */
                :target {
                    animation: highlight 2s ease-in-out;
                }
                
                @keyframes highlight {
                    0% { background-color: var(--vscode-editor-selectionBackground); }
                    100% { background-color: transparent; }
                }
            </style>
        </head>
        <body>
            <div id="walkthrough-content">
                ${processedContent}
            </div>
            
            <script>
                const vscode = acquireVsCodeApi();
                
                // Handle component link clicks
                document.addEventListener('click', function(event) {
                    const target = event.target;
                    if (target.classList.contains('component-link')) {
                        event.preventDefault();
                        const componentId = target.getAttribute('data-component-id');
                        const cellIndex = parseInt(target.getAttribute('data-cell-index') || '0');
                        const lineInCell = parseInt(target.getAttribute('data-line-in-cell') || '0');
                        
                        vscode.postMessage({
                            command: 'navigateToComponent',
                            componentId: componentId,
                            cellIndex: cellIndex,
                            lineInCell: lineInCell
                        });
                    }
                });
                
                // Handle block link clicks (scroll to section)
                document.addEventListener('click', function(event) {
                    const target = event.target;
                    if (target.classList.contains('block-link')) {
                        event.preventDefault();
                        const blockId = target.getAttribute('data-block-id');
                        const element = document.getElementById('block-' + blockId);
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }
                });
                
                // Handle messages from the extension
                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.command) {
                        case 'highlightComponent':
                            // Clear previous highlights
                            document.querySelectorAll('.component-link').forEach(link => {
                                link.classList.remove('highlighted');
                            });
                            
                            // Highlight the target component
                            const targetLinks = document.querySelectorAll(\`[data-component-id="\${message.componentId}"]\`);
                            targetLinks.forEach(link => {
                                link.classList.add('highlighted');
                                // Scroll to the first occurrence
                                if (link === targetLinks[0]) {
                                    link.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }
                            });
                            break;
                    }
                });
            </script>
        </body>
        </html>`;
    }
    
    private _processComponentLinks(content: string, components: Array<{id: string, name: string, cellIndex: number, lineInCell: number}>) {
        // Convert markdown to HTML (basic conversion)
        let html = content;
        
        // Convert headers
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        html = html.replace(/^## (.+)$/gm, '<h2 id="block-$1">$1</h2>');
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        
        // Convert paragraphs
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        
        // Convert horizontal rules
        html = html.replace(/^---$/gm, '<hr>');
        
        // Process component links: [[component:cellIndex:lineInCell:id|display_name]]
        html = html.replace(/\[\[component:(\d+):(\d+):([^|]+)\|([^\]]+)\]\]/g, (match, cellIndex, lineInCell, componentId, displayName) => {
            return `<a href="#" class="component-link" data-component-id="${componentId}" data-cell-index="${cellIndex}" data-line-in-cell="${lineInCell}">${displayName}</a>`;
        });
        
        // Process block links: [[block:id]]
        html = html.replace(/\[\[block:(\d+)\]\]/g, (match, blockId) => {
            return `<a href="#block-${blockId}" class="block-link" data-block-id="${blockId}">Block ${blockId}</a>`;
        });
        
        // Convert **bold** to <strong>
        html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
        
        // Convert `code` to <code>
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Clean up empty paragraphs
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/<p>\s*<\/p>/g, '');
        
        return html;
    }
}