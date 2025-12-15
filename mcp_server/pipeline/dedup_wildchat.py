import duckdb
import os
import time

# ================= CONFIGURATION =================
# Path to your current (dirty) database
ORIGINAL_DB = "/private/m248lu/wildchat.db"
# Path to the new (clean) database we will create
CLEAN_DB = "/private/m248lu/wildchat_dedup.db"
# Memory limit (Adjust based on your server, e.g., '60GB')
MEMORY_LIMIT = '60GB'
# =================================================

def clean_database():
    start_time = time.time()
    print(f"🧹 Starting Deduplication Pipeline...")
    print(f"   Source: {ORIGINAL_DB}")
    print(f"   Target: {CLEAN_DB}")

    # 1. Remove target file if it exists to start fresh
    if os.path.exists(CLEAN_DB):
        print(f"   [Warning] Target file exists. Removing: {CLEAN_DB}")
        os.remove(CLEAN_DB)

    try:
        # 2. Connect to the NEW database file
        # We connect to the NEW file and "pull" data from the OLD one.
        con = duckdb.connect(CLEAN_DB)
        
        # 3. Optimize System Settings
        con.execute(f"PRAGMA memory_limit='{MEMORY_LIMIT}'")
        con.execute("PRAGMA threads=16")
        print(f"   [System] Memory Limit set to {MEMORY_LIMIT}")

        # 4. Attach the original database (Read-Only mode is safer)
        print(f"   [Step 1] Attaching source database...")
        con.execute(f"ATTACH '{ORIGINAL_DB}' AS source_db (READ_ONLY)")

        # 5. Analyze current duplicates
        print(f"   [Step 2] Analyzing duplicates in source...")
        count_total = con.execute("SELECT count(*) FROM source_db.wildchat").fetchone()[0]
        count_distinct = con.execute("SELECT count(DISTINCT id) FROM source_db.wildchat").fetchone()[0]
        duplicates = count_total - count_distinct
        
        print(f"      - Total Rows:    {count_total:,}")
        print(f"      - Unique IDs:    {count_distinct:,}")
        print(f"      - Duplicates:    {duplicates:,}")

        if duplicates == 0:
            print("   ✅ No duplicates found! You don't need to run this.")
            return

        # 6. The Heavy Lifting: CTAS with QUALIFY
        # QUALIFY ROW_NUMBER() ... = 1 keeps only the FIRST occurrence of an ID.
        # We order by 'rowid' effectively keeping the first insertion.
        # If you prefer to keep the longest text, change to: ORDER BY length(search_text) DESC
        print(f"   [Step 3] rewriting table to remove duplicates (This implies I/O)...")
        t0 = time.time()
        
        query = """
        CREATE TABLE wildchat AS 
        SELECT * FROM source_db.wildchat
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY rowid) = 1
        """
        con.execute(query)
        elapsed = time.time() - t0
        print(f"   ✅ Table rewritten in {elapsed:.1f} seconds.")

        # 7. Verification
        print(f"   [Step 4] Verifying new table...")
        new_count = con.execute("SELECT count(*) FROM wildchat").fetchone()[0]
        print(f"      - New Table Rows: {new_count:,}")
        
        if new_count == count_distinct:
            print("      - SUCCESS: Row count matches unique ID count.")
        else:
            print("      - WARNING: Row count mismatch. Check logic.")

        # 8. Detach and Close
        con.execute("DETACH source_db")
        con.close()

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        # Clean up partial file
        if os.path.exists(CLEAN_DB):
            os.remove(CLEAN_DB)
        return

    total_time = (time.time() - start_time) / 60
    print("-" * 50)
    print(f"🎉 Pipeline Complete in {total_time:.1f} minutes.")
    print(f"👉 NEXT STEPS:")
    print(f"1. mv {ORIGINAL_DB} {ORIGINAL_DB}.bak")
    print(f"2. mv {CLEAN_DB} {ORIGINAL_DB}")
    print(f"3. Re-run your FTS index script.")

if __name__ == "__main__":
    clean_database()