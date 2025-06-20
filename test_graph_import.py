#!/usr/bin/env python3
"""Test if the LangGraph can be imported correctly"""

import sys
import os
from pathlib import Path

# Add orchestrator to Python path
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))

try:
    from langraph_workflow import app
    print("✅ Successfully imported LangGraph app")
    print(f"   App type: {type(app)}")
    print(f"   App object: {app}")
    
    # Try to get graph structure
    if hasattr(app, 'graph'):
        print(f"   Graph nodes: {list(app.graph.nodes.keys()) if hasattr(app.graph, 'nodes') else 'N/A'}")
    
except ImportError as e:
    print(f"❌ Failed to import app: {e}")
    print("\nTrying to diagnose the issue...")
    
    try:
        import langraph_workflow
        print("✅ Can import langraph_workflow module")
        print(f"   Module attributes: {dir(langraph_workflow)}")
    except ImportError as e2:
        print(f"❌ Cannot import langraph_workflow module: {e2}")
        
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()