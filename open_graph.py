#!/usr/bin/env python3
"""
Quick opener for Ember graph visualizations on Windows WSL
"""

import sys
import subprocess
import os
from pathlib import Path

def open_graph_visualization(run_path: str):
    """Open graph visualization in Windows browser from WSL"""
    
    # Find the HTML file
    html_path = Path(run_path) / "generated_graphs" / "graph_visualization.html"
    
    if not html_path.exists():
        print(f"❌ Graph visualization not found: {html_path}")
        print(f"🔧 Generate it first: python3 generate_d3_graph.py '{run_path}'")
        return False
    
    # Convert WSL path to Windows path
    wsl_path = str(html_path.absolute())
    
    print(f"🌐 Opening graph visualization...")
    print(f"📁 File: {html_path}")
    
    try:
        # Method 1: Try using explorer.exe (most reliable)
        subprocess.run(['explorer.exe', str(html_path)], check=True)
        print("✅ Opened in Windows browser!")
        return True
        
    except subprocess.CalledProcessError:
        print("⚠️  Explorer method failed, trying alternative...")
        
        try:
            # Method 2: Try cmd.exe start
            subprocess.run(['cmd.exe', '/c', 'start', str(html_path)], check=True)
            print("✅ Opened in Windows browser!")
            return True
            
        except subprocess.CalledProcessError:
            print("⚠️  Windows commands failed, trying HTTP server...")
            
            # Method 3: Start HTTP server and provide localhost URL
            graphs_dir = html_path.parent
            print(f"\n🚀 Starting HTTP server in: {graphs_dir}")
            print("🌐 Open this URL in your Windows browser:")
            print("   http://localhost:8000/graph_visualization.html")
            print("\n⏹️  Press Ctrl+C to stop the server")
            
            try:
                os.chdir(graphs_dir)
                subprocess.run(['python3', '-m', 'http.server', '8000'])
            except KeyboardInterrupt:
                print("\n👋 HTTP server stopped")
                return True
            
    return False

def main():
    if len(sys.argv) != 2:
        print("📊 Ember Graph Visualization Opener")
        print("\nUsage:")
        print("  python3 open_graph.py <ember_output_run_directory>")
        print("\nExamples:")
        print("  python3 open_graph.py ember/ember_output/tiny_demo_20250806_062811")
        print("  python3 open_graph.py ember/ember_output/multi_agent_20250806_072751")
        print("\n💡 Use list_ember_runs.py to see available runs")
        return
    
    run_path = sys.argv[1]
    
    if not Path(run_path).exists():
        print(f"❌ Directory not found: {run_path}")
        return
        
    success = open_graph_visualization(run_path)
    
    if not success:
        print("\n❌ All methods failed. Manual options:")
        html_path = Path(run_path) / "generated_graphs" / "graph_visualization.html"
        wsl_path = f"\\\\wsl$\\Ubuntu{html_path.absolute()}"
        print(f"1. Copy this path to Windows browser: file:///{wsl_path}")
        print(f"2. Copy file to Windows: cp '{html_path}' /mnt/c/temp/")

if __name__ == "__main__":
    main()