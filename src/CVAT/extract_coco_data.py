#!/usr/bin/env python3
"""
Extract image URLs and annotations from COCO files into separate text files.
"""

import json
import argparse
import os


def extract_from_coco(coco_file_path, output_dir=None):
    """Extract image URLs and annotations from a COCO file."""

    if output_dir is None:
        output_dir = os.path.dirname(coco_file_path)

    # Get base name for output files
    base_name = os.path.basename(coco_file_path).replace("_coco.json", "")

    try:
        with open(coco_file_path, 'r') as f:
            coco_data = json.load(f)

        # Extract image URLs
        images = coco_data.get("images", [])
        image_urls = [img.get("file_name") for img in images if img.get("file_name")]

        # Extract annotations
        annotations = coco_data.get("annotations", [])

        # Save image URLs to text file
        urls_file = os.path.join(output_dir, f"{base_name}_image_urls.txt")
        with open(urls_file, 'w') as f:
            for url in image_urls:
                f.write(f"{url}\n")

        print(f"✅ Saved {len(image_urls)} image URLs to: {urls_file}")

        # Save annotations to JSON file
        annotations_file = os.path.join(output_dir, f"{base_name}_annotations.json")
        with open(annotations_file, 'w') as f:
            json.dump(annotations, f, indent=2)

        print(f"✅ Saved {len(annotations)} annotations to: {annotations_file}")

        # Also create a simple text summary of annotations
        summary_file = os.path.join(output_dir, f"{base_name}_annotations_summary.txt")
        with open(summary_file, 'w') as f:
            f.write(f"Annotation Summary for {base_name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total annotations: {len(annotations)}\n\n")

            for i, ann in enumerate(annotations, 1):
                f.write(f"Annotation {i}:\n")
                f.write(f"  ID: {ann.get('id')}\n")
                f.write(f"  Image ID: {ann.get('image_id')}\n")
                f.write(f"  Category ID: {ann.get('category_id')}\n")
                f.write(f"  BBox: {ann.get('bbox')}\n")
                f.write(f"  Area: {ann.get('area')}\n")
                f.write(f"  Has Segmentation: {'Yes' if ann.get('segmentation') else 'No'}\n")
                if ann.get('segmentation'):
                    seg_count = len(ann['segmentation']) if isinstance(ann['segmentation'], list) else 1
                    f.write(f"  Segmentation Points: {seg_count} polygon(s)\n")
                f.write("\n")

        print(f"✅ Saved annotation summary to: {summary_file}")

        return {
            "urls_file": urls_file,
            "annotations_file": annotations_file,
            "summary_file": summary_file,
            "image_count": len(image_urls),
            "annotation_count": len(annotations)
        }

    except Exception as e:
        print(f"❌ Error processing {coco_file_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract image URLs and annotations from COCO files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script extracts image URLs and annotations from COCO format files
and saves them to separate text files for easy use.

Examples:
  python extract_coco_data.py coco_exports/QuadrupedFoot_coco.json
  python extract_coco_data.py coco_exports/QuadrupedFoot_coco.json --output-dir ./extracted_data
  python extract_coco_data.py --all-coco coco_exports/
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
        help="Output directory for extracted files (default: same as input file)"
    )

    parser.add_argument(
        "--all-coco",
        type=str,
        help="Process all *_coco.json files in the specified directory"
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

    print(f"🔄 Processing {len(files_to_process)} COCO file(s)...")

    results = []
    for coco_file in files_to_process:
        print(f"\n📋 Processing: {os.path.basename(coco_file)}")
        result = extract_from_coco(coco_file, args.output_dir)
        if result:
            results.append(result)

    # Summary
    print(f"\n🎉 Summary:")
    print(f"   📋 COCO files processed: {len(files_to_process)}")
    print(f"   ✅ Successfully extracted: {len(results)}")

    if results:
        total_images = sum(r['image_count'] for r in results)
        total_annotations = sum(r['annotation_count'] for r in results)
        print(f"\n📊 Totals:")
        print(f"   🖼️  Images: {total_images}")
        print(f"   📝 Annotations: {total_annotations}")

        print(f"\n📝 Generated files:")
        for result in results:
            base_name = os.path.basename(result['urls_file']).replace('_image_urls.txt', '')
            print(f"   • {base_name}:")
            print(f"     - Image URLs: {result['urls_file']}")
            print(f"     - Annotations: {result['annotations_file']}")
            print(f"     - Summary: {result['summary_file']}")


if __name__ == "__main__":
    main()
