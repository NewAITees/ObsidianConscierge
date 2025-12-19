# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ObsidianConscierge** is an AI-driven knowledge management system for Obsidian. It provides semantic search, automated document analysis, and daily insights to help users focus on writing and thinking rather than organizing.

### Core Services
1. **Vector Indexing & DB Management**: Indexes Obsidian markdown files into ChromaDB for semantic search
2. **Daily Insight**: Provides daily reports and search UI for knowledge discovery
3. **Analysis**: Detects duplicates, identifies bridge articles, and generates knowledge maps

### Key Technologies
- **Package Manager**: `uv` (faster than Poetry)
- **LLM**: Ollama (llama3/mistral) for text generation (summaries, tags)
- **Embeddings**: sentence-transformers (distiluse-base-multilingual-cased-v2) for vector generation
- **Vector DB**: ChromaDB (local, persistent storage)
- **Git Sync**: GitPython for managing `TargetObsidianVault` directory
- **Web Framework**: FastAPI for search API and UI

## Common Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_embedding_service.py

# Run integration tests only
uv run pytest tests/integration/
```

### Code Quality
```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Type checking
uv run mypy app/
```

### Running the Application
```bash
# Start FastAPI server (development mode)
uv run uvicorn app.main:app --reload --port 8000

# Create initial index (first-time setup)
uv run python scripts/initial_index.py

# CLI search tool
uv run python scripts/search_cli.py

# Git sync (pull from remote)
uv run python scripts/git_sync.py
# or using bash script
bash scripts/git_sync.sh
```

### Systemd Service Management
```bash
# Git sync service (runs every 30 minutes)
sudo systemctl start obsidian-conscierge-sync.timer
sudo systemctl status obsidian-conscierge-sync.timer
sudo journalctl -u obsidian-conscierge-sync.service -f
```

## Architecture Overview

### Dependency Flow
```
main.py (FastAPI app)
  ├─> Services (initialized once)
  │   ├─> EmbeddingService (sentence-transformers)
  │   ├─> LLMService (Ollama)
  │   └─> VectorDBService (ChromaDB)
  │
  ├─> Core Logic
  │   ├─> IndexingService (orchestrates indexing pipeline)
  │   ├─> SearchService (semantic search)
  │   └─> GitSyncService (Git operations)
  │
  └─> API Routes
      ├─> /api/v1/search (semantic search)
      ├─> /api/v1/config (vault configuration)
      └─> /health (health check)
```

### LLM vs Embeddings: Critical Distinction
- **Ollama (LLM)**: Used ONLY for text generation (summaries, tag suggestions)
- **sentence-transformers**: Used for embedding generation (vector representation)
- **DO NOT** use Ollama for embeddings - the existing sentence-transformers implementation is faster and proven

### Git Sync Architecture
- Obsidian vault is cloned into `TargetObsidianVault/` directory
- Git operations are performed locally using `GitPython` (NOT GitHub API)
- Change detection compares current HEAD with last processed commit ID (stored in `data/last_commit.txt`)
- Only modified/added/deleted `.md` files trigger re-indexing

### AI Auto-Generated Section: Critical Safety Rule

**⚠️ ABSOLUTE RULE FOR OBSIDIAN FILE EDITING ⚠️**

The system can automatically edit Obsidian markdown files to insert similar links and auto-generated tags. This is done ONLY within a specially marked section:

```markdown
========== AI AUTO-GENERATED SECTION START ==========
## 🤖 AI自動生成セクション

### 🔗 類似ドキュメント
- 🔗 [[Document1]] (類似度: 0.850)

### 🏷️ 自動タグ
#python #fastapi

最終更新: 2025-01-15 10:30:00
========== AI AUTO-GENERATED SECTION END ==========
```

**NEVER edit content outside this section.** All existing text, headings, links, tags, and frontmatter MUST be preserved exactly.

Implementation: `app/core/document_updater.py` manages this section exclusively. Excluded folders (configured in `.env`) are never touched.

## Important Design Decisions

### Why uv instead of Poetry?
- Faster dependency resolution and installation
- Modern Python packaging standards
- Better compatibility with Python 3.11+

### Why Local LLM (Ollama)?
- Privacy: no data sent to external APIs
- Cost: no per-token charges
- Control: can run offline
- Performance: comparable to GPT-3.5/GPT-4 for summarization tasks

### Why sentence-transformers for Embeddings?
- Proven implementation in `sample_code/` (5,800+ files indexed successfully)
- Fast: ~1 second per article
- Multilingual support (Japanese + English)
- Deterministic fallback when model loading fails

### Excluded Folders (AI Auto-Editing)
The following folders are NEVER modified by auto-editing features:
- `01DIARY`, `02TEMPLATES`, `06MOC`, `10KANBAN`, `11MEDIA`
- `Excalidraw`, `Maybe`, `Omnivore`, `model_cache`, `PythonScripts`
- `github`, `.chroma_db`, `.claude`, `.devcontainer`
- Root directory files (configurable via `EXCLUDE_ROOT_FILES=true`)

## Configuration

All settings are managed through `.env` file (see `.env.example` for full list). Key settings:

```env
# GitHub (for TargetObsidianVault sync)
GITHUB_REPO_NAME=username/vault-repo  # or GITHUB_REPO_URL
GITHUB_TOKEN=ghp_xxxxx

# Obsidian
OBSIDIAN_VAULT_NAME=YourVaultName
OBSIDIAN_VAULT_PATH=./TargetObsidianVault

# Ollama (text generation only)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=gpt-oss:20b  # or llama3, mistral

# Vector DB
CHROMA_DB_PATH=./data/chroma_db

# AI Auto-Editing
ENABLE_AUTO_LINK_INSERT=true
ENABLE_AUTO_TAG_INSERT=true
EXCLUDED_FOLDERS=01DIARY,02TEMPLATES,06MOC,...
```

## Testing Strategy

### Current Coverage
Target: 80%+ coverage. Check current coverage: `uv run pytest --cov=app --cov-report=term-missing`

### Test Structure
- `tests/unit/`: Unit tests with mocked dependencies
- `tests/integration/`: End-to-end workflow tests
- `tests/fixtures/`: Shared test data and mock implementations

### Running Tests Without Models
Tests use mocked Ollama and sentence-transformers to avoid downloading large models (4-5GB). See `tests/fixtures/` for mock implementations.

## Development Workflow

1. **Make changes to code**
2. **Run tests**: `uv run pytest`
3. **Check code quality**: `uv run ruff check . && uv run mypy app/`
4. **Format code**: `uv run ruff format .`
5. **Test locally**: `uv run uvicorn app.main:app --reload`
6. **Commit with descriptive message**: Follow conventional commits (feat:/fix:/docs:)

## Implementation Status

### ✅ Completed (Phase 1)
- Core services (Embedding, LLM, VectorDB, Git sync)
- FastAPI app with search API and UI
- Initial indexing and incremental updates
- CLI search tool
- Systemd configuration for Git sync

### ⏳ In Progress (Phase 2)
- Daily report generation (`scripts/daily_report.py`)
- Analysis service (duplicate detection, MOC candidates)
- Test coverage improvement (currently 43%, target 80%)

### 📋 Planned (Phase 3+)
- Knowledge map visualization
- Bridge article detection
- Clustering and advanced analysis

## Common Issues & Solutions

### Ollama Connection Failed
- Ensure Ollama is running: `ollama serve`
- Check model is downloaded: `ollama list`
- Verify base URL in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`

### ChromaDB Permission Errors
- Check directory permissions: `chmod -R 755 data/chroma_db`
- Ensure `data/` directory exists: `mkdir -p data/chroma_db`

### Git Sync Fails
- Verify GitHub token has repo read/write access
- Check `TargetObsidianVault/.git` exists
- Review logs: `sudo journalctl -u obsidian-conscierge-sync.service`

## Key Files to Understand

- `app/main.py`: FastAPI application initialization, service dependency injection
- `app/core/indexing.py`: Orchestrates the indexing pipeline (Git → Extract → Embed → Store)
- `app/core/search.py`: Semantic search implementation using ChromaDB
- `app/services/`: Service layer (embedding, LLM, vector DB abstractions)
- `app/core/config.py`: Pydantic Settings for configuration management
- `scripts/initial_index.py`: Initial indexing of all articles (first-time setup)
- `scripts/git_sync.py`: Periodic Git sync and incremental indexing

## Reference Documentation

For detailed information, see:
- `docs/PRD.md`: Product requirements and feature specifications
- `docs/TODO.md`: Detailed task list with priorities and dependencies
- `docs/STATUS.md`: Current implementation status
- `docs/SYSTEMD_SETUP.md`: Systemd service setup instructions
- `README.md`: Quick start and user-facing documentation
