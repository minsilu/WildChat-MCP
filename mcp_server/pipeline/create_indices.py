import duckdb
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_FILE

def create_indices():
    print(f"Connecting to database: {DB_FILE}...")
    con = duckdb.connect(DB_FILE)

    # ================= B-Tree Indexes =================
    print("\n[1/3] Building Standard B-Tree Indexes...")
    standard_indices = [
        ("idx_topic", "topic"),
        ("idx_model", "model_family"),
        ("idx_time", "timestamp"),
        ("idx_country", "country") 
    ]

    for idx_name, col_name in standard_indices:
        try:
            start_time = time.time()
            con.execute(f"DROP INDEX IF EXISTS {idx_name}")
            con.execute(f"CREATE INDEX {idx_name} ON wildchat({col_name})")
            elapsed = time.time() - start_time
            print(f"   Successfully created {idx_name} on '{col_name}' ({elapsed:.2f}s)")
        except Exception as e:
            print(f"   Failed to create {idx_name}: {e}")

    # ================= FTS Index =================
    print("\n[2/3] Building Full Text Search (FTS) Index...")
    try:
        start_time = time.time()
        con.execute("INSTALL fts; LOAD fts;")
        con.execute("PRAGMA create_fts_index('wildchat', 'id', 'search_text')")
        elapsed = time.time() - start_time
        print(f"   FTS Index built successfully on 'search_text' ({elapsed:.2f}s)")
        
    except Exception as e:
        if "already exists" in str(e):
             print(f"   FTS Index already exists (Skipping re-creation).")
        else:
             print(f"   Failed to create FTS Index: {e}")

    # ================= Verification =================
    print("\n[3/3] Verifying Indexes...")
    

    print("   Current B-Tree Indexes in Database:")
    indices = con.execute("SELECT index_name, table_name FROM duckdb_indexes").fetchall()
    for idx in indices:
        print(f"      - {idx[0]} (on {idx[1]})")

    print("\n   Testing Search Performance:")
    test_query = "quantum physics"
    
    try:
        t0 = time.time()
        res = con.execute(f"""
            SELECT id, substr(search_text, 1, 50) as snippet, score
            FROM (
                SELECT *, fts_main_wildchat.match_bm25(id, '{test_query}') AS score
                FROM wildchat
            )
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT 3
        """).fetchall()
        t1 = time.time()
        
        print(f"      Search term: '{test_query}'")
        print(f"      Time taken: {(t1-t0)*1000:.2f} ms")
        print(f"      Top Results:")
        for row in res:
            print(f"      - ID: {row[0][:8]}... | Score: {row[2]:.2f} | Text: {row[1]}...")
            
    except Exception as e:
        print(f"      Search Verification Failed: {e}")
    con.close()
    print("\nDone.")

if __name__ == "__main__":
    create_indices()
