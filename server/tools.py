import duckdb
import json
from typing import Dict, Any
import os
import sys
from typing import List, Optional, Literal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_FILE

# ================= Auxiliary Function =================
def get_db_connection():
    return duckdb.connect(DB_FILE, read_only=True)


def _build_filters(
    models: Optional[List[str]] = None, 
    topic: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    exclude_noise: bool = True
) -> tuple[str, list]:
    """
    Constructs WHERE clauses dynamically based on provided filters.
    Returns (sql_fragment, parameters_list).
    """
    conditions = []
    params = []

    if exclude_noise:
        conditions.append("topic != 'General / Noise'")
    
    if models:
        placeholders = ', '.join(['?'] * len(models))
        conditions.append(f"model_family IN ({placeholders})")
        params.extend(models)
    
    if topic:
        conditions.append("topic = ?")
        params.append(topic)
        
    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)
        
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params

# ================= Meta Summary Tools =================
def get_dataset_summary() -> str:
    """
    Retrieves high-level statistics about the WildChat dataset.
    Returns total counts, date ranges, and distributions for models, topics, and geography.
    Use this tool FIRST to understand the dataset's shape, scale, and coverage.
    
    Returns:
        JSON string with the following structure:
        {
          "Total Conversations": 1645032,
          "Date Range": "2023-04-01 to 2024-11-20",
          "Top Models": [{"name": "gpt-4", "count": 50000}, ...],
          "Top Topics": [{"name": "Coding", "count": 20000}, ...],
          "Top Countries": [{"name": "United States", "count": 10000}, ...]
        }
    """
    con = get_db_connection()
    try:
        query = """
            SELECT 
                total_count, 
                CAST(start_date AS VARCHAR) as start_date, 
                CAST(end_date AS VARCHAR) as end_date,
                model_json, 
                topic_json, 
                country_json 
            FROM dataset_meta
        """
        result = con.execute(query).fetchone()
        
        if not result:
            return "Error: Metadata not found. Please run the ingestion pipeline."

        total, start, end, model_str, topic_str, country_str = result
        
        stats = {
            "Total Conversations": total,
            "Date Range": f"{start} to {end}",
            "Top Models": json.loads(model_str),
            "Top Topics": json.loads(topic_str),
            "Top Countries": json.loads(country_str)
        }
        
        return json.dumps(stats, indent=2)
        
    except Exception as e:
        return f"Error retrieving summary: {str(e)}"
    finally:
        con.close()

def get_db_schema() -> str:
    """
    Returns the schema of the 'wildchat' table as a Markdown list.
    
    Use this to:
    1. Understand available columns for filtering (e.g., 'turn_count', 'country').
    2. Check valid data types before forming complex logic.
    
    Returns:
        Text string containing column names and types (e.g., "- timestamp (TIMESTAMP)").
    """
    con = get_db_connection()
    try:
        df = con.execute("DESCRIBE wildchat").fetchdf()
        
        schema_info = []
        for _, row in df.iterrows():
            schema_info.append(f"- {row['column_name']} ({row['column_type']})")
            
        return "Table 'wildchat' Schema:\n" + "\n".join(schema_info)
    except Exception as e:
        return f"Error getting schema: {str(e)}"
    finally:
        con.close()
        
# ================= Macro Analytics Tools =================
   
def get_topic_stats(
    models: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Analyzes the distribution of conversation topics.
    
    Args:
        models: List of model families.
                - If >1 models provided: Returns a SIDE-BY-SIDE comparison dictionary.
                - If 0 or 1 model provided: Returns AGGREGATE statistics.
        start_date: Filter start (YYYY-MM-DD).
        end_date: Filter end (YYYY-MM-DD).
        limit: Top N topics to return.
    Returns: 
        JSON string.
        [Mode A: Aggregate] (One or All models)
        {
            "mode": "aggregate",
            "filters": {...},
            "metadata": {"total_conversations": 1250},
            "topics": [
                {"topic": "Coding", "count": 500, "percentage": 40.0},
                {"topic": "Writing", "count": 300, "percentage": 24.0}
            ]
        }

        [Mode B: Comparison] (Multiple models specified)
        {
            "mode": "comparison",
            "filters": {...},
            "comparison": {
                "gpt-4": {
                    "total_conversations": 1000,
                    "data": [{"topic": "Coding", "count":...}, ...]
                },
                "o1": {
                    "total_conversations": 800,
                    "data": [{"topic": "Creative Writing", "count":...}, ...]
                }
            }
        }
    """
    con = get_db_connection()
    try:
        def _query_single_scope(model_list_filter: Optional[List[str]]):
            where_clause, params = _build_filters(
                models=model_list_filter, 
                start_date=start_date, 
                end_date=end_date
            )
            
            total_query = f"SELECT COUNT(*) FROM wildchat {where_clause}"
            total_count = con.execute(total_query, params).fetchone()[0]
            
            if total_count == 0:
                return {"total_conversations": 0, "data": []}

            query = f"""
                SELECT 
                    topic, 
                    COUNT(*) as count,
                    CAST(COUNT(*) * 100.0 / {total_count} AS DECIMAL(5,2)) as percentage
                FROM wildchat
                {where_clause}
                GROUP BY topic
                ORDER BY count DESC
                LIMIT ?
            """
            df = con.execute(query, params + [limit]).fetchdf()
            return {
                "total_conversations": int(total_count),
                "data": df.to_dict(orient='records')
            }


        if models and len(models) > 1:
            comparison_results = {}
            for m in models:
                stats = _query_single_scope([m])
                comparison_results[m] = stats
            
            return {
                "mode": "comparison",
                "filters": {"date": f"{start_date or 'Start'} to {end_date or 'Now'}"},
                "comparison": comparison_results
            }
            
        else:
            stats = _query_single_scope(models)
            
            return {
                "mode": "aggregate",
                "filters": {"models": models if models else "ALL"},
                "metadata": {"total_conversations": stats["total_conversations"]},
                "topics": stats["data"]
            }
        
    except Exception as e:
        return f"Error analyzing topics: {str(e)}"
    finally:
        con.close()

def get_engagement_stats(
    group_by: Literal["model", "topic"] = "model",
    target_models: Optional[List[str]] = None,
    target_topic: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Calculates engagement metrics (length, turns, verbosity) grouped by Model or Topic.
    Use this for 'Model Comparison' (group_by='model') or 'Topic Depth' (group_by='topic').
    
    Args:
        group_by: Dimension to compare ('model' or 'topic').
        target_models: If comparing models, specific ones to list (e.g. ['gpt-4', 'gpt-3.5', 'gpt-4o', 'o1']).
        target_topic: Filter analysis to a specific topic.
        limit: Max rows to return.
        
    Returns: 
            JSON string containing a LIST of dictionary records.
            Example:
            [
                {
                    "group_name": "gpt-4",
                    "total_convos": 1500,
                    "avg_turns": 12,
                    "median_turns": 8,
                    "avg_total_tokens": 4000,
                    "avg_tokens_per_turn": 333  # <--- Key Indicator for Verbosity/Style
                },
                ...
            ]
    """
    con = get_db_connection()
    try:
        group_col = "model_family" if group_by == "model" else "topic"
        
        where_clause, params = _build_filters(
            models=target_models, 
            topic=target_topic, 
            exclude_noise=True
        )
        
        query = f"""
            SELECT 
                {group_col} as group_name,
                COUNT(*) as total_convos,
                CAST(AVG(turn_count) AS INTEGER) as avg_turns,
                CAST(MEDIAN(turn_count) AS INTEGER) as median_turns,
                CAST(AVG(token_count) AS INTEGER) as avg_total_tokens,
                CAST(SUM(token_count) / SUM(turn_count) AS INTEGER) as avg_tokens_per_turn
            FROM wildchat
            {where_clause}
            GROUP BY {group_col}
            HAVING count(*) > 50 
            ORDER BY avg_total_tokens DESC
            LIMIT ?
        """
        query_params = params + [limit]
        df = con.execute(query, query_params).fetchdf()
    
        return df.to_dict(orient='records')
        
    except Exception as e:
        return f"Error calculating engagement: {str(e)}"
    finally:
        con.close()

def get_temporal_trends(
    interval: Literal["month", "week"] = "month",
    topic: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Retrieves time-series data for conversation volume over time.
    Can be filtered by specific topic or model to see their specific evolution.
    
    Args:
        interval: Time granularity ('month' or 'week').
        topic: Filter by specific topic.
        model: Filter by specific model.
    Returns:
        JSON string structured for line chart visualization.
        Structure:
        {
            "interval": "month",
            "filters": {...},
            "trend_data": [
                {
                    "period": "2023-04-01",  # Represents the start of the interval
                    "count": 1205
                },
                ...
            ]
        }    
    """
    con = get_db_connection()
    try:
        model_list = [model] if model else None
        where_clause, params = _build_filters(
            models=model_list, 
            topic=topic
        )

        query = f"""
            SELECT 
                date_trunc(?, timestamp) as period,
                COUNT(*) as count
            FROM wildchat
            {where_clause}
            GROUP BY period
            ORDER BY period
        """
        
        df = con.execute(query, [interval] + params).fetchdf()
        
        df['period'] = df['period'].astype(str)
        
        return {
            "interval": interval,
            "filters": {"topic": topic, "model": model},
            "trend_data": df.to_dict(orient='records')
        }
        
    except Exception as e:
        return f"Error analyzing trends: {str(e)}"
    finally:
        con.close()
        
# ================= Discovery Tools =================

def search_conversations(
    query: Optional[str] = None,
    topic: Optional[str] = None,
    model: Optional[str] = None,
    min_turns: Optional[int] = None,
    limit: int = 5
) -> str:
    """
    Search for conversations using keywords (BM25) OR filters (Topic/Model/Length).
    
    Args:
        query: Keyword string for semantic search (e.g. "python error").
        topic: Filter by specific topic category.
        model: Filter by model family (e.g. "gpt-4", "o1").
        min_turns: Minimum number of turns (useful for finding deep discussions).
        limit: Max results to return.

    Returns:
        JSON string containing a list of matches.
        Structure: [{"id": "...", "snippet": "...", "score": 1.5, "model_family": "..."}]
        
        IMPORTANT: The 'id' field is required to fetch the full content using `get_conversation_content`.
    """
    con = get_db_connection()
    try:
        model_list = [model] if model else None
        where_clause, params = _build_filters(model_list, topic, None, None)
        
        if query:
            # === Mode A: Semantic/Keyword Search (BM25) ===
            # We use the FTS index we built earlier. 
            # Note: We combine FTS scores with WHERE clause filters.
            
            metadata_filter = where_clause.replace("WHERE", "AND") if where_clause else ""
            
            sql = f"""
                SELECT 
                    id, 
                    model_family,
                    topic,
                    turn_count,
                    fts_main_wildchat.match_bm25(id, ?) AS score,
                    -- Extract a preview snippet (first 200 chars of search_text)
                    substr(search_text, 1, 200) as snippet
                FROM wildchat
                WHERE score IS NOT NULL
                {metadata_filter}
            """
            if min_turns:
                sql += f" AND turn_count >= {min_turns}"
            
            sql += " ORDER BY score DESC LIMIT ?"
            
            query_params = [query] + params + [limit]
            
        else:
            # === Mode B: Pure Metadata Filtering ===
            # No keyword provided, just looking for random examples matching criteria
            
            sql = f"""
                SELECT 
                    id, 
                    model_family, 
                    topic, 
                    turn_count,
                    0 as score,
                    substr(search_text, 1, 200) as snippet
                FROM wildchat
                {where_clause}
            """
            if min_turns:
                connector = "AND" if where_clause else "WHERE"
                sql += f" {connector} turn_count >= {min_turns}"
                
            sql += " ORDER BY timestamp DESC LIMIT ?"
            query_params = params + [limit]

        df = con.execute(sql, query_params).fetchdf()
        
        if df.empty:
            return "No conversations found matching criteria."
            
        return df.to_dict(orient='records')

    except Exception as e:
        return f"Error searching conversations: {str(e)}"
    finally:
        con.close()
             
def count_matches(
    query: Optional[str] = None,
    topic: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Counts the number of conversations matching specific criteria.Counts the total number of conversations matching specific criteria without returning them.
    Useful for quick validation before running a heavy analysis.
    
    Use case: 
    - Quick validation: "Are there enough examples of 'segfault' to analyze?"
    - Statistics: "How many conversations discuss 'election'?"
    
    Returns:
        A natural language string (e.g., "Found 12,450 matching conversations.")
    """
    con = get_db_connection()
    try:
        model_list = [model] if model else None
        where_clause, params = _build_filters(model_list, topic, None, None)
        
        if query:
            metadata_filter = where_clause.replace("WHERE", "AND") if where_clause else ""
            sql = f"""
                SELECT COUNT(*) 
                FROM wildchat 
                WHERE fts_main_wildchat.match_bm25(id, ?) IS NOT NULL
                {metadata_filter}
            """
            query_params = [query] + params
        else:
            sql = f"SELECT COUNT(*) FROM wildchat {where_clause}"
            query_params = params
            
        count = con.execute(sql, query_params).fetchone()[0]
        return f"Found {count} matching conversations."
        
    except Exception as e:
        return f"Error counting matches: {str(e)}"
    finally:
        con.close()

def analyze_user_behavior(
    behavior_type: Literal["power_users", "topic_consistency"] = "power_users",
    limit: int = 10
) -> str:
    """
    Analyzes user engagement patterns based on hashed IPs.
    
    Args:
        behavior_type:
            - 'power_users': Finds users with the most conversations and their favorite topics.
            - 'topic_consistency': Finds users who are "Specialists" (stick to 1 topic) vs "Generalists".
        limit: Max rows to return.

    Returns:
        JSON string.
        Example (power_users):
        [
            {
                "hashed_ip": "a1b2...",
                "total_convos": 150,
                "favorite_topic": "Coding",
                "avg_turns": 25
            }, ...
        ]
    """
    con = get_db_connection()
    try:
        base_filter = "topic IS NOT NULL AND topic != 'General / Noise'"
        if behavior_type == "power_users":
            query = f"""
                SELECT 
                    hashed_ip,
                    COUNT(*) as total_convos,
                    mode(topic) as favorite_topic, -- Most frequent topic
                    CAST(AVG(turn_count) AS INTEGER) as avg_turns
                FROM wildchat
                WHERE {base_filter}
                GROUP BY hashed_ip
                ORDER BY total_convos DESC
                LIMIT ?
            """
        else:
            # Identify "Specialists" 
            query = f"""
                SELECT 
                    hashed_ip,
                    COUNT(*) as total_convos,
                    COUNT(DISTINCT topic) as distinct_topics,
                    mode(topic) as main_interest
                FROM wildchat
                WHERE {base_filter}
                GROUP BY hashed_ip
                HAVING total_convos > 10 -- Only analyze recurring users
                ORDER BY (CAST(distinct_topics AS FLOAT) / total_convos) ASC -- Low ratio = Specialist
                LIMIT ?
            """
        
        df = con.execute(query, [limit]).fetchdf()
        return df.to_dict(orient='records')

    except Exception as e:
        return f"Error analyzing behavior: {str(e)}"
    finally:
        con.close()

def detect_conversation_anomalies(
    anomaly_type: Literal["length_outlier", "rare_topic"] = "length_outlier",
    model: Optional[str] = None,
    threshold: float = 10.0
) -> str:
    """
    Finds specific anomalous conversations for inspection.
    Use this to discover "Edge Cases" or potential jailbreaks/errors.

    Args:
        anomaly_type:
            - 'length_outlier': Finds conversations > 10x (threshold) the average length.
            - 'rare_topic': Finds conversations in topics that appear less than N times.
        model: Filter by model family (optional).
        threshold: Multiplier for length outliers (default 10.0x avg).

    Returns:
        JSON string list of Discovery Summaries (ID, Snippet, Reason).
        Structure:
        [
            {
                "id": "...", 
                "model_family": "...",
                "snippet": "...", 
                "metric_value": 150, 
                "avg_benchmark": 40 or topic: "Quantum Computing"
            }
        ]
        
        IMPORTANT: Use the 'id' to call `get_conversation_content` for deep inspection.
    """
    con = get_db_connection()
    try:
        model_list = [model] if model else None
        where_clause, params = _build_filters(model_list, None, None, None)
        
        if anomaly_type == "length_outlier":
            avg_query = f"SELECT AVG(turn_count) FROM wildchat {where_clause}"
            avg_turns = con.execute(avg_query, params).fetchone()[0] or 0
            
            # 2. Find Outliers
            target = avg_turns * threshold
            
            query = f"""
                SELECT 
                    id, 
                    model_family, 
                    turn_count as metric_value,
                    {int(avg_turns)} as avg_benchmark,
                    substr(search_text, 1, 100) as snippet
                FROM wildchat
                {where_clause} 
                {'AND' if where_clause else 'WHERE'} turn_count > ?
                ORDER BY turn_count DESC
                LIMIT 10
            """
            params.append(target)
            
        elif anomaly_type == "rare_topic":
            # Find topics with very few conversations (Potential hallucinations or niche attacks)
            query = f"""
                WITH RareTopics AS (
                    SELECT topic 
                    FROM wildchat 
                    GROUP BY topic 
                    HAVING COUNT(*) < 50
                )
                SELECT 
                    id, model_family, topic, substr(search_text, 1, 100) as snippet
                FROM wildchat
                WHERE topic IN (SELECT topic FROM RareTopics)
                LIMIT 10
            """
            
        else:
            return "Error: Unknown anomaly type."

        df = con.execute(query, params).fetchdf()
        
        if df.empty:
            return "No anomalies found with current thresholds."
            
        return df.to_dict(orient='records')

    except Exception as e:
        return f"Error detecting anomalies: {str(e)}"
    finally:
        con.close()

# ================= Micro retrieval Tool =================

def get_conversation_content(conversation_id: str) -> str:
    """
    Retrieves the FULL content of a specific conversation by ID.
    
    Args:
        conversation_id: The unique hash ID found via `search_conversations`.

    Returns:
        JSON string with the complete dialogue history.
        Structure: 
        {
            "id": "...",
            "metadata": {"model": "...", "topic": "...", "turn_count": ...},
            "search_text": "...",
            "conversation": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    """
    con = get_db_connection()
    try:
        result = con.execute(
            "SELECT search_text, full_content, model, topic FROM wildchat WHERE id = ?", 
            [conversation_id]
        ).fetchone()
        
        if not result:
            return "Error: Conversation ID not found."
            
        search_text, content_json, model, topic = result
        
        messages = json.loads(content_json)
        
        response = {
            "id": conversation_id,
            "metadata": {"model": model, "topic": topic, "turn_count": len(messages)},
            "search_text": search_text,
            "conversation": messages
        }
        
        return response
        
    except Exception as e:
        return f"Error retrieving conversation: {str(e)}"
    finally:
        con.close()
        
def run_sql_query(query: str) -> str:
    """
    Executes a raw SQL query against the WildChat database.
    
    Use this tool ONLY when other specialized tools (get_topic_stats, etc.) 
    cannot answer the specific analytical question.
    
    Constraints:
    - Connection is READ-ONLY.
    - Max rows returned: 20 (to save context window).
    - Max execution time: 5 seconds.
    
    Args:
        query: Valid DuckDB SQL string. 
               Example: "SELECT substring(search_text, 1, 50) FROM wildchat WHERE turn_count > 100 LIMIT 5"
    
    Returns:
        JSON string of the query result.
    """
    con = duckdb.connect(DB_FILE, read_only=True)
    
    try:
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
        if any(k in query.upper() for k in forbidden_keywords):
            return "Error: Write operations are strictly forbidden."

        df = con.execute(query).fetchdf()
        
        if len(df) > 20:
            df = df.head(20)
            warning = f"\n(Note: Result truncated. Showing top 20 of {len(df)} rows. Use LIMIT in SQL to refine.)"
        else:
            warning = ""
            
        return df.to_json(orient='records', date_format='iso') + warning

    except Exception as e:

        return f"SQL Execution Error: {str(e)}"
    finally:
        con.close()        

        
        
