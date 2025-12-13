from mcp.server.fastmcp import FastMCP
import duckdb
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "wildchat.db")


mcp = FastMCP("wildchat")


@mcp.tool()
def get_total_count() -> str:
    """
    Check how many conversations are in the database.
    Useful for checking if the database is connected.
    """
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
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
        con = duckdb.connect(DB_PATH, read_only=True)

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