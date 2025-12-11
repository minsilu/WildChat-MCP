import duckdb
from datasets import load_dataset
import pandas as pd
import datetime

# --- 配置部分 ---
DB_FILENAME = "wildchat.db"  # 本地数据库文件名
SAMPLE_LIMIT = 10000         # 为了演示，我们只取前1万条。作业展示足够了，且速度快。
                             # 如果你想跑更多数据，可以把这个改大，比如 50000

def process_and_ingest():
    print(f"🚀 开始连接 HuggingFace，准备下载 WildChat 数据 (Limit: {SAMPLE_LIMIT} 条)...")
    
    # 使用 streaming=True 模式，这样不需要下载整个几百GB的数据集，而是边下边处理
    ds = load_dataset("allenai/WildChat-4.8M", split="train", streaming=True)
    
    data_buffer = []
    count = 0
    
    print("⏳ 正在处理数据，提取特征...")
    
    for sample in ds:
        # 1. 提取基础信息
        conversation = sample.get('conversation', [])
        model = sample.get('model', 'unknown')
        language = sample.get('language', 'unknown')
        timestamp = sample.get('timestamp') # 通常是 datetime 对象
        
        # 2. 针对队友 Proposal 的特征提取：
        
        # A. 为了分析 "Prompt Topic"：提取用户的第一个问题
        user_prompt = ""
        if len(conversation) > 0 and conversation[0]['role'] == 'user':
            user_prompt = conversation[0]['content']
            
        # B. 为了分析 "Conversation Length"：计算对话轮数
        turn_count = len(conversation)
        
        # 将清洗后的数据加入列表
        data_buffer.append({
            "conversation_hash": sample.get('conversation_hash'),
            "model": model,
            "language": language,
            "timestamp": timestamp,
            "user_prompt": user_prompt, # 存入数据库，之后给 LLM 看来做分类
            "turn_count": turn_count
        })
        
        count += 1
        if count % 1000 == 0:
            print(f"   已处理 {count} 条...")
            
        if count >= SAMPLE_LIMIT:
            break
            
    print("✅ 数据提取完成，正在转换为 DataFrame...")
    df = pd.DataFrame(data_buffer)
    
    # 简单的清洗：去掉空 prompt
    df = df[df['user_prompt'] != ""]
    
    print(f"💾 正在将 {len(df)} 条数据存入 DuckDB ({DB_FILENAME})...")
    
    # --- DuckDB 操作 ---
    # 连接到本地文件数据库。如果文件不存在，会自动创建。
    con = duckdb.connect(DB_FILENAME)
    
    # 将 DataFrame 直接存为一张表，表名为 'wildchat'
    # CREATE OR REPLACE TABLE 确保你可以反复运行脚本而不会报错
    con.execute("CREATE OR REPLACE TABLE wildchat AS SELECT * FROM df")
    
    # --- 验证环节 ---
    print("\n🔍 验证数据库内容:")
    
    # 1. 检查总行数
    count_result = con.execute("SELECT COUNT(*) FROM wildchat").fetchone()
    print(f"   -> 总行数: {count_result[0]}")
    
    # 2. 预览前 3 条数据 (只看 model 和 prompt)
    print("   -> 数据预览 (Model, Prompt):")
    preview = con.execute("SELECT model, user_prompt FROM wildchat LIMIT 3").fetchall()
    for row in preview:
        # 截断一下 prompt 方便显示
        short_prompt = row[1][:50].replace('\n', ' ') + "..."
        print(f"      [{row[0]}] {short_prompt}")
        
    con.close()
    print(f"\n🎉 成功！数据库文件 '{DB_FILENAME}' 已就绪。")

if __name__ == "__main__":
    process_and_ingest()