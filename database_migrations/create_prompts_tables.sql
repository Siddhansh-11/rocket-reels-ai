-- Create scripts table if it doesn't exist
CREATE TABLE IF NOT EXISTS scripts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID REFERENCES articles(id),
    content TEXT NOT NULL,
    style VARCHAR(50),
    template VARCHAR(50),
    platform VARCHAR(50),
    duration INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create prompts table for storing image generation prompts
CREATE TABLE IF NOT EXISTS prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    script_id UUID REFERENCES scripts(id),
    scene_number INTEGER NOT NULL,
    scene_description TEXT NOT NULL,
    prompt TEXT NOT NULL,
    style VARCHAR(50),
    aspect_ratio VARCHAR(10),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create generated_images table for storing generated images
CREATE TABLE IF NOT EXISTS generated_images (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id UUID REFERENCES prompts(id),
    prompt TEXT NOT NULL,
    scene_number INTEGER,
    scene_description TEXT,
    image_url TEXT,
    image_base64 TEXT,
    revised_prompt TEXT,
    model VARCHAR(100),
    style VARCHAR(50),
    aspect_ratio VARCHAR(10),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_scripts_article_id ON scripts(article_id);
CREATE INDEX IF NOT EXISTS idx_prompts_script_id ON prompts(script_id);
CREATE INDEX IF NOT EXISTS idx_prompts_scene_number ON prompts(scene_number);
CREATE INDEX IF NOT EXISTS idx_generated_images_prompt_id ON generated_images(prompt_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_scene_number ON generated_images(scene_number);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_scripts_updated_at BEFORE UPDATE ON scripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_generated_images_updated_at BEFORE UPDATE ON generated_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();