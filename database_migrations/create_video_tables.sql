-- Video Generation Tables for Rocket Reels AI
-- This migration adds tables to support video generation workflow

-- Table to store video prompts generated for each script
CREATE TABLE IF NOT EXISTS video_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    from_image_index INTEGER,
    to_image_index INTEGER,
    motion_description TEXT NOT NULL,
    transition_type VARCHAR(50) NOT NULL DEFAULT 'crossfade',
    duration DECIMAL(4,2) NOT NULL DEFAULT 3.0,
    effects JSONB DEFAULT '[]'::jsonb,
    mood VARCHAR(50),
    camera_movement JSONB DEFAULT '{}'::jsonb,
    prompt_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table to store generated video segments
CREATE TABLE IF NOT EXISTS video_segments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_prompt_id UUID REFERENCES video_prompts(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    duration DECIMAL(4,2) NOT NULL,
    resolution VARCHAR(20), -- e.g., "1920x1080"
    fps INTEGER DEFAULT 30,
    format VARCHAR(10) DEFAULT 'mp4',
    generation_method VARCHAR(50), -- 'gemini', 'replicate', 'opencv', etc.
    generation_cost DECIMAL(10,4) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table to store final combined videos
CREATE TABLE IF NOT EXISTS generated_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    total_duration DECIMAL(6,2) NOT NULL,
    resolution VARCHAR(20),
    fps INTEGER DEFAULT 30,
    format VARCHAR(10) DEFAULT 'mp4',
    segment_count INTEGER NOT NULL DEFAULT 0,
    generation_method VARCHAR(50),
    total_cost DECIMAL(10,4) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table to track video generation jobs and their progress
CREATE TABLE IF NOT EXISTS video_generation_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'prompt_generation', 'video_generation', 'combination'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0, -- 0-100
    current_step VARCHAR(100),
    total_steps INTEGER DEFAULT 1,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_video_prompts_article_id ON video_prompts(article_id);
CREATE INDEX IF NOT EXISTS idx_video_prompts_script_id ON video_prompts(script_id);
CREATE INDEX IF NOT EXISTS idx_video_prompts_segment_index ON video_prompts(segment_index);

CREATE INDEX IF NOT EXISTS idx_video_segments_article_id ON video_segments(article_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_video_prompt_id ON video_segments(video_prompt_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_status ON video_segments(status);

CREATE INDEX IF NOT EXISTS idx_generated_videos_article_id ON generated_videos(article_id);
CREATE INDEX IF NOT EXISTS idx_generated_videos_script_id ON generated_videos(script_id);
CREATE INDEX IF NOT EXISTS idx_generated_videos_status ON generated_videos(status);

CREATE INDEX IF NOT EXISTS idx_video_generation_jobs_article_id ON video_generation_jobs(article_id);
CREATE INDEX IF NOT EXISTS idx_video_generation_jobs_status ON video_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_generation_jobs_job_type ON video_generation_jobs(job_type);

-- Update triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to all video tables
DO $$
BEGIN
    -- video_prompts table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_video_prompts_updated_at') THEN
        CREATE TRIGGER update_video_prompts_updated_at 
            BEFORE UPDATE ON video_prompts 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- video_segments table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_video_segments_updated_at') THEN
        CREATE TRIGGER update_video_segments_updated_at 
            BEFORE UPDATE ON video_segments 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- generated_videos table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_generated_videos_updated_at') THEN
        CREATE TRIGGER update_generated_videos_updated_at 
            BEFORE UPDATE ON generated_videos 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- video_generation_jobs table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_video_generation_jobs_updated_at') THEN
        CREATE TRIGGER update_video_generation_jobs_updated_at 
            BEFORE UPDATE ON video_generation_jobs 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Views for easier querying

-- View to get complete video generation status for an article
CREATE OR REPLACE VIEW video_generation_status AS
SELECT 
    a.id as article_id,
    a.title,
    s.id as script_id,
    s.platform,
    COUNT(vp.id) as prompt_count,
    COUNT(vs.id) as segment_count,
    COUNT(gv.id) as video_count,
    COALESCE(SUM(vs.generation_cost), 0) + COALESCE(SUM(gv.total_cost), 0) as total_cost,
    MAX(gv.created_at) as last_video_created,
    CASE 
        WHEN COUNT(gv.id) > 0 THEN 'completed'
        WHEN COUNT(vs.id) > 0 THEN 'generating'
        WHEN COUNT(vp.id) > 0 THEN 'prompted'
        ELSE 'pending'
    END as status
FROM articles a
LEFT JOIN scripts s ON a.id = s.article_id
LEFT JOIN video_prompts vp ON s.id = vp.script_id
LEFT JOIN video_segments vs ON vp.id = vs.video_prompt_id
LEFT JOIN generated_videos gv ON s.id = gv.script_id
GROUP BY a.id, a.title, s.id, s.platform;

-- View to get video segments with their prompts
CREATE OR REPLACE VIEW video_segments_with_prompts AS
SELECT 
    vs.*,
    vp.motion_description,
    vp.transition_type,
    vp.effects,
    vp.mood,
    vp.camera_movement,
    vp.segment_index
FROM video_segments vs
JOIN video_prompts vp ON vs.video_prompt_id = vp.id;

-- Comments for documentation
COMMENT ON TABLE video_prompts IS 'Stores AI-generated prompts for video creation from image sequences';
COMMENT ON TABLE video_segments IS 'Stores individual video segments created from prompts';
COMMENT ON TABLE generated_videos IS 'Stores final combined videos ready for publishing';
COMMENT ON TABLE video_generation_jobs IS 'Tracks the progress of video generation workflows';

COMMENT ON COLUMN video_prompts.motion_description IS 'Detailed description of how objects/camera should move';
COMMENT ON COLUMN video_prompts.transition_type IS 'Type of transition between images (crossfade, swipe, zoom, etc.)';
COMMENT ON COLUMN video_prompts.camera_movement IS 'JSON object describing camera movement parameters';
COMMENT ON COLUMN video_segments.generation_method IS 'Which AI service or method was used to generate this segment';
COMMENT ON COLUMN generated_videos.segment_count IS 'Number of segments combined to create this video';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;