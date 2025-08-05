# Component Linking System - Help Request

## Overview
We're building a code analysis system that generates educational walkthroughs for Jupyter notebooks. The system extracts components (functions, classes, variables, etc.) from code blocks and creates clickable links in a special markdown format for a VS Code extension.

## Goal
Generate walkthroughs where EVERY component mention is properly linked using the format:
```
[[component:block_id:component_number:component_name|display text]]
```

## Current Issue
Some components are being missed or not properly linked in the final walkthrough. We need to ensure 100% coverage of all component references.

## System Architecture

### 1. Component Extraction
We extract components from each code block:

```python
async def analyze_block_components(block: dict, explanation: CodeExplanation, block_index: int) -> ComponentAnalysis:
    """Analyze components within a specific code block"""
    
    prompt = COMPONENT_EXTRACTION_PROMPT.format(
        code_block=block["content"],
        block_index=block_index,
        explanation_overview=explanation.blocks[block_index].overview,
        dependencies=json.dumps([{"from": e.from_id, "to": e.to_id, "type": e.type} for e in explanation.dependencies])
    )
    
    chain = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(ComponentAnalysis)
    result = await chain.ainvoke(prompt)
    
    return result
```

### 2. Component Extraction Prompt
```python
COMPONENT_EXTRACTION_PROMPT = """Analyze this code block and extract ALL meaningful components that would help someone understand the code structure.

CODE BLOCK (Block {block_index}):
{code_block}

BLOCK OVERVIEW:
{explanation_overview}

DEPENDENCIES:
{dependencies}

Extract components including but not limited to:
- Import statements (e.g., "import pandas", "from X import Y")
- Function definitions (e.g., "def function_name")
- Class definitions (e.g., "class ClassName")
- Method definitions (e.g., "def method_name" inside classes)
- Variable assignments (e.g., "variable = value")
- Constants (e.g., "MAX_VALUE = 100")
- Key expressions or operations (e.g., "list.append()", "dict['key']")

For each component, provide:
1. component_name: The exact name as it appears in code
2. component_type: One of [import, function, class, method, variable, constant, expression]
3. description: A brief description of what this component does
4. line_numbers: List of line numbers where this component appears/is defined
5. usage_context: How this component is used in this block
6. calls: List of other component names this component directly calls/uses
"""
```

### 3. Walkthrough Generation with Component Linking

```python
BLOCK_WALKTHROUGH_PROMPT = """Generate an educational walkthrough for this code block, incorporating ALL component descriptions.

## BLOCK INFORMATION:
Block {block_index}: {block_name}
Overview: {overview}
Deep Description: {deep_description}

## COMPONENT DESCRIPTIONS:
{component_descriptions}

## COMPONENT LINK MAPPING:
Below are the EXACT links you must use when mentioning any component by name. When you need to mention a component, find it in this map and use the provided link format:

{component_link_map}

## CROSS-REFERENCE MAPPING:
Some components appear in multiple blocks. Here are all occurrences:
{cross_reference_map}

## INSTRUCTIONS:
Create a comprehensive educational walkthrough that:
1. Explains the block's purpose and architecture
2. Integrates ALL component descriptions naturally
3. Uses the EXACT component links from the mapping above
4. When referring to components from other blocks, use their specific block's link
5. Maintain narrative flow while being technically accurate

IMPORTANT: 
- Use the EXACT link format from the component link mapping
- Every component name mentioned MUST use its corresponding link
- Do not create new links - only use the ones provided in the mapping
- When a component appears in multiple blocks, choose the most contextually appropriate link
"""
```

### 4. Component Link Mapping Functions

```python
def build_component_name_map(walkthrough_state: WalkthroughState) -> Dict[str, str]:
    """Build a dynamic component name mapping from the walkthrough state"""
    component_map = {}
    
    for block_id, block_state in walkthrough_state.block_states.items():
        for comp_id, comp_state in block_state.component_states.items():
            key = f"{block_id}:{comp_state.component_number}"
            # Make component names safe for linking
            safe_name = comp_state.component_name.replace(" ", "_").replace("-", "_")
            component_map[key] = safe_name
    
    return component_map

def build_cross_reference_map(walkthrough_state: WalkthroughState) -> Dict[str, List[str]]:
    """Build a map of component names to all their occurrences across blocks"""
    cross_refs = {}
    
    for block_id, block_state in walkthrough_state.block_states.items():
        for comp_state in block_state.component_states.values():
            comp_name = comp_state.component_name
            if comp_name not in cross_refs:
                cross_refs[comp_name] = []
            
            link = f"[[component:{block_id}:{comp_state.component_number}:{comp_name}|{comp_name}]]"
            cross_refs[comp_name].append(link)
    
    return cross_refs

async def generate_block_walkthrough(block_id: str, walkthrough_state: WalkthroughState) -> str:
    """Generate walkthrough content for a single block with component links"""
    block_state = walkthrough_state.block_states[block_id]
    
    # Build component descriptions
    component_descriptions = []
    for comp_state in block_state.component_states.values():
        desc = f"{comp_state.component_number}. **{comp_state.component_name}** ({comp_state.component_type}): {comp_state.final_description}"
        component_descriptions.append(desc)
    
    # Build component link map with variations
    component_link_map = []
    for comp_state in block_state.component_states.values():
        safe_name = comp_state.component_name.replace(" ", "_").replace("-", "_")
        link = f"[[component:{block_id}:{comp_state.component_number}:{safe_name}|{{display_text}}]]"
        
        # Add variations of the component name
        variations = [
            comp_state.component_name,
            f"{comp_state.component_name} function",
            f"{comp_state.component_name} method",
            f"{comp_state.component_name} class",
            f"{comp_state.component_name} variable",
            f"{comp_state.component_name}()",
            f"`{comp_state.component_name}`"
        ]
        
        for variation in variations:
            component_link_map.append(f'"{variation}": {link.format(display_text=variation)}')
    
    # Get cross-references
    cross_refs = build_cross_reference_map(walkthrough_state)
    cross_ref_text = json.dumps(cross_refs, indent=2)
    
    prompt = BLOCK_WALKTHROUGH_PROMPT.format(
        block_index=block_id,
        block_name=block_state.explanation_block.name,
        overview=block_state.explanation_block.overview,
        deep_description=block_state.deep_description,
        component_descriptions="\n".join(component_descriptions),
        component_link_map="{\n" + ",\n".join(component_link_map) + "\n}",
        cross_reference_map=cross_ref_text
    )
    
    chain = ChatOpenAI(model="gpt-4o", temperature=0.1)
    response = await chain.ainvoke(prompt)
    
    return response.content
```

## Problem Examples

### Example 1: Missing Components
In the tiny_demo.ipynb test file, these components weren't being captured or linked:
- `VectorStore` (the class itself, not just its methods)
- `clean_text` function 
- `tokenize` function
- `append` expression in `self.vectors.append(vector)`
- Various variable names like `store`, `cleaned`, `tokens`

### Example 2: Inconsistent Linking
Some components appeared with variations:
- `clean_text` vs `clean_text function` vs `clean_text()`
- `__init__` vs `__init__ method`
- `store.add` vs `store.add()`

### Example 3: Components Not Highlighted
When viewing in VS Code, some components showed as yellow (properly linked) while others didn't, particularly those with "function" in the brackets.

## Current Results
From tiny_demo_walkthrough.json:
- Total components: 19
- Components covered: 19

But when manually reviewing the markdown, we can see that not all component mentions are actually linked.

## What We've Tried

1. **Dynamic Component Mapping**: Building component maps from the walkthrough state
2. **Explicit Link Mapping in Prompt**: Providing exact link formats for each component
3. **Component Variations**: Including different ways a component might be referenced
4. **Cross-Reference Mapping**: Tracking components that appear in multiple blocks

## Questions for Qwen Coder

1. **Component Detection**: How can we ensure our component extraction catches ALL meaningful components, including:
   - Class names (not just their methods)
   - All variable assignments
   - Method calls and expressions
   - Import statements

2. **Link Coverage**: How can we ensure that EVERY mention of a component in the walkthrough text gets properly linked? Currently, the LLM sometimes uses the component name without the link format.

3. **Prompt Engineering**: Is there a better way to structure our prompts to ensure the LLM always uses the provided link format and never mentions a component without its link?

4. **Post-Processing**: Should we implement a post-processing step that searches for unlinked component names and adds the links? If so, how do we handle ambiguous cases?

5. **Validation**: How can we validate that all components are properly linked before saving the final walkthrough?

## Desired Outcome
A system that:
1. Extracts 100% of meaningful components from code
2. Generates walkthroughs where EVERY component mention is properly linked
3. Handles variations in how components are referenced
4. Works automatically for any notebook without manual intervention