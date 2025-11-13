#!/usr/bin/env python3
"""
Generate instance count visualization by part category for CVPR figures.
Shows total number of instances (annotations) for each part category.
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from collections import defaultdict
from matplotlib.patches import Patch

# Set the style
matplotlib.style.use('seaborn-v0_8-white')

# Configure fonts
plt.rcParams['font.family'] = ['Inter', 'Open Sans', 'Arial', 'sans-serif']
plt.rcParams['font.size'] = 14  # Increased from 11 to 14 (about 27% increase)

def load_annotation_data(filepath):
    """Load annotation data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_contrast_text_color(hex_color):
    """Determine if white or black text has better contrast on the given background color."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return 'white' if luminance < 0.5 else '#1a1a1a'

def count_total_instances(datasets):
    """
    Count total instances (annotations) for each category across all datasets.
    
    Returns:
        supercategory_data: dict mapping supercategory -> category -> total_count
        category_lookup: dict mapping category_id -> category_info
    """
    # Build category lookup from first dataset
    category_lookup = {}
    for cat in datasets[0]['categories']:
        category_lookup[cat['id']] = {
            'name': cat['name'],
            'supercategory': cat['supercategory']
        }
    
    # Count total annotations per category
    category_counts = defaultdict(int)
    
    for dataset in datasets:
        for ann in dataset['annotations']:
            category_id = ann['category_id']
            category_counts[category_id] += 1
    
    # Organize by supercategory
    supercategory_data = defaultdict(dict)
    for category_id, count in category_counts.items():
        cat_info = category_lookup[category_id]
        supercategory = cat_info['supercategory']
        category_name = cat_info['name']
        supercategory_data[supercategory][category_name] = count
    
    return supercategory_data, category_lookup

def create_instance_count_chart(supercategory_data, output_path='cvpr_figures/instance_count_chart.png'):
    """
    Create a bar chart showing total instance count by part category,
    grouped by supercategory.
    """
    # Prepare data for plotting
    supercategories = sorted(supercategory_data.keys())
    
    # Use a single color with slight variations per supercategory
    base_color = '#4A90E2'  # Professional blue
    
    # Calculate figure size based on number of categories
    total_categories = sum(len(cats) for cats in supercategory_data.values())
    fig_width = max(18, total_categories * 0.55)
    fig_height = max(9, total_categories * 0.2)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor('white')
    
    # Prepare data
    all_categories = []
    all_supercategories = []
    all_counts = []
    
    for supercategory in supercategories:
        categories = sorted(supercategory_data[supercategory].keys())
        for category in categories:
            all_categories.append(category)
            all_supercategories.append(supercategory)
            all_counts.append(supercategory_data[supercategory][category])
    
    # Add alternating background bands per supercategory
    group_starts = []
    group_ends = []
    if len(all_supercategories) > 0:
        current = all_supercategories[0]
        start_idx = 0
        for i, sc in enumerate(all_supercategories):
            if sc != current:
                group_starts.append(start_idx)
                group_ends.append(i)
                start_idx = i
                current = sc
        group_starts.append(start_idx)
        group_ends.append(len(all_supercategories))

        for gi, (gs, ge) in enumerate(zip(group_starts, group_ends)):
            left = gs - 0.5
            right = ge - 0.5
            ax.axvspan(left, right, facecolor='#f6f7fb' if gi % 2 == 0 else '#ffffff',
                       alpha=0.8, zorder=0)

    # Create bar chart
    x = np.arange(len(all_categories))
    width = 0.98  # Increased from 0.92 for larger bars
    
    bars = ax.bar(x, all_counts, width, 
                  color=base_color, edgecolor='none', linewidth=0, alpha=0.85)

    # Add value labels on top of bars
    max_count = max(all_counts) if all_counts else 0
    label_offset = max_count * 0.02 if max_count else 1.0
    if max_count:
        ax.set_ylim(0, max_count * 1.15)

    text_color = get_contrast_text_color(base_color)
    
    for idx, (bar, count) in enumerate(zip(bars, all_counts)):
        height = bar.get_height()
        # Place label on top of bar
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + label_offset,
                f"{count:,}", ha='center', va='bottom', fontsize=11,
                color='#1a1a1a', fontweight='semibold')
    
    # Add thin vertical lines to separate supercategories
    current_supercategory = all_supercategories[0]
    supercategory_positions = [0]
    supercategory_labels = [current_supercategory]
    
    for i, supercategory in enumerate(all_supercategories[1:], start=1):
        if supercategory != current_supercategory:
            ax.axvline(x=i - 0.5, color='#d0d4e4', linestyle='-', linewidth=1.0, alpha=0.8)
            supercategory_positions.append(i)
            supercategory_labels.append(supercategory)
            current_supercategory = supercategory
    
    # Labels and formatting
    ax.set_xlabel('Part Category', fontweight='bold', fontsize=18, color='#333333')
    ax.set_ylabel('Number of Instances', fontweight='bold', fontsize=22, color='#333333')
    ax.set_title('Instance Count per Part Category', 
                 fontweight='bold', pad=20, fontsize=26, color='#1a1a1a')
    
    # X-axis: show category names rotated
    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, rotation=45, ha='right', color='#555555', fontsize=14)
    
    # Add supercategory labels on a secondary x-axis
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    
    # Calculate midpoints for supercategory labels
    supercategory_midpoints = []
    for i in range(len(supercategory_positions)):
        start = supercategory_positions[i]
        end = supercategory_positions[i + 1] if i + 1 < len(supercategory_positions) else len(all_categories)
        midpoint = (start + end - 1) / 2
        supercategory_midpoints.append(midpoint)
    
    ax2.set_xticks(supercategory_midpoints)
    ax2.set_xticklabels(supercategory_labels, fontweight='bold', fontsize=18, color='#1f2a44')
    ax2.tick_params(axis='x', which='major', pad=10)
    ax2.spines['top'].set_visible(False)
    
    # No grid for cleaner appearance
    ax.grid(False)
    ax.set_axisbelow(True)
    
    # Style the tick colors
    ax.tick_params(colors='#555555')
    
    # Tight layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save figure with high resolution for printing
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=450, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"Figure saved to {output_path}")
    
    plt.close(fig)
    
    return fig, ax

def print_statistics(supercategory_data):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("INSTANCE COUNT STATISTICS BY SUPERCATEGORY")
    print("="*80)
    
    total_instances = 0
    
    for supercategory in sorted(supercategory_data.keys()):
        print(f"\n{supercategory}:")
        print("-" * 60)
        print(f"{'Part Category':<30} {'Instance Count':<15}")
        print("-" * 60)
        
        supercategory_total = 0
        
        for category in sorted(supercategory_data[supercategory].keys()):
            count = supercategory_data[supercategory][category]
            print(f"{category:<30} {count:<15,}")
            supercategory_total += count
        
        print("-" * 60)
        print(f"{'Subtotal':<30} {supercategory_total:<15,}")
        total_instances += supercategory_total
    
    print("\n" + "="*80)
    print(f"{'GRAND TOTAL':<30} {total_instances:<15,}")
    print("="*80)

def main():
    # Paths to all annotation files
    annotation_files = [
        'data/annotations/spin2_train_parts.json',
        'data/annotations/spin2_val_parts.json',
        'data/annotations/spin2_test_parts.json'
    ]
    
    # Load all datasets
    datasets = []
    for annotation_file in annotation_files:
        if not os.path.exists(annotation_file):
            print(f"Warning: File not found: {annotation_file}")
            continue
        datasets.append(load_annotation_data(annotation_file))
    
    if not datasets:
        print("Error: No annotation files found!")
        return
    
    print(f"\nLoaded {len(datasets)} dataset(s)")
    
    # Count total instances per category
    supercategory_data, category_lookup = count_total_instances(datasets)
    
    # Print statistics
    print_statistics(supercategory_data)
    
    # Create visualization
    create_instance_count_chart(supercategory_data)

if __name__ == "__main__":
    main()
