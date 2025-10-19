"""
Tests for multi-round sequential tool calling in AIGenerator
"""

import os
import sys
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


# Mock response classes
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


class TestMultiRoundToolCalling:
    """Test suite for multi-round sequential tool calling"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch("anthropic.Anthropic") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator with mocked client"""
        return AIGenerator(api_key="test-key", model="claude-test")

    def test_single_round_early_termination(self, ai_generator, mock_anthropic_client):
        """Test that Claude can stop after 1 tool call"""
        # Round 1: tool_use
        round1_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t1", input={"query": "test"}
                )
            ],
            stop_reason="tool_use",
        )

        # Round 2: end_turn (Claude provides answer directly)
        round2_response = MockResponse(
            content=[MockTextBlock(text="Here's the answer from one search")],
            stop_reason="end_turn",
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Search result")

        result = ai_generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify only 1 tool execution
        assert mock_tool_manager.execute_tool.call_count == 1
        assert result == "Here's the answer from one search"

        # Verify 2 API calls (initial + round 2)
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_full_two_rounds(self, ai_generator, mock_anthropic_client):
        """Test 2 sequential tool calls"""
        # Initial: tool_use
        round1_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t1", input={"query": "X"}
                )
            ],
            stop_reason="tool_use",
        )

        # Round 2: tool_use again
        round2_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t2", input={"query": "Y"}
                )
            ],
            stop_reason="tool_use",
        )

        # Final: end_turn
        final_response = MockResponse(
            content=[MockTextBlock(text="Combined answer from both searches")],
            stop_reason="end_turn",
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        result = ai_generator.generate_response(
            query="What is X and Y?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify 2 tool executions
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Combined answer from both searches"

        # Verify 3 API calls (initial + round 2 + final)
        assert mock_anthropic_client.messages.create.call_count == 3

    def test_tool_failure_round_1(self, ai_generator, mock_anthropic_client):
        """Test graceful handling of tool failure in round 1"""
        round1_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t1", input={"query": "test"}
                )
            ],
            stop_reason="tool_use",
        )

        # Error-aware final response
        error_response = MockResponse(
            content=[
                MockTextBlock(
                    text="I encountered an error searching for that information"
                )
            ],
            stop_reason="end_turn",
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            error_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Database error")

        result = ai_generator.generate_response(
            query="Test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should get error-aware response
        assert "error" in result.lower()

        # Should have made 2 API calls (initial + error response)
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_max_rounds_reached_with_tool_use(
        self, ai_generator, mock_anthropic_client
    ):
        """Test behavior when max rounds reached but Claude wants more tools"""
        # Round 1: tool_use
        round1_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t1", input={"query": "X"}
                )
            ],
            stop_reason="tool_use",
        )

        # Round 2: tool_use (max rounds reached here)
        round2_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t2", input={"query": "Y"}
                )
            ],
            stop_reason="tool_use",
        )

        # Final: forced response without tools
        final_response = MockResponse(
            content=[MockTextBlock(text="Answer based on available results")],
            stop_reason="end_turn",
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        result = ai_generator.generate_response(
            query="Multi-part question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should execute both tools
        assert mock_tool_manager.execute_tool.call_count == 2

        # Should get final response
        assert result == "Answer based on available results"

    def test_message_history_accumulates(self, ai_generator, mock_anthropic_client):
        """Test that message history grows correctly across rounds"""
        round1_response = MockResponse(
            content=[MockToolUseBlock(name="search", id="t1", input={})],
            stop_reason="tool_use",
        )

        round2_response = MockResponse(
            content=[MockTextBlock(text="Done")], stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        ai_generator.generate_response(
            query="Test", tools=[{"name": "search"}], tool_manager=mock_tool_manager
        )

        # Check round 2 API call
        second_call = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        # Should have: user query + assistant tool_use + user tool_result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_tools_included_in_all_rounds(self, ai_generator, mock_anthropic_client):
        """Test that tools parameter is included in intermediate rounds"""
        round1_response = MockResponse(
            content=[MockToolUseBlock(name="search", id="t1", input={})],
            stop_reason="tool_use",
        )

        round2_response = MockResponse(
            content=[MockTextBlock(text="Done")], stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        ai_generator.generate_response(
            query="Test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Check that round 2 (not final) includes tools
        second_call = mock_anthropic_client.messages.create.call_args_list[1]
        assert "tools" in second_call[1]
        assert second_call[1]["tools"] == [{"name": "search_course_content"}]

    def test_no_tools_in_final_call_after_max_rounds(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that final call after max rounds has no tools"""
        round1_response = MockResponse(
            content=[MockToolUseBlock(name="search", id="t1", input={})],
            stop_reason="tool_use",
        )

        round2_response = MockResponse(
            content=[MockToolUseBlock(name="search", id="t2", input={})],
            stop_reason="tool_use",  # Still wants tools at max
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Forced final answer")], stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        ai_generator.generate_response(
            query="Test", tools=[{"name": "search"}], tool_manager=mock_tool_manager
        )

        # Check final call (3rd call) has no tools
        final_call = mock_anthropic_client.messages.create.call_args_list[2]
        assert "tools" not in final_call[1] or final_call[1].get("tools") is None

    def test_empty_tool_results_handled(self, ai_generator, mock_anthropic_client):
        """Test handling of empty tool results"""
        round1_response = MockResponse(
            content=[MockToolUseBlock(name="search", id="t1", input={})],
            stop_reason="tool_use",
        )

        round2_response = MockResponse(
            content=[MockTextBlock(text="No results found")], stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = ""  # Empty result

        result = ai_generator.generate_response(
            query="Test", tools=[{"name": "search"}], tool_manager=mock_tool_manager
        )

        assert result == "No results found"

    def test_different_tools_in_sequence(self, ai_generator, mock_anthropic_client):
        """Test using different tools in sequence"""
        round1_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="get_course_outline", id="t1", input={"course_name": "X"}
                )
            ],
            stop_reason="tool_use",
        )

        round2_response = MockResponse(
            content=[
                MockToolUseBlock(
                    name="search_course_content", id="t2", input={"query": "Y"}
                )
            ],
            stop_reason="tool_use",
        )

        final_response = MockResponse(
            content=[MockTextBlock(text="Combined info from outline and search")],
            stop_reason="end_turn",
        )

        mock_anthropic_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Outline", "Search results"]

        result = ai_generator.generate_response(
            query="Test",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify both tools were called
        calls = mock_tool_manager.execute_tool.call_args_list
        assert calls[0][0][0] == "get_course_outline"
        assert calls[1][0][0] == "search_course_content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
