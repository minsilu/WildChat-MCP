from huggingface_hub import login, HfApi

MY_TOKEN = "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"

print("logging Hugging Face...")
login(token=MY_TOKEN)


api = HfApi()
repo_id = "luminlemon/wildchat-cs651" 

print("starting upload...")



api.upload_file(
    path_or_fileobj="wildchat.duckdb.zst",  
    path_in_repo="wildchat.duckdb.zst",     
    repo_id=repo_id,
    repo_type="dataset"
)

api.upload_file(
    path_or_fileobj="schema.sql",
    path_in_repo="schema.sql",
    repo_id=repo_id,
    repo_type="dataset"
)

api.upload_file(
    path_or_fileobj="scripts/build_indexes.py",
    path_in_repo="scripts/build_indexes.py",
    repo_id=repo_id,
    repo_type="dataset"
)

