#!/usr/bin/env python3
"""
Hierarchical Flowchart Generator for Ember Analysis Results

Creates a structured, top-to-bottom flowchart similar to the reference image,
with grouped components within blocks and clear execution flow.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import colorsys

@dataclass
class FlowchartBlock:
    """Represents a block in the hierarchical flowchart"""
    id: str
    name: str
    type: str
    components: List[Dict]
    x: int
    y: int
    width: int
    height: int
    color: str
    level: int  # Hierarchy level for positioning

class EmberHierarchicalGenerator:
    """Generate hierarchical flowchart from ember_output directory"""
    
    def __init__(self, ember_output_dir: str):
        self.ember_dir = Path(ember_output_dir)
        self.validate_directory()
        
        # Load all necessary data
        self.dependency_graph = self.load_dependency_graph()
        self.block_details = self.load_block_details()
        self.component_data = self.load_component_data()
        
        # Layout configuration
        self.block_width = 300
        self.block_min_height = 120
        self.component_height = 30
        self.component_padding = 5
        self.block_margin_x = 50
        self.block_margin_y = 80
        self.level_height = 200
        
        # Color schemes - darker, more professional
        self.block_type_colors = {
            "imports": "#2c3e50",      # Dark blue-gray
            "classes": "#8e44ad",      # Purple
            "utilities": "#27ae60",    # Green
            "functions": "#e67e22",    # Orange
            "mixed": "#34495e",        # Dark gray
            "config": "#16a085"        # Teal
        }
        
        self.component_type_colors = {
            "import": "#3498db",       # Blue
            "class": "#9b59b6",        # Light purple
            "function": "#2ecc71",     # Light green
            "method": "#e74c3c",       # Red
            "variable": "#f39c12",     # Orange
            "expression": "#1abc9c",   # Teal
            "decorator": "#95a5a6"     # Gray
        }
    
    def validate_directory(self):
        """Ensure the ember_output directory has the required structure"""
        required_files = [
            "step2_analysis/dependency_graph.json",
            "step3_components/block_details.json"
        ]
        
        for file_path in required_files:
            full_path = self.ember_dir / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"Required file not found: {full_path}")
        
        print(f"✅ Validated ember_output directory: {self.ember_dir}")
    
    def load_dependency_graph(self) -> Dict:
        """Load block-level dependency graph"""
        path = self.ember_dir / "step2_analysis" / "dependency_graph.json"
        with open(path) as f:
            return json.load(f)
    
    def load_block_details(self) -> List[Dict]:
        """Load block details and metadata"""
        path = self.ember_dir / "step3_components" / "block_details.json"
        with open(path) as f:
            return json.load(f)
    
    def load_component_data(self) -> Dict[str, List[Dict]]:
        """Load component data for all blocks"""
        components = {}
        component_dir = self.ember_dir / "step3_components"
        
        for block in self.block_details:
            block_id = block["block_id"]
            component_file = component_dir / f"block_{block_id}_components.json"
            
            if component_file.exists():
                with open(component_file) as f:
                    components[block_id] = json.load(f)
            else:
                components[block_id] = []
        
        return components
    
    def calculate_hierarchy_levels(self) -> Dict[str, int]:
        """Calculate the hierarchy level for each block based on dependencies"""
        levels = {}
        execution_order = self.dependency_graph["execution_order"]
        
        # Simple approach: use execution order as hierarchy
        for i, block_id in enumerate(execution_order):
            levels[block_id] = i
        
        return levels
    
    def calculate_block_dimensions(self, components: List[Dict]) -> Tuple[int, int]:
        """Calculate width and height needed for a block based on its components"""
        # Height: base height + (component_count * component_height) + padding
        component_count = len(components)
        height = max(
            self.block_min_height,
            60 + (component_count * (self.component_height + self.component_padding)) + 20
        )
        
        # Width: fixed width but could be dynamic based on longest component name
        max_name_length = max((len(comp.get("name", "")) for comp in components), default=10)
        width = max(self.block_width, min(400, max_name_length * 8 + 100))
        
        return width, height
    
    def position_blocks_hierarchically(self) -> List[FlowchartBlock]:
        """Position blocks in a hierarchical layout"""
        levels = self.calculate_hierarchy_levels()
        positioned_blocks = []
        
        # Group blocks by level
        blocks_by_level = {}
        for block in self.block_details:
            block_id = block["block_id"]
            level = levels.get(block_id, 0)
            if level not in blocks_by_level:
                blocks_by_level[level] = []
            blocks_by_level[level].append(block)
        
        # Calculate total width needed for each level
        canvas_width = 1200  # Base canvas width
        start_x = 50
        
        for level, blocks in blocks_by_level.items():
            # Calculate positions for blocks at this level
            total_blocks = len(blocks)
            
            if total_blocks == 1:
                # Center single block
                x_positions = [canvas_width // 2 - self.block_width // 2]
            else:
                # Distribute multiple blocks evenly
                available_width = canvas_width - (2 * start_x)
                spacing = available_width / total_blocks
                x_positions = []
                for i in range(total_blocks):
                    x = start_x + (i * spacing) + (spacing - self.block_width) // 2
                    x_positions.append(int(x))
            
            # Create positioned blocks
            for i, block in enumerate(blocks):
                block_id = block["block_id"]
                components = self.component_data.get(block_id, [])
                width, height = self.calculate_block_dimensions(components)
                
                flowchart_block = FlowchartBlock(
                    id=block_id,
                    name=block["block_name"],
                    type=block["block_type"],
                    components=components,
                    x=x_positions[i],
                    y=level * self.level_height + 50,
                    width=width,
                    height=height,
                    color=self.block_type_colors.get(block["block_type"], "#34495e"),
                    level=level
                )
                positioned_blocks.append(flowchart_block)
        
        return positioned_blocks
    
    def generate_hierarchical_data(self) -> Dict[str, Any]:
        """Generate hierarchical flowchart data"""
        positioned_blocks = self.position_blocks_hierarchically()
        
        # Create flowchart data structure
        flowchart_data = {
            "type": "hierarchical_flowchart",
            "canvas": {
                "width": 1200,
                "height": max(block.y + block.height for block in positioned_blocks) + 100
            },
            "blocks": [],
            "connections": [],
            "metadata": {
                "total_blocks": len(positioned_blocks),
                "execution_order": self.dependency_graph["execution_order"],
                "analysis_directory": str(self.ember_dir)
            }
        }
        
        # Add block data
        for block in positioned_blocks:
            block_data = {
                "id": block.id,
                "name": block.name,
                "type": block.type,
                "x": block.x,
                "y": block.y,
                "width": block.width,
                "height": block.height,
                "color": block.color,
                "level": block.level,
                "components": []
            }
            
            # Add component data within block
            for i, component in enumerate(block.components):
                comp_y = block.y + 50 + (i * (self.component_height + self.component_padding))
                component_data = {
                    "id": component.get("component_id", f"{block.id}:{i}"),
                    "name": component.get("name", "unknown"),
                    "type": component.get("type", "unknown"),
                    "x": block.x + 10,
                    "y": comp_y,
                    "width": block.width - 20,
                    "height": self.component_height,
                    "color": self.component_type_colors.get(component.get("type", "unknown"), "#95a5a6"),
                    "description": component.get("description", ""),
                    "library": component.get("library", ""),
                    "code": component.get("full_code", "")
                }
                block_data["components"].append(component_data)
            
            flowchart_data["blocks"].append(block_data)
        
        # Add connections between blocks
        for edge in self.dependency_graph["edges"]:
            source_block = next((b for b in positioned_blocks if b.id == edge["from"]), None)
            target_block = next((b for b in positioned_blocks if b.id == edge["to"]), None)
            
            if source_block and target_block:
                connection = {
                    "source": edge["from"],
                    "target": edge["to"],
                    "type": edge["type"],
                    "points": [
                        {
                            "x": source_block.x + source_block.width // 2,
                            "y": source_block.y + source_block.height
                        },
                        {
                            "x": target_block.x + target_block.width // 2,
                            "y": target_block.y
                        }
                    ]
                }
                flowchart_data["connections"].append(connection)
        
        return flowchart_data
    
    def generate_hierarchical_html(self, flowchart_data: Dict) -> str:
        """Generate HTML visualization for hierarchical flowchart"""
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ember Hierarchical Flowchart</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #2c3e50;
            color: white;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }}
        
        .controls {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        button {{
            padding: 10px 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }}
        
        button:hover {{
            background: #2980b9;
        }}
        
        #flowchart {{
            width: 100%;
            height: {flowchart_data['canvas']['height']}px;
            border: 1px solid #34495e;
            border-radius: 8px;
            background: #34495e;
            overflow: auto;
        }}
        
        /* outer group boxes — dashed outlines, no fill */
        .block {{
            fill: none;
            stroke-width: 2;
            stroke-dasharray: 4,4;
            stroke: #ffffff80;   /* semiopaque white */
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .block:hover {{
            stroke-width: 3;
            stroke-dasharray: none;
        }}
        
        /* the inner "boxes" — solid fill, rounded */
        .component {{
            stroke: none;
            fill-opacity: 1;
            rx: 5px;
            ry: 5px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .component:hover {{
            opacity: 0.9;
        }}
        
        .block-title {{
            font-size: 12px;
            font-weight: bold;
            text-anchor: start;       /* left‐aligned */
            fill: white;
            pointer-events: none;
            /* position will be set in JS */
        }}
        
        .component-label {{
            font-size: 11px;
            text-anchor: start;
            fill: white;
            pointer-events: none;
        }}
        
        .connection {{
            stroke: #7f8c8d;
            stroke-width: 2;
            fill: none;
            marker-end: url(#arrowhead);
        }}
        
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 10px;
            border-radius: 5px;
            pointer-events: none;
            font-size: 12px;
            max-width: 300px;
            z-index: 1000;
            border: 1px solid #7f8c8d;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            gap: 20px;
        }}
        
        .stat-card {{
            background: #34495e;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            text-align: center;
            flex: 1;
            border: 1px solid #7f8c8d;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .legend {{
            background: #34495e;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            border: 1px solid #7f8c8d;
        }}
        
        .legend-item {{
            display: inline-block;
            margin: 5px 10px;
            color: white;
        }}
        
        .legend-color {{
            display: inline-block;
            width: 15px;
            height: 15px;
            margin-right: 5px;
            border: 1px solid #bdc3c7;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Ember Hierarchical Flowchart</h1>
            <p>Analysis: {self.ember_dir.name}</p>
        </div>
        
        <div class="controls">
            <button onclick="resetView()">Reset View</button>
            <button onclick="toggleComponents()">Toggle Components</button>
            <button onclick="exportSVG()">Export SVG</button>
        </div>
        
        <svg id="flowchart" width="{flowchart_data['canvas']['width']}" height="{flowchart_data['canvas']['height']}">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                        refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#7f8c8d" />
                </marker>
            </defs>
        </svg>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(flowchart_data['blocks'])}</div>
                <div>Code Blocks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{sum(len(block['components']) for block in flowchart_data['blocks'])}</div>
                <div>Components</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(flowchart_data['connections'])}</div>
                <div>Dependencies</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{max((block['level'] for block in flowchart_data['blocks']), default=0) + 1}</div>
                <div>Levels</div>
            </div>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div>
                <strong>Block Types:</strong><br>
                <span class="legend-item"><span class="legend-color" style="background: #2c3e50;"></span>Imports</span>
                <span class="legend-item"><span class="legend-color" style="background: #8e44ad;"></span>Classes</span>
                <span class="legend-item"><span class="legend-color" style="background: #27ae60;"></span>Utilities</span>
                <span class="legend-item"><span class="legend-color" style="background: #e67e22;"></span>Functions</span>
                <span class="legend-item"><span class="legend-color" style="background: #34495e;"></span>Mixed</span>
                <span class="legend-item"><span class="legend-color" style="background: #16a085;"></span>Config</span>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip" style="display: none;"></div>
    
    <script>
        // Flowchart data
        const flowchartData = {json.dumps(flowchart_data, indent=8)};
        
        const svg = d3.select("#flowchart");
        const tooltip = d3.select("#tooltip");
        
        let showComponents = true;
        
        function renderFlowchart() {{
            // Clear previous content
            svg.selectAll("*").remove();
            
            // Re-add arrow marker
            svg.append("defs")
                .append("marker")
                .attr("id", "arrowhead")
                .attr("markerWidth", 10)
                .attr("markerHeight", 7)
                .attr("refX", 9)
                .attr("refY", 3.5)
                .attr("orient", "auto")
                .append("polygon")
                .attr("points", "0 0, 10 3.5, 0 7")
                .attr("fill", "#7f8c8d");
            
            // Draw connections first (so they appear behind blocks)
            svg.selectAll(".connection")
                .data(flowchartData.connections)
                .enter()
                .append("path")
                .attr("class", "connection")
                .attr("d", d => {{
                    const points = d.points;
                    return `M ${{points[0].x}} ${{points[0].y}} L ${{points[1].x}} ${{points[1].y}}`;
                }});
            
            // Draw blocks
            const blockGroups = svg.selectAll(".block-group")
                .data(flowchartData.blocks)
                .enter()
                .append("g")
                .attr("class", "block-group");
            
            // Block rectangles
            blockGroups.append("rect")
                .attr("class", "block")
                .attr("x", d => d.x)
                .attr("y", d => d.y)
                .attr("width", d => d.width)
                .attr("height", d => d.height)
                .attr("fill", d => d.color)
                .on("mouseover", (event, d) => {{
                    tooltip.style("display", "block")
                        .html(`
                            <strong>${{d.name}}</strong><br>
                            Type: ${{d.type}}<br>
                            Level: ${{d.level}}<br>
                            Components: ${{d.components.length}}
                        `)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", () => {{
                    tooltip.style("display", "none");
                }});
            
            // Block titles
            blockGroups.append("text")
                .attr("class", "block-title")
                .attr("x", d => d.x + 10)      // 10px from left edge
                .attr("y", d => d.y + 18)      // 18px down from top edge
                .text(d => d.name);
            
            // Components within blocks
            if (showComponents) {{
                blockGroups.each(function(blockData) {{
                    const blockGroup = d3.select(this);
                    
                    blockGroup.selectAll(".component")
                        .data(blockData.components)
                        .enter()
                        .append("rect")
                        .attr("class", "component")
                        .attr("x", d => d.x)
                        .attr("y", d => d.y)
                        .attr("width", d => d.width)
                        .attr("height", d => d.height)
                        .attr("fill", d => d.color)
                        .attr("rx", 4)
                        .attr("ry", 4)
                        .on("mouseover", (event, d) => {{
                            tooltip.style("display", "block")
                                .html(`
                                    <strong>${{d.name}}</strong><br>
                                    Type: ${{d.type}}<br>
                                    Library: ${{d.library}}<br>
                                    <em>${{d.description.substring(0, 100)}}${{d.description.length > 100 ? "..." : ""}}</em>
                                `)
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        }})
                        .on("mouseout", () => {{
                            tooltip.style("display", "none");
                        }});
                    
                    // Component labels
                    blockGroup.selectAll(".component-label")
                        .data(blockData.components)
                        .enter()
                        .append("text")
                        .attr("class", "component-label")
                        .attr("x", d => d.x + 8)
                        .attr("y", d => d.y + d.height / 2 + 4)
                        .attr("fill", "white")
                        .text(d => d.name);
                }});
            }}
        }}
        
        function resetView() {{
            renderFlowchart();
        }}
        
        function toggleComponents() {{
            showComponents = !showComponents;
            renderFlowchart();
        }}
        
        function exportSVG() {{
            const svgElement = document.getElementById("flowchart");
            const svgData = new XMLSerializer().serializeToString(svgElement);
            const blob = new Blob([svgData], {{type: "image/svg+xml"}});
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "ember_flowchart.svg";
            link.click();
            URL.revokeObjectURL(url);
        }}
        
        // Initial render
        renderFlowchart();
    </script>
</body>
</html>"""
        
        return html_template
    
    def save_hierarchical_visualization(self, output_dir: Optional[str] = None) -> str:
        """Save hierarchical flowchart visualization"""
        if output_dir is None:
            output_dir = self.ember_dir / "generated_graphs"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # Generate flowchart data
        flowchart_data = self.generate_hierarchical_data()
        
        # Save JSON data
        json_path = output_dir / "hierarchical_flowchart.json"
        with open(json_path, "w") as f:
            json.dump(flowchart_data, f, indent=2)
        
        # Generate and save HTML
        html_content = self.generate_hierarchical_html(flowchart_data)
        html_path = output_dir / "hierarchical_flowchart.html"
        with open(html_path, "w") as f:
            f.write(html_content)
        
        print(f"📊 Generated hierarchical flowchart:")
        print(f"   ✅ Data: {json_path}")
        print(f"   ✅ HTML: {html_path}")
        
        return str(html_path)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Generate hierarchical flowchart from Ember analysis results"
    )
    
    parser.add_argument(
        "ember_directory",
        help="Path to ember_output analysis directory"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output directory for generated files (default: <ember_dir>/generated_graphs)"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"🚀 Generating hierarchical flowchart...")
        generator = EmberHierarchicalGenerator(args.ember_directory)
        
        html_path = generator.save_hierarchical_visualization(args.output)
        
        print(f"\n✅ Hierarchical flowchart complete!")
        print(f"🌐 Open in browser: {html_path}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()