"""
Video Generation Agent for Rocket Reels AI

This agent creates videos from static images using various AI video generation services.
It uses motion prompts to create smooth transitions and natural movement between frames.
"""

import json
import os
import base64
from typing import Dict, List, TypedDict, Optional
import requests
from datetime import datetime
import time
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import cv2
import numpy as np
from gdrive_storage import initialize_gdrive_storage, save_video_to_gdrive, extract_topic_from_prompt

class VideoGenerationState(TypedDict):
    generated_images: List[Dict]
    video_prompts: List[Dict]
    script_content: str
    generated_videos: Optional[List[Dict]]
    final_video_path: Optional[str]
    error: Optional[str]
    cost: float

class VideoGenerationAgent:
    def __init__(self):
        # Try to get Gemini API key
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.use_gemini = True
        else:
            self.use_gemini = False
            print("⚠️  GEMINI_API_KEY not found - using alternative video generation methods")
        
        # Alternative: Replicate API for Stable Video Diffusion
        self.replicate_api_key = os.getenv('REPLICATE_API_TOKEN')
        
        # Paths
        # Use relative paths for cross-platform compatibility
        self.image_dir = Path("generated_images")
        self.video_dir = Path("generated_videos")
        self.video_dir.mkdir(parents=True, exist_ok=True)  # <-- add parents=True
        
        # Initialize Google Drive storage
        self.gdrive_storage = None
        try:
            self.gdrive_storage = initialize_gdrive_storage()
            print("✅ Google Drive storage initialized for video generation")
        except Exception as e:
            print(f"⚠️ Google Drive storage not available: {str(e)}")
    def generate_videos(self, state: VideoGenerationState) -> VideoGenerationState:
        """Generate videos from images using AI or fallback methods"""
        try:
            print("\n🎥 Starting Video Generation...")
            
            if not state.get('generated_images'):
                state['error'] = "No generated images found"
                return state
            
            if not state.get('video_prompts'):
                state['error'] = "No video prompts found"
                return state
            
            # Prepare image paths
            image_paths = self._prepare_image_paths(state['generated_images'])
            if not image_paths:
                state['error'] = "Could not find image files"
                return state
            
            print(f"\n📸 Found {len(image_paths)} images to process")
            
            # Generate video segments
            video_segments = []
            
            if self.use_gemini:
                print("\n🤖 Using Gemini AI for video generation...")
                video_segments = self._generate_with_gemini(image_paths, state['video_prompts'])
            elif self.replicate_api_key:
                print("\n🎬 Using Replicate (Stable Video Diffusion) for video generation...")
                video_segments = self._generate_with_replicate(image_paths, state['video_prompts'])
            else:
                print("\n🎞️ Using OpenCV for basic video generation...")
                video_segments = self._generate_with_opencv(image_paths, state['video_prompts'])
            
            if video_segments:
                # Combine segments into final video
                final_video = self._combine_segments(video_segments)
                
                if final_video:
                    state['generated_videos'] = video_segments
                    state['final_video_path'] = final_video
                    print(f"\n✅ Video generated successfully: {final_video}")
                    
                    # Upload to Google Drive with topic organization
                    if self.gdrive_storage and final_video:
                        try:
                            # Extract topic from script content or use timestamp
                            topic_name = extract_topic_from_prompt(state.get('script_content', '')) if state.get('script_content') else f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            
                            gdrive_file_id = save_video_to_gdrive(final_video, self.gdrive_storage, topic_name)
                            state['gdrive_file_id'] = gdrive_file_id
                            state['gdrive_topic_folder'] = topic_name
                            print(f"☁️ Video uploaded to Google Drive in topic folder: {topic_name}")
                        except Exception as e:
                            print(f"⚠️ Google Drive upload failed: {str(e)}")
                            state['gdrive_error'] = str(e)
                else:
                    state['error'] = "Failed to combine video segments"
            else:
                state['error'] = "No video segments were generated"
            
            return state
            
        except Exception as e:
            state['error'] = f"Video generation failed: {str(e)}"
            print(f"\n❌ Error: {state['error']}")
            return state
    
    def _prepare_image_paths(self, generated_images: List[Dict]) -> List[str]:
        """Get full paths for generated images"""
        paths = []
        
        for img in generated_images:
            filename = img.get('filename', '')
            if filename:
                full_path = self.image_dir / filename
                if full_path.exists():
                    paths.append(str(full_path))
                else:
                    # Try without directory
                    if Path(filename).exists():
                        paths.append(filename)
        
        return paths
    
    def _generate_with_gemini(self, image_paths: List[str], video_prompts: List[Dict]) -> List[Dict]:
        """Generate video using Google's Gemini API (when available)"""
        # Note: As of now, Gemini doesn't have direct video generation
        # This is a placeholder for when the API becomes available
        # For now, we'll use Gemini's image understanding to enhance our fallback method
        
        print("ℹ️  Gemini video generation API not yet available. Using enhanced OpenCV method.")
        return self._generate_with_opencv(image_paths, video_prompts, use_ai_enhancement=True)
    
    def _generate_with_replicate(self, image_paths: List[str], video_prompts: List[Dict]) -> List[Dict]:
        """Generate video using Replicate's Stable Video Diffusion"""
        import replicate
        
        segments = []
        
        for i, prompt in enumerate(video_prompts):
            try:
                from_idx = prompt.get('from_image', 1) - 1 if prompt.get('from_image') else 0
                
                if from_idx < len(image_paths):
                    print(f"\n🎬 Generating segment {i+1}/{len(video_prompts)}...")
                    
                    # Use Stable Video Diffusion
                    output = replicate.run(
                        "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                        input={
                            "input_image": open(image_paths[from_idx], "rb"),
                            "video_length": "14_frames",  # or "25_frames"
                            "sizing_strategy": "maintain_aspect_ratio",
                            "frames_per_second": 7,
                            "motion_bucket_id": 127,  # Controls motion amount
                            "cond_aug": 0.02
                        }
                    )
                    
                    # Save the output
                    segment_path = self.video_dir / f"segment_{i+1}.mp4"
                    
                    # Download the video
                    response = requests.get(output)
                    with open(segment_path, 'wb') as f:
                        f.write(response.content)
                    
                    segments.append({
                        "path": str(segment_path),
                        "duration": prompt.get('duration', 3.0),
                        "prompt": prompt
                    })
                    
                    print(f"✅ Segment {i+1} generated")
                    
            except Exception as e:
                print(f"❌ Failed to generate segment {i+1}: {str(e)}")
                continue
        
        return segments
    
    def _generate_with_opencv(self, image_paths: List[str], video_prompts: List[Dict], 
                            use_ai_enhancement: bool = False) -> List[Dict]:
        """Generate video using OpenCV with Ken Burns effect and transitions"""
        segments = []
        
        for i, prompt in enumerate(video_prompts):
            try:
                from_idx = prompt.get('from_image', 1) - 1 if prompt.get('from_image') else None
                to_idx = prompt.get('to_image', 1) - 1 if prompt.get('to_image') else None
                
                segment_path = self.video_dir / f"segment_{i+1}.mp4"
                
                # Get motion parameters
                motion = prompt.get('camera_movement', {})
                transition = prompt.get('transition_type', 'crossfade')
                duration = prompt.get('duration', 3.0)
                
                # Create segment based on type
                if from_idx is None and to_idx is not None:
                    # Intro segment
                    self._create_intro_segment(image_paths[to_idx], segment_path, duration, motion)
                elif from_idx is not None and to_idx is None:
                    # Outro segment
                    self._create_outro_segment(image_paths[from_idx], segment_path, duration, motion)
                elif from_idx is not None and to_idx is not None:
                    # Transition segment
                    self._create_transition_segment(
                        image_paths[from_idx], 
                        image_paths[to_idx], 
                        segment_path, 
                        duration, 
                        transition, 
                        motion
                    )
                
                if segment_path.exists():
                    segments.append({
                        "path": str(segment_path),
                        "duration": duration,
                        "prompt": prompt
                    })
                    print(f"✅ Segment {i+1} created: {prompt.get('motion_description', 'Basic transition')}")
                
            except Exception as e:
                print(f"❌ Failed to create segment {i+1}: {str(e)}")
                continue
        
        return segments
    
    def _create_intro_segment(self, image_path: str, output_path: Path, duration: float, motion: Dict):
        """Create intro segment with fade in and motion"""
        img = cv2.imread(image_path)
        height, width = img.shape[:2]
        
        # Video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames = int(duration * fps)
        
        for frame_idx in range(frames):
            progress = frame_idx / frames
            
            # Apply zoom
            zoom = 1.0 + (motion.get('zoom', 1.1) - 1.0) * progress
            zoomed = self._apply_zoom(img, zoom)
            
            # Apply fade in
            alpha = progress
            faded = (zoomed * alpha).astype(np.uint8)
            
            out.write(faded)
        
        out.release()
    
    def _create_outro_segment(self, image_path: str, output_path: Path, duration: float, motion: Dict):
        """Create outro segment with fade out and motion"""
        img = cv2.imread(image_path)
        height, width = img.shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames = int(duration * fps)
        
        for frame_idx in range(frames):
            progress = frame_idx / frames
            
            # Apply zoom out
            zoom = motion.get('zoom', 0.9) + (1.0 - motion.get('zoom', 0.9)) * progress
            zoomed = self._apply_zoom(img, zoom)
            
            # Apply fade out
            alpha = 1.0 - progress
            faded = (zoomed * alpha).astype(np.uint8)
            
            out.write(faded)
        
        out.release()
    
    def _create_transition_segment(self, from_path: str, to_path: str, output_path: Path, 
                                 duration: float, transition: str, motion: Dict):
        """Create transition between two images"""
        img1 = cv2.imread(from_path)
        img2 = cv2.imread(to_path)
        
        # Ensure same dimensions
        height = max(img1.shape[0], img2.shape[0])
        width = max(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (width, height))
        img2 = cv2.resize(img2, (width, height))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames = int(duration * fps)
        
        for frame_idx in range(frames):
            progress = frame_idx / frames
            
            # Apply Ken Burns effect to both images
            if motion.get('type') == 'ken_burns':
                zoom1 = 1.0 + 0.15 * progress  # Zoom on first image
                zoom2 = 1.15 - 0.15 * progress  # Reverse zoom on second
                img1_frame = self._apply_zoom(img1, zoom1)
                img2_frame = self._apply_zoom(img2, zoom2)
            else:
                img1_frame = img1
                img2_frame = img2
            
            # Apply transition
            if transition == 'crossfade':
                frame = cv2.addWeighted(img1_frame, 1 - progress, img2_frame, progress, 0)
            elif transition == 'swipe_left':
                split = int(width * progress)
                frame = np.hstack([img2_frame[:, :split], img1_frame[:, split:]])
            elif transition == 'zoom_transition':
                # Zoom out from first, zoom in to second
                if progress < 0.5:
                    zoom = 1.0 + progress
                    frame = self._apply_zoom(img1_frame, zoom)
                else:
                    zoom = 2.0 - progress
                    frame = self._apply_zoom(img2_frame, zoom)
            else:
                # Default crossfade
                frame = cv2.addWeighted(img1_frame, 1 - progress, img2_frame, progress, 0)
            
            out.write(frame)
        
        out.release()
    
    def _apply_zoom(self, img: np.ndarray, zoom_factor: float) -> np.ndarray:
        """Apply zoom to image maintaining center"""
        height, width = img.shape[:2]
        
        # Calculate new dimensions
        new_height = int(height / zoom_factor)
        new_width = int(width / zoom_factor)
        
        # Calculate crop area
        y1 = (height - new_height) // 2
        x1 = (width - new_width) // 2
        y2 = y1 + new_height
        x2 = x1 + new_width
        
        # Crop and resize
        cropped = img[y1:y2, x1:x2]
        zoomed = cv2.resize(cropped, (width, height))
        
        return zoomed
    
    def _combine_segments(self, segments: List[Dict]) -> Optional[str]:
        """Combine video segments into final video"""
        if not segments:
            return None
        
        try:
            # Create concat file
            concat_file = self.video_dir / "concat.txt"
            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{segment['path']}'\n")
            
            # Output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.video_dir / f"rocket_reel_{timestamp}.mp4"
            
            # Use ffmpeg to concatenate (if available)
            import subprocess
            
            try:
                cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                    '-c', 'copy', '-y', str(output_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Clean up
                concat_file.unlink()
                
                return str(output_path)
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: Use OpenCV to combine
                print("⚠️  ffmpeg not found, using OpenCV to combine segments")
                return self._combine_with_opencv(segments, output_path)
            
        except Exception as e:
            print(f"❌ Failed to combine segments: {str(e)}")
            return None
    
    def _combine_with_opencv(self, segments: List[Dict], output_path: Path) -> Optional[str]:
        """Combine segments using OpenCV"""
        try:
            # Read first segment to get properties
            first_cap = cv2.VideoCapture(segments[0]['path'])
            fps = int(first_cap.get(cv2.CAP_PROP_FPS))
            width = int(first_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(first_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            first_cap.release()
            
            # Create output video
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            # Write all segments
            for segment in segments:
                cap = cv2.VideoCapture(segment['path'])
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                cap.release()
            
            out.release()
            return str(output_path)
            
        except Exception as e:
            print(f"❌ OpenCV combine failed: {str(e)}")
            return None

def video_generation_node(state: VideoGenerationState) -> VideoGenerationState:
    """Node function for LangGraph integration"""
    agent = VideoGenerationAgent()
    return agent.generate_videos(state)

if __name__ == "__main__":
    # Test the agent
    test_state = VideoGenerationState(
        generated_images=[
            {"filename": "test1.jpg"},
            {"filename": "test2.jpg"}
        ],
        video_prompts=[
            {
                "segment_index": 0,
                "from_image": None,
                "to_image": 1,
                "motion_description": "Fade in with zoom",
                "transition_type": "fade_in",
                "duration": 2.0,
                "camera_movement": {"type": "zoom_in", "zoom": 1.1}
            },
            {
                "segment_index": 1,
                "from_image": 1,
                "to_image": 2,
                "motion_description": "Ken Burns effect",
                "transition_type": "crossfade",
                "duration": 3.0,
                "camera_movement": {"type": "ken_burns"}
            }
        ],
        script_content="Test script",
        generated_videos=None,
        final_video_path=None,
        error=None,
        cost=0.0
    )
    
    agent = VideoGenerationAgent()
    result = agent.generate_videos(test_state)
    
    if result['final_video_path']:
        print(f"\n✅ Video generated: {result['final_video_path']}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")