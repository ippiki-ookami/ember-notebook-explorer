#!/usr/bin/env python3
"""
Run the ember notebook code with comprehensive logging of all outputs.
This script extracts code cells from ember.py and executes them while
capturing all print outputs to a log file.
"""

import json
import sys
import os
from datetime import datetime
from contextlib import redirect_stdout
import io

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Generate timestamp for log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/ember_run_{timestamp}.log"

class TeeOutput:
    """Duplicate output to both console and log file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')
        
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        self.log.close()

# Set up logging
tee = TeeOutput(log_filename)
sys.stdout = tee

print(f"=== Ember Notebook Execution Log ===")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Log file: {log_filename}")
print("=" * 60)
print()

# Load the notebook from ember.py
with open('ember.py', 'r') as f:
    notebook_content = f.read()

# Parse the notebook JSON
notebook = json.loads(notebook_content)

# Initialize global namespace for code execution
exec_namespace = {}

# Execute each code cell
for i, cell in enumerate(notebook['cells']):
    if cell['cell_type'] == 'code':
        print(f"\n{'='*60}")
        print(f"CELL {i+1} (ID: {cell.get('id', 'unknown')})")
        print(f"{'='*60}")
        
        # Get the source code
        source = cell.get('source', [])
        if isinstance(source, list):
            code = ''.join(source)
        else:
            code = source
            
        # Print the code being executed
        print("CODE:")
        print("-" * 40)
        print(code)
        print("-" * 40)
        print("\nOUTPUT:")
        
        # Execute the code
        try:
            # Capture any additional output
            output_buffer = io.StringIO()
            
            # Execute with output capture
            exec(code, exec_namespace)
            
            # Get captured output
            captured = output_buffer.getvalue()
            if captured:
                print(captured)
                
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        print()  # Empty line after each cell

# Add summary at the end
print("\n" + "="*60)
print("EXECUTION SUMMARY")
print("="*60)
print(f"Total cells processed: {len(notebook['cells'])}")
print(f"Code cells executed: {sum(1 for c in notebook['cells'] if c['cell_type'] == 'code')}")
print(f"Log saved to: {log_filename}")
print("\nKey objects created:")

# List key objects in the namespace
for name, obj in exec_namespace.items():
    if not name.startswith('_') and name not in ['In', 'Out', 'get_ipython', 'exit', 'quit']:
        obj_type = type(obj).__name__
        print(f"  - {name}: {obj_type}")

# Close the log file
print(f"\n=== Execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
tee.close()
sys.stdout = tee.terminal

print(f"\nExecution complete! Full log saved to: {log_filename}")