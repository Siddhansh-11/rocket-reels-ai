# Prompt and Image Generation Agents

This document describes the new prompt generation and image generation agents integrated into the Rocket Reels AI workflow.

## Overview

The system now includes two new agents that work together:

1. **Prompt Generation Agent**: Takes scripts and generates detailed image prompts for different scenes
2. **Image Generation Agent**: Takes prompts and generates images using AI services (OpenAI DALL-E 3, Stability AI, etc.)

## Database Schema

Three tables support this functionality:

### `scripts` table
```sql
- id: UUID (primary key)
- article_id: UUID (foreign key to articles)
- content: TEXT
- style: VARCHAR(50)
- template: VARCHAR(50)
- platform: VARCHAR(50)
- duration: INTEGER
- metadata: JSONB
- created_at/updated_at: TIMESTAMP
```

### `prompts` table
```sql
- id: UUID (primary key)
- script_id: UUID (foreign key to scripts)
- scene_number: INTEGER
- scene_description: TEXT
- prompt: TEXT
- style: VARCHAR(50)
- aspect_ratio: VARCHAR(10)
- metadata: JSONB
- created_at/updated_at: TIMESTAMP
```

### `generated_images` table
```sql
- id: UUID (primary key)
- prompt_id: UUID (foreign key to prompts)
- prompt: TEXT
- scene_number: INTEGER
- scene_description: TEXT
- image_url: TEXT
- image_base64: TEXT
- revised_prompt: TEXT
- model: VARCHAR(100)
- style: VARCHAR(50)
- aspect_ratio: VARCHAR(10)
- metadata: JSONB
- created_at/updated_at: TIMESTAMP
```

## Setup

1. **Database Migration**: Run the SQL migration to create the tables:
   ```bash
   # Execute the migration file in your Supabase database
   psql -h your-db-host -U your-db-user -d your-db-name -f database_migrations/create_prompts_tables.sql
   ```

2. **Environment Variables**: Add these to your `.env` file:
   ```env
   # For AIML API with Flux models (recommended - high quality)
   AIML_API_KEY=your-aiml-api-key
   
   # For OpenAI DALL-E 3 (alternative)
   OPENAI_API_KEY=your-openai-api-key
   
   # For Stability AI (alternative)
   STABILITY_API_KEY=your-stability-api-key
   
   # For Replicate (future support)
   REPLICATE_API_KEY=your-replicate-api-key
   
   # Choose default service
   IMAGE_GENERATION_SERVICE=aiml  # Options: aiml, openai, stability
   ```

## Usage

### Via Workflow

The agents are integrated into the main workflow. After script generation, they automatically:
1. Generate prompts from the script
2. Generate images from the prompts

You can also trigger them directly:

```python
# In a chat/workflow context
"generate prompts"  # Triggers prompt generation
"create images"     # Triggers image generation
```

### Direct API Usage

```python
from orchestrator.prompt_generation_agent import PromptGenerationAgent
from orchestrator.image_generation_agent import ImageGenerationAgent

# Generate prompts
prompt_agent = PromptGenerationAgent()
prompts = await prompt_agent.generate_prompts_from_script(
    script_content="Your script here...",
    script_id="optional_script_id",
    num_prompts=5
)

# Generate images
image_agent = ImageGenerationAgent()
images = await image_agent.generate_images_from_prompts(
    prompts=prompts['prompts'],
    service="openai"  # or "stability"
)
```

### Testing

Run the test script to verify everything works:

```bash
python test_prompt_image_workflow.py
```

## Workflow Integration

The agents are integrated into the main workflow:

1. **Script Writing** → 2. **Prompt Generation** → 3. **Image Generation** → 4. **Visual Generation**

Each phase includes human review checkpoints.

## Features

### Prompt Generation Agent
- Analyzes scripts to identify key scenes
- Generates detailed, style-specific prompts
- Supports different visual styles (photorealistic, illustration, 3D render)
- Optimizes for different aspect ratios (16:9, 9:16, 1:1)
- Stores prompts in database with metadata

### Image Generation Agent
- Supports multiple AI services:
  - AIML API with Flux models (recommended - state-of-the-art quality)
  - OpenAI DALL-E 3 (good quality, more expensive)
  - Stability AI (fast, affordable)
  - Extensible for other services
- Handles different aspect ratios
- Stores both URLs and base64 data
- Includes revised prompts from AI
- Rate limiting protection

## Example Output

When you generate a script, the system will:

1. **Generate Prompts**:
   ```
   1. Scene 1: Hook moment - presenter speaking to camera
      Prompt: "Professional content creator in modern studio, looking directly at camera with excited expression, dramatic lighting..."
   
   2. Scene 2: Problem visualization - frustrated creator
      Prompt: "Stressed content creator at cluttered desk, multiple monitors showing low view counts..."
   ```

2. **Generate Images**:
   - Creates high-quality images for each scene
   - Stores them in the database
   - Makes them available for video assembly

## Cost Considerations

- **Prompt Generation**: Uses Claude API (~$0.01-0.02 per script)
- **Image Generation**:
  - AIML API (Flux): ~$0.01-0.02 per image
  - OpenAI DALL-E 3: ~$0.04-0.08 per image
  - Stability AI: ~$0.002-0.02 per image
- Total cost for 5 prompts + 5 images: ~$0.10-0.45 (depending on service)

## Troubleshooting

1. **No API Keys**: Ensure you have at least one image generation API key set
2. **Database Errors**: Run the migration script to create required tables
3. **Rate Limits**: The system includes delays between image generations
4. **Memory Issues**: For base64 storage, consider using URLs only for large batches

## Future Enhancements

- Support for more image generation services (Midjourney, Replicate)
- Batch processing optimization
- Image variations and editing
- Style transfer capabilities
- Integration with video assembly pipeline