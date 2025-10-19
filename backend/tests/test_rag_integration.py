"""
Integration tests for RAG system content query handling
"""

import os
import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from rag_system import RAGSystem


@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    name: str = ""
    id: str = ""
    input: dict = None


@dataclass
class MockResponse:
    content: list
    stop_reason: str


class TestRAGSystemIntegration:
    """Integration tests for RAG system query processing"""

    @pytest.fixture
    def mock_config(self):
        """Create a test configuration"""
        config = Config()
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test"
        config.CHROMA_PATH = "./test_chroma_db"
        config.MAX_RESULTS = 5
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_HISTORY = 2
        return config

    @pytest.fixture
    def rag_system(self, mock_config):
        """Create RAG system with mocked components"""
        with (
            patch("anthropic.Anthropic"),
            patch("chromadb.PersistentClient"),
            patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ),
        ):
            return RAGSystem(mock_config)

    def test_query_with_tool_execution_flow(self, rag_system):
        """Test end-to-end query flow with tool execution"""
        # Mock the AI response with tool use
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_123",
                    input={"query": "MCP basics"},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="MCP is the Model Context Protocol")],
            stop_reason="end_turn",
        )

        # Mock the Anthropic client
        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        # Mock vector store search
        from vector_store import SearchResults

        mock_search_results = SearchResults(
            documents=["MCP allows AI assistants to connect to data sources"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": 1}],
            distances=[0.3],
            error=None,
        )
        rag_system.vector_store.search = Mock(return_value=mock_search_results)
        rag_system.vector_store.get_lesson_link = Mock(
            return_value="http://example.com/mcp/lesson1"
        )

        # Execute query
        response, sources = rag_system.query("What is MCP?")

        # Verify response
        assert response == "MCP is the Model Context Protocol"

        # Verify vector store was queried
        rag_system.vector_store.search.assert_called_once()

        # Verify sources were extracted
        assert len(sources) == 1
        assert sources[0]["text"] == "Introduction to MCP - Lesson 1"
        assert sources[0]["link"] == "http://example.com/mcp/lesson1"

    def test_query_without_tool_use(self, rag_system):
        """Test query that doesn't require tool use (general knowledge)"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Python is a programming language")],
            stop_reason="end_turn",
        )

        rag_system.ai_generator.client.messages.create = Mock(
            return_value=mock_response
        )

        response, sources = rag_system.query("What is Python?")

        # Should get direct response
        assert response == "Python is a programming language"

        # No sources since no tool was used
        assert len(sources) == 0

    def test_query_with_search_error(self, rag_system):
        """Test handling of search errors"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_456",
                    input={"query": "test", "course_name": "NonExistent"},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="I couldn't find that course")],
            stop_reason="end_turn",
        )

        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        # Mock search returning error
        from vector_store import SearchResults

        error_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'NonExistent'",
        )
        rag_system.vector_store.search = Mock(return_value=error_results)

        response, sources = rag_system.query("Tell me about NonExistent course")

        # Should still get a response
        assert "couldn't find" in response
        assert len(sources) == 0

    def test_query_with_session_management(self, rag_system):
        """Test that session history is maintained"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Response")], stop_reason="end_turn"
        )
        rag_system.ai_generator.client.messages.create = Mock(
            return_value=mock_response
        )

        # First query
        response1, _ = rag_system.query("First question", session_id="session_123")

        # Second query with same session
        response2, _ = rag_system.query("Second question", session_id="session_123")

        # Check that history was passed in second call
        second_call_args = (
            rag_system.ai_generator.client.messages.create.call_args_list[1]
        )
        system_prompt = second_call_args[1]["system"]

        # History should contain the first exchange
        assert "First question" in system_prompt
        assert "Response" in system_prompt

    def test_query_empty_search_results(self, rag_system):
        """Test handling of empty search results"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_789",
                    input={"query": "rare topic"},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="No content found on that topic")],
            stop_reason="end_turn",
        )

        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        # Mock empty search results
        from vector_store import SearchResults

        empty_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        rag_system.vector_store.search = Mock(return_value=empty_results)

        response, sources = rag_system.query("Find rare topic")

        assert "No content found" in response or "No relevant content found" in response
        assert len(sources) == 0

    def test_query_with_course_filter(self, rag_system):
        """Test query with course-specific search"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_course",
                    input={"query": "servers", "course_name": "MCP"},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="MCP servers provide tools to AI")],
            stop_reason="end_turn",
        )

        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        from vector_store import SearchResults

        mock_results = SearchResults(
            documents=["Server content"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": 2}],
            distances=[0.2],
            error=None,
        )
        rag_system.vector_store.search = Mock(return_value=mock_results)
        rag_system.vector_store.get_lesson_link = Mock(return_value=None)

        response, sources = rag_system.query("What are MCP servers?")

        # Verify course filter was used
        call_args = rag_system.vector_store.search.call_args
        assert call_args[1]["course_name"] == "MCP"

    def test_query_with_lesson_filter(self, rag_system):
        """Test query with lesson-specific search"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_lesson",
                    input={"query": "content", "lesson_number": 3},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Lesson 3 covers...")], stop_reason="end_turn"
        )

        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        from vector_store import SearchResults

        mock_results = SearchResults(
            documents=["Lesson content"],
            metadata=[{"course_title": "Course", "lesson_number": 3}],
            distances=[0.1],
            error=None,
        )
        rag_system.vector_store.search = Mock(return_value=mock_results)
        rag_system.vector_store.get_lesson_link = Mock(return_value=None)

        response, sources = rag_system.query("What's in lesson 3?")

        # Verify lesson filter was used
        call_args = rag_system.vector_store.search.call_args
        assert call_args[1]["lesson_number"] == 3

    def test_sources_reset_after_query(self, rag_system):
        """Test that sources are reset after being retrieved"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_reset",
                    input={"query": "test"},
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Answer")], stop_reason="end_turn"
        )

        rag_system.ai_generator.client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        from vector_store import SearchResults

        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Course", "lesson_number": 1}],
            distances=[0.3],
            error=None,
        )
        rag_system.vector_store.search = Mock(return_value=mock_results)
        rag_system.vector_store.get_lesson_link = Mock(return_value=None)

        # First query
        response1, sources1 = rag_system.query("Query 1")
        assert len(sources1) > 0

        # Sources should be reset for next query
        assert len(rag_system.search_tool.last_sources) == 0

    def test_tool_manager_registration(self, rag_system):
        """Test that tools are properly registered"""
        tool_defs = rag_system.tool_manager.get_tool_definitions()

        # Should have both search and outline tools
        assert len(tool_defs) == 2

        tool_names = [tool["name"] for tool in tool_defs]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_query_uses_correct_tool_definitions(self, rag_system):
        """Test that query passes correct tool definitions to AI"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Response")], stop_reason="end_turn"
        )
        rag_system.ai_generator.client.messages.create = Mock(
            return_value=mock_response
        )

        rag_system.query("Test query")

        call_args = rag_system.ai_generator.client.messages.create.call_args[1]

        # Should have tools parameter
        assert "tools" in call_args
        assert len(call_args["tools"]) == 2

        # Should have tool_choice set to auto
        assert call_args["tool_choice"] == {"type": "auto"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
