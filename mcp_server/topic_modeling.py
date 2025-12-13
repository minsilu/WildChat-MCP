import duckdb
import pandas as pd
import torch
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
import numpy as np

# ================= CONFIG =================
DB_FILE = "/private/m248lu/wildchat.db"
BATCH_SIZE = 512         # GPU 
MIN_TOPIC_SIZE = 300      
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



if __name__ == "__main__":
    run_quality_pipeline()