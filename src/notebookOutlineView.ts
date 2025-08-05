import * as vscode from 'vscode';
import { CodeNode, NotebookParser, GraphData, EmberOutput, Phase } from './notebookParser';
import { GraphPanel } from './graphPanel';
import { execFile } from 'child_process';
import * as path from 'path';

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
        
        // Use new component-based analysis if available
        if (config.get<boolean>('useNewAnalysis', true)) {
            args.push('--use-new-analysis');
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

// Interface for phase nodes in the tree
export interface PhaseNode {
    id: string;
    name: string;
    type: 'phase';
    children: CodeNode[];
    phase?: Phase;
}

export type TreeNode = CodeNode | PhaseNode;

export class NotebookOutlineTreeItem extends vscode.TreeItem {
    constructor(
        public readonly node: TreeNode,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(node.name, collapsibleState);
        
        if (node.type === 'phase') {
            // Phase node
            this.label = node.name;
            this.iconPath = new vscode.ThemeIcon('layers');
            this.contextValue = 'phase';
            if (node.phase) {
                this.tooltip = node.phase.summary;
            }
        } else {
            // Code node
            this.label = node.name;
            this.tooltip = node.content.length > 100 
                ? node.content.substring(0, 100) + '...' 
                : node.content;
            
            // Set appropriate icons
            switch (node.type) {
                case 'cell':
                    this.iconPath = new vscode.ThemeIcon('notebook');
                    break;
                case 'block':
                    this.iconPath = new vscode.ThemeIcon('code');
                    break;
                case 'class':
                    this.iconPath = new vscode.ThemeIcon('symbol-class');
                    break;
                case 'function':
                    this.iconPath = new vscode.ThemeIcon('symbol-method');
                    break;
                case 'method':
                    this.iconPath = new vscode.ThemeIcon('symbol-method');
                    break;
                case 'variable':
                    this.iconPath = new vscode.ThemeIcon('symbol-variable');
                    break;
                case 'import':
                    this.iconPath = new vscode.ThemeIcon('package');
                    break;
                case 'expression':
                    this.iconPath = new vscode.ThemeIcon('symbol-operator');
                    break;
                case 'decorator':
                    this.iconPath = new vscode.ThemeIcon('symbol-color');
                    break;
                default:
                    this.iconPath = new vscode.ThemeIcon('symbol-misc');
            }
            
            // Set command to reveal on click
            this.command = {
                command: 'emberNotebookOutline.reveal',
                title: 'Reveal',
                arguments: [node]
            };
            
            // Add context value for conditional menus
            this.contextValue = node.type;
            
            // Add cell badge as description
            if (node.cellIndex !== undefined) {
                this.description = `Cell ${node.cellIndex + 1}`;
            }
        }
    }
}

export class NotebookOutlineProvider implements vscode.TreeDataProvider<TreeNode> {
    private _onDidChangeTreeData: vscode.EventEmitter<TreeNode | undefined | null | void> = new vscode.EventEmitter<TreeNode | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<TreeNode | undefined | null | void> = this._onDidChangeTreeData.event;
    
    private parser = new NotebookParser();
    private hierarchy: TreeNode[] = [];
    private phases: Phase[] = [];
    private allNodes: CodeNode[] = [];
    private activeNotebook: vscode.NotebookDocument | undefined;
    private disposables: vscode.Disposable[] = [];
    
    constructor(context: vscode.ExtensionContext) {
        // Watch for notebook document events
        this.disposables.push(
            vscode.workspace.onDidOpenNotebookDocument(this.onNotebookOpen, this),
            vscode.workspace.onDidChangeNotebookDocument(this.onNotebookChange, this),
            vscode.window.onDidChangeActiveNotebookEditor(this.onActiveNotebookChange, this)
        );
        
        context.subscriptions.push(...this.disposables);
        
        // Parse current notebook if available
        if (vscode.window.activeNotebookEditor) {
            this.parseAndRefresh(vscode.window.activeNotebookEditor.notebook);
        }
    }
    
    private async onNotebookOpen(notebook: vscode.NotebookDocument) {
        if (notebook.uri.fsPath.endsWith('.ipynb')) {
            await this.parseAndRefresh(notebook);
        }
    }
    
    private async onNotebookChange(event: vscode.NotebookDocumentChangeEvent) {
        // Only refresh if there are actual content changes, not just selection changes
        if (event.notebook === this.activeNotebook && event.contentChanges.length > 0) {
            console.log('Notebook content changed, refreshing...');
            await this.parseAndRefresh(event.notebook);
        }
    }
    
    private async onActiveNotebookChange(editor: vscode.NotebookEditor | undefined) {
        if (editor && editor.notebook.uri.fsPath.endsWith('.ipynb')) {
            await this.parseAndRefresh(editor.notebook);
        }
    }
    
    private async parseAndRefresh(notebook: vscode.NotebookDocument) {
        this.activeNotebook = notebook;
        
        try {
            // Use ember.py to parse the notebook
            const notebookPath = notebook.uri.fsPath;
            const emberOutput = await loadGraphFromEmber(notebookPath);
            
            // Store all nodes and phases
            this.allNodes = emberOutput.graph.nodes;
            this.phases = emberOutput.phases || [];
            
            // Always build phase-based hierarchy (will create cell-based phases if no phases from ember.py)
            this.hierarchy = this.buildPhaseHierarchy();
            
            console.log('Hierarchy built:', {
                hierarchyLength: this.hierarchy.length,
                firstItem: this.hierarchy[0] ? {
                    id: this.hierarchy[0].id,
                    name: this.hierarchy[0].name,
                    type: this.hierarchy[0].type,
                    childrenCount: this.hierarchy[0].children?.length || 0
                } : null
            });
            
            this._onDidChangeTreeData.fire();
            
            // Update graph panel if it exists
            if (GraphPanel.currentPanel) {
                GraphPanel.currentPanel.update(emberOutput, notebook);
            } else if (vscode.window.activeNotebookEditor) {
                // If no graph panel exists but we have a notebook, store it for later
                // This ensures the graph panel will have the notebook when created
                GraphPanel.setLastNotebook(notebook);
            }
        } catch (error) {
            console.error('Failed to parse notebook:', error);
            vscode.window.showWarningMessage(`Failed to parse notebook with ember.py: ${error}`);
        }
    }
    
    private buildPhaseHierarchy(): TreeNode[] {
        // If no phases from ember.py, create phases by cell
        if (this.phases.length === 0) {
            return this.buildCellBasedPhases();
        }
        
        const phaseNodes: PhaseNode[] = [];
        
        // First, extract all components from block nodes
        const allComponents: CodeNode[] = [];
        const componentById = new Map<string, CodeNode>();
        const componentByName = new Map<string, CodeNode>();
        
        // Extract components from blocks (they are nested inside block nodes)
        for (const node of this.allNodes) {
            if (node.type === 'block' && node.children) {
                // Add all components from this block
                this.extractComponents(node.children, allComponents, componentById, componentByName);
            } else if (node.type !== 'cell' && node.type !== 'block') {
                // Also handle nodes that aren't in blocks (backward compatibility)
                allComponents.push(node);
                componentById.set(node.id, node);
                componentByName.set(node.name, node);
            }
        }
        
        console.log('Building phase hierarchy:', {
            totalNodes: this.allNodes.length,
            totalComponents: allComponents.length,
            phases: this.phases.length,
            phaseDetails: this.phases.map(p => ({
                id: p.phase_id || p.id,
                title: p.title || p.name,
                components: p.components
            }))
        });
        
        // Create phase nodes
        for (const phase of this.phases) {
            const phaseNode: PhaseNode = {
                id: phase.phase_id || phase.id || '',
                name: phase.title ? `${phase.phase_id || phase.id} · ${phase.title}` : (phase.name || 'Unknown Phase'),
                type: 'phase',
                children: [],
                phase: phase
            };
            
            // Track which components have been added as children
            const addedAsChild = new Set<string>();
            
            // Add components to this phase, preserving hierarchy
            for (const componentRef of phase.components) {
                // Try to find by ID first, then by name
                const component = componentById.get(componentRef) || componentByName.get(componentRef);
                if (component) {
                    // Check if this component has a parent that's also in this phase
                    let hasParentInPhase = false;
                    
                    // Look for parent by checking if this component is in another component's children
                    for (const otherRef of phase.components) {
                        const parent = componentById.get(otherRef) || componentByName.get(otherRef);
                        if (parent && parent.children) {
                            if (this.containsChild(parent, component)) {
                                hasParentInPhase = true;
                                addedAsChild.add(component.id);
                                break;
                            }
                        }
                    }
                    
                    // Only add top-level components (those without parents in this phase)
                    if (!hasParentInPhase) {
                        phaseNode.children.push(component);
                    }
                }
            }
            
            phaseNodes.push(phaseNode);
        }
        
        // Add any unassigned components to an "Other" phase
        const assignedNodeRefs = new Set<string>();
        for (const phase of this.phases) {
            for (const componentRef of phase.components) {
                assignedNodeRefs.add(componentRef);
            }
        }
        
        const unassignedComponents = allComponents.filter(c => {
            return !assignedNodeRefs.has(c.id) && !assignedNodeRefs.has(c.name);
        });
        
        if (unassignedComponents.length > 0) {
            const otherPhase: PhaseNode = {
                id: 'phase_other',
                name: 'Other',
                type: 'phase',
                children: unassignedComponents
            };
            phaseNodes.push(otherPhase);
        }
        
        return phaseNodes;
    }
    
    private extractComponents(nodes: CodeNode[], allComponents: CodeNode[], byId: Map<string, CodeNode>, byName: Map<string, CodeNode>): void {
        for (const node of nodes) {
            allComponents.push(node);
            byId.set(node.id, node);
            byName.set(node.name, node);
            
            if (node.children && node.children.length > 0) {
                // Don't recurse - children are already included in the node
                // The tree view will handle displaying them
            }
        }
    }
    
    private containsChild(parent: CodeNode, child: CodeNode): boolean {
        if (!parent.children) return false;
        
        for (const c of parent.children) {
            if (c.id === child.id) return true;
            if (this.containsChild(c, child)) return true;
        }
        return false;
    }
    
    private buildCellBasedPhases(): TreeNode[] {
        // Group nodes by cell, but as phases
        const cellPhases = new Map<number, PhaseNode>();
        
        // Find root nodes (nodes that are not children of any other code node, excluding cell nodes)
        const childIds = new Set<string>();
        for (const node of this.allNodes) {
            if (node.type !== 'cell' && node.children) {
                for (const child of node.children) {
                    childIds.add(child.id);
                }
            }
        }
        
        const rootNodes = this.allNodes.filter(n => !childIds.has(n.id) && n.type !== 'cell');
        
        console.log('Building cell-based phases:', {
            totalNodes: this.allNodes.length,
            childIds: childIds.size,
            rootNodes: rootNodes.map(n => `${n.type}: ${n.name} (Cell ${n.cellIndex})`)
        });
        
        // Group root nodes by cell
        for (const node of rootNodes) {
            const cellIndex = node.cellIndex;
            if (!cellPhases.has(cellIndex)) {
                cellPhases.set(cellIndex, {
                    id: `phase_cell_${cellIndex}`,
                    name: `Cell ${cellIndex + 1}`,
                    type: 'phase',
                    children: []
                });
            }
            cellPhases.get(cellIndex)!.children.push(node);
        }
        
        // Return phases sorted by cell index
        return Array.from(cellPhases.values()).sort((a, b) => {
            const aIndex = parseInt(a.id.split('_')[2]);
            const bIndex = parseInt(b.id.split('_')[2]);
            return aIndex - bIndex;
        });
    }
    
    refresh(): void {
        if (this.activeNotebook) {
            this.parseAndRefresh(this.activeNotebook);
        }
    }
    
    getTreeItem(element: TreeNode): vscode.TreeItem {
        const hasChildren = element.children && element.children.length > 0;
        // For phases and classes, default to expanded; for others, collapsed
        const defaultState = (element.type === 'phase' || element.type === 'class') 
            ? vscode.TreeItemCollapsibleState.Expanded
            : vscode.TreeItemCollapsibleState.Collapsed;
        
        return new NotebookOutlineTreeItem(
            element,
            hasChildren 
                ? defaultState 
                : vscode.TreeItemCollapsibleState.None
        );
    }
    
    getChildren(element?: TreeNode): Thenable<TreeNode[]> {
        if (!element) {
            // Root level - return top-level nodes (phases or cells)
            console.log('getChildren called for root, returning:', this.hierarchy.map(h => ({
                id: h.id,
                name: h.name,
                type: h.type,
                childrenCount: h.children?.length || 0
            })));
            return Promise.resolve(this.hierarchy);
        } else {
            // Return children of the element
            const children = element.children || [];
            console.log(`getChildren called for ${element.name}, returning ${children.length} children`);
            return Promise.resolve(children);
        }
    }
    
    getParent(element: TreeNode): vscode.ProviderResult<TreeNode> {
        // Find parent by checking which node contains this element in its children
        for (const node of this.hierarchy) {
            if (node.children?.includes(element as any)) {
                return node;
            }
            // Check nested children
            for (const child of node.children || []) {
                if ('children' in child && child.children?.includes(element as any)) {
                    return child;
                }
            }
        }
        return undefined;
    }
    
    // Method to find a node by its properties
    public findNodeByPosition(cellIndex: number, lineInCell: number): CodeNode | undefined {
        const searchNodes = (nodes: TreeNode[]): CodeNode | undefined => {
            for (const node of nodes) {
                if (node.type === 'phase') {
                    // Search in phase children
                    const found = searchNodes(node.children);
                    if (found) return found;
                } else {
                    // This is a CodeNode
                    const codeNode = node as CodeNode;
                    if (codeNode.cellIndex === cellIndex && codeNode.lineInCell === lineInCell) {
                        return codeNode;
                    }
                    if (codeNode.children) {
                        const found = searchNodes(codeNode.children);
                        if (found) return found;
                    }
                }
            }
            return undefined;
        };
        
        return searchNodes(this.hierarchy);
    }
    
    // Method to highlight a node in the tree
    public highlightNode(nodeId: string): void {
        const node = this.findNodeById(nodeId);
        if (node) {
            // VS Code will automatically reveal and highlight the item
            vscode.commands.executeCommand('emberNotebookOutline.reveal', node);
        }
    }
    
    public findNodeById(nodeId: string): CodeNode | undefined {
        const searchNodes = (nodes: TreeNode[]): CodeNode | undefined => {
            for (const node of nodes) {
                if (node.type === 'phase') {
                    // Search in phase children
                    const found = searchNodes(node.children);
                    if (found) return found;
                } else {
                    // This is a CodeNode
                    const codeNode = node as CodeNode;
                    if (codeNode.id === nodeId) {
                        return codeNode;
                    }
                    if (codeNode.children) {
                        const found = searchNodes(codeNode.children);
                        if (found) return found;
                    }
                }
            }
            return undefined;
        };
        
        return searchNodes(this.hierarchy);
    }
    
    dispose() {
        this.disposables.forEach(d => d.dispose());
    }
    
    // Method to get the currently tracked notebook
    public getActiveNotebook(): vscode.NotebookDocument | undefined {
        return this.activeNotebook;
    }
}