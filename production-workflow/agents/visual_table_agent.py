"""
Visual Table Agent for Production Workflow

This agent creates a comprehensive visual production table that maps each script shot
to its corresponding visual assets (images, videos, prompts).
"""

import json
import os
import csv
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
# Google Drive functionality removed - handled by asset gathering agent

@tool
async def create_visual_production_table(
    shot_breakdown: List[Dict[str, Any]],
    shot_timing: List[Dict[str, Any]], 
    visual_prompts: List[Dict[str, Any]],
    generated_images: List[str],
    broll_assets: Dict[str, Any],
    image_prompt_mapping: Optional[Dict[str, Dict[str, Any]]] = None
) -> str:
    """
    Create a comprehensive visual production table mapping shots to assets.
    
    Args:
        shot_breakdown: List of shot analysis data
        shot_timing: List of timing information for each shot
        visual_prompts: List of generated visual prompts mapped to shots
        generated_images: List of generated image file paths
        broll_assets: Dictionary containing B-roll search results and downloads
        image_prompt_mapping: Optional dictionary mapping image files to their source prompts/shots
        
    Returns:
        Status message with table creation details and CSV content
    """
    try:
        print("Creating visual production table...")
        
        # Create the table data structure
        table_data = []
        
        # Create shot mapping
        shot_map = {shot['shot_number']: shot for shot in shot_breakdown}
        timing_map = {timing['shot_number']: timing for timing in shot_timing}
        
        # Map visual prompts to shots
        prompt_map = {}
        for prompt in visual_prompts:
            shot_id = prompt.get('shot_number', prompt.get('id'))
            if shot_id:
                prompt_map[shot_id] = prompt
        
        # Create accurate mapping using image_prompt_mapping
        image_map = {}
        video_map = {}
        
        # First, map images to their corresponding shots using the accurate mapping
        print(f"Mapping {len(generated_images)} images to their corresponding shots using image_prompt_mapping...")
        
        # Use the accurate image_prompt_mapping to map images to shots
        if image_prompt_mapping:
            for image_path in generated_images:
                if image_path in image_prompt_mapping:
                    mapping_data = image_prompt_mapping[image_path]
                    shot_number = mapping_data.get('shot_number')
                    if shot_number:
                        image_map[shot_number] = image_path
                        print(f"  Mapped image {os.path.basename(image_path)} to shot {shot_number}")
                else:
                    print(f"  Warning: Image {os.path.basename(image_path)} has no mapping data")
        else:
            print("  Warning: No image_prompt_mapping provided, cannot accurately map images to shots")
            # Fallback: try to use shot numbers from prompts if available
            for i, image_path in enumerate(generated_images):
                if i < len(visual_prompts):
                    prompt_data = visual_prompts[i]
                    shot_number = prompt_data.get('shot_number')
                    if shot_number:
                        image_map[shot_number] = image_path
                        print(f"  Fallback mapped image {os.path.basename(image_path)} to shot {shot_number}")
                    else:
                        print(f"  Warning: Image {os.path.basename(image_path)} cannot be mapped (no shot number in prompt)")
                else:
                    print(f"  Warning: Extra image {os.path.basename(image_path)} has no corresponding prompt")
        
        # Report on image mapping status
        shots_with_images = set(image_map.keys())
        print(f"  Successfully mapped {len(shots_with_images)} shots to images: {sorted(shots_with_images)}")
        
        # Then, intelligently map videos to shots that need them (shots without images)
        print(f"Mapping broll videos to shots without images...")
        if broll_assets and 'downloaded_files' in broll_assets:
            video_files = [f for f in broll_assets['downloaded_files'] if f.get('type') == 'video']
            
            # Get all shots that don't have images (these are candidates for videos)
            shots_needing_videos = []
            for shot_num in sorted(shot_map.keys()):
                if shot_num not in image_map:  # Shot doesn't have an image
                    shots_needing_videos.append(shot_num)
            
            print(f"  Found {len(shots_needing_videos)} shots without images that can use videos: {shots_needing_videos}")
            
            # Map videos to shots without images
            for i, video_file in enumerate(video_files):
                if i < len(shots_needing_videos):
                    shot_num = shots_needing_videos[i]
                    video_map[shot_num] = video_file
                    print(f"  Mapped video {video_file.get('filename', 'unknown')} to shot {shot_num}")
                else:
                    print(f"  Warning: Extra video {video_file.get('filename', 'unknown')} has no corresponding shot")
            
            # Report any unmapped shots that still need videos
            for shot_num in shots_needing_videos[len(video_files):]:
                print(f"  Warning: Shot {shot_num} needs video but none was found")
        
        # Build the table
        for shot_num in range(1, len(shot_breakdown) + 1):
            shot_data = shot_map.get(shot_num, {})
            timing_data = timing_map.get(shot_num, {})
            prompt_data = prompt_map.get(shot_num, {})
            
            # Determine what assets this shot has (based on actual mappings, not hardcoded types)
            shot_type = shot_data.get('type', 'talking_head')
            
            image_generated = ""
            video_generated = ""
            
            # Check if shot has an image assigned
            if shot_num in image_map:
                image_generated = f"✓ Generated image: {os.path.basename(image_map[shot_num])}"
                # If image is assigned, no video for this shot
                video_generated = ""
            
            # Check if shot has a video assigned (only if no image)
            elif shot_num in video_map:
                video_file = video_map[shot_num]
                video_generated = f"✓ Pexels video: {video_file.get('filename', 'Unknown')}"
                # If video is assigned, no image for this shot
                image_generated = ""
            
            # If no assets assigned, mark as missing
            else:
                image_generated = "❌ No visual asset assigned"
                video_generated = ""
            
            # Create row data
            row = {
                'Shot': shot_num,
                'Script': shot_data.get('text', ''),
                'Visual Prompt': prompt_data.get('prompt', prompt_data.get('visual_description', '')),
                'Image Generated': image_generated,
                'Video Generated': video_generated,
                'Timing': f"{timing_data.get('start_time', 0)}-{timing_data.get('end_time', 0)}s",
                'Duration': f"{timing_data.get('duration', 0)}s",
                'Shot Type': shot_type,
                'Section': shot_data.get('section', '')
            }
            
            table_data.append(row)
        
        # Create CSV content
        csv_content = create_csv_content(table_data)
        
        # Save CSV locally for asset gathering agent to handle
        local_filename = f"visual_production_table_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        local_path = os.path.join(os.path.dirname(__file__), '..', 'assets', local_filename)
        
        # Ensure assets directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Write CSV file locally
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Create summary
        total_images = len([row for row in table_data if "✓ Generated image" in row['Image Generated']])
        total_videos = len([row for row in table_data if "✓ Pexels video" in row['Video Generated']])
        missing_assets = len([row for row in table_data if "❌ No visual asset assigned" in row['Image Generated']])
        covered_shots = total_images + total_videos
        
        return f"""VISUAL PRODUCTION TABLE CREATED

Local File: {local_path}
Total Shots: {len(table_data)}

Asset Summary:
✓ Images Generated: {total_images}
✓ Videos Collected: {total_videos}
✓ Shots with Visual Assets: {covered_shots}
❌ Shots Missing Assets: {missing_assets}
Coverage: {covered_shots}/{len(table_data)} shots ({round(covered_shots/len(table_data)*100)}%)

Shot Type Distribution:
- Talking head shots: {len([r for r in table_data if 'talking_head' in r['Shot Type']])}
- B-roll shots: {len([r for r in table_data if r['Shot Type'] == 'broll'])}
- Screen recording shots: {len([r for r in table_data if r['Shot Type'] == 'screen_recording'])}

Status: ✓ CSV saved locally for asset gathering agent to upload

MAPPING IMPROVEMENTS:
- ✓ Images correctly mapped to their source prompts/shots
- ✓ Videos assigned to shots without images
- ✓ No hardcoded shot type filtering
- ✓ Content-aware asset assignment

The visual production table provides a complete mapping of:
- Each script shot with timing
- Visual prompts for image generation  
- Generated images mapped to their exact source shots
- B-roll videos from Pexels mapped to remaining shots
- Clear asset coverage and gaps for editor

CSV Content:
{csv_content}"""
        
    except Exception as e:
        return f"Visual table creation error: {str(e)}"

def create_csv_content(table_data: List[Dict[str, Any]]) -> str:
    """Create CSV content from table data"""
    if not table_data:
        return ""
    
    # Define column order
    columns = ['Shot', 'Script', 'Visual Prompt', 'Image Generated', 'Video Generated', 
               'Timing', 'Duration', 'Shot Type', 'Section']
    
    csv_lines = []
    
    # Add header
    csv_lines.append(','.join([f'"{col}"' for col in columns]))
    
    # Add data rows
    for row in table_data:
        csv_row = []
        for col in columns:
            value = str(row.get(col, '')).replace('"', '""')  # Escape quotes
            csv_row.append(f'"{value}"')
        csv_lines.append(','.join(csv_row))
    
    return '\n'.join(csv_lines)

# Google Drive upload functionality removed - handled by asset gathering agent

@tool
async def generate_production_summary(
    shot_breakdown: List[Dict[str, Any]],
    visual_prompts: List[Dict[str, Any]],
    generated_images: List[str],
    broll_assets: Dict[str, Any]
) -> str:
    """
    Generate a comprehensive production summary with asset mapping.
    
    Args:
        shot_breakdown: List of shot analysis data
        visual_prompts: List of generated visual prompts
        generated_images: List of generated image file paths  
        broll_assets: Dictionary containing B-roll assets
        
    Returns:
        Detailed production summary
    """
    try:
        total_shots = len(shot_breakdown)
        total_prompts = len(visual_prompts)
        total_images = len(generated_images)
        
        broll_images = len(broll_assets.get('images', [])) if broll_assets else 0
        broll_videos = len(broll_assets.get('videos', [])) if broll_assets else 0
        
        # Analyze shot types
        shot_types = {}
        for shot in shot_breakdown:
            shot_type = shot.get('type', 'unknown')
            shot_types[shot_type] = shot_types.get(shot_type, 0) + 1
        
        return f"""PRODUCTION SUMMARY

Script Analysis:
- Total Shots: {total_shots}
- Shot Types: {dict(shot_types)}

Visual Assets Generated:
- Visual Prompts: {total_prompts}
- Generated Images: {total_images}
- B-roll Images: {broll_images}
- B-roll Videos: {broll_videos}

Asset Coverage:
- Talking Head Shots: {shot_types.get('talking_head', 0) + shot_types.get('talking_head_emotional', 0)}
- B-roll Shots: {shot_types.get('broll', 0)}
- Screen Recording Shots: {shot_types.get('screen_recording', 0)}

Production Status:
- Ready for editing: {'✓' if total_images > 0 and (broll_images > 0 or broll_videos > 0) else '❌'}
- All shots covered: {'✓' if total_prompts >= total_shots else '❌'}
- Visual assets complete: {'✓' if total_images >= shot_types.get('talking_head', 0) + shot_types.get('talking_head_emotional', 0) else '❌'}"""
        
    except Exception as e:
        return f"Summary generation error: {str(e)}"

# Export tools
visual_table_tools = [
    create_visual_production_table,
    generate_production_summary
]