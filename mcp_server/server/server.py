from fastmcp import FastMCP
import duckdb
import os
import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import DB_FILE
import tools
import prompts
import resources

mcp = FastMCP("wildchat")

# meta analytics tools
mcp.add_tool(tools.get_dataset_summary)
mcp.add_tool(tools.get_db_schema)

# macro analytics tools
mcp.add_tool(tools.get_topic_stats)
mcp.add_tool(tools.get_engagement_stats)
mcp.add_tool(tools.get_temporal_trends)

# discovery tools
mcp.add_tool(tools.search_conversations)
mcp.add_tool(tools.count_matches)
mcp.add_tool(tools.analyze_user_behavior)
mcp.add_tool(tools.detect_conversation_anomalies)

# micro retrieval tool
mcp.add_tool(tools.get_conversation_content)
mcp.add_tool(tools.run_sql_query)

@mcp.prompt("analyze-wildchat")
def analyze_wildchat(focus: str = "general") -> str:
    """
    Returns a system prompt to guide the LLM in analyzing the WildChat dataset.
    Args:
        focus: 'general', 'models', 'topics', or 'temporal'
    """
    return prompts.analyze_wildchat_prompt(focus)

@mcp.prompt("audit-conversation")
def audit_conversation(conversation_id: str) -> str:
    """
    Start a deep-dive audit on a specific conversation ID.
    Use this when you have an ID and want to check for safety/quality issues.
    """
    return prompts.audit_conversation_prompt(conversation_id)

@mcp.resource("wildchat://info/schema")
def resource_schema() -> str:
    """The database schema definition."""
    return resources.get_resource_content("wildchat://info/schema")

@mcp.resource("wildchat://info/summary")
def resource_summary() -> str:
    """High-level dataset statistics (counts, top models, dates)."""
    return resources.get_resource_content("wildchat://info/summary")

@mcp.resource("wildchat://conversations/{id}")
def conversation_resource(id: str) -> str:
    """
    Direct access to a full conversation log.
    """
    return resources.get_resource_content(f"wildchat://conversations/{id}")



if __name__ == "__main__":

    print("Starting WildChat MCP Server...")
    mcp.run(transport='stdio')