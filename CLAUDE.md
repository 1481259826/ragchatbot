# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for querying course materials. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation with tool-calling capabilities, and FastAPI for the web interface.

## Key Commands

### Development
```bash
# Install dependencies
uv sync

# Run the application (starts on port 8000)
./run.sh

# Or manually from backend directory
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Environment Setup
Create a `.env` file in the root directory:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

### Core Components

The system follows a layered architecture with clear separation of concerns:

1. **RAGSystem** (backend/rag_system.py) - Central orchestrator that coordinates all components. Entry point for document ingestion and query processing.

2. **VectorStore** (backend/vector_store.py) - ChromaDB wrapper with two collections:
   - `course_catalog`: Stores course metadata (titles, instructors, lesson lists)
   - `course_content`: Stores chunked course content with metadata
   - Key feature: Semantic course name resolution allows partial matching (e.g., "MCP" finds "Introduction to Model Context Protocol")

3. **DocumentProcessor** (backend/document_processor.py) - Handles document parsing and text chunking:
   - Extracts structured course metadata from document headers
   - Parses lesson markers and creates lesson hierarchies
   - Chunks text using sentence-based splitting with configurable overlap
   - Adds contextual prefixes to chunks (e.g., "Course X Lesson Y content:")

4. **AIGenerator** (backend/ai_generator.py) - Claude API integration with tool-calling:
   - Uses Claude Sonnet 4 with tool definitions
   - Implements tool execution loop for search operations
   - Maintains conversation context via system prompts

5. **ToolManager & CourseSearchTool** (backend/search_tools.py) - Tool-calling framework:
   - `CourseSearchTool`: Provides semantic search with course/lesson filtering
   - `ToolManager`: Registers tools and handles execution
   - Tools track sources for UI display

6. **SessionManager** (backend/session_manager.py) - Conversation history management with configurable history limits.

### Document Format

Course documents follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [Lesson Title]
Lesson Link: [url]
[content]

Lesson 1: [Lesson Title]
[content]
```

### Data Flow

**Query Processing:**
1. FastAPI receives query at `/api/query` endpoint
2. RAGSystem.query() creates session and builds prompt
3. AIGenerator sends query to Claude with tool definitions
4. Claude may invoke `search_course_content` tool
5. ToolManager executes CourseSearchTool.execute()
6. VectorStore performs semantic search with optional filters
7. Results formatted and returned to Claude
8. Claude generates final response
9. Sources extracted from tool and returned to UI

**Document Ingestion:**
1. Startup event loads documents from `../docs`
2. RAGSystem.add_course_folder() processes each file
3. DocumentProcessor parses structure and creates chunks
4. VectorStore adds course metadata and content chunks
5. Existing courses detected and skipped based on titles

## Configuration

Settings in backend/config.py:
- `CHUNK_SIZE`: 800 chars - controls vector search granularity
- `CHUNK_OVERLAP`: 100 chars - ensures context continuity
- `MAX_RESULTS`: 5 - search results returned per query
- `MAX_HISTORY`: 2 - conversation exchanges remembered
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" - for vector embeddings
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"

## Technology Stack

- **Backend**: FastAPI + Uvicorn (Python 3.13+)
- **Vector DB**: ChromaDB 1.0.15 with persistent storage
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **AI**: Anthropic Claude with tool-calling
- **Frontend**: Static HTML/CSS/JS served by FastAPI
- **Package Manager**: uv

## Important Implementation Details

### Vector Store Design
- Course titles serve as unique IDs in both collections
- Lesson metadata stored as JSON strings in course_catalog
- Course name resolution uses vector similarity, not exact string matching
- Filters support AND/OR combinations for course + lesson searches

### Tool-Calling Pattern
- AI has access to `search_course_content` tool only
- System prompt enforces "one search per query maximum"
- Tool results formatted with course/lesson context headers
- Sources tracked separately from search results for UI

### Session Management
- Sessions auto-created if not provided
- History limited to last N exchanges (configurable)
- History included in system prompt, not as message array

### Chunking Strategy
- Sentence-based splitting preserves semantic units
- First chunk of each lesson gets "Lesson X content:" prefix
- Last lesson chunks get "Course Y Lesson X content:" prefix for better retrieval
- Overlap calculated in characters, applied at sentence boundaries
- make sure use uv to run python files