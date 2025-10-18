"""
Tests for AIGenerator tool-calling behavior
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


# Mock response classes to simulate Anthropic API responses
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


class TestAIGenerator:
    """Test suite for AIGenerator tool-calling behavior"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch('anthropic.Anthropic') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator with mocked client"""
        return AIGenerator(api_key="test-key", model="claude-test")

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test basic response generation without tool usage"""
        # Mock response without tool use
        mock_response = MockResponse(
            content=[MockTextBlock(text="This is a test response")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create = Mock(return_value=mock_response)

        result = ai_generator.generate_response(
            query="What is 2+2?",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )

        assert result == "This is a test response"

        # Verify API call was made correctly
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args is not None
        assert call_args[1]["messages"][0]["content"] == "What is 2+2?"
        assert "tools" not in call_args[1]

    def test_generate_response_with_conversation_history(self, ai_generator, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Response")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create = Mock(return_value=mock_response)

        history = "User: Previous question\nAssistant: Previous answer"
        ai_generator.generate_response(
            query="New question",
            conversation_history=history,
            tools=None,
            tool_manager=None
        )

        # Check that history was added to system prompt
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous question" in system_content
        assert "Previous answer" in system_content

    def test_generate_response_with_tools_but_no_tool_use(self, ai_generator, mock_anthropic_client):
        """Test response when tools are available but not used"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Direct answer without tools")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create = Mock(return_value=mock_response)

        tool_defs = [{
            "name": "search_course_content",
            "description": "Search for content",
            "input_schema": {"type": "object", "properties": {}}
        }]
        mock_tool_manager = Mock()

        result = ai_generator.generate_response(
            query="What is AI?",
            tools=tool_defs,
            tool_manager=mock_tool_manager
        )

        assert result == "Direct answer without tools"

        # Verify tools were provided in API call
        call_args = mock_anthropic_client.messages.create.call_args
        assert "tools" in call_args[1]
        assert call_args[1]["tools"] == tool_defs
        assert call_args[1]["tool_choice"] == {"type": "auto"}

        # Tool manager should not have been called
        mock_tool_manager.execute_tool.assert_not_called()

    def test_generate_response_with_tool_execution(self, ai_generator, mock_anthropic_client):
        """Test tool execution workflow"""
        # First response triggers tool use
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    type="tool_use",
                    name="search_course_content",
                    id="tool_123",
                    input={"query": "MCP basics", "course_name": "MCP"}
                )
            ],
            stop_reason="tool_use"
        )

        # Second response after tool execution
        final_response = MockResponse(
            content=[MockTextBlock(text="Based on the search, MCP stands for...")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(
            return_value="[MCP Course - Lesson 1]\nMCP is Model Context Protocol..."
        )

        tool_defs = [{"name": "search_course_content"}]

        result = ai_generator.generate_response(
            query="What is MCP?",
            tools=tool_defs,
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="MCP basics",
            course_name="MCP"
        )

        # Verify final response
        assert "Based on the search" in result

        # Verify two API calls were made
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_execution_message_sequence(self, ai_generator, mock_anthropic_client):
        """Test that tool execution creates correct message sequence"""
        tool_use_block = MockToolUseBlock(
            name="search_course_content",
            id="tool_456",
            input={"query": "test query"}
        )

        tool_use_response = MockResponse(
            content=[tool_use_block],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Final answer")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Tool result content")

        ai_generator.generate_response(
            query="Query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Check the second API call (after tool execution)
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args[1]["messages"]

        # Should have 3 messages: user query, assistant tool use, user tool result
        assert len(messages) == 3

        # First message: user query
        assert messages[0]["role"] == "user"

        # Second message: assistant with tool use
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"][0].type == "tool_use"

        # Third message: user with tool results
        assert messages[2]["role"] == "user"
        tool_results = messages[2]["content"]
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_456"
        assert tool_results[0]["content"] == "Tool result content"

    def test_multiple_tool_calls(self, ai_generator, mock_anthropic_client):
        """Test handling multiple tool calls in one response"""
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_1",
                    input={"query": "query1"}
                ),
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_2",
                    input={"query": "query2"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Combined answer")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(
            side_effect=["Result 1", "Result 2"]
        )

        ai_generator.generate_response(
            query="Query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Both tools should be executed
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_api_parameters(self, ai_generator, mock_anthropic_client):
        """Test that correct API parameters are used"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Response")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create = Mock(return_value=mock_response)

        ai_generator.generate_response(query="Test query")

        call_args = mock_anthropic_client.messages.create.call_args[1]

        # Verify base parameters
        assert call_args["model"] == "claude-test"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800

    def test_system_prompt_structure(self, ai_generator, mock_anthropic_client):
        """Test that system prompt contains expected instructions"""
        mock_response = MockResponse(
            content=[MockTextBlock(text="Response")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create = Mock(return_value=mock_response)

        ai_generator.generate_response(query="Test")

        call_args = mock_anthropic_client.messages.create.call_args[1]
        system_prompt = call_args["system"]

        # Check for key elements in system prompt
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        # Updated to check for multi-round capability
        assert "TWO times per query" in system_prompt or "up to TWO" in system_prompt

    def test_tool_execution_without_tool_manager(self, ai_generator, mock_anthropic_client):
        """Test that tool use without tool_manager returns text response"""
        # Response that wants to use tools
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content",
                    id="tool_999",
                    input={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        mock_anthropic_client.messages.create = Mock(return_value=tool_use_response)

        # Call without tool_manager
        result = ai_generator.generate_response(
            query="Query",
            tools=[{"name": "search_course_content"}],
            tool_manager=None
        )

        # Should return empty string since there's no text block
        # (This tests edge case handling)
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
