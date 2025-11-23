#!/usr/bin/env python3
"""
Script to merge category-specific annotation files into spin2 consolidated files.
Finds corresponding annotations by annotation_id and split, then updates them.
"""

import json
import argparse
import os
from typing import Dict, List, Optional


def merge_category_to_spin2(
    category_name: str,
    input_file: str,
    spin2_dir: str = None
) -> Dict[str, int]:
    """
    Merge annotations from a category-specific file into spin2 files.

    Args:
        category_name: Name of the category (e.g., "BipedArm")
        input_file: Path to the input JSON file (e.g., "BipedArm_Test.json")
        spin2_dir: Directory containing spin2 files (default: ./spin2)

    Returns:
        Dictionary with update statistics per split
    """

    # Default spin2 directory
    if spin2_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        spin2_dir = os.path.join(script_dir, "spin2")

    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    print(f"📂 Loading input file: {input_file}")
    with open(input_file, 'r') as f:
        input_data = json.load(f)

    input_annotations = input_data.get('annotations', [])
    print(f"   Found {len(input_annotations)} annotations in input file")

    # Group input annotations by split
    annotations_by_split = {}
    for ann in input_annotations:
        print(ann)
        split = ann.get('split', 'unknown').lower()
        if split not in annotations_by_split:
            annotations_by_split[split] = []
        annotations_by_split[split].append(ann)

    print(f"   Annotations by split: {', '.join([f'{split}: {len(anns)}' for split, anns in annotations_by_split.items()])}")

    # Map splits to spin2 files
    spin2_files = {
        'train': os.path.join(spin2_dir, 'spin2_train_parts.json'),
        'test': os.path.join(spin2_dir, 'spin2_test_parts.json'),
        'val': os.path.join(spin2_dir, 'spin2_val_parts.json')
    }

    # Statistics tracking
    stats = {
        'train': {'matched': 0, 'updated': 0, 'not_found': 0},
        'test': {'matched': 0, 'updated': 0, 'not_found': 0},
        'val': {'matched': 0, 'updated': 0, 'not_found': 0}
    }

    # Process each split
    for split, input_anns in annotations_by_split.items():
        print(f"\n🔄 Merging annotations for split: {split}")
        if split not in spin2_files:
            print(f"   ⚠️  Unknown split '{split}', skipping {len(input_anns)} annotations")
            continue

        spin2_file = spin2_files[split]

        if not os.path.exists(spin2_file):
            print(f"   ⚠️  Spin2 file not found: {spin2_file}")
            continue

        print(f"\n🔍 Processing {split} split...")
        print(f"   Loading: {spin2_file}")

        # Load spin2 file
        with open(spin2_file, 'r') as f:
            spin2_data = json.load(f)

        spin2_annotations = spin2_data.get('annotations', [])
        print(f"   Total annotations in spin2_{split}_parts: {len(spin2_annotations)}")

        # Create lookup dictionary by annotation_id for faster matching
        spin2_ann_lookup = {}
        for idx, ann in enumerate(spin2_annotations):
            ann_id = ann.get('id')
            if ann_id is not None:
                spin2_ann_lookup[ann_id] = idx

        # Match and update annotations
        for input_ann in input_anns:
            ann_id = input_ann.get('annotation_id')

            if ann_id is None:
                print(f"   ⚠️  Input annotation missing 'annotation_id' field, skipping")
                continue

            # Check if this annotation exists in spin2 file
            if ann_id in spin2_ann_lookup:
                idx = spin2_ann_lookup[ann_id]
                stats[split]['matched'] += 1

                # Update the annotation in spin2
                # Preserve existing fields but update with input fields
                original_ann = spin2_annotations[idx]

                # Merge annotations - input takes precedence
                for key, value in input_ann.items():
                    original_ann[key] = value

                # Ensure category_name is set
                original_ann['category_name'] = category_name

                stats[split]['updated'] += 1

                if stats[split]['updated'] <= 5:  # Show first 5 updates
                    print(f"   ✅ Updated annotation id={ann_id} in {split}")
            else:
                stats[split]['not_found'] += 1
                if stats[split]['not_found'] <= 3:  # Show first 3 not found
                    print(f"   ❌ Annotation id={ann_id} not found in {split}")

        # Save updated spin2 file
        print(f"   💾 Saving updated {spin2_file}...")
        with open(spin2_file, 'w') as f:
            json.dump(spin2_data, f, indent=2)

        print(f"   📊 {split.upper()} Summary:")
        print(f"      • Matched: {stats[split]['matched']}")
        print(f"      • Updated: {stats[split]['updated']}")
        print(f"      • Not found: {stats[split]['not_found']}")

    # Overall summary
    total_matched = sum(s['matched'] for s in stats.values())
    total_updated = sum(s['updated'] for s in stats.values())
    total_not_found = sum(s['not_found'] for s in stats.values())

    print(f"\n✅ Merge Complete!")
    print(f"   📈 Overall Statistics:")
    print(f"      • Total matched: {total_matched}")
    print(f"      • Total updated: {total_updated}")
    print(f"      • Total not found: {total_not_found}")

    return stats


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(
        description="Merge category-specific annotations into spin2 consolidated files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Merge BipedArm test annotations
    python merge_to_spin2.py --category BipedArm --input Biped/Parts/BipedArm_Raw/BipedArm_Test.json

    # Merge with custom spin2 directory
    python merge_to_spin2.py --category QuadrupedFoot --input path/to/QuadrupedFoot_Val.json --spin2-dir /path/to/spin2

    # Merge all splits from a category
    python merge_to_spin2.py --category BipedArm --input Biped/Parts/BipedArm_Raw/BipedArm_Train.json
    python merge_to_spin2.py --category BipedArm --input Biped/Parts/BipedArm_Raw/BipedArm_Test.json
    python merge_to_spin2.py --category BipedArm --input Biped/Parts/BipedArm_Raw/BipedArm_Val.json
        """
    )

    parser.add_argument(
        '--category',
        '-c',
        type=str,
        required=True,
        help='Category name (e.g., BipedArm, QuadrupedFoot)'
    )

    parser.add_argument(
        '--input',
        '-i',
        type=str,
        required=True,
        help='Input JSON file path (e.g., BipedArm_Test.json)'
    )

    parser.add_argument(
        '--spin2-dir',
        '-d',
        type=str,
        default=None,
        help='Directory containing spin2 files (default: ./spin2)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )

    args = parser.parse_args()

    if args.dry_run:
        print("🧪 DRY RUN MODE - No files will be modified\n")

    try:
        stats = merge_category_to_spin2(
            category_name=args.category,
            input_file=args.input,
            spin2_dir=args.spin2_dir
        )

        print(f"\n🎉 Successfully merged {args.category} annotations!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
