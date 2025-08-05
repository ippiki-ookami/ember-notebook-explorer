# Ember Extension - Phase-Based Tree View Implementation

## Problem Statement
The VS Code extension was showing a flat cell-based tree structure instead of organizing code components by logical phases. The graph visualization was also missing phase clustering.

## Implementation Summary

### 1. Python Backend Changes (ember.py)

**Added phase support to JSON export:**
```python
# Line 1126-1134
# Full analysis: graph plus phase plan
explainer = NotebookExplainer(openai_client=openai_client)
graph, phases = explainer.analyze_notebook(notebook_data)
phase_json = [asdict(p) for p in phases]

output = {
    "graph": graph_to_dict(graph),
    "phases": phase_json      # ← NEW
}
```

**Fixed JSON output pollution:**
```python
# Line 82-83: Added global flag
json_export_mode = False

# Lines 594-595, 600-601, 608-609, 616-617: Conditional printing
if not json_export_mode:
    print("Using cached code graph")
```

### 2. TypeScript Extension Changes

**notebookOutlineView.ts - Phase-based tree building:**
```typescript
// Line 197-264: New buildPhaseHierarchy method
private buildPhaseHierarchy(): TreeNode[] {
    // Map nodes by name (phases use component names)
    const nodeByName = new Map<string, CodeNode>();
    for (const node of this.allNodes) {
        if (node.type !== 'cell') {
            nodeByName.set(node.name, node);
        }
    }
    
    // Create phase nodes
    for (const phase of this.phases) {
        const phaseNode: PhaseNode = {
            id: phase.phase_id,
            name: `${phase.phase_id} · ${phase.title}`,
            type: 'phase',
            children: [],
            phase: phase
        };
        
        // Add components by name
        for (const componentName of phase.components) {
            const node = nodeByName.get(componentName);
            if (node) {
                phaseNode.children.push(node);
            }
        }
        phaseNodes.push(phaseNode);
    }
    return phaseNodes;
}
```

**graphPanel.ts - D3 Phase Clustering:**
```typescript
// Line 285-333: Phase-aware hierarchy building
if (phases && phases.length > 0) {
    phases.forEach(phase => {
        const phaseNode = {
            id: phase.phase_id,
            name: `${phase.phase_id} · ${phase.title}`,
            type: 'phase',
            children: [],
            color: phaseColour(phase.phase_id)
        };
        // ... add components to phase
        root.children.push(phaseNode);
    });
}

// Line 434-486: Phase hull visualization
function updatePhaseHulls() {
    phaseNodes.forEach(phaseNode => {
        // Calculate convex hull of phase components
        const hull = d3.polygonHull(points);
        phaseGroups.append("path")
            .attr("class", "phase-hull")
            .attr("d", "M" + expandedHull.join("L") + "Z")
            .attr("fill", phaseNode.data.color)
            .attr("fill-opacity", 0.1)
            .attr("stroke-dasharray", "5,5");
    });
}
```

## Current Issue
The tree view is only showing "Notebook" as the root node. This could be because:

1. **Empty phase components**: The cached phase data has empty component arrays
2. **Phase matching issue**: Component names might not match between graph nodes and phase components
3. **Tree building logic**: The hierarchy might not be properly constructed

## Test Data
Running `ember.py tiny_demo.ipynb --export-json` produces:
```json
{
  "graph": {
    "nodes": [...],  // Contains VectorStore, clean_text, tokenize, etc.
    "edges": [...]
  },
  "phases": [
    {
      "phase_id": "p1",
      "title": "Data Loading",
      "components": []  // ← EMPTY!
    },
    // ... all phases have empty components arrays
  ]
}
```

## Key Files Modified
1. `/home/aesyr/repos/ember_extension/ember.py` - Added phase export and JSON cleanup
2. `/home/aesyr/repos/ember_extension/src/notebookOutlineView.ts` - Phase hierarchy building
3. `/home/aesyr/repos/ember_extension/src/graphPanel.ts` - D3 phase clustering
4. `/home/aesyr/repos/ember_extension/src/extension.ts` - Cache control option

## Debug Steps Taken
1. Added debug prefixes ([PHASE], [NODE]) to tree items
2. Added console logging for hierarchy building
3. Implemented VS Code setting for --no-cache option
4. Fixed Python print statements corrupting JSON output

## Next Steps
1. Run with --no-cache to get fresh phase analysis with components
2. Debug why tree view shows only "Notebook" 
3. Verify phase component assignment in ember.py

## Questions for Investigation
1. Is the LLM properly assigning components to phases?
2. Is the component name matching working correctly?
3. Is the tree view refresh being triggered after data loads?