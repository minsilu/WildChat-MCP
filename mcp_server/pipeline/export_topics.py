import duckdb
import os

DB_PATH = "/private/m248lu/wildchat.db"
OUTPUT_FILE = "topics_to_rename.txt"

def export_topics():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Connecting to {DB_PATH}...")
    con = duckdb.connect(DB_PATH, read_only=True)

    print("Querying Top 50 topics...")
    try:
        df = con.execute("""
            SELECT topic, COUNT(*) as cnt 
            FROM wildchat 
            WHERE topic != 'General / Noise' 
              AND topic IS NOT NULL
            GROUP BY topic 
            ORDER BY cnt DESC 
        """).fetchdf()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("Please rename the following topics into high-level categories:\n\n")
            for index, row in df.iterrows():
                line = f"{row['topic']}"
                f.write(line + "\n")
        
        print(f"\nSuccess! Topics saved to: {os.path.abspath(OUTPUT_FILE)}")
        print("You can now download this file or view it using 'cat topics_to_rename.txt'")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    export_topics()