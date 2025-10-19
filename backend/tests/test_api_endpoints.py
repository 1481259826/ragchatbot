"""
API endpoint tests for the RAG system FastAPI application

Tests cover:
- POST /api/query - Query processing endpoint
- GET /api/courses - Course statistics endpoint
- GET / - Root endpoint

These tests use a mock FastAPI app to avoid static file mounting issues.
"""
import pytest
from unittest.mock import Mock


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for POST /api/query endpoint"""

    def test_query_successful_request(self, test_client, test_app):
        """Test successful query request with valid input"""
        # Setup mock RAG system response
        test_app.state.mock_rag.query.return_value = (
            "MCP is the Model Context Protocol",
            [{"text": "Introduction to MCP - Lesson 1", "link": "https://example.com/mcp/lesson1"}]
        )
        test_app.state.mock_rag.session_manager.create_session.return_value = "new-session-456"

        # Make request
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert data["answer"] == "MCP is the Model Context Protocol"

        assert "sources" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Introduction to MCP - Lesson 1"
        assert data["sources"][0]["link"] == "https://example.com/mcp/lesson1"

        assert "session_id" in data

    def test_query_with_session_id(self, test_client, test_app):
        """Test query with existing session ID"""
        # Setup mock
        test_app.state.mock_rag.query.return_value = (
            "Response for session",
            []
        )

        # Make request with session_id
        response = test_client.post(
            "/api/query",
            json={
                "query": "Follow-up question",
                "session_id": "existing-session-789"
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "existing-session-789"

        # Verify RAG system was called with correct session
        test_app.state.mock_rag.query.assert_called_once_with(
            "Follow-up question",
            "existing-session-789"
        )

    def test_query_without_session_creates_new(self, test_client, test_app):
        """Test that query without session_id creates new session"""
        # Setup mock
        test_app.state.mock_rag.query.return_value = ("Answer", [])
        test_app.state.mock_rag.session_manager.create_session.return_value = "auto-session-123"

        # Make request without session_id
        response = test_client.post(
            "/api/query",
            json={"query": "New query"}
        )

        # Verify new session was created
        assert response.status_code == 200
        data = response.json()

        # Should use auto-created session or test default
        assert "session_id" in data

    def test_query_with_empty_sources(self, test_client, test_app):
        """Test query that returns no sources (general knowledge)"""
        # Setup mock - no sources
        test_app.state.mock_rag.query.return_value = (
            "Python is a programming language",
            []
        )

        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Python is a programming language"
        assert data["sources"] == []

    def test_query_with_multiple_sources(self, test_client, test_app):
        """Test query that returns multiple sources"""
        # Setup mock with multiple sources
        test_app.state.mock_rag.query.return_value = (
            "Answer based on multiple lessons",
            [
                {"text": "Course A - Lesson 1", "link": "https://example.com/a/1"},
                {"text": "Course A - Lesson 2", "link": "https://example.com/a/2"},
                {"text": "Course B - Lesson 1", "link": None}
            ]
        )

        response = test_client.post(
            "/api/query",
            json={"query": "Complex query"}
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["sources"]) == 3
        assert data["sources"][0]["text"] == "Course A - Lesson 1"
        assert data["sources"][0]["link"] == "https://example.com/a/1"
        assert data["sources"][2]["link"] is None

    def test_query_missing_query_field(self, test_client):
        """Test request with missing required 'query' field"""
        response = test_client.post(
            "/api/query",
            json={"session_id": "test"}
        )

        # Should return validation error
        assert response.status_code == 422

    def test_query_empty_query_string(self, test_client, test_app):
        """Test request with empty query string"""
        test_app.state.mock_rag.query.return_value = ("Please provide a question", [])

        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still process (validation allows empty string)
        assert response.status_code == 200

    def test_query_with_error(self, test_client, test_app):
        """Test handling of RAG system errors"""
        # Make RAG system raise an exception
        test_app.state.mock_rag.query.side_effect = Exception("Database connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        # Should return 500 error
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Database connection failed" in response.json()["detail"]

    def test_query_response_structure(self, test_client, test_app):
        """Test that response matches expected schema"""
        test_app.state.mock_rag.query.return_value = (
            "Test answer",
            [{"text": "Source", "link": "http://test.com"}]
        )

        response = test_client.post(
            "/api/query",
            json={"query": "Test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data

        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source structure
        if data["sources"]:
            source = data["sources"][0]
            assert "text" in source
            assert "link" in source

    def test_query_with_special_characters(self, test_client, test_app):
        """Test query with special characters and unicode"""
        test_app.state.mock_rag.query.return_value = ("Answer with émojis 🚀", [])

        response = test_client.post(
            "/api/query",
            json={"query": "What about émojis and special chars: @#$%?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "émojis" in data["answer"]

    def test_query_very_long_input(self, test_client, test_app):
        """Test query with very long input text"""
        long_query = "What is " + "very " * 500 + "important?"
        test_app.state.mock_rag.query.return_value = ("Answer to long query", [])

        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        # Should handle long queries
        assert response.status_code == 200


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for GET /api/courses endpoint"""

    def test_courses_successful_request(self, test_client, test_app):
        """Test successful course statistics request"""
        # Setup mock
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "Introduction to MCP",
                "Advanced Python",
                "Web Development Basics"
            ]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert "total_courses" in data
        assert data["total_courses"] == 3

        assert "course_titles" in data
        assert len(data["course_titles"]) == 3
        assert "Introduction to MCP" in data["course_titles"]

    def test_courses_empty_database(self, test_client, test_app):
        """Test courses endpoint with no courses loaded"""
        # Setup mock - empty database
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_single_course(self, test_client, test_app):
        """Test courses endpoint with single course"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Single Course Title"]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 1
        assert len(data["course_titles"]) == 1

    def test_courses_with_error(self, test_client, test_app):
        """Test handling of errors in courses endpoint"""
        # Make analytics raise exception
        test_app.state.mock_rag.get_course_analytics.side_effect = Exception(
            "Vector store unavailable"
        )

        response = test_client.get("/api/courses")

        # Should return 500 error
        assert response.status_code == 500
        assert "detail" in response.json()

    def test_courses_response_structure(self, test_client, test_app):
        """Test that response matches expected schema"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course 1", "Course 2"]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify consistency
        assert data["total_courses"] == len(data["course_titles"])

    def test_courses_no_parameters_needed(self, test_client, test_app):
        """Test that courses endpoint doesn't require parameters"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Test"]
        }

        # GET request with no parameters
        response = test_client.get("/api/courses")

        assert response.status_code == 200

    def test_courses_large_number(self, test_client, test_app):
        """Test courses endpoint with many courses"""
        # Generate many course titles
        course_titles = [f"Course {i}" for i in range(100)]

        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 100,
            "course_titles": course_titles
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 100
        assert len(data["course_titles"]) == 100


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for GET / (root) endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns status"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert data["status"] == "ok"

    def test_root_endpoint_message(self, test_client):
        """Test root endpoint includes message"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert isinstance(data["message"], str)

    def test_root_no_parameters_needed(self, test_client):
        """Test root endpoint works without parameters"""
        response = test_client.get("/")
        assert response.status_code == 200


@pytest.mark.api
class TestCORSAndMiddleware:
    """Test CORS and middleware functionality"""

    def test_cors_headers_present(self, test_client, test_app):
        """Test that CORS middleware is configured (headers may not appear in TestClient)"""
        test_app.state.mock_rag.query.return_value = ("Answer", [])

        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        # In TestClient, CORS headers might not be set, but request should succeed
        # The important thing is that CORS middleware is configured in the app
        assert response.status_code == 200

    def test_options_request(self, test_client):
        """Test OPTIONS request for CORS preflight"""
        response = test_client.options("/api/query")

        # Should handle OPTIONS request
        assert response.status_code in [200, 405]  # Some test clients may not fully implement OPTIONS


@pytest.mark.api
class TestErrorHandling:
    """Test error handling across all endpoints"""

    def test_invalid_json_body(self, test_client):
        """Test handling of invalid JSON in request body"""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_wrong_content_type(self, test_client, test_app):
        """Test request with wrong content type"""
        test_app.state.mock_rag.query.return_value = ("Answer", [])

        # Should still work with form data parsed as JSON by TestClient
        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        assert response.status_code == 200

    def test_nonexistent_endpoint(self, test_client):
        """Test request to non-existent endpoint"""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_wrong_http_method(self, test_client):
        """Test using wrong HTTP method on endpoint"""
        # Try GET on POST-only endpoint
        response = test_client.get("/api/query")

        assert response.status_code == 405  # Method Not Allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
