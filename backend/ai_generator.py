import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content**: Search for specific course content with optional course/lesson filters
2. **get_course_outline**: Retrieve course outline showing course name, link, and complete lesson list

Tool Usage Guidelines:
- **Course outline/structure queries**: Use get_course_outline tool
- **Specific content queries**: Use search_course_content tool
- **Multi-part questions**: You may use tools up to TWO times per query if needed
  - Example: "What is X and Y?" → Search for X, then search for Y if needed
  - Example: "Compare topic A in course X with course Y" → Search course X, then search course Y
  - Prioritize efficiency: Use one search if possible
- **Tool independence**: Each tool call should gather distinct, complementary information
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline questions** (e.g., "What lessons are in X?", "Show me the course structure"): Use get_course_outline
- **Course content questions**: Use search_course_content first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

When presenting course outlines:
- Include course name and link
- List all lessons with their numbers and titles
- Include lesson links when available

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str, base_url: str = None):
        # Create client with optional base_url
        if base_url:
            self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            # Use new multi-round tool execution (supports up to MAX_TOOL_ROUNDS)
            return self._execute_tool_rounds(response, api_params, tool_manager, max_rounds=2)

        # Return direct response
        # Try to extract text, handle cases where first block might not have text
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text

        # Fallback if no text block found
        return ""
    
    def _execute_tool_rounds(self, initial_response, base_params: Dict[str, Any], tool_manager, max_rounds: int = 2):
        """
        Execute up to max_rounds of sequential tool calls with Claude.

        Args:
            initial_response: The first response containing tool_use
            base_params: Base API parameters (contains messages, system, tools)
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool execution rounds (default 2)

        Returns:
            Final response text after all tool rounds
        """
        # Initialize tracking
        current_round = 0
        messages = base_params["messages"].copy()  # Start with initial user message
        current_response = initial_response

        # LOOP: Execute up to max_rounds
        while current_round < max_rounds:
            current_round += 1

            # STEP 1: Add assistant's tool_use response to messages
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })

            # STEP 2: Execute all tool calls in this response
            tool_results = []
            tool_execution_failed = False

            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result
                        })
                    except Exception as e:
                        # Tool execution failed - terminate immediately
                        tool_execution_failed = True
                        error_msg = f"Tool execution failed: {str(e)}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": error_msg,
                            "is_error": True
                        })
                        break

            # TERMINATION CHECK 1: Tool execution failed
            if tool_execution_failed:
                # Add error results to messages
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                # Make final call WITHOUT tools to get error-aware response
                final_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"]
                    # NO tools parameter
                }
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text

            # STEP 3: Add tool results to messages
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # STEP 4: Determine if this is the last round
            is_last_round = (current_round >= max_rounds)

            # STEP 5: Make next API call
            # Tools available if NOT last round
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }

            if not is_last_round:
                # Still have rounds left - provide tools
                next_params["tools"] = base_params.get("tools", [])
                next_params["tool_choice"] = {"type": "auto"}
            # else: No tools - forces final response

            # Make API call
            current_response = self.client.messages.create(**next_params)

            # TERMINATION CHECK 2: No tool_use in response
            if current_response.stop_reason != "tool_use":
                # Claude chose to answer directly - we're done
                return current_response.content[0].text

            # TERMINATION CHECK 3: Last round reached
            if is_last_round:
                # At max_rounds and Claude wants to use tools
                # Execute final tool calls then make one more call without tools
                messages.append({
                    "role": "assistant",
                    "content": current_response.content
                })

                # Execute the final tool calls
                final_tool_results = []
                for content_block in current_response.content:
                    if content_block.type == "tool_use":
                        try:
                            tool_result = tool_manager.execute_tool(
                                content_block.name,
                                **content_block.input
                            )
                            final_tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": tool_result
                            })
                        except Exception as e:
                            # Tool failed on last round - include error
                            final_tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": f"Tool execution failed: {str(e)}",
                                "is_error": True
                            })

                if final_tool_results:
                    messages.append({"role": "user", "content": final_tool_results})

                # Final call without tools
                final_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"]
                }
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text

        # Should never reach here, but safety fallback
        return "Error: Maximum rounds exceeded without proper termination"

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        DEPRECATED: Legacy single-round tool execution for backward compatibility.
        Use _execute_tool_rounds() instead.

        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name,
                    **content_block.input
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }

        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text