# AI Agent Prompt: Refactor uingest to PostgreSQL & Enhance Metadata

**Objective:**

You are tasked with refactoring the `src/crawl4ai_mcp.py` and relevant utility functions for the `uingest` project. The primary goal is to remove all Supabase Cloud dependencies and replace them with direct PostgreSQL database interactions, utilizing a local Dockerized PostgreSQL instance. This refactoring must implement "Option 2" for metadata handling, which involves storing richer metadata along with crawled content.

**Context - Project `uingest`:**

`uingest` is a fork of `mcp-crawl4ai-rag`. It aims to ingest data from websites, create embeddings via OpenAI, and store results in PostgreSQL with PGVector.

**Core Requirements (Option 2 Metadata Handling):**

1.  **Enhanced Metadata Storage:** The system must store the following additional metadata fields for each content chunk in the `documents` table:
    *   `chunk_index` (INTEGER): The index of the chunk within its original document.
    *   `headers` (TEXT): Extracted headers relevant to the chunk (e.g., "H1 Welcome; H2 Introduction").
    *   `char_count` (INTEGER): Character count of the chunk.
    *   `word_count` (INTEGER): Word count of the chunk.
    *   `crawl_type` (TEXT, NULLABLE): The type of crawl that sourced the content (e.g., "webpage", "sitemap", "text_file"). This might be null if not applicable (e.g., for a single page crawl that doesn't specify type).
    *   `crawl_time` (TEXT): Timestamp or indicator of when the crawl occurred (e.g., ISO format timestamp or the original coroutine name `str(asyncio.current_task().get_coro().__name__)`).

2.  **Database Schema Update:** The `documents` table schema needs to be updated to include these new fields.
3.  **Utility Function Updates (`utils.py`):**
    *   `add_documents_to_pgvector`: Must be modified to accept and insert these new metadata fields.
    *   `search_documents_pgvector`: Must be modified to select and return these new metadata fields along with `url` and `content`.
4.  **Main Application Logic (`src/crawl4ai_mcp.py`):**
    *   Must be refactored to prepare and pass the new metadata to the updated `add_documents_to_pgvector`.
    *   Must correctly call the updated `search_documents_pgvector` and handle the richer results.
    *   All Supabase client usage must be removed.

**Step-by-Step Instructions:**

**Phase 1: File Acquisition & Setup**

1.  **Fetch Original Files:**
    Use the MCP tool `get_file_contents:` to retrieve the following files from the `coleam00/mcp-crawl4ai-rag` repository:
    *   `target_repo_url`: `https://github.com/coleam00/mcp-crawl4ai-rag`
    *   `target_path`: `src/crawl4ai_mcp.py`
        *   Save this content as `original_mcp.py`. This will be the primary file you refactor.
    *   `target_repo_url`: `https://github.com/coleam00/mcp-crawl4ai-rag`
    *   `target_path`: `src/utils.py`
        *   Save this content as `original_utils.py`. This file contains Supabase-specific helper functions and will serve as a partial reference, but you will create a new `utils.py` for `uingest`.

**Phase 2: Create the new `uingest/src/utils.py`**

The `uingest` project requires specific utility functions. You will create a new `utils.py` file containing the following, ensuring it does **not** use Supabase:

1.  **`get_pg_connection()` function:**
    ```python
    import os
    import psycopg2

    def get_pg_connection():
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", 5432),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
    ```

2.  **`create_embeddings_batch()` function (OpenAI v1.x SDK):**
    ```python
    import os
    import openai
    from typing import List

    # Load OpenAI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    # Initialize OpenAI client
    client = openai.OpenAI()

    def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
        response = client.embeddings.create(input=texts, model="text-embedding-ada-002")
        return [item.embedding for item in response.data]
    ```

3.  **NEW `add_documents_to_pgvector()` function:**
    *   **Signature:** `def add_documents_to_pgvector(documents_data: List[Dict[str, Any]]):`
        *   Each dictionary in `documents_data` will contain keys for all fields of the new `documents` table: `url`, `source`, `content`, `chunk_index`, `headers`, `char_count`, `word_count`, `crawl_type`, `crawl_time`.
    *   **Functionality:**
        *   Extract the `content` from each document in `documents_data` to create a list of texts.
        *   Generate embeddings for these texts using `create_embeddings_batch()`.
        *   Prepare a list of tuples, where each tuple contains all values for a row to be inserted into the `documents` table (including the generated embedding and all metadata from the input dictionary).
        *   Use `psycopg2.extras.execute_values` for efficient batch insertion into the `documents` table.
        *   Ensure proper connection handling (acquire from `get_pg_connection()`, use `with conn:`, and close).
    *   **SQL Query inside:** The `INSERT` query should target all columns of the new `documents` table schema (see Phase 3).

4.  **UPDATED `search_documents_pgvector()` function:**
    *   **Signature:** `def search_documents_pgvector(query: str, top_k: int = 5, source_filter: str = None) -> List[Dict[str, Any]]:`
    *   **Functionality:**
        *   Generate an embedding for the `query` using `create_embeddings_batch()`.
        *   Acquire a PostgreSQL connection.
        *   **SQL Query:** Construct a SQL query that:
            *   Selects `url`, `content`, and all the new metadata fields (`chunk_index`, `headers`, `char_count`, `word_count`, `crawl_type`, `crawl_time`).
            *   Filters by `source` if `source_filter` is provided.
            *   Orders by similarity to the `query_embedding` (`<->` operator).
            *   Limits results to `top_k`.
        *   Execute the query and fetch results.
        *   Return a list of dictionaries, where each dictionary represents a retrieved document and includes all selected fields.
        *   Ensure proper connection handling.

**Phase 3: Define the Updated `documents` Table Schema**

Propose the SQL DDL for creating the `documents` table in `crawled_pages.sql`. It should include:
*   `id SERIAL PRIMARY KEY`
*   `url TEXT`
*   `source TEXT`
*   `content TEXT` (this will store the chunk)
*   `embedding vector(1536)`
*   `chunk_index INTEGER`
*   `headers TEXT`
*   `char_count INTEGER`
*   `word_count INTEGER`
*   `crawl_type TEXT`
*   `crawl_time TEXT`
*   Include the pgvector index: `CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`

**Phase 4: Refactor `original_mcp.py` (This will become the new `uingest/src/crawl4ai_mcp.py`)**

Apply the following changes to the content of `original_mcp.py`:

1.  **Remove Supabase Imports and Dependencies:**
    *   Delete `from supabase import Client`.
    *   Remove any other Supabase-specific imports if present.

2.  **Update `Crawl4AIContext` and `crawl4ai_lifespan`:**
    *   Remove `supabase_client: Client` from the `Crawl4AIContext` dataclass.
    *   In `crawl4ai_lifespan`, remove all code related to initializing or yielding `supabase_client`. The context should only contain the `crawler`.

3.  **Refactor `crawl_single_page` tool:**
    *   Remove any retrieval of `supabase_client` from the context.
    *   After crawling and chunking, prepare a list of dictionaries for `add_documents_to_pgvector`. Each dictionary should conform to the structure expected by your new `add_documents_to_pgvector` function in `utils.py`, including:
        *   `url`: The crawled URL.
        *   `source`: Derived (e.g., `urlparse(url).netloc`).
        *   `content`: The text chunk.
        *   `chunk_index`: The index of the chunk.
        *   `headers`, `char_count`, `word_count`: Extracted via `extract_section_info(chunk)`.
        *   `crawl_time`: e.g., `str(asyncio.current_task().get_coro().__name__)` or a proper timestamp.
        *   `crawl_type`: Can be omitted or set to a default like "single_page" if desired (this tool didn't originally set it).
    *   Call `utils.add_documents_to_pgvector(documents_data=your_prepared_list_of_dicts)`.
    *   Update the JSON response string as appropriate (it no longer directly interacts with Supabase for counts if those were Supabase-specific).

4.  **Refactor `smart_crawl_url` tool:**
    *   Remove any retrieval of `supabase_client` from the context.
    *   After crawling various sources (text file, sitemap, webpage) and chunking, prepare the list of dictionaries for `add_documents_to_pgvector` similarly to `crawl_single_page`.
    *   Crucially, ensure `crawl_type` metadata is correctly populated based on the detection logic (e.g., "text_file", "sitemap", "webpage").
    *   The existing `batch_size = 20` logic in this function (which was for Supabase) might need re-evaluation. Your new `utils.add_documents_to_pgvector` should ideally handle batching for embedding creation internally if a very large number of documents are passed at once. For now, you can have `smart_crawl_url` accumulate all document dictionaries and pass them as one list.
    *   Call `utils.add_documents_to_pgvector(documents_data=your_prepared_list_of_dicts)`.
    *   Update the JSON response string.

5.  **Refactor `get_available_sources` tool:**
    *   Remove `supabase_client` usage.
    *   Use `utils.get_pg_connection()` to get a database connection.
    *   Execute the SQL query: `SELECT DISTINCT source FROM documents;`.
    *   Fetch results and format them into the JSON response: `{"success": True, "sources": sorted_list_of_sources, "count": len(sources)}`.
    *   Ensure proper error handling and connection management.

6.  **Refactor `perform_rag_query` tool:**
    *   Remove `supabase_client` usage.
    *   The `filter_metadata` dictionary (`{"source": source}` or `None`) should be used to pass the `source` string directly to `utils.search_documents_pgvector` as the `source_filter` argument.
    *   Call `results = utils.search_documents_pgvector(query=query, top_k=match_count, source_filter=source_value_or_none)`.
    *   The `results` will now be a list of dictionaries (from your updated `utils.search_documents_pgvector`).
    *   Format the `formatted_results` in the JSON response to include all fields returned by `search_documents_pgvector` (url, content, and all new metadata). The "similarity" score might not be directly available unless pgvector's distance is converted to similarity and returned by `search_documents_pgvector`. For now, focus on returning the raw data fields. If similarity is not returned by `search_documents_pgvector`, omit it from the response.

7.  **General Cleanup:**
    *   Ensure all imported utility functions from `utils` are correctly named (e.g., `search_documents_pgvector` not `search_documents_pgvector_pgvector`).
    *   Remove any lingering Supabase-specific comments or logic.
    *   The `main()` function and FastMCP setup should largely remain the same, focusing on environment variables for host/port.

**Phase 5: Deliverables**

Provide the following:
1.  The complete refactored content for the new `uingest/src/crawl4ai_mcp.py` file.
2.  The complete content for the new `uingest/src/utils.py` file.
3.  The recommended SQL DDL for the updated `documents` table (to be used in `crawled_pages.sql`).

**Important Considerations:**

*   **Error Handling:** Maintain robust error handling (`try-except` blocks) in all modified functions.
*   **Async Operations:** Ensure `async/await` is used correctly for database operations if you choose to make the utility functions in `utils.py` async (currently `get_pg_connection` is sync; psycopg2 generally works synchronously, but can be used with async wrappers if needed, though for this exercise, keeping it sync as in the provided snippet for `get_pg_connection` is fine).
*   **Dependencies:** Assume `psycopg2-binary` and `openai` are correctly listed in the project's dependencies (`pyproject.toml`).

If any part of these instructions is unclear, please ask for clarification before proceeding.
