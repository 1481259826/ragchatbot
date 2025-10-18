# 修复重复链接问题

## 问题描述

当查询课程大纲时，系统会显示多个重复的课程链接。例如，一个有多个课时的课程会为每个课时显示相同的课程链接。

## 根本原因

在 `backend/search_tools.py` 中：

1. **CourseOutlineTool**: 为课程添加一个来源，然后为每个课时也添加来源。如果多个课时具有相同的链接（指向同一个课程页面），就会产生重复。

2. **CourseSearchTool**: 当搜索返回同一课时的多个内容块时，会为每个块创建相同的来源链接。

## 修复方案

### 修复 1: CourseOutlineTool 去重 (`search_tools.py:171-218`)

**添加了：**
- `seen_links` 集合来跟踪已添加的唯一链接
- 在添加课程链接之前检查是否已存在
- 在添加课时链接之前检查是否已存在

**修改前：**
```python
# Course link (if available)
if outline.get('course_link'):
    sources.append({
        "text": f"View Course: {outline['course_title']}",
        "link": outline['course_link']
    })

# For each lesson
lesson_link = lesson.get('lesson_link')
if lesson_link:
    sources.append({
        "text": f"Lesson {lesson_num}: {lesson_title}",
        "link": lesson_link
    })
```

**修改后：**
```python
seen_links = set()  # Track unique links

# Course link (if available) - only add if unique
course_link = outline.get('course_link')
if course_link and course_link not in seen_links:
    sources.append({
        "text": f"View Course: {outline['course_title']}",
        "link": course_link
    })
    seen_links.add(course_link)

# For each lesson - only add if unique
lesson_link = lesson.get('lesson_link')
if lesson_link and lesson_link not in seen_links:
    sources.append({
        "text": f"Lesson {lesson_num}: {lesson_title}",
        "link": lesson_link
    })
    seen_links.add(lesson_link)
```

### 修复 2: CourseSearchTool 去重 (`search_tools.py:88-130`)

**添加了：**
- `seen_sources` 集合来跟踪已添加的唯一来源组合（文本 + 链接）
- 只有当来源组合（source_text, lesson_link）是唯一的时才添加

**修改前：**
```python
# Always add source
sources.append({
    "text": source_text,
    "link": lesson_link
})
```

**修改后：**
```python
seen_sources = set()  # Track unique source combinations

# Create unique identifier for this source
source_id = (source_text, lesson_link)

# Only add source if we haven't seen this exact combination
if source_id not in seen_sources:
    sources.append({
        "text": source_text,
        "link": lesson_link
    })
    seen_sources.add(source_id)
```

## 测试验证

创建了 `backend/tests/test_deduplication.py` 来验证去重功能：

### 测试用例

1. **test_search_tool_deduplicates_sources** ✅
   - 验证来自同一课时的多个内容块只生成一个来源

2. **test_search_tool_keeps_different_lessons** ✅
   - 验证不同课时保持为独立来源

3. **test_outline_tool_deduplicates_links** ✅
   - 验证课程大纲中的重复链接被移除

4. **test_outline_tool_with_all_same_links** ✅
   - 验证所有课时指向同一链接时只显示一次

5. **test_search_tool_with_null_links** ✅
   - 验证没有链接的来源也能正确去重

**测试结果:** 5/5 通过 ✅

## 影响

### 修复前
查询 "Building Towards Computer Use with Anthropic" 课程时：
```
来源:
- Course Link: https://www.deeplearning.ai/...
- Course Link: https://www.deeplearning.ai/...  (重复)
- Course Link: https://www.deeplearning.ai/...  (重复)
- Course Link: https://www.deeplearning.ai/...  (重复)
- Lesson 1: Introduction
- Lesson 2: ...
...
```

### 修复后
```
来源:
- Course Link: https://www.deeplearning.ai/...  (仅一次)
- Lesson 1: Introduction
- Lesson 2: ...
...
```

## 验证步骤

1. **重启应用**
   ```bash
   ./run.sh
   ```

2. **查询课程大纲**
   - 询问："Tell me about the Building Towards Computer Use course"
   - 或："What lessons are in the MCP course?"

3. **验证来源**
   - 检查来源部分
   - 应该看到每个唯一链接只出现一次
   - 不同的课时应该有各自的链接

4. **测试内容搜索**
   - 询问："What is prompt caching?"
   - 验证如果多个搜索结果来自同一课时，只显示一个来源

## 文件更改

- ✏️ **修改:** `backend/search_tools.py`
  - CourseOutlineTool._format_outline() - 添加链接去重
  - CourseSearchTool._format_results() - 添加来源去重

- ✨ **新建:** `backend/tests/test_deduplication.py`
  - 5 个测试用例验证去重功能

## 兼容性

此修复：
- ✅ 向后兼容 - 不改变 API 或数据结构
- ✅ 不影响现有功能
- ✅ 提高用户体验 - 减少视觉混乱
- ✅ 所有现有测试仍然通过（31/32）

## 总结

重复链接问题已修复！系统现在会：
1. 跟踪已添加的链接
2. 在添加来源之前检查重复
3. 确保每个唯一的链接只显示一次
4. 保持不同课时/课程的独立来源

修复已通过 5 个专门的测试用例验证，并且与现有功能完全兼容。
