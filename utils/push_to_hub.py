from datasets import load_from_disk

def push_dataset(dataset_path, repo_id):
    """
    Load a saved DatasetDict and push it to the Hugging Face Hub.
    """
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_from_disk(dataset_path)

    print(f"Pushing to Hub: {repo_id}...")
    # private=True makes the dataset private initially. Change to False if you want it public.
    dataset.push_to_hub(repo_id, private=True)

    print("✅ Upload complete!")

if __name__ == "__main__":
    # Path to your saved DatasetDict
    DATASET_PATH = "hf_dataset/spin2_dataset_dict"

    # REPLACE THIS with your Hugging Face username and dataset name
    # e.g., "Andy-LZH/PartInventory"
    REPO_ID = "Andy-LZH/PartInventory"

    push_dataset(DATASET_PATH, REPO_ID)
