import * as vscode from 'vscode';
import { GraphData, EmberOutput } from './notebookParser';

export class GraphPanel {
    public static currentPanel: GraphPanel | undefined;
    private static lastNotebook: vscode.NotebookDocument | undefined;
    
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _emberOutput: EmberOutput | undefined;
    private _notebookDocument: vscode.NotebookDocument | undefined;
    
    public static createOrShow(extensionUri: vscode.Uri, emberOutput: EmberOutput, notebookDocument?: vscode.NotebookDocument) {
        const column = vscode.ViewColumn.Two;
        
        // Use provided notebook or fall back to last known notebook
        const notebook = notebookDocument || GraphPanel.lastNotebook;
        
        if (GraphPanel.currentPanel) {
            GraphPanel.currentPanel._panel.reveal(column);
            GraphPanel.currentPanel.update(emberOutput, notebook);
            return;
        }
        
        const panel = vscode.window.createWebviewPanel(
            'emberGraph',
            'Notebook Graph',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );
        
        GraphPanel.currentPanel = new GraphPanel(panel, extensionUri);
        GraphPanel.currentPanel.initializeGraph(emberOutput, notebook);
    }
    
    public static setLastNotebook(notebook: vscode.NotebookDocument) {
        GraphPanel.lastNotebook = notebook;
    }
    
    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'selectNode':
                        this._handleNodeSelection(message.nodeId);
                        return;
                }
            },
            null,
            this._disposables
        );
    }
    
    public dispose() {
        GraphPanel.currentPanel = undefined;
        
        this._panel.dispose();
        
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
    
    public update(emberOutput: EmberOutput, notebookDocument?: vscode.NotebookDocument) {
        this._emberOutput = emberOutput;
        if (notebookDocument) {
            this._notebookDocument = notebookDocument;
        }
        
        // Instead of regenerating all HTML, just send the new data
        // This preserves the graph state and avoids re-initialization issues
        this._panel.webview.postMessage({
            command: 'updateData',
            graphData: emberOutput.graph,
            phases: emberOutput.phases || []
        });
    }
    
    public initializeGraph(emberOutput: EmberOutput, notebookDocument?: vscode.NotebookDocument) {
        this._emberOutput = emberOutput;
        if (notebookDocument) {
            this._notebookDocument = notebookDocument;
        }
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview, emberOutput);
    }
    
    public highlightNodeAtPosition(cellIndex: number, lineInCell: number) {
        if (!this._emberOutput) return;
        
        // Find node at cell position
        const node = this._emberOutput.graph.nodes.find(n => 
            n.cellIndex === cellIndex && n.lineInCell === lineInCell
        );
        
        if (node) {
            this._panel.webview.postMessage({
                command: 'highlightNode',
                nodeId: node.id
            });
        }
    }
    
    public highlightNodeById(nodeId: string) {
        this._panel.webview.postMessage({
            command: 'highlightNode',
            nodeId: nodeId
        });
    }
    
    private async _handleNodeSelection(nodeId: string) {
        // Find the node
        const node = this._emberOutput?.graph.nodes.find((n: any) => n.id === nodeId);
        if (!node) return;
        
        // Store the notebook reference for the reveal command
        if (this._notebookDocument) {
            GraphPanel.lastNotebook = this._notebookDocument;
        }
        
        // Simply execute the reveal command which handles everything
        vscode.commands.executeCommand('emberNotebookOutline.reveal', node);
    }
    
    public getNotebookDocument(): vscode.NotebookDocument | undefined {
        return this._notebookDocument;
    }
    
    private _getHtmlForWebview(webview: vscode.Webview, emberOutput: EmberOutput) {
        const graphData = emberOutput.graph;
        const phases = emberOutput.phases || [];
        
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Notebook Graph</title>
            <style>
                html, body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                    background: var(--vscode-editor-background);
                    color: var(--vscode-editor-foreground);
                    width: 100%;
                    height: 100%;
                }
                
                #graph {
                    width: 100%;
                    height: 100%;
                    position: absolute;
                    top: 0;
                    left: 0;
                }
                
                .node {
                    cursor: pointer;
                }
                
                .node rect {
                    fill: var(--vscode-editor-background);
                    stroke: var(--vscode-panel-border);
                    stroke-width: 1px;
                    rx: 4;
                    ry: 4;
                }
                
                .node.highlighted rect {
                    stroke: var(--vscode-focusBorder);
                    stroke-width: 2px;
                    filter: drop-shadow(0 0 3px var(--vscode-focusBorder));
                }
                
                .phase-box {
                    fill: none;
                    stroke: var(--vscode-panel-border);
                    stroke-width: 2px;
                    stroke-dasharray: 5,5;
                    rx: 10;
                    ry: 10;
                }
                
                .phase-title {
                    font-size: 14px;
                    font-weight: bold;
                    fill: var(--vscode-editor-foreground);
                    opacity: 0.7;
                }
                
                .node.class rect {
                    fill: rgba(242, 142, 44, 0.2);
                }
                
                .node.function rect, .node.method rect {
                    fill: rgba(225, 87, 89, 0.2);
                }
                
                .node.import rect {
                    fill: rgba(118, 183, 178, 0.2);
                }
                
                .node.variable rect {
                    fill: rgba(89, 161, 79, 0.2);
                }
                
                .node.block rect {
                    fill: rgba(156, 146, 184, 0.2);
                }
                
                .node.expression rect {
                    fill: rgba(129, 161, 193, 0.2);
                }
                
                .node.decorator rect {
                    fill: rgba(250, 200, 99, 0.2);
                }
                
                .node text {
                    font: 12px var(--vscode-font-family);
                    fill: var(--vscode-editor-foreground);
                    pointer-events: none;
                }
                
                .link {
                    fill: none;
                    stroke: var(--vscode-panel-border);
                    stroke-opacity: 0.6;
                    stroke-width: 1.5px;
                    marker-end: url(#arrowhead);
                }
                
                .link.calls {
                    stroke: rgba(255, 128, 128, 0.6);
                }
                
                .tooltip {
                    position: absolute;
                    text-align: center;
                    padding: 8px;
                    font: 12px sans-serif;
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    border-radius: 4px;
                    pointer-events: none;
                    opacity: 0;
                }
            </style>
        </head>
        <body>
            <div id="debug" style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); color: white; padding: 10px; font-size: 12px; max-width: 300px; z-index: 1000; display: none;"></div>
            <div id="graph"></div>
            <div class="tooltip"></div>
            
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <script src="https://unpkg.com/dagre-d3@0.6.4/dist/dagre-d3.min.js"></script>
            <script>
                const vscode = acquireVsCodeApi();
                
                // Cache the full graph data to preserve component structure
                let cachedGraphData = ${JSON.stringify(graphData)};
                let cachedPhases = ${JSON.stringify(phases)};
                
                // Use cached data for initial render
                const graphData = cachedGraphData;
                const phases = cachedPhases;
                
                // Create a new directed graph with compound nodes enabled
                const g = new dagreD3.graphlib.Graph({ compound: true })
                    .setGraph({ 
                        rankdir: 'TB', 
                        nodesep: 30, 
                        ranksep: 40, 
                        marginx: 20, 
                        marginy: 20,
                        edgesep: 10
                    })
                    .setDefaultEdgeLabel(() => ({}));
                
                // Extract all components (including those nested in blocks/cells)
                const nodeMap = new Map();
                
                function extractComponents(nodes) {
                    if (!nodes) return; // Safety guard for undefined nodes
                    
                    nodes.forEach(node => {
                        // Skip containers (blocks and cells) but process their children
                        if (node.type === 'block' || node.type === 'cell') {
                            console.log('Found container:', node.id, 'type:', node.type, 'with children:', node.children ? node.children.length : 0);
                            // Recurse into container children to get actual components
                            if (node.children && node.children.length > 0) {
                                extractComponents(node.children);
                            }
                            return; // Don't register the container itself
                        }
                        
                        // Register actual components (not cells or blocks)
                        nodeMap.set(node.id, node);
                        nodeMap.set(node.name, node);
                        console.log('Registered component:', node.id, node.type, node.name);
                        
                        // Recurse into nested components (e.g., methods in classes)
                        if (node.children && node.children.length > 0) {
                            extractComponents(node.children);
                        }
                    });
                }
                
                // Extract all components from the graph data
                // Show debug info
                const debugDiv = document.getElementById('debug');
                debugDiv.style.display = 'block';
                
                let debugInfo = 'Initial Load:<br>';
                debugInfo += '- Nodes: ' + graphData.nodes.length + '<br>';
                debugInfo += '- First node type: ' + (graphData.nodes[0] ? graphData.nodes[0].type : 'none') + '<br>';
                debugInfo += '- Has children: ' + (graphData.nodes[0] && graphData.nodes[0].children ? 'Yes (' + graphData.nodes[0].children.length + ')' : 'No') + '<br>';
                
                console.log('Initial graphData nodes:', graphData.nodes.length, 'First node:', graphData.nodes[0]);
                extractComponents(graphData.nodes);
                
                debugInfo += '- Extracted: ' + nodeMap.size + ' components<br>';
                debugInfo += '- Types: ' + Array.from(new Set(Array.from(nodeMap.values()).map(n => n.type))).join(', ') + '<br>';
                debugDiv.innerHTML = debugInfo;
                
                console.log('Extracted components:', nodeMap.size);
                console.log('Node map entries:', Array.from(nodeMap.entries()).slice(0, 5));
                
                // Step 1: Add phase cluster nodes first
                phases.forEach((phase, i) => {
                    const phaseId = phase.phase_id || phase.id || 'unknown';
                    const phaseTitle = phase.title || phase.name || 'Phase';
                    g.setNode('phase_' + phaseId, {
                        label: phaseId + ' · ' + phaseTitle,
                        clusterLabelPos: 'top',
                        style: 'fill: ' + getPhaseColor(i) + '; fill-opacity: 0.1; stroke: ' + getPhaseColor(i) + '; stroke-width: 2px; stroke-dasharray: 5,5; rx: 10; ry: 10;',
                        class: 'phase cluster'
                    });
                });
                
                // Step 2: Add class nodes as clusters (so methods can be nested inside)
                for (const [id, node] of nodeMap) {
                    if (node.type === 'class') {
                        g.setNode(node.id, {
                            label: node.name,
                            clusterLabelPos: 'top',
                            style: 'fill: rgba(242, 142, 44, 0.1); stroke: rgba(242, 142, 44, 0.6); stroke-width: 2px; rx: 5; ry: 5;',
                            class: 'node class cluster'
                        });
                    }
                }
                
                // Helper to find parent class for a method
                function findParentClass(methodId) {
                    for (const [, node] of nodeMap) {
                        if (node.type === 'class' && node.children) {
                            if (node.children.some(c => c.id === methodId)) {
                                return node;
                            }
                        }
                    }
                    return null;
                }
                
                // Step 3: Add all component nodes and assign to phases/classes
                phases.forEach(phase => {
                    const phaseId = phase.phase_id || phase.id || 'unknown';
                    
                    phase.components.forEach(compId => {
                        const node = nodeMap.get(compId);
                        if (!node) {
                            console.log('Component not found:', compId);
                            return;
                        }
                        
                        // Skip if already added (classes were added as clusters)
                        if (node.type === 'class') {
                            // Class already added as cluster, just set its parent to phase
                            g.setParent(node.id, 'phase_' + phaseId);
                            return;
                        }
                        
                        // Add the component node
                        g.setNode(node.id, {
                            label: node.name,
                            class: 'node ' + node.type,
                            nodeData: node,
                            width: Math.max(120, node.name.length * 8),
                            height: 35
                        });
                        
                        // Set parent based on type
                        if (node.type === 'method') {
                            // Methods go inside their class
                            const parentClass = findParentClass(node.id);
                            if (parentClass) {
                                g.setParent(node.id, parentClass.id);
                                // Also ensure the class is in the phase
                                g.setParent(parentClass.id, 'phase_' + phaseId);
                            } else {
                                // Orphan method, put directly in phase
                                g.setParent(node.id, 'phase_' + phaseId);
                            }
                        } else {
                            // Everything else goes directly in the phase
                            g.setParent(node.id, 'phase_' + phaseId);
                        }
                    });
                });
                
                console.log('Graph has', g.nodeCount(), 'nodes and', g.edgeCount(), 'edges');
                
                // Step 4: Add orphan components (not in any phase)
                const assignedNodes = new Set();
                phases.forEach(phase => {
                    phase.components.forEach(comp => {
                        assignedNodes.add(comp);
                    });
                });
                
                // Check all extracted components for orphans
                for (const [id, node] of nodeMap) {
                    if (!assignedNodes.has(node.id) && !assignedNodes.has(node.name)) {
                        // Add orphan node
                        if (!g.node(node.id)) {
                            g.setNode(node.id, {
                                label: node.name,
                                class: 'node ' + node.type,
                                nodeData: node,
                                width: Math.max(120, node.name.length * 8),
                                height: 35
                            });
                        }
                    }
                }
                
                // Step 5: Add edges between components
                graphData.edges.forEach(edge => {
                    // Skip block-level edges
                    if (edge.source.startsWith('block_') || edge.target.startsWith('block_')) {
                        return;
                    }
                    
                    // Only add edge if both nodes exist
                    if (g.node(edge.source) && g.node(edge.target)) {
                        g.setEdge(edge.source, edge.target, {
                            class: 'link ' + edge.type,
                            curve: d3.curveBasis
                        });
                    }
                });
                
                console.log('After adding edges - Graph has', g.nodeCount(), 'nodes and', g.edgeCount(), 'edges');
                
                // Create the renderer
                const render = new dagreD3.render();
                
                // Set up SVG
                const svg = d3.select("#graph").append("svg")
                    .attr("width", "100%")
                    .attr("height", "100%");
                
                // Add arrow marker
                svg.append("defs").append("marker")
                    .attr("id", "arrowhead")
                    .attr("viewBox", "0 0 10 10")
                    .attr("refX", 9)
                    .attr("refY", 5)
                    .attr("markerWidth", 8)
                    .attr("markerHeight", 8)
                    .attr("orient", "auto")
                    .append("path")
                    .attr("d", "M 0 0 L 10 5 L 0 10 z")
                    .attr("fill", "var(--vscode-panel-border)");
                
                const svgGroup = svg.append("g");
                
                // Render the graph
                render(svgGroup, g);
                
                // Center and fit the graph
                const graphBounds = svgGroup.node().getBBox();
                const width = svg.node().clientWidth;
                const height = svg.node().clientHeight;
                const midX = graphBounds.x + graphBounds.width / 2;
                const midY = graphBounds.y + graphBounds.height / 2;
                const scale = 0.9 * Math.min(width / graphBounds.width, height / graphBounds.height);
                const translate = [width / 2 - midX * scale, height / 2 - midY * scale];
                
                // Set up zoom behavior
                const zoom = d3.zoom()
                    .scaleExtent([0.1, 10])
                    .on("zoom", (event) => {
                        svgGroup.attr("transform", event.transform);
                    });
                
                svg.call(zoom);
                
                // Apply initial transform
                svg.call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
                
                // Add click handlers to nodes
                svgGroup.selectAll(".node")
                    .on("click", function(event) {
                        const nodeId = d3.select(this).datum();
                        const nodeData = g.node(nodeId).nodeData;
                        if (nodeData) {
                            vscode.postMessage({
                                command: 'selectNode',
                                nodeId: nodeData.id
                            });
                        }
                    })
                    .on("mouseover", function(event) {
                        const nodeId = d3.select(this).datum();
                        const nodeData = g.node(nodeId).nodeData;
                        if (nodeData && nodeData.content) {
                            const tooltip = d3.select(".tooltip");
                            tooltip.transition()
                                .duration(200)
                                .style("opacity", .9);
                            tooltip.html(nodeData.content.substring(0, 100) + "...")
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 28) + "px");
                        }
                    })
                    .on("mouseout", function() {
                        d3.select(".tooltip").transition()
                            .duration(500)
                            .style("opacity", 0);
                    });
                
                // Merge functions to preserve component data
                function mergeGraphData(base, delta) {
                    if (!base) return delta;
                    
                    // Create a map of existing nodes by ID
                    const idMap = new Map();
                    
                    // First, add all base nodes
                    base.nodes.forEach(n => {
                        // Convert cell to block if needed for consistency
                        if (n.type === 'cell') {
                            const blockNode = Object.assign({}, n, { type: 'block' });
                            idMap.set(n.id, blockNode);
                        } else {
                            idMap.set(n.id, n);
                        }
                    });
                    
                    // Then update with delta nodes
                    delta.nodes.forEach(n => {
                        // Only replace if the delta has children (full data)
                        const existing = idMap.get(n.id);
                        if (!existing || (n.children && n.children.length > 0)) {
                            idMap.set(n.id, n);
                        }
                    });
                    
                    const nodes = Array.from(idMap.values());
                    
                    // Merge edges (dedup by source|target)
                    // Fix edge merge - don't lose edges
                    function mergeEdges(baseEdges, deltaEdges) {
                        const key = (e) => e.source + '|' + e.target + '|' + e.type;
                        const map = new Map();
                        [...(baseEdges || []), ...(deltaEdges || [])].forEach(e => {
                            map.set(key(e), e);
                        });
                        return Array.from(map.values());
                    }
                    
                    return { nodes: nodes, edges: mergeEdges(base.edges, delta.edges) };
                }
                
                function mergePhases(base, delta) {
                    if (!base) return delta;
                    const pMap = new Map(base.map(p => [p.id || p.phase_id, p]));
                    delta.forEach(p => pMap.set(p.id || p.phase_id, p));
                    return Array.from(pMap.values());
                }
                
                // Function to rebuild graph with new data
                function rebuildGraph(newGraphData, newPhases) {
                    // Clear existing graph
                    svgGroup.selectAll("*").remove();
                    
                    // Rebuild with new data
                    const g = new dagreD3.graphlib.Graph({ compound: true })
                        .setGraph({ 
                            rankdir: 'TB', 
                            nodesep: 30, 
                            ranksep: 40, 
                            marginx: 20, 
                            marginy: 20,
                            edgesep: 10
                        })
                        .setDefaultEdgeLabel(() => ({}));
                    
                    // Re-run all the extraction and node addition logic
                    const nodeMap = new Map();
                    
                    function extractComponentsInRebuild(nodes) {
                        if (!nodes) return;
                        nodes.forEach(node => {
                            // Skip containers but process their children
                            if (node.type === 'block' || node.type === 'cell') {
                                console.log('Rebuild - Found container:', node.id, 'type:', node.type, 'with children:', node.children ? node.children.length : 0);
                                if (node.children && node.children.length > 0) {
                                    extractComponentsInRebuild(node.children);
                                }
                                return; // Don't register the container
                            }
                            // Register actual components
                            nodeMap.set(node.id, node);
                            nodeMap.set(node.name, node);
                            // Process nested components
                            if (node.children && node.children.length > 0) {
                                extractComponentsInRebuild(node.children);
                            }
                        });
                    }
                    
                    console.log('Rebuild - Processing nodes:', newGraphData.nodes.length);
                    extractComponentsInRebuild(newGraphData.nodes);
                    
                    // Fix the core problem: normalize phase.components to reference actual components, not blocks
                    function expandPhaseComponentIds(phases, nodeMap) {
                        return phases.map(p => {
                            const expanded = [];
                            p.components.forEach(id => {
                                const n = nodeMap.get(id);
                                if (!n) return;
                                
                                if (n.type === 'block' || n.type === 'cell') {
                                    // This is a container, collect its leaf components
                                    collectLeaves(n, expanded);
                                } else {
                                    // This is already a component
                                    expanded.push(id);
                                }
                            });
                            return Object.assign({}, p, { components: Array.from(new Set(expanded)) });
                        });
                    }
                    
                    function collectLeaves(node, out) {
                        if (!node.children || node.children.length === 0) {
                            // No children, this is a leaf
                            if (node.type !== 'block' && node.type !== 'cell') {
                                out.push(node.id);
                            }
                            return;
                        }
                        node.children.forEach(c => {
                            if (c.type === 'block' || c.type === 'cell') {
                                collectLeaves(c, out);
                            } else {
                                out.push(c.id);
                                // Also collect from nested components (methods in classes)
                                if (c.children && c.children.length > 0) {
                                    collectLeaves(c, out);
                                }
                            }
                        });
                    }
                    
                    // Create a temporary nodeMap that includes containers for the expansion
                    const fullNodeMap = new Map(nodeMap);
                    newGraphData.nodes.forEach(n => {
                        if (n.type === 'block' || n.type === 'cell') {
                            fullNodeMap.set(n.id, n);
                        }
                    });
                    
                    // Normalize phases to reference actual components
                    const normalizedPhases = expandPhaseComponentIds(newPhases, fullNodeMap);
                    console.log('Normalized phases:', normalizedPhases.map(p => ({id: p.id, components: p.components})));
                    
                    const debugDiv = document.getElementById('debug');
                    if (debugDiv) {
                        debugDiv.innerHTML += '<br><b>Rebuild:</b><br>';
                        debugDiv.innerHTML += '- Extracted: ' + nodeMap.size + ' components<br>';
                        debugDiv.innerHTML += '- Phases: ' + newPhases.length + '<br>';
                        debugDiv.innerHTML += '- Phase components: ' + newPhases.map(p => p.components ? p.components.length : 0).join(', ') + '<br>';
                    }
                    
                    console.log('Rebuild: extracted components:', nodeMap.size);
                    
                    // Same logic as initial render:
                    // Step 1: Add phase clusters
                    normalizedPhases.forEach((phase, i) => {
                        const phaseId = phase.phase_id || phase.id || 'unknown';
                        const phaseTitle = phase.title || phase.name || 'Phase';
                        g.setNode('phase_' + phaseId, {
                            label: phaseId + ' · ' + phaseTitle,
                            clusterLabelPos: 'top',
                            style: 'fill: ' + getPhaseColor(i) + '; fill-opacity: 0.1; stroke: ' + getPhaseColor(i) + '; stroke-width: 2px; stroke-dasharray: 5,5; rx: 10; ry: 10;',
                            class: 'phase cluster'
                        });
                    });
                    
                    // Step 2: Add class nodes as clusters
                    for (const [id, node] of nodeMap) {
                        if (node.type === 'class') {
                            g.setNode(node.id, {
                                label: node.name,
                                clusterLabelPos: 'top',
                                style: 'fill: rgba(242, 142, 44, 0.1); stroke: rgba(242, 142, 44, 0.6); stroke-width: 2px; rx: 5; ry: 5;',
                                class: 'node class cluster'
                            });
                        }
                    }
                    
                    // Helper to find parent class
                    function findParentClass(methodId) {
                        for (const [, node] of nodeMap) {
                            if (node.type === 'class' && node.children) {
                                if (node.children.some(c => c.id === methodId)) {
                                    return node;
                                }
                            }
                        }
                        return null;
                    }
                    
                    // Step 3: Add all components
                    console.log('Adding components from phases. NodeMap has:', nodeMap.size, 'entries');
                    console.log('First few nodeMap keys:', Array.from(nodeMap.keys()).slice(0, 10));
                    
                    normalizedPhases.forEach(phase => {
                        const phaseId = phase.phase_id || phase.id || 'unknown';
                        console.log('Processing phase:', phaseId, 'with components:', phase.components);
                        
                        phase.components.forEach(compId => {
                            const node = nodeMap.get(compId);
                            if (!node) return;
                            
                            if (node.type === 'class') {
                                g.setParent(node.id, 'phase_' + phaseId);
                                return;
                            }
                            
                            g.setNode(node.id, {
                                label: node.name,
                                class: 'node ' + node.type,
                                nodeData: node,
                                width: Math.max(120, node.name.length * 8),
                                height: 35
                            });
                            
                            if (node.type === 'method') {
                                const parentClass = findParentClass(node.id);
                                if (parentClass) {
                                    g.setParent(node.id, parentClass.id);
                                    g.setParent(parentClass.id, 'phase_' + phaseId);
                                } else {
                                    g.setParent(node.id, 'phase_' + phaseId);
                                }
                            } else {
                                g.setParent(node.id, 'phase_' + phaseId);
                            }
                        });
                    });
                    
                    // Step 4: Add edges
                    console.log('Adding edges:', newGraphData.edges.length);
                    newGraphData.edges.forEach(edge => {
                        if (edge.source.startsWith('block_') || edge.target.startsWith('block_')) {
                            return;
                        }
                        if (g.node(edge.source) && g.node(edge.target)) {
                            g.setEdge(edge.source, edge.target, {
                                class: 'link ' + edge.type,
                                curve: d3.curveBasis
                            });
                        }
                    });
                    
                    console.assert(g.nodeCount() > 0, 'No nodes added to Dagre graph!');
                    console.assert(g.edgeCount() >= 0, 'Edge count check');
                    
                    console.log('Rebuild complete: Graph has', g.nodeCount(), 'nodes and', g.edgeCount(), 'edges');
                    
                    if (debugDiv) {
                        debugDiv.innerHTML += '- Final graph nodes: ' + g.nodeCount() + '<br>';
                        debugDiv.innerHTML += '- Final graph edges: ' + g.edgeCount() + '<br>';
                    }
                    
                    // Re-render
                    render(svgGroup, g);
                    
                    // Re-apply zoom
                    const graphBounds = svgGroup.node().getBBox();
                    const width = svg.node().clientWidth;
                    const height = svg.node().clientHeight;
                    const midX = graphBounds.x + graphBounds.width / 2;
                    const midY = graphBounds.y + graphBounds.height / 2;
                    const scale = 0.9 * Math.min(width / graphBounds.width, height / graphBounds.height);
                    const translate = [width / 2 - midX * scale, height / 2 - midY * scale];
                    svg.call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
                }
                
                // Handle messages from extension
                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.command) {
                        case 'updateData':
                            // Merge new data with cached to preserve component structure
                            const debugDiv = document.getElementById('debug');
                            let updateInfo = debugDiv.innerHTML + '<br><b>Update received:</b><br>';
                            updateInfo += '- Delta nodes: ' + message.graphData.nodes.length + '<br>';
                            updateInfo += '- First delta type: ' + (message.graphData.nodes[0] ? message.graphData.nodes[0].type : 'none') + '<br>';
                            updateInfo += '- Has children: ' + (message.graphData.nodes[0] && message.graphData.nodes[0].children ? 'Yes' : 'No') + '<br>';
                            
                            console.log('Update received, merging with cache');
                            console.log('Delta nodes:', message.graphData.nodes.map(n => ({id: n.id, type: n.type, hasChildren: !!n.children})));
                            
                            cachedGraphData = mergeGraphData(cachedGraphData, message.graphData);
                            cachedPhases = mergePhases(cachedPhases, message.phases);
                            
                            updateInfo += '- After merge: ' + cachedGraphData.nodes.length + ' nodes<br>';
                            updateInfo += '- First merged type: ' + (cachedGraphData.nodes[0] ? cachedGraphData.nodes[0].type : 'none') + '<br>';
                            debugDiv.innerHTML = updateInfo;
                            
                            console.log('Merged data, total nodes:', cachedGraphData.nodes.length);
                            rebuildGraph(cachedGraphData, cachedPhases);
                            break;
                            
                        case 'highlightNode':
                            // Remove previous highlights
                            svgGroup.selectAll('.node').classed('highlighted', false);
                            
                            // Highlight new node
                            svgGroup.selectAll('.node').each(function() {
                                const nodeId = d3.select(this).datum();
                                const nodeData = g.node(nodeId)?.nodeData;
                                if (nodeData && nodeData.id === message.nodeId) {
                                    d3.select(this).classed('highlighted', true);
                                    
                                    // Center view on highlighted node
                                    const nodeBounds = this.getBBox();
                                    const nodeX = nodeBounds.x + nodeBounds.width / 2;
                                    const nodeY = nodeBounds.y + nodeBounds.height / 2;
                                    
                                    const currentTransform = d3.zoomTransform(svg.node());
                                    const transform = d3.zoomIdentity
                                        .translate(width / 2 - nodeX * currentTransform.k, height / 2 - nodeY * currentTransform.k)
                                        .scale(currentTransform.k);
                                    
                                    svg.transition()
                                        .duration(750)
                                        .call(zoom.transform, transform);
                                }
                            });
                            break;
                    }
                });
                
                // Helper function for phase colors
                function getPhaseColor(index) {
                    const colors = [
                        '#7c9dbd', // blue
                        '#9dbd7c', // green  
                        '#bd9d7c', // orange
                        '#bd7c9d', // pink
                        '#9d7cbd', // purple
                        '#7cbdbd'  // cyan
                    ];
                    return colors[index % colors.length];
                }
            </script>
        </body>
        </html>`;
    }
}