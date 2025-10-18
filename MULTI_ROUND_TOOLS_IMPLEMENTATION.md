# Multi-Round Sequential Tool Calling Implementation

## 概述

成功实施了方案 1（循环式设计），支持 Claude 在不同的 API 轮次中进行最多 2 次顺序工具调用。

## 实施的更改

### 1. 配置更新 (`backend/config.py`)

**添加:**
```python
# Tool execution settings
MAX_TOOL_ROUNDS: int = 2     # Maximum sequential tool calls per query
```

**用途:** 配置每个查询允许的最大工具调用轮次。

---

### 2. 核心实现 (`backend/ai_generator.py`)

#### 新方法: `_execute_tool_rounds()`

实现了支持多轮工具执行的主要逻辑：

**特性:**
- 最多支持 2 轮工具调用
- 在所有轮次中保留工具定义（Claude 需要理解 tool_result）
- 消息历史在轮次间累积
- 3 个终止条件：
  1. 达到最大轮次（2 轮）
  2. Claude 返回 `stop_reason="end_turn"`（自然终止）
  3. 工具执行失败（快速失败）

**工作流程:**
```
第 1 轮:
  → Claude 请求工具
  → 执行工具
  → 添加结果到消息
  → 进行第 2 轮 API 调用（包含工具）

第 2 轮（如果需要）:
  → Claude 可以：
     a) 直接回答（stop_reason="end_turn"）→ 返回答案
     b) 再次请求工具（stop_reason="tool_use"）→ 执行并强制最终调用

最终调用（如果第 2 轮请求工具）:
  → 执行第 2 轮工具
  → 进行最终 API 调用（不包含工具）
  → 返回答案
```

#### 更新: `generate_response()`

**更改前:**
```python
if response.stop_reason == "tool_use" and tool_manager:
    return self._handle_tool_execution(response, api_params, tool_manager)
```

**更改后:**
```python
if response.stop_reason == "tool_use" and tool_manager:
    # Use new multi-round tool execution (supports up to MAX_TOOL_ROUNDS)
    return self._execute_tool_rounds(response, api_params, tool_manager, max_rounds=2)
```

#### 保留的遗留方法

`_handle_tool_execution()` 被标记为 DEPRECATED 但保留用于向后兼容。

#### 改进的错误处理

添加了防御性检查以处理边缘情况：
```python
# Try to extract text, handle cases where first block might not have text
for block in response.content:
    if hasattr(block, 'text'):
        return block.text
return ""  # Fallback
```

---

### 3. 系统提示更新 (`backend/ai_generator.py`)

**添加的指导:**

```
Tool Usage Guidelines:
- **Multi-part questions**: You may use tools up to TWO times per query if needed
  - Example: "What is X and Y?" → Search for X, then search for Y if needed
  - Example: "Compare topic A in course X with course Y" → Search course X, then search course Y
  - Prioritize efficiency: Use one search if possible
- **Tool independence**: Each tool call should gather distinct, complementary information
```

**目的:**
- 告知 Claude 多轮能力
- 鼓励高效的工具使用
- 提供多步骤推理的示例

---

### 4. 测试 (`backend/tests/test_multi_round_tools.py`)

**创建了 9 个综合测试:**

| 测试 | 验证内容 |
|------|---------|
| `test_single_round_early_termination` | Claude 在 1 次搜索后可以停止 |
| `test_full_two_rounds` | 完整的 2 轮工具执行 |
| `test_tool_failure_round_1` | 第 1 轮工具失败的优雅处理 |
| `test_max_rounds_reached_with_tool_use` | 达到最大轮次时的行为 |
| `test_message_history_accumulates` | 消息历史正确增长 |
| `test_tools_included_in_all_rounds` | 工具在中间轮次中包含 |
| `test_no_tools_in_final_call_after_max_rounds` | 最大轮次后的最终调用无工具 |
| `test_empty_tool_results_handled` | 空工具结果的处理 |
| `test_different_tools_in_sequence` | 顺序使用不同工具 |

**测试结果:** ✅ 9/9 通过

#### 更新的现有测试

**`test_ai_generator.py`:**
- 更新了 `test_system_prompt_structure` 以检查新的多轮指导
- 改进了 `test_tool_execution_without_tool_manager` 的边缘情况处理

**总测试覆盖率:** ✅ 46/46 测试通过

---

## 架构设计决策

### 工具可用性策略

**决策:** 在所有轮次中保留工具

**原因:**
1. Claude 需要工具定义来理解 `tool_result` 消息
2. 允许 Claude 自主决定何时停止使用工具
3. 支持自然的提前终止（如果 1 次搜索足够）

**实现:**
```python
if not is_last_round:
    # Still have rounds left - provide tools
    next_params["tools"] = base_params.get("tools", [])
    next_params["tool_choice"] = {"type": "auto"}
```

### 消息历史管理

**策略:** 完整累积

每轮添加：
- 1 条 assistant 消息（包含 tool_use）
- 1 条 user 消息（包含 tool_result）

**示例流程:**
```python
# 初始
messages = [{"role": "user", "content": "query"}]

# 第 1 轮后
messages = [
    {"role": "user", "content": "query"},
    {"role": "assistant", "content": [tool_use_block]},
    {"role": "user", "content": [tool_result]}
]

# 第 2 轮后
messages = [
    {"role": "user", "content": "query"},
    {"role": "assistant", "content": [tool_use_1]},
    {"role": "user", "content": [tool_result_1]},
    {"role": "assistant", "content": [tool_use_2]},
    {"role": "user", "content": [tool_result_2]}
]
```

### 终止条件

| 条件 | 检查位置 | 行为 |
|------|---------|------|
| **第 2 轮达到** | 轮次开始 | 执行工具，不在下次调用中提供工具 |
| **无 tool_use** | API 响应后 | 立即返回文本响应 |
| **工具失败** | 工具执行期间 | 添加错误，进行最终调用，返回错误感知响应 |

---

## 使用示例

### 示例 1: 单部分查询（早期终止）

**用户:** "What is MCP?"

**执行流程:**
```
初始 API 调用 → tool_use (search "MCP")
第 1 轮: 执行搜索 → 返回结果
第 2 轮 API 调用 → end_turn（直接回答）
返回: "MCP is Model Context Protocol..."
```

**轮次:** 1 次工具调用
**API 调用:** 2 次（初始 + 第 2 轮）

---

### 示例 2: 多部分查询（完整 2 轮）

**用户:** "What is MCP and what are the prerequisites?"

**执行流程:**
```
初始 API 调用 → tool_use (search "MCP introduction")
第 1 轮: 执行搜索 → 返回 MCP 信息
第 2 轮 API 调用 → tool_use (search "prerequisites")
第 2 轮: 执行搜索 → 返回先决条件
最终 API 调用（无工具）→ end_turn
返回: "MCP is... Prerequisites include..."
```

**轮次:** 2 次工具调用
**API 调用:** 3 次（初始 + 第 2 轮 + 最终）

---

### 示例 3: 比较查询

**用户:** "Compare prompt caching in the MCP course with the Computer Use course"

**执行流程:**
```
初始 → tool_use (search "prompt caching" in "MCP")
第 1 轮: 搜索 MCP 课程 → 找到 MCP 缓存信息
第 2 轮 → tool_use (search "prompt caching" in "Computer Use")
第 2 轮: 搜索 Computer Use 课程 → 找到其缓存信息
最终 → 综合两个来源的答案
```

**轮次:** 2 次工具调用
**结果:** 来自两个不同课程的综合比较

---

## 性能影响

### 延迟

**当前（1 轮）:**
- 初始 API: ~800ms
- 工具执行: ~200ms
- 最终 API: ~800ms
- **总计: ~1.8 秒**

**新（2 轮，最坏情况）:**
- 初始 API: ~800ms
- 第 1 轮工具 + API: ~1000ms
- 第 2 轮工具 + API: ~1000ms
- 最终 API: ~800ms
- **总计: ~3.6 秒**

**平均情况（提前终止）:**
- ~2.0 秒（仅比当前慢一点）

### 成本

**Claude Haiku 4.5 定价:**
- 输入: $1 / 1M 令牌
- 输出: $5 / 1M 令牌

**每个查询（2 轮）:**
- 输入令牌: ~3,500 → $0.0035
- 输出令牌: ~500 → $0.0025
- **总计: ~$0.006**

**与 1 轮比较:**
- 1 轮: ~$0.004
- 2 轮: ~$0.006
- **增加: +50%**

**规模成本:**
- 1,000 查询/天: $6/天 vs $4/天（+$2/天）
- 对于显著更好的答案来说是可接受的增长

---

## 向后兼容性

✅ **完全兼容**

- 现有代码无需更改
- 现有测试已更新但仍通过
- `_handle_tool_execution()` 保留用于回退
- 通过默认参数支持单轮行为

---

## 回滚策略

如果出现问题：

1. **立即:** 在 `generate_response()` 中恢复到 `_handle_tool_execution()`
2. **或:** 将 `max_rounds=2` 更改为 `max_rounds=1`（等同于旧行为）

---

## 监控建议

跟踪以下指标：

| 指标 | 目的 | 警报阈值 |
|------|------|---------|
| `avg_tool_rounds_per_query` | 工具使用模式 | > 1.5（过多使用） |
| `queries_with_2_rounds` | 功能使用 | 跟踪百分比 |
| `tool_failure_rate` | 系统健康 | > 5% |
| `avg_query_latency` | 性能 | > 4 秒 |

---

## 未来增强

潜在改进：

1. **自适应轮次限制** - 根据查询复杂度学习最佳轮次
2. **并行工具执行** - 在同一轮中执行多个工具
3. **工具结果缓存** - 缓存常见搜索
4. **动态工具可用性** - 每轮提供不同工具
5. **流式响应** - 流式传输最终响应

---

## 文件更改总结

**修改的文件:**
- `backend/config.py` - 添加 MAX_TOOL_ROUNDS
- `backend/ai_generator.py` - 实现多轮逻辑 + 更新系统提示
- `backend/tests/test_ai_generator.py` - 更新 2 个测试

**新文件:**
- `backend/tests/test_multi_round_tools.py` - 9 个新测试

**未更改:**
- `backend/rag_system.py` - 无更改
- `backend/search_tools.py` - 无更改
- `backend/vector_store.py` - 无更改
- 所有其他文件

---

## 测试总结

**总测试:** 46
**通过:** 46 ✅
**失败:** 0

**测试分解:**
- CourseSearchTool: 13/13 ✅
- AIGenerator: 9/9 ✅
- RAG 集成: 10/10 ✅
- 去重: 5/5 ✅
- **多轮工具: 9/9 ✅**

---

## 手动测试建议

建议测试以下查询类型：

### 1. 单部分查询
- "What is MCP?"
- "Show me the course outline for Computer Use"

**预期:** 1 次工具调用

### 2. 多部分查询
- "What is MCP and what are the prerequisites?"
- "Tell me about lesson 1 and lesson 2 of the MCP course"

**预期:** 可能 1-2 次工具调用

### 3. 比较查询
- "Compare prompt caching in MCP with Computer Use"
- "What topics are covered in both courses?"

**预期:** 2 次工具调用（每个课程一次）

### 4. 结构 + 内容查询
- "What lessons are in the MCP course and what does lesson 3 cover?"

**预期:** 2 次工具调用（outline + search）

---

## 结论

方案 1（循环式设计）已成功实施，具有：

✅ 简单直观的实现
✅ 全面的测试覆盖（46/46 通过）
✅ 向后兼容
✅ 清晰的文档
✅ 合理的性能权衡

系统现在可以处理需要多次搜索的复杂查询，同时对简单查询保持高效。
