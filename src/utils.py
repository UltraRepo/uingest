"""
Utility functions for the Uingest MCP server.
"""
import os
import json
import openai
import asyncio
from typing import List, Tuple, Dict, Any, Optional
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables from the project root .env file
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path, override=True)

# Initialize OpenAI client
# The OpenAI client will automatically pick up OPENAI_API_KEY and OPENAI_BASE_URL (if set)
# from the environment.
client = openai.OpenAI()

async def get_postgres_client() -> psycopg.AsyncConnection:
    """
    Returns a PostgreSQL client.
    """
    try:
        conn = await psycopg.AsyncConnection.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", 5432),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            row_factory=dict_row
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Creates embeddings for a batch of texts.
    """
    model_name = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")
    response = client.embeddings.create(input=texts, model=model_name)
    return [item.embedding for item in response.data]

async def add_documents_to_postgres(
    client: psycopg.AsyncConnection,
    urls: List[str],
    chunk_numbers: List[int],
    contents: List[str],
    metadatas: List[Dict[str, Any]],
    url_to_full_document: Dict[str, str],
    batch_size: int = 20
):
    """
    Adds documents to PostgreSQL with metadata.
    """
    try:
        embeddings = create_embeddings_batch(contents)
        data = list(zip(urls, chunk_numbers, contents, embeddings, metadatas))

        async with client.cursor() as cur:
            insert_query = """
                INSERT INTO crawled_pages (url, chunk_number, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """
            await cur.executemany(insert_query, data)
        await client.commit()
        print(f"Successfully added {len(urls)} documents to PostgreSQL.")

    except Exception as e:
        print(f"Error adding documents to PostgreSQL: {e}")
        raise

async def search_documents(
    client: psycopg.AsyncConnection,
    query: str,
    match_count: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Searches documents in PostgreSQL based on vector similarity.
    Filters by metadata.source if provided.
    """
    try:
        embedding = create_embeddings_batch([query])[0]

        async with client.cursor(row_factory=dict_row) as cur:
            query_parts = [
                "SELECT url, content, metadata, 1 - (embedding <=> %s) AS similarity",
                "FROM crawled_pages"
            ]
            # Parameters for the query. Start with the query embedding.
            params: List[Any] = [embedding]

            # Add metadata filter if provided and 'source' key exists and has a value
            if filter_metadata and "source" in filter_metadata and filter_metadata["source"] is not None:
                query_parts.append("WHERE metadata->>'source' = %s")
                params.append(filter_metadata["source"])
            
            # Add ordering by similarity (the first %s refers to the first parameter: embedding)
            query_parts.append("ORDER BY embedding <=> %s")
            # Add limit
            query_parts.append("LIMIT %s")
            params.append(match_count)

            final_query_str = " ".join(query_parts)
            
            await cur.execute(final_query_str, tuple(params))

            results = await cur.fetchall()
            return results

    except Exception as e:
        print(f"Error searching documents in PostgreSQL: {e}")
        raise