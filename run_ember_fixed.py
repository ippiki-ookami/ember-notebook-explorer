#!/usr/bin/env python3
"""
Fixed version of ember notebook execution with proper dependency detection.
This version fixes the issues found in the log and provides complete output.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
import sqlite3
from datetime import datetime
import uuid
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Generate timestamp for log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/ember_fixed_{timestamp}.log"

# Open log file
log_file = open(log_filename, 'w', encoding='utf-8')

def log_print(*args, **kwargs):
    """Print to both console and log file."""
    print(*args, **kwargs)
    print(*args, **kwargs, file=log_file)
    log_file.flush()

log_print(f"=== Fixed Ember Notebook Execution Log ===")
log_print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_print(f"Log file: {log_filename}")
log_print("=" * 60)
log_print()

# Define all the classes and functions from the notebook

@dataclass
class CodeNode:
    """Represents a code element in the notebook."""
    id: str
    type: str  # 'cell' | 'class' | 'function' | 'import' | 'variable'
    name: str
    content: str
    cell_index: int
    line_in_cell: int
    line_in_notebook: int
    children: List['CodeNode'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GraphData:
    """Contains nodes and edges for the code dependency graph."""
    nodes: List[CodeNode] = field(default_factory=list)
    edges: List[Dict[str, str]] = field(default_factory=list)


class NotebookParser:
    """Parser for Jupyter notebooks to extract code structure and dependencies."""
    
    def __init__(self):
        self.node_id = 0
    
    def parse_notebook(self, notebook_data: Dict[str, Any]) -> GraphData:
        """Parse a notebook from JSON data (similar to vscode.NotebookDocument)."""
        nodes = []
        edges = []
        absolute_line = 0
        
        if 'cells' not in notebook_data:
            raise ValueError('Invalid notebook format: missing cells')
        
        for cell_index, cell in enumerate(notebook_data['cells']):
            if cell.get('cell_type') == 'code':
                cell_node = self._parse_cell(cell, cell_index, absolute_line)
                nodes.append(cell_node)
                
                code_content = self._get_cell_source(cell)
                child_nodes = self._parse_code_structure(code_content, cell_index, absolute_line)
                cell_node.children = child_nodes
                nodes.extend(self._flatten_nodes(child_nodes))
            
            # Update absolute line counter
            content = self._get_cell_source(cell)
            absolute_line += len(content.split('\n')) + 1
        
        # Use the fixed dependency detection
        self._detect_dependencies_fixed(nodes, edges)
        
        return GraphData(nodes=nodes, edges=edges)
    
    def _parse_cell(self, cell: Dict[str, Any], index: int, absolute_line: int) -> CodeNode:
        """Parse a single notebook cell."""
        content = self._get_cell_source(cell)
        
        return CodeNode(
            id=f'cell_{index}',
            type='cell',
            name=f'Cell {index + 1}',
            content=content,
            cell_index=index,
            line_in_cell=0,
            line_in_notebook=absolute_line,
            metadata=cell.get('metadata')
        )
    
    def _get_cell_source(self, cell: Dict[str, Any]) -> str:
        """Extract source code from a cell."""
        source = cell.get('source', '')
        if isinstance(source, list):
            return ''.join(source)
        return source
    
    def _parse_code_structure(self, code: str, cell_index: int, cell_start_line: int) -> List[CodeNode]:
        """Parse Python code structure to extract classes, functions, imports, and variables."""
        nodes = []
        lines = code.split('\n')
        
        # Regex patterns for Python code elements
        import_regex = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$')
        class_regex = re.compile(r'^class\s+(\w+)(?:\s*\(([^)]*)\))?\s*:')
        function_regex = re.compile(r'^def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:')
        variable_regex = re.compile(r'^(\w+)\s*=\s*(.+)$')
        
        current_indent = 0
        parent_stack = []
        
        for i, line in enumerate(lines):
            trimmed_line = line.strip()
            
            if not trimmed_line or trimmed_line.startswith('#'):
                continue
            
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            if not line.strip():
                continue
            
            # Pop from parent stack if we've decreased indentation
            while parent_stack and indent <= current_indent:
                parent_stack.pop()
                current_indent = parent_stack[-1].line_in_cell if parent_stack else 0
            
            node = None
            
            # Check for imports
            if import_match := import_regex.match(trimmed_line):
                node = CodeNode(
                    id=f'import_{self.node_id}',
                    type='import',
                    name=import_match.group(1) or import_match.group(2),
                    content=trimmed_line,
                    cell_index=cell_index,
                    line_in_cell=i,
                    line_in_notebook=cell_start_line + i
                )
                self.node_id += 1
            
            # Check for classes
            elif class_match := class_regex.match(trimmed_line):
                node = CodeNode(
                    id=f'class_{class_match.group(1)}_{self.node_id}',
                    type='class',
                    name=class_match.group(1),
                    content=trimmed_line,
                    cell_index=cell_index,
                    line_in_cell=i,
                    line_in_notebook=cell_start_line + i
                )
                self.node_id += 1
            
            # Check for functions
            elif function_match := function_regex.match(trimmed_line):
                node = CodeNode(
                    id=f'function_{function_match.group(1)}_{self.node_id}',
                    type='function',
                    name=function_match.group(1),
                    content=trimmed_line,
                    cell_index=cell_index,
                    line_in_cell=i,
                    line_in_notebook=cell_start_line + i
                )
                self.node_id += 1
            
            # Check for top-level variables
            elif indent == 0 and (var_match := variable_regex.match(trimmed_line)):
                node = CodeNode(
                    id=f'var_{var_match.group(1)}_{self.node_id}',
                    type='variable',
                    name=var_match.group(1),
                    content=trimmed_line,
                    cell_index=cell_index,
                    line_in_cell=i,
                    line_in_notebook=cell_start_line + i
                )
                self.node_id += 1
            
            if node:
                if parent_stack:
                    parent_stack[-1].children.append(node)
                else:
                    nodes.append(node)
                
                if node.type in ['class', 'function']:
                    parent_stack.append(node)
                    current_indent = indent
        
        return nodes
    
    def _flatten_nodes(self, nodes: List[CodeNode]) -> List[CodeNode]:
        """Flatten nested node structure into a flat list."""
        flattened = []
        
        for node in nodes:
            flattened.append(node)
            if node.children:
                flattened.extend(self._flatten_nodes(node.children))
        
        return flattened
    
    def _detect_dependencies_fixed(self, nodes: List[CodeNode], edges: List[Dict[str, str]]):
        """Fixed version that detects dependencies in the full function body."""
        # Create a map of node names to nodes
        node_map = {}
        for node in nodes:
            if node.type != 'cell':
                node_map[node.name] = node
        
        # Look for function calls in the entire function body
        for node in nodes:
            if node.type in ['function', 'class']:
                # Get the cell content
                cell_node = next((n for n in nodes if n.type == 'cell' and n.cell_index == node.cell_index), None)
                if not cell_node:
                    continue
                    
                cell_lines = cell_node.content.split('\n')
                
                # Find the full function body
                func_start = node.line_in_cell
                func_end = func_start
                
                # Find the end of the function
                for i in range(func_start + 1, len(cell_lines)):
                    line = cell_lines[i]
                    if line and not line.startswith((' ', '\t')):
                        func_end = i - 1
                        break
                    elif i == len(cell_lines) - 1:
                        func_end = i
                
                # Extract full function body
                func_body = '\n'.join(cell_lines[func_start:func_end + 1])
                
                # Find all function calls in the body
                call_pattern = re.compile(r'\b(\w+)\s*\(')
                matches = call_pattern.findall(func_body)
                
                for called_name in matches:
                    if called_name in node_map and called_name != node.name:
                        edges.append({
                            'source': node.id,
                            'target': node_map[called_name].id,
                            'type': 'calls'
                        })
                        if called_name not in node.dependencies:
                            node.dependencies.append(called_name)


# Helper functions for serialization
def node_to_dict(node: CodeNode) -> Dict[str, Any]:
    """Convert a CodeNode to a dictionary."""
    return {
        'id': node.id,
        'type': node.type,
        'name': node.name,
        'content': node.content,
        'cellIndex': node.cell_index,
        'lineInCell': node.line_in_cell,
        'lineInNotebook': node.line_in_notebook,
        'children': [node_to_dict(child) for child in node.children],
        'dependencies': node.dependencies,
        'metadata': node.metadata
    }


def graph_to_dict(graph: GraphData) -> Dict[str, Any]:
    """Convert GraphData to a dictionary."""
    return {
        'nodes': [node_to_dict(node) for node in graph.nodes],
        'edges': graph.edges
    }


# Create the tiny demo notebook
tiny_demo_notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "source": ["# Demo RAG Application\n", "This notebook demonstrates a simple RAG implementation."]
        },
        {
            "cell_type": "code",
            "source": [
                "# Import necessary libraries\n",
                "import pandas as pd\n",
                "from langchain import OpenAI\n",
                "import numpy as np"
            ]
        },
        {
            "cell_type": "code", 
            "source": [
                "# Helper function to clean text\n",
                "def clean_text(text):\n",
                "    \"\"\"Remove extra whitespace and normalize text.\"\"\"\n",
                "    return ' '.join(text.split())\n",
                "\n",
                "# Another helper\n",
                "def tokenize(text):\n",
                "    \"\"\"Simple tokenization.\"\"\"\n",
                "    return text.lower().split()"
            ]
        },
        {
            "cell_type": "code",
            "source": [
                "class VectorStore:\n",
                "    \"\"\"Simple vector storage for embeddings.\"\"\"\n",
                "    def __init__(self):\n",
                "        self.vectors = []\n",
                "    \n",
                "    def add(self, vector):\n",
                "        self.vectors.append(vector)\n",
                "    \n",
                "    def search(self, query_vector, k=5):\n",
                "        # Simplified search\n",
                "        return self.vectors[:k]"
            ]
        },
        {
            "cell_type": "code",
            "source": [
                "def build_rag_graph(documents):\n",
                "    \"\"\"Main function to build RAG pipeline.\"\"\"\n",
                "    store = VectorStore()\n",
                "    \n",
                "    for doc in documents:\n",
                "        cleaned = clean_text(doc)\n",
                "        tokens = tokenize(cleaned)\n",
                "        # Add to store (simplified)\n",
                "        store.add(tokens)\n",
                "    \n",
                "    return store\n",
                "\n",
                "# Configuration\n",
                "MAX_TOKENS = 100\n",
                "TEMPERATURE = 0.7"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python", 
            "name": "python3"
        }
    }
}

log_print("Created tiny demo notebook with", len(tiny_demo_notebook["cells"]), "cells")
log_print()

# Test the NotebookParser with fixed dependency detection
parser = NotebookParser()
graph_data = parser.parse_notebook(tiny_demo_notebook)

log_print(f"Found {len(graph_data.nodes)} nodes and {len(graph_data.edges)} edges\n")

# Display all nodes
log_print("Nodes found:")
for node in graph_data.nodes:
    if node.type != 'cell':  # Skip cell nodes for cleaner output
        log_print(f"  {node.type.upper()}: {node.name} (Cell {node.cell_index + 1}, Line {node.line_in_cell})")
        if node.dependencies:
            log_print(f"    Dependencies: {', '.join(node.dependencies)}")

log_print("\nEdges (dependencies):")
for edge in graph_data.edges:
    source_node = next(n for n in graph_data.nodes if n.id == edge['source'])
    target_node = next(n for n in graph_data.nodes if n.id == edge['target'])
    log_print(f"  {source_node.name} -> {target_node.name} ({edge['type']})")

# Show detailed dependency analysis
log_print("\n\n=== Detailed Dependency Analysis ===")
log_print("\nFunctions and their dependencies:")
for node in graph_data.nodes:
    if node.type == 'function' and node.dependencies:
        log_print(f"\n{node.name}:")
        log_print(f"  Calls: {', '.join(node.dependencies)}")
        
        # Show the function body
        cell_node = next(n for n in graph_data.nodes if n.type == 'cell' and n.cell_index == node.cell_index)
        cell_lines = cell_node.content.split('\n')
        func_start = node.line_in_cell
        func_end = func_start
        
        for i in range(func_start + 1, len(cell_lines)):
            line = cell_lines[i]
            if line and not line.startswith((' ', '\t')):
                func_end = i - 1
                break
            elif i == len(cell_lines) - 1:
                func_end = i
        
        func_body = '\n'.join(cell_lines[func_start:func_end + 1])
        log_print(f"  Function body:")
        for line in func_body.split('\n'):
            log_print(f"    {line}")

# Define the missing base class
@dataclass
class Phase:
    """Represents a phase in the code explanation."""
    phase_id: str
    title: str
    summary: str
    details: Optional[str] = None
    components: List[str] = field(default_factory=list)


@dataclass 
class ComponentInfo:
    """Extended information for a code component."""
    node_id: str
    name: str
    type: str
    phase_ids: List[str] = field(default_factory=list)
    tooltip: Optional[str] = None
    source_link: Optional[str] = None


@dataclass
class WalkthroughSession:
    """Tracks user progress through code walkthrough."""
    session_id: str
    file_hash: str
    current_phase: Optional[str] = None
    current_component: Optional[str] = None
    visited_phases: List[str] = field(default_factory=list)
    visited_components: List[str] = field(default_factory=list)


class NotebookCache:
    """Cache implementation for notebook parsing and explanations."""
    
    def __init__(self, db_path='ember_cache.db'):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        """Create cache tables if they don't exist."""
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS file_state (
                hash TEXT PRIMARY KEY,
                path TEXT,
                mtime REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS code_graph (
                file_hash TEXT PRIMARY KEY,
                graph_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS phase_plan (
                cache_key TEXT PRIMARY KEY,  -- (file_hash, prompt_version)
                phases_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS component_tooltips (
                cache_key TEXT PRIMARY KEY,  -- (component_name, file_hash)
                tooltip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS external_docs (
                cache_key TEXT PRIMARY KEY,  -- (package, version)
                doc_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        self.conn.commit()
    
    def get_file_hash(self, content: str) -> str:
        """Generate SHA-256 hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_code_graph(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached code graph."""
        cursor = self.conn.execute(
            'SELECT graph_json FROM code_graph WHERE file_hash = ?', 
            (file_hash,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def save_code_graph(self, file_hash: str, graph_data: GraphData):
        """Save code graph to cache."""
        graph_json = json.dumps(graph_to_dict(graph_data))
        self.conn.execute(
            'INSERT OR REPLACE INTO code_graph (file_hash, graph_json) VALUES (?, ?)',
            (file_hash, graph_json)
        )
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


# Base explainer class
class NotebookExplainer:
    """Base class for notebook explanation."""
    
    def __init__(self, openai_client=None):
        self.parser = NotebookParser()
        self.cache = NotebookCache()
        self.openai_client = openai_client
    
    def _dict_to_graph(self, graph_dict: Dict[str, Any]) -> GraphData:
        """Convert dictionary back to GraphData object."""
        nodes = []
        for node_dict in graph_dict['nodes']:
            # Recursively create child nodes
            children = []
            for child_dict in node_dict.get('children', []):
                children.append(self._dict_to_node(child_dict))
            
            node = CodeNode(
                id=node_dict['id'],
                type=node_dict['type'],
                name=node_dict['name'],
                content=node_dict['content'],
                cell_index=node_dict['cellIndex'],
                line_in_cell=node_dict['lineInCell'],
                line_in_notebook=node_dict['lineInNotebook'],
                children=children,
                dependencies=node_dict.get('dependencies', []),
                metadata=node_dict.get('metadata')
            )
            nodes.append(node)
        
        return GraphData(nodes=nodes, edges=graph_dict.get('edges', []))
    
    def _dict_to_node(self, node_dict: Dict[str, Any]) -> CodeNode:
        """Convert dictionary to CodeNode."""
        children = []
        for child_dict in node_dict.get('children', []):
            children.append(self._dict_to_node(child_dict))
            
        return CodeNode(
            id=node_dict['id'],
            type=node_dict['type'],
            name=node_dict['name'],
            content=node_dict['content'],
            cell_index=node_dict['cellIndex'],
            line_in_cell=node_dict['lineInCell'],
            line_in_notebook=node_dict['lineInNotebook'],
            children=children,
            dependencies=node_dict.get('dependencies', []),
            metadata=node_dict.get('metadata')
        )


class NotebookExplainerV2(NotebookExplainer):
    """Enhanced explainer that uses real parsed data."""
    
    def _generate_phase_plan_from_graph(self, graph_data: GraphData) -> List[Phase]:
        """Generate phases based on actual parsed graph data."""
        phases = []
        
        # Group components by type and cell
        imports_by_cell = {}
        functions_by_cell = {}
        classes_by_cell = {}
        variables_by_cell = {}
        
        for node in graph_data.nodes:
            if node.type == 'import':
                imports_by_cell.setdefault(node.cell_index, []).append(node.name)
            elif node.type == 'function':
                functions_by_cell.setdefault(node.cell_index, []).append(node.name)
            elif node.type == 'class':
                classes_by_cell.setdefault(node.cell_index, []).append(node.name)
            elif node.type == 'variable':
                variables_by_cell.setdefault(node.cell_index, []).append(node.name)
        
        # Phase 1: Setup and Imports (if any imports exist)
        if imports_by_cell:
            import_components = []
            for cell_imports in imports_by_cell.values():
                import_components.extend(cell_imports)
            
            phases.append(Phase(
                phase_id="p1",
                title="Setup and Imports",
                summary="Import necessary libraries and set up the environment.",
                components=import_components
            ))
        
        # Phase 2: Helper Functions (if any exist)
        helper_functions = []
        for cell_idx, funcs in functions_by_cell.items():
            # Consider functions that don't call other custom functions as helpers
            for func in funcs:
                func_node = next(n for n in graph_data.nodes if n.name == func and n.type == 'function')
                # Check if it only calls built-in functions or has no dependencies
                if not func_node.dependencies or all(
                    dep in ['print', 'len', 'join', 'split', 'lower', 'append', 'VectorStore'] 
                    for dep in func_node.dependencies
                ):
                    helper_functions.append(func)
        
        if helper_functions:
            phases.append(Phase(
                phase_id="p2",
                title="Helper Functions",
                summary="Utility functions that provide basic functionality used by other components.",
                components=helper_functions
            ))
        
        # Phase 3: Core Components (classes and main functions)
        core_components = []
        
        # Add all classes
        for cell_classes in classes_by_cell.values():
            core_components.extend(cell_classes)
        
        # Add functions that call other custom functions
        for cell_idx, funcs in functions_by_cell.items():
            for func in funcs:
                if func not in helper_functions:
                    core_components.append(func)
        
        # Add important variables
        for cell_vars in variables_by_cell.values():
            core_components.extend(cell_vars)
        
        if core_components:
            phases.append(Phase(
                phase_id="p3",
                title="Core Components",
                summary="Main classes, functions, and configuration that implement the core functionality.",
                components=core_components
            ))
        
        return phases
    
    def assign_components_to_phases_from_graph(self, graph_data: GraphData, phases: List[Phase]) -> Dict[str, ComponentInfo]:
        """Assign components to phases based on actual graph data."""
        component_registry = {}
        
        # Create a mapping of component names to phase IDs
        component_to_phases = {}
        for phase in phases:
            for component_name in phase.components:
                if component_name not in component_to_phases:
                    component_to_phases[component_name] = []
                component_to_phases[component_name].append(phase.phase_id)
        
        # Create ComponentInfo for each node
        for node in graph_data.nodes:
            if node.type != 'cell':
                phase_ids = component_to_phases.get(node.name, [])
                
                # Generate tooltip based on node type and content
                tooltip = self._generate_tooltip(node)
                
                component_info = ComponentInfo(
                    node_id=node.id,
                    name=node.name,
                    type=node.type,
                    phase_ids=phase_ids,
                    tooltip=tooltip,
                    source_link=f"cell_{node.cell_index}#L{node.line_in_cell}"
                )
                component_registry[node.name] = component_info
        
        return component_registry
    
    def _generate_tooltip(self, node: CodeNode) -> str:
        """Generate a tooltip description for a component."""
        if node.type == 'import':
            return f"Imports {node.name} module"
        elif node.type == 'function':
            if node.dependencies:
                return f"Function that calls: {', '.join(node.dependencies)}"
            else:
                return "Utility function"
        elif node.type == 'class':
            return f"Class definition with {len(node.children)} methods"
        elif node.type == 'variable':
            return "Configuration variable"
        return "Code component"
    
    def analyze_notebook(self, notebook_data: Dict[str, Any]) -> Tuple[GraphData, List[Phase]]:
        """Override to use real data generation."""
        # Get file hash
        notebook_content = json.dumps(notebook_data)
        file_hash = self.cache.get_file_hash(notebook_content)
        
        # Parse notebook (using cache if available)
        cached_graph_dict = self.cache.get_code_graph(file_hash)
        if cached_graph_dict:
            graph_data = self._dict_to_graph(cached_graph_dict)
            log_print("Using cached code graph")
        else:
            graph_data = self.parser.parse_notebook(notebook_data)
            self.cache.save_code_graph(file_hash, graph_data)
            log_print("Parsed and cached new code graph")
        
        # Generate phases from actual data
        phases = self._generate_phase_plan_from_graph(graph_data)
        
        return graph_data, phases


# Test with the enhanced explainer
log_print("\n=== Testing Enhanced Explainer with Real Data ===\n")
explainer_v2 = NotebookExplainerV2(openai_client=None)
graph_data, phases = explainer_v2.analyze_notebook(tiny_demo_notebook)

log_print("Generated Phases from Actual Data:")
for phase in phases:
    log_print(f"\n{phase.phase_id}: {phase.title}")
    log_print(f"  Summary: {phase.summary}")
    log_print(f"  Components: {', '.join(phase.components)}")

# Assign components with real data
component_registry = explainer_v2.assign_components_to_phases_from_graph(graph_data, phases)

log_print(f"\n\nComponent Registry ({len(component_registry)} components):")
for name, info in component_registry.items():
    log_print(f"\n{name} ({info.type}):")
    log_print(f"  Phases: {', '.join(info.phase_ids)}")
    log_print(f"  Tooltip: {info.tooltip}")
    log_print(f"  Source: {info.source_link}")

explainer_v2.cache.close()


# Walkthrough Manager Demo
class WalkthroughManager:
    """Manages user walkthrough sessions."""
    
    def __init__(self, graph_data: GraphData, phases: List[Phase], component_registry: Dict[str, ComponentInfo]):
        self.graph_data = graph_data
        self.phases = phases
        self.component_registry = component_registry
        self.phase_order = [p.phase_id for p in phases]
        
    def create_session(self, file_hash: str) -> WalkthroughSession:
        """Create a new walkthrough session."""
        return WalkthroughSession(
            session_id=str(uuid.uuid4()),
            file_hash=file_hash,
            current_phase=self.phases[0].phase_id if self.phases else None
        )
    
    def get_current_content(self, session: WalkthroughSession) -> Dict[str, Any]:
        """Get content for the current position in the walkthrough."""
        if not session.current_phase:
            return {"type": "overview", "content": "No phases available"}
        
        current_phase = next(p for p in self.phases if p.phase_id == session.current_phase)
        
        # Get components for this phase
        phase_components = []
        for comp_name in current_phase.components:
            if comp_name in self.component_registry:
                comp_info = self.component_registry[comp_name]
                # Find the actual node
                node = next((n for n in self.graph_data.nodes if n.name == comp_name and n.type != 'cell'), None)
                if node:
                    phase_components.append({
                        "name": comp_name,
                        "type": comp_info.type,
                        "tooltip": comp_info.tooltip,
                        "content": node.content,
                        "cell": node.cell_index + 1,
                        "line": node.line_in_cell + 1
                    })
        
        return {
            "type": "phase",
            "phase_id": current_phase.phase_id,
            "title": current_phase.title,
            "summary": current_phase.summary,
            "components": phase_components,
            "progress": {
                "current": self.phase_order.index(session.current_phase) + 1,
                "total": len(self.phases)
            }
        }
    
    def next_phase(self, session: WalkthroughSession) -> bool:
        """Move to the next phase. Returns True if successful."""
        if not session.current_phase:
            return False
            
        current_idx = self.phase_order.index(session.current_phase)
        if current_idx < len(self.phase_order) - 1:
            session.visited_phases.append(session.current_phase)
            session.current_phase = self.phase_order[current_idx + 1]
            return True
        return False


# Create a walkthrough demo
log_print("\n\n=== Walkthrough Session Demo ===\n")

# Initialize walkthrough manager
manager = WalkthroughManager(graph_data, phases, component_registry)

# Create a session
notebook_content = json.dumps(tiny_demo_notebook)
file_hash = hashlib.sha256(notebook_content.encode()).hexdigest()
session = manager.create_session(file_hash)

log_print(f"Created session: {session.session_id[:8]}...")
log_print(f"Starting at phase: {session.current_phase}\n")

# Walk through each phase
while True:
    content = manager.get_current_content(session)
    
    log_print(f"\n{'='*60}")
    log_print(f"Phase {content['progress']['current']}/{content['progress']['total']}: {content['title']}")
    log_print(f"{'='*60}")
    log_print(f"\nSummary: {content['summary']}\n")
    
    if content['components']:
        log_print("Components in this phase:")
        for comp in content['components']:
            log_print(f"\n  📄 {comp['name']} ({comp['type']})")
            log_print(f"     Location: Cell {comp['cell']}, Line {comp['line']}")
            log_print(f"     Tooltip: {comp['tooltip']}")
            log_print(f"     Code: {comp['content'][:50]}...")
    
    # Try to go to next phase
    if not manager.next_phase(session):
        log_print("\n✅ Walkthrough complete!")
        break

log_print(f"\n\nVisited phases: {session.visited_phases}")

# Close log file
log_print(f"\n\n=== Execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
log_file.close()

print(f"\nExecution complete! Full log saved to: {log_filename}")