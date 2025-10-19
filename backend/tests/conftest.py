"""
Shared test fixtures for the RAG system test suite

This module provides reusable fixtures for:
- Mock Anthropic API responses
- Test configuration
- RAG system instances
- FastAPI test client setup
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from rag_system import RAGSystem


# Mock response classes to simulate Anthropic API responses
@dataclass
class MockTextBlock:
    """Mock text content block from Claude API"""
    type: str = "text"
    text: str = ""


@dataclass
class MockToolUseBlock:
    """Mock tool use block from Claude API"""
    type: str = "tool_use"
    name: str = ""
    id: str = ""
    input: dict = None


@dataclass
class MockResponse:
    """Mock Claude API response"""
    content: List
    stop_reason: str


# Configuration Fixtures

@pytest.fixture
def mock_config():
    """Create a test configuration with safe defaults"""
    config = Config()
    config.ANTHROPIC_API_KEY = "test-api-key-12345"
    config.ANTHROPIC_MODEL = "claude-test-model"
    config.CHROMA_PATH = "./test_chroma_db"
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    return config


# Anthropic Client Fixtures

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    with patch('anthropic.Anthropic') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


# RAG System Fixtures

@pytest.fixture
def mock_rag_system(mock_config):
    """Create RAG system with fully mocked dependencies"""
    with patch('anthropic.Anthropic'), \
         patch('chromadb.PersistentClient'), \
         patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
        rag = RAGSystem(mock_config)
        yield rag


@pytest.fixture
def mock_vector_store_search():
    """Create a mock vector store search function that returns sample results"""
    from vector_store import SearchResults

    def search_func(query: str = "", course_name: str = None, lesson_number: int = None):
        """Mock search that returns sample course content"""
        return SearchResults(
            documents=["Sample course content about the topic"],
            metadata=[{
                "course_title": "Sample Course",
                "lesson_number": 1,
                "lesson_title": "Introduction"
            }],
            distances=[0.25],
            error=None
        )

    return search_func


# FastAPI Test Client Fixtures

@pytest.fixture
def test_app():
    """Create a test FastAPI application without static file mounting

    This avoids issues with missing frontend directory in test environment.
    The app includes only the API endpoints needed for testing.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app
    app = FastAPI(title="Test RAG System")

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Mock RAG system for test app
    mock_rag = Mock()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Test endpoint for querying documents"""
        try:
            session_id = request.session_id or "test-session-123"

            # Use mock RAG system
            answer, sources = mock_rag.query(request.query, session_id)

            source_items = [SourceItem(**s) for s in sources] if sources else []

            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Test endpoint for course statistics"""
        try:
            analytics = mock_rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Test root endpoint"""
        return {"status": "ok", "message": "RAG System API"}

    # Store mock for access in tests
    app.state.mock_rag = mock_rag

    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test FastAPI app"""
    return TestClient(test_app)


# Mock Response Builders

@pytest.fixture
def create_text_response():
    """Factory fixture for creating mock text responses"""
    def _create(text: str) -> MockResponse:
        return MockResponse(
            content=[MockTextBlock(text=text)],
            stop_reason="end_turn"
        )
    return _create


@pytest.fixture
def create_tool_use_response():
    """Factory fixture for creating mock tool use responses"""
    def _create(tool_name: str, tool_id: str, tool_input: dict) -> MockResponse:
        return MockResponse(
            content=[MockToolUseBlock(
                name=tool_name,
                id=tool_id,
                input=tool_input
            )],
            stop_reason="tool_use"
        )
    return _create


# Test Data Fixtures

@pytest.fixture
def sample_course_metadata():
    """Sample course metadata for testing"""
    return {
        "course_title": "Introduction to Model Context Protocol",
        "course_link": "https://example.com/mcp-course",
        "course_instructor": "Jane Smith",
        "lessons": [
            {"lesson_number": 0, "title": "Getting Started", "link": "https://example.com/mcp/lesson0"},
            {"lesson_number": 1, "title": "Core Concepts", "link": "https://example.com/mcp/lesson1"},
            {"lesson_number": 2, "title": "Building Servers", "link": "https://example.com/mcp/lesson2"}
        ]
    }


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    from vector_store import SearchResults
    return SearchResults(
        documents=[
            "MCP allows AI assistants to connect to data sources and tools.",
            "Servers provide resources and tools to clients via the MCP protocol."
        ],
        metadata=[
            {"course_title": "Introduction to MCP", "lesson_number": 1, "lesson_title": "Core Concepts"},
            {"course_title": "Introduction to MCP", "lesson_number": 2, "lesson_title": "Building Servers"}
        ],
        distances=[0.2, 0.35],
        error=None
    )


@pytest.fixture
def sample_query_response():
    """Sample query response for API testing"""
    return {
        "answer": "MCP (Model Context Protocol) is a protocol that allows AI assistants to connect to data sources.",
        "sources": [
            {"text": "Introduction to MCP - Lesson 1", "link": "https://example.com/mcp/lesson1"}
        ],
        "session_id": "test-session-123"
    }


# Cleanup Fixtures

@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Automatically cleanup test database after each test"""
    yield
    # Cleanup code runs after test
    import shutil
    test_db_path = "./test_chroma_db"
    if os.path.exists(test_db_path):
        try:
            shutil.rmtree(test_db_path)
        except Exception:
            pass  # Ignore cleanup errors
