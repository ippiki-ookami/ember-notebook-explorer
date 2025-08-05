import * as vscode from 'vscode';
import { GraphPanel } from './graphPanel';
import { WalkthroughPanel } from './walkthroughPanel';
import { NotebookParser } from './notebookParser';
import { NotebookOutlineProvider, NotebookOutlineTreeItem } from './notebookOutlineView';
import { CodeNode } from './notebookParser';
import { HighlightController } from './highlightController';
import { execFile } from 'child_process';
import * as path from 'path';
import { GraphData, EmberOutput } from './notebookParser';

async function loadGraphFromEmber(notebookPath: string): Promise<EmberOutput> {
    return new Promise((resolve, reject) => {
        const script = path.join(__dirname, '..', 'ember.py');
        
        // Try to find python in venv first, fallback to system python
        const venvPython = path.join(__dirname, '..', '.venv', 'bin', 'python');
        const pythonCmd = require('fs').existsSync(venvPython) ? venvPython : 'python3';
        
        // Add --no-cache flag if you want to force fresh analysis
        const args = [script, notebookPath, '--export-json'];
        
        // Check VS Code configuration for cache setting
        const config = vscode.workspace.getConfiguration('emberNotebook');
        if (config.get<boolean>('disableCache', false)) {
            args.push('--no-cache');
        }
        
        execFile(pythonCmd, args, 
            { maxBuffer: 10 * 1024 * 1024 },
            (err, stdout, stderr) => {
                if (err) {
                    console.error('ember.py error:', stderr);
                    return reject(new Error(`ember.py failed: ${stderr || err.message}`));
                }
                try {
                    const json = JSON.parse(stdout);
                    // Handle both old format (direct GraphData) and new format (EmberOutput)
                    if (json.graph) {
                        resolve(json as EmberOutput);
                    } else {
                        // Old format - wrap in EmberOutput
                        resolve({ graph: json as GraphData, phases: [] });
                    }
                } catch (e) {
                    reject(new Error("Failed to parse ember.py JSON: " + e));
                }
            }
        );
    });
}

async function loadWalkthroughFromEmber(notebookPath: string): Promise<{content: string, components: any[]}> {
    return new Promise((resolve, reject) => {
        const fs = require('fs');
        
        // First, try to find an existing walkthrough file
        const baseName = path.basename(notebookPath, '.ipynb');
        const dir = path.dirname(notebookPath);
        const walkthroughPath = path.join(dir, `${baseName}_walkthrough.md`);
        
        if (fs.existsSync(walkthroughPath)) {
            try {
                const content = fs.readFileSync(walkthroughPath, 'utf8');
                // Extract components from the content (simplified - could be improved)
                const components: any[] = [];
                const componentMatches = content.matchAll(/\[\[component:(\d+):(\d+):([^|]+)\|([^\]]+)\]\]/g);
                for (const match of componentMatches) {
                    components.push({
                        id: match[3],
                        name: match[4],
                        cellIndex: parseInt(match[1]),
                        lineInCell: parseInt(match[2])
                    });
                }
                resolve({ content, components });
            } catch (e) {
                reject(new Error(`Failed to read walkthrough file: ${e}`));
            }
        } else {
            // If no walkthrough file exists, try to generate one using ember.py
            // For now, return a placeholder
            resolve({
                content: `# Walkthrough for ${baseName}\n\nNo walkthrough available yet. Generate one using the ember analysis pipeline.`,
                components: []
            });
        }
    });
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Ember Notebook Explorer is now active!');
    vscode.window.showInformationMessage('Ember Notebook Explorer activated!');
    
    // Create a status bar item to show the extension is active
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.text = "$(notebook) Ember Active";
    statusBar.tooltip = "Ember Notebook Explorer is active";
    statusBar.show();
    context.subscriptions.push(statusBar);

    // Create the centralized highlight controller
    const highlightController = new HighlightController(context);
    
    // Create the tree data provider with context
    const outlineProvider = new NotebookOutlineProvider(context);
    
    // Register the tree view
    const treeView = vscode.window.createTreeView('emberNotebookOutline', {
        treeDataProvider: outlineProvider,
        showCollapseAll: true
    });
    
    context.subscriptions.push(treeView);
    
    // Register reveal command
    context.subscriptions.push(
        vscode.commands.registerCommand('emberNotebookOutline.reveal', async (node: CodeNode) => {
            // Try to get notebook from multiple sources
            let notebookDocument: vscode.NotebookDocument | undefined;
            
            // First try active notebook editor
            if (vscode.window.activeNotebookEditor) {
                notebookDocument = vscode.window.activeNotebookEditor.notebook;
            }
            
            // If no active notebook, try to find the notebook that contains this node
            if (!notebookDocument) {
                // Get from the outline provider's active notebook
                const providerNotebook = outlineProvider.getActiveNotebook();
                if (providerNotebook) {
                    notebookDocument = providerNotebook;
                }
            }
            
            // If no notebook from outline provider, try graph panel
            if (!notebookDocument && GraphPanel.currentPanel) {
                notebookDocument = GraphPanel.currentPanel.getNotebookDocument();
            }
            
            // If still no notebook, try to find any open .ipynb
            if (!notebookDocument) {
                for (const doc of vscode.workspace.notebookDocuments) {
                    if (doc.uri.fsPath.endsWith('.ipynb')) {
                        notebookDocument = doc;
                        break;
                    }
                }
            }
            
            if (notebookDocument && node.cellIndex !== undefined) {
                // Use the highlight controller for navigation and highlighting
                await highlightController.navigateAndHighlight(
                    notebookDocument,
                    node.cellIndex,
                    node.lineInCell
                );
                
                // Highlight in graph panel
                if (GraphPanel.currentPanel) {
                    GraphPanel.currentPanel.highlightNodeById(node.id);
                }
                
                // Highlight in walkthrough panel
                if (WalkthroughPanel.currentPanel) {
                    WalkthroughPanel.currentPanel.highlightComponent(node.id);
                }
                
                // Select in tree view (but don't steal focus from notebook)
                // Add a small delay to ensure tree view is ready
                setTimeout(async () => {
                    try {
                        // First ensure parent nodes are expanded
                        if (node.type !== 'cell') {
                            // Find and expand the parent cell first
                            const parentCell = outlineProvider.findNodeById(`cell_${node.cellIndex}`);
                            if (parentCell) {
                                await treeView.reveal(parentCell, { select: false, focus: false, expand: 3 });
                            }
                        }
                        
                        // Then reveal the actual node
                        await treeView.reveal(node, { select: true, focus: false, expand: true });
                    } catch (error) {
                        console.log('TreeView reveal error:', error);
                        // Try finding the node by ID and revealing again
                        const foundNode = outlineProvider.findNodeById(node.id);
                        if (foundNode) {
                            await treeView.reveal(foundNode, { select: true, focus: false, expand: true });
                        }
                    }
                }, 150);
            } else {
                vscode.window.showErrorMessage('No notebook found to navigate to');
            }
        })
    );

    // Listen for notebook selection changes
    context.subscriptions.push(
        vscode.window.onDidChangeNotebookEditorSelection(e => {
            if (!GraphPanel.currentPanel || !outlineProvider) return;
            
            const selections = e.selections;
            if (selections.length === 0) return;
            
            const cellIndex = selections[0].start;
            
            // Get the active cell's text editor to find cursor position
            const cell = e.notebookEditor.notebook.cellAt(cellIndex);
            if (cell.kind !== vscode.NotebookCellKind.Code) return;
            
            // Try to find active text editor for this cell
            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor && activeEditor.document.uri.toString() === cell.document.uri.toString()) {
                const position = activeEditor.selection.active;
                const lineInCell = position.line;
                
                // Find matching node
                const node = outlineProvider.findNodeByPosition(cellIndex, lineInCell);
                if (node) {
                    GraphPanel.currentPanel.highlightNodeById(node.id);
                    treeView.reveal(node, { select: true, focus: false });
                    
                    // Also highlight in walkthrough panel
                    if (WalkthroughPanel.currentPanel) {
                        WalkthroughPanel.currentPanel.highlightComponent(node.id);
                    }
                }
            }
        })
    );

    let disposable = vscode.commands.registerCommand('ember.showGraph', async () => {
        // Try to get active notebook first
        const activeNotebook = vscode.window.activeNotebookEditor;
        if (activeNotebook) {
            try {
                // Use ember.py to parse the notebook
                const notebookPath = activeNotebook.notebook.uri.fsPath;
                const emberOutput = await loadGraphFromEmber(notebookPath);
                
                // Show graph panel with notebook reference
                GraphPanel.createOrShow(context.extensionUri, emberOutput, activeNotebook.notebook);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to parse notebook: ${error}`);
            }
            return;
        }
        
        // Fallback to text editor (for .ipynb opened as JSON)
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            // Try to find an open .ipynb file
            const notebookEditors = vscode.window.visibleTextEditors.filter(
                editor => editor.document.fileName.endsWith('.ipynb')
            );
            
            if (notebookEditors.length === 0) {
                vscode.window.showErrorMessage('Please open a Jupyter notebook (.ipynb file)');
                return;
            }
            
            // Use the first found notebook
            const document = notebookEditors[0].document;
            try {
                // For text editors showing .ipynb, we need to save temporarily or use the file path
                const notebookPath = document.uri.fsPath;
                const emberOutput = await loadGraphFromEmber(notebookPath);
                
                // Show graph panel (outline is already in sidebar)
                GraphPanel.createOrShow(context.extensionUri, emberOutput);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to parse notebook: ${error}`);
            }
            return;
        }

        const document = activeEditor.document;
        
        if (!document.fileName.endsWith('.ipynb')) {
            vscode.window.showErrorMessage('Please open a Jupyter notebook (.ipynb file)');
            return;
        }

        try {
            const notebookPath = document.uri.fsPath;
            const emberOutput = await loadGraphFromEmber(notebookPath);
            
            // Show graph panel (outline is already in sidebar)
            GraphPanel.createOrShow(context.extensionUri, emberOutput);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to parse notebook: ${error}`);
        }
    });

    context.subscriptions.push(disposable);

    // Register walkthrough command
    const walkthroughDisposable = vscode.commands.registerCommand('ember.showWalkthrough', async () => {
        // Try to get active notebook first
        const activeNotebook = vscode.window.activeNotebookEditor;
        if (activeNotebook) {
            try {
                // Load walkthrough for the notebook
                const notebookPath = activeNotebook.notebook.uri.fsPath;
                const walkthroughData = await loadWalkthroughFromEmber(notebookPath);
                
                // Show walkthrough panel with notebook reference
                WalkthroughPanel.createOrShow(context.extensionUri, walkthroughData, activeNotebook.notebook);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to load walkthrough: ${error}`);
            }
            return;
        }
        
        // Fallback to text editor (for .ipynb opened as JSON)
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            // Try to find an open .ipynb file
            const notebookEditors = vscode.window.visibleTextEditors.filter(
                editor => editor.document.fileName.endsWith('.ipynb')
            );
            
            if (notebookEditors.length === 0) {
                vscode.window.showErrorMessage('Please open a Jupyter notebook (.ipynb file)');
                return;
            }
            
            // Use the first found notebook
            const document = notebookEditors[0].document;
            try {
                const notebookPath = document.uri.fsPath;
                const walkthroughData = await loadWalkthroughFromEmber(notebookPath);
                
                // Show walkthrough panel
                WalkthroughPanel.createOrShow(context.extensionUri, walkthroughData);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to load walkthrough: ${error}`);
            }
            return;
        }

        const document = activeEditor.document;
        
        if (!document.fileName.endsWith('.ipynb')) {
            vscode.window.showErrorMessage('Please open a Jupyter notebook (.ipynb file)');
            return;
        }

        try {
            const notebookPath = document.uri.fsPath;
            const walkthroughData = await loadWalkthroughFromEmber(notebookPath);
            
            // Show walkthrough panel
            WalkthroughPanel.createOrShow(context.extensionUri, walkthroughData);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to load walkthrough: ${error}`);
        }
    });

    context.subscriptions.push(walkthroughDisposable);
}

export function deactivate() {}