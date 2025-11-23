#!/usr/bin/env python3
"""
Check when 'Multiple Instances' (result=1) first appears across different data splits.
Analyzes spin_val_parts, spin_train_parts, agreeTest, and main splits.
Tracks annotations needed to reach first and first 5 'Multiple Instances'.
"""

import argparse, json, re, os
import boto3
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Global tracking across all supercategories
GLOBAL_PROGRESSION_TRACKER = {
    "all_progressions": [],  # List of all progression indices
    "by_supercategory": {},  # Progression data per supercategory
    "global_stats": {}       # Overall statistics
}

# Flat file pattern: group_0_3IXQG4....json  -> group idx = 0
GROUP_RE = re.compile(r"group_(\d+)_.*\.json$")

# Define supercategory mappings (same as validate_and_merge.py)
SUPERCATEGORY_MAPPINGS = {
    "Quadruped": ["QuadrupedHead", "QuadrupedBody", "QuadrupedTail", "QuadrupedLeg"],
    "Biped": ["BipedHead", "BipedBody", "BipedArm", "BipedLeg", "BipedTail"],
    "Fish": ["FishHead", "FishBody", "FishFin", "FishTail"],
    "Bird": ["BirdHead", "BirdBody", "BirdWing", "BirdFoot", "BirdTail"],
    "Snake": ["SnakeHead", "SnakeBody"],
    "Reptile": ["ReptileHead", "ReptileBody", "ReptileFoot", "ReptileTail"],
    "Car": ["CarBody", "CarTire", "CarSideMirror"],
    "Bicycle": ["BicycleBody", "BicycleHead", "BicycleSeat", "BicycleTire", "BicycleTier"],
    "Boat": ["BoatBody", "BoatSail"],
    "Aeroplane": ["AeroplaneHead", "AeroplaneBody", "AeroplaneEngine", "AeroplaneWing", "AeroplaneTail"],
    "Bottle": ["BottleMouth", "BottleBody"],
}


def list_all_keys(s3, bucket, prefix):
    """List all keys under prefix (handles >1k via paginator)."""
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def find_groups_from_keys(keys, base_prefix):
    """Parse group indices from filenames like group_{idx}_{aid}.json."""
    groups = set()
    for k in keys:
        if not k.startswith(base_prefix):
            continue
        fname = k[len(base_prefix) :]  # strip base
        m = GROUP_RE.match(fname)
        if m:
            groups.add(int(m.group(1)))
    return sorted(groups)


def list_group_submission_keys(keys, base_prefix, group_idx):
    """Return all submission keys for a specific group idx."""
    prefix = f"{base_prefix}group_{group_idx}_"
    return sorted(
        [
            k
            for k in keys
            if k.startswith(prefix)
            and k.endswith(".json")
            and not k.endswith("_merged.json")
        ]
    )


def read_json(s3, bucket, key):
    """Read JSON from S3."""
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    return json.loads(body)


def check_annotation_agreement(submissions):
    """
    Check agreement for annotations (simplified version from validate_and_merge.py).
    Returns consensus results where agreement exists.
    """
    if not submissions:
        return []

    # Extract per-annotation results
    rows = []
    for s in submissions:
        anns = s.get("annotations", [])
        rows.append([a.get("result") for a in anns])

    # Pad to same length
    max_len = max(len(r) for r in rows) if rows else 0
    for r in rows:
        if len(r) < max_len:
            r.extend([None] * (max_len - len(r)))

    consensus_results = []

    for ann_idx in range(max_len):
        # Get all results for this annotation position
        ann_results = [row[ann_idx] for row in rows if row[ann_idx] is not None]

        if len(ann_results) < 2:
            # For single submissions in main/spin_train_parts, accept as-is
            if len(ann_results) == 1:
                consensus_results.append(ann_results[0])
            continue

        # Count occurrences
        from collections import Counter
        result_counts = Counter(ann_results)
        most_common = result_counts.most_common()

        # Check for agreement (unanimous or 2+ majority)
        if len(most_common) == 1 or most_common[0][1] >= 2:
            consensus_results.append(most_common[0][0])

    return consensus_results


def analyze_multiple_first_appearance(supercategory):
    """
    Analyze when 'Multiple Instances' (result=1) first appears in each split.
    """

    # S3 configuration
    s3 = boto3.client(
        "s3",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="us-east-1",
    )
    bucket = "spin-instance"

    # Get subcategories for the selected supercategory
    subcategories = SUPERCATEGORY_MAPPINGS.get(supercategory, [])

    if not subcategories:
        print(f"❌ Unknown supercategory: {supercategory}")
        return

    print(f"🔍 Checking 'Multiple Instances' first appearance in {supercategory}")
    print(f"📋 Subcategories: {', '.join(subcategories)}")

    # Track first appearances
    first_multiple_appearances = defaultdict(dict)
    split_stats = defaultdict(lambda: defaultdict(int))

    # Define splits to check with priority order (first found will be used)
    splits_to_check = [
        "agreeTest",        # Highest priority
        "spin_val_parts",   # Second priority
        "spin_test_parts",  # Third priority
        "main",             # Lowest priority
        # "spin_train_parts", # Commented out - typically not used
    ]

    print("\n🔍 Analyzing splits for first 'Multiple Instances' appearance...")
    print("Note: Only ONE split per category will be processed (priority: agreeTest > spin_val_parts > spin_test_parts > main)")
    print("=" * 80)

    for subcategory in subcategories:
        print(f"\n📁 Processing category: {subcategory}")

        category_first_multiples = {}

        # Find the first available split for this category (priority-based selection)
        selected_split = None
        for split in splits_to_check:
            base_prefix = f"HITs/{subcategory}/{split}/live/"

            try:
                # Check if this split has data
                all_keys = list_all_keys(s3, bucket, base_prefix)
                if all_keys:
                    # Find groups to verify there's actual data
                    groups = find_groups_from_keys(all_keys, base_prefix)
                    if groups:
                        selected_split = split
                        print(f"   ✓ Selected split: {split} (found {len(groups)} groups)")
                        break
            except Exception as e:
                print(f"   ❌ Error checking {split}: {e}")
                continue

        if not selected_split:
            print(f"   ❌ No valid splits found for {subcategory}")
            continue

        # Process only the selected split
        split = selected_split
        base_prefix = f"HITs/{subcategory}/{split}/live/"

        try:
            # List all files in this path (re-getting keys for processing)
            all_keys = list_all_keys(s3, bucket, base_prefix)

            if not all_keys:
                print(f"   {split}: No files found")
                continue

            # Find groups
            groups = find_groups_from_keys(all_keys, base_prefix)

            if not groups:
                print(f"   {split}: No groups found")
                continue

            print(f"   {split}: Found {len(groups)} groups")

            # Track annotations sequentially without group-based indexing
            first_multiple_annotation_count = None
            first_5_multiples_annotation_count = None
            total_annotations = 0
            multiple_count = 0

            for group_idx in sorted(groups):
                sub_keys = list_group_submission_keys(all_keys, base_prefix, group_idx)

                if not sub_keys:
                    continue

                # Load submissions
                submissions = []
                for key in sub_keys:
                    try:
                        submission = read_json(s3, bucket, key)
                        submissions.append(submission)
                    except Exception as e:
                        print(f"     ⚠️  Error reading {key}: {e}")
                        continue

                if not submissions:
                    continue

                # For single submission splits (main, spin_train_parts), handle differently
                if split in ["main", "spin_train_parts"] and len(submissions) == 1:
                    # Single submission - take results directly
                    submission = submissions[0]
                    results = [ann.get("result") for ann in submission.get("annotations", [])]
                    consensus_results = [r for r in results if r is not None]
                else:
                    # Multiple submissions - check agreement
                    consensus_results = check_annotation_agreement(submissions)

                # Check for Multiple Instances (result=1) in consensus results
                for ann_idx, result in enumerate(consensus_results):
                    total_annotations += 1
                    if result == 1:  # Multiple Instances
                        multiple_count += 1
                        if first_multiple_annotation_count is None:
                            first_multiple_annotation_count = total_annotations
                            print(f"     🎯 FIRST Multiple Instance found after {total_annotations} annotations (group {group_idx}, annotation {ann_idx})")

                        # Track when we reach 5 multiple instances
                        if multiple_count == 5 and first_5_multiples_annotation_count is None:
                            first_5_multiples_annotation_count = total_annotations
                            print(f"     🎯 5th Multiple Instance reached after {total_annotations} annotations (group {group_idx}, annotation {ann_idx})")
                            break  # Stop counting once we reach 5 multiples

                # Break out of group loop if we've reached 5 multiples
                if multiple_count >= 5:
                    break

            # Store results for this category (single split only now)
            split_stats[subcategory][f"{split}_total_annotations"] = total_annotations
            split_stats[subcategory][f"{split}_multiple_count"] = multiple_count
            split_stats[subcategory][f"{split}_multiple_rate"] = (multiple_count / total_annotations * 100) if total_annotations > 0 else 0.0

            if first_multiple_annotation_count is not None:
                category_first_multiples[split] = {
                    "first_multiple_at_annotation": first_multiple_annotation_count,
                    "annotations_to_5_multiples": first_5_multiples_annotation_count,
                    "total_annotations": total_annotations,
                    "multiple_count": multiple_count,
                    "multiple_rate": round((multiple_count / total_annotations * 100), 2) if total_annotations > 0 else 0.0,
                    "reached_5_multiples": first_5_multiples_annotation_count is not None
                }
                print(f"     📊 {split}: First multiple after {first_multiple_annotation_count} annotations")
                if first_5_multiples_annotation_count is not None:
                    print(f"     📊 {split}: 5 multiples reached after {first_5_multiples_annotation_count} annotations")
                print(f"     📊 {split}: Total: {multiple_count}/{total_annotations} ({category_first_multiples[split]['multiple_rate']:.1f}%)")

                # Add to global tracker
                GLOBAL_PROGRESSION_TRACKER["all_progressions"].append({
                        "supercategory": supercategory,
                        "subcategory": subcategory,
                    "split": split,
                    "first_multiple_at_annotation": first_multiple_annotation_count,
                    "annotations_to_5_multiples": first_5_multiples_annotation_count,
                    "multiple_rate": category_first_multiples[split]['multiple_rate'],
                    "reached_5_multiples": first_5_multiples_annotation_count is not None
                })
            else:
                print(f"     📊 {split}: No multiple instances found ({total_annotations} annotations checked)")

        except Exception as e:
            print(f"   ❌ Error processing {subcategory}/{split}: {e}")
            continue        # Store category results
        if category_first_multiples:
            first_multiple_appearances[subcategory] = category_first_multiples

    # Create summary report
    print("\n" + "=" * 80)
    print("📈 FIRST 'MULTIPLE INSTANCES' APPEARANCE SUMMARY")
    print("=" * 80)

    # Print summary table
    print(f"{'Category':<18} {'Split':<18} {'1st Multiple@':<14} {'5 Multiples@':<14} {'Multi Rate%':<12} {'Status':<10}")
    print("-" * 105)

    summary_data = []
    for subcategory in subcategories:
        if subcategory in first_multiple_appearances:
            for split in splits_to_check:
                if split in first_multiple_appearances[subcategory]:
                    data = first_multiple_appearances[subcategory][split]
                    first_at = data.get('first_multiple_at_annotation')
                    five_at = data.get('annotations_to_5_multiples')

                    # Convert None values to "N/A" for display
                    first_at_display = str(first_at) if first_at is not None else "N/A"
                    five_at_display = str(five_at) if five_at is not None else "N/A"

                    print(f"{subcategory:<18} {split:<18} {first_at_display:<14} {five_at_display:<14} {data['multiple_rate']:<12.1f} {'FOUND':<10}")
                    summary_data.append({
                        "category": subcategory,
                        "split": split,
                        "first_multiple_at_annotation": data.get("first_multiple_at_annotation"),
                        "annotations_to_5_multiples": data.get("annotations_to_5_multiples"),
                        "reached_5_multiples": data.get("reached_5_multiples", False),
                        "total_annotations": data["total_annotations"],
                        "multiple_count": data["multiple_count"],
                        "multiple_rate": data["multiple_rate"]
                    })
                else:
                    # Check if we have stats but no multiples found
                    if f"{split}_total_annotations" in split_stats[subcategory] and split_stats[subcategory][f"{split}_total_annotations"] > 0:
                        print(f"{subcategory:<18} {split:<18} {'N/A':<14} {'N/A':<14} {'0.0':<12} {'NO MULTI':<10}")
                        summary_data.append({
                            "category": subcategory,
                            "split": split,
                            "first_multiple_at_annotation": None,
                            "annotations_to_10_multiples": None,
                            "reached_10_multiples": False,
                            "total_annotations": split_stats[subcategory][f"{split}_total_annotations"],
                            "multiple_count": 0,
                            "multiple_rate": 0.0
                        })
                    else:
                        print(f"{subcategory:<18} {split:<18} {'N/A':<14} {'N/A':<14} {'N/A':<12} {'NO DATA':<10}")
        else:
            # No multiples found in any split for this category
            for split in splits_to_check:
                if f"{split}_total_annotations" in split_stats[subcategory] and split_stats[subcategory][f"{split}_total_annotations"] > 0:
                    print(f"{subcategory:<18} {split:<18} {'N/A':<14} {'N/A':<14} {'0.0':<12} {'NO MULTI':<10}")
                else:
                    print(f"{subcategory:<18} {split:<18} {'N/A':<14} {'N/A':<14} {'N/A':<12} {'NO DATA':<10}")

    print("-" * 105)

    # Store supercategory data in global tracker
    if supercategory not in GLOBAL_PROGRESSION_TRACKER["by_supercategory"]:
        GLOBAL_PROGRESSION_TRACKER["by_supercategory"][supercategory] = {
            "progressions": [],
            "avg_first_multiple": 0.0,
            "avg_multiple_rate": 0.0,
            "total_first_multiples": 0
        }

    # Calculate supercategory statistics
    supercategory_first_multiples = [item["first_multiple_at_annotation"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item["supercategory"] == supercategory and item["first_multiple_at_annotation"] is not None]
    supercategory_rates = [item["multiple_rate"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item["supercategory"] == supercategory and item["first_multiple_at_annotation"] is not None]
    supercategory_5_multiples = [item["annotations_to_5_multiples"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item["supercategory"] == supercategory and item.get("annotations_to_5_multiples") is not None]

    if supercategory_first_multiples:
        GLOBAL_PROGRESSION_TRACKER["by_supercategory"][supercategory].update({
            "first_multiples_annotations": supercategory_first_multiples,
            "avg_first_multiple": sum(supercategory_first_multiples) / len(supercategory_first_multiples),
            "avg_multiple_rate": sum(supercategory_rates) / len(supercategory_rates) if supercategory_rates else 0.0,
            "total_first_multiples": len(supercategory_first_multiples),
            "min_first_multiple": min(supercategory_first_multiples),
            "max_first_multiple": max(supercategory_first_multiples),
            "splits_reaching_5_multiples": len(supercategory_5_multiples),
            "avg_annotations_to_5_multiples": sum(supercategory_5_multiples) / len(supercategory_5_multiples) if supercategory_5_multiples else 0.0
        })

        print(f"\n📊 {supercategory} SUPERCATEGORY SUMMARY:")
        print(f"   • First multiples found: {len(supercategory_first_multiples)}")
        print(f"   • Average annotations to first multiple: {GLOBAL_PROGRESSION_TRACKER['by_supercategory'][supercategory]['avg_first_multiple']:.1f}")
        print(f"   • Average multiple rate: {GLOBAL_PROGRESSION_TRACKER['by_supercategory'][supercategory]['avg_multiple_rate']:.2f}%")
        print(f"   • Fastest to first multiple: {min(supercategory_first_multiples)} annotations")
        print(f"   • Slowest to first multiple: {max(supercategory_first_multiples)} annotations")
        print(f"   • Splits reaching 5 multiples: {len(supercategory_5_multiples)}")
        if supercategory_5_multiples:
            print(f"   • Average annotations to reach 5 multiples: {GLOBAL_PROGRESSION_TRACKER['by_supercategory'][supercategory]['avg_annotations_to_5_multiples']:.1f}")    # Save detailed results
    output_dir = f"data/analytics/parts/{supercategory}"
    os.makedirs(output_dir, exist_ok=True)

    full_report = {
        "supercategory": supercategory,
        "analysis_timestamp": datetime.now().isoformat(),
        "analysis_type": "first_multiple_appearance",
        "splits_analyzed": splits_to_check,
        "subcategories": subcategories,
        "first_appearances": dict(first_multiple_appearances),
        "split_statistics": dict(split_stats),
        "summary_data": summary_data,
        "supercategory_stats": GLOBAL_PROGRESSION_TRACKER["by_supercategory"][supercategory] if supercategory in GLOBAL_PROGRESSION_TRACKER["by_supercategory"] else {}
    }

    report_file = os.path.join(output_dir, f'{supercategory}_first_multiple_appearance.json')
    with open(report_file, 'w') as f:
        json.dump(full_report, f, indent=2)

    print(f"\n💾 First multiple appearance analysis saved to '{report_file}'")

    # Print insights
    print("\n📊 KEY INSIGHTS:")
    earliest_by_split = defaultdict(list)

    for item in summary_data:
        earliest_by_split[item["split"]].append((item["category"]))

    for split in splits_to_check:
        if split in earliest_by_split and earliest_by_split[split]:
            earliest_cat = min(earliest_by_split[split], key=lambda x: x[1])
            print(f"  • {split}: Earliest multiple in {earliest_cat}")
        else:
            print(f"  • {split}: No multiple instances found")

    return full_report


def print_global_summary():
    """Print global summary statistics across all supercategories"""
    if not GLOBAL_PROGRESSION_TRACKER["all_progressions"]:
        print("\n📊 GLOBAL SUMMARY: No progression data available")
        return

    all_first_multiples = [item["first_multiple_at_annotation"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item["first_multiple_at_annotation"] is not None]
    all_rates = [item["multiple_rate"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item["first_multiple_at_annotation"] is not None]
    all_5_multiples = [item["annotations_to_5_multiples"] for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"] if item.get("annotations_to_5_multiples") is not None]

    if not all_first_multiples:
        print("\n📊 GLOBAL SUMMARY: No valid first multiple data found")
        return

    # Calculate global statistics
    GLOBAL_PROGRESSION_TRACKER["global_stats"] = {
        "total_first_multiples_found": len(all_first_multiples),
        "global_avg_first_multiple": sum(all_first_multiples) / len(all_first_multiples),
        "global_avg_multiple_rate": sum(all_rates) / len(all_rates) if all_rates else 0.0,
        "global_min_first_multiple": min(all_first_multiples),
        "global_max_first_multiple": max(all_first_multiples),
        "global_median_first_multiple": sorted(all_first_multiples)[len(all_first_multiples)//2],
        "splits_reaching_5_multiples": len(all_5_multiples),
        "global_avg_annotations_to_5_multiples": sum(all_5_multiples) / len(all_5_multiples) if all_5_multiples else 0.0
    }

    print("\n" + "=" * 100)
    print("🌍 GLOBAL SUMMARY ACROSS ALL SUPERCATEGORIES")
    print("=" * 100)
    print(f"Total first multiples found across all supercategories: {GLOBAL_PROGRESSION_TRACKER['global_stats']['total_first_multiples_found']}")
    print(f"Global average annotations to first multiple: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_avg_first_multiple']:.2f}")
    print(f"Global average multiple rate: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_avg_multiple_rate']:.2f}%")
    print(f"Fastest global first multiple: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_min_first_multiple']} annotations")
    print(f"Slowest global first multiple: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_max_first_multiple']} annotations")
    print(f"Median global first multiple: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_median_first_multiple']} annotations")
    print(f"Splits that reached 5 multiples: {GLOBAL_PROGRESSION_TRACKER['global_stats']['splits_reaching_5_multiples']}")
    if all_5_multiples:
        print(f"Global average annotations to reach 5 multiples: {GLOBAL_PROGRESSION_TRACKER['global_stats']['global_avg_annotations_to_5_multiples']:.2f}")

    print(f"\n📋 PER-SUPERCATEGORY BREAKDOWN:")
    print(f"{'Supercategory':<15} {'First Multiples':<15} {'Avg 1st Multi':<14} {'Avg Multi Rate%':<16} {'Reached 5+':<12} {'Avg to 5+':<12}")
    print("-" * 100)

    for supercat, stats in GLOBAL_PROGRESSION_TRACKER["by_supercategory"].items():
        if stats["total_first_multiples"] > 0:
            reached_5 = stats.get("splits_reaching_5_multiples", 0)
            avg_to_5 = f"{stats.get('avg_annotations_to_5_multiples', 0.0):.1f}" if reached_5 > 0 else "N/A"
            print(f"{supercat:<15} {stats['total_first_multiples']:<15} {stats['avg_first_multiple']:<14.2f} {stats['avg_multiple_rate']:<16.2f} {reached_5:<12} {avg_to_5:<12}")

    print("-" * 110)


def generate_5_multiples_histogram():
    """Generate modern histogram for annotations needed to reach 5+ multiples"""
    if not GLOBAL_PROGRESSION_TRACKER["all_progressions"]:
        print("\n📊 HISTOGRAM: No progression data available")
        return

    # Collect data with special handling for val/test split averaging
    category_data = defaultdict(list)  # category -> list of (split, annotations_to_5)

    for item in GLOBAL_PROGRESSION_TRACKER["all_progressions"]:
        if item.get("annotations_to_5_multiples") is not None:
            category = f"{item['supercategory']}_{item['subcategory']}"
            split = item['split']
            annotations = item['annotations_to_5_multiples']
            category_data[category].append((split, annotations))

    if not category_data:
        print("\n📊 HISTOGRAM: No data for categories reaching 5+ multiples")
        return

    # Process data: average val/test splits for same category
    final_values = []
    category_details = []

    for category, split_data in category_data.items():
        # Group by split type
        val_test_values = []
        other_values = []

        for split, annotations in split_data:
            if split in ['spin_val_parts', 'spin_test_parts']:
                val_test_values.append(annotations)
            else:
                other_values.append(annotations)

        # Average val/test if both exist, otherwise use individual values
        if len(val_test_values) > 1:
            avg_val_test = sum(val_test_values) / len(val_test_values)
            final_values.append(avg_val_test)
            category_details.append(f"{category.replace('_', ' ')}")
        elif len(val_test_values) == 1:
            final_values.append(val_test_values[0])
            category_details.append(f"{category.replace('_', ' ')}")

        # Add other splits individually
        for annotations in other_values:
            final_values.append(annotations)
            category_details.append(f"{category.replace('_', ' ')}")

    if not final_values:
        print("\n📊 HISTOGRAM: No valid data after processing")
        return

    # Calculate statistics
    avg_annotations = np.mean(final_values)
    median_annotations = np.median(final_values)

    # Set style for modern look
    plt.style.use('default')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Main histogram
    n_bins = min(25, max(8, len(final_values) // 2))
    n, bins, patches = ax1.hist(final_values, bins=n_bins, alpha=0.7, edgecolor='white',
                               color='#4A90E2', linewidth=1.2)

    # Color the bars with a gradient
    cm = plt.cm.viridis
    for i, (patch, height) in enumerate(zip(patches, n)):
        patch.set_facecolor(cm(i / len(patches)))
        patch.set_alpha(0.8)

    # Add statistics lines
    ax1.axvline(avg_annotations, color='#E74C3C', linestyle='--', linewidth=3,
                label=f'Mean: {avg_annotations:.1f}', alpha=0.9)
    ax1.axvline(median_annotations, color='#F39C12', linestyle='-.', linewidth=3,
                label=f'Median: {median_annotations:.1f}', alpha=0.9)

    # Formatting main plot
    ax1.set_xlabel('Annotations Needed to Reach 5+ Multiples', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=14, fontweight='bold')
    ax1.set_title('Distribution of Annotations Needed to Reach 5+ Multiple Instances\n' +
                  f'Data Points: {len(final_values)} categories | Mean: {avg_annotations:.1f} | Range: {min(final_values):.0f}-{max(final_values):.0f}',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3, linestyle='-')
    ax1.set_facecolor('#F8F9FA')

    # Individual data points strip plot
    y_positions = np.random.normal(0, 0.1, len(final_values))  # Add some jitter

    for i, (value, detail) in enumerate(zip(final_values, category_details)):
        ax2.scatter(value, y_positions[i], c='#4A90E2',
                   s=100, alpha=0.8, edgecolors='white', linewidth=1)

    ax2.set_xlabel('Annotations Count', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Individual\nData Points', fontsize=12, fontweight='bold')
    ax2.set_ylim(-0.5, 0.5)
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.set_facecolor('#F8F9FA')

    # Add statistics box
    stats_text = (f'Statistics:\n'
                 f'Mean: {avg_annotations:.1f}\n'
                 f'Median: {median_annotations:.1f}\n'
                 f'Std Dev: {np.std(final_values):.1f}\n'
                 f'Min: {min(final_values):.0f}\n'
                 f'Max: {max(final_values):.0f}\n'
                 f'Q1: {np.percentile(final_values, 25):.1f}\n'
                 f'Q3: {np.percentile(final_values, 75):.1f}')

    ax1.text(0.98, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='gray'))

    plt.tight_layout()

    # Save the plot
    histogram_path = 'annotations_to_5_multiples_histogram.png'
    svg_path = 'annotations_to_5_multiples_histogram.svg'
    plt.savefig(histogram_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(svg_path, bbox_inches='tight', facecolor='white')
    plt.show()

    print(f"\n📊 MODERN HISTOGRAM GENERATED")
    print(f"📁 Saved as: {histogram_path} and {svg_path}")
    print(f"📈 Data points: {len(final_values)} categories")
    print(f"📊 Mean annotations to reach 10+ multiples: {avg_annotations:.1f}")
    print(f"📊 Median annotations to reach 10+ multiples: {median_annotations:.1f}")
    print(f"� Standard deviation: {np.std(final_values):.1f}")
    print(f"�📋 Range: {min(final_values):.0f} - {max(final_values):.0f} annotations")

    # Print detailed breakdown sorted by value
    print(f"\n📋 DETAILED BREAKDOWN (sorted by annotation count):")
    sorted_data = sorted(zip(final_values, category_details))
    for i, (value, detail) in enumerate(sorted_data):
        print(f"  {i+1:2d}. {value:4.0f} annotations | {detail}")

    return histogram_path


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(
        description="Check when 'Multiple Instances' first appears across data splits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available supercategories:
{chr(10).join([f"  - {cat}: {', '.join(subs)}" for cat, subs in SUPERCATEGORY_MAPPINGS.items()])}

Examples:
  python {os.path.basename(__file__)} --supercategory Quadruped
  python {os.path.basename(__file__)} --all-supercategories
  python {os.path.basename(__file__)} --all-supercategories --histogram
        """
    )

    parser.add_argument(
        "--supercategory", "-s",
        type=str,
        choices=list(SUPERCATEGORY_MAPPINGS.keys()),
        help="Supercategory to analyze"
    )

    parser.add_argument(
        "--all-supercategories", "-a",
        action="store_true",
        help="Analyze all supercategories sequentially"
    )

    parser.add_argument(
        "--histogram",
        action="store_true",
        help="Generate histogram for annotations to reach 10+ multiples (only with --all-supercategories)"
    )

    args = parser.parse_args()

    if not args.supercategory and not args.all_supercategories:
        print("❌ Error: Please specify a supercategory with --supercategory or use --all-supercategories")
        parser.print_help()
        return

    print("🚀 Starting 'Multiple Instances' First Appearance Analysis...")

    if args.all_supercategories:
        for supercat in SUPERCATEGORY_MAPPINGS.keys():
            print("\n" + "-" * 80)
            analyze_multiple_first_appearance(supercat)

        # Print global summary after analyzing all supercategories
        print_global_summary()

        # Generate histogram if requested
        if args.histogram:
            print("\n" + "=" * 80)
            generate_5_multiples_histogram()

        print("\n✅ Analysis complete for ALL supercategories!")
    else:
        analyze_multiple_first_appearance(args.supercategory)

        if args.histogram:
            print("⚠️  Histogram generation requires --all-supercategories flag")

        print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
