"""
Tests for CourseSearchTool execution method
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock VectorStore"""
        store = Mock()
        store.get_lesson_link = Mock(return_value=None)
        return store

    @pytest.fixture
    def search_tool(self, mock_vector_store):
        """Create CourseSearchTool with mock store"""
        return CourseSearchTool(mock_vector_store)

    def test_execute_basic_search_success(self, search_tool, mock_vector_store):
        """Test basic search without filters returns formatted results"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["This is lesson content about MCP"],
            metadata=[{
                "course_title": "Introduction to Model Context Protocol",
                "lesson_number": 1
            }],
            distances=[0.5],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        # Execute search
        result = search_tool.execute(query="What is MCP?")

        # Verify store.search was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?",
            course_name=None,
            lesson_number=None
        )

        # Verify formatted output
        assert "Introduction to Model Context Protocol" in result
        assert "Lesson 1" in result
        assert "This is lesson content about MCP" in result

    def test_execute_with_course_filter(self, search_tool, mock_vector_store):
        """Test search with course_name filter"""
        mock_results = SearchResults(
            documents=["Course content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.3],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test query", course_name="Test Course")

        # Verify filter was passed
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="Test Course",
            lesson_number=None
        )

    def test_execute_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test search with lesson_number filter"""
        mock_results = SearchResults(
            documents=["Lesson content"],
            metadata=[{"course_title": "Course", "lesson_number": 2}],
            distances=[0.2],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test", lesson_number=2)

        # Verify lesson filter
        mock_vector_store.search.assert_called_once_with(
            query="test",
            course_name=None,
            lesson_number=2
        )

    def test_execute_with_both_filters(self, search_tool, mock_vector_store):
        """Test search with both course and lesson filters"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Course", "lesson_number": 3}],
            distances=[0.1],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(
            query="query",
            course_name="Course",
            lesson_number=3
        )

        mock_vector_store.search.assert_called_once_with(
            query="query",
            course_name="Course",
            lesson_number=3
        )

    def test_execute_returns_error_from_results(self, search_tool, mock_vector_store):
        """Test that errors from SearchResults are returned"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'NonExistent'"
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test", course_name="NonExistent")

        assert result == "No course found matching 'NonExistent'"

    def test_execute_empty_results_no_filter(self, search_tool, mock_vector_store):
        """Test empty results without filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="nonexistent content")

        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(self, search_tool, mock_vector_store):
        """Test empty results with course filter message"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test", course_name="Some Course")

        assert "No relevant content found" in result
        assert "in course 'Some Course'" in result

    def test_execute_empty_results_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test empty results with lesson filter message"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test", lesson_number=5)

        assert "No relevant content found" in result
        assert "in lesson 5" in result

    def test_execute_multiple_results(self, search_tool, mock_vector_store):
        """Test formatting of multiple search results"""
        mock_results = SearchResults(
            documents=[
                "First document content",
                "Second document content"
            ],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2}
            ],
            distances=[0.3, 0.5],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test")

        # Both results should be in output
        assert "Course A" in result
        assert "Course B" in result
        assert "Lesson 1" in result
        assert "Lesson 2" in result
        assert "First document content" in result
        assert "Second document content" in result

    def test_execute_stores_sources(self, search_tool, mock_vector_store):
        """Test that execute() stores sources in last_sources"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.3],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)
        mock_vector_store.get_lesson_link = Mock(return_value="http://example.com/lesson1")

        search_tool.execute(query="test")

        # Verify sources were stored
        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert search_tool.last_sources[0]["link"] == "http://example.com/lesson1"

    def test_execute_lesson_link_retrieval(self, search_tool, mock_vector_store):
        """Test that lesson links are retrieved from vector store"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Course", "lesson_number": 3}],
            distances=[0.2],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)
        mock_vector_store.get_lesson_link = Mock(return_value="http://lesson.link")

        search_tool.execute(query="test")

        # Verify get_lesson_link was called
        mock_vector_store.get_lesson_link.assert_called_once_with("Course", 3)

    def test_execute_without_lesson_number(self, search_tool, mock_vector_store):
        """Test formatting when lesson_number is None"""
        mock_results = SearchResults(
            documents=["Content without lesson"],
            metadata=[{"course_title": "Course", "lesson_number": None}],
            distances=[0.4],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_results)

        result = search_tool.execute(query="test")

        # Should have course title but not lesson info
        assert "Course" in result
        assert "Lesson" not in result

    def test_get_tool_definition(self, search_tool):
        """Test that tool definition is correctly structured"""
        definition = search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"

        # Check required fields
        assert "query" in definition["input_schema"]["required"]
        assert "course_name" not in definition["input_schema"]["required"]
        assert "lesson_number" not in definition["input_schema"]["required"]

        # Check properties
        props = definition["input_schema"]["properties"]
        assert "query" in props
        assert "course_name" in props
        assert "lesson_number" in props


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
