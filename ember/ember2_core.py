"""
Core analysis functions extracted from ember2.ipynb
This module contains the actual component-based analysis implementation
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Add necessary imports
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI()

# Import dataclasses from ember2_integration
from ember2_integration import (
    ComponentState,
    BlockState, 
    WalkthroughState
)

# LangGraph state management (simplified for now)
class AnalysisGraph:
    """Simplified analysis graph for component extraction"""
    
    def __init__(self):
        self.state = None
        
    async def analyze_notebook(self, notebook_path: str) -> WalkthroughState:
        """
        Analyze a notebook using component-based approach
        This is a simplified version - in production would use full LangGraph pipeline
        """
        
        # Load notebook
        with open(notebook_path, 'r') as f:
            notebook_data = json.load(f)
        
        # Create initial state
        state = WalkthroughState(
            code_overview="Analyzing notebook with component-based approach",
            notebook_path=notebook_path,
            total_blocks=len([c for c in notebook_data.get('cells', []) if c.get('cell_type') == 'code'])
        )
        
        # Process each code cell
        block_id = 1
        for cell_idx, cell in enumerate(notebook_data.get('cells', [])):
            if cell.get('cell_type') != 'code':
                continue
                
            # Extract source code
            source = cell.get('source', [])
            if isinstance(source, list):
                source = ''.join(source)
            
            if not source.strip():
                continue
            
            # Create block state
            block = BlockState(
                block_id=str(block_id),
                block_name=f"Block {block_id}",
                block_type=self._determine_block_type(source),
                block_content=source,
                initial_description=f"Code block {block_id} from cell {cell_idx}"
            )
            
            # Extract components from the block
            components = self._extract_components(source, str(block_id))
            block.component_states = {c.component_id: c for c in components}
            
            state.block_states[str(block_id)] = block
            block_id += 1
        
        # Analyze dependencies between blocks
        self._analyze_dependencies(state)
        
        # Set execution order
        state.execution_order = sorted(state.block_states.keys())
        state.total_components = sum(len(b.component_states) for b in state.block_states.values())
        state.blocks_analyzed = len(state.block_states)
        state.analysis_phase = "complete"
        
        return state
    
    def _determine_block_type(self, source: str) -> str:
        """Determine the type of a code block"""
        if 'import ' in source or 'from ' in source:
            return 'imports'
        elif 'class ' in source:
            return 'classes'
        elif 'def ' in source:
            return 'utilities'
        else:
            return 'main'
    
    def _extract_components(self, source: str, block_id: str) -> List[ComponentState]:
        """Extract components from source code"""
        components = []
        lines = source.split('\n')
        component_num = 1
        
        # Track class context for methods
        current_class_id = None
        
        for line_num, line in enumerate(lines):
            stripped = line.strip()
            
            # Import statements
            if stripped.startswith('import ') or stripped.startswith('from '):
                comp_id = f"{block_id}:{component_num}"
                # Extract module name
                if 'import ' in stripped:
                    parts = stripped.split('import')
                    if len(parts) > 1:
                        module = parts[1].strip().split()[0].replace(',', '')
                    else:
                        module = 'unknown'
                else:
                    module = stripped.split('from')[1].split('import')[0].strip()
                
                components.append(ComponentState(
                    component_id=comp_id,
                    component_name=f"Import_{module.replace('.', '_')}",
                    component_number=component_num,
                    type="import",
                    library=module,
                    full_code=stripped,
                    description=f"Import {module}",
                    block_id=block_id,
                    line_start=line_num,
                    line_end=line_num
                ))
                component_num += 1
            
            # Class definitions
            elif stripped.startswith('class '):
                comp_id = f"{block_id}:{component_num}"
                class_name = stripped.split('class')[1].split('(')[0].split(':')[0].strip()
                current_class_id = comp_id
                
                components.append(ComponentState(
                    component_id=comp_id,
                    component_name=class_name,
                    component_number=component_num,
                    type="class",
                    library="local",
                    full_code=stripped,
                    description=f"Class {class_name}",
                    block_id=block_id,
                    line_start=line_num,
                    line_end=line_num
                ))
                component_num += 1
            
            # Function/method definitions
            elif stripped.startswith('def '):
                comp_id = f"{block_id}:{component_num}"
                func_name = stripped.split('def')[1].split('(')[0].strip()
                
                # Check if this is a method (indented under a class)
                is_method = len(line) - len(line.lstrip()) > 0
                
                comp = ComponentState(
                    component_id=comp_id,
                    component_name=func_name,
                    component_number=component_num,
                    type="method" if is_method else "function",
                    library="local",
                    full_code=stripped,
                    description=f"{'Method' if is_method else 'Function'} {func_name}",
                    block_id=block_id,
                    line_start=line_num,
                    line_end=line_num
                )
                
                # If it's a method, set parent to current class
                if is_method and current_class_id:
                    comp.parent_component_ids = [current_class_id]
                    # Also update the class's children
                    for c in components:
                        if c.component_id == current_class_id:
                            c.child_component_ids.append(comp_id)
                
                components.append(comp)
                component_num += 1
            
            # Variable assignments (top-level only)
            elif '=' in stripped and not stripped.startswith('#'):
                if len(line) - len(line.lstrip()) == 0:  # Top-level
                    var_name = stripped.split('=')[0].strip()
                    if var_name and var_name[0].isalpha():
                        comp_id = f"{block_id}:{component_num}"
                        components.append(ComponentState(
                            component_id=comp_id,
                            component_name=var_name,
                            component_number=component_num,
                            type="variable",
                            library="local",
                            full_code=stripped,
                            description=f"Variable {var_name}",
                            block_id=block_id,
                            line_start=line_num,
                            line_end=line_num
                        ))
                        component_num += 1
        
        return components
    
    def _analyze_dependencies(self, state: WalkthroughState):
        """Analyze dependencies between blocks and components"""
        # Build registries
        for block_id, block in state.block_states.items():
            for comp in block.component_states.values():
                # Register imports
                if comp.type == "import":
                    state.import_registry.setdefault(comp.library, []).append(comp.component_id)
                # Register functions
                elif comp.type == "function":
                    state.function_registry[comp.component_name] = comp.component_id
                # Register classes
                elif comp.type == "class":
                    state.class_registry[comp.component_name] = comp.component_id
        
        # Analyze block dependencies
        block_ids = list(state.block_states.keys())
        for i, block_id in enumerate(block_ids):
            block = state.block_states[block_id]
            
            # Check if this block uses components from previous blocks
            for prev_block_id in block_ids[:i]:
                prev_block = state.block_states[prev_block_id]
                
                # Check if any component names from prev_block appear in this block's content
                for comp in prev_block.component_states.values():
                    if comp.component_name in block.block_content:
                        if prev_block_id not in block.depends_on_blocks:
                            block.depends_on_blocks.append(prev_block_id)
                        if block_id not in prev_block.depended_by_blocks:
                            prev_block.depended_by_blocks.append(block_id)
                        break


async def run_complete_analysis(notebook_path: str) -> WalkthroughState:
    """
    Run the complete analysis pipeline
    This is the main entry point for the component-based analysis
    """
    graph = AnalysisGraph()
    return await graph.analyze_notebook(notebook_path)


# Export main function
__all__ = ['run_complete_analysis', 'AnalysisGraph']