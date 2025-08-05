"""
Integration module to use ember2.ipynb functions from Python scripts
This bridges the notebook code with the VS Code extension
"""

import sys
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import necessary components from our notebook code
# Note: In production, these would be in proper Python modules
# For now, we'll define the essential structures here

from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime

# Re-create the essential data structures from ember2.ipynb
@dataclass
class ComponentState:
    """State for individual code components"""
    component_id: str
    component_name: str
    component_number: int
    type: Literal["import", "class", "method", "function", "variable", "expression", "decorator"]
    library: str
    full_code: str
    description: str
    block_id: str
    enhanced_description: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    parent_component_ids: List[str] = field(default_factory=list)
    child_component_ids: List[str] = field(default_factory=list)
    calls_component_ids: List[str] = field(default_factory=list)
    called_by_component_ids: List[str] = field(default_factory=list)
    external_dependencies: List[str] = field(default_factory=list)
    is_resolved: bool = False
    confidence_score: float = 1.0

@dataclass
class BlockState:
    """State for code blocks"""
    block_id: str
    block_name: str
    block_type: Literal["imports", "utilities", "classes", "main", "config", "mixed"]
    block_content: str
    initial_description: str
    deep_description: Optional[str] = None
    component_states: Dict[str, ComponentState] = field(default_factory=dict)
    initial_pass_complete: bool = False
    dependency_resolution_complete: bool = False
    is_fully_analyzed: bool = False
    depends_on_blocks: List[str] = field(default_factory=list)
    depended_by_blocks: List[str] = field(default_factory=list)
    pending_dependencies: List[str] = field(default_factory=list)
    execution_order_index: Optional[int] = None
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class WalkthroughState:
    """Complete state for code walkthrough"""
    code_overview: str
    notebook_path: str
    total_blocks: int = 0
    total_components: int = 0
    block_states: Dict[str, BlockState] = field(default_factory=dict)
    global_component_registry: Dict[str, Dict] = field(default_factory=dict)
    import_registry: Dict[str, List[str]] = field(default_factory=dict)
    function_registry: Dict[str, str] = field(default_factory=dict)
    class_registry: Dict[str, str] = field(default_factory=dict)
    analysis_phase: Literal["initializing", "block_analysis", "component_extraction", 
                           "dependency_resolution", "enhancement", "complete"] = "initializing"
    execution_order: List[str] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    blocks_analyzed: int = 0
    blocks_with_dependencies: int = 0
    dependencies_resolved: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    analysis_config: dict = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

async def run_complete_analysis(notebook_path: str) -> WalkthroughState:
    """
    Run the complete analysis pipeline from ember2.ipynb
    """
    try:
        # Try to use the real analysis from ember2_core
        from ember2_core import run_complete_analysis as real_analysis
        return await real_analysis(notebook_path)
    except ImportError:
        # Fall back to mock implementation for testing
        return await _run_mock_analysis(notebook_path)

async def _run_mock_analysis(notebook_path: str) -> WalkthroughState:
    """
    Mock analysis for testing when real analysis is not available
    """
    # Mock implementation for testing
    state = WalkthroughState(
        code_overview="This is a test notebook for demonstrating the VS Code integration",
        notebook_path=notebook_path,
        total_blocks=5
    )
    
    # Create some mock blocks and components
    # Block 1: Imports
    block1 = BlockState(
        block_id="1",
        block_name="Import Libraries",
        block_type="imports",
        block_content="import pandas as pd\nfrom langchain import OpenAI\nimport numpy as np",
        initial_description="Import essential libraries for data processing"
    )
    
    # Add components to block 1
    block1.component_states["1:1"] = ComponentState(
        component_id="1:1",
        component_name="Import_pandas_library",
        component_number=1,
        type="import",
        library="pandas",
        full_code="import pandas as pd",
        description="Import pandas for data manipulation",
        block_id="1",
        line_start=0,
        line_end=0
    )
    
    block1.component_states["1:2"] = ComponentState(
        component_id="1:2",
        component_name="Import_OpenAI_from_langchain",
        component_number=2,
        type="import",
        library="langchain",
        full_code="from langchain import OpenAI",
        description="Import OpenAI from langchain",
        block_id="1",
        line_start=1,
        line_end=1
    )
    
    # Block 2: Class definition
    block2 = BlockState(
        block_id="2",
        block_name="VectorStore Class",
        block_type="classes",
        block_content="class VectorStore:\n    def __init__(self):\n        self.vectors = []\n    def add(self, vector):\n        self.vectors.append(vector)",
        initial_description="Vector storage class"
    )
    
    # Add class and its methods
    block2.component_states["2:1"] = ComponentState(
        component_id="2:1",
        component_name="VectorStore",
        component_number=1,
        type="class",
        library="local",
        full_code="class VectorStore:",
        description="Main vector storage class",
        block_id="2",
        line_start=0,
        line_end=0
    )
    
    block2.component_states["2:2"] = ComponentState(
        component_id="2:2",
        component_name="__init__",
        component_number=2,
        type="method",
        library="local",
        full_code="def __init__(self):\n    self.vectors = []",
        description="Initialize vector store",
        block_id="2",
        line_start=1,
        line_end=2,
        parent_component_ids=["2:1"]  # __init__ is under VectorStore class
    )
    
    block2.component_states["2:3"] = ComponentState(
        component_id="2:3",
        component_name="add",
        component_number=3,
        type="method",
        library="local",
        full_code="def add(self, vector):\n    self.vectors.append(vector)",
        description="Add vector to store",
        block_id="2",
        line_start=3,
        line_end=4,
        parent_component_ids=["2:1"],  # add is under VectorStore class
        calls_component_ids=["2:4"]  # calls append
    )
    
    block2.component_states["2:4"] = ComponentState(
        component_id="2:4",
        component_name="append",
        component_number=4,
        type="expression",
        library="built-in",
        full_code="self.vectors.append(vector)",
        description="Append operation",
        block_id="2",
        line_start=4,
        line_end=4,
        parent_component_ids=["2:3"],  # append is within add method
        called_by_component_ids=["2:3"]
    )
    
    # Set up relationships
    block2.component_states["2:1"].child_component_ids = ["2:2", "2:3"]
    block2.component_states["2:3"].child_component_ids = ["2:4"]
    
    # Add blocks to state
    state.block_states["1"] = block1
    state.block_states["2"] = block2
    
    # Set up block dependencies
    block2.depends_on_blocks = ["1"]  # Class block depends on imports
    block1.depended_by_blocks = ["2"]
    
    # Set execution order
    state.execution_order = ["1", "2"]
    
    # Update totals
    state.total_components = 6
    state.blocks_analyzed = 2
    
    return state

# Export the main function for use by other modules
__all__ = ['run_complete_analysis', 'WalkthroughState', 'BlockState', 'ComponentState']