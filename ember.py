import os
import sys
import argparse
import getpass
from dotenv import load_dotenv
import logging
from datetime import datetime
import asyncio

load_dotenv()
os.environ["TAVILY_API_KEY"] 
os.environ["OPENAI_API_KEY"] 
os.environ["LANGCHAIN_TRACING_V2"] 
os.environ["LANGCHAIN_PROJECT"] 
os.environ["LANGCHAIN_API_KEY"]

from openai import OpenAI

# Try to import langsmith, but make it optional
try:
    from langsmith.wrappers import wrap_openai
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Create dummy decorator if langsmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator

# Use wrapped OpenAI client if langsmith is available
if LANGSMITH_AVAILABLE:
    openai_client = wrap_openai(OpenAI())
else:
    openai_client = OpenAI()

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
from collections import defaultdict

# Try to import nbformat, but handle if it's missing
try:
    import nbformat
    NBFORMAT_AVAILABLE = True
except ImportError:
    NBFORMAT_AVAILABLE = False

# Create a custom logger that writes to both file and console
class DualLogger:
    """Logger that writes to both file and console with different truncation settings."""
    def __init__(self, log_file_path: str):
        self.log_file = open(log_file_path, 'w', encoding='utf-8')
        self.console = sys.stdout
        
    def write(self, message: str, truncate_console: bool = False, max_console_length: int = 50):
        """Write to both log file and console."""
        # Write full message to log file
        self.log_file.write(message)
        self.log_file.flush()
        
        # Write to console (potentially truncated)
        if truncate_console and len(message) > max_console_length:
            console_message = message[:max_console_length] + "..."
        else:
            console_message = message
        self.console.write(console_message)
        self.console.flush()
    
    def close(self):
        """Close the log file."""
        self.log_file.close()

# Store the original print function FIRST
import builtins
_original_print = builtins.print

# Global logger instance (will be initialized in main)
dual_logger = None
# Global flag for JSON export mode
json_export_mode = False

def print_dual(*args, truncate_console=False, max_console_length=50, sep=' ', end='\n', **kwargs):
    """Print function that outputs to both console and log file."""
    message = sep.join(str(arg) for arg in args) + end
    if dual_logger:
        dual_logger.write(message, truncate_console=truncate_console, max_console_length=max_console_length)
    else:
        # Fall back to built-in print
        _original_print(*args, sep=sep, end=end, **kwargs)

# Override the built-in print to use our dual logger
print = print_dual

# -------- Token accounting ---------
class TokenTracker:
    """Lightweight counter for prompt / completion / total tokens."""
    def __init__(self):
        self.totals = defaultdict(int)  # keys: prompt, completion, total

    def add(self, usage):
        if not usage:
            return
        self.totals["prompt"]     += usage.prompt_tokens or 0
        self.totals["completion"] += usage.completion_tokens or 0
        self.totals["total"]      += usage.total_tokens or 0

    def summary(self) -> str:
        return (
            f"Tokens – prompt: {self.totals['prompt']}, "
            f"completion: {self.totals['completion']}, "
            f"total: {self.totals['total']}"
        )

TOKEN_TRACKER = TokenTracker()
# -----------------------------------

# LLM configuration
LLM_MODEL = "gpt-4o-mini"  # or whatever tier you use

def chat(prompt: str, **kwargs) -> str:
    """Single entry-point for all LLM calls *and* token accounting."""
    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=kwargs.get("temperature", 0.3),
        max_tokens=kwargs.get("max_tokens", 1024),
    )
    # 💡 accumulate tokens
    TOKEN_TRACKER.add(response.usage)
    return response.choices[0].message.content.strip()


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
        
        self._detect_dependencies(nodes, edges)
        
        return GraphData(nodes=nodes, edges=edges)
    
    def parse(self, notebook_json: str) -> GraphData:
        """Legacy method for JSON string parsing (backward compatibility)."""
        notebook_data = json.loads(notebook_json)
        return self.parse_notebook(notebook_data)
    
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
    
    def _detect_dependencies(self, nodes: List[CodeNode], edges: List[Dict[str, str]]):
        """Detect dependencies between code nodes - FIXED VERSION."""
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
    
    
    
# Function to load notebook from file
def load_notebook(notebook_path: str) -> Dict[str, Any]:
    """Load a Jupyter notebook from file."""
    if not os.path.exists(notebook_path):
        raise FileNotFoundError(f"Notebook not found: {notebook_path}")
    
    with open(notebook_path, 'r') as f:
        return json.load(f)



# This test code will be moved to the main execution section
    
    
    
# Updated INITIAL_EXPLANATION_STRUCTURE based on chatgpt.md recommendations
INITIAL_EXPLANATION_STRUCTURE = """You are an expert Python tutor who just finished writing the attached notebook / script.

**Goal:** Produce an *initial*, learner-friendly walkthrough so that a reader with basic Python skills can eventually understand what every cell or file fragment does and how the pieces fit together.

### How to structure the explanation  
1. **High-level overview**  
   • What the program achieves and why someone would run it.  
2. **Phase map** (0-N phases)  
   • Each *phase* is a coherent chunk of work (e.g., *Data Loading*, *Helper Functions*, *Model Training*).  
   • Give each phase ✔ a short prose summary (1-3 sentences) and ✔ a numbered handle so we can refer back to it.  
3. **Phase details** - ordered for comprehension, not file order  
   For each phase  
   1. *What* it does in 2-4 beginner-level sentences.  
   2. *How* it works: describe the key components **only at the level needed for a first pass** (e.g., "calls the helper function `clean_text`, then groups rows by author").  
   3. List *components* referenced in this phase (functions, classes, imports, top-level variables) as a Markdown bullet list:  
      ```
      - def clean_text(): …
      - class VectorStore(): …
      - import langchain …
      ```
      Do **not** explain these components yet – just enumerate them so we can hook detailed tooltips later.  

### Writing style
* • *Teach, don't lecture*: assume curiosity but limited prior knowledge.  
* • Skip microscopic details (e.g., how `sum()` works) in this pass; simply note "adds values" so we can attach drill-down tooltips later.  
* • Keep paragraphs short; prefer lists where natural.
"""

# Caching implementation based on chatgpt.md
import sqlite3
from datetime import datetime

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
    
    def get_phase_plan(self, file_hash: str, prompt_version: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached phase plan."""
        cache_key = f"{file_hash}:{prompt_version}"
        cursor = self.conn.execute(
            'SELECT phases_json FROM phase_plan WHERE cache_key = ?',
            (cache_key,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def save_phase_plan(self, file_hash: str, prompt_version: str, phases: Dict[str, Any]):
        """Save phase plan to cache."""
        cache_key = f"{file_hash}:{prompt_version}"
        self.conn.execute(
            'INSERT OR REPLACE INTO phase_plan (cache_key, phases_json) VALUES (?, ?)',
            (cache_key, json.dumps(phases))
        )
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


# Cache test code removed - will be part of main execution




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


class NotebookExplainer:
    """Main class for generating and managing code explanations."""

    def __init__(self, openai_client=None):
        self.parser = NotebookParser()
        self.cache = NotebookCache()
        self.openai_client = openai_client

    @traceable(name="analyze_notebook")
    def analyze_notebook(self, notebook_data: Dict[str, Any]) -> Tuple[GraphData, List[Phase]]:
        """Analyze notebook and generate phase-based explanation."""
        # Get file hash
        notebook_content = json.dumps(notebook_data)
        file_hash = self.cache.get_file_hash(notebook_content)

        # Check cache for graph
        cached_graph_dict = self.cache.get_code_graph(file_hash)
        if cached_graph_dict:
            # Reconstruct GraphData from cached dict
            graph_data = self._dict_to_graph(cached_graph_dict)
            if not json_export_mode:
                print("Using cached code graph")
        else:
            # Parse notebook
            graph_data = self.parser.parse_notebook(notebook_data)
            self.cache.save_code_graph(file_hash, graph_data)
            if not json_export_mode:
                print("Parsed and cached new code graph")

        # Check cache for phase plan
        prompt_version = "2025-07-v1"  # Version the prompt for cache invalidation
        cached_phases = self.cache.get_phase_plan(file_hash, prompt_version)
        if cached_phases:
            phases = [Phase(**p) for p in cached_phases['phases']]
            if not json_export_mode:
                print("Using cached phase plan")
        else:
            # Generate phase plan from actual graph data
            phases = self._generate_phase_plan_from_graph(graph_data)
            self.cache.save_phase_plan(file_hash, prompt_version, {
                'phases': [asdict(p) for p in phases]
            })
            if not json_export_mode:
                print("Generated and cached new phase plan")

        return graph_data, phases

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

    def _generate_phase_plan_from_graph(self, graph_data: GraphData) -> List[Phase]:
        """Use LLM to create Phase Plan; fall back to heuristic if the call fails."""
        try:
            # ❶ build a lightweight description of the notebook
            sketch = []
            for node in graph_data.nodes:
                if node.type != "cell":
                    sketch.append(f"- {node.type}: {node.name}")
            sketch_text = "\n".join(sketch[:200])  # keep prompt small

            prompt = (
                INITIAL_EXPLANATION_STRUCTURE
                + "\n\nHere is an inventory of code elements you may reference:\n"
                + sketch_text
            )
            raw = chat(prompt)
            # ❷ parse the JSON-ish blocks back into Phase objects
            phases = self._parse_phase_response(raw)
            if phases:
                # The LLM response doesn't include component lists, so we need to add them
                # This will be done later in assign_components_to_phases
                return phases
        except Exception as e:
            print("⚠️  LLM phase-plan generation failed, falling back:", e)

        # fallback
        return self._generate_phase_plan_heuristic(graph_data)

    def _generate_phase_plan_heuristic(self, graph_data: GraphData) -> List[Phase]:
        """Heuristic phase generation as fallback."""
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
                    dep in ['print', 'len', 'join', 'split', 'lower', 'append']
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

    def _parse_phase_response(self, text: str) -> List[Phase]:
        """
        Very forgiving parser that extracts phase information from LLM response.
        Looking for patterns like:
        - '1. **Data Loading**' or '1. Data Loading'
        - With summaries on the next line
        """
        phases = []
        
        # Look for the Phase Map section
        phase_map_match = re.search(r"## Phase Map(.*?)(?=## |$)", text, re.S)
        if phase_map_match:
            phase_text = phase_map_match.group(1)
        else:
            phase_text = text
        
        # Find numbered phases with optional bold titles
        pattern = re.compile(r"^\s*(\d+)\.\s*\*?\*?([^*\n]+?)\*?\*?\s*\n\s*([^\n]+)", re.M)
        
        for m in pattern.finditer(phase_text):
            pid = f"p{m.group(1)}"
            title = m.group(2).strip()
            summary = m.group(3).strip()
            
            # Clean up title - remove any remaining markdown or punctuation
            title = re.sub(r'[*_]', '', title).strip()
            
            phases.append(Phase(phase_id=pid, title=title, summary=summary))
        
        # If no phases found, return empty list to trigger fallback
        return phases

    def assign_components_to_phases(self, graph_data: GraphData, phases: List[Phase]) -> Dict[str, ComponentInfo]:
        """Assign components to phases based on actual graph data."""
        component_registry = {}

        # Build a tiny prompt: we only need names, not code
        component_names = [n.name for n in graph_data.nodes if n.type != "cell"]
        phase_titles = [f"{p.phase_id}: {p.title}" for p in phases]
        prompt = (
            "Assign each component to one or more phase IDs.\n"
            "Phases:\n" + "\n".join(phase_titles) + "\n\n"
            "Components:\n" + "\n".join(component_names) +
            "\n\nRespond with JSON object {component: [phase_id,...], ...}"
        )

        mapping = {}
        try:
            mapping_json = chat(prompt)
            # Strip markdown code blocks if present
            if "```json" in mapping_json:
                mapping_json = mapping_json.split("```json")[1].split("```")[0].strip()
            elif "```" in mapping_json:
                mapping_json = mapping_json.split("```")[1].split("```")[0].strip()
            mapping = json.loads(mapping_json)
        except Exception as e:
            print("⚠️  LLM mapping failed, using heuristic:", e)
            mapping = {}   # will drop to heuristic below

        # Create a mapping of component names to phase IDs (heuristic fallback)
        component_to_phases = {}
        for phase in phases:
            for component_name in phase.components:
                if component_name not in component_to_phases:
                    component_to_phases[component_name] = []
                component_to_phases[component_name].append(phase.phase_id)

        # Create ComponentInfo for each node
        for node in graph_data.nodes:
            if node.type != 'cell':
                # First check LLM mapping, then fall back to heuristic
                if node.name in mapping:
                    phase_ids = mapping[node.name]
                    if isinstance(phase_ids, str):
                        phase_ids = [phase_ids]
                else:
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
                
                # Also update the phase components lists
                for phase_id in phase_ids:
                    phase = next((p for p in phases if p.phase_id == phase_id), None)
                    if phase and node.name not in phase.components:
                        phase.components.append(node.name)

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

    def close(self):
        """Clean up resources."""
        self.cache.close()


@traceable(name="ember_complete_demo")
def run_complete_demo(notebook_path: str):
    """Run the complete ember demo under a single trace."""
    # Load the notebook
    print(f"Loading notebook: {notebook_path}")
    notebook_data = load_notebook(notebook_path)
    
    # Test with the enhanced explainer
    print("\n=== Testing Enhanced Explainer with Real Data ===\n")
    explainer_v2 = NotebookExplainer(openai_client=openai_client)
    graph_data, phases = explainer_v2.analyze_notebook(notebook_data)

    print("Generated Phases from Actual Data:")
    for phase in phases:
        print(f"\n{phase.phase_id}: {phase.title}")
        print(f"  Summary: {phase.summary}")
        print(f"  Components: {', '.join(phase.components)}")

    # Assign components with real data - FIXED: using correct method name
    component_registry = explainer_v2.assign_components_to_phases(graph_data, phases)

    print(f"\n\nComponent Registry ({len(component_registry)} components):")
    for name, info in component_registry.items():
        print(f"\n{name} ({info.type}):")
        print(f"  Phases: {', '.join(info.phase_ids)}")
        print(f"  Tooltip: {info.tooltip}")
        print(f"  Source: {info.source_link}")
    
    # Now run the walkthrough demo - all in the same trace
    run_walkthrough_demo(explainer_v2, graph_data, phases, component_registry, notebook_data)



import uuid

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
    
    def previous_phase(self, session: WalkthroughSession) -> bool:
        """Move to the previous phase. Returns True if successful."""
        if not session.current_phase:
            return False
            
        current_idx = self.phase_order.index(session.current_phase)
        if current_idx > 0:
            session.current_phase = self.phase_order[current_idx - 1]
            return True
        return False


def run_walkthrough_demo(explainer_v2, graph_data, phases, component_registry, notebook_data):
    """Run the walkthrough demo."""
    # Create a walkthrough demo
    print("=== Walkthrough Session Demo ===\n")

    # Initialize walkthrough manager
    manager = WalkthroughManager(graph_data, phases, component_registry)

    # Create a session
    notebook_content = json.dumps(notebook_data)
    file_hash = hashlib.sha256(notebook_content.encode()).hexdigest()
    session = manager.create_session(file_hash)

    print(f"Created session: {session.session_id[:8]}...")
    print(f"Starting at phase: {session.current_phase}\n")

    # Walk through each phase
    while True:
        content = manager.get_current_content(session)
        
        print(f"\n{'='*60}")
        print(f"Phase {content['progress']['current']}/{content['progress']['total']}: {content['title']}")
        print(f"{'='*60}")
        print(f"\nSummary: {content['summary']}\n")
        
        if content['components']:
            print("Components in this phase:")
            for comp in content['components']:
                print(f"\n  📄 {comp['name']} ({comp['type']})")
                print(f"     Location: Cell {comp['cell']}, Line {comp['line']}")
                print(f"     Tooltip: {comp['tooltip']}")
                # Show truncated code in console but full code in log
                code_line = f"     Code: {comp['content']}"
                print(code_line, truncate_console=True, max_console_length=60)
        
        # Try to go to next phase
        if not manager.next_phase(session):
            print("\n✅ Walkthrough complete!")
            break

    print(f"\n\nVisited phases: {session.visited_phases}")


    # Show dependency graph
    print("=== Dependency Graph ===\n")

    # First, let's see all the nodes we found
    print("All Components:")
    for node in graph_data.nodes:
        if node.type != 'cell':
            print(f"  {node.name} ({node.type})")
            if node.dependencies:
                print(f"    → Calls: {', '.join(node.dependencies)}")

    print("\n\nDependency Edges:")
    if graph_data.edges:
        for edge in graph_data.edges:
            source_node = next(n for n in graph_data.nodes if n.id == edge['source'])
            target_node = next(n for n in graph_data.nodes if n.id == edge['target'])
            print(f"  {source_node.name} --{edge['type']}--> {target_node.name}")
    else:
        print("  No dependencies detected between custom components")

    # Let's check why dependencies might not be detected
    print("\n\nDetailed Function Analysis:")
    for node in graph_data.nodes:
        if node.type == 'function' and node.dependencies:
            print(f"\n{node.name}:")
            print(f"  Dependencies: {', '.join(node.dependencies)}")
            
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
            print(f"  Function body:")
            for line in func_body.split('\n'):
                print(f"    {line}")

    # Print token usage summary
    print("\n=== Token usage summary ===")
    print(TOKEN_TRACKER.summary())

    # Clean up
    explainer_v2.close()


# Import our new component-based analysis
try:
    # Try to import the new analysis if available
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ember'))
    from vscode_integration import analyze_notebook_for_vscode
    NEW_ANALYSIS_AVAILABLE = True
except ImportError as e:
    NEW_ANALYSIS_AVAILABLE = False
    import traceback
    _original_print(f"Warning: Could not import new analysis: {e}", file=sys.stderr)
    _original_print(traceback.format_exc(), file=sys.stderr)

# Main execution - everything under one top-level trace  
if __name__ == "__main__":
    
    # Set up argument parser
    arg_parser = argparse.ArgumentParser(description="Analyze a Jupyter notebook and generate phase-based explanations.")
    arg_parser.add_argument("notebook", help="Path to the Jupyter notebook file (.ipynb)")
    arg_parser.add_argument("--no-cache", action="store_true", help="Disable caching and force fresh analysis")
    arg_parser.add_argument("--log-dir", default="logs", help="Directory to store log files (default: logs)")
    arg_parser.add_argument("--export-json", action="store_true", 
        help="Export graph and phase plan as JSON (to stdout) so the VS Code extension can build its outline & graph without re-parsing")
    arg_parser.add_argument("--use-new-analysis", action="store_true", help="Use the new component-based analysis")
    
    args = arg_parser.parse_args()
    
    if args.export_json:
        # JSON export mode - minimal output, no logging
        # Suppress any import warnings in JSON mode
        import warnings
        warnings.filterwarnings("ignore")
        
        # Set global flag for JSON export mode
        json_export_mode = True
        
        # Redirect all print statements to stderr in JSON mode
        import builtins
        builtins.print = lambda *args, **kwargs: _original_print(*args, **kwargs, file=sys.stderr)
        
        # Check if we should use new analysis
        if args.use_new_analysis and NEW_ANALYSIS_AVAILABLE:
            # Use the new component-based analysis
            try:
                # Run async analysis
                result = asyncio.run(analyze_notebook_for_vscode(args.notebook))
                # Output JSON to stdout
                _original_print(json.dumps(result))
            except Exception as e:
                # Error to stderr so it doesn't contaminate JSON output
                import traceback
                _original_print(f"Error in new analysis: {str(e)}", file=sys.stderr)
                _original_print(traceback.format_exc(), file=sys.stderr)
                sys.exit(1)
        else:
            # Use the original analysis
            # Check for required dependencies
            if not NBFORMAT_AVAILABLE:
                _original_print(json.dumps({
                    "error": "Missing dependencies",
                    "message": "Please install required packages: pip install nbformat openai",
                    "details": "Run this from the ember_extension directory: source .venv/bin/activate && pip install -r requirements.txt"
                }), file=sys.stderr)
                sys.exit(1)
            
            try:
                # Load and parse notebook
                notebook_data = load_notebook(args.notebook)
                
                # ── 1. analyse  ──────────────────────────────────────────────
                explainer = NotebookExplainer(openai_client=openai_client)
                graph, phases = explainer.analyze_notebook(notebook_data)
                
                # ── 2. *populate* components lists (mutates `phases` in place)
                _ = explainer.assign_components_to_phases(graph, phases)
                
                # ── 3. emit json  ───────────────────────────────────────────
                output = {
                    "graph": graph_to_dict(graph),
                    "phases": [asdict(p) for p in phases]   # now non‑empty
                }
                
                # Output JSON to stdout
                _original_print(json.dumps(output))
            except Exception as e:
                # Error to stderr so it doesn't contaminate JSON output
                import traceback
                _original_print(f"Error: {str(e)}", file=sys.stderr)
                _original_print(traceback.format_exc(), file=sys.stderr)
                sys.exit(1)
    else:
        # Normal interactive mode with logging
        # Create log directory if it doesn't exist
        os.makedirs(args.log_dir, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        notebook_name = os.path.splitext(os.path.basename(args.notebook))[0]
        log_file_path = os.path.join(args.log_dir, f"ember_{notebook_name}_{timestamp}.log")
        
        # Initialize the dual logger
        globals()['dual_logger'] = DualLogger(log_file_path)
        print(f"Logging to: {log_file_path}")
        
        try:
            # Clear cache if requested
            if args.no_cache:
                cache_file = "ember_cache.db"
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print(f"Cache cleared: {cache_file}")
            
            # Run the complete demo
            run_complete_demo(args.notebook)
        finally:
            # Close the logger
            if dual_logger:
                dual_logger.close()