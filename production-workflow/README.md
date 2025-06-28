# Production Workflow

A proper graph-structured workflow for automated content creation following this sequence:

## Workflow Sequence

```
Search → Crawl → Store Article → Script Generation → Store Script
                                                        ↓
                    Prompt Generation ← ← ← ← ← ← ← ← ← ←
                           ↓
                    Image Generation (parallel)
                           ↓
                    Voice Generation (parallel)
                           ↓
                        Finalize
```

## Architecture

The workflow uses LangGraph to create a state-managed graph with the following nodes:

1. **Search Node**: Finds trending tech articles using Tavily search
2. **Crawl Node**: Extracts full article content using enhanced parsing
3. **Store Article Node**: Saves article content to Supabase database
4. **Script Generation Node**: Creates engaging scripts from article content
5. **Store Script Node**: Saves generated scripts to Supabase
6. **Parallel Generation Nodes**:
   - **Prompt Generation**: Creates image prompts from script content
   - **Image Generation**: Generates images from prompts
   - **Voice Generation**: Creates voiceover from script text
7. **Finalize Node**: Compiles all results and provides summary

## Usage

### Basic Usage
```bash
python run_workflow.py "latest AI breakthrough"
```

### Interactive Mode
```bash
python run_workflow.py
# Enter topic when prompted
```

### Programmatic Usage
```python
from production_workflow import run_production_workflow

result = await run_production_workflow("quantum computing news")
print(f"Article ID: {result.article_id}")
print(f"Script ID: {result.script_id}")
```

## State Management

The workflow uses a `WorkflowState` dataclass to track:
- Input parameters (topic, user query)
- Search results and URLs
- Crawled article data
- Storage results and IDs
- Generated script content
- Parallel generation results
- Error tracking and status

## Dependencies

Install required packages:
```bash
pip install -r requirements.txt
```

## Environment Variables

Ensure these environment variables are set:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key
- `MISTRAL_API_KEY`: Mistral AI API key for content analysis
- `TAVILY_API_KEY`: Tavily search API key

## Output

The workflow generates:
- Article content stored in Supabase
- Script content stored in Supabase
- Image prompts and generated images
- Voice files from script content
- Comprehensive workflow summary

## Error Handling

The workflow includes robust error handling:
- Individual node failures don't stop the entire workflow
- Errors are tracked in the state and reported in the final summary
- Graceful degradation when optional services fail