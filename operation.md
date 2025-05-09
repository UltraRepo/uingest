# Uingest App Operation

Uingest is a web crawling and data ingestion application that extracts content from websites and stores it in a PostgreSQL database. It uses the OpenAI API to generate embeddings for the extracted content, which enables semantic search and retrieval.

## Core Components

The Uingest app consists of two main components:

1.  `uingest_mcp.py`: This file implements the MCP (Model Context Protocol) server, which provides tools for crawling websites and storing the extracted content in the database.
2.  `utils.py`: This file contains utility functions for interacting with the PostgreSQL database and the OpenAI API.

## Functionality

The Uingest app provides the following functionality:

*   Crawling web pages
*   Extracting content from web pages
*   Generating embeddings for the extracted content
*   Storing the extracted content and embeddings in a PostgreSQL database
*   Searching for documents based on semantic similarity

## File Details

### `uingest_mcp.py`

This file implements the MCP server, which provides tools for crawling websites. The key functions in this file are:

*   `crawl_single_page(ctx: Context, url: str) -> str`: This function crawls a single web page and stores its content in the database.
*   `smart_crawl_url(ctx: Context, url: str, max_depth: int = 3, max_concurrent: int = 10, chunk_size: int = 5000) -> str`: This function intelligently crawls a URL based on its type (e.g., sitemap, text file, or regular web page) and stores the extracted content in the database.
*   `get_available_sources(ctx: Context) -> str`: This function retrieves a list of available sources from the database.
*   `perform_rag_query(ctx: Context, query: str, source: str = None, match_count: int = 5) -> str`: This function performs a RAG (Retrieval Augmented Generation) query on the stored content.

### `utils.py`

This file contains utility functions for interacting with the PostgreSQL database and the OpenAI API. The key functions in this file are:

*   `get_postgres_client()`: This function establishes an asynchronous connection to the PostgreSQL database.
*   `add_documents_to_postgres(client: psycopg.AsyncConnection, urls: List[str], chunk_numbers: List[int], contents: List[str], metadatas: List[Dict[str, Any]], url_to_full_document: Dict[str, str], batch_size: int = 20)`: This function adds documents to the PostgreSQL database. It creates embeddings for the `contents` in a single API call and uses `executemany` for efficient database insertion. The `url_to_full_document` parameter is available but not currently used by the calling functions in `uingest_mcp.py`. The `batch_size` parameter in this function's definition is also not explicitly set by callers in `uingest_mcp.py` and pertains to database operation, not OpenAI call batching.
*   `search_documents(client: psycopg.AsyncConnection, query: str, match_count: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`: This function searches for documents in the PostgreSQL database based on vector similarity.
*   `create_embeddings_batch(texts: List[str]) -> List[List[float]]`: This function generates embeddings for a batch of text using the OpenAI API.

## Data Flow

The data flow in the Uingest app is as follows:

1.  The user provides a URL to crawl.
2.  The `uingest_mcp.py` file uses the `smart_crawl_url` function to crawl the URL and extract the content.
3.  The extracted content is chunked into smaller pieces using `smart_chunk_markdown`.
4.  For each batch of documents processed by `smart_crawl_url` (or for a single page in `crawl_single_page`), the `add_documents_to_postgres` function in `utils.py` is called.
5.  Inside `add_documents_to_postgres`, the `create_embeddings_batch` function generates embeddings for all chunks of content in that batch via a single OpenAI API call.
6.  Then, `add_documents_to_postgres` stores the content, embeddings, and metadata in the PostgreSQL `crawled_pages` table using `executemany`.
7.  The user provides a search query to `perform_rag_query`.
8.  The `search_documents` function in `utils.py` is called. It first generates an embedding for the search query using `create_embeddings_batch`.
9.  Then, `search_documents` queries the `crawled_pages` table in PostgreSQL for documents that are semantically similar to the search query embedding.
10. The search results are returned to the user.
