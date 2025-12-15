import duckdb
import os
import time

# ================= 配置路径 =================
# 请确保文件名和你 ls 看到的一致
SOURCE_DB = "/private/m248lu/wildchat.db"  
TARGET_DB = "/private/m248lu/wildchat_mini.db"
SAMPLE_RATE = "10%"  # 抽取 10%
# ===========================================

def create_mini_dataset():
    print(f"🚀 Starting sampling process...")
    print(f"   Source: {SOURCE_DB}")
    print(f"   Target: {TARGET_DB}")

    # 1. 如果目标存在，先删除，确保干净
    if os.path.exists(TARGET_DB):
        print("   🗑️  Removing existing target file...")
        os.remove(TARGET_DB)

    # 2. 连接到【新】数据库 (TARGET)
    # 这样主连接在 target 上，source 只是作为外部库挂载
    con = duckdb.connect(TARGET_DB)
    
    try:
        start_time = time.time()

        # 3. 挂载源数据库 (只读模式)
        print(f"   🔗 Attaching source database...")
        con.execute(f"ATTACH '{SOURCE_DB}' AS source_db (READ_ONLY)")

        # 4. 执行采样复制
        # BERNOULLI 采样能保证更好的随机性，适合生成测试集
        print(f"   🎲 Sampling {SAMPLE_RATE} of data into new table...")
        
        query = f"""
        CREATE TABLE wildchat AS 
        SELECT * FROM source_db.wildchat 
        USING SAMPLE {SAMPLE_RATE} (BERNOULLI);
        """
        con.execute(query)

        # 5. 获取行数验证
        count = con.execute("SELECT count(*) FROM wildchat").fetchone()[0]
        print(f"   ✅ Created 'wildchat' table with {count:,} rows.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # 6. 必须关闭连接
        con.close()
        print("   🔒 Connection closed.")

    # 7. 打印文件大小对比
    if os.path.exists(TARGET_DB) and os.path.exists(SOURCE_DB):
        src_size = os.path.getsize(SOURCE_DB) / (1024**3)
        tgt_size = os.path.getsize(TARGET_DB) / (1024**3)
        print("-" * 30)
        print(f"📉 Original Size: {src_size:.2f} GB")
        print(f"🎉 Mini DB Size:  {tgt_size:.2f} GB")
        print("-" * 30)
        print(f"Done in {time.time()-start_time:.1f} seconds.")

if __name__ == "__main__":
    create_mini_dataset()




