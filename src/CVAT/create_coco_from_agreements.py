# create_coco_from_agreements.py - Generate COCO format files from agreement data for manual CVAT import
import os, json, argparse, glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# S3 bucket configuration for image URLs
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "spin-instance")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-2.amazonaws.com"


def load_image_and_annotation_mappings(data_type='part'):
    """Load image ID -> filename mappings and annotation data from local JSONs in ./data/"""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    image_mappings = {
        "train": {},
        "val": {},
        "test": {}
    }
    annotation_mappings = {
        "train": {},
        "val": {},
        "test": {}
    }

    # Select data files based on type (part or subpart)
    suffix = "parts" if data_type == "part" else "subparts"
    data_files = [
        f"spin_val_{suffix}.json",
        f"spin_test_{suffix}.json",
        f"spin_train_{suffix}.json",
    ]

    for data_file in data_files:
        fp = os.path.join(data_dir, data_file)
        if os.path.exists(fp):
            with open(fp, "r") as f:
                data = json.load(f)

            split = data_file.split("_")[1]  # val, test, train

            # Load image mappings
            for img in data.get("images", []):
                image_id = img.get("id")
                file_name = img.get("file_name")
                if image_id is not None and file_name:
                    image_mappings[split][image_id] = {
                        "file_name": file_name,
                        "height": img.get("height"),
                        "width": img.get("width")
                    }
                    # print(f"   • Loaded image_id {image_id} -> {file_name} ({img.get('width')}x{img.get('height')}) in {split}")

            # Load annotation mappings
            for ann in data.get("annotations", []):
                ann_id = ann.get("id")
                if ann_id is not None:
                    annotation_mappings[split][ann_id] = ann

    # print(f"Loaded {sum(len(split_imgs) for split_imgs in image_mappings.values())} image mappings and {len(annotation_mappings)} annotations")

    # save image mappings to a JSON file
    with open("image_mappings.json", "w") as f:
        json.dump(image_mappings, f, indent=2)
        print("Saved image mappings to image_mappings.json")

    return image_mappings, annotation_mappings


def generate_s3_url(file_name, prefix="train"):
    """Generate S3 URL for an image file."""
    fn = file_name.lstrip("/")
    if "." not in os.path.basename(fn):
        fn = f"{fn}.JPEG"
    return f"{S3_BASE_URL}/{prefix}/{fn}" if prefix else f"{S3_BASE_URL}/{fn}"

def process_agreement_file_to_coco(agreement_file_path, image_mappings, annotation_mappings):
    """Convert agreement file to COCO format for CVAT import - images only for manual annotation."""
    try:
        with open(agreement_file_path, "r") as f:
            agreement_data = json.load(f)

        category = agreement_data.get("category")
        agreements = agreement_data.get("results", [])

        # Filter for "Multiple Instances" consensus
        multiple_agreements = [a for a in agreements if a.get("consensus_result") == 1]
        if not multiple_agreements:
            print(f"No multiple-instance agreements in {category}")
            return None

        print(f"\n📋 Processing {category}: {len(multiple_agreements)} multiple-instance agreements")

        # COCO format structure - NO PRE-EXISTING ANNOTATIONS
        # This creates a clean task for manual annotation
        coco_data = {
            "info": {
                "description": f"SPIN Instance Dataset - {category} Multiple Instances (With Original Annotations)",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "SPIN Project",
                "date_created": datetime.now().isoformat()
            },
            "licenses": [
                {
                    "id": 1,
                    "name": "Unknown License",
                    "url": ""
                }
            ],
            "categories": [
                {
                    "id": 1,
                    "name": category,
                    "supercategory": "object"
                }
            ],
            "images": [],
            "annotations": []  # Will contain original annotations from agreement data
        }

        # Track processed images to avoid duplicates
        processed_images = set()
        annotation_id_counter = 0
        conversion = {
            "spin_val_parts": "val",
            "spin_test_parts": "test",
            "spin_train_parts": "train",
            "spin_val_subparts": "val",
            "spin_test_subparts": "test",
            "spin_train_subparts": "train",
            "train": "train",
            "val": "val",
            "test": "test"
        }

        for agreement in multiple_agreements:
            image_id = agreement.get("image_id")
            annotation_id = agreement.get("annotation_id")
            task_types = agreement.get("task_type")
            print(f"   🔍 Processing image_id {image_id}, annotation_id {annotation_id} with task_types {task_types}")
            if task_types in conversion:
                splits = conversion.get(task_types)
            else:
                splits = agreement.get("split")  # Fallback to 'split' field if available

            if image_id is None or annotation_id is None:
                continue

            if splits is None:
                print(f"   ⚠️  Unknown task_types '{task_types}' for image_id {image_id}")
                continue


            # Get image info
            if image_id not in image_mappings[splits]:
                print(f"   ⚠️  Missing image mapping for image_id {image_id}")
                continue

            image_info = image_mappings[splits][image_id]

            # Add image to COCO (only once per image)
            if image_id not in processed_images:
                coco_image = {
                    "id": image_id,
                    "file_name": generate_s3_url(image_info["file_name"], splits),
                    "height": image_info["height"],
                    "width": image_info["width"],
                    "license": 1
                }
                coco_data["images"].append(coco_image)
                processed_images.add(image_id)

            # Add annotation from original data
            if annotation_id in annotation_mappings[splits]:
                original_annotation = annotation_mappings[splits][annotation_id]

                # Convert to COCO annotation format
                coco_annotation = {
                    "id": annotation_id_counter,
                    "annotation_id": annotation_id,  # Keep original annotation ID for reference
                    "split": splits,
                    "image_id": image_id,
                    "category_id": 1,  # Our single category
                    "bbox": original_annotation.get("bbox", []),
                    "area": original_annotation.get("area", 0),
                    "iscrowd": 0
                }

                # Add segmentation if available
                if "segmentation" in original_annotation:
                    coco_annotation["segmentation"] = original_annotation["segmentation"]
                coco_data["annotations"].append(coco_annotation)
                annotation_id_counter += 1
            else:
                print(f"   ⚠️  Missing annotation mapping for annotation_id {annotation_id}")

        if not coco_data["images"]:
            print(f"   ❌ No valid images found for {category}")
            return None

        print(f"   ✅ Generated COCO data: {len(coco_data['images'])} images, {len(coco_data['annotations'])} annotations")

        return {
            "category": category,
            "coco_data": coco_data,
            "image_count": len(coco_data["images"]),
            "annotation_count": len(coco_data["annotations"])
        }

    except Exception as e:
        print(f"Error processing {agreement_file_path}: {e}")
        return None


def save_coco_file(coco_result, output_dir):
    """Save COCO data to JSON file."""
    if not coco_result:
        return None

    category = coco_result["category"]
    safe_category = category.replace("/", "_").replace("\\", "_").replace(" ", "_")

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{safe_category}_coco.json")

    try:
        with open(output_file, 'w') as f:
            json.dump(coco_result["coco_data"], f, indent=2)

        print(f"   💾 Saved COCO file: {output_file}")
        return output_file

    except Exception as e:
        print(f"   ❌ Error saving COCO file for {category}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate COCO format files from agreement data for manual CVAT import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script reads agreement files and generates COCO format JSON files that can be
manually imported into CVAT. Only annotations with consensus_result=1 (Multiple Instances)
are included.

Examples:
  python create_coco_from_agreements.py --category QuadrupedFoot --type part
  python create_coco_from_agreements.py --all --type subpart
  python create_coco_from_agreements.py --category QuadrupedFoot --output-dir ./coco_exports --type part
        """
    )

    parser.add_argument(
        "--category", "-c",
        type=str,
        help="Process specific category (e.g., QuadrupedFoot)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Process all agreement files"
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=['part', 'subpart'],
        default='part',
        help="Type of annotations: 'part' or 'subpart' (default: part)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./coco_exports",
        help="Output directory for COCO JSON files"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories"
    )

    args = parser.parse_args()

    # Find agreement files based on type
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    agreements_subdir = "subpart" if args.type == "subpart" else "part"
    agreements_dir = os.path.join(data_dir, "agreements", agreements_subdir)

    if not os.path.exists(agreements_dir):
        print(f"❌ Agreements directory not found: {agreements_dir}")
        print(f"   Expected: {agreements_dir}")
        return


    agreement_files = glob.glob(os.path.join(agreements_dir, "*_agreements.json"))
    if not agreement_files:
        print(f"❌ No agreement files in {agreements_dir}")
        return

    # Extract available categories
    available_categories = sorted([
        os.path.basename(p).replace("_agreements.json", "")
        for p in agreement_files
    ])

    if args.list_categories:
        print(f"📋 Available {args.type} categories:")
        for c in available_categories:
            print(f"   • {c}")
        return

    if not args.category and not args.all:
        print("❌ Must specify either --category or --all")
        print("    Use --list-categories to see options.")
        return

    # Load mappings
    print(f"🔄 Loading {args.type} image and annotation mappings...")
    image_mappings, annotation_mappings = load_image_and_annotation_mappings(args.type)

    if not image_mappings or not annotation_mappings:
        print("❌ No mappings loaded. Check your data files.")
        return

    # Select files to process
    files_to_process = []
    if args.category:
        target = os.path.join(agreements_dir, f"{args.category}_agreements.json")
        print(f"🔍 Looking for category file: {target}")
        if os.path.exists(target):
            files_to_process.append(target)
        else:
            print(f"❌ Agreement file not found for category: {args.category}")
            print(f"Available: {', '.join(available_categories)}")
            return
    else:
        files_to_process = agreement_files

    # Process files
    print(f"\n🚀 Processing {len(files_to_process)} agreement file(s)...")
    results = []

    for agreement_file in files_to_process:
        coco_result = process_agreement_file_to_coco(agreement_file, image_mappings, annotation_mappings)
        if coco_result:
            output_file = save_coco_file(coco_result, args.output_dir)
            if output_file:
                results.append({
                    **coco_result,
                    "output_file": output_file
                })

    # Summary
    print(f"\n🎉 Summary:")
    print(f"   📋 Type: {args.type}")
    print(f"   📋 Agreement files processed: {len(files_to_process)}")
    print(f"   ✅ COCO files generated: {len(results)}")
    print(f"   📁 Output directory: {os.path.abspath(args.output_dir)}")

    if results:
        print(f"\n📝 Generated COCO files:")
        total_images = 0
        total_annotations = 0
        for result in results:
            print(f"   • {result['category']}: {result['image_count']} images, {result['annotation_count']} annotations")
            total_images += result['image_count']
            total_annotations += result['annotation_count']

        print(f"\n📊 Totals: {total_images} images, {total_annotations} annotations")
        print(f"\n🔗 To import into CVAT:")
        print(f"   1. Go to app.cvat.ai and create a new task")
        print(f"   2. Upload images using 'Remote source' with S3 URLs from the COCO files")
        print(f"   3. Import annotations using 'Upload annotation' → 'COCO 1.0' format")


if __name__ == "__main__":
    main()
