#!/usr/bin/env python3
"""
Simple verification script to check if the reorganized structure is correct
without requiring external dependencies
"""

import os
import sys
from pathlib import Path

def verify_structure():
    """Verify the new organized structure is correct"""
    print("🔍 Production Workflow Structure Verification")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    
    # Expected structure
    expected_structure = {
        "core/": ["production_workflow.py", "__init__.py"],
        "agents/": [
            "search_agent.py", "crawl_agent.py", "supabase_agent.py",
            "scripting_agent.py", "prompt_generation_agent.py", 
            "image_generation_agent.py", "voice_generation_agent.py",
            "__init__.py"
        ],
        "storage/": ["gdrive_storage.py", "upload_to_gdrive.py", "__init__.py"],
        "scripts/": ["run_workflow.py", "test_workflow.py", "__init__.py"],
        "assets/": [],
        "legacy/": ["agent1.py"],
        "": [  # Root files
            "README.md", "WORKFLOW_FIXES.md", "requirements.txt", 
            "langgraph.json", "credentials.json", "token.json", 
            "gdrive_folders.json"
        ]
    }
    
    print("📁 Checking directory structure...")
    all_good = True
    
    for dir_path, expected_files in expected_structure.items():
        full_dir_path = base_dir / dir_path if dir_path else base_dir
        
        if dir_path and not full_dir_path.exists():
            print(f"❌ Missing directory: {dir_path}")
            all_good = False
            continue
        
        if dir_path:
            print(f"✅ Directory exists: {dir_path}")
        
        for file_name in expected_files:
            file_path = full_dir_path / file_name
            if file_path.exists():
                print(f"  ✅ {file_name}")
            else:
                print(f"  ❌ Missing: {file_name}")
                all_good = False
    
    # Check asset directories
    asset_dirs = [
        "assets/generated_images",
        "assets/langgraph/generated_voices", 
        "assets/langgraph/voice_samples"
    ]
    
    print("\n📁 Checking asset directories...")
    for asset_dir in asset_dirs:
        full_path = base_dir / asset_dir
        if full_path.exists():
            print(f"✅ {asset_dir}")
        else:
            print(f"❌ Missing: {asset_dir}")
            all_good = False
    
    # Check for Python syntax errors (basic check)
    print("\n🐍 Checking Python files for basic syntax...")
    python_files = [
        "core/production_workflow.py",
        "scripts/run_workflow.py",
        "scripts/test_workflow.py"
    ]
    
    for py_file in python_files:
        file_path = base_dir / py_file
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                # Basic syntax check by compiling
                compile(content, str(file_path), 'exec')
                print(f"✅ Syntax OK: {py_file}")
            except SyntaxError as e:
                print(f"❌ Syntax Error in {py_file}: {e}")
                all_good = False
            except Exception as e:
                print(f"⚠️  Could not check {py_file}: {e}")
        else:
            print(f"❌ File not found: {py_file}")
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ Structure verification PASSED!")
        print("🎉 Production workflow has been successfully reorganized!")
    else:
        print("❌ Structure verification FAILED!")
        print("🔧 Some issues need to be addressed.")
    
    return all_good

if __name__ == "__main__":
    success = verify_structure()
    sys.exit(0 if success else 1)