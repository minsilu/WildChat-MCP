from datasets import load_dataset
from collections import Counter
import time

# dataset name on Hugging Face
HF_DATASET = "allenai/WildChat-4.8M"

def scan_models_from_hf():
    print(f"scanning dataset: {HF_DATASET} ...")
    
    ds = load_dataset(HF_DATASET, split="train", streaming=True)
    
    model_counter = Counter()
    total_processed = 0
    start_time = time.time()
    
    try:
        for record in ds:
            model_name = record.get('model', 'unknown')
            model_counter[model_name] += 1
            
            total_processed += 1
            
            # print progress every 10,000 records
            if total_processed % 10000 == 0:
                elapsed = time.time() - start_time
                speed = total_processed / elapsed
                print(f"already processed {total_processed} records, speed: {int(speed)} records/sec")
                
            # 为了节省时间，你可以选择只扫描前 100万条，或者让它一直跑完
            # if total_processed >= 1000000: 
            #     print("达到 100万条上限，提前停止。")
            #     break
                
    except KeyboardInterrupt:
        print("\nThe scanning was interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")

    print("\n" + "="*50)
    print(f"{'Model Name':<40} | {'Count':<10}")
    print("-" * 55)
    
    for model, count in model_counter.most_common():
        print(f"{model:<40} | {count:<10}")
        
    print("="*50)

if __name__ == "__main__":
    scan_models_from_hf()