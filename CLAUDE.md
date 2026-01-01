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

# Install pre-commit hooks (recommended for development)
uv run pre-commit install

# Run pre-commit checks manually
uv run pre-commit run --all-files
```

**IMPORTANT: Pre-commit Hook Usage**
- Pre-commit hooks automatically run linter, formatter, and type checks before each commit
- Install hooks immediately when starting development: `uv run pre-commit install`
- If checks fail, the commit is aborted - fix issues and retry
- This prevents CI/CD failures and maintains code quality in commit history
- Priority: Address warnings and info messages proactively to reduce context consumption

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

# Daily report generation
uv run python scripts/daily_report.py

# Database statistics
uv run python scripts/db_stats.py

# Test search methods (all 7 search types)
uv run python scripts/test_search_methods.py
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
      ├─> /api/v1/reports/daily/{date} (daily reports)
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

### Search Methods (7 Types)
The system provides 7 comprehensive search methods implemented in `app/core/search.py`:

1. **Semantic Search**: Natural language queries using embeddings (primary method)
2. **Tag Search**: Filter by one or more tags
3. **Keyword Search**: Exact text matching in title/content
4. **Date Range Search**: Filter by creation/modification date
5. **Word Count Range Search**: Filter by article length
6. **Hybrid Search**: Combine semantic + tags + word count filters
7. **Similar Document Search**: Find articles similar to a given document

All methods support pagination and are accessible via CLI (`scripts/search_cli.py`) and API (`/api/v1/search`).

### Atomic Notes Workflow (Planned Phase 3)

**Concept**: Information management based on "1 file = 1 theme" principle instead of folder-based organization.

**4-Stage Pipeline:**
1. **00_Raw (Input)**: Dump all information without classification
2. **01_Summary (Formatting)**: AI-powered summarization and tag generation
3. **02_Atomic (Atomization)**: Split long notes into independent atomic notes
4. **03_MOC (Linking)**: Connect notes via links, not folders (Map of Contents)

**Benefits:**
- AI-friendly structure (no folder hierarchy confusion)
- High reusability (combine like Lego blocks)
- Eliminates classification ambiguity
- Clean graph view visualization

**Key Features (Planned):**
- Note splitting: Automatically extract atomic concepts from long notes
- Atomicity scoring: Evaluate if note follows "1 file = 1 theme" principle
- Pipeline management: Track notes through 4-stage workflow
- MOC auto-generation: Automatically create Maps of Contents from related notes

See `docs/ATOMIC_NOTES_INTEGRATION.md` for detailed design.

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

**Implementation Details:**
- `app/core/document_updater.py`: Core section management with regex-based extraction
  - `extract_ai_section()`: Safely extracts AI section using explicit markers
  - `create_ai_section()`: Generates new section content with links and tags
  - `update_document()`: Replaces existing section or appends to file end
  - `is_file_excluded()`: Checks if file is in excluded folders or vault root
- `app/core/link_inserter.py`: Manages similar document link insertion
- `app/core/tag_inserter.py`: Manages auto-generated tag insertion
- Section markers are unique strings to prevent accidental matches: `"=" * 10 + " AI AUTO-GENERATED SECTION START " + "=" * 10`
- Excluded folders (configured in `.env`) are never touched
- Root directory files are excluded by default (`EXCLUDE_ROOT_FILES=true`)

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
- **Current**: 59% (71 tests passing)
- **Target**: 80%+
- Check coverage: `uv run pytest --cov=app --cov-report=term-missing`
- Generate HTML report: `uv run pytest --cov=app --cov-report=html` (view at `htmlcov/index.html`)

### Test Structure
- `tests/unit/`: Unit tests with mocked dependencies (25 tests for analysis, 10+ for services)
- `tests/integration/`: End-to-end workflow tests (API, indexing, search workflows)
- `tests/fixtures/`: Shared test data and mock implementations (Ollama, sentence-transformers)

### Running Tests Without Models
Tests use mocked Ollama and sentence-transformers to avoid downloading large models (4-5GB). See `tests/fixtures/` for mock implementations.

### Test Execution Notes
- All 71 tests pass successfully
- Integration tests use real Git repositories (temporary clones)
- Async tests use `pytest-asyncio` in auto mode
- Coverage excludes `__init__.py`, test files, and abstract methods

## Development Workflow

1. **Setup pre-commit hooks** (first time only): `uv run pre-commit install`
2. **Make changes to code**
3. **Run tests**: `uv run pytest`
4. **Check code quality**: `uv run ruff check . && uv run mypy app/`
5. **Format code**: `uv run ruff format .`
6. **Test locally**: `uv run uvicorn app.main:app --reload`
7. **Commit with descriptive message**:
   - Follow conventional commits (feat:/fix:/docs:/refactor:/test:/chore:)
   - Pre-commit hooks will auto-run linter, formatter, and type checks
   - If hooks fail, fix issues and retry commit
8. **Address all warnings**: Proactively fix warning and info messages to reduce context consumption

### Commit Message Format
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

**Examples**:
- ✅ `feat: add semantic search with pagination`
- ✅ `fix: resolve ChromaDB connection timeout`
- ✅ `refactor: extract document updater logic to separate module`
- ❌ `update code` (too vague)
- ❌ `wip` (not descriptive)

## Implementation Status

### ✅ Completed (Phase 1)
- Core services (Embedding, LLM, VectorDB, Git sync)
- FastAPI app with search API and UI
- Initial indexing and incremental updates
- CLI search tool
- Systemd configuration for Git sync

### ✅ Completed (Phase 2)
- Daily report generation (`scripts/daily_report.py`) - COMPLETED
- Analysis service (`app/core/analysis.py`) - duplicate detection, MOC candidates, writing statistics
- Reports API (`app/api/reports.py`) - daily report endpoints

### ⏳ In Progress (Phase 2.3)
- Test coverage improvement (currently 59%, target 80%)

### 📋 Planned (Phase 3+)
- **Atomic Notes Workflow** (Phase 3.1-3.5): 4-stage pipeline integration
  - 00_Raw (input), 01_Summary (formatting), 02_Atomic (atomization), 03_MOC (linking)
  - Note splitting, atomicity scoring, MOC auto-generation
  - See `docs/ATOMIC_NOTES_INTEGRATION.md` for details
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

### Core Application
- `app/main.py`: FastAPI application initialization, service dependency injection
- `app/core/config.py`: Pydantic Settings for configuration management, GitHub repo URL resolution
- `app/core/indexing.py`: Orchestrates the indexing pipeline (Git → Extract → Embed → Store)
- `app/core/search.py`: Semantic search implementation using ChromaDB (7 search methods)
- `app/core/analysis.py`: Analysis logic (duplicates, MOC candidates, writing stats, random picks)

### AI Auto-Editing
- `app/core/document_updater.py`: Safe section-based document editing with exclusion rules
- `app/core/link_inserter.py`: Similar document link insertion
- `app/core/tag_inserter.py`: Auto-generated tag insertion

### Services
- `app/services/embedding_service.py`: sentence-transformers wrapper with deterministic fallback
- `app/services/llm_service.py`: Ollama API client with retry logic
- `app/services/vector_db_service.py`: ChromaDB operations (add, search, delete, update)

### API Routes
- `app/api/search.py`: Search endpoints with pagination and filtering
- `app/api/reports.py`: Daily report endpoints
- `app/api/config.py`: Configuration endpoints

### Scripts
- `scripts/initial_index.py`: Initial indexing of all articles (first-time setup)
- `scripts/git_sync.py`: Periodic Git sync and incremental indexing
- `scripts/daily_report.py`: Daily report generation (Markdown/HTML output)
- `scripts/search_cli.py`: CLI search tool with 7 search methods
- `scripts/db_stats.py`: ChromaDB statistics and diagnostics
- `scripts/test_search_methods.py`: Test script for all search methods

## MCP (Model Context Protocol) Integration

This project supports MCP for enhanced automation and workflow execution.

### Available MCP Server: Serena

**Serena** (`oraios/serena`) is an MCP execution engine for IDE assistant contexts, enabling command execution and workflow triggers.

### When to Use MCP

1. **Repetitive script execution**: Automated workflows that run multiple times
2. **Project-specific execution flows**: Custom pipelines for indexing, sync, or analysis
3. **Safe command triggering**: Execution with security guards and logging

### MCP Usage Pattern

```text
[Plan] Define objective, inputs, outputs, safety guards, and MCP server to use
  ↓ (y/n confirmation)
[Select MCP] {serena}
  ↓
[Call] Minimize input (no PII/secrets), set timeout/retry
  ↓
[Record] Save logs to logs/mcp/
  ↓
[Review] Summarize results, propose next action (y/n)
```

### Example MCP Invocation (Serena)

```bash
docker run --rm -i --network host -v "$PWD":/workspaces/projects \
  ghcr.io/oraios/serena:latest serena start-mcp-server \
  --transport stdio --context ide-assistant --project /workspaces/projects
```

### MCP Governance

- **Logging**: All MCP calls logged to `logs/mcp/` with timestamp, input summary, output hash
- **Secrets**: Never pass env vars or tokens directly; use Serena's safe context
- **Retry Policy**: Max 2 retries on failure; alternative approaches require re-approval

## Reference Documentation

For detailed information, see:
- `docs/PRD.md`: Product requirements and feature specifications
- `docs/TODO.md`: Detailed task list with priorities and dependencies
- `docs/STATUS.md`: Current implementation status
- `docs/ATOMIC_NOTES_INTEGRATION.md`: Atomic Notes workflow integration design (Phase 3)
- `docs/SYSTEMD_SETUP.md`: Systemd service setup instructions
- `docs/SEARCH_METHODS.md`: Comprehensive search methods documentation
- `README.md`: Quick start and user-facing documentation
