
DB_FILE = "/private/m248lu/wildchat_orginal.db" # local database
HF_DATASET = "allenai/WildChat-4.8M" # the original wildchat database 
BATCH_SIZE = 10000 



# Set to True to process only the first 5000 rows for testing
DEBUG_MODE = False
# =================== config for topic modeling ========================
EMBEDDING_FILE = "/private/m248lu/wildchat_embeddings.npy"
BATCH_SIZE = 512         # GPU 
N_CLUSTERS = 50             
DIMENSIONS = 5              
OLLAMA_MODEL = "qwen2.5:7b"  
OLLAMA_URL = "http://localhost:11434/api/generate"