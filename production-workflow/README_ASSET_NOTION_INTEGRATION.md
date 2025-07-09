# Asset Gathering & Notion Integration

This document describes the new asset gathering and Notion integration nodes added to the production workflow.

## New Workflow Flow

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

## New Nodes

### 1. Asset Gathering Node

**Purpose**: Organizes all generated assets into a structured Google Drive folder.

**What it does**:
- Creates a project folder in `RocketReelsAI/` named after the script
- Creates organized subfolders:
  - `generated_images/` - AI-generated images
  - `voiceover/` - Generated voice files
  - `scripts/` - Script content and metadata
  - `final_draft/` - Empty folder for editor to upload final video
  - `resources/` - Additional resources
- Moves generated assets to appropriate folders
- Creates project metadata file

### 2. Notion Integration Node

**Purpose**: Creates project tracking in Notion workspace and sets up monitoring.

**What it does**:
- Creates new row in Notion database with project details
- Sets initial status to "Assets Ready"
- Links to Google Drive folder path
- Prepares for video upload monitoring

## Setup Requirements

### Google Drive Setup

1. Ensure `RocketReelsAI` folder exists in your Google Drive
2. Configure Google Drive API credentials:
   - Place `credentials.json` in `langgraph/` directory
   - Run workflow once to generate `token.json`

### Notion Setup

1. Create a Notion integration:
   - Go to https://developers.notion.com/
   - Create new integration
   - Copy the integration token

2. Create a database with these properties:
   - `Project Name` (Title)
   - `Status` (Select: "Assets Ready", "Video Ready", "Published")
   - `Created Date` (Date)
   - `Script ID` (Text)
   - `Article ID` (Text)
   - `Folder Path` (Text)
   - `Script Preview` (Text)
   - `Visual Suggestions` (Text)
   - `Video Upload Date` (Date)
   - `Video File` (Text)

3. Share the database with your integration

4. Configure environment variables:
   ```bash
   NOTION_API_KEY=your_notion_integration_token
   NOTION_DATABASE_ID=your_notion_database_id
   ```

## Folder Structure Created

```
RocketReelsAI/
└── ProjectName_YYYYMMDD_HHMM/
    ├── generated_images/
    │   ├── image1.jpg
    │   ├── image2.jpg
    │   └── ...
    ├── voiceover/
    │   ├── voice_file.wav
    │   └── ...
    ├── scripts/
    │   ├── script_YYYYMMDD_HHMM.txt
    │   └── project_metadata.json
    ├── final_draft/          # Editor uploads video here
    │   └── (empty initially)
    └── resources/
        └── (additional files)
```

## Monitoring Video Uploads

### Manual Monitoring

Use the monitoring script to check for video uploads:

```bash
# Check all projects
python production-workflow/scripts/monitor_final_draft.py check-all

# Monitor specific project
python production-workflow/scripts/monitor_final_draft.py monitor "RocketReelsAI/ProjectName_20241228_1430"

# Manually trigger Notion update
python production-workflow/scripts/monitor_final_draft.py update "RocketReelsAI/ProjectName_20241228_1430" "final_video.mp4"

# Get project summary
python production-workflow/scripts/monitor_final_draft.py summary "RocketReelsAI/ProjectName_20241228_1430"
```

### Automated Monitoring (Future)

For production use, implement:
- Google Drive webhooks for real-time notifications
- Scheduled cron job to run monitoring script
- Notion webhook integration for status updates

## Workflow State Updates

New state fields added:

```python
# Asset gathering phase
project_folder_path: str = ""
asset_organization_result: str = ""

# Notion integration phase
notion_project_id: str = ""
notion_status: str = ""
```

## Error Handling

Both nodes include comprehensive error handling:
- Google Drive API failures
- Notion API failures
- Folder creation errors
- Asset organization errors

Errors are captured in the workflow state and displayed in the final summary.

## Usage Flow

1. **Run Production Workflow**: Execute normal workflow to generate assets
2. **Asset Organization**: New node automatically creates and organizes folders
3. **Notion Tracking**: Project row created with "Assets Ready" status
4. **Editor Work**: Editor downloads assets, creates video, uploads to `final_draft/`
5. **Monitoring**: Run monitoring script or use automated system
6. **Status Update**: Notion automatically updated to "Video Ready"
7. **Publishing**: Video ready for final publishing workflow

## API Tools Available

### Asset Gathering Tools

- `create_project_folder_structure()` - Create organized folder structure
- `organize_generated_assets()` - Move assets to appropriate folders
- `monitor_final_draft_folder()` - Check for video uploads
- `get_project_summary()` - Get detailed project status

### Notion Tools

- `create_notion_project_row()` - Create project tracking row
- `update_notion_video_status()` - Update status when video uploaded
- `monitor_gdrive_folder()` - Set up monitoring (placeholder)
- `list_notion_projects()` - List current projects

## Troubleshooting

### Common Issues

1. **Folder not created**: Check Google Drive credentials and permissions
2. **Notion not updating**: Verify API key and database ID
3. **Assets not moved**: Ensure source files exist and are accessible
4. **Monitoring not working**: Check folder paths and permissions

### Debug Commands

```bash
# Test Google Drive connection
python -c "from production-workflow.agents.asset_gathering_agent import _get_drive_service; print(_get_drive_service().files().list().execute())"

# Test Notion connection
python -c "from production-workflow.agents.notion_agent import notion_tools; import asyncio; asyncio.run(notion_tools[3].ainvoke(''))"
```

## Future Enhancements

- Real-time webhook integration
- Automated video processing triggers
- Integration with video editing APIs
- Advanced project analytics in Notion
- Multi-editor collaboration features