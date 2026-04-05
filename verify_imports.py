import sys
import os

# Add the current directory to sys.path to simulate how langgraph-api loads it
sys.path.append(os.getcwd())

try:
    from src.graph import graph
    print("Successfully loaded graph 'agent' from src/graph.py")
except Exception as e:
    print(f"Failed to load graph: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
