#!/usr/bin/env python3
"""
Create a COCO dataset in archive format with train/val split and proper naming.
"""

import json
import argparse
import os
import requests
import shutil
from urllib.parse import urlparse
from pathlib import Path
import time
import zipfile


def download_image(url, output_path, max_retries=3):
    """Download an image from URL with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)

            return True

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   ⚠️  Attempt {attempt + 1} failed for {os.path.basename(output_path)}: {e}")
                time.sleep(1)  # Brief delay before retry
            else:
                print(f"   ❌ Failed to download {os.path.basename(output_path)}: {e}")
                return False

    return False


def extract_split_from_url(url):
    """Extract the split (train/val) from the S3 URL."""
    if '/train/' in url:
        return 'train'
    elif '/val/' in url:
        return 'val'
    elif '/test/' in url:
        return 'test'
    else:
        return 'unknown'


def check_image_exists(image_path):
    """Check if an image file already exists."""
    return os.path.exists(image_path)


def split_large_dataset(split_images, split_annotations, max_items=150):
    """Split a large dataset into multiple chunks if it exceeds max_items.

    Args:
        split_images: List of image entries
        split_annotations: List of annotation entries
        max_items: Maximum number of images per chunk (default: 150)

    Returns:
        List of tuples (chunk_images, chunk_annotations, chunk_index)
    """
    if len(split_images) <= max_items:
        return [(split_images, split_annotations, None)]

    # Calculate number of chunks needed
    num_chunks = (len(split_images) + max_items - 1) // max_items
    chunks = []

    print(f"   📦 Splitting {len(split_images)} images into {num_chunks} chunks...")

    for i in range(num_chunks):
        start_idx = i * max_items
        end_idx = min((i + 1) * max_items, len(split_images))

        chunk_images = split_images[start_idx:end_idx]

        # Get image IDs for this chunk
        chunk_image_ids = {img['id'] for img in chunk_images}

        # Filter annotations for this chunk
        chunk_annotations = [
            ann for ann in split_annotations
            if ann.get('image_id') in chunk_image_ids
        ]

        chunks.append((chunk_images, chunk_annotations, i))
        print(f"      • Chunk {i}: {len(chunk_images)} images, {len(chunk_annotations)} annotations")

    return chunks


def create_annotations_only(coco_file_path, output_dir, create_zip=False, split_filter=None):
    """Create only the annotation files in archive format without downloading images.
    For large datasets (>200 images), creates separate archives for each chunk.

    Args:
        coco_file_path: Path to COCO JSON file
        output_dir: Output directory for archive
        create_zip: Whether to create a ZIP file
        split_filter: Optional split to filter (train/val/test). If specified, only create
                     annotation for that split.
    """

    try:
        with open(coco_file_path, 'r') as f:
            coco_data = json.load(f)

        # Get dataset name from filename
        dataset_name = os.path.basename(coco_file_path).replace('_coco.json', '')

        # If split filter is specified, append it to dataset name
        if split_filter:
            dataset_name_with_split = f"{dataset_name}_{split_filter}"
        else:
            dataset_name_with_split = dataset_name

        print(f"📁 Processing dataset: {dataset_name}")
        if split_filter:
            print(f"🔍 Filter: Only creating {split_filter} split annotation")

        # Organize images by split (without downloading)
        images = coco_data.get("images", [])
        train_images = []
        val_images = []
        test_images = []

        print(f"📋 Processing {len(images)} image references...")

        for i, img in enumerate(images, 1):
            image_url = img.get("file_name")
            if not image_url:
                continue

            # Determine split from URL
            split = extract_split_from_url(image_url)

            # Extract filename from URL
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)

            # Ensure filename has extension
            if not filename or '.' not in filename:
                filename = f"image_{img.get('id', i)}.jpg"

            # Update image entry with local path (relative to images directory)
            img_copy = img.copy()

            # Determine split and add to appropriate list
            if split == 'train':
                img_copy["file_name"] = f"train/{filename}"
                train_images.append(img_copy)
            elif split == 'val':
                img_copy["file_name"] = f"val/{filename}"
                val_images.append(img_copy)
            elif split == 'test':
                img_copy["file_name"] = f"test/{filename}"
                test_images.append(img_copy)
            else:
                # Default to train if unknown
                img_copy["file_name"] = f"train/{filename}"
                train_images.append(img_copy)

        print(f"✅ Processed: {len(train_images)} train, {len(val_images)} val, {len(test_images)} test image references")

        # Create separate annotation files for each split
        results = {}
        all_archives = []

        # If split filter is set, only create annotation for that split
        splits_to_process = [(split_filter, eval(f"{split_filter}_images"))] if split_filter else [('train', train_images), ('val', val_images), ('test', test_images)]

        for split_name, split_images in splits_to_process:
            if not split_images:
                continue

            # Filter annotations for this split
            image_ids = {img['id'] for img in split_images}
            split_annotations = [
                ann for ann in coco_data.get('annotations', [])
                if ann.get('image_id') in image_ids
            ]

            # Split into chunks if too large (>150 images)
            chunks = split_large_dataset(split_images, split_annotations, max_items=150)

            # Track split results
            results[split_name] = {
                'images': len(split_images),
                'annotations': len(split_annotations),
                'archives': [],
                'chunks': len(chunks)
            }

            # Process each chunk - create separate archive for each
            for chunk_images, chunk_annotations, chunk_idx in chunks:
                # Determine archive name
                if chunk_idx is None:
                    # Single archive (not split)
                    archive_name = f"{dataset_name}_{split_name}_archive"
                    annotation_filename = f"{dataset_name}_{split_name}.json"
                else:
                    # Multiple archives (split into chunks)
                    archive_name = f"{dataset_name}_{split_name}{chunk_idx}_archive"
                    annotation_filename = f"{dataset_name}_{split_name}{chunk_idx}.json"

                # Create archive directory structure
                archive_dir = os.path.join(output_dir, archive_name)
                annotations_dir = os.path.join(archive_dir, "annotations")
                os.makedirs(annotations_dir, exist_ok=True)

                # Create split-specific COCO data
                split_coco_data = {
                    "info": {
                        **coco_data.get("info", {}),
                        "description": f"{coco_data.get('info', {}).get('description', '')} - {split_name.title()} Split (Annotations Only)",
                        "date_created": time.strftime("%Y-%m-%dT%H:%M:%S")
                    },
                    "licenses": coco_data.get("licenses", []),
                    "categories": coco_data.get("categories", []),
                    "images": chunk_images,
                    "annotations": chunk_annotations
                }

                # Save annotation file
                annotation_file = os.path.join(annotations_dir, annotation_filename)
                with open(annotation_file, 'w') as f:
                    json.dump(split_coco_data, f, indent=2)

                if chunk_idx is None:
                    print(f"💾 Saved {split_name} annotations: {annotation_file}")
                else:
                    print(f"💾 Saved {split_name} chunk {chunk_idx} annotations: {annotation_file}")

                # Create dataset info file for this archive
                info_file = os.path.join(archive_dir, "dataset_info.txt")
                with open(info_file, 'w') as f:
                    chunk_info = f" - Chunk {chunk_idx}" if chunk_idx is not None else ""
                    f.write(f"COCO Archive Dataset: {dataset_name} - {split_name.title()}{chunk_info} (Annotations Only)\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Original COCO file: {os.path.basename(coco_file_path)}\n")
                    f.write(f"Mode: Annotations only (no images downloaded)\n")
                    f.write(f"Split: {split_name}\n")
                    if chunk_idx is not None:
                        f.write(f"Chunk: {chunk_idx} of {len(chunks)}\n")
                    f.write("\n")
                    f.write(f"Image references: {len(chunk_images)}\n")
                    f.write(f"Annotations: {len(chunk_annotations)}\n")
                    f.write(f"Categories: {len(coco_data.get('categories', []))}\n\n")

                    f.write("Archive structure:\n")
                    f.write(f"├── annotations/\n")
                    f.write(f"│   └── {annotation_filename}\n")
                    f.write(f"└── dataset_info.txt   (this file)\n\n")

                    f.write("Category information:\n")
                    for cat in coco_data.get("categories", []):
                        f.write(f"- {cat.get('name')} (ID: {cat.get('id')})\n")

                print(f"📄 Created dataset info: {info_file}")

                # Create README for this archive
                readme_file = os.path.join(archive_dir, "README.md")
                with open(readme_file, 'w') as f:
                    chunk_title = f" - Chunk {chunk_idx}" if chunk_idx is not None else ""
                    f.write(f"# {dataset_name} - {split_name.title()}{chunk_title} Archive (Annotations Only)\n\n")
                    f.write(f"This archive contains COCO format annotation files (annotations only, no images).\n\n")
                    f.write(f"## Dataset Information\n\n")
                    f.write(f"- **Split**: {split_name}\n")
                    if chunk_idx is not None:
                        f.write(f"- **Chunk**: {chunk_idx} of {len(chunks)}\n")
                    f.write(f"- **Image References**: {len(chunk_images)}\n")
                    f.write(f"- **Annotations**: {len(chunk_annotations)} instances\n")
                    f.write(f"- **Categories**: {', '.join([cat.get('name', '') for cat in coco_data.get('categories', [])])}\n")
                    f.write(f"- **Created**: {time.strftime('%Y-%m-%d')}\n")
                    f.write(f"- **Mode**: Annotations only (no images downloaded)\n\n")
                    f.write(f"## Usage\n\n")
                    f.write(f"```python\n")
                    f.write(f"from torchvision.datasets import CocoDetection\n\n")
                    f.write(f"# Load this chunk (after downloading images)\n")
                    f.write(f"dataset = CocoDetection(\n")
                    f.write(f"    root='images/{split_name}/',\n")
                    f.write(f"    annFile='annotations/{annotation_filename}'\n")
                    f.write(f")\n")
                    f.write(f"```\n\n")

                print(f"📖 Created README: {readme_file}")

                # Create ZIP archive if requested
                zip_path = None
                if create_zip:
                    zip_filename = f"{archive_name}.zip"
                    zip_path = os.path.join(output_dir, zip_filename)
                    print(f"📦 Creating ZIP archive: {zip_path}")

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(archive_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_path = os.path.relpath(file_path, archive_dir)
                                zipf.write(file_path, arc_path)

                    print(f"✅ Created ZIP archive: {zip_path}")

                # Track this archive
                archive_info = {
                    'archive_dir': archive_dir,
                    'zip_path': zip_path,
                    'images': len(chunk_images),
                    'annotations': len(chunk_annotations),
                    'chunk_idx': chunk_idx
                }
                results[split_name]['archives'].append(archive_info)
                all_archives.append(archive_info)

        return {
            "archives": all_archives,
            "images_downloaded": 0,
            "images_failed": 0,
            "total_images": len(images),
            "total_annotations": len(coco_data.get("annotations", [])),
            "splits": results,
            "dataset_name": dataset_name,
            "annotations_only": True
        }

    except Exception as e:
        print(f"❌ Error creating annotations-only archive: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_archive_dataset(coco_file_path, output_dir, create_zip=False, split_filter=None):
    """Create an archive-format COCO dataset with train/val split.
    For large datasets (>150 images), creates separate archives for each chunk with their own images.

    Args:
        coco_file_path: Path to COCO JSON file
        output_dir: Output directory for archive
        create_zip: Whether to create a ZIP file
        split_filter: Optional split to filter (train/val/test). If specified, only that split's
                     images will be downloaded.
    """

    try:
        with open(coco_file_path, 'r') as f:
            coco_data = json.load(f)

        # Get dataset name from filename
        dataset_name = os.path.basename(coco_file_path).replace('_coco.json', '')

        print(f"📁 Processing dataset: {dataset_name}")
        if split_filter:
            print(f"🔍 Filter: Only downloading {split_filter} split images")

        # Organize images by split
        images = coco_data.get("images", [])
        train_images = []
        val_images = []
        test_images = []

        print(f"🔄 Processing {len(images)} images...")

        for i, img in enumerate(images, 1):
            image_url = img.get("file_name")
            if not image_url:
                continue

            # Determine split from URL
            split = extract_split_from_url(image_url)

            # Extract filename from URL
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)

            # Ensure filename has extension
            if not filename or '.' not in filename:
                filename = f"image_{img.get('id', i)}.jpg"

            # Store image info with URL for later downloading
            img_copy = img.copy()
            img_copy["file_name"] = f"{split}/{filename}"
            img_copy["_original_url"] = image_url  # Store original URL for downloading

            # Determine split and add to appropriate list
            if split == 'train':
                train_images.append(img_copy)
            elif split == 'val':
                val_images.append(img_copy)
            elif split == 'test':
                test_images.append(img_copy)
            else:
                # Default to train if unknown
                img_copy["file_name"] = f"train/{filename}"
                train_images.append(img_copy)

        print(f"✅ Organized: {len(train_images)} train, {len(val_images)} val, {len(test_images)} test images")

        # Create separate archives for each split
        results = {}
        all_archives = []
        total_successful = 0
        total_failed = 0

        # If split filter is set, only process that split
        splits_to_process = [(split_filter, eval(f"{split_filter}_images"))] if split_filter else [('train', train_images), ('val', val_images), ('test', test_images)]

        for split_name, split_images in splits_to_process:
            if not split_images:
                continue

            # Filter annotations for this split
            image_ids = {img['id'] for img in split_images}
            split_annotations = [
                ann for ann in coco_data.get('annotations', [])
                if ann.get('image_id') in image_ids
            ]

            # Split into chunks if too large (>150 images)
            chunks = split_large_dataset(split_images, split_annotations, max_items=150)

            # Track split results
            results[split_name] = {
                'images': len(split_images),
                'annotations': len(split_annotations),
                'archives': [],
                'chunks': len(chunks)
            }

            # Process each chunk - create separate archive with images for each
            for chunk_images, chunk_annotations, chunk_idx in chunks:
                # Determine archive name
                if chunk_idx is None:
                    # Single archive (not split)
                    archive_name = f"{dataset_name}_{split_name}_archive"
                    annotation_filename = f"{dataset_name}_{split_name}.json"
                else:
                    # Multiple archives (split into chunks)
                    archive_name = f"{dataset_name}_{split_name}{chunk_idx}_archive"
                    annotation_filename = f"{dataset_name}_{split_name}{chunk_idx}.json"

                # Create archive directory structure for this chunk
                archive_dir = os.path.join(output_dir, archive_name)
                images_dir = os.path.join(archive_dir, "images")
                annotations_dir = os.path.join(archive_dir, "annotations")
                split_images_dir = os.path.join(images_dir, split_name)

                os.makedirs(split_images_dir, exist_ok=True)
                os.makedirs(annotations_dir, exist_ok=True)

                print(f"\n📁 Creating archive: {archive_name}")
                if chunk_idx is not None:
                    print(f"   Processing chunk {chunk_idx} with {len(chunk_images)} images")

                # Download images for this chunk
                chunk_successful = 0
                chunk_failed = 0

                for i, img in enumerate(chunk_images, 1):
                    original_url = img.get("_original_url")
                    if not original_url:
                        continue

                    # Extract filename
                    filename = os.path.basename(img["file_name"])
                    output_path = os.path.join(split_images_dir, filename)

                    # Check if image already exists
                    if check_image_exists(output_path):
                        print(f"   ⏭️  [{i}/{len(chunk_images)}] Skipping: {filename} (already exists)")
                        chunk_successful += 1
                    else:
                        print(f"   📥 [{i}/{len(chunk_images)}] Downloading: {filename}")

                        if download_image(original_url, output_path):
                            chunk_successful += 1
                        else:
                            chunk_failed += 1

                total_successful += chunk_successful
                total_failed += chunk_failed

                print(f"   ✅ Downloaded: {chunk_successful}/{len(chunk_images)}")
                if chunk_failed > 0:
                    print(f"   ❌ Failed: {chunk_failed}")

                # Remove the temporary _original_url field from images before saving
                clean_chunk_images = []
                for img in chunk_images:
                    img_clean = img.copy()
                    img_clean.pop("_original_url", None)
                    clean_chunk_images.append(img_clean)

                # Create split-specific COCO data
                split_coco_data = {
                    "info": {
                        **coco_data.get("info", {}),
                        "description": f"{coco_data.get('info', {}).get('description', '')} - {split_name.title()} Split",
                        "date_created": time.strftime("%Y-%m-%dT%H:%M:%S")
                    },
                    "licenses": coco_data.get("licenses", []),
                    "categories": coco_data.get("categories", []),
                    "images": clean_chunk_images,
                    "annotations": chunk_annotations
                }

                # Save annotation file
                annotation_file = os.path.join(annotations_dir, annotation_filename)
                with open(annotation_file, 'w') as f:
                    json.dump(split_coco_data, f, indent=2)

                if chunk_idx is None:
                    print(f"💾 Saved {split_name} annotations: {annotation_file}")
                else:
                    print(f"💾 Saved {split_name} chunk {chunk_idx} annotations: {annotation_file}")

                # Create dataset info file for this archive
                info_file = os.path.join(archive_dir, "dataset_info.txt")
                with open(info_file, 'w') as f:
                    chunk_info = f" - Chunk {chunk_idx}" if chunk_idx is not None else ""
                    f.write(f"COCO Archive Dataset: {dataset_name} - {split_name.title()}{chunk_info}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Original COCO file: {os.path.basename(coco_file_path)}\n")
                    f.write(f"Split: {split_name}\n")
                    if chunk_idx is not None:
                        f.write(f"Chunk: {chunk_idx} of {len(chunks)}\n")
                    f.write("\n")
                    f.write(f"Images downloaded: {chunk_successful}/{len(chunk_images)}\n")
                    f.write(f"Total annotations: {len(chunk_annotations)}\n")
                    f.write(f"Categories: {len(coco_data.get('categories', []))}\n\n")

                    f.write("Archive structure:\n")
                    f.write(f"├── images/\n")
                    f.write(f"│   └── {split_name}/         ({chunk_successful} images)\n")
                    f.write(f"├── annotations/\n")
                    f.write(f"│   └── {annotation_filename}\n")
                    f.write(f"└── dataset_info.txt   (this file)\n\n")

                    f.write("Category information:\n")
                    for cat in coco_data.get("categories", []):
                        f.write(f"- {cat.get('name')} (ID: {cat.get('id')})\n")

                print(f"📄 Created dataset info: {info_file}")

                # Create README for this archive
                readme_file = os.path.join(archive_dir, "README.md")
                with open(readme_file, 'w') as f:
                    chunk_title = f" - Chunk {chunk_idx}" if chunk_idx is not None else ""
                    f.write(f"# {dataset_name} - {split_name.title()}{chunk_title} Archive\n\n")
                    f.write(f"This is a COCO format dataset archive.\n\n")
                    f.write(f"## Dataset Information\n\n")
                    f.write(f"- **Split**: {split_name}\n")
                    if chunk_idx is not None:
                        f.write(f"- **Chunk**: {chunk_idx} of {len(chunks)}\n")
                    f.write(f"- **Total Images**: {chunk_successful} downloaded images\n")
                    f.write(f"- **Total Annotations**: {len(chunk_annotations)} instances\n")
                    f.write(f"- **Categories**: {', '.join([cat.get('name', '') for cat in coco_data.get('categories', [])])}\n")
                    f.write(f"- **Created**: {time.strftime('%Y-%m-%d')}\n\n")
                    f.write(f"## Archive Structure\n\n")
                    f.write(f"```\n")
                    f.write(f"{archive_name}/\n")
                    f.write(f"├── images/\n")
                    f.write(f"│   └── {split_name}/\n")
                    f.write(f"│       ├── <image1.ext>\n")
                    f.write(f"│       ├── <image2.ext>\n")
                    f.write(f"│       └── ...\n")
                    f.write(f"├── annotations/\n")
                    f.write(f"│   └── {annotation_filename}\n")
                    f.write(f"├── dataset_info.txt\n")
                    f.write(f"└── README.md\n")
                    f.write(f"```\n\n")
                    f.write(f"## Usage\n\n")
                    f.write(f"```python\n")
                    f.write(f"from torchvision.datasets import CocoDetection\n\n")
                    f.write(f"dataset = CocoDetection(\n")
                    f.write(f"    root='images/{split_name}/',\n")
                    f.write(f"    annFile='annotations/{annotation_filename}'\n")
                    f.write(f")\n")
                    f.write(f"```\n\n")

                print(f"📖 Created README: {readme_file}")

                # Create ZIP archive if requested
                zip_path = None
                if create_zip:
                    zip_filename = f"{archive_name}.zip"
                    zip_path = os.path.join(output_dir, zip_filename)
                    print(f"📦 Creating ZIP archive: {zip_path}")

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(archive_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_path = os.path.relpath(file_path, archive_dir)
                                zipf.write(file_path, arc_path)

                    print(f"✅ Created ZIP archive: {zip_path}")

                # Track this archive
                archive_info = {
                    'archive_dir': archive_dir,
                    'zip_path': zip_path,
                    'images': chunk_successful,
                    'images_failed': chunk_failed,
                    'annotations': len(chunk_annotations),
                    'chunk_idx': chunk_idx
                }
                results[split_name]['archives'].append(archive_info)
                all_archives.append(archive_info)

        print(f"\n✅ Overall Downloaded: {total_successful}")
        print(f"❌ Overall Failed: {total_failed}")

        return {
            "archives": all_archives,
            "images_downloaded": total_successful,
            "images_failed": total_failed,
            "total_images": len(images),
            "total_annotations": len(coco_data.get("annotations", [])),
            "splits": results,
            "dataset_name": dataset_name
        }

    except Exception as e:
        print(f"❌ Error creating archive dataset: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create a COCO dataset in archive format with train/val organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates an archive-format COCO dataset by:
1. Downloading images and organizing them into train/val/test subdirectories
2. Creating split-specific annotation files (task_train.json, task_val.json, task_test.json)
3. For large datasets (>150 images per split), automatically splits into multiple archives
   (e.g., BipedLeg_train0_archive, BipedLeg_train1_archive, each with their own images)
4. Following the archive structure format
5. Optionally creating a ZIP archive for each split/chunk

Examples:
  # Download all splits (automatically splits large datasets)
  python create_archive_dataset.py coco_exports/QuadrupedFoot_coco.json --zip

  # Download only train split (creates BipedLeg_train0_archive, train1_archive, etc. if >150 images)
  python create_archive_dataset.py coco_exports/BipedLeg_coco.json --split train --zip

  # Download only val split
  python create_archive_dataset.py coco_exports/QuadrupedFoot_coco.json --split val --zip

  # Process all COCO files in directory
  python create_archive_dataset.py --all-coco coco_exports/ --output-dir ./archives --zip

  # Annotations only mode (also splits into separate archives for >150 images)
  python create_archive_dataset.py coco_exports/BipedLeg_coco.json --annotations-only --zip
        """
    )

    parser.add_argument(
        "coco_file",
        nargs="?",
        help="Path to COCO JSON file"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./archive_datasets",
        help="Output directory for archive datasets (default: ./archive_datasets)"
    )

    parser.add_argument(
        "--all-coco",
        type=str,
        help="Process all *_coco.json files in the specified directory"
    )

    parser.add_argument(
        "--zip",
        action="store_true",
        help="Create ZIP archive of the dataset"
    )

    parser.add_argument(
        "--annotations-only",
        action="store_true",
        help="Create only annotation files without downloading images"
    )

    parser.add_argument(
        "--split",
        type=str,
        choices=["train", "val", "test"],
        help="Only download images for specified split (train/val/test). Folder structure is maintained but other splits remain empty."
    )

    args = parser.parse_args()

    if not args.coco_file and not args.all_coco:
        print("❌ Must specify either a COCO file or --all-coco directory")
        return

    files_to_process = []

    if args.all_coco:
        # Process all COCO files in directory
        import glob
        pattern = os.path.join(args.all_coco, "*_coco.json")
        files_to_process = glob.glob(pattern)
        if not files_to_process:
            print(f"❌ No *_coco.json files found in {args.all_coco}")
            return
    else:
        # Process single file
        if not os.path.exists(args.coco_file):
            print(f"❌ File not found: {args.coco_file}")
            return
        files_to_process = [args.coco_file]

    print(f"🚀 Creating archive dataset(s) from {len(files_to_process)} file(s)...")
    print(f"📁 Output directory: {os.path.abspath(args.output_dir)}")
    if args.split:
        print(f"🔍 Split filter: Only downloading {args.split} split images")

    results = []
    for coco_file in files_to_process:
        print(f"\n📋 Processing: {os.path.basename(coco_file)}")

        if args.annotations_only:
            result = create_annotations_only(coco_file, args.output_dir, args.zip, args.split)
        else:
            result = create_archive_dataset(coco_file, args.output_dir, args.zip, args.split)

        if result:
            results.append(result)

    # Summary
    print(f"\n🎉 Archive Creation Summary:")
    print(f"   📋 COCO files processed: {len(files_to_process)}")
    print(f"   ✅ Archives created: {len(results)}")

    if results:
        total_images = sum(r['images_downloaded'] for r in results)
        total_failed = sum(r['images_failed'] for r in results)
        total_annotations = sum(r['total_annotations'] for r in results)

        print(f"\n📊 Totals:")
        print(f"   🖼️  Images downloaded: {total_images}")
        print(f"   ❌ Images failed: {total_failed}")
        print(f"   📝 Total annotations: {total_annotations}")

        print(f"\n📁 Created archives:")
        for result in results:
            mode_info = " (annotations only)" if result.get('annotations_only') else ""
            print(f"   • {result['dataset_name']}{mode_info}:")

            # If there are multiple archives (from splitting), list them
            if result.get('archives'):
                for archive_info in result['archives']:
                    chunk_label = f" (chunk {archive_info['chunk_idx']})" if archive_info['chunk_idx'] is not None else ""
                    print(f"      - {os.path.basename(archive_info['archive_dir'])}{chunk_label}")
                    if mode_info:
                        print(f"        • {archive_info['images']} image refs, {archive_info['annotations']} annotations")
                    else:
                        print(f"        • {archive_info['images']} images, {archive_info['annotations']} annotations")
                    if archive_info.get('zip_path'):
                        print(f"        • ZIP: {archive_info['zip_path']}")
            # Legacy support for old single-archive format
            elif result.get('archive_dir'):
                print(f"      - {result['archive_dir']}")
                if result.get('zip_path'):
                    print(f"        • ZIP: {result['zip_path']}")
                for split_name, split_info in result['splits'].items():
                    if split_info.get('chunks', 1) > 1:
                        if result.get('annotations_only'):
                            print(f"        • {split_name}: {split_info['images']} image refs, {split_info['annotations']} annotations ({split_info['chunks']} chunks)")
                        else:
                            print(f"        • {split_name}: {split_info['images']} images, {split_info['annotations']} annotations ({split_info['chunks']} chunks)")
                    else:
                        if result.get('annotations_only'):
                            print(f"        • {split_name}: {split_info['images']} image refs, {split_info['annotations']} annotations")
                        else:
                            print(f"        • {split_name}: {split_info['images']} images, {split_info['annotations']} annotations")

        print(f"\n🔗 Next steps:")
        print(f"   1. Navigate to your archive directory")
        print(f"   2. Use split-specific annotation files for training")
        print(f"   3. Check README.md for usage examples")
        if any(r.get('zip_path') for r in results):
            print(f"   4. Extract ZIP archives as needed")


if __name__ == "__main__":
    main()
