-- Enable pgvector extension (run this once)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the crawled_pages table
CREATE TABLE IF NOT EXISTS crawled_pages (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    chunk_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(url, chunk_number)
);

-- Index for faster vector similarity search
-- The 'lists' parameter for ivfflat might need tuning based on dataset size.
-- See README Performance Tuning section.
CREATE INDEX IF NOT EXISTS idx_crawled_pages_embedding ON crawled_pages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for filtering by source in metadata (used by get_available_sources and search_documents)
CREATE INDEX IF NOT EXISTS idx_crawled_pages_metadata_source ON crawled_pages ((metadata->>'source'));

-- General GIN index for metadata, useful for other queries on metadata
CREATE INDEX IF NOT EXISTS idx_crawled_pages_metadata_gin ON crawled_pages USING gin (metadata);

-- Optional: Function to search for documentation chunks.
-- If you use this, src/utils.py (search_documents) will need to be updated to call this function.
/*
CREATE OR REPLACE FUNCTION match_crawled_pages (
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (
  id BIGINT,
  url TEXT,
  chunk_number INTEGER,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    cp.id,
    cp.url,
    cp.chunk_number,
    cp.content,
    cp.metadata,
    1 - (cp.embedding <=> query_embedding) AS similarity
  FROM crawled_pages AS cp
  WHERE cp.metadata @> filter -- This allows filtering by any key-value pairs in the filter JSONB
  ORDER BY cp.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
*/

-- Optional: Row Level Security (RLS)
-- Evaluate if RLS is needed for your specific deployment and security requirements.
/*
ALTER TABLE crawled_pages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access"
  ON crawled_pages
  FOR SELECT
  TO public
  USING (true);
*/
