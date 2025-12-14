import duckdb
import pandas as pd
import torch
import numpy as np
import requests
import json
import gc
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import CountVectorizer

import time

# ================= CONFIG =================
DB_FILE = "/private/m248lu/wildchat.db"
BATCH_SIZE = 512         # GPU 
N_CLUSTERS = 50             
DIMENSIONS = 5              
OLLAMA_MODEL = "qwen2.5:7b"  
OLLAMA_URL = "http://localhost:11434/api/generate"
# ==========================================

def run_fast_pipeline():
    start_global = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Starting Turbo Pipeline on: {device.upper()}")

    print(f"\n[Step 1/5] Reading Data from DuckDB...")
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT id, search_text 
        FROM wildchat 
        WHERE search_text IS NOT NULL AND length(search_text) > 10
    """).fetchdf()
    
    docs = df['search_text'].tolist()
    ids = df['id'].tolist()
    print(f"   Loaded {len(docs):,} documents.")

    print(f"\n[Step 2/5] Calculating Embeddings (This uses GPU)...")
    t0 = time.time()
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    
    embeddings = embedding_model.encode(
        docs, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    print(f"   Embeddings calculated in {(time.time()-t0)/60:.1f} minutes.")

    print(f"\n[Step 3/5] Dimensionality Reduction (PCA)...")
    t0 = time.time()
    dim_model = PCA(n_components=DIMENSIONS, random_state=42)
    reduced_embeddings = dim_model.fit_transform(embeddings)
    print(f"   PCA Finished in {time.time()-t0:.1f} seconds. Shape: {reduced_embeddings.shape}")

    del embeddings 
    import gc
    gc.collect()
    print("   PCA done. Freed original embeddings memory.")
    
    print(f"\n[Step 4/5] Clustering (MiniBatchKMeans)...")
    t0 = time.time()
    cluster_model = MiniBatchKMeans(
        n_clusters=N_CLUSTERS, 
        batch_size=4096,
        random_state=42,
        n_init='auto',
        verbose=1 
    )

    labels = cluster_model.fit_predict(reduced_embeddings)
    print(f"   Clustering Finished in {time.time()-t0:.1f} seconds.")

    # 5. Assembly BERTopic
    print(f"\n[Step 5/5] Extracting Topic Keywords...")
    df['topic_id'] = labels
    topic_docs = df.groupby('topic_id')['search_text'].apply(lambda x: " ".join(x.head(1000))).reset_index()
    vectorizer = CountVectorizer(stop_words='english', max_features=1000)
    X = vectorizer.fit_transform(topic_docs['search_text'])
    feature_names = vectorizer.get_feature_names_out()

    topic_mapping = {}
    for i, row in enumerate(X.toarray()):
        topic_id = topic_docs.iloc[i]['topic_id']
        top_indices = row.argsort()[-3:][::-1]
        keywords = [feature_names[ind] for ind in top_indices]
        topic_mapping[topic_id] = "_".join(keywords).title() # e.g. "Python_Code_Error"
        print(f"   Topic {topic_id}: {topic_mapping[topic_id]}")

    print("\nUpdating Database...")
    final_labels = [topic_mapping.get(t, "General") for t in labels]

    update_df = pd.DataFrame({
        'id': ids,
        'new_topic': final_labels
    })

    con.execute("CREATE OR REPLACE TABLE topic_updates AS SELECT * FROM update_df")
    con.execute("""
        UPDATE wildchat 
        SET topic = topic_updates.new_topic
        FROM topic_updates
        WHERE wildchat.id = topic_updates.id
    """)
    con.execute("DROP TABLE topic_updates")
    print("Database Updated Successfully.")
    print(f"Total Time: {(time.time()-start_global)/60:.1f} minutes.")


def get_label_from_ollama(cluster_id, keywords, sample_texts):

    prompt = f"""
    [Role]: You are a data analyst classifying user queries.
    
    [Input Data]:
    - Top Keywords: {", ".join(keywords)}
    - User Query Samples:
      1. {sample_texts[0][:150]}...
      2. {sample_texts[1][:150]}...
      3. {sample_texts[2][:150]}...
    
    [Task]: 
    Analyze the keywords and samples to create a concise Category Label (2-4 words).
    
    [Rules]:
    1. If keywords contain 'class, div, span', label it "Web Development (HTML/CSS)".
    2. If keywords contain 'def, return, import', label it "Python Programming".
    3. If keywords contain 'sql, select', label it "SQL Database".
    4. If keywords contain 'dan, jailbreak', label it "Jailbreak Attempt".
    5. Avoid generic names. Be specific.
    
    [Output]: Return ONLY the label name. Do not write explanations.
    """
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2, 
            "num_ctx": 1024    
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json().get('response', '').strip()
            clean_label = result.split('\n')[0].replace('"', '').replace("'", "").replace("Label:", "").strip()
            return clean_label
        else:
            print(f"Ollama Error {response.status_code}: {response.text}")
            return "_".join(keywords[:2])
    except Exception as e:
        print(f"⚠️ Connection Error: Is Ollama running? {e}")
        return "_".join(keywords[:2])

def run_turbo_pipeline():
    start_global = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f" Starting Turbo Pipeline on: {device.upper()}")

    print(f"\n[Step 1/6] Reading Data from DuckDB...")
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT id, search_text 
        FROM wildchat 
        WHERE search_text IS NOT NULL AND length(search_text) > 10
    """).fetchdf()
    
    docs = df['search_text'].tolist()
    ids = df['id'].tolist()
    print(f"   Loaded {len(docs):,} documents.")

    print(f"\n[Step 2/6] Calculating Embeddings...")
    t0 = time.time()
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    embeddings = embedding_model.encode(
        docs, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    del embedding_model
    gc.collect()
    torch.cuda.empty_cache()
    print(f"   Embeddings calculated in {(time.time()-t0)/60:.1f} minutes.")

    print(f"\n[Step 3/6] Dimensionality Reduction (PCA)...")
    t0 = time.time()
    dim_model = PCA(n_components=DIMENSIONS, random_state=42)
    reduced_embeddings = dim_model.fit_transform(embeddings)
    print(f"   PCA Finished in {time.time()-t0:.1f} seconds.")

    del embeddings 
    gc.collect()

    print(f"\n[Step 4/6] Clustering (MiniBatchKMeans)...")
    t0 = time.time()
    cluster_model = MiniBatchKMeans(
        n_clusters=N_CLUSTERS, 
        batch_size=4096,
        random_state=42,
        n_init='auto'
    )
    labels = cluster_model.fit_predict(reduced_embeddings)
    df['cluster_id'] = labels
    print(f"   Clustering Finished in {time.time()-t0:.1f} seconds.")

    print(f"\n[Step 5/6] Generating Smart Labels with Ollama ({OLLAMA_MODEL})...")
    
    vectorizer = CountVectorizer(
        stop_words='english', 
        max_features=1000,
        token_pattern=r'(?u)\b[a-zA-Z]{3,}\b' 
    )
    
    cluster_docs = df.groupby('cluster_id')['search_text'].agg(
        combined_text=lambda x: " ".join(x.head(200)), 
        sample_docs=lambda x: x.head(3).tolist()       
    ).reset_index()
    
    X = vectorizer.fit_transform(cluster_docs['combined_text'])
    feature_names = vectorizer.get_feature_names_out()
    
    label_map = {} 
    
    print(f"   Processing {N_CLUSTERS} clusters...")
    for i, row in cluster_docs.iterrows():
        cluster_id = row['cluster_id']
        samples = row['sample_docs']
        
        tfidf_row = X[i].toarray().flatten()
        top_indices = tfidf_row.argsort()[-15:][::-1]
        keywords = [feature_names[ind] for ind in top_indices]
        

        human_label = get_label_from_ollama(cluster_id, keywords, samples)
        
        label_map[cluster_id] = human_label
        print(f"   Cluster {cluster_id:02d}: {human_label} \n      (Ctx: {', '.join(keywords[:3])}...)")

    del dim_model
    del cluster_model
    del reduced_embeddings
    del X
    gc.collect()

    print(f"\n[Step 6/6] Writing to Database (CTAS Strategy)...")
    t0 = time.time()
    
    final_labels = [label_map.get(cid, "General") for cid in labels]
    
    update_df = pd.DataFrame({
        'id': ids,
        'new_topic': final_labels
    })

    con.execute("CREATE OR REPLACE TABLE topic_updates AS SELECT * FROM update_df")
    
    con.execute("PRAGMA memory_limit='75GB'")
    con.execute("PRAGMA temp_directory='/private/m248lu/duckdb_temp.tmp'")
    
    print("   Rewriting table (CTAS)...")
    con.execute("""
        CREATE OR REPLACE TABLE wildchat_new AS 
        SELECT 
            w.* EXCLUDE (topic),
            COALESCE(t.new_topic, 'General') as topic
        FROM wildchat w
        LEFT JOIN topic_updates t ON w.id = t.id
    """)
    
    con.execute("DROP TABLE wildchat")
    con.execute("ALTER TABLE wildchat_new RENAME TO wildchat")
    con.execute("DROP TABLE topic_updates")
    
    print(f"   Database updated in {time.time()-t0:.1f} seconds.")
    print(f"Pipeline Complete! Total Time: {(time.time()-start_global)/60:.1f} minutes.")
    con.close()
if __name__ == "__main__":
    print("Running Topic Modeling Pipeline with Ollama...")
    try:
        if requests.get("http://localhost:11434").status_code == 200:
            print("Ollama is online.")
            run_turbo_pipeline()
        else:
            print("Ollama seems offline. Please run 'ollama serve' first.")
    except:
        print("Could not connect to Ollama. Make sure it's running on port 11434.")