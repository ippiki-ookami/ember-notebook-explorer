import * as vscode from 'vscode';

export interface CodeNode {
    id: string;
    type: 'cell' | 'class' | 'function' | 'import' | 'variable' | 'block' | 'method' | 'expression' | 'decorator';
    name: string;
    content: string;
    cellIndex: number;
    lineInCell: number;
    lineInNotebook: number;
    children: CodeNode[];
    dependencies: string[];
    metadata?: any;
}

export interface Phase {
    phase_id?: string;  // Optional for compatibility
    id?: string;        // Alternative field name
    title?: string;     // Optional for compatibility
    name?: string;      // Alternative field name
    summary: string;
    components: string[];
}

export interface GraphData {
    nodes: CodeNode[];
    edges: Array<{
        source: string;
        target: string;
        type: 'calls' | 'imports' | 'uses' | 'defines';
    }>;
}

export interface EmberOutput {
    graph: GraphData;
    phases: Phase[];
}

export class NotebookParser {
    private nodeId = 0;

    async parseNotebook(notebook: vscode.NotebookDocument): Promise<GraphData> {
        const nodes: CodeNode[] = [];
        const edges: Array<any> = [];
        let absoluteLine = 0;

        for (let cellIndex = 0; cellIndex < notebook.cellCount; cellIndex++) {
            const cell = notebook.cellAt(cellIndex);
            
            if (cell.kind === vscode.NotebookCellKind.Code) {
                const cellNode = this.parseCell(cell, cellIndex, absoluteLine);
                nodes.push(cellNode);
                
                const codeContent = cell.document.getText();
                const childNodes = this.parseCodeStructure(codeContent, cellIndex, absoluteLine);
                cellNode.children = childNodes;
                nodes.push(...this.flattenNodes(childNodes));
            }
            
            // Update absolute line counter (adding 1 for cell boundary)
            absoluteLine += cell.document.lineCount + 1;
        }
        
        this.detectDependencies(nodes, edges);
        
        return { nodes, edges };
    }

    // Legacy method for JSON parsing (backward compatibility)
    async parse(notebookJson: string): Promise<GraphData> {
        const notebook = JSON.parse(notebookJson);
        const nodes: CodeNode[] = [];
        const edges: Array<any> = [];
        let absoluteLine = 0;
        
        if (!notebook.cells) {
            throw new Error('Invalid notebook format');
        }

        for (let i = 0; i < notebook.cells.length; i++) {
            const cell = notebook.cells[i];
            
            if (cell.cell_type === 'code') {
                const codeContent = Array.isArray(cell.source) 
                    ? cell.source.join('') 
                    : cell.source;
                
                const lines = codeContent.split('\n');
                
                const cellNode: CodeNode = {
                    id: `cell_${i}`,
                    type: 'cell',
                    name: `Cell ${i + 1}`,
                    content: codeContent,
                    cellIndex: i,
                    lineInCell: 0,
                    lineInNotebook: absoluteLine,
                    children: [],
                    dependencies: [],
                    metadata: cell.metadata
                };
                nodes.push(cellNode);
                
                const childNodes = this.parseCodeStructure(codeContent, i, absoluteLine);
                cellNode.children = childNodes;
                nodes.push(...this.flattenNodes(childNodes));
                
                absoluteLine += lines.length + 1;
            } else {
                // Still count lines for non-code cells
                const content = Array.isArray(cell.source) ? cell.source.join('') : cell.source;
                absoluteLine += content.split('\n').length + 1;
            }
        }
        
        this.detectDependencies(nodes, edges);
        
        return { nodes, edges };
    }

    private parseCell(cell: vscode.NotebookCell, index: number, absoluteLine: number): CodeNode {
        const content = cell.document.getText();
        
        return {
            id: `cell_${index}`,
            type: 'cell',
            name: `Cell ${index + 1}`,
            content,
            cellIndex: index,
            lineInCell: 0,
            lineInNotebook: absoluteLine,
            children: [],
            dependencies: [],
            metadata: cell.metadata
        };
    }

    private parseCodeStructure(code: string, cellIndex: number, cellStartLine: number): CodeNode[] {
        const nodes: CodeNode[] = [];
        const lines = code.split('\n');
        
        const importRegex = /^(?:from\s+(\S+)\s+)?import\s+(.+)$/;
        const classRegex = /^class\s+(\w+)(?:\s*\(([^)]*)\))?\s*:/;
        const functionRegex = /^def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:/;
        const variableRegex = /^(\w+)\s*=\s*(.+)$/;
        
        let currentIndent = 0;
        let parentStack: CodeNode[] = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            if (!trimmedLine || trimmedLine.startsWith('#')) continue;
            
            const indent = line.search(/\S/);
            if (indent === -1) continue;
            
            while (parentStack.length > 0 && indent <= currentIndent) {
                parentStack.pop();
                currentIndent = parentStack.length > 0 ? 
                    parentStack[parentStack.length - 1].lineInCell || 0 : 0;
            }
            
            let node: CodeNode | null = null;
            
            if (importRegex.test(trimmedLine)) {
                const match = trimmedLine.match(importRegex);
                if (match) {
                    node = {
                        id: `import_${this.nodeId++}`,
                        type: 'import',
                        name: match[1] || match[2],
                        content: trimmedLine,
                        cellIndex,
                        lineInCell: i,
                        lineInNotebook: cellStartLine + i,
                        children: [],
                        dependencies: []
                    };
                }
            } else if (classRegex.test(trimmedLine)) {
                const match = trimmedLine.match(classRegex);
                if (match) {
                    node = {
                        id: `class_${match[1]}_${this.nodeId++}`,
                        type: 'class',
                        name: match[1],
                        content: trimmedLine,
                        cellIndex,
                        lineInCell: i,
                        lineInNotebook: cellStartLine + i,
                        children: [],
                        dependencies: []
                    };
                }
            } else if (functionRegex.test(trimmedLine)) {
                const match = trimmedLine.match(functionRegex);
                if (match) {
                    node = {
                        id: `function_${match[1]}_${this.nodeId++}`,
                        type: 'function',
                        name: match[1],
                        content: trimmedLine,
                        cellIndex,
                        lineInCell: i,
                        lineInNotebook: cellStartLine + i,
                        children: [],
                        dependencies: []
                    };
                }
            } else if (indent === 0 && variableRegex.test(trimmedLine)) {
                const match = trimmedLine.match(variableRegex);
                if (match) {
                    node = {
                        id: `var_${match[1]}_${this.nodeId++}`,
                        type: 'variable',
                        name: match[1],
                        content: trimmedLine,
                        cellIndex,
                        lineInCell: i,
                        lineInNotebook: cellStartLine + i,
                        children: [],
                        dependencies: []
                    };
                }
            }
            
            if (node) {
                if (parentStack.length > 0) {
                    parentStack[parentStack.length - 1].children.push(node);
                } else {
                    nodes.push(node);
                }
                
                if (node.type === 'class' || node.type === 'function') {
                    parentStack.push(node);
                    currentIndent = indent;
                }
            }
        }
        
        return nodes;
    }

    private flattenNodes(nodes: CodeNode[]): CodeNode[] {
        const flattened: CodeNode[] = [];
        
        for (const node of nodes) {
            flattened.push(node);
            if (node.children.length > 0) {
                flattened.push(...this.flattenNodes(node.children));
            }
        }
        
        return flattened;
    }

    private detectDependencies(nodes: CodeNode[], edges: any[]) {
        const nodeMap = new Map<string, CodeNode>();
        
        for (const node of nodes) {
            if (node.type !== 'cell') {
                nodeMap.set(node.name, node);
            }
        }
        
        for (const node of nodes) {
            if (node.type === 'function' || node.type === 'class') {
                const callMatches = node.content.match(/\b(\w+)\s*\(/g);
                
                if (callMatches) {
                    for (const match of callMatches) {
                        const calledName = match.replace(/\s*\(/, '');
                        
                        if (nodeMap.has(calledName) && calledName !== node.name) {
                            edges.push({
                                source: node.id,
                                target: nodeMap.get(calledName)!.id,
                                type: 'calls'
                            });
                            node.dependencies.push(calledName);
                        }
                    }
                }
            }
        }
    }
}