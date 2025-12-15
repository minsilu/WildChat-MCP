
import duckdb
import os

DB_PATH = '/private/m248lu/wildchat.db'
CSV_PATH = '/private/m248lu/wildchat_labels_backup.csv'

assert os.path.exists(DB_PATH), f"DB not found: {DB_PATH}"
assert os.path.exists(CSV_PATH), f"CSV not found: {CSV_PATH}"

con = duckdb.connect(DB_PATH)

con.execute("SET threads TO 8;")
con.execute("BEGIN TRANSACTION;")

# 1) 读入 CSV -> 临时表（只保留 id, new_topic）
con.execute("""
CREATE TEMP TABLE labels_raw AS
SELECT
  CAST(id AS VARCHAR) AS id,
  CAST(new_topic AS VARCHAR) AS new_topic
FROM read_csv_auto(?, header=True);
""", [CSV_PATH])

con.execute("""
CREATE TEMP TABLE labels AS
SELECT id, MAX(new_topic) AS new_topic
FROM labels_raw
WHERE new_topic IS NOT NULL
GROUP BY id;
""")

# 3) 统计将会更新的行数（仅供参考）
will_update = con.execute("""
SELECT COUNT(*)
FROM wildchat w
JOIN labels l ON w.id = l.id
WHERE w.topic IS DISTINCT FROM l.new_topic;
""").fetchone()[0]
print(f"计划更新行数: {will_update}")

# 4) 执行更新（匹配到 id 才更新；未匹配自动跳过）
#    DuckDB 支持 MERGE，这里用 MERGE 更直观
con.execute("""
MERGE INTO wildchat AS w
USING labels AS l
ON w.id = l.id
WHEN MATCHED THEN UPDATE SET topic = l.new_topic;
""")

# 5) 提交并做 CHECKPOINT，确保落盘
con.execute("COMMIT;")
con.execute("CHECKPOINT;")

# 6) 验证更新后结果（可选）
updated = con.execute("""
SELECT COUNT(*)
FROM wildchat w
JOIN labels l ON w.id = l.id
WHERE w.topic = l.new_topic;
""").fetchone()[0]
print(f"匹配且已更新为新值的行数: {updated}")

con.close()
print("更新完成。")
