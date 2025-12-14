from fastmcp import FastMCP
import duckdb
import json
import os
import sys
import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_FILE

def get_resource_content(uri: str) -> str:
    """
    Handler for wildchat://conversations/{id}
    """
    try:
        if uri == "wildchat://info/schema":
            return tools.get_db_schema()
        
        elif uri == "wildchat://info/summary":
            return tools.get_dataset_summary()
        
        elif uri.startswith("wildchat://conversations/"):
            conv_id = uri.split("/")[-1]

            con = duckdb.connect(DB_FILE, read_only=True)
            result = con.execute("SELECT full_content FROM wildchat WHERE id = ?", [conv_id]).fetchone()
            con.close()
            
            if result:
                return result[0]
            else:
                return json.dumps({"error": "Not found"})
            
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    except Exception as e:
        return json.dumps({"error": str(e)})