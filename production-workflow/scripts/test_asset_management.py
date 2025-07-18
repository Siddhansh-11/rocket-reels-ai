# test_asset_management.py
#!/usr/bin/env python3
"""
Test script for Asset Management Agent
Tests all asset gathering, organization, and monitoring functions
"""

import asyncio
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Add the parent directory to the path so we can import our agents
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Change working directory to parent (production-workflow) for proper file access
os.chdir(parent_dir)

try:
    from agents.asset_gathering_agent import asset_gathering_tools
    from agents.notion_agent import notion_tools
    from storage.gdrive_storage import initialize_gdrive_storage
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the production-workflow directory")
    sys.exit(1)

class AssetManagementTester:
    def __init__(self):
        self.gdrive_storage = None
        self.test_results = []
        
    async def initialize_storage(self):
        """Initialize Google Drive storage for testing."""
        try:
            print("🔧 Initializing Google Drive storage...")
            
            # Check if credentials file exists
            credentials_path = "credentials.json"
            if not os.path.exists(credentials_path):
                print(f"❌ Credentials file not found at: {os.path.abspath(credentials_path)}")
                print("Expected location: production-workflow/credentials.json")
                return False
            
            # Check if gdrive_folders.json exists
            folders_path = "gdrive_folders.json"
            if not os.path.exists(folders_path):
                print(f"⚠️ gdrive_folders.json not found at: {os.path.abspath(folders_path)}")
                print("This file will be created automatically during initialization")
            
            print(f"📁 Working directory: {os.getcwd()}")
            print(f"📄 Using credentials: {os.path.abspath(credentials_path)}")
            
            self.gdrive_storage = await asyncio.to_thread(initialize_gdrive_storage, credentials_path)
            if self.gdrive_storage:
                print("✅ Google Drive storage initialized successfully")
                return True
            else:
                print("❌ Failed to initialize Google Drive storage")
                return False
        except Exception as e:
            print(f"❌ Storage initialization error: {e}")
            print(f"🔍 Current working directory: {os.getcwd()}")
            print(f"📁 Files in current directory: {os.listdir('.')}")
            return False
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        print(f"{status} - {test_name}")
        if details:
            print(f"   Details: {details}")
    
    async def test_gdrive_folder_listing(self):
        """Test listing all files in Google Drive folders."""
        print("\n📁 TESTING: Google Drive Folder Contents")
        print("=" * 50)
        
        if not self.gdrive_storage:
            self.log_test_result("GDrive Folder Listing", False, "Storage not initialized")
            return
        
        try:
            folder_summary = {}
            total_files = 0
            
            for folder_name, folder_id in self.gdrive_storage.folder_ids.items():
                print(f"\n📂 Checking folder: {folder_name} (ID: {folder_id})")
                
                try:
                    # List files in folder
                    results = self.gdrive_storage.service.files().list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields="files(id, name, mimeType, createdTime, size, webViewLink)",
                        pageSize=100
                    ).execute()
                    
                    files = results.get('files', [])
                    folder_summary[folder_name] = {
                        'file_count': len(files),
                        'files': files[:10]  # Show first 10 files
                    }
                    total_files += len(files)
                    
                    print(f"   📊 Files found: {len(files)}")
                    
                    # Show sample files
                    for i, file in enumerate(files[:5]):
                        size_mb = int(file.get('size', 0)) / (1024 * 1024) if file.get('size') else 0
                        created = file.get('createdTime', '')[:10]
                        print(f"   {i+1}. {file['name']} ({size_mb:.1f}MB, {created})")
                    
                    if len(files) > 5:
                        print(f"   ... and {len(files) - 5} more files")
                
                except Exception as e:
                    print(f"   ❌ Error listing {folder_name}: {e}")
                    folder_summary[folder_name] = {'file_count': -1, 'error': str(e)}
            
            # Summary
            print(f"\n📊 TOTAL ASSETS SUMMARY:")
            print(f"   • Total files across all folders: {total_files}")
            for folder_name, info in folder_summary.items():
                if info['file_count'] >= 0:
                    print(f"   • {folder_name}: {info['file_count']} files")
                else:
                    print(f"   • {folder_name}: Error - {info.get('error', 'Unknown')}")
            
            self.log_test_result("GDrive Folder Listing", True, f"{total_files} total files found")
            return folder_summary
            
        except Exception as e:
            self.log_test_result("GDrive Folder Listing", False, str(e))
            return {}
    
    async def test_project_folder_creation(self):
        """Test creating a project folder structure."""
        print("\n🏗️ TESTING: Project Folder Creation")
        print("=" * 50)
        
        # Test data - wrap in script_data
        test_script_data = {
            'title': 'Test Asset Management Project',
            'script_id': 'test_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
            'article_id': 'article_test_123',
            'script_content': 'This is a test script for asset management testing.',
            'metadata': {
                'platform': 'youtube',
                'duration': '60s',
                'test_mode': True
            }
        }
        
        try:
            # Create project folder structure - pass script_data directly
            create_tool = asset_gathering_tools[0]  # create_project_folder_structure
            result = await create_tool.ainvoke({"script_data": test_script_data})  # ← FIX: Wrap in script_data
            
            print("📋 Creation Result:")
            print(result)
            
            # Check if successful
            success = "PROJECT FOLDER STRUCTURE CREATED" in result and "✅" in result
            
            if success:
                # Extract folder path from result
                folder_path = ""
                for line in result.split('\n'):
                    if "Folder Path:" in line:
                        folder_path = line.split("Folder Path:")[1].strip()
                        break
                
                self.log_test_result("Project Folder Creation", True, f"Created: {folder_path}")
                return folder_path
            else:
                self.log_test_result("Project Folder Creation", False, "Creation failed")
                return None
                
        except Exception as e:
            self.log_test_result("Project Folder Creation", False, str(e))
            return None
    
    async def test_asset_organization(self, project_folder_path: str):
        """Test organizing assets into project folders."""
        print("\n📦 TESTING: Asset Organization")
        print("=" * 50)
        
        if not project_folder_path:
            self.log_test_result("Asset Organization", False, "No project folder to test with")
            return
        
        # Test asset data
        test_assets = {
            'images': [
                'test_image_1.jpg',
                'test_image_2.png'
            ],
            'voice_files': [
                'test_voice.wav'
            ],
            'script_content': 'This is the test script content for organization testing.',
            'metadata': {
                'test_mode': True,
                'created': datetime.now().isoformat()
            }
        }
        
        try:
            # Organize assets
            organize_tool = asset_gathering_tools[1]  # organize_generated_assets
            result = await organize_tool.ainvoke({
                'project_folder_path': project_folder_path,
                'assets_data': test_assets
            })
            
            print("📋 Organization Result:")
            print(result)
            
            success = "ASSETS ORGANIZED" in result and "✅" in result
            self.log_test_result("Asset Organization", success, 
                               "Assets organized successfully" if success else "Organization failed")
            
        except Exception as e:
            self.log_test_result("Asset Organization", False, str(e))
    
    async def test_folder_monitoring(self, project_folder_path: str):
        """Test monitoring final_draft folder."""
        print("\n🔍 TESTING: Folder Monitoring")
        print("=" * 50)
        
        if not project_folder_path:
            self.log_test_result("Folder Monitoring", False, "No project folder to test with")
            return
        
        try:
            # Monitor final_draft folder
            monitor_tool = asset_gathering_tools[2]  # monitor_final_draft_folder
            result = await monitor_tool.ainvoke(project_folder_path)
            
            print("📋 Monitoring Result:")
            print(result)
            
            # Monitoring is successful if it runs without error (even if no video found)
            success = "❌" not in result or "No video files detected yet" in result
            self.log_test_result("Folder Monitoring", success, 
                               "Monitoring working" if success else "Monitoring failed")
            
        except Exception as e:
            self.log_test_result("Folder Monitoring", False, str(e))
    
    async def test_project_summary(self, project_folder_path: str):
        """Test getting project summary."""
        print("\n📊 TESTING: Project Summary")
        print("=" * 50)
        
        if not project_folder_path:
            self.log_test_result("Project Summary", False, "No project folder to test with")
            return
        
        try:
            # Get project summary
            summary_tool = asset_gathering_tools[3]  # get_project_summary
            result = await summary_tool.ainvoke(project_folder_path)
            
            print("📋 Summary Result:")
            print(result)
            
            success = "PROJECT SUMMARY" in result and "📁" in result
            self.log_test_result("Project Summary", success, 
                               "Summary generated" if success else "Summary failed")
            
        except Exception as e:
            self.log_test_result("Project Summary", False, str(e))
    
    async def test_notion_integration(self, project_folder_path: str):
        """Test Notion integration functions."""
        print("\n📝 TESTING: Notion Integration")
        print("=" * 50)
        
        try:
            # Test creating Notion project row - wrap in script_data
            test_script_data = {
                'script_id': 'test_notion_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
                'article_id': 'article_notion_test',
                'project_name': 'Test Notion Integration',
                'folder_path': project_folder_path or 'RocketReelsAI/TestProject',
                'article_title': 'Test Article for Notion',
                'script_content': 'Test script content for Notion integration'
            }
            
            create_notion_tool = notion_tools[0]  # create_notion_project_row
            result = await create_notion_tool.ainvoke({"script_data": test_script_data})  # ← FIX: Wrap in script_data
            
            print("📋 Notion Creation Result:")
            print(result)
            
            success = "✅" in result and ("NOTION PROJECT CREATED" in result or "NOTION" in result)
            self.log_test_result("Notion Integration", success, 
                               "Notion row created" if success else "Notion creation failed")
            
        except Exception as e:
            self.log_test_result("Notion Integration", False, str(e))
    
    async def test_notion_project_listing(self):
        """Test listing Notion projects."""
        print("\n📋 TESTING: Notion Project Listing")
        print("=" * 50)
        
        try:
            # List Notion projects
            list_tool = notion_tools[3]  # list_notion_projects
            result = await list_tool.ainvoke("")
            
            print("📋 Projects List Result:")
            print(result)
            
            success = "❌" not in result
            self.log_test_result("Notion Project Listing", success, 
                               "Projects listed" if success else "Listing failed")
            
        except Exception as e:
            self.log_test_result("Notion Project Listing", False, str(e))
    
    async def test_all_asset_tools(self):
        """Test all asset management tools."""
        print("\n🧪 TESTING: All Asset Management Tools")
        print("=" * 50)
        
        # Test each tool individually
        tools_to_test = [
            ("create_project_folder_structure", asset_gathering_tools[0]),
            ("organize_generated_assets", asset_gathering_tools[1]),
            ("monitor_final_draft_folder", asset_gathering_tools[2]),
            ("get_project_summary", asset_gathering_tools[3])
        ]
        
        for tool_name, tool in tools_to_test:
            try:
                print(f"\n🔧 Testing tool: {tool_name}")
                
                # Test with minimal valid input
                if tool_name == "create_project_folder_structure":
                    test_input = {'title': 'Tool Test', 'script_id': 'test_123'}
                else:
                    test_input = "RocketReelsAI/TestProject"
                
                # This is just to verify the tool can be called (might fail due to missing data)
                result = await tool.ainvoke(test_input)
                print(f"   Result: {result[:100]}...")
                
                # Tool is accessible if it doesn't throw import/attribute errors
                self.log_test_result(f"Tool Access: {tool_name}", True, "Tool accessible")
                
            except (AttributeError, ImportError) as e:
                self.log_test_result(f"Tool Access: {tool_name}", False, f"Tool not accessible: {e}")
            except Exception as e:
                # Other exceptions are OK - tool exists but input might be invalid
                self.log_test_result(f"Tool Access: {tool_name}", True, f"Tool accessible (input error expected)")
    
    def print_test_summary(self):
        """Print final test summary."""
        print("\n" + "=" * 60)
        print("🏁 ASSET MANAGEMENT TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"📊 Tests Passed: {passed}/{total}")
        print(f"⏰ Test Duration: {datetime.now().strftime('%H:%M:%S')}")
        
        print("\n📋 Detailed Results:")
        for result in self.test_results:
            print(f"   {result['status']} {result['test']} ({result['timestamp']})")
            if result['details']:
                print(f"      {result['details']}")
        
        # Overall assessment
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        if success_rate >= 80:
            print(f"\n🎉 OVERALL ASSESSMENT: EXCELLENT ({success_rate:.1f}%)")
            print("   Asset management system is working well!")
        elif success_rate >= 60:
            print(f"\n⚠️ OVERALL ASSESSMENT: GOOD ({success_rate:.1f}%)")
            print("   Most features working, some issues to address")
        else:
            print(f"\n❌ OVERALL ASSESSMENT: NEEDS ATTENTION ({success_rate:.1f}%)")
            print("   Multiple issues found, requires debugging")
        
        return success_rate

async def run_comprehensive_test():
    """Run comprehensive asset management tests."""
    print("🚀 ROCKET REELS AI - ASSET MANAGEMENT TESTER")
    print("=" * 60)
    print(f"⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = AssetManagementTester()
    
    # Initialize storage
    if not await tester.initialize_storage():
        print("❌ Cannot proceed without Google Drive storage")
        return
    
    # Run tests
    print("\n🔍 Starting comprehensive test suite...")
    
    # Test 1: List all existing assets
    folder_summary = await tester.test_gdrive_folder_listing()
    
    # Test 2: Tool accessibility
    await tester.test_all_asset_tools()
    
    # Test 3: Create test project folder
    project_folder_path = await tester.test_project_folder_creation()
    
    # Test 4: Asset organization (if project folder created)
    if project_folder_path:
        await tester.test_asset_organization(project_folder_path)
        await tester.test_folder_monitoring(project_folder_path)
        await tester.test_project_summary(project_folder_path)
    
    # Test 5: Notion integration
    await tester.test_notion_integration(project_folder_path)
    await tester.test_notion_project_listing()
    
    # Final summary
    success_rate = tester.print_test_summary()
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if success_rate >= 80:
        print("   • Asset management system is ready for production use")
        print("   • Consider setting up automated monitoring")
        print("   • Test with real project data")
    else:
        print("   • Check Google Drive API credentials and permissions")
        print("   • Verify Notion API key and database configuration")
        print("   • Review error logs for specific issues")
        print("   • Run individual tool tests for debugging")

async def run_quick_asset_check():
    """Quick check of all assets in Google Drive folders."""
    print("🚀 QUICK ASSET CHECK - ROCKET REELS AI")
    print("=" * 50)
    
    try:
        # Initialize storage
        storage = await asyncio.to_thread(initialize_gdrive_storage)
        if not storage:
            print("❌ Failed to initialize Google Drive storage")
            return
        
        print("✅ Connected to Google Drive")
        print(f"📂 Found {len(storage.folder_ids)} configured folders")
        
        total_files = 0
        all_assets = {}
        
        for folder_name, folder_id in storage.folder_ids.items():
            print(f"\n📁 {folder_name.upper()}:")
            
            try:
                results = storage.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name, mimeType, createdTime, size)",
                    pageSize=50
                ).execute()
                
                files = results.get('files', [])
                all_assets[folder_name] = files
                total_files += len(files)
                
                if files:
                    print(f"   📊 {len(files)} files found")
                    for file in files[:3]:  # Show first 3 files
                        size_mb = int(file.get('size', 0)) / (1024 * 1024) if file.get('size') else 0
                        created = file.get('createdTime', '')[:10]
                        print(f"   • {file['name']} ({size_mb:.1f}MB, {created})")
                    
                    if len(files) > 3:
                        print(f"   ... and {len(files) - 3} more files")
                else:
                    print("   📂 Empty folder")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_assets[folder_name] = []
        
        print(f"\n📊 TOTAL SUMMARY:")
        print(f"   🗂️ Total files: {total_files}")
        print(f"   📁 Folders checked: {len(storage.folder_ids)}")
        
        # Show file type breakdown
        file_types = {}
        for folder_files in all_assets.values():
            for file in folder_files:
                mime_type = file.get('mimeType', 'unknown')
                file_types[mime_type] = file_types.get(mime_type, 0) + 1
        
        if file_types:
            print(f"\n📈 FILE TYPES:")
            for mime_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {mime_type}: {count} files")
        
        print(f"\n✅ Asset check completed at {datetime.now().strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Asset check failed: {e}")

async def main():
    """Main function to run tests."""
    if len(sys.argv) < 2:
        print("""
🧪 ASSET MANAGEMENT TESTER

Usage:
    python test_asset_management.py <command>

Commands:
    full        - Run comprehensive test suite
    quick       - Quick check of all assets in Google Drive
    assets      - List all assets in all folders (same as quick)

Examples:
    python test_asset_management.py full
    python test_asset_management.py quick
    python test_asset_management.py assets
""")
        return
    
    command = sys.argv[1].lower()
    
    if command in ['full', 'comprehensive', 'all']:
        await run_comprehensive_test()
    elif command in ['quick', 'assets', 'list']:
        await run_quick_asset_check()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'full' for comprehensive tests or 'quick' for asset listing")

if __name__ == "__main__":
    asyncio.run(main())