import duckdb
import pandas as pd
import torch
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.cluster import MiniBatchKMeans

import time

# ================= CONFIG =================
DB_FILE = "/private/m248lu/wildchat.db"
BATCH_SIZE = 512         # GPU 
N_CLUSTERS = 50             
DIMENSIONS = 5              
CPU_CORES = -1            # USE ALL CORES
# ==========================================

def run_quality_pipeline():
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Starting Pipeline on: {device.upper()}")

    con = duckdb.connect(DB_FILE)

    print(f"Reading 1.6M records from DuckDB...")
    
    # filter out very short / null entries
    df = con.execute("""
        SELECT id, search_text 
        FROM wildchat 
        WHERE search_text IS NOT NULL AND length(search_text) > 10
    """).fetchdf()
    
    docs = df['search_text'].tolist()
    ids = df['id'].tolist()
    print(f"Loaded {len(docs)} documents.")

    print("Encoding embeddings (GPU)...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    
    embeddings = embedding_model.encode(
        docs, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    print("Embeddings calculated.")

 
    
    # UMAP
    print("Configuring UMAP (Dimensionality Reduction)...")
    umap_model = UMAP(
        n_neighbors=30,      
        n_components=5, 
        min_dist=0.0, 
        metric='cosine', 
        low_memory=False,
        random_state=42,
        n_jobs=CPU_CORES
    )

    # HDBSCAN
    # prediction_data=True is needed for topic prediction on new data
    print("Configuring HDBSCAN (Density Clustering)...")
    hdbscan_model = HDBSCAN(
        min_cluster_size=MIN_TOPIC_SIZE,
        metric='euclidean', 
        cluster_selection_method='eom', 
        prediction_data=True
    )

    print(f"Training BERTopic ...")
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        calculate_probabilities=False,
        verbose=True,
        nr_topics="auto" 
    )

    topics, probs = topic_model.fit_transform(docs, embeddings)
    
    print("\nTopic Modeling Finished! Top 20 Topics:")
    print(topic_model.get_topic_info().head(20))

    print("Preparing to update DuckDB...")
    
    topic_info = topic_model.get_topic_info()
    
    label_map = {}
    for index, row in topic_info.iterrows():
        t_id = row['Topic']
        if t_id == -1:
            label_map[t_id] = "General / Noise"
        else:
            keywords = [w[0] for w in topic_model.get_topic(t_id)[:3]]
            label_map[t_id] = "_".join(keywords)

    final_topic_labels = [label_map.get(t, "General") for t in topics]

    update_df = pd.DataFrame({
        'id': ids,
        'new_topic': final_topic_labels
    })

    print("Writing updates to database...")
    con.execute("CREATE OR REPLACE TABLE topic_updates AS SELECT * FROM update_df")
    
    con.execute("""
        UPDATE wildchat 
        SET topic = topic_updates.new_topic
        FROM topic_updates
        WHERE wildchat.id = topic_updates.id
    """)
    
    con.execute("DROP TABLE topic_updates")
    print("Main Table Updated.")

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

    print(f"\n[Step 4/5] Clustering (MiniBatchKMeans)...")
    t0 = time.time()
    cluster_model = MiniBatchKMeans(
        n_clusters=N_CLUSTERS, 
        batch_size=4096,
        random_state=42,
        n_init='auto',
        verbose=1 
    )

    clusters = cluster_model.fit_predict(reduced_embeddings)
    print(f"   ✅ Clustering Finished in {time.time()-t0:.1f} seconds.")

    # 5. Assembly BERTopic
    print(f"\n[Step 5/5] Extracting Topic Keywords...")
    topic_model = BERTopic(
        embedding_model=embedding_model, 
        umap_model=dim_model,            
        hdbscan_model=cluster_model,     
        calculate_probabilities=False,
        verbose=True
    )


    topic_model.fit(docs, embeddings) 
    
    print("\nPipeline Finished!")
    print(topic_model.get_topic_info().head(20))

    print("\nUpdating Database...")
    topic_info = topic_model.get_topic_info()
    
    topic_mapping = {}
    for topic_id in range(N_CLUSTERS):
        try:
            keywords = [w[0] for w in topic_model.get_topic(topic_id)[:3]]
            label = "_".join(keywords)
            topic_mapping[topic_id] = label
        except:
            topic_mapping[topic_id] = "General"

    doc_topics = topic_model.topics_

    final_labels = [topic_mapping.get(t, "General") for t in doc_topics]

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
    print("✅ Database Updated Successfully.")
    print(f"Total Time: {(time.time()-start_global)/60:.1f} minutes.")


if __name__ == "__main__":
    run_quality_pipeline()