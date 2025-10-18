"""
Test deduplication of sources in search results and course outlines
"""
import pytest
import sys
import os
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool, CourseOutlineTool
from vector_store import SearchResults


class TestSourceDeduplication:
    """Test that duplicate sources are removed"""

    def test_search_tool_deduplicates_sources(self):
        """Test that CourseSearchTool removes duplicate sources"""
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)

        # Mock search results with multiple chunks from the same lesson
        mock_results = SearchResults(
            documents=[
                "Content chunk 1 from lesson 1",
                "Content chunk 2 from lesson 1",
                "Content chunk 3 from lesson 1"
            ],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1},
                {"course_title": "Test Course", "lesson_number": 1},
                {"course_title": "Test Course", "lesson_number": 1}
            ],
            distances=[0.1, 0.2, 0.3],
            error=None
        )
        mock_store.search = Mock(return_value=mock_results)
        mock_store.get_lesson_link = Mock(return_value="http://example.com/lesson1")

        # Execute search
        result = tool.execute(query="test query")

        # Verify only ONE source was stored (despite 3 results)
        assert len(tool.last_sources) == 1, f"Expected 1 source, got {len(tool.last_sources)}"
        assert tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert tool.last_sources[0]["link"] == "http://example.com/lesson1"

    def test_search_tool_keeps_different_lessons(self):
        """Test that different lessons are kept as separate sources"""
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)

        # Mock search results from different lessons
        mock_results = SearchResults(
            documents=[
                "Lesson 1 content",
                "Lesson 2 content",
                "Lesson 1 content again"
            ],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1},
                {"course_title": "Test Course", "lesson_number": 2},
                {"course_title": "Test Course", "lesson_number": 1}
            ],
            distances=[0.1, 0.2, 0.3],
            error=None
        )
        mock_store.search = Mock(return_value=mock_results)
        mock_store.get_lesson_link = Mock(
            side_effect=lambda course, lesson: f"http://example.com/lesson{lesson}"
        )

        # Execute search
        result = tool.execute(query="test query")

        # Should have 2 unique sources (lesson 1 and lesson 2)
        assert len(tool.last_sources) == 2, f"Expected 2 sources, got {len(tool.last_sources)}"

        # Verify both lessons are present
        source_texts = [s["text"] for s in tool.last_sources]
        assert "Test Course - Lesson 1" in source_texts
        assert "Test Course - Lesson 2" in source_texts

    def test_outline_tool_deduplicates_links(self):
        """Test that CourseOutlineTool removes duplicate links"""
        mock_store = Mock()
        tool = CourseOutlineTool(mock_store)

        # Mock course outline with some lessons having the same link
        outline = {
            'course_title': 'Test Course',
            'course_link': 'http://example.com/course',
            'instructor': 'Test Instructor',
            'lessons': [
                {
                    'lesson_number': 1,
                    'lesson_title': 'Introduction',
                    'lesson_link': 'http://example.com/lesson1'
                },
                {
                    'lesson_number': 2,
                    'lesson_title': 'Basics',
                    'lesson_link': 'http://example.com/lesson2'
                },
                {
                    'lesson_number': 3,
                    'lesson_title': 'Advanced',
                    'lesson_link': 'http://example.com/lesson1'  # Duplicate link!
                }
            ]
        }

        mock_store.get_course_outline = Mock(return_value=outline)

        # Execute outline retrieval
        result = tool.execute(course_name="Test Course")

        # Should have 3 sources: 1 course link + 2 unique lesson links
        assert len(tool.last_sources) == 3, f"Expected 3 sources, got {len(tool.last_sources)}"

        # Check that links are unique
        links = [s["link"] for s in tool.last_sources]
        unique_links = set(links)
        assert len(links) == len(unique_links), "Found duplicate links in sources"

        # Verify the correct links are present
        assert 'http://example.com/course' in links
        assert 'http://example.com/lesson1' in links
        assert 'http://example.com/lesson2' in links

    def test_outline_tool_with_all_same_links(self):
        """Test outline when all lessons have the same link"""
        mock_store = Mock()
        tool = CourseOutlineTool(mock_store)

        # Mock course outline where all lessons point to the same URL
        same_link = 'http://example.com/course'
        outline = {
            'course_title': 'Test Course',
            'course_link': same_link,
            'instructor': 'Test Instructor',
            'lessons': [
                {
                    'lesson_number': 1,
                    'lesson_title': 'Lesson 1',
                    'lesson_link': same_link
                },
                {
                    'lesson_number': 2,
                    'lesson_title': 'Lesson 2',
                    'lesson_link': same_link
                },
                {
                    'lesson_number': 3,
                    'lesson_title': 'Lesson 3',
                    'lesson_link': same_link
                }
            ]
        }

        mock_store.get_course_outline = Mock(return_value=outline)

        # Execute outline retrieval
        result = tool.execute(course_name="Test Course")

        # Should have only 1 source (all links are the same)
        assert len(tool.last_sources) == 1, f"Expected 1 source, got {len(tool.last_sources)}"
        assert tool.last_sources[0]["link"] == same_link

    def test_search_tool_with_null_links(self):
        """Test that sources with null links are still deduplicated by text"""
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)

        # Mock results with no links
        mock_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course", "lesson_number": 1},
                {"course_title": "Course", "lesson_number": 1}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        mock_store.search = Mock(return_value=mock_results)
        mock_store.get_lesson_link = Mock(return_value=None)

        # Execute search
        result = tool.execute(query="test")

        # Should deduplicate based on source text even without links
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Course - Lesson 1"
        assert tool.last_sources[0]["link"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
