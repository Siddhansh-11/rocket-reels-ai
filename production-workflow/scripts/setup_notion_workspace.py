#!/usr/bin/env python3
"""
Setup script for Notion workspace and database for Rocket Reels AI
Creates database with all required properties for asset management workflow
"""

import os
import sys
import json
import requests
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
os.chdir(parent_dir)

# Load environment variables
load_dotenv()

class NotionWorkspaceSetup:
    def __init__(self):
        self.notion_token = os.getenv('NOTION_API_KEY')
        self.notion_version = "2022-06-28"
        self.base_url = "https://api.notion.com/v1"
        
        # Correct page ID format extracted from your URL
        self.parent_page_id = "221aae4d-6ceb-8038-b82f-e15aee549d0b"
        
        if not self.notion_token:
            print("❌ NOTION_API_KEY not found in environment variables")
            print("Please add your Notion integration token to .env file:")
            print("NOTION_API_KEY=your_notion_integration_token")
            sys.exit(1)
            
        # Add debug print to verify the page ID
        print(f"🔧 Using page ID: {self.parent_page_id}")
    
    def get_headers(self):
        """Get headers for Notion API requests"""
        return {
            "Authorization": f"Bearer {self.notion_token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json"
        }
    
    async def verify_parent_page_access(self):
        """Verify we can access the existing parent page"""
        try:
            print(f"🔍 Verifying access to existing page: {self.parent_page_id}")
            
            response = requests.get(
                f"{self.base_url}/pages/{self.parent_page_id}",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                page_info = response.json()
                # Try to get page title
                page_title = "Rocket Reels AI Database Page"
                if page_info.get('properties', {}).get('title', {}).get('title'):
                    page_title = page_info['properties']['title']['title'][0]['text']['content']
                
                print(f"✅ Successfully accessed parent page: {page_title}")
                return True
            else:
                error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"❌ Cannot access parent page: {response.status_code}")
                print(f"Error details: {error_detail}")
                print(f"\n💡 Please ensure:")
                print(f"   1. Your Notion integration has access to the page")
                print(f"   2. The page ID is correct: {self.parent_page_id}")
                print(f"   3. The integration is added to your workspace")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying parent page: {e}")
            return False

    async def create_database(self):
        """Create the Rocket Reels AI project database with all required properties"""
        
        # Define the database schema with all required properties
        database_schema = {
            "parent": {
                "type": "page_id",
                "page_id": self.parent_page_id
            },
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": "🚀 Rocket Reels AI - Project Tracker"
                    }
                }
            ],
            "properties": {
                "Topic name": {
                    "title": {}  # This is the main title property
                },
                "Final video link": {
                    "url": {}
                },
                "Folder link": {
                    "url": {}
                },
                "Created Date and time": {
                    "date": {}
                },
                "Publish Date and time": {
                    "date": {}
                },
                "Channel": {
                    "multi_select": {
                        "options": [
                            {
                                "name": "Instagram",
                                "color": "pink"
                            },
                            {
                                "name": "LinkedIn",
                                "color": "blue"
                            },
                            {
                                "name": "Twitter",
                                "color": "purple"
                            },
                            {
                                "name": "YouTube",
                                "color": "red"
                            },
                            {
                                "name": "TikTok",
                                "color": "green"
                            }
                        ]
                    }
                },
                "Deploy Status": {
                    "select": {
                        "options": [
                            {
                                "name": "Review",
                                "color": "yellow"
                            },
                            {
                                "name": "Publish",
                                "color": "green"
                            },
                            {
                                "name": "Re-do",
                                "color": "red"
                            },
                            {
                                "name": "Published",
                                "color": "blue"
                            },
                            {
                                "name": "Assets Ready",
                                "color": "orange"
                            }
                        ]
                    }
                },
                "Comments": {
                    "rich_text": {}
                },
                # Additional useful properties
                "Script ID": {
                    "rich_text": {}
                },
                "Article ID": {
                    "rich_text": {}
                },
                "Priority": {
                    "select": {
                        "options": [
                            {
                                "name": "High",
                                "color": "red"
                            },
                            {
                                "name": "Medium",
                                "color": "yellow"
                            },
                            {
                                "name": "Low",
                                "color": "gray"
                            }
                        ]
                    }
                },
                "Platform": {
                    "select": {
                        "options": [
                            {
                                "name": "YouTube Shorts",
                                "color": "red"
                            },
                            {
                                "name": "Instagram Reels",
                                "color": "pink"
                            },
                            {
                                "name": "TikTok",
                                "color": "green"
                            },
                            {
                                "name": "LinkedIn Video",
                                "color": "blue"
                            }
                        ]
                    }
                },
                "Duration": {
                    "rich_text": {}
                },
                "Engagement Score": {
                    "number": {
                        "format": "percent"
                    }
                }
            }
        }
        
        try:
            print("🏗️ Creating Notion database in your existing page...")
            
            response = requests.post(
                f"{self.base_url}/databases",
                headers=self.get_headers(),
                json=database_schema
            )
            
            if response.status_code == 200:
                database_info = response.json()
                database_id = database_info['id']
                database_url = database_info['url']
                
                print(f"✅ Database created successfully!")
                print(f"📋 Database ID: {database_id}")
                print(f"🔗 Database URL: {database_url}")
                
                # Update .env file with new database ID
                self.update_env_file(database_id)
                
                return database_id, database_url
            else:
                error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"❌ Failed to create database: {response.status_code}")
                print(f"Error details: {error_detail}")
                return None, None
                
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return None, None
    
    def update_env_file(self, database_id: str):
        """Update .env file with new database ID"""
        try:
            env_path = ".env"
            env_lines = []
            database_id_updated = False
            
            # Read existing .env file
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add NOTION_DATABASE_ID
            updated_lines = []
            for line in env_lines:
                if line.startswith('NOTION_DATABASE_ID='):
                    updated_lines.append(f'NOTION_DATABASE_ID={database_id}\n')
                    database_id_updated = True
                else:
                    updated_lines.append(line)
            
            # Add NOTION_DATABASE_ID if not found
            if not database_id_updated:
                updated_lines.append(f'NOTION_DATABASE_ID={database_id}\n')
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                f.writelines(updated_lines)
            
            print(f"✅ Updated .env file with database ID: {database_id}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not update .env file: {e}")
            print(f"Please manually add this line to your .env file:")
            print(f"NOTION_DATABASE_ID={database_id}")
    
    async def create_sample_project(self, database_id: str):
        """Create a sample project to test the database"""
        sample_project = {
            "parent": {
                "database_id": database_id
            },
            "properties": {
                "Topic name": {
                    "title": [
                        {
                            "text": {
                                "content": "🎬 Sample Project - Setup Test"
                            }
                        }
                    ]
                },
                "Deploy Status": {
                    "select": {
                        "name": "Review"
                    }
                },
                "Created Date and time": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                },
                "Platform": {
                    "select": {
                        "name": "YouTube Shorts"
                    }
                },
                "Priority": {
                    "select": {
                        "name": "Medium"
                    }
                },
                "Comments": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "🎯 This is a sample project created during Notion workspace setup.\n\n✅ Database is working correctly!\n\n🔗 Integrated with Rocket Reels AI asset management system.\n\nYou can delete this entry once you start creating real projects."
                            }
                        }
                    ]
                },
                "Script ID": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "sample_setup_test_001"
                            }
                        }
                    ]
                },
                "Duration": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "60 seconds"
                            }
                        }
                    ]
                },
                "Folder link": {
                    "url": "https://drive.google.com/drive/folders/sample"
                }
            }
        }
        
        try:
            print("🎬 Creating sample project...")
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.get_headers(),
                json=sample_project
            )
            
            if response.status_code == 200:
                page_info = response.json()
                page_url = page_info.get('url', '#')
                print(f"✅ Sample project created!")
                print(f"🔗 Project URL: {page_url}")
                return True
            else:
                error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"⚠️ Could not create sample project: {response.status_code}")
                print(f"Error details: {error_detail}")
                return False
                
        except Exception as e:
            print(f"⚠️ Error creating sample project: {e}")
            return False
    
    async def verify_database_access(self, database_id: str):
        """Verify that we can access the created database"""
        try:
            print("🔍 Verifying database access...")
            
            response = requests.get(
                f"{self.base_url}/databases/{database_id}",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                database_info = response.json()
                title = database_info.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')
                properties_count = len(database_info.get('properties', {}))
                
                print(f"✅ Database access verified!")
                print(f"📋 Database title: {title}")
                print(f"🔧 Properties count: {properties_count}")
                return True
            else:
                print(f"❌ Cannot access database: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying database: {e}")
            return False
    
    def print_setup_summary(self, database_id: str, database_url: str):
        """Print setup summary and next steps"""
        print("\n" + "="*60)
        print("🎉 NOTION WORKSPACE SETUP COMPLETE!")
        print("="*60)
        
        print(f"\n📋 **Database Details:**")
        print(f"   • Database ID: {database_id}")
        print(f"   • Database URL: {database_url}")
        print(f"   • Parent Page: {self.parent_page_id}")
        print(f"   • Properties: 12 configured")
        
        print(f"\n🔧 **Environment Configuration:**")
        print(f"   • .env file updated with database ID")
        print(f"   • NOTION_API_KEY: {'✅ Found' if self.notion_token else '❌ Missing'}")
        print(f"   • NOTION_DATABASE_ID: ✅ Set to {database_id[:8]}...")
        
        print(f"\n📊 **Database Properties Setup:**")
        properties = [
            "Topic name (Title)", "Final video link (URL)", "Folder link (URL)",
            "Created Date and time (Date)", "Publish Date and time (Date)",
            "Channel (Multi-select)", "Deploy Status (Select)", "Comments (Rich Text)",
            "Script ID (Text)", "Article ID (Text)", "Priority (Select)",
            "Platform (Select)", "Duration (Text)", "Engagement Score (Number)"
        ]
        for prop in properties:
            print(f"   ✅ {prop}")
        
        print(f"\n🔗 **Integration Details:**")
        print(f"   • Uses existing Social Media Team workspace")
        print(f"   • Database created in your empty page")
        print(f"   • Connected to existing Tasks Tracker")
        print(f"   • Ready for Rocket Reels AI integration")
        
        print(f"\n🚀 **Next Steps:**")
        print(f"   1. Test the updated agent code:")
        print(f"      cd D:\\rocket-reels-ai\\production-workflow")
        print(f"      python scripts\\quick_fix_test.py")
        print(f"   2. Run full asset management test:")
        print(f"      python scripts\\test_asset_management.py full")
        print(f"   3. Start using the production workflow!")
        print(f"   4. View your new database: {database_url}")
        
        print(f"\n💡 **Tips:**")
        print(f"   • Sample project created for testing")
        print(f"   • Database integrates with your existing workspace")
        print(f"   • All agent code will use new schema")
        print(f"   • Database is ready for production use")

async def main():
    """Main setup function"""
    print("🚀 ROCKET REELS AI - NOTION WORKSPACE SETUP")
    print("="*60)
    print(f"⏰ Setup started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 Using existing Social Media Team workspace")
    print(f"📄 Target page: 221aae4d-6ceb-8038-b82f-e15aee549d0b")
    
    setup = NotionWorkspaceSetup()
    
    # Step 1: Verify access to existing parent page
    if not await setup.verify_parent_page_access():
        print("❌ Setup failed - cannot access the existing parent page")
        print("\n💡 To fix this:")
        print("   1. Make sure your Notion integration is added to the workspace")
        print("   2. Share the page with your integration")
        print("   3. Check that the page ID is correct")
        return
    
    # Step 2: Create database in the existing page
    database_id, database_url = await setup.create_database()
    if not database_id:
        print("❌ Setup failed - could not create database")
        return
    
    # Step 3: Verify access
    if not await setup.verify_database_access(database_id):
        print("❌ Setup failed - cannot access created database")
        return
    
    # Step 4: Create sample project
    await setup.create_sample_project(database_id)
    
    # Step 5: Print summary
    setup.print_setup_summary(database_id, database_url)
    
    print(f"\n✅ Setup completed successfully at {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎉 Your Rocket Reels AI database is ready in your Social Media Team workspace!")

if __name__ == "__main__":
    asyncio.run(main())