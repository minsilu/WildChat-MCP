# Overview
The MCP server will transform static notebook analysis into an interactive conversational interface, allowing Claude to dynamically query and analyze the WildChat dataset to answer complex questions about user-LLM interactions.

## Key Insight: Unlike Pyserini (which focuses on document retrieval), our MCP server needs to support:



## 数据清洗
保留哪些数据？
英语，
不同的model编号怎么处理？
是否要构建vector index?来支持相似度搜索
元数据？
模型发布时间？
In-memory indexes for fast querying:
Topic classification index (pre-computed or on-demand)
Temporal index (by timestamp)
Model-specific indexes

Conversation length buckets

Caching strategy: Pre-compute expensive operations (topic modeling, embeddings) and store results


Implementation Considerations
Pre-compute topic classifications (using LDA, BERTopic, or LLM-based classification)
Build inverted indexes for fast filtering
Cache frequent query results
Use sampling for very large result sets with extrapolation

Load data in chunks, not all at once
Use database (SQLite/DuckDB) instead of pure in-memory for 3.2M conversations
Lazy loading of conversation content (load summaries first, full text on demand)

Plugin architecture for new analysis methods
Easy to add new topic categories or classification schemes
Support for custom user-defined metrics

## Resources 设计 (Data 层)
Resources 是被动的数据源，用于提供“上下文”。

wildchat://conversation/{conversation_hash} (核心资源)
功能: 类似于 Pyserini 的 get_document。根据 ID 返回完整的、未经截断的 JSON 或 Markdown 格式的对话全文。
用途: Claude 在用 Tool 找到感兴趣的 ID 后，读取这个 Resource 来做深度文本分析（风格分析、准确性评估、情感分析）。

wildchat://stats/overview (静态资源)
功能: 返回数据集的元数据（总条数、包含的模型列表、时间跨度）。
用途: 让 Claude 在对话一开始就“心里有数”，知道自己在分析什么数据。

Resources (Read-only data exposures)

dataset://metadata
Dataset schema, available models, date ranges, language list


dataset://topics/taxonomy
Topic classification scheme and definitions

dataset://models/specs
Model family information, capabilities, release dates

## tool 设计
1. 核心设计理念: "Macro-Analytics, Micro-Inspection"
我们不应该只写一个“万能查询器”，而应该把能力拆分为三个层次，让 Claude 像一个数据科学家一样工作：

宏观层 (Macro Tools): 提供统计数据、聚合报表（对应你的 4 个 Insight）, 比如aggregate statistics, distributions, trends 
Multi-dimensional exploration - combining filters (model + time + topic + language, etc.)

发现层 (Discovery Tools): 根据宏观发现，查找具体的对话样本 ID（类似 Pyserini 的 search）。

微观层 (Resources): 调取单条对话的完整全文，进行深度定性分析（类似 Pyserini 的 get_document）。
Conversational retrieval - finding conversations by various criteria



4. Prompts 设计 (Guide 层)
这是为了展示你的 System 如何引导 LLM 进行复杂分析（Chain-of-Thought）。

@analyze_model_comparison
预设指令:
调用 get_engagement_metrics(group_by="model") 对比各模型的对话长度。
调用 get_topic_distribution(model="gpt-4") 和 (model="claude") 对比话题偏好。
使用 search_conversations 分别找出两个模型的典型对话。
读取 Resource 全文，分析其回答风格（Tone, Verbosity）的区别。
生成一份对比报告。

@investigate_spike (探索性分析)
预设指令: “请调用 get_temporal_trends 找出用户活跃度的峰值月份，然后使用 search_conversations 调查那个月大家都在问什么，并给出解释。”


### Meta-Analysis 
get_dataset_summary
Overall dataset statistics and health metrics
Parameters: summary_level (basic/detailed)
Returns: Counts, distributions, coverage statistics
Use case: "Give me an overview of the dataset"

generate_insights_prompt
Suggest interesting questions based on data patterns
Parameters: focus_area (models/topics/temporal/geographic)
Returns: List of suggested analytical questions
Use case: Help users discover what to explore

### 宏观分析工具 (Analytics Tools)
用于回答 "What", "How many", "Trends" 类问题

get_topic_distribution(model: str = None, start_date: str = None, end_date: str = None)
功能: 获取话题分布统计。
Insight 对应: Prompt Topic Distribution
灵活性: 支持按模型筛选（例如：“GPT-4 的话题分布和 GPT-3.5 有什么不同？”），支持时间范围（例如：“2024年之后大家还聊 Coding 吗？”）。
如果模型和时间都没有限制呢？
返回: JSON List [{"topic": "Coding", "count": 500, "percentage": 0.2}, ...]

get_top_topics(n: int) — return top N most frequent conversation categories.

get_engagement_metrics(group_by: str = "model", topic: str = None)
功能: 获取对话长度（turn_count）和参与度的统计信息（平均值、中位数）。
Statistics on conversation length (turns, tokens)
Returns: Distribution statistics, histograms data, correlations
Directly addresses: Conversation Length and Engagement question
Insight 对应: Conversation Length and Engagement & Model Comparison
灵活性: group_by 参数允许 Claude 自主决定是按“模型”对比，还是按“话题”对比（例如：“聊 Politics 的人是不是比聊 Coding 的人说话更多？”）。
返回: JSON List [{"group": "gpt-4", "avg_turns": 5.2}, {"group": "claude", "avg_turns": 8.1}]
get_model_stats(model_name: str) — summarize dataset statistics for a
given LLM (average length, sentiment, etc.).与之类似，需要实现情感分类吗？


get_temporal_trends(interval: str = "month", topic: str = None)
功能: 获取随时间变化的热度数据。
Insight 对应: Temporal Trends
灵活性: 可以看整体趋势，也可以只看特定 Topic 的趋势（例如：“O1 发布后，Reasoning 类话题的趋势图是怎样的？”）。
返回: Time-series JSON。
Track metrics over time (volume, avg turns, topic shifts)
Parameters: metric_type, time_granularity (daily/weekly/monthly), models, date_range
Returns: Time series data with annotations for major events
Directly addresses: Temporal Trends question


compare_models
Compare response characteristics across models
Parameters: models_list, comparison_dimensions (response_length, formality, structure, code_blocks, etc.)
Returns: Comparative statistics and examples
Directly addresses: Model Comparison question

### 发现与搜索工具 (Discovery Tools)
用于回答 "Show me examples", "Find conversations about X" 类问题
search_conversations(query: str, topic: str = None, model: str = None, limit: int = 5)
功能: 类似于 Pyserini 的 search。根据关键词或过滤条件，返回相关的 Conversation ID 和简短摘要。
目的: 当 Claude 发现“Coding 话题激增”时，它可以调用这个 tool 找几个具体的例子来看看大家到底在问什么代码。
返回: List of {"id": "hash_123", "summary": "User asks about python sort...", "model": "gpt-4"}

Search conversations by keyword, topic, or semantic similarity
Parameters: query, model, date_range, language, min_turns, max_results
Returns: Conversation summaries with metadata
Use case: "Find conversations about coding in GPT-4 from January 2025"
search_conversations(keyword: str, limit: int) — return sample
conversations containing specific topics or phrases.

get_conversation
Retrieve full conversation by conversation_hash or turn_identifier
Parameters: conversation_hash
Returns: Complete conversation with all metadata
Use case: Deep dive into specific interesting conversations

Find conversations matching interaction patterns (e.g., code-switching, multi-turn reasoning)
Parameters: pattern_type, model, limit
Returns: Conversations matching the pattern
Use case: "Show me conversations where users switched languages mid-conversation"

@mcp.tool()
def count_conversations(
    query: str = None,   # 支持按关键词查总数
    topic: str = None,   # 支持按话题查总数
    model: str = None    # 支持按模型查总数
) -> int:
与“推理”相关的话题有多少条？


### Advanced Insight Tools

analyze_user_behavior
Analyze patterns from hashed_ip + header combinations
Parameters: behavior_type (return_users, topic_consistency, session_patterns)
Returns: User engagement patterns, cohort analysis
Additional insight: User retention and behavior patterns



detect_conversation_anomalies
Find unusual conversations (very long, unusual patterns, rare topics)
Parameters: anomaly_type, threshold, model
Returns: Anomalous conversations with explanations
cross-model, and behavioral comparisons  


get_reasoning_insights (specialized for o1 models)
Analyze reasoning model conversations (o1-preview, o1-mini)
Parameters: comparison_with (other models), metric
Returns: Reasoning-specific patterns, problem complexity
Additional insight: How reasoning models differ



