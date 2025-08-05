"""
VS Code Extension Integration Module
Bridges the new component-based analysis with the VS Code extension
"""

import json
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import asyncio

# Import our new analysis components
from ember2_integration import (
    run_complete_analysis,
    WalkthroughState,
    ComponentState,
    BlockState
)

@dataclass
class VSCodeNode:
    """Node format expected by VS Code extension"""
    id: str
    type: str  # 'block' | 'class' | 'function' | 'method' | 'import' | 'variable' | 'expression'
    name: str
    content: str
    cellIndex: int
    lineInCell: int
    lineInNotebook: int
    children: List['VSCodeNode'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "content": self.content,
            "cellIndex": self.cellIndex,
            "lineInCell": self.lineInCell,
            "lineInNotebook": self.lineInNotebook,
            "children": [child.to_dict() for child in self.children],
            "dependencies": self.dependencies,
            "metadata": self.metadata or {}
        }

@dataclass
class VSCodeEdge:
    """Edge format for VS Code graph"""
    source: str
    target: str
    type: str  # 'uses' | 'bidirectional' | 'calls' | 'inherits'
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type
        }

@dataclass
class VSCodePhase:
    """Phase format for VS Code extension"""
    id: str
    name: str
    summary: str
    components: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)

class ComponentToVSCodeConverter:
    """Converts our component-based analysis to VS Code extension format"""
    
    def __init__(self, walkthrough_state: WalkthroughState):
        self.state = walkthrough_state
        self.nodes: List[VSCodeNode] = []
        self.edges: List[VSCodeEdge] = []
        self.phases: List[VSCodePhase] = []
        self.node_map: Dict[str, VSCodeNode] = {}
        
    def convert(self) -> Dict[str, Any]:
        """Convert walkthrough state to VS Code format"""
        
        # 1. Create phase groups
        self._create_phases()
        
        # 2. Convert blocks and components to nodes
        self._convert_blocks_to_nodes()
        
        # 3. Create edges from dependencies
        self._create_edges()
        
        # 4. Build nested structure
        self._build_hierarchy()
        
        return {
            "graph": {
                "nodes": [node.to_dict() for node in self.nodes],
                "edges": [edge.to_dict() for edge in self.edges]
            },
            "phases": [phase.to_dict() for phase in self.phases],
            "walkthrough": self._get_walkthrough_data()
        }
    
    def _create_phases(self):
        """Create phases from analysis phases"""
        # We'll group by block types for now
        phase_map = {
            "imports": VSCodePhase("1", "Imports & Setup", "Library imports and initial configuration"),
            "utilities": VSCodePhase("2", "Utility Functions", "Helper functions and utilities"),
            "classes": VSCodePhase("3", "Class Definitions", "Main classes and data structures"),
            "main": VSCodePhase("4", "Main Logic", "Core processing and execution"),
            "config": VSCodePhase("5", "Configuration", "Settings and parameters")
        }
        
        # Assign components to phases based on block type
        for block_id, block_state in self.state.block_states.items():
            phase = phase_map.get(block_state.block_type)
            if phase:
                # Add all component IDs from this block to the phase
                for comp_id in block_state.component_states.keys():
                    phase.components.append(comp_id)
        
        self.phases = list(phase_map.values())
    
    def _convert_blocks_to_nodes(self):
        """Convert blocks and their components to VS Code nodes"""
        line_offset = 0
        
        for block_idx, (block_id, block_state) in enumerate(self.state.block_states.items()):
            # Create block node
            block_node = VSCodeNode(
                id=f"block_{block_id}",
                type="block",
                name=block_state.block_name,
                content=block_state.block_content,
                cellIndex=block_idx,
                lineInCell=0,
                lineInNotebook=line_offset,
                metadata={"block_id": block_id, "block_type": block_state.block_type}
            )
            
            self.nodes.append(block_node)
            self.node_map[block_node.id] = block_node
            
            # Convert components within block
            self._convert_components(block_state, block_node, block_idx, line_offset)
            
            # Update line offset for next block
            line_offset += len(block_state.block_content.split('\n')) + 1
    
    def _convert_components(self, block_state: BlockState, block_node: VSCodeNode, 
                           cell_index: int, line_offset: int):
        """Convert components to nodes with proper nesting"""
        
        # Group components by parent for nesting
        parent_map: Dict[Optional[str], List[ComponentState]] = {}
        
        for comp_state in block_state.component_states.values():
            # Determine parent
            parent_id = None
            if comp_state.parent_component_ids:
                parent_id = comp_state.parent_component_ids[0]  # Use first parent
            
            if parent_id not in parent_map:
                parent_map[parent_id] = []
            parent_map[parent_id].append(comp_state)
        
        # First create top-level components (no parent)
        for comp_state in parent_map.get(None, []):
            comp_node = self._create_component_node(
                comp_state, block_state.block_id, cell_index, line_offset
            )
            block_node.children.append(comp_node)
            self.node_map[comp_node.id] = comp_node
            
            # Recursively add children
            self._add_child_components(comp_state.component_id, parent_map, 
                                      comp_node, cell_index, line_offset)
    
    def _create_component_node(self, comp_state: ComponentState, block_id: str,
                              cell_index: int, line_offset: int) -> VSCodeNode:
        """Create a VS Code node from a component"""
        # Map component types to VS Code types
        type_map = {
            "class": "class",
            "function": "function",
            "method": "method",
            "import": "import",
            "variable": "variable",
            "expression": "expression",
            "decorator": "decorator"
        }
        
        return VSCodeNode(
            id=comp_state.component_id,
            type=type_map.get(comp_state.type, "variable"),
            name=comp_state.component_name,
            content=comp_state.full_code,
            cellIndex=cell_index,
            lineInCell=comp_state.line_start,
            lineInNotebook=line_offset + comp_state.line_start,
            dependencies=comp_state.calls_component_ids,
            metadata={
                "component_number": comp_state.component_number,
                "library": comp_state.library,
                "description": comp_state.enhanced_description or comp_state.description
            }
        )
    
    def _add_child_components(self, parent_id: str, parent_map: Dict, 
                             parent_node: VSCodeNode, cell_index: int, line_offset: int):
        """Recursively add child components"""
        children = parent_map.get(parent_id, [])
        for child_comp in children:
            child_node = self._create_component_node(
                child_comp, parent_id.split(':')[0], cell_index, line_offset
            )
            parent_node.children.append(child_node)
            self.node_map[child_node.id] = child_node
            
            # Recurse for grandchildren
            self._add_child_components(child_comp.component_id, parent_map,
                                      child_node, cell_index, line_offset)
    
    def _create_edges(self):
        """Create edges between components based on dependencies"""
        for block_state in self.state.block_states.values():
            for comp_state in block_state.component_states.values():
                source_id = comp_state.component_id
                
                # Create edges for calls
                for target_id in comp_state.calls_component_ids:
                    self.edges.append(VSCodeEdge(
                        source=source_id,
                        target=target_id,
                        type="calls"
                    ))
                
                # Create edges for external dependencies
                for dep_id in comp_state.external_dependencies:
                    self.edges.append(VSCodeEdge(
                        source=source_id,
                        target=dep_id,
                        type="uses"
                    ))
        
        # Add block-level dependencies
        for block_id, block_state in self.state.block_states.items():
            source = f"block_{block_id}"
            for dep_block_id in block_state.depends_on_blocks:
                target = f"block_{dep_block_id}"
                self.edges.append(VSCodeEdge(
                    source=source,
                    target=target,
                    type="uses"
                ))
    
    def _build_hierarchy(self):
        """Build the final hierarchical structure"""
        # Already handled in _convert_components with parent-child relationships
        pass
    
    def _get_walkthrough_data(self) -> Optional[Dict]:
        """Get walkthrough data if available"""
        # This will be populated after walkthrough generation
        # For now, return None
        return None

async def analyze_notebook_for_vscode(notebook_path: str) -> Dict[str, Any]:
    """
    Main entry point for VS Code extension integration
    Returns JSON data in the format expected by the extension
    """
    try:
        # Run our complete analysis pipeline
        walkthrough_state = await run_complete_analysis(notebook_path)
        
        # Convert to VS Code format
        converter = ComponentToVSCodeConverter(walkthrough_state)
        return converter.convert()
        
    except Exception as e:
        return {
            "error": str(e),
            "graph": {"nodes": [], "edges": []},
            "phases": []
        }

if __name__ == "__main__":
    # Command-line interface for VS Code extension
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze notebook for VS Code extension")
    parser.add_argument("notebook", help="Path to notebook file")
    parser.add_argument("--export-json", action="store_true", help="Export as JSON")
    
    args = parser.parse_args()
    
    if args.export_json:
        # Run async analysis
        result = asyncio.run(analyze_notebook_for_vscode(args.notebook))
        
        # Output JSON to stdout
        print(json.dumps(result))
    else:
        print("Please use --export-json flag for VS Code integration", file=sys.stderr)
        sys.exit(1)