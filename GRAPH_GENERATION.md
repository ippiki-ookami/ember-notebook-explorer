# 📊 D3.js Graph Generation for Ember Analysis

This document explains how to generate interactive D3.js visualizations from your Ember analysis results.

## 🎯 Overview

The Ember analysis pipeline generates rich data about notebook structure, component relationships, and dependencies. These utilities convert that data into interactive D3.js graphs that can be used in the VS Code extension or viewed standalone.

## 🔧 Tools Provided

### 1. `generate_d3_graph.py` - Main Graph Generator

Converts ember_output analysis data into D3.js-compatible JSON and HTML visualizations.

**Features:**
- ✅ Block-level dependency graphs
- ✅ Component-level relationship graphs  
- ✅ Interactive HTML visualization
- ✅ Color-coded by type and library
- ✅ Drag-and-drop node positioning
- ✅ Zoom and pan capabilities
- ✅ Hover tooltips with detailed info

**Usage:**
```bash
# Basic usage
python3 generate_d3_graph.py ember/ember_output/tiny_demo_20250806_062811

# Custom output directory
python3 generate_d3_graph.py analysis_dir --output /path/to/graphs

# Generate only HTML visualization
python3 generate_d3_graph.py analysis_dir --html-only
```

**Output Files:**
- `graph_data.json` - Complete combined graph data
- `graph_blocks.json` - Block-level graph only
- `graph_components.json` - Component-level graph only  
- `graph_visualization.html` - Interactive HTML viewer

### 2. `list_ember_runs.py` - Run Discovery Tool

Finds and analyzes all available ember_output analysis runs.

**Usage:**
```bash
# Search current directory
python3 list_ember_runs.py

# Search specific path
python3 list_ember_runs.py /path/to/search
```

**Shows:**
- 📂 All ember_output directories found
- 📊 Analysis runs with completion status
- 📁 File counts and key file sizes
- 🔧 Commands to generate missing graphs
- 🌐 Paths to existing visualizations

## 📊 Graph Data Structure

The generated graph data follows D3.js conventions with Ember-specific enhancements:

### Block-Level Graph (`graph_blocks.json`)
```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Import Libraries", 
      "type": "block",
      "blockType": "imports",
      "group": 1,
      "size": 35,
      "color": "#cc3d3d",
      "componentCount": 3,
      "isComplete": true,
      "hasDependencies": false
    }
  ],
  "links": [
    {
      "source": "1",
      "target": "2", 
      "type": "uses",
      "weight": 1,
      "color": "#cc3d3d",
      "strokeWidth": 2
    }
  ]
}
```

### Component-Level Graph (`graph_components.json`)
```json
{
  "nodes": [
    {
      "id": "1:1",
      "name": "pandas_import",
      "type": "component", 
      "componentType": "import",
      "blockId": "1",
      "blockName": "Import Libraries",
      "library": "pandas",
      "code": "import pandas as pd",
      "description": "Imports pandas for data manipulation"
    }
  ]
}
```

## 🎨 Visual Features

### Color Coding

**Block Types:**
- 🔴 Imports (`#e74c3c`)
- 🔵 Classes (`#3498db`) 
- 🟢 Functions (`#2ecc71`)
- 🟠 Utilities (`#f39c12`)
- 🟣 Config (`#9b59b6`)

**Component Types:**
- 🔴 Imports (`#e74c3c`)
- 🔵 Classes (`#3498db`)
- 🟢 Functions (`#2ecc71`) 
- 🟠 Methods (`#f39c12`)
- 🟣 Variables (`#9b59b6`)
- 🟦 Expressions (`#1abc9c`)
- ⚫ Decorators (`#34495e`)

### Node Sizing
- **Blocks**: Size based on number of components (3-50+ components = 35-270+ pixels)
- **Components**: Size based on description length and complexity

### Interactive Features
- **Drag & Drop**: Reposition nodes by dragging
- **Zoom & Pan**: Mouse wheel zoom, drag background to pan
- **Hover Tooltips**: Detailed information on hover
- **View Toggle**: Switch between block and component views
- **Label Toggle**: Show/hide node labels
- **Reset Zoom**: Return to default view

## 🔗 Integration with VS Code Extension

The generated JSON files are designed to be consumed by the VS Code extension:

1. **Load graph data**: Extension reads `graph_data.json`
2. **Render visualization**: D3.js renders nodes and edges
3. **Enable interaction**: Click nodes to navigate to source code
4. **Sync with panels**: Highlight corresponding components in outline/walkthrough

### Expected Extension Integration Points:
```javascript
// Load graph data
const graphData = await vscode.workspace.openTextDocument(graphDataPath);
const data = JSON.parse(graphData.getText());

// Render with D3.js 
const svg = d3.select("#graph-container")
  .append("svg")
  .attr("width", width)
  .attr("height", height);

// Add click handlers for navigation
nodes.on("click", (event, d) => {
  if (d.type === "component") {
    // Navigate to component in source code
    navigateToComponent(d.blockId, d.component_number);
  }
});
```

## 🚀 Quick Start

1. **Run Ember Analysis** (if not done):
   ```bash
   # In ember2_working.ipynb, set NOTEBOOK_TO_ANALYZE and run all cells
   ```

2. **Find Available Runs**:
   ```bash
   python3 list_ember_runs.py
   ```

3. **Generate Graphs**:
   ```bash
   python3 generate_d3_graph.py ember/ember_output/your_analysis_run
   ```

4. **View Results**:
   ```bash
   # Open the HTML file in your browser
   open ember/ember_output/your_analysis_run/generated_graphs/graph_visualization.html
   ```

## 📋 Requirements

- Python 3.8+
- Complete ember_output directory with:
  - `step2_analysis/dependency_graph.json`
  - `step3_components/block_details.json`  
  - `step3_components/block_*_components.json`
  - Optional: `step5_walkthrough/walkthrough_data.json`

## 🐛 Troubleshooting

**"Required file not found" error:**
- Ensure you're pointing to a complete analysis run directory
- Run the full Ember analysis pipeline first

**Empty or broken graphs:**
- Check that the analysis completed successfully (5+ steps)
- Verify JSON files aren't corrupted
- Try regenerating the analysis

**HTML visualization not working:**
- Ensure you have internet connection (loads D3.js from CDN)
- Try opening in different browser
- Check browser console for JavaScript errors

## 🎯 Next Steps

The generated graph data is ready for VS Code extension integration. The extension should:

1. Load graph data from `graph_data.json`
2. Implement D3.js rendering in webview panel
3. Add click handlers for source code navigation
4. Sync highlighting with outline and walkthrough panels
5. Support both block and component view modes

This creates the missing link between the analysis pipeline and the interactive VS Code extension! 🔗✨