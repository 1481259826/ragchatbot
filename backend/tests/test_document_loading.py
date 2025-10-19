"""
Test document loading to diagnose why courses aren't in vector store
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
print("DOCUMENT LOADING TEST")
print("=" * 70)

# Initialize system
config = Config()
rag = RAGSystem(config)

print("\n1. Checking initial state...")
course_count = rag.vector_store.get_course_count()
print(f"   Courses in DB before loading: {course_count}")

if course_count > 0:
    titles = rag.vector_store.get_existing_course_titles()
    print(f"   Existing courses: {titles}")

# Check docs directory
print("\n2. Checking docs directory...")
docs_path = "../docs"
full_path = os.path.abspath(docs_path)
print(f"   Looking for docs at: {full_path}")
print(f"   Exists: {os.path.exists(docs_path)}")

if os.path.exists(docs_path):
    files = os.listdir(docs_path)
    print(f"   Files found: {len(files)}")
    for f in files:
        file_path = os.path.join(docs_path, f)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            print(f"      - {f} ({size} bytes)")

# Try loading documents
print("\n3. Attempting to load documents...")
try:
    courses_added, chunks_added = rag.add_course_folder(docs_path, clear_existing=False)
    print(f"   ✓ Loaded {courses_added} courses with {chunks_added} chunks")
except Exception as e:
    print(f"   ✗ Error loading documents: {e}")
    import traceback

    traceback.print_exc()

# Check final state
print("\n4. Checking final state...")
course_count = rag.vector_store.get_course_count()
print(f"   Courses in DB after loading: {course_count}")

if course_count > 0:
    titles = rag.vector_store.get_existing_course_titles()
    print(f"   Courses: {titles}")

    # Test a search
    print("\n5. Testing search...")
    from vector_store import SearchResults

    results = rag.vector_store.search("MCP", limit=2)

    if results.error:
        print(f"   ✗ Search error: {results.error}")
    elif results.is_empty():
        print(f"   No results found")
    else:
        print(f"   ✓ Found {len(results.documents)} results")
        for i, (doc, meta) in enumerate(zip(results.documents, results.metadata)):
            print(f"      Result {i+1}: {meta.get('course_title')} - {doc[:100]}...")

print("\n" + "=" * 70)
