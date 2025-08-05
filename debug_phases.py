#!/usr/bin/env python3
"""Debug script to check phase component assignment"""

import json
import subprocess
import sys

def run_ember(notebook_path, use_cache=True):
    """Run ember.py and return the output"""
    cmd = ['.venv/bin/python', 'ember.py', notebook_path, '--export-json']
    if not use_cache:
        cmd.append('--no-cache')
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print stderr for debugging
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    # Parse JSON from stdout
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}", file=sys.stderr)
        print(f"STDOUT: {result.stdout}", file=sys.stderr)
        return None

def analyze_output(data):
    """Analyze the ember output"""
    if not data:
        return
    
    print("\n=== GRAPH ANALYSIS ===")
    nodes = data.get('graph', {}).get('nodes', [])
    
    # Count node types
    node_types = {}
    node_names = []
    for node in nodes:
        node_type = node.get('type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
        if node_type not in ['cell']:
            node_names.append(f"{node.get('name')} ({node_type})")
    
    print(f"Total nodes: {len(nodes)}")
    for ntype, count in sorted(node_types.items()):
        print(f"  {ntype}: {count}")
    
    print("\nComponent names:")
    for name in sorted(node_names):
        print(f"  - {name}")
    
    print("\n=== PHASE ANALYSIS ===")
    phases = data.get('phases', [])
    print(f"Total phases: {len(phases)}")
    
    for phase in phases:
        components = phase.get('components', [])
        print(f"\n{phase['phase_id']}: {phase['title']}")
        print(f"  Components ({len(components)}):")
        if components:
            for comp in components:
                print(f"    - {comp}")
        else:
            print("    (empty)")

def main():
    notebook = sys.argv[1] if len(sys.argv) > 1 else 'tiny_demo.ipynb'
    
    print(f"Analyzing {notebook}...")
    
    # Test with cache
    print("\n>>> WITH CACHE:")
    data = run_ember(notebook, use_cache=True)
    analyze_output(data)
    
    # Test without cache (commented out to avoid API calls)
    # print("\n>>> WITHOUT CACHE:")
    # data = run_ember(notebook, use_cache=False)
    # analyze_output(data)

if __name__ == "__main__":
    main()