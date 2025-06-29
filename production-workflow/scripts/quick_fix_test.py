# quick_fix_test.py
import os
import sys
from datetime import datetime

# Add the production-workflow directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Change working directory to parent (production-workflow) for proper file access
os.chdir(parent_dir)

# Test with corrected parameters
async def test_corrected_tools():
    try:
        from agents.asset_gathering_agent import asset_gathering_tools
        from agents.notion_agent import notion_tools
        
        print("✅ Successfully imported agent modules")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📄 Asset tools found: {len(asset_gathering_tools)}")
        print(f"📄 Notion tools found: {len(notion_tools)}")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"📁 Current directory: {os.getcwd()}")
        print(f"📂 Available files: {os.listdir('.')}")
        return
    
    # Test data with proper structure
    test_script_data = {
        'title': 'Quick Fix Test Project',
        'script_id': 'quickfix_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'article_id': 'article_quickfix_123',
        'script_content': 'HOOK: This is a test hook for the quick fix. This is test script content for quick fix testing.',
        'project_name': 'Quick Fix Test',
        'folder_path': 'RocketReelsAI/QuickFixTest',
        'article_title': 'Quick Fix Test Article',
        'metadata': {
            'platform': 'youtube',
            'test_mode': True
        }
    }
    
    print("\n🧪 Testing with corrected parameters...")
    
    try:
        # Test asset gathering with proper script_data parameter
        create_tool = asset_gathering_tools[0]
        print(f"🔧 Testing tool: {create_tool.name}")
        result = await create_tool.ainvoke({"script_data": test_script_data})
        print("\n📁 Asset Creation Result:")
        print(result[:300] + "..." if len(result) > 300 else result)
    except Exception as e:
        print(f"❌ Asset creation error: {e}")
    
    try:
        # Test Notion with proper script_data parameter
        notion_tool = notion_tools[0]
        print(f"\n🔧 Testing tool: {notion_tool.name}")
        result = await notion_tool.ainvoke({"script_data": test_script_data})
        print("\n📝 Notion Creation Result:")
        print(result[:300] + "..." if len(result) > 300 else result)
    except Exception as e:
        print(f"❌ Notion creation error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_corrected_tools())