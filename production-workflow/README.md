# Production Workflow 🚀

A complete automated content creation workflow that transforms trending tech news into production-ready video assets. This workflow uses LangGraph to orchestrate a series of AI agents that search, crawl, analyze, script, and generate all assets needed for viral tech content.

## ✨ What This Workflow Does

1. **🔍 Intelligent Search** - Finds trending tech articles using AI-powered search
2. **🕷️ Smart Crawling** - Extracts full article content with enhanced parsing
3. **🗄️ Data Storage** - Saves content to Supabase for persistence
4. **📝 Script Generation** - Creates engaging YouTube/social media scripts
5. **🎨 Asset Creation** - Generates images, prompts, and voiceover in parallel
6. **📁 Organization** - Creates organized Google Drive project folders
7. **📋 Project Tracking** - Sets up Notion workspace for team collaboration
8. **🎬 Production Ready** - Delivers complete asset package for editors

## 🏗️ Workflow Architecture

```
Search → Crawl → Store Article → Generate Script → Store Script
                                                        ↓
    Image Generation ← Prompt Generation ← Voice Generation (parallel)
            ↓                                    ↓
            └──── Asset Gathering ←──────────────┘
                        ↓
                Notion Integration
                        ↓
                    Finalize
```

## 🚀 Quick Setup Guide

### Prerequisites

- Python 3.8+ installed
- Google Account (for Drive integration)
- Notion account
- Required API keys (see below)

### 1. Clone and Navigate

```bash
git clone https://github.com/your-repo/rocket-reels-ai.git
cd rocket-reels-ai/production-workflow
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the production-workflow directory:

```bash
cp .env.template .env
```

Edit `.env` with your API keys:

```properties
# Required API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
TAVILY_API_KEY=your_tavily_api_key
MISTRAL_API_KEY=your_mistral_api_key
OPENAI_API_KEY=your_openai_api_key

# Supabase (Database)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Notion (Project Management)
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# Optional: Advanced Features
ELEVENLABS_API_KEY=your_elevenlabs_api_key  # For voice generation
PEXELS_API_KEY=your_pexels_api_key          # For stock images
```

### 4. Google Drive Setup

1. **Enable Google Drive API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google Drive API
   - Create credentials (Desktop Application)
   - Download `credentials.json`

2. **Place credentials**:
   ```bash
   # Place credentials.json in production-workflow directory
   cp /path/to/your/credentials.json ./credentials.json
   ```

3. **Create main folder**:
   - Create a folder named "RocketReelsAI" in your Google Drive
   - This will contain all generated project folders

### 5. Notion Setup

Run the automated setup script:

```bash
python scripts/setup_notion_workspace.py
```

This will:
- Create a properly configured Notion database
- Set up all required properties
- Update your `.env` file with the database ID
- Create a sample project for testing

### 6. Test Installation

```bash
# Test the workflow structure
python scripts/test_workflow.py

# Run a quick test workflow
python scripts/run_workflow.py "AI breakthrough"
```

## 📖 Detailed Usage

### Basic Usage

```bash
# Run workflow with a topic
python scripts/run_workflow.py "latest AI breakthrough"

# Interactive mode
python scripts/run_workflow.py
# Enter topic when prompted
```

### Programmatic Usage

```python
import asyncio
from core.production_workflow import run_production_workflow

async def main():
    result = await run_production_workflow("quantum computing news")
    print(f"✅ Workflow Complete!")
    print(f"📄 Article ID: {result.article_id}")
    print(f"📝 Script ID: {result.script_id}")
    print(f"📁 Project Folder: {result.project_folder_path}")
    print(f"📋 Notion Project: {result.notion_project_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Output Structure

Each workflow run creates:

```
Google Drive: RocketReelsAI/ProjectName_YYYYMMDD_HHMM/
├── generated_images/     # AI-generated images
├── voiceover/           # Generated voice files
├── scripts/             # Script files and metadata
├── final_draft/         # For editor to upload final video
└── resources/           # Additional resources

Supabase Database:
├── Articles table       # Stored article content
└── Scripts table        # Generated scripts with metadata

Notion Workspace:
└── Project tracking row with all details and status
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API for AI processing |
| `TAVILY_API_KEY` | ✅ | Search API for finding articles |
| `MISTRAL_API_KEY` | ✅ | Content analysis and processing |
| `SUPABASE_URL` | ✅ | Database URL |
| `SUPABASE_ANON_KEY` | ✅ | Database access key |
| `NOTION_API_KEY` | ✅ | Notion integration token |
| `NOTION_DATABASE_ID` | ✅ | Target database ID |
| `OPENAI_API_KEY` | ⚠️ | Alternative AI provider |
| `ELEVENLABS_API_KEY` | 🔲 | Premium voice generation |
| `PEXELS_API_KEY` | 🔲 | Stock image access |

### Workflow Customization

Edit `core/production_workflow.py` to customize:
- Search parameters and filters
- Script generation prompts
- Image generation styles
- Voice generation settings
- Asset organization structure

## 🛠️ API Keys Setup Guide

### 1. Anthropic (Claude)
- Visit [Anthropic Console](https://console.anthropic.com/)
- Create account and get API key
- Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### 2. Tavily (Search)
- Visit [Tavily](https://tavily.com/)
- Sign up and get API key
- Add to `.env`: `TAVILY_API_KEY=tvly-...`

### 3. Supabase (Database)
- Visit [Supabase](https://supabase.com/)
- Create new project
- Go to Settings > API
- Copy URL and anon key
- Add to `.env`

### 4. Notion (Project Management)
- Visit [Notion Developers](https://developers.notion.com/)
- Create new integration
- Copy integration token
- Run setup script to create database

### 5. Optional APIs
- **ElevenLabs**: [ElevenLabs](https://elevenlabs.io/) for premium voice
- **Pexels**: [Pexels API](https://www.pexels.com/api/) for stock images
- **OpenAI**: [OpenAI](https://openai.com/) as alternative AI provider

## 📊 Monitoring & Management

### Project Status Tracking

Use the Notion database to track:
- ✅ Assets Ready - Workflow completed, assets organized
- 🎬 Video Ready - Editor uploaded final video
- 📺 Published - Content live on platforms

### Monitoring Scripts

```bash
# Check all active projects
python scripts/monitor_final_draft.py check-all

# Monitor specific project for video uploads
python scripts/monitor_final_draft.py monitor "ProjectName_20241228_1430"

# Get detailed project summary
python scripts/monitor_final_draft.py summary "ProjectName_20241228_1430"
```

## 🚨 Troubleshooting

### Common Issues

1. **Google Drive Authentication Failed**
   ```bash
   # Delete token and re-authenticate
   rm token.json
   python scripts/run_workflow.py "test"
   ```

2. **Notion Database Not Found**
   ```bash
   # Re-run setup script
   python scripts/setup_notion_workspace.py
   ```

3. **Supabase Connection Error**
   - Verify URL and keys in `.env`
   - Check Supabase project status
   - Ensure tables exist (run schema setup)

4. **API Rate Limits**
   - Check API usage in respective dashboards
   - Implement delays between requests
   - Use alternative API providers

### Debug Mode

```bash
# Run with verbose logging
DEBUG=true python scripts/run_workflow.py "test topic"

# Test individual components
python scripts/test_workflow.py --component search
python scripts/test_workflow.py --component notion
```

## 🔄 Workflow States

The workflow tracks progress through these states:

| State | Description |
|-------|-------------|
| `search` | Finding trending articles |
| `crawl` | Extracting article content |
| `store_article` | Saving to database |
| `generate_script` | Creating script content |
| `store_script` | Saving script to database |
| `prompt_generation` | Creating image prompts |
| `image_generation` | Generating visual assets |
| `voice_generation` | Creating voiceover |
| `asset_gathering` | Organizing in Google Drive |
| `notion_integration` | Setting up project tracking |
| `complete` | Workflow finished |

## 🎯 Team Workflow

### For Content Creators
1. Run workflow with your topic
2. Review generated script and assets
3. Notify editor about new project

### For Editors
1. Check Notion for "Assets Ready" projects
2. Download assets from Google Drive project folder
3. Create final video
4. Upload to `final_draft/` folder
5. Status automatically updates to "Video Ready"

### For Publishers
1. Monitor Notion for "Video Ready" projects
2. Download final video from `final_draft/`
3. Publish to target platforms
4. Update status to "Published"

## 📚 Advanced Features

### Custom Agents
Add new agents in `agents/` directory:
```python
# agents/custom_agent.py
from langchain.tools import tool

@tool
async def custom_function(input_data: str) -> str:
    """Your custom processing logic"""
    return "processed_result"
```

### Workflow Extensions
Extend the workflow by adding nodes:
```python
# In core/production_workflow.py
self.workflow.add_node("custom_node", self.custom_node)
self.workflow.add_edge("existing_node", "custom_node")
```

### Integration with Other Tools
- **Video Editing APIs**: Integrate with automated video creation
- **Social Media APIs**: Auto-publish to platforms
- **Analytics**: Track performance and optimize content

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- 📧 Email: support@rocket-reels-ai.com
- 💬 Discord: [Join our community](https://discord.gg/rocket-reels)
- 📖 Documentation: [Full docs](https://docs.rocket-reels-ai.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Made with ❤️ by the Rocket Reels AI Team**

*Transform trending tech news into viral content with the power of AI!*