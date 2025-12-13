import duckdb
import pandas as pd
import json
from datetime import datetime
from datasets import load_dataset

# ================= CONFIGURATION =================

DB_FILE = "wildchat.db"
HF_DATASET = "allenai/WildChat-4.8M"
BATCH_SIZE = 10000 

# TODO: Set to True to process only the first 5000 rows for testing
DEBUG_MODE = True

# ================= MAPPING LOGIC =================

# Model Map
MODEL_META_MAP = {
    # GPT-4 Family
    "gpt-4":                   {"family": "gpt-4",   "date": "2023-03-14"},
    "gpt-4-0314":              {"family": "gpt-4",   "date": "2023-03-14"},
    "gpt-4-0613":              {"family": "gpt-4",   "date": "2023-06-13"},
    "gpt-4-1106-preview":      {"family": "gpt-4",   "date": "2023-11-06"},
    "gpt-4-0125-preview":      {"family": "gpt-4",   "date": "2024-01-25"},
    "gpt-4-turbo":             {"family": "gpt-4",   "date": "2024-04-09"},
    "gpt-4-turbo-2024-04-09":  {"family": "gpt-4",   "date": "2024-04-09"},
    "gpt-4o":                  {"family": "gpt-4o",  "date": "2024-05-13"},
    "gpt-4o-2024-05-13":       {"family": "gpt-4o",  "date": "2024-05-13"},
    "gpt-4o-mini":             {"family": "gpt-4o",  "date": "2024-07-18"},
    
    # GPT-3.5 Family
    "gpt-3.5-turbo":           {"family": "gpt-3.5", "date": "2022-11-30"},
    "gpt-3.5-turbo-0301":      {"family": "gpt-3.5", "date": "2023-03-01"},
    "gpt-3.5-turbo-0613":      {"family": "gpt-3.5", "date": "2023-06-13"},
    "gpt-3.5-turbo-1106":      {"family": "gpt-3.5", "date": "2023-11-06"},
    "gpt-3.5-turbo-0125":      {"family": "gpt-3.5", "date": "2024-01-25"},
    "text-davinci-002-render-sha": {"family": "gpt-3.5", "date": "2022-11-30"},
    
    # O1 Family
    "o1-preview":              {"family": "o1",      "date": "2024-09-12"},
    "o1-mini":                 {"family": "o1",      "date": "2024-09-12"}
}

# Default metadata for unknown models
DEFAULT_META = {"family": "other", "date": None}


# 2. Simple Keyword-based Topic Classifier
TOPIC_KEYWORDS = {
    "Coding & Debugging": ["python", "java", "code", "error", "bug", "sql", "api", "function", "script", "html", "css", "react", "node"],
    "Math & Logic": ["calculate", "solve", "math", "equation", "proof", "logic", "probability", "geometry", "calculus", "algebra"],
    "Creative Writing": ["write", "story", "poem", "essay", "script", "lyrics", "novel", "fiction", "character", "plot"],
    "Academic & Research": ["thesis", "research", "citation", "summary", "paper", "article", "bibliography", "study", "analysis"],
    "Roleplay & Simulation": ["act as", "pretend", "you are a", "simulation", "dungeon", "game", "character"],
    "Translation & Lang": ["translate", "english to", "spanish", "chinese", "grammar", "vocabulary", "language"],
    "Advice & Life": ["advice", "help me", "suggestion", "tip", "relationship", "gift", "idea", "plan"]
}
## TODO: we need more comprehensive topic classification later

def process_record(record):
    """
    Process a single record: clean, normalize, and calculate metrics.
    Returns: A dictionary representing the cleaned row, or None if filtered out.
    """
    
    if record.get('language') != 'English': 
        return None
    
    raw_model = record.get('model', 'unknown')
    meta = MODEL_META_MAP.get(raw_model, DEFAULT_META)
    family = meta["family"]
    release_date = meta["date"] # 'YYYY-MM-DD' or None
    
    raw_timestamp = record.get('timestamp')
    dt = None
    if raw_timestamp:
        try:
            dt = pd.to_datetime(raw_timestamp)
        except:
            pass
            
    convs = record.get('conversation', [])
    
    user_texts = [t['content'] for t in convs if t['role'] == 'user' and t.get('content')]
    search_text = "\n".join(user_texts)
    
    first_turn = user_texts[0][:200] if user_texts else ""
    
    # Token Count (Rule of thumb: 4 chars ~= 1 token)
    total_len = sum(len(t.get('content', '')) for t in convs if t.get('content'))
    token_est = int(total_len / 4)
    
    assigned_topic = "General"
    search_lower = search_text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(k in search_lower for k in keywords):
            assigned_topic = topic
            break # Stop after the first match to save time
            
    return {
        "id": record.get('conversation_hash'),
        "model": raw_model,                
        "model_release_date": release_date,
        "model_family": family,
        "timestamp": dt,
        "year": dt.year if dt else None,
        "month": dt.month if dt else None,
        "day": dt.day if dt else None,
        "hour": dt.hour if dt else None,
        "hashed_ip": record.get('hashed_ip'),
        "country": record.get('country'),
        "state": record.get('state'),      
        "turn_count": record.get('turn'),
        "token_count": token_est,
        "topic": assigned_topic,
        "search_text": search_text,  # For ILIKE search queries
        "first_turn": first_turn,    # For list display
        "full_content": json.dumps(convs)  # Stored as JSON string for retrieval
    }

def ingest_pipeline():
    print(f"Connecting to DuckDB: {DB_FILE}...")
    con = duckdb.connect(DB_FILE)
    
    # Initialize Table Schema
    con.execute("DROP TABLE IF EXISTS wildchat")
    con.execute("""
        CREATE TABLE wildchat (
            id VARCHAR,
            model VARCHAR, 
            model_release_date DATE,
            model_family VARCHAR,
            timestamp TIMESTAMP,
            year INTEGER, 
            month INTEGER, 
            day INTEGER, 
            hour INTEGER,
            hashed_ip VARCHAR, 
            country VARCHAR,
            state VARCHAR,
            turn_count INTEGER, 
            token_count INTEGER, 
            topic VARCHAR,
            search_text VARCHAR, 
            first_turn VARCHAR, 
            full_content VARCHAR
        )
    """)
    
    print(f"Loading dataset from Hugging Face: {HF_DATASET} (Streaming Mode)...")
    
    ds = load_dataset(HF_DATASET, split="train", streaming=True)
    
    batch = []
    total_processed = 0
    total_inserted = 0
    
    print("Start processing pipeline...")
    
    for record in ds:
        row = process_record(record)
        
        if row:
            batch.append(row)
            
        total_processed += 1
        
        # Batch Insert (Write to DB every BATCH_SIZE rows)
        if len(batch) >= BATCH_SIZE:
            df = pd.DataFrame(batch)
            con.execute("INSERT INTO wildchat SELECT * FROM df")
            total_inserted += len(batch)
            batch = [] 
            print(f"Processed: {total_processed}, Inserted: {total_inserted}")
            
        # Debugging exit condition
        if DEBUG_MODE and total_processed >= 5000:
            print("Debug limit reached. Stopping.")
            break

    if batch:
        df = pd.DataFrame(batch)
        con.execute("INSERT INTO wildchat SELECT * FROM df")
        total_inserted += len(batch)
        
    print(f"\nTotal Processed: {total_processed}")
    print(f"Total Inserted: {total_inserted}")
    
    # Build Indexes (Performance Optimization)
    print("Building Indexes (This may take a moment)...")
    con.execute("CREATE INDEX idx_search ON wildchat(search_text)")
    con.execute("CREATE INDEX idx_topic ON wildchat(topic)")
    con.execute("CREATE INDEX idx_model ON wildchat(model_family)")
    con.execute("CREATE INDEX idx_model_release_date ON wildchat(model_release_date)")
    con.execute("CREATE INDEX idx_time ON wildchat(timestamp)")
    
    # Generate Metadata Table (Pre-computation for fast stats)
    print("Generating Metadata Table...")
    con.execute("DROP TABLE IF EXISTS dataset_meta")
    con.execute("""
        CREATE TABLE dataset_meta AS 
        SELECT 
            COUNT(*) as total_count,
            COUNT(DISTINCT model_family) as model_count,
            MIN(timestamp) as start_date,
            MAX(timestamp) as end_date
        FROM wildchat
    """)
    
    con.close()
    print("Done! Database is ready.")

if __name__ == "__main__":
    ingest_pipeline()