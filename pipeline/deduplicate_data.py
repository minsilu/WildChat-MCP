
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从 /private/m248lu/wildchat.db 读入 wildchat 表，
按 id 去重（每个 id 只保留一行），写入到新的 /private/m248lu/wildchat_dup.db。
不修改原库、不删除原库索引，便于你手动验证。
"""

import duckdb
import os
import time
from datetime import datetime

# ===== 路径配置 =====
SOURCE_DB = "/private/m248lu/wildchat.db"
TARGET_DB = "/private/m248lu/wildchat_dup.db"

# ===== 资源配置（按机器调整）=====
THREADS = 16            # 并行线程数
MEMORY_LIMIT = "60GB"   # DuckDB 内存上限

# ===== 去重保留策略（修改 ORDER BY 即可）=====
# 保留“最新时间”的一行：
ORDER_CLAUSE = "timestamp DESC NULLS LAST, rowid DESC"
# 如果你想保留“最早时间”的一行：改为
# ORDER_CLAUSE = "timestamp ASC NULLS FIRST, rowid ASC"
# 如果想保留 token_count 最大的：改为
# ORDER_CLAUSE = "token_count DESC NULLS LAST, timestamp DESC NULLS LAST, rowid DESC"

def main():
    assert os.path.exists(SOURCE_DB), f"Source DB not found: {SOURCE_DB}"
    print(f"Connecting to source: {SOURCE_DB}")
    print(f"Target (dedup subset): {TARGET_DB}")

    # 如果目标文件已存在，先删除，避免脏文件干扰
    if os.path.exists(TARGET_DB):
        print(f"Target exists, removing: {TARGET_DB}")
        os.remove(TARGET_DB)

    # 连接到新库（只在新库写入）
    con = duckdb.connect(TARGET_DB)
    con.execute(f"SET threads TO {THREADS};")
    con.execute(f"PRAGMA memory_limit='{MEMORY_LIMIT}';")
    con.execute("PRAGMA enable_progress_bar=true;")

    # 只读挂载原库
    print("\n[1/4] Attaching source database (READ_ONLY)...")
    con.execute(f"ATTACH '{SOURCE_DB}' AS src (READ_ONLY);")

    # 预统计：总行数 & DISTINCT(id)
    print("[2/4] Inspecting duplicates in source...")
    total_rows = con.execute("SELECT COUNT(*) FROM src.wildchat;").fetchone()[0]
    distinct_ids = con.execute("SELECT COUNT(DISTINCT id) FROM src.wildchat;").fetchone()[0]
    duplicates = total_rows - distinct_ids
    print(f"   - Total rows     : {total_rows:,}")
    print(f"   - Distinct id    : {distinct_ids:,}")
    print(f"   - Duplicate rows : {duplicates:,}")

    # 去重生成子集（CTAS）：在新库里创建同名表 wildchat
    print("\n[3/4] Creating deduplicated subset table in target DB...")
    t0 = time.time()
    con.execute("DROP TABLE IF EXISTS wildchat;")

    # 用窗口函数 + WHERE rn=1（兼容性更好，避免 QUALIFY 的潜在问题）
    # 注意：PARTITION BY id 会把 id=NULL 的行也分为同一组，最终只保留一行。
    # 如你希望“保留所有 id=NULL 的行”，可以在内层加 WHERE id IS NOT NULL，并在外层 UNION ALL 回去。
    con.execute(f"""
        CREATE TABLE wildchat AS
        SELECT
            id, model, model_release_date, model_family, timestamp,
            year, month, day, hour, hashed_ip, country, state,
            turn_count, token_count, topic, search_text, first_turn, full_content
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY id
                       ORDER BY {ORDER_CLAUSE}
                   ) AS rn
            FROM src.wildchat
        )
        WHERE rn = 1;
    """)
    elapsed = time.time() - t0
    new_rows = con.execute("SELECT COUNT(*) FROM wildchat;").fetchone()[0]
    print(f"   - Done. Rows in subset: {new_rows:,} (elapsed {elapsed:.2f}s)")

    # 验证：是否还存在重复 id（理论上应为 0）
    still_dups = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT id, COUNT(*) AS cnt
            FROM wildchat
            GROUP BY id
            HAVING COUNT(*) > 1
        );
    """).fetchone()[0]
    if still_dups == 0:
        print("   - ✅ No duplicate ids in subset.")
    else:
        print(f"   - ⚠️ Found {still_dups} duplicated id groups in subset (unexpected).")

    # 展示几条样例，便于你人工核验
    sample = con.execute("""
        SELECT id, timestamp, substr(search_text, 1, 80) AS snippet
        FROM wildchat
        ORDER BY timestamp DESC NULLS LAST
        LIMIT 5;
    """).fetchall()
    print("\nSample rows (top 5 by latest timestamp):")
    for r in sample:
        _id = (r[0][:8] + "...") if r[0] else "NULL"
        print(f"  - id: {_id} | ts: {r[1]} | text: {r[2]}")

    # 显示目标库大小
    size_info = con.execute("PRAGMA database_size;").fetchall()
    print("\nTarget DB size info (wildchat_dup.db):")
    for row in size_info:
        print(row)

    # 清理连接
    con.execute("DETACH src;")
    con.close()
    print("\nDone ✅  A deduplicated subset has been written to wildchat_dup.db.")

if __name__ == "__main__":
    main()

