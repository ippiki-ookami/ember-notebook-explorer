#!/usr/bin/env python3
"""
Ember Analysis Run Explorer

This utility helps you discover and examine available ember_output analysis runs.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

def find_ember_output_dirs(base_path: str = ".") -> List[Path]:
    """Find all ember_output directories recursively"""
    base = Path(base_path)
    ember_dirs = []
    
    for path in base.rglob("ember_output"):
        if path.is_dir():
            ember_dirs.append(path)
    
    return ember_dirs

def get_run_info(run_path: Path) -> Dict:
    """Extract information about an analysis run"""
    info = {
        "path": str(run_path),
        "name": run_path.name,
        "notebook": "unknown",
        "timestamp": "unknown",
        "steps_completed": 0,
        "total_files": 0,
        "has_walkthrough": False,
        "has_graphs": False,
        "file_sizes": {}
    }
    
    # Read run_info.json if available
    run_info_path = run_path / "run_info.json"
    if run_info_path.exists():
        try:
            with open(run_info_path) as f:
                run_data = json.load(f)
                info["notebook"] = run_data.get("notebook", "unknown")
                info["timestamp"] = run_data.get("timestamp", "unknown")
                info["steps_completed"] = len(run_data.get("steps_completed", []))
        except Exception as e:
            print(f"Warning: Could not read {run_info_path}: {e}")
    
    # Count files and check for key components
    try:
        for item in run_path.rglob("*"):
            if item.is_file():
                info["total_files"] += 1
                
                # Check for walkthrough
                if "walkthrough" in item.name.lower():
                    info["has_walkthrough"] = True
                
                # Check for generated graphs
                if "graph_" in item.name or item.name == "graph_visualization.html":
                    info["has_graphs"] = True
                
                # Store file sizes for key files
                if item.name in ["graph_data.json", "complete_walkthrough.md", "final_state.json"]:
                    info["file_sizes"][item.name] = item.stat().st_size
                    
        # Check step directories
        step_dirs = []
        for step_dir in run_path.iterdir():
            if step_dir.is_dir() and step_dir.name.startswith("step"):
                step_dirs.append(step_dir.name)
        
        info["step_directories"] = sorted(step_dirs)
        
    except Exception as e:
        print(f"Warning: Could not analyze {run_path}: {e}")
    
    return info

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def main():
    """Main function"""
    if len(sys.argv) > 1:
        search_path = sys.argv[1]
    else:
        search_path = "."
    
    print("🔍 Searching for ember_output directories...")
    ember_dirs = find_ember_output_dirs(search_path)
    
    if not ember_dirs:
        print("❌ No ember_output directories found")
        print("💡 Make sure you're in the right directory or specify a path:")
        print("   python3 list_ember_runs.py /path/to/search")
        return
    
    print(f"\n📁 Found {len(ember_dirs)} ember_output director{'y' if len(ember_dirs) == 1 else 'ies'}:\n")
    
    for ember_dir in ember_dirs:
        print(f"📂 {ember_dir}")
        
        # Get all analysis runs in this directory
        runs = []
        for item in ember_dir.iterdir():
            if item.is_dir() and "_" in item.name:  # Likely a timestamped run
                run_info = get_run_info(item)
                runs.append(run_info)
        
        if not runs:
            print("   (No analysis runs found)")
            continue
        
        # Sort by timestamp
        runs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        print(f"   📊 Analysis runs: {len(runs)}")
        
        for i, run in enumerate(runs):
            status_icons = []
            if run["steps_completed"] >= 5:
                status_icons.append("✅")
            if run["has_walkthrough"]:
                status_icons.append("📖")
            if run["has_graphs"]:
                status_icons.append("📊")
            
            status = " ".join(status_icons) if status_icons else "⏳"
            
            print(f"   {i+1}. {run['name']} {status}")
            print(f"      📄 Notebook: {run['notebook']}")
            print(f"      🕒 Time: {run['timestamp']}")
            print(f"      📁 Steps: {run['steps_completed']}, Files: {run['total_files']}")
            
            if run["file_sizes"]:
                size_info = []
                for filename, size in run["file_sizes"].items():
                    size_info.append(f"{filename}: {format_file_size(size)}")
                print(f"      💾 Key files: {', '.join(size_info)}")
            
            # Show command to generate graphs
            if not run["has_graphs"] and run["steps_completed"] >= 2:
                print(f"      🔧 Generate graphs: python3 generate_d3_graph.py '{run['path']}'")
            elif run["has_graphs"]:
                graph_html = Path(run["path"]) / "generated_graphs" / "graph_visualization.html"
                if graph_html.exists():
                    print(f"      🌐 View graphs: open '{graph_html}'")
            
            print()
    
    print("🎯 Usage:")
    print("   Generate graphs: python3 generate_d3_graph.py <run_path>")
    print("   View walkthrough: open <run_path>/step5_walkthrough/complete_walkthrough_preview.md")
    print("   ✅ = Complete analysis")
    print("   📖 = Has walkthrough") 
    print("   📊 = Has graphs")

if __name__ == "__main__":
    main()