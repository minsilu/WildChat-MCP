import duckdb
import json
import os
import sys


# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_FILE

def generate_metadata():
    print(f"Connecting to database: {DB_FILE}...")
    con = duckdb.connect(DB_FILE)
    print("Generating Metadata Table (Pre-computing statistics)...")
    
    con.execute("DROP TABLE IF EXISTS dataset_meta")
 
    con.execute("""
        CREATE TABLE dataset_meta AS 
        WITH 
        -- 1. basic stats
        basic_stats AS (
            SELECT 
                COUNT(*) as total_count,
                MIN(timestamp) as start_date,
                MAX(timestamp) as end_date
            FROM wildchat
        ),
        -- 2. model distribution (Top 10) -> JSON
        model_dist AS (
            SELECT to_json(list(struct_pack(name := model_family, count := cnt))) as model_json
            FROM (
                SELECT model_family, COUNT(*) as cnt 
                FROM wildchat 
                GROUP BY model_family 
                ORDER BY cnt DESC 
                LIMIT 10
            )
        ),
        -- 3. topic distribution (Top 10) -> JSON
        topic_dist AS (
            SELECT to_json(list(struct_pack(name := topic, count := cnt))) as topic_json
            FROM (
                SELECT topic, COUNT(*) as cnt 
                FROM wildchat 
                WHERE topic IS NOT NULL AND topic != 'General / Noise'
                GROUP BY topic 
                ORDER BY cnt DESC 
                LIMIT 10
            )
        ),
        -- 4. geographic distribution (Top 10) -> JSON
        geo_dist AS (
            SELECT to_json(list(struct_pack(name := country, count := cnt))) as country_json
            FROM (
                SELECT country, COUNT(*) as cnt 
                FROM wildchat 
                WHERE country IS NOT NULL
                GROUP BY country 
                ORDER BY cnt DESC 
                LIMIT 10
            )
        )

        -- 5. merge all stats into one row
        SELECT 
            b.total_count,
            b.start_date,
            b.end_date,
            m.model_json,
            t.topic_json,
            g.country_json
        FROM basic_stats b, model_dist m, topic_dist t, geo_dist g
    """)
    
    print("\nVerification:")
    row = con.execute("SELECT * FROM dataset_meta").fetchone()
    
    cols = ["total_count", "start_date", "end_date", "model_json", "topic_json", "country_json"]
    result = dict(zip(cols, row))

    print(f"Total Count: {result['total_count']}")
    print(f"Date Range:  {result['start_date']} to {result['end_date']}")
    print("-" * 40)
    print("Model Distribution (JSON):")
    print(json.dumps(json.loads(result['model_json']), indent=2))
    print("-" * 40)
    print("Topic Distribution (JSON):")
    print(json.dumps(json.loads(result['topic_json']), indent=2))
    print("-" * 40)
    print("Geographic Distribution (JSON):")
    print(json.dumps(json.loads(result['country_json']), indent=2))
    con.close()
    print("\nDone!")