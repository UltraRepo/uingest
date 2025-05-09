# Uingest: UltraRepo Ingestor

A fork of Crawl4AI RAG MCP server with PostgreSQL + PGVector support.

Uingest ingests data from websites, sitemaps, or GitHub repos, creates embeddings using OpenAI, and stores results in PostgreSQL with PGVector. This enables powerful Retrieval-Augmented Generation (RAG) workflows through the Model Context Protocol (MCP).

## 🚀 Features

- **Smart URL Detection**: Auto-detects webpage, sitemap, or file list.
- **Recursive Crawling**: Full site ingestion support.
- **Parallel Processing**: Fast concurrent downloads and parsing.
- **Chunking Strategy**: Splits by headings and size.
- **Embeddings via OpenAI**: Creates vector embeddings using `text-embedding-ada-002`.
- **Vector Search with PGVector**: Semantic search over ingested content.
- **MCP Server**: SSE-based protocol support for integration with tools.

---

## 🧱 Setup

### 1. Clone the repository and install dependencies

```bash
git clone <repository_url>
cd uingest
python3 -m venv .venv
source .venv/bin/activate
# This project uses uv for dependency management. pyproject.toml is the primary source of dependencies.
# Install dependencies from pyproject.toml and update uv.lock:
uv pip install -p .
# Or, if uv.lock is already up-to-date and you just want to sync your environment:
# uv pip sync
```
This project relies on several key libraries managed through `pyproject.toml`:
- **FastMCP**: For the Model Context Protocol server functionality. Ensure `fastmcp` is a dependency in `pyproject.toml` (add with `uv add fastmcp` if missing). The correct import in `src/uingest_mcp.py` is `from fastmcp import FastMCP, Context`.
- **Crawl4AI**: Provides the core web crawling capabilities (e.g., `AsyncWebCrawler` from the `uingest` module). This should be listed as `crawl4ai` in `pyproject.toml`.

### 2. Create a `.env` file and set environment variables

Create a `.env` file by copying `.env.example` (if it exists, otherwise create it based on the template below) and set the environment variables.
A `.env.example` would typically include:
```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
# OPENAI_ORG_ID=your_openai_org_id_if_applicable

# PostgreSQL Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=uingest
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password_here

# MCP Server Configuration
HOST=0.0.0.0
PORT=8051
```

Make sure to fill in your actual `OPENAI_API_KEY` and PostgreSQL credentials in your `.env` file.

```bash
cp .env.example .env # If .env.example exists
# Or create .env manually and add the variables
nano .env
```

### 3. Database: PostgreSQL with PGVector

Use the following SQL to initialize your database (see `crawled_pages.sql` for the full schema, including other indexes and options):

```sql
CREATE EXTENSION IF NOT EXISTS vector;

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

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_crawled_pages_embedding ON crawled_pages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for filtering by source in metadata
CREATE INDEX IF NOT EXISTS idx_crawled_pages_metadata_source ON crawled_pages ((metadata->>'source'));
```
(Note: The `WITH (lists = 100)` parameter in the IVFFlat index might need tuning based on dataset size for optimal performance. See the Performance Tuning section below and the comments in `crawled_pages.sql`.)

### 4. Run the application

```bash
python src/uingest_mcp.py
```

---

## 🔌 MCP Integration

For SSE transport:

```json
{
  "mcpServers": {
    "uingest": {
      "transport": "sse",
      "url": "http://localhost:8051/sse"
    }
  }
}
```

For stdio config:

```json
{
  "mcpServers": {
    "uingest": {
      "command": "python",
      "args": ["src/uingest_mcp.py"],
      "env": {
        "TRANSPORT": "stdio",
        "OPENAI_API_KEY": "your_key",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "uingest",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres"
      }
    }
  }
}
```

---

## 📜 License

MIT License

---

## 🙌 Acknowledgements

- Based on [Crawl4AI](https://github.com/coleam00/mcp-crawl4ai-rag)
- MCP protocol by [Archon](https://github.com/coleam00/archon)

## ⚡ Performance Tuning & Optimization

Optimizing `uingest` involves tuning several aspects of the crawling, embedding, and database storage process. Here are key areas to consider:

### 1. PostgreSQL PGVector Indexing

The efficiency of vector similarity searches heavily depends on the `ivfflat` index configuration, specifically the `lists` parameter.

- **`lists` parameter**: This determines the number of IVF lists. A higher number can lead to more accurate but slower searches, while a lower number can be faster but less accurate.
- **General Guidance**:
    - For up to 1 million rows, a good starting point for `lists` is `number_of_rows / 1000`.
    - For more than 1 million rows, consider `sqrt(number_of_rows)`.
    - The default `WITH (lists = 100)` in `crawled_pages.sql` is a sensible default for smaller datasets.
- **Tuning**: You may need to experiment to find the optimal value based on your specific dataset size and performance requirements.
- **Re-indexing**: If you change the `lists` parameter after data has been ingested, you will need to re-index:
  ```sql
  DROP INDEX IF EXISTS idx_crawled_pages_embedding;
  CREATE INDEX idx_crawled_pages_embedding ON crawled_pages USING ivfflat (embedding vector_cosine_ops) WITH (lists = new_value);
  ```
- **Resources**:
    - PGVector Indexing Guide: [https://github.com/pgvector/pgvector#indexing](https://github.com/pgvector/pgvector#indexing)

### 2. Content Chunking Strategy

The `smart_chunk_markdown` function, used by tools like `smart_crawl_url`, splits crawled content before embedding. The `chunk_size` parameter (defaulting to 5000 characters in the `smart_crawl_url` tool in `src/uingest_mcp.py`) is critical.

- **Impact**:
    - **Smaller chunks**: Can provide more targeted and specific context for RAG, potentially improving relevance. However, this leads to more chunks per document, increasing the number of OpenAI API calls for embeddings and more rows in your database.
    - **Larger chunks**: Reduce API calls and database rows, but may dilute the specificity of the retrieved context.
- **Tuning**: Adjust the `chunk_size` parameter when calling the `smart_crawl_url` MCP tool based on your content characteristics and desired RAG performance.
- **Note**: The `smart_crawl_url` tool in `src/uingest_mcp.py` has a `chunk_size` parameter that defaults to 5000. Ensure your calls to this tool use a `chunk_size` that suits your needs.

### 3. Concurrent Crawling

The `smart_crawl_url` tool accepts a `max_concurrent` parameter (default 10) to control how many browser sessions run in parallel.

- **Impact**: Higher concurrency can speed up crawling significantly, especially for sitemaps or sites with many internal links. However, it also consumes more system resources (CPU, memory, network bandwidth).
- **Tuning**: Monitor your system load while crawling. If you experience slowdowns or errors, reduce `max_concurrent`. If you have ample resources, you might be able to increase it.

### 4. OpenAI Embedding Process

- **Batching for Large Ingestions**: The `add_documents_to_postgres` function in `src/utils.py` creates embeddings for all provided document contents in a single call to OpenAI's API via `create_embeddings_batch`. For very large individual ingestion jobs (many documents passed at once to `add_documents_to_postgres`), this could hit OpenAI API rate limits or payload size limits.
    - **Recommendation**: For very large-scale initial ingestions (e.g., if directly calling `add_documents_to_postgres` with a huge list of documents outside the `smart_crawl_url` tool's own processing flow), consider modifying your calling code to batch the calls to `add_documents_to_postgres` itself, or modify `add_documents_to_postgres` to internally loop and call `create_embeddings_batch` in smaller batches.
- **`smart_crawl_url` Batching Note**: The `smart_crawl_url` tool in `src/uingest_mcp.py` includes a `batch_size = 20` variable when preparing data for `add_documents_to_postgres`. This `batch_size` in `smart_crawl_url` refers to how many documents are grouped before being passed to `add_documents_to_postgres`. The `add_documents_to_postgres` function itself has a `batch_size` parameter in its definition (defaulting to 20) which is *not* currently used by `smart_crawl_url` when calling it. The `add_documents_to_postgres` function itself uses `cursor.executemany` for database insertion, which is efficient, but the call to `create_embeddings_batch` within it processes all contents in one go.
- **Environment Variables**: Ensure `OPENAI_API_KEY` is correctly set in your `.env` file. If you are part of multiple OpenAI organizations, you might also need to set `OPENAI_ORG_ID`.

### 5. System & Docker Resources

- **Allocate Sufficient Resources**: When running `uingest` via Docker, especially during intensive crawling or large data ingestions, ensure your Docker daemon has access to adequate CPU and memory. Resource limitations can lead to slow performance or failed crawls.
- **Package Management**: This project uses `uv` for dependency management, as indicated by the `pyproject.toml` and `uv.lock` files. If you modify dependencies in `pyproject.toml` (e.g., using `uv add <package>` or `uv remove <package>`), you may need to regenerate or update the lock file using `uv pip compile pyproject.toml -o uv.lock` or simply rely on `uv pip install -p .` to handle it. To install dependencies strictly from the lockfile, use `uv pip sync`.

### Package the project in a ZIP: 

Zip file creation for MacOS without .ds files:
```bash
7z a -tzip ../ingest.zip * -xr!'__MACOSX' -xr!'.DS_Store'
```

---

## 🚀 Detailed Startup and Troubleshooting Walkthrough (Lessons Learned)

This section details the practical steps taken to get the server running, including common issues and their resolutions. This can be helpful if you encounter similar problems.

**1. Initial Setup & Virtual Environment:**

*   Clone the repository: `git clone <repository_url> && cd uingest`
*   Create a Python virtual environment (requires Python >=3.12):
    ```bash
    python3 -m venv .venv
    ```
*   Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
    *(Your terminal prompt should now show `(.venv)`)*

**2. Installing `uv` (Python Package Manager):**

*   If `uv` is not installed, you might get `zsh: command not found: uv`.
*   Install `uv` (official method for macOS/Linux):
    ```bash
    curl -Ls https://astral.sh/uv/install.sh | sh
    ```
*   After installation, `uv` might be in `$HOME/.local/bin`. Add this to your PATH for the current session (or add it to your shell profile like `.zshrc` or `.bashrc` for permanent availability):
    ```bash
    source $HOME/.local/bin/env
    ```

**3. Installing Project Dependencies with `uv`:**

*   Ensure your `pyproject.toml` correctly lists dependencies like `fastmcp` (for FastMCP 2.0), `crawl4ai`, and `psycopg[binary]>=3.1` (for PostgreSQL v3 driver).
*   With the virtual environment active and `uv` in your PATH, install dependencies:
    ```bash
    uv pip install .
    ```
    *(This reads `pyproject.toml`, installs packages, and creates/updates `uv.lock`.)*
    *Troubleshooting `uv` commands:*
        *   If `uv pip sync uv.lock` gives parsing errors, it might be due to a malformed lock file or incorrect usage. Prefer `uv pip install .` to regenerate the lock file from `pyproject.toml` if unsure.
        *   Ensure you use `uv pip install .` (with the dot) for `pyproject.toml` in the current directory.

**3.1. Install Playwright Browsers (Required for Crawl4AI Initialization):**

*   Crawl4AI uses Playwright for browser automation to crawl dynamic web pages. Even if you primarily intend to crawl sitemaps or text files (which use `requests` or direct fetching), the `AsyncWebCrawler` component currently attempts to initialize its Playwright setup when the server starts (during its lifespan initialization). Therefore, installing Playwright browsers is a required step for the server to start and function correctly.
*   After installing dependencies via `uv pip install .`, you need to install the browser binaries for Playwright:
    ```bash
    playwright install
    ```
    *(Run this with your virtual environment active.)*

**4. Setting up the PostgreSQL Database with Docker:**

*   Your project uses `docker-compose.yml` to define a PostgreSQL service with pgvector.
*   **Start the Docker container:**
    ```bash
    docker-compose up -d
    ```
    *Troubleshooting Port Conflicts:*
        *   If you see an error like `Bind for 0.0.0.0:5432 failed: port is already allocated`, it means another service is using port 5432.
        *   Identify and stop the conflicting service (e.g., on macOS: `sudo lsof -i :5432`).
        *   Alternatively, change the host port in `docker-compose.yml` (e.g., `"5433:5432"`) and update `POSTGRES_PORT` in your `.env` file accordingly.
*   **Apply the Database Schema:**
    Once the container is running, apply the schema from `crawled_pages.sql`:
    ```bash
    cat crawled_pages.sql | docker-compose exec -T postgres psql -U postgres -d uingest
    ```
    *(This command should be run from the project root where `crawled_pages.sql` and `docker-compose.yml` are located.)*

**5. Creating the `.env` Environment File:**

*   Copy `.env.example` (if provided) or manually create a `.env` file in the project root (`/Users/sc/dev/ultra/ingest/.env`).
*   Populate it with necessary variables, especially for LocalAI/OpenAI and PostgreSQL:
    ```env
    # For LocalAI/OpenAI
    OPENAI_BASE_URL=http://localhost:8080/v1 # Or your LocalAI endpoint
    OPENAI_API_KEY=your_api_key # Can be a dummy key for some LocalAI setups
    EMBEDDING_MODEL_NAME=your_localai_model_name # e.g., granite-embed-30m-eng

    # For PostgreSQL (should match docker-compose.yml if using it)
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_DB=uingest
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres

    # For the MCP Server itself
    HOST=0.0.0.0
    PORT=8051
    ```

**6. Running the Application:**

*   Ensure your virtual environment is active: `source .venv/bin/activate`
*   **To start the server (Foreground Mode):**
    Run the main script. The server will run in your terminal, and you'll see live logs. Press `Ctrl+C` to stop it.
    ```bash
    .venv/bin/python3 src/uingest_mcp.py
    ```
    *(Using the full path to the venv's python3 interpreter, `.venv/bin/python3`, is more robust than just `python` or `python3` if you encounter `command not found` or `ModuleNotFoundError` issues.)*

*   **To start the server (Background Mode - Not Recommended for Debugging):**
    If you need to run it in the background (e.g., for testing with `curl` without occupying the terminal), you can use `nohup` and `&` on macOS/Linux. However, logs will go to `nohup.out`, and errors might be harder to catch live.
    ```bash
    nohup .venv/bin/python3 src/uingest_mcp.py &
    ```
    To find and stop this background server:
    1.  Find its Process ID (PID): `ps aux | grep uingest_mcp.py` (or `lsof -i :8051` to find what's using the port).
    2.  Stop it: `kill <PID>` (or `kill -9 <PID>` if it doesn't stop).

*Troubleshooting Python Module Errors:*
    *   `ModuleNotFoundError: No module named 'fastmcp'`, `... 'psycopg'`, `... 'uingest'`, etc.:
        *   Ensure the virtual environment is active and was active when `uv pip install .` was run.
        *   Verify the correct Python interpreter is being used (hence `.venv/bin/python3 ...`).
        *   Check `pyproject.toml` for the correct package names (e.g., `psycopg[binary]>=3.1` for `from psycopg import ...`, `fastmcp` for `from fastmcp import ...`).
        *   Ensure imports in the Python code match the library providing them (e.g., `from crawl4ai import AsyncWebCrawler...` if `crawl4ai` provides those, not `from uingest import ...` if `uingest` is your project's name).
    *   `ImportError: cannot import name ...` often indicates a circular dependency. For example, if `uingest_mcp.py` imports `utils.py`, but `utils.py` also tries to import from `uingest_mcp.py`. Utility modules should generally not import from higher-level application scripts that depend on them.
    *   `NameError: name 'Path' is not defined`: Caused by missing `from pathlib import Path` in the script using `Path`.

**7. Verifying the Server:**

*   If successful, you'll see Uvicorn logs: `Uvicorn running on http://0.0.0.0:8051`.
*   **Primary Check (SSE Endpoint):** The main MCP endpoint is `/sse`. You can test its basic availability with `curl` (though it's a streaming endpoint):
    ```bash
    curl http://localhost:8051/sse
    ```
    You should see an immediate response from the server, typically starting with an event line like `event: endpoint` or similar, indicating the SSE connection is established. If the server subsequently encounters an issue (like Playwright browsers not being installed during lifespan setup), the `curl` might then show an error or close, but the initial connection indicates FastMCP is responding on `/sse`.
*   **API Docs & Health Check:** Endpoints like `/docs` (Swagger UI), `/openapi.json`, and `/health` may return a `404 Not Found` with this version of FastMCP or its default configuration. The absence of these at the root doesn't necessarily mean the MCP server isn't working; `/sse` is the key functional endpoint for MCP clients.
*   For full functionality (e.g., crawling tools), ensure Playwright browsers are installed by running `playwright install` in your activated virtual environment.

This detailed walkthrough should help in setting up and running the application smoothly.
