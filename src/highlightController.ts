import * as vscode from 'vscode';

export class HighlightController {
    private ignoreSelection = false;
    private clearTimer?: NodeJS.Timeout;
    private decoration: vscode.TextEditorDecorationType;
    
    constructor(context: vscode.ExtensionContext) {
        // Create decoration type
        this.decoration = vscode.window.createTextEditorDecorationType({
            isWholeLine: true,
            backgroundColor: new vscode.ThemeColor('editor.lineHighlightBackground'),
            borderColor: new vscode.ThemeColor('editor.lineHighlightBorder'),
            borderWidth: '1px',
            borderStyle: 'solid'
        });
        
        // Single subscription for selection changes
        context.subscriptions.push(
            vscode.window.onDidChangeTextEditorSelection(e => {
                if (this.ignoreSelection) return;
                this.clearAll();
            })
        );
        
        // Dispose decoration on deactivate
        context.subscriptions.push(this.decoration);
    }
    
    public async navigateAndHighlight(
        notebookDocument: vscode.NotebookDocument,
        cellIndex: number,
        lineInCell: number
    ) {
        // 1) Suppress clears until we're done
        this.ignoreSelection = true;
        
        try {
            // 2) Show the notebook and navigate to cell
            const nbEditor = await vscode.window.showNotebookDocument(
                notebookDocument,
                { viewColumn: vscode.ViewColumn.One }
            );
            
            // 3) Reveal and select the cell
            nbEditor.revealRange(
                new vscode.NotebookRange(cellIndex, cellIndex),
                vscode.NotebookEditorRevealType.InCenter
            );
            nbEditor.selections = [new vscode.NotebookRange(cellIndex, cellIndex)];
            
            // 4) If specific line, open cell document and highlight
            if (lineInCell >= 0) {
                const cell = nbEditor.notebook.cellAt(cellIndex);
                if (cell.kind === vscode.NotebookCellKind.Code) {
                    const editor = await vscode.window.showTextDocument(
                        cell.document,
                        { 
                            viewColumn: vscode.ViewColumn.One,
                            preserveFocus: false,
                            preview: false
                        }
                    );
                    
                    const position = new vscode.Position(lineInCell, 0);
                    editor.selection = new vscode.Selection(position, position);
                    editor.revealRange(
                        new vscode.Range(position, position),
                        vscode.TextEditorRevealType.InCenter
                    );
                    
                    // Apply the decoration
                    editor.setDecorations(this.decoration, [new vscode.Range(position, position)]);
                }
            }
        } finally {
            // 5) Re-enable selection events after a tick
            setTimeout(() => {
                this.ignoreSelection = false;
            }, 50);
        }
    }
    
    public clearAll() {
        // Clear any pending timer
        if (this.clearTimer) {
            clearTimeout(this.clearTimer);
        }
        
        // Debounce the clear to avoid flicker
        this.clearTimer = setTimeout(() => {
            for (const editor of vscode.window.visibleTextEditors) {
                editor.setDecorations(this.decoration, []);
            }
        }, 50);
    }
    
    public dispose() {
        if (this.clearTimer) {
            clearTimeout(this.clearTimer);
        }
        this.clearAll();
    }
}