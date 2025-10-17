# Course Materials RAG Chatbot

A full-stack Retrieval-Augmented Generation (RAG) system for querying course materials using semantic search and AI-powered responses.

![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- **Semantic Search**: Intelligent course content search using ChromaDB vector database
- **AI-Powered Responses**: Context-aware answers powered by Anthropic's Claude Sonnet 4
- **Tool Calling**: Claude autonomously decides when to search course materials
- **Session Management**: Maintains conversation history for contextual follow-ups
- **Smart Course Matching**: Partial course name matching (e.g., "MCP" finds full course title)
- **Source Attribution**: Transparent source references for all answers
- **Modern Web UI**: Clean, responsive chat interface with markdown support
- **RESTful API**: Well-documented FastAPI backend with automatic OpenAPI docs

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

The system follows a layered architecture:

```
Frontend (HTML/JS) → FastAPI → RAG System → AI Generator ↔ Claude API
                                    ↓              ↓
                              Vector Store    Tool Manager
                                    ↓
                               ChromaDB
```

### Core Components

- **RAGSystem**: Central orchestrator coordinating all components
- **VectorStore**: ChromaDB wrapper with two collections (catalog + content)
- **AIGenerator**: Claude API integration with tool-calling support
- **ToolManager**: Manages search tools for Claude
- **SessionManager**: Conversation history management
- **DocumentProcessor**: Parses and chunks course documents

See [CLAUDE.md](./CLAUDE.md) for detailed architectural documentation.

## 📦 Prerequisites

- **Python 3.13+**
- **uv** (Python package manager) - [Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Anthropic API Key** - [Get yours here](https://console.anthropic.com/)
- **Git Bash** (Windows only) - [Download](https://git-scm.com/downloads/win)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/1481259826/ragchatbot.git
   cd ragchatbot
   ```

2. **Install uv** (if not already installed)
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Set up environment variables**

   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

   Or copy from the example:
   ```bash
   cp .env.example .env
   # Then edit .env with your API key
   ```

5. **Add course documents** (optional)

   Place course documents (.txt, .pdf, .docx) in the `docs/` folder.
   Documents should follow this format:
   ```
   Course Title: [title]
   Course Link: [url]
   Course Instructor: [name]

   Lesson 0: [Lesson Title]
   Lesson Link: [url]
   [content]
   ```

## 🎮 Running the Application

### Quick Start

```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## 📁 Project Structure

```
.
├── backend/
│   ├── app.py              # FastAPI application
│   ├── rag_system.py       # RAG orchestrator
│   ├── vector_store.py     # ChromaDB wrapper
│   ├── ai_generator.py     # Claude API integration
│   ├── search_tools.py     # Tool calling framework
│   ├── session_manager.py  # Conversation history
│   ├── document_processor.py # Document parsing
│   ├── models.py           # Data models
│   └── config.py           # Configuration
├── frontend/
│   ├── index.html          # Main UI
│   ├── script.js           # Frontend logic
│   └── style.css           # Styling
├── docs/                   # Course documents
├── .env.example            # Environment template
├── pyproject.toml          # Python dependencies
├── CLAUDE.md               # Detailed documentation
└── README.md               # This file
```

## ⚙️ Configuration

Edit `backend/config.py` to customize:

```python
CHUNK_SIZE = 800           # Text chunk size for embeddings
CHUNK_OVERLAP = 100        # Overlap between chunks
MAX_RESULTS = 5            # Search results per query
MAX_HISTORY = 2            # Conversation exchanges to remember
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
```

## 📚 API Documentation

### POST /api/query

Query the course materials.

**Request:**
```json
{
  "query": "What is RAG?",
  "session_id": "session_1" // optional
}
```

**Response:**
```json
{
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "sources": ["Course A - Lesson 2", "Course B - Lesson 5"],
  "session_id": "session_1"
}
```

### GET /api/courses

Get course statistics.

**Response:**
```json
{
  "total_courses": 3,
  "course_titles": ["Course A", "Course B", "Course C"]
}
```

## 🛠️ Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black backend/
uv run isort backend/
```

### Type Checking

```bash
uv run mypy backend/
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude API
- [ChromaDB](https://www.trychroma.com/) for vector database
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [Sentence Transformers](https://www.sbert.net/) for embeddings

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Built with ❤️ using Claude, FastAPI, and ChromaDB**