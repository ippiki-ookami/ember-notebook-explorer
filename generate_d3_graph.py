#!/usr/bin/env python3
"""
D3.js Graph Generator for Ember Analysis Results

This script generates D3.js-compatible graph data from ember_output analysis results.
It creates both block-level and component-level graphs with interactive capabilities.

Usage:
    python generate_d3_graph.py <ember_output_directory>
    python generate_d3_graph.py /path/to/ember_output/tiny_demo_20250806_062811

Output:
    - graph_data.json: Complete D3.js graph data
    - graph_visualization.html: Standalone HTML visualization
    - graph_blocks.json: Block-level graph only
    - graph_components.json: Component-level graph only
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
class GraphNode:
    """Represents a node in the D3.js graph"""
    id: str
    name: str
    type: str
    group: int
    size: int
    color: str
    description: str
    metadata: Dict[str, Any]

@dataclass
class GraphEdge:
    """Represents an edge in the D3.js graph"""
    source: str
    target: str
    type: str
    weight: int
    color: str
    metadata: Dict[str, Any]

class EmberGraphGenerator:
    """Generate D3.js graph data from ember_output directory"""
    
    def __init__(self, ember_output_dir: str):
        self.ember_dir = Path(ember_output_dir)
        self.validate_directory()
        
        # Load all necessary data
        self.dependency_graph = self.load_dependency_graph()
        self.block_details = self.load_block_details()
        self.component_data = self.load_component_data()
        self.walkthrough_data = self.load_walkthrough_data()
        
        # Color schemes
        self.block_colors = self.generate_color_scheme(len(self.block_details))
        self.component_type_colors = {
            "import": "#e74c3c",      # Red
            "class": "#3498db",       # Blue  
            "function": "#2ecc71",    # Green
            "method": "#f39c12",      # Orange
            "variable": "#9b59b6",    # Purple
            "expression": "#1abc9c",  # Teal
            "decorator": "#34495e"    # Dark gray
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
    
    def load_walkthrough_data(self) -> Optional[Dict]:
        """Load walkthrough data if available"""
        path = self.ember_dir / "step5_walkthrough" / "walkthrough_data.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None
    
    def generate_color_scheme(self, num_colors: int) -> List[str]:
        """Generate visually distinct colors for blocks"""
        colors = []
        for i in range(num_colors):
            hue = i / num_colors
            saturation = 0.7
            value = 0.8
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors
    
    def generate_block_graph(self) -> Dict[str, List[Dict]]:
        """Generate block-level D3.js graph data"""
        nodes = []
        edges = []
        
        # Create nodes for each block
        for i, block in enumerate(self.block_details):
            block_id = block["block_id"]
            
            node = {
                "id": block_id,
                "name": block["block_name"],
                "type": "block",
                "blockType": block["block_type"],
                "group": i + 1,
                "size": block["component_count"] * 5 + 20,  # Size based on components
                "color": self.block_colors[i],
                "description": f"Block {block_id}: {block['block_name']} ({block['component_count']} components)",
                "componentCount": block["component_count"],
                "isComplete": block["is_complete"],
                "hasDependencies": block["has_dependencies"],
                "dependencyCount": block["dependency_count"],
                "fx": None,  # Allow D3 to position
                "fy": None
            }
            nodes.append(node)
        
        # Create edges from dependency graph
        for edge in self.dependency_graph["edges"]:
            source_id = edge["from"]
            target_id = edge["to"]
            edge_type = edge["type"]
            
            # Find source block for color
            source_block = next((b for b in self.block_details if b["block_id"] == source_id), None)
            color = self.block_colors[0] if not source_block else self.block_colors[int(source_id) - 1]
            
            graph_edge = {
                "source": source_id,
                "target": target_id,
                "type": edge_type,
                "weight": 1,
                "color": color,
                "strokeWidth": 2
            }
            edges.append(graph_edge)
        
        return {
            "nodes": nodes,
            "links": edges,
            "metadata": {
                "type": "block_level",
                "total_blocks": len(nodes),
                "total_edges": len(edges),
                "execution_order": self.dependency_graph["execution_order"]
            }
        }
    
    def generate_component_graph(self) -> Dict[str, List[Dict]]:
        """Generate component-level D3.js graph data"""
        nodes = []
        edges = []
        
        # Create nodes for each component
        for block_id, components in self.component_data.items():
            block_info = next((b for b in self.block_details if b["block_id"] == block_id), {})
            block_color = self.block_colors[int(block_id) - 1] if block_id.isdigit() else "#95a5a6"
            
            for component in components:
                comp_type = component.get("type", "unknown")
                comp_color = self.component_type_colors.get(comp_type, "#95a5a6")
                
                node = {
                    "id": component["component_id"],
                    "name": component["name"],
                    "type": "component",
                    "componentType": comp_type,
                    "blockId": block_id,
                    "blockName": block_info.get("block_name", f"Block {block_id}"),
                    "group": int(block_id) if block_id.isdigit() else 1,
                    "size": len(component.get("description", "")) // 10 + 10,  # Size based on description
                    "color": comp_color,
                    "blockColor": block_color,
                    "description": component.get("enhanced_description") or component.get("description", ""),
                    "library": component.get("library", ""),
                    "code": component.get("full_code", ""),
                    "isResolved": component.get("is_resolved", False),
                    "externalDependencies": component.get("external_dependencies", []),
                    "fx": None,
                    "fy": None
                }
                nodes.append(node)
        
        # Create edges between components (simplified - could be enhanced)
        # For now, create edges based on block dependencies
        for edge in self.dependency_graph["edges"]:
            source_block = edge["from"]
            target_block = edge["to"]
            
            # Connect components between dependent blocks
            source_components = [n for n in nodes if n["blockId"] == source_block]
            target_components = [n for n in nodes if n["blockId"] == target_block]
            
            if source_components and target_components:
                # Connect first component of source to first component of target
                # In practice, you'd want more sophisticated component-level dependency analysis
                source_comp = source_components[0]
                target_comp = target_components[0]
                
                graph_edge = {
                    "source": source_comp["id"],
                    "target": target_comp["id"],
                    "type": "block_dependency",
                    "weight": 1,
                    "color": "#bdc3c7",
                    "strokeWidth": 1,
                    "sourceBlock": source_block,
                    "targetBlock": target_block
                }
                edges.append(graph_edge)
        
        return {
            "nodes": nodes,
            "links": edges,
            "metadata": {
                "type": "component_level",
                "total_components": len(nodes),
                "total_edges": len(edges),
                "blocks_represented": len(set(n["blockId"] for n in nodes)),
                "component_types": list(set(n["componentType"] for n in nodes))
            }
        }
    
    def generate_combined_graph(self) -> Dict[str, Any]:
        """Generate combined graph with both blocks and components"""
        block_graph = self.generate_block_graph()
        component_graph = self.generate_component_graph()
        
        # Combine with hierarchical structure
        combined = {
            "blocks": block_graph,
            "components": component_graph,
            "metadata": {
                "type": "combined",
                "analysis_directory": str(self.ember_dir),
                "total_blocks": len(block_graph["nodes"]),
                "total_components": len(component_graph["nodes"]),
                "has_walkthrough": self.walkthrough_data is not None,
                "execution_order": self.dependency_graph["execution_order"],
                "color_schemes": {
                    "blocks": self.block_colors,
                    "component_types": self.component_type_colors
                }
            }
        }
        
        if self.walkthrough_data:
            combined["walkthrough"] = {
                "introduction": self.walkthrough_data["introduction"],
                "sections": len(self.walkthrough_data["sections"]),
                "coverage_percentage": self.walkthrough_data["coverage_percentage"]
            }
        
        return combined
    
    def save_graph_data(self, output_dir: Optional[str] = None) -> str:
        """Save all graph data to JSON files"""
        if output_dir is None:
            output_dir = self.ember_dir / "generated_graphs"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # Generate all graph types
        block_graph = self.generate_block_graph()
        component_graph = self.generate_component_graph()
        combined_graph = self.generate_combined_graph()
        
        # Save individual files
        files_saved = []
        
        with open(output_dir / "graph_blocks.json", "w") as f:
            json.dump(block_graph, f, indent=2)
            files_saved.append("graph_blocks.json")
        
        with open(output_dir / "graph_components.json", "w") as f:
            json.dump(component_graph, f, indent=2)
            files_saved.append("graph_components.json")
        
        with open(output_dir / "graph_data.json", "w") as f:
            json.dump(combined_graph, f, indent=2)
            files_saved.append("graph_data.json")
        
        print(f"📊 Generated graph data files:")
        for filename in files_saved:
            print(f"   ✅ {output_dir / filename}")
        
        return str(output_dir)
    
    def generate_html_visualization(self, output_dir: Optional[str] = None) -> str:
        """Generate standalone HTML visualization"""
        if output_dir is None:
            output_dir = self.ember_dir / "generated_graphs"
        else:
            output_dir = Path(output_dir)
        
        # Generate graph data
        combined_graph = self.generate_combined_graph()
        
        # HTML template with D3.js visualization
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ember Analysis Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
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
        
        button.active {{
            background: #e74c3c;
        }}
        
        #graph {{
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }}
        
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            pointer-events: none;
            font-size: 12px;
            max-width: 300px;
            z-index: 1000;
        }}
        
        .node {{
            cursor: pointer;
            stroke: #fff;
            stroke-width: 2px;
        }}
        
        .link {{
            fill: none;
            stroke-opacity: 0.6;
        }}
        
        .node-label {{
            font-size: 12px;
            text-anchor: middle;
            pointer-events: none;
            fill: #333;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            gap: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            flex: 1;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .legend-item {{
            display: inline-block;
            margin: 5px 10px;
        }}
        
        .legend-color {{
            display: inline-block;
            width: 15px;
            height: 15px;
            margin-right: 5px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Ember Analysis Graph Visualization</h1>
            <p>Analysis from: {self.ember_dir.name}</p>
        </div>
        
        <div class="controls">
            <button id="blockView" class="active" onclick="showBlockView()">Block View</button>
            <button id="componentView" onclick="showComponentView()">Component View</button>
            <button onclick="resetZoom()">Reset Zoom</button>
            <button onclick="toggleLabels()">Toggle Labels</button>
        </div>
        
        <svg id="graph"></svg>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(combined_graph['blocks']['nodes'])}</div>
                <div>Code Blocks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(combined_graph['components']['nodes'])}</div>
                <div>Components</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(combined_graph['blocks']['links'])}</div>
                <div>Dependencies</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{combined_graph.get('walkthrough', {}).get('coverage_percentage', 0):.0f}%</div>
                <div>Coverage</div>
            </div>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div id="block-legend">
                <strong>Block Types:</strong><br>
                <span class="legend-item"><span class="legend-color" style="background: #e74c3c;"></span>Imports</span>
                <span class="legend-item"><span class="legend-color" style="background: #3498db;"></span>Classes</span>
                <span class="legend-item"><span class="legend-color" style="background: #2ecc71;"></span>Functions</span>
                <span class="legend-item"><span class="legend-color" style="background: #f39c12;"></span>Utilities</span>
                <span class="legend-item"><span class="legend-color" style="background: #9b59b6;"></span>Config</span>
            </div>
            <div id="component-legend" style="display: none;">
                <strong>Component Types:</strong><br>
                <span class="legend-item"><span class="legend-color" style="background: #e74c3c;"></span>Imports</span>
                <span class="legend-item"><span class="legend-color" style="background: #3498db;"></span>Classes</span>
                <span class="legend-item"><span class="legend-color" style="background: #2ecc71;"></span>Functions</span>
                <span class="legend-item"><span class="legend-color" style="background: #f39c12;"></span>Methods</span>
                <span class="legend-item"><span class="legend-color" style="background: #9b59b6;"></span>Variables</span>
                <span class="legend-item"><span class="legend-color" style="background: #1abc9c;"></span>Expressions</span>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip" style="display: none;"></div>
    
    <script>
        // Graph data
        const graphData = {json.dumps(combined_graph, indent=8)};
        
        // D3.js visualization setup
        const width = 1160;
        const height = 600;
        
        const svg = d3.select("#graph")
            .attr("width", width)
            .attr("height", height);
        
        const g = svg.append("g");
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
        
        svg.call(zoom);
        
        // Tooltip
        const tooltip = d3.select("#tooltip");
        
        let currentView = "blocks";
        let showLabels = true;
        let simulation;
        
        function showBlockView() {{
            currentView = "blocks";
            document.getElementById("blockView").classList.add("active");
            document.getElementById("componentView").classList.remove("active");
            document.getElementById("block-legend").style.display = "block";
            document.getElementById("component-legend").style.display = "none";
            renderGraph(graphData.blocks);
        }}
        
        function showComponentView() {{
            currentView = "components";
            document.getElementById("componentView").classList.add("active");
            document.getElementById("blockView").classList.remove("active");
            document.getElementById("block-legend").style.display = "none";
            document.getElementById("component-legend").style.display = "block";
            renderGraph(graphData.components);
        }}
        
        function resetZoom() {{
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity
            );
        }}
        
        function toggleLabels() {{
            showLabels = !showLabels;
            d3.selectAll(".node-label")
                .style("display", showLabels ? "block" : "none");
        }}
        
        function renderGraph(data) {{
            // Clear previous graph
            g.selectAll("*").remove();
            
            // Stop any existing simulation
            if (simulation) simulation.stop();
            
            // Create simulation
            simulation = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(d => d.size + 5));
            
            // Create links
            const link = g.append("g")
                .selectAll("line")
                .data(data.links)
                .enter().append("line")
                .attr("class", "link")
                .style("stroke", d => d.color)
                .style("stroke-width", d => d.strokeWidth || 2);
            
            // Create nodes
            const node = g.append("g")
                .selectAll("circle")
                .data(data.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", d => d.size)
                .style("fill", d => d.color)
                .on("mouseover", (event, d) => {{
                    tooltip.style("display", "block")
                        .html(`
                            <strong>${{d.name}}</strong><br>
                            Type: ${{d.type}}<br>
                            ${{d.description}}<br>
                            ${{currentView === "components" ? `Library: ${{d.library}}<br>Block: ${{d.blockName}}` : `Components: ${{d.componentCount}}`}}
                        `)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", () => {{
                    tooltip.style("display", "none");
                }})
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // Add labels
            const labels = g.append("g")
                .selectAll("text")
                .data(data.nodes)
                .enter().append("text")
                .attr("class", "node-label")
                .text(d => d.name.length > 20 ? d.name.substring(0, 17) + "..." : d.name)
                .style("display", showLabels ? "block" : "none");
            
            // Update positions on simulation tick
            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                labels
                    .attr("x", d => d.x)
                    .attr("y", d => d.y + d.size + 15);
            }});
        }}
        
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Initialize with block view
        showBlockView();
    </script>
</body>
</html>"""
        
        html_path = output_dir / "graph_visualization.html"
        with open(html_path, "w") as f:
            f.write(html_template)
        
        print(f"🌐 Generated HTML visualization: {html_path}")
        return str(html_path)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Generate D3.js graph data from Ember analysis results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_d3_graph.py ember/ember_output/tiny_demo_20250806_062811
  python generate_d3_graph.py /path/to/analysis --output /path/to/graphs
  python generate_d3_graph.py analysis_dir --html-only
        """
    )
    
    parser.add_argument(
        "ember_directory",
        help="Path to ember_output analysis directory"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output directory for generated files (default: <ember_dir>/generated_graphs)"
    )
    
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Generate only HTML visualization, skip JSON files"
    )
    
    parser.add_argument(
        "--blocks-only",
        action="store_true", 
        help="Generate only block-level graph"
    )
    
    parser.add_argument(
        "--components-only",
        action="store_true",
        help="Generate only component-level graph"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        print(f"🚀 Initializing Ember Graph Generator...")
        generator = EmberGraphGenerator(args.ember_directory)
        
        # Generate output
        if args.html_only:
            print("📊 Generating HTML visualization only...")
            html_path = generator.generate_html_visualization(args.output)
            print(f"✅ Complete! Open in browser: {html_path}")
        else:
            print("📊 Generating graph data files...")
            output_dir = generator.save_graph_data(args.output)
            
            print("🌐 Generating HTML visualization...")
            html_path = generator.generate_html_visualization(output_dir)
            
            print(f"\n✅ Graph generation complete!")
            print(f"📁 Output directory: {output_dir}")
            print(f"🌐 HTML visualization: {html_path}")
            print(f"\n🎯 To view: open {Path(html_path).name} in your browser")
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you're pointing to a complete ember_output directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()