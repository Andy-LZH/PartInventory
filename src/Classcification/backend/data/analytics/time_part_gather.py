#!/usr/bin/env python3
import argparse, json, re, os
import boto3
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
import seaborn as sns
from dateutil import parser as date_parser

# Flat file pattern: group_0_3IXQG4....json  -> group idx = 0
GROUP_RE = re.compile(r"group_(\d+)_(.+)\.json$")

# Define supercategory mappings
SUPERCATEGORY_MAPPINGS = {
    "Quadruped": ["QuadrupedHead", "QuadrupedBody", "QuadrupedFoot", "QuadrupedTail"],
    "Biped": ["BipedHead", "BipedBody", "BipedHand", "BipedFoot", "BipedTail"],
    "Fish": ["FishHead", "FishBody", "FishFin", "FishTail"],
    "Bird": ["BirdHead", "BirdBody", "BirdWing", "BirdFoot", "BirdTail"],
    "Snake": ["SnakeHead", "SnakeBody"],
    "Reptile": ["ReptileHead", "ReptileBody", "ReptileFoot", "ReptileTail"],
    "Car": ["CarBody", "CarTier", "CarSideMirror"],
    "Bicycle": ["BicycleBody", "BicycleHead", "BicycleSeat", "BicycleTier"],
    "Boat": ["BoatBody", "BoatSail"],
    "Aeroplane": [
        "AeroplaneHead",
        "AeroplaneBody",
        "AeroplaneEngine",
        "AeroplaneWing",
        "AeroplaneTail",
    ],
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


def extract_assignment_id_from_filename(filename):
    """Extract assignment ID from filename like group_0_3IXQG4....json"""
    match = GROUP_RE.search(filename)
    if match:
        return match.group(2)  # Return the assignment ID part
    return None


def read_json(s3, bucket, key):
    """Read JSON file from S3"""
    try:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        return json.loads(body)
    except Exception as e:
        print(f"Error reading {key}: {e}")
        return None


def get_assignment_timing_data(mturk, assignment_id):
    """Get timing data for an assignment from MTurk"""
    try:
        response = mturk.get_assignment(AssignmentId=assignment_id)
        assignment = response["Assignment"]

        accept_dt = assignment.get("AcceptTime")
        submit_dt = assignment.get("SubmitTime")

        # Calculate duration in seconds
        duration = (submit_dt - accept_dt).total_seconds()

        # Additional validation
        if duration < 0:
            print(f"Warning: Negative duration for {assignment_id}: {duration} seconds")
            return None

        return {
            "assignment_id": assignment_id,
            "accept_time": accept_dt,
            "submit_time": submit_dt,
            "accept_time_str": accept_dt.strftime('%Y-%m-%d %H:%M:%S%z'),
            "submit_time_str": submit_dt.strftime('%Y-%m-%d %H:%M:%S%z'),
            "duration_seconds": duration,
            "duration_minutes": duration / 60,
            "duration_hours": duration / 3600,
            "worker_id": assignment.get("WorkerId", "Unknown"),
            "hit_id": assignment.get("HITId", "Unknown"),
            "status": assignment.get("AssignmentStatus", "Unknown"),
            "timezone": str(accept_dt.tzinfo) if accept_dt.tzinfo else "No timezone"
        }

    except Exception as e:
        print(f"Error getting timing data for assignment {assignment_id}: {e}")
        return None


def analyze_timing_data(supercategory=None):
    """
    Analyze timing data for HITs from S3 structure:
    HITs/subcategory/spin_val_parts(spin_test_parts)/live/group_x_assignmentId.json
    """

    # S3 configuration
    s3 = boto3.client(
        "s3",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="us-east-1",
    )
    bucket = "spin-instance"

    # MTurk configuration - using production endpoint
    mturk = boto3.client(
        "mturk",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="us-east-1",
        endpoint_url="https://mturk-requester.us-east-1.amazonaws.com",
    )

    # Get subcategories to analyze
    if supercategory:
        subcategories = SUPERCATEGORY_MAPPINGS.get(supercategory, [])
        if not subcategories:
            print(f"❌ Unknown supercategory: {supercategory}")
            return
        analysis_scope = supercategory
    else:
        # Analyze all categories
        subcategories = []
        for cat_subs in SUPERCATEGORY_MAPPINGS.values():
            subcategories.extend(cat_subs)
        analysis_scope = "All_Categories"

    print(f"🏷️  Processing scope: {analysis_scope}")
    print(f"📋 Subcategories: {', '.join(subcategories)}")

    # Create output directory
    output_dir = f"data/analytics/timing/{analysis_scope}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")

    task_types = ["agreeTest", "main"]

    # Storage for timing data
    timing_data = []
    assignment_ids_found = set()
    hit_ids_found = set()
    failed_assignments = []
    timezone_info = set()

    print("🔍 Scanning S3 for assignment IDs...")
    print("=" * 80)

    for subcategory in subcategories:
        for task_type in task_types:
            base_prefix = f"HITs/{subcategory}/{task_type}/live/"

            try:
                # List all files in this path
                all_keys = list_all_keys(s3, bucket, base_prefix)

                if not all_keys:
                    continue

                print(f"\n📁 {subcategory} - {task_type}")
                print(f"   Found {len(all_keys)} files")

                # Process each file to extract assignment IDs
                for key in all_keys:
                    if not key.endswith(".json") or key.endswith("_merged.json"):
                        continue

                    # Extract assignment ID from filename
                    filename = os.path.basename(key)
                    assignment_id = extract_assignment_id_from_filename(filename)

                    if assignment_id and assignment_id not in assignment_ids_found:
                        assignment_ids_found.add(assignment_id)

                        # Read the JSON to get additional context
                        json_data = read_json(s3, bucket, key)
                        if json_data:
                            group_index = json_data.get("group_index", "Unknown")
                            hit_id = json_data.get("HITId", "Unknown")
                            worker_id = json_data.get("worker_id", "Unknown")

                            if hit_id != "Unknown":
                                hit_ids_found.add(hit_id)

                            # Get timing data from MTurk
                            timing_info = get_assignment_timing_data(
                                mturk, assignment_id
                            )

                            if timing_info:
                                timing_info.update(
                                    {
                                        "subcategory": subcategory,
                                        "task_type": task_type,
                                        "group_index": group_index,
                                        "s3_path": key,
                                    }
                                )
                                timing_data.append(timing_info)
                                timezone_info.add(timing_info.get("timezone", "Unknown"))
                                print(
                                    f"     ✅ {assignment_id}: {timing_info['duration_minutes']:.2f} minutes"
                                )
                            else:
                                failed_assignments.append({
                                    "assignment_id": assignment_id,
                                    "subcategory": subcategory,
                                    "task_type": task_type,
                                    "s3_path": key
                                })
                                print(
                                    f"     ❌ {assignment_id}: Failed to get timing data"
                                )

                        # Add small delay to avoid rate limiting
                        import time

                        time.sleep(0.1)

            except Exception as e:
                print(f"❌ Error processing {subcategory}/{task_type}: {e}")
                continue

    print(f"\n📊 TIMING DATA COLLECTION SUMMARY")
    print("=" * 80)
    print(f"Total assignment IDs found: {len(assignment_ids_found)}")
    print(f"Total HIT IDs found: {len(hit_ids_found)}")
    print(f"Successful timing data retrievals: {len(timing_data)}")
    print(f"Failed timing data retrievals: {len(failed_assignments)}")
    print(f"Timezones detected: {', '.join(timezone_info)}")

    if not timing_data:
        print("❌ No timing data collected. Exiting.")
        return

    # Convert to DataFrame for analysis
    df = pd.DataFrame(timing_data)

    # Filter out any negative or extremely long durations (potential data errors)
    initial_count = len(df)
    df = df[(df['duration_minutes'] >= 0) & (df['duration_minutes'] <= 300)]  # Max 5 hours
    filtered_count = len(df)

    if initial_count != filtered_count:
        print(f"⚠️  Filtered out {initial_count - filtered_count} assignments with invalid durations")

    # Save raw timing data
    timing_csv_file = os.path.join(output_dir, f"{analysis_scope}_timing_data.csv")
    df.to_csv(timing_csv_file, index=False)
    print(f"📄 Timing data saved to '{timing_csv_file}'")

    # Save failed assignments for debugging
    if failed_assignments:
        failed_csv_file = os.path.join(output_dir, f"{analysis_scope}_failed_assignments.csv")
        pd.DataFrame(failed_assignments).to_csv(failed_csv_file, index=False)
        print(f"📄 Failed assignments saved to '{failed_csv_file}'")

    # Generate statistics
    print(f"\n📈 TIMING STATISTICS")
    print("=" * 80)
    print(f"Total assignments analyzed: {len(df)}")
    print(f"Duration statistics (minutes):")
    print(f"  Mean: {df['duration_minutes'].mean():.2f}")
    print(f"  Median: {df['duration_minutes'].median():.2f}")
    print(f"  Std Dev: {df['duration_minutes'].std():.2f}")
    print(f"  Min: {df['duration_minutes'].min():.2f}")
    print(f"  Max: {df['duration_minutes'].max():.2f}")
    print(f"  25th percentile: {df['duration_minutes'].quantile(0.25):.2f}")
    print(f"  75th percentile: {df['duration_minutes'].quantile(0.75):.2f}")

    # Category-wise statistics
    print(f"\n📋 CATEGORY-WISE TIMING STATISTICS")
    print("=" * 80)
    category_stats = (
        df.groupby("subcategory")["duration_minutes"]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .round(2)
    )
    print(category_stats)

    # Task type statistics
    print(f"\n📋 TASK TYPE TIMING STATISTICS")
    print("=" * 80)
    task_stats = (
        df.groupby("task_type")["duration_minutes"]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .round(2)
    )
    print(task_stats)

    # Create visualizations
    create_timing_visualizations(df, output_dir, analysis_scope)

    # Save detailed analysis report
    analysis_report = {
        "analysis_scope": analysis_scope,
        "subcategories": subcategories if supercategory else "All",
        "analysis_timestamp": datetime.now().isoformat(),
        "total_assignments": len(df),
        "total_hit_ids": len(hit_ids_found),
        "duration_statistics": {
            "mean_minutes": float(df["duration_minutes"].mean()),
            "median_minutes": float(df["duration_minutes"].median()),
            "std_minutes": float(df["duration_minutes"].std()),
            "min_minutes": float(df["duration_minutes"].min()),
            "max_minutes": float(df["duration_minutes"].max()),
            "q25_minutes": float(df["duration_minutes"].quantile(0.25)),
            "q75_minutes": float(df["duration_minutes"].quantile(0.75)),
        },
        "category_statistics": category_stats.to_dict("index"),
        "task_type_statistics": task_stats.to_dict("index"),
    }

    report_file = os.path.join(
        output_dir, f"{analysis_scope}_timing_analysis_report.json"
    )
    with open(report_file, "w") as f:
        json.dump(analysis_report, f, indent=2)
    print(f"\n📄 Detailed analysis report saved to '{report_file}'")


def create_timing_visualizations(df, output_dir, analysis_scope):
    """Create histogram and box plots for timing data"""

    # Set up the plotting style
    plt.style.use("default")
    sns.set_palette("husl")

    # Filter out outliers for better visualization (optional)
    q1 = df["duration_minutes"].quantile(0.25)
    q3 = df["duration_minutes"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    # Create filtered dataset for cleaner visualizations
    df_filtered = df[(df["duration_minutes"] >= lower_bound) & (df["duration_minutes"] <= upper_bound)]
    outliers_count = len(df) - len(df_filtered)

    if outliers_count > 0:
        print(f"📊 Note: {outliers_count} outliers detected (beyond 1.5*IQR), using filtered data for cleaner visualizations")

    # 1. Overall Duration Histogram with better binning
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor("#f8f9fa")

    # Histogram with adaptive binning
    bins = min(30, max(10, len(df_filtered) // 20))
    ax1.hist(
        df_filtered["duration_minutes"],
        bins=bins,
        color="#3b82f6",
        alpha=0.7,
        edgecolor="white",
        linewidth=1,
    )
    ax1.set_title(
        f"{analysis_scope} - Assignment Duration Distribution",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax1.set_xlabel("Duration (minutes)", fontsize=12, fontweight="600")
    ax1.set_ylabel("Frequency", fontsize=12, fontweight="600")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_facecolor("#ffffff")

    # Add statistics text with outlier info
    stats_text = f'Mean: {df["duration_minutes"].mean():.1f} min\nMedian: {df["duration_minutes"].median():.1f} min\nStd: {df["duration_minutes"].std():.1f} min'
    if outliers_count > 0:
        stats_text += f'\nOutliers: {outliers_count}'
    ax1.text(
        0.7,
        0.9,
        stats_text,
        transform=ax1.transAxes,
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
    )

    # Box plot (using full dataset to show outliers)
    box_plot = ax2.boxplot(
        df["duration_minutes"],
        patch_artist=True,
        boxprops=dict(facecolor="#10b981", alpha=0.7),
        medianprops=dict(color="#065f46", linewidth=2),
        whiskerprops=dict(color="#065f46", linewidth=1.5),
        capprops=dict(color="#065f46", linewidth=1.5),
        flierprops=dict(marker='o', markerfacecolor='red', markersize=5, alpha=0.5)
    )

    # Add quartile annotations on the box plot
    q1 = df["duration_minutes"].quantile(0.25)
    median = df["duration_minutes"].median()
    q3 = df["duration_minutes"].quantile(0.75)

    # Annotate quartiles on the box plot
    ax2.text(1.15, q1, f'Q1: {q1:.1f}', va='center', ha='left', fontsize=10,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    ax2.text(1.15, median, f'Median: {median:.1f}', va='center', ha='left', fontsize=10,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
    ax2.text(1.15, q3, f'Q3: {q3:.1f}', va='center', ha='left', fontsize=10,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.7))

    ax2.set_title(
        f"{analysis_scope} - Assignment Duration Box Plot",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax2.set_ylabel("Duration (minutes)", fontsize=12, fontweight="600")
    ax2.grid(axis="y", alpha=0.3)
    ax2.set_facecolor("#ffffff")
    ax2.set_xticklabels(["All Assignments"])

    plt.tight_layout()
    hist_file = os.path.join(output_dir, f"{analysis_scope}_duration_overview.png")
    fig.savefig(hist_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
    print(f"💾 Duration overview saved as '{hist_file}'")
    plt.close()

    # 2. Time-based Analysis (Hour of Day) - NEW ADDITION
    if len(df) > 10:  # Only if we have enough data
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.patch.set_facecolor("#f8f9fa")

        # Extract hour from accept_time and submit_time
        df['accept_hour'] = df['accept_time'].dt.hour
        df['submit_hour'] = df['submit_time'].dt.hour

        # Hour of day analysis
        accept_hours = df['accept_hour'].value_counts().sort_index()
        submit_hours = df['submit_hour'].value_counts().sort_index()

        hours = range(24)
        accept_counts = [accept_hours.get(h, 0) for h in hours]
        submit_counts = [submit_hours.get(h, 0) for h in hours]

        ax1.bar(hours, accept_counts, alpha=0.7, label='Accept Time', color='#3b82f6')
        ax1.set_title('Assignment Accept Times by Hour', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Hour of Day', fontsize=12, fontweight='600')
        ax1.set_ylabel('Number of Assignments', fontsize=12, fontweight='600')
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_facecolor('#ffffff')
        ax1.set_xticks(range(0, 24, 2))

        ax2.bar(hours, submit_counts, alpha=0.7, label='Submit Time', color='#10b981')
        ax2.set_title('Assignment Submit Times by Hour', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Hour of Day', fontsize=12, fontweight='600')
        ax2.set_ylabel('Number of Assignments', fontsize=12, fontweight='600')
        ax2.grid(axis='y', alpha=0.3)
        ax2.set_facecolor('#ffffff')
        ax2.set_xticks(range(0, 24, 2))

        plt.tight_layout()
        time_file = os.path.join(output_dir, f"{analysis_scope}_hourly_distribution.png")
        fig.savefig(time_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
        print(f"💾 Hourly distribution saved as '{time_file}'")
        plt.close()

    # 2. Category-wise Box Plot
    if "subcategory" in df.columns and df["subcategory"].nunique() > 1:
        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor("#f8f9fa")

        # Create box plot by category
        categories = sorted(df["subcategory"].unique())
        box_data = [
            df[df["subcategory"] == cat]["duration_minutes"].values
            for cat in categories
        ]

        box_plot = ax.boxplot(box_data, labels=categories, patch_artist=True)

        # Color each box differently
        colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
        for patch, color in zip(box_plot["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # Add quartile annotations for each category
        for i, cat in enumerate(categories):
            cat_data = df[df["subcategory"] == cat]["duration_minutes"]
            q1 = cat_data.quantile(0.25)
            median = cat_data.median()
            q3 = cat_data.quantile(0.75)

            x_pos = i + 1
            # Position text to the right of each box
            ax.text(x_pos + 0.35, q1, f'{q1:.1f}', ha='left', va='center', fontsize=8,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="lightblue", alpha=0.6))
            ax.text(x_pos + 0.35, median, f'{median:.1f}', ha='left', va='center', fontsize=8,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.6))
            ax.text(x_pos + 0.35, q3, f'{q3:.1f}', ha='left', va='center', fontsize=8,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="lightcoral", alpha=0.6))

        ax.set_title(
            f"{analysis_scope} - Duration by Category",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        ax.set_xlabel("Category", fontsize=12, fontweight="600")
        ax.set_ylabel("Duration (minutes)", fontsize=12, fontweight="600")
        ax.grid(axis="y", alpha=0.3)
        ax.set_facecolor("#ffffff")

        # Rotate x-axis labels if needed
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        plt.tight_layout()
        category_file = os.path.join(
            output_dir, f"{analysis_scope}_duration_by_category.png"
        )
        fig.savefig(category_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
        print(f"💾 Category duration plot saved as '{category_file}'")
        plt.close()

    # 3. Task Type Comparison
    if "task_type" in df.columns and df["task_type"].nunique() > 1:
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#f8f9fa")

        task_types = sorted(df["task_type"].unique())
        task_data = [
            df[df["task_type"] == task]["duration_minutes"].values
            for task in task_types
        ]

        box_plot = ax.boxplot(task_data, labels=task_types, patch_artist=True)

        # Color the boxes
        colors = ["#3b82f6", "#ef4444"]  # Blue and red
        for patch, color in zip(box_plot["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # Add quartile annotations for each task type
        for i, task in enumerate(task_types):
            task_data = df[df["task_type"] == task]["duration_minutes"]
            q1 = task_data.quantile(0.25)
            median = task_data.median()
            q3 = task_data.quantile(0.75)

            x_pos = i + 1
            # Position text to the right of each box
            ax.text(x_pos + 0.25, q1, f'{q1:.1f}', ha='left', va='center', fontsize=9,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="lightblue", alpha=0.6))
            ax.text(x_pos + 0.25, median, f'{median:.1f}', ha='left', va='center', fontsize=9,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.6))
            ax.text(x_pos + 0.25, q3, f'{q3:.1f}', ha='left', va='center', fontsize=9,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="lightcoral", alpha=0.6))

        ax.set_title(
            f"{analysis_scope} - Duration by Task Type",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        ax.set_xlabel("Task Type", fontsize=12, fontweight="600")
        ax.set_ylabel("Duration (minutes)", fontsize=12, fontweight="600")
        ax.grid(axis="y", alpha=0.3)
        ax.set_facecolor("#ffffff")

        plt.tight_layout()
        task_file = os.path.join(
            output_dir, f"{analysis_scope}_duration_by_task_type.png"
        )
        fig.savefig(task_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
        print(f"💾 Task type duration plot saved as '{task_file}'")
        plt.close()

    # 4. Detailed Histogram with Multiple Bins
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#f8f9fa")

    # Create histogram with better binning
    n_bins = min(50, len(df) // 10)  # Adaptive binning
    n, bins, patches = ax.hist(
        df["duration_minutes"],
        bins=n_bins,
        color="#3b82f6",
        alpha=0.7,
        edgecolor="white",
        linewidth=0.5,
    )

    # Color gradient for bars
    cm = plt.cm.viridis
    for i, (patch, bin_center) in enumerate(zip(patches, bins[:-1])):
        patch.set_facecolor(cm(i / len(patches)))

    ax.set_title(
        f"{analysis_scope} - Detailed Duration Distribution",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("Duration (minutes)", fontsize=12, fontweight="600")
    ax.set_ylabel("Frequency", fontsize=12, fontweight="600")
    ax.grid(axis="y", alpha=0.3)
    ax.set_facecolor("#ffffff")

    # Add vertical lines for key statistics
    mean_val = df["duration_minutes"].mean()
    median_val = df["duration_minutes"].median()
    ax.axvline(
        mean_val,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {mean_val:.1f} min",
    )
    ax.axvline(
        median_val,
        color="orange",
        linestyle="-",
        linewidth=2,
        label=f"Median: {median_val:.1f} min",
    )

    ax.legend(fontsize=10)

    plt.tight_layout()
    detailed_hist_file = os.path.join(
        output_dir, f"{analysis_scope}_detailed_duration_histogram.png"
    )
    fig.savefig(detailed_hist_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
    print(f"💾 Detailed histogram saved as '{detailed_hist_file}'")
    plt.close()


def main():
    """Main function to run the timing analysis with command line arguments"""
    parser = argparse.ArgumentParser(
        description="Analyze MTurk assignment timing data from S3 HITs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available supercategories:
{chr(10).join([f"  - {cat}: {', '.join(subs)}" for cat, subs in SUPERCATEGORY_MAPPINGS.items()])}

Examples:
  python timing_analysis.py --supercategory Quadruped
  python timing_analysis.py --all-categories
  python timing_analysis.py --list-categories
        """,
    )

    parser.add_argument(
        "--supercategory",
        "-s",
        type=str,
        choices=list(SUPERCATEGORY_MAPPINGS.keys()),
        help="Supercategory to analyze (e.g., Quadruped, Bird, Car, etc.)",
    )

    parser.add_argument(
        "--all-categories",
        "-a",
        action="store_true",
        help="Analyze timing data for all categories",
    )

    parser.add_argument(
        "--list-categories",
        "-l",
        action="store_true",
        help="List all available supercategories and their subcategories",
    )

    args = parser.parse_args()

    # Handle list categories option
    if args.list_categories:
        print("🏷️  Available Supercategories and Subcategories:")
        print("=" * 60)
        for supercategory, subcategories in SUPERCATEGORY_MAPPINGS.items():
            print(f"\n📂 {supercategory}:")
            for subcategory in subcategories:
                print(f"   • {subcategory}")
        print("\n" + "=" * 60)
        return

    # Determine analysis scope
    if args.all_categories:
        print("🚀 Starting timing analysis for ALL categories...")
        analyze_timing_data(None)
    elif args.supercategory:
        print(f"🚀 Starting timing analysis for {args.supercategory}...")
        analyze_timing_data(args.supercategory)
    else:
        print("❌ Error: Please specify either --supercategory or --all-categories")
        print("Use --list-categories to see available options")
        parser.print_help()
        return

    print("\n✅ Timing analysis complete!")


if __name__ == "__main__":
    main()
