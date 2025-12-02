import json
import os
from datasets import Dataset, Features, Value, Sequence, ClassLabel, Image
from PIL import Image as PILImage

def create_hf_dataset(json_path, image_dir):
    """
    Convert a COCO-style JSON annotation file to a Hugging Face Dataset.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    images = {img['id']: img for img in data['images']}
    categories = {cat['id']: cat['name'] for cat in data['categories']}

    # Create a mapping of category IDs to continuous indices (0 to N-1)
    # This is useful for ClassLabel feature
    sorted_cat_ids = sorted(categories.keys())
    cat_id_to_idx = {cat_id: idx for idx, cat_id in enumerate(sorted_cat_ids)}
    category_names = [categories[cat_id] for cat_id in sorted_cat_ids]

    # Group annotations by image_id
    annotations = {}
    for ann in data['annotations']:
        img_id = ann['image_id']
        if img_id not in annotations:
            annotations[img_id] = []
        annotations[img_id].append(ann)


    def generator():
        for img_id, img_info in images.items():
            file_name = img_info['file_name']
            image_path = os.path.join(image_dir, file_name)

            # Check if image exists
            if not os.path.exists(image_path):
                # Try finding it without the split prefix if it fails
                # e.g. val/image.jpg -> image.jpg
                basename = os.path.basename(file_name)
                potential_path = os.path.join(image_dir, basename)
                if os.path.exists(potential_path):
                    image_path = potential_path
                else:
                    print(f"Warning: Image {file_name} not found at {image_path}")
                    continue

            # Initialize dict of lists for objects (columnar format required for Sequence of dicts)
            objects_dict = {
                "id": [],
                "image_id": [],
                "category_id": [],
                "category_name": [],
                "area": [],
                "bbox": [],
                "iscrowd": [],
                "instance_type": [],
                "segmentation": []
            }

            if img_id in annotations:
                for ann in annotations[img_id]:
                    objects_dict["id"].append(ann['id'])
                    objects_dict["image_id"].append(ann['image_id'])
                    objects_dict["category_id"].append(cat_id_to_idx[ann['category_id']])
                    objects_dict["category_name"].append(categories[ann['category_id']])
                    objects_dict["area"].append(ann.get('area', 0))
                    objects_dict["bbox"].append(ann.get('bbox') or [0,0,0,0])
                    objects_dict["iscrowd"].append(ann.get('iscrowd', 0))
                    objects_dict["instance_type"].append(ann.get('instance_id', 0))

                    # Handle segmentation
                    seg = ann.get('segmentation', [])
                    if isinstance(seg, dict) and 'counts' in seg:
                        objects_dict["segmentation"].append([str(seg['counts'])])
                    elif isinstance(seg, list):
                        objects_dict["segmentation"].append([str(s) for s in seg])
                    else:
                        objects_dict["segmentation"].append([])

            yield {
                "image_id": img_id,
                "image": image_path,
                "width": img_info['width'],
                "height": img_info['height'],
                "file_name": file_name,
                "annotations": objects_dict
            }

    # Define features
    features = Features({
        "image_id": Value("int64"),
        "image": Image(),
        "width": Value("int32"),
        "height": Value("int32"),
        "file_name": Value("string"),
        "annotations": Sequence({
            "id": Value("int64"),
            "image_id": Value("int64"),
            "category_id": ClassLabel(names=category_names),
            "category_name": Value("string"),
            "area": Value("float32"), # Area can be float
            "bbox": Sequence(Value("float32"), length=4),
            "iscrowd": Value("int8"),
            "segmentation": Sequence(Value("string")) # Changed to string to support RLE counts and Polygons
        })
    })

    dataset = Dataset.from_generator(generator, features=features)
    return dataset

if __name__ == "__main__":
    from datasets import DatasetDict

    # Configuration
    IMAGE_DIR_ROOT = "data/images"
    OUTPUT_DIR = "hf_dataset"

    # Define splits to process
    splits_to_process = ["train", "val", "test"]

    # Dictionary to hold all datasets
    dataset_dict = {}

    for split in splits_to_process:
        print(f"\nProcessing {split} split...")

        # Determine JSON path based on split
        # Note: Adjust filenames if they differ (e.g. _with_instances vs plain)
        # Based on previous context, train/test might have _with_instances suffix in src/CVAT/merged...
        # But user pointed to data/annotations/spin2_val_parts.json recently.
        # Let's try to find the best matching file.

        possible_paths = [
            f"data/annotations/spin2_{split}_parts.json",
        ]

        json_path = None
        for p in possible_paths:
            if os.path.exists(p):
                json_path = p
                break

        if not json_path:
            print(f"Warning: Could not find annotation file for {split}. Skipping.")
            continue

        print(f"Using annotation file: {json_path}")

        try:
            ds = create_hf_dataset(json_path, IMAGE_DIR_ROOT)
            dataset_dict[split] = ds
            print(f"Successfully created {split} dataset with {len(ds)} examples.")

            # Save individual parquet file
            parquet_path = os.path.join(OUTPUT_DIR, f"spin2_{split}.parquet")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            ds.to_parquet(parquet_path)
            print(f"Saved parquet to {parquet_path}")

        except Exception as e:
            print(f"Error processing {split}: {e}")

    # Create DatasetDict
    if dataset_dict:
        dd = DatasetDict(dataset_dict)

        # Save DatasetDict to disk (Arrow format)
        dd_output_path = os.path.join(OUTPUT_DIR, "spin2_dataset_dict")
        dd.save_to_disk(dd_output_path)
        print(f"\nSaved full DatasetDict to {dd_output_path}")

        # Example of how to push to hub
        # dd.push_to_hub("your-username/part-inventory")
    else:
        print("\nNo datasets were created.")
