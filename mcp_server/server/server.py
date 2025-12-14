from fastmcp import FastMCP
import duckdb
import os
import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import DB_FILE
import tools
import prompts

mcp = FastMCP("wildchat")

# meta analytics tools
mcp.add_tool(tools.get_dataset_summary)
mcp.add_tool(tools.get_db_schema)

# macro analytics tools
mcp.add_tool(tools.get_topic_stats)
mcp.add_tool(tools.get_engagement_stats)
mcp.add_tool(tools.get_temporal_trends)


@mcp.prompt("analyze-wildchat")
def analyze_wildchat(focus: str = "general") -> str:
    """
    Returns a system prompt to guide the LLM in analyzing the WildChat dataset.
    Args:
        focus: 'general', 'models', 'topics', or 'temporal'
    """
    return prompts.analyze_wildchat_prompt(focus)

@mcp.tool()
def get_total_count() -> str:
    """
    Check how many conversations are in the database.
    Useful for checking if the database is connected.
    """
    try:
        con = duckdb.connect(DB_FILE, read_only=True)
        count = con.execute("SELECT COUNT(*) FROM wildchat").fetchone()[0]
        con.close()
        return f"Database connected! Total conversations: {count}"
    except Exception as e:
        return f"Error connecting to DB: {str(e)}"

@mcp.tool()
def get_sample_prompt(model_name: str) -> str:
    """
    Get one recent user prompt for a specific model.
    Args:
        model_name: e.g., 'gpt-4', 'gpt-3.5-turbo'
    """
    try:
        con = duckdb.connect(DB_FILE, read_only=True)

        result = con.execute("""
            SELECT user_prompt, timestamp 
            FROM wildchat 
            WHERE model = ? 
            LIMIT 1
        """, [model_name]).fetchone()
        
        con.close()
        
        if result:
            return f"Found a prompt for {model_name} from {result[1]}:\n\n'{result[0]}'"
        else:
            return f"No prompts found for model: {model_name}"
            
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":

    print("Starting WildChat MCP Server...")
    mcp.run()