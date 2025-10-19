"""
Real system test to diagnose the "Query failed" issue
This test runs against the actual system with real components
"""

import io
import os
import sys

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from rag_system import RAGSystem

print("=" * 70)
print("REAL SYSTEM DIAGNOSTIC TEST")
print("=" * 70)

# Initialize the real system
print("\n1. Initializing RAG system...")
try:
    config = Config()

    # Check if API key is set
    if not config.ANTHROPIC_API_KEY:
        print("✗ ANTHROPIC_API_KEY not set in environment")
        print("  Please set ANTHROPIC_API_KEY in your .env file")
        sys.exit(1)

    print(f"✓ API Key found: {config.ANTHROPIC_API_KEY[:10]}...")
    print(f"✓ Model: {config.ANTHROPIC_MODEL}")

    rag = RAGSystem(config)
    print("✓ RAG system initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize RAG system: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Check vector store
print("\n2. Checking vector store...")
try:
    course_count = rag.vector_store.get_course_count()
    print(f"✓ Found {course_count} courses in vector store")

    if course_count == 0:
        print(
            "  WARNING: No courses loaded. The system won't be able to answer content queries."
        )
    else:
        course_titles = rag.vector_store.get_existing_course_titles()
        print(
            f"  Courses: {', '.join(course_titles[:3])}{'...' if len(course_titles) > 3 else ''}"
        )
except Exception as e:
    print(f"✗ Error checking vector store: {e}")
    import traceback

    traceback.print_exc()

# Test tool manager
print("\n3. Checking tool manager...")
try:
    tool_defs = rag.tool_manager.get_tool_definitions()
    print(f"✓ {len(tool_defs)} tools registered")
    for tool_def in tool_defs:
        print(f"  - {tool_def['name']}: {tool_def['description'][:50]}...")
except Exception as e:
    print(f"✗ Error checking tools: {e}")
    import traceback

    traceback.print_exc()

# Test a simple search tool execution (without AI)
print("\n4. Testing search tool directly...")
try:
    # Manually execute search tool
    result = rag.tool_manager.execute_tool(
        "search_course_content", query="What is MCP?"
    )

    if "error" in result.lower() or "no" in result.lower()[:20]:
        print(f"✗ Search returned: {result[:200]}")
    else:
        print(f"✓ Search successful, returned {len(result)} characters")
        print(f"  Preview: {result[:150]}...")

    # Check if sources were captured
    sources = rag.tool_manager.get_last_sources()
    print(f"✓ {len(sources)} sources captured")
    if sources:
        print(f"  First source: {sources[0]}")

except Exception as e:
    print(f"✗ Search tool execution failed: {e}")
    import traceback

    traceback.print_exc()

# Test AI generator
print("\n5. Testing AI generator (without real API call)...")
try:
    # Check AI generator is properly configured
    print(f"✓ AI Generator model: {rag.ai_generator.model}")
    print(f"✓ Base params: {rag.ai_generator.base_params}")

    # Check system prompt
    system_prompt = rag.ai_generator.SYSTEM_PROMPT
    if "search_course_content" in system_prompt:
        print("✓ System prompt contains tool instructions")
    else:
        print("✗ System prompt missing tool instructions")

except Exception as e:
    print(f"✗ AI generator check failed: {e}")
    import traceback

    traceback.print_exc()

# Test a full query (this will make a real API call)
print("\n6. Testing full query flow...")
print("   NOTE: This will make a real API call to Anthropic")

try:
    import time

    # Test with a content query
    print("\n   Test query: 'What is MCP?'")
    start_time = time.time()

    response, sources = rag.query("What is MCP?")

    elapsed = time.time() - start_time

    print(f"\n   ✓ Query completed in {elapsed:.2f}s")
    print(f"   Response length: {len(response)} characters")
    print(f"   Sources returned: {len(sources)}")

    if not response or response.lower() == "query failed":
        print(f"   ✗ PROBLEM FOUND: Response is '{response}'")
    else:
        print(f"   ✓ Response: {response[:200]}...")

    if sources:
        print(f"   ✓ Sources:")
        for source in sources:
            print(f"      - {source}")
    else:
        print(f"   ⚠ No sources returned (may be normal for general knowledge)")

except Exception as e:
    print(f"   ✗ Query failed with exception: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 70)
