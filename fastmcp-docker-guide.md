
# 📘 Running FastMCP with FastAPI in Docker and Accessing via SSE

This guide explains how to run a **FastMCP**-powered server inside a **Docker container** that already uses **FastAPI**, and how to access its tools using the **Model Context Protocol (MCP)** over **Server-Sent Events (SSE)**.

---

## 🧠 What is FastMCP?

**FastMCP** is a Python framework built on top of **FastAPI** to expose AI tools using the **Model Context Protocol (MCP)**. It supports:
- HTTP (via FastAPI)
- Stdio (for local use)
- SSE (for streaming over HTTP)

---

## 🔧 Requirements

- Docker installed
- Your FastAPI + FastMCP project (e.g., `crawl4ai_mcp.py`)
- Exposed port (e.g., 8008)

---

## 📁 Example Project Structure

```
your-project/
├── src/
│   └── crawl4ai_mcp.py    # Your FastAPI + FastMCP entrypoint
├── Dockerfile
├── .env
```

---

## ⚙️ Example `crawl4ai_mcp.py` with FastMCP

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool()
def hello_world():
    return "Hello from FastMCP!"

# Run with: python src/crawl4ai_mcp.py
```

This automatically creates:
- `/sse` for Server-Sent Events
- `/health` for health checks
- `/docs` for OpenAPI docs (FastAPI-native)

---

## 🐳 Example `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --upgrade pip
RUN pip install -e .  # Or install your dependencies here

EXPOSE 8008

CMD ["python", "src/crawl4ai_mcp.py"]
```

---

## 🧪 Running the Container

Build and run:

```bash
docker build -t fastmcp-app .
docker run --env-file .env -p 8008:8008 fastmcp-app
```

---

## 🌐 Accessing FastMCP via SSE

Once running, your FastMCP server is live at:

```
http://localhost:8008/sse
```

You can now connect to it from any MCP-compatible client using this configuration:

```json
{
  "mcpServers": {
    "fastmcp": {
      "transport": "sse",
      "url": "http://localhost:8008/sse"
    }
  }
}
```

✅ You can test with:
- Claude Desktop
- Windsurf
- Archon CLI
- Any tool using the MCP spec

---

## 🛠 Troubleshooting

| Issue                       | Fix                                                                 |
|----------------------------|----------------------------------------------------------------------|
| `404 /sse`                 | Ensure `FastMCP` is initialized and `python src/crawl4ai_mcp.py` is the entrypoint |
| No response via SSE        | Check `.env` and FastAPI logs, validate with `curl http://localhost:8008/health` |
| Docker not exposing port   | Ensure `-p 8008:8008` is used during `docker run`                    |

---

## ✅ Health Check & Testing

- Visit `http://localhost:8008/docs` to view the FastAPI Swagger UI.
- Visit `http://localhost:8008/health` to confirm the server is running.
