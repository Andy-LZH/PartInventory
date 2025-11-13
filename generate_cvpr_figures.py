import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.patches import Patch
import seaborn as sns
import os

# Set style for modern publication-quality figures
plt.style.use('seaborn-v0_8-white')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter', 'Open Sans', 'Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 15  # Increased from 12
plt.rcParams['axes.labelsize'] = 19  # Increased from 15
plt.rcParams['axes.titlesize'] = 23  # Increased from 18
plt.rcParams['xtick.labelsize'] = 14  # Increased from 11
plt.rcParams['ytick.labelsize'] = 14  # Increased from 11
plt.rcParams['legend.fontsize'] = 14  # Increased from 11
plt.rcParams['figure.titlesize'] = 21  # Increased from 17
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

def get_contrast_text_color(hex_color):
    """Return a contrasting text color (black/white) for the given hex color."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return '#1a1a1a'
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return '#1a1a1a' if luminance > 0.6 else '#ffffff'

def load_annotation_data(json_path):
    """Load annotation data from JSON file."""
    print(f"Loading data from {json_path}...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def count_instances_per_category(datasets):
    """
    Count annotations grouped by part category and supercategory,
    split by instance count (1-10, 10+).
    Processes multiple datasets (train, val, test).
    """
    # Create category lookup from first dataset
    category_lookup = {}
    for cat in datasets[0]['categories']:
        category_lookup[cat['id']] = {
            'name': cat['name'],
            'supercategory': cat['supercategory']
        }
    
    # Count instances per image and category across all datasets
    # Structure: {image_id: {category_id: set(instance_ids)}}
    image_category_instances = defaultdict(lambda: defaultdict(set))
    
    for data in datasets:
        for ann in data['annotations']:
            image_id = ann['image_id']
            category_id = ann['category_id']
            # Use instance_id if available, otherwise use instance_type
            instance_id = ann.get('instance_id', ann.get('instance_type', 0))
            image_category_instances[image_id][category_id].add(instance_id)
    
    # Count annotations by category and instance count (1-10, 10+)
    instance_keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10+']
    category_instance_counts = defaultdict(lambda: {k: 0 for k in instance_keys})
    
    for image_id, categories in image_category_instances.items():
        for category_id, instance_set in categories.items():
            num_instances = len(instance_set)  # Count unique instances
            
            if num_instances <= 9:
                category_instance_counts[category_id][str(num_instances)] += 1
            else:  # 10 or more
                category_instance_counts[category_id]['10+'] += 1
    
    # Group by supercategory
    supercategory_data = defaultdict(lambda: defaultdict(lambda: {k: 0 for k in instance_keys}))
    
    for category_id, counts in category_instance_counts.items():
        cat_info = category_lookup[category_id]
        supercategory = cat_info['supercategory']
        category_name = cat_info['name']
        supercategory_data[supercategory][category_name] = counts
    
    return supercategory_data, category_lookup

def create_histogram(supercategory_data, output_path='cvpr_figures/instance_histogram.png'):
    """
    Create a grouped histogram showing annotations by part category,
    grouped by supercategory, with splits for 1-9 and 10+ instances.
    """
    # Prepare data for plotting
    supercategories = sorted(supercategory_data.keys())
    
    # Use a 10-color palette - combining tab10 for better distinction
    palette = sns.color_palette("tab10", 10)
    colors = {
        '1': '#1f77b4',    # Blue
        '2': '#ff7f0e',    # Orange
        '3': '#2ca02c',    # Green
        '4': '#d62728',    # Red
        '5': '#9467bd',    # Purple
        '6': '#8c564b',    # Brown
        '7': '#e377c2',    # Pink
        '8': '#7f7f7f',    # Gray
        '9': '#bcbd22',    # Olive
        '10+': '#17becf'   # Cyan
    }
    
    # Calculate figure size based on number of categories
    total_categories = sum(len(cats) for cats in supercategory_data.values())
    fig_width = max(18, total_categories * 0.55)
    fig_height = max(9, total_categories * 0.2)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor('white')
    
    # Prepare data
    all_categories = []
    all_supercategories = []
    counts_1 = []
    counts_2 = []
    counts_3 = []
    counts_4 = []
    counts_5 = []
    counts_6 = []
    counts_7 = []
    counts_8 = []
    counts_9 = []
    counts_10plus = []
    
    for supercategory in supercategories:
        categories = sorted(supercategory_data[supercategory].keys())
        for category in categories:
            all_categories.append(category)
            all_supercategories.append(supercategory)
            counts = supercategory_data[supercategory][category]
            counts_1.append(counts['1'])
            counts_2.append(counts['2'])
            counts_3.append(counts['3'])
            counts_4.append(counts['4'])
            counts_5.append(counts['5'])
            counts_6.append(counts['6'])
            counts_7.append(counts['7'])
            counts_8.append(counts['8'])
            counts_9.append(counts['9'])
            counts_10plus.append(counts['10+'])

    total_counts = {
        '1': int(np.sum(counts_1)),
        '2': int(np.sum(counts_2)),
        '3': int(np.sum(counts_3)),
        '4': int(np.sum(counts_4)),
        '5': int(np.sum(counts_5)),
        '6': int(np.sum(counts_6)),
        '7': int(np.sum(counts_7)),
        '8': int(np.sum(counts_8)),
        '9': int(np.sum(counts_9)),
        '10+': int(np.sum(counts_10plus))
    }
    total_annotations = sum(total_counts.values())
    summary_lines = [
        'Image Annotations',
        f"- 1 instance: {total_counts['1']:,} images",
        f"- 2 instances: {total_counts['2']:,} images",
        f"- 3 instances: {total_counts['3']:,} images",
        f"- 4 instances: {total_counts['4']:,} images",
        f"- 5 instances: {total_counts['5']:,} images",
        f"- 6 instances: {total_counts['6']:,} images",
        f"- 7 instances: {total_counts['7']:,} images",
        f"- 8 instances: {total_counts['8']:,} images",
        f"- 9 instances: {total_counts['9']:,} images",
        f"- 10+ instances: {total_counts['10+']:,} images",
        f"Total: {total_annotations:,} image-part pairs"
    ]
    
    # Apply minimum threshold for display so small values are visible but proportional
    # Use a logarithmic-like scaling: small values get boosted to min_display_height
    def apply_display_threshold(value, min_display_height=15, transition_point=30):
        """
        Apply a minimum display height while preserving relative differences.
        Values below transition_point are scaled to be at least min_display_height.
        """
        if value == 0:
            return 0
        elif value < transition_point:
            # Logarithmic scaling for small values: ensures visibility and proportionality
            # Maps [1, transition_point] to [min_display_height, transition_point]
            scale_factor = (transition_point - min_display_height) / np.log(transition_point)
            return min_display_height + scale_factor * np.log(value)
        else:
            return value
    
    # Store original counts for labels
    original_counts_1 = counts_1.copy()
    original_counts_2 = counts_2.copy()
    original_counts_3 = counts_3.copy()
    original_counts_4 = counts_4.copy()
    original_counts_5 = counts_5.copy()
    original_counts_6 = counts_6.copy()
    original_counts_7 = counts_7.copy()
    original_counts_8 = counts_8.copy()
    original_counts_9 = counts_9.copy()
    original_counts_10plus = counts_10plus.copy()
    
    # Apply threshold to display values
    counts_1_display = [apply_display_threshold(c) for c in counts_1]
    counts_2_display = [apply_display_threshold(c) for c in counts_2]
    counts_3_display = [apply_display_threshold(c) for c in counts_3]
    counts_4_display = [apply_display_threshold(c) for c in counts_4]
    counts_5_display = [apply_display_threshold(c) for c in counts_5]
    counts_6_display = [apply_display_threshold(c) for c in counts_6]
    counts_7_display = [apply_display_threshold(c) for c in counts_7]
    counts_8_display = [apply_display_threshold(c) for c in counts_8]
    counts_9_display = [apply_display_threshold(c) for c in counts_9]
    counts_10plus_display = [apply_display_threshold(c) for c in counts_10plus]
    
    # Add alternating background bands per supercategory to increase salience
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

    # Create stacked bar chart with modern styling
    x = np.arange(len(all_categories))
    width = 0.98  # Increased from 0.92 for larger bars
    
    bars1 = ax.bar(x, counts_1_display, width, label='1 Instance', 
                   color=colors['1'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_2 = np.array(counts_1_display)
    bars2 = ax.bar(x, counts_2_display, width, bottom=bottom_2, label='2 Instances', 
                   color=colors['2'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_3 = bottom_2 + np.array(counts_2_display)
    bars3 = ax.bar(x, counts_3_display, width, bottom=bottom_3, label='3 Instances', 
                   color=colors['3'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_4 = bottom_3 + np.array(counts_3_display)
    bars4 = ax.bar(x, counts_4_display, width, bottom=bottom_4, label='4 Instances', 
                   color=colors['4'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_5 = bottom_4 + np.array(counts_4_display)
    bars5 = ax.bar(x, counts_5_display, width, bottom=bottom_5, label='5 Instances', 
                   color=colors['5'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_6 = bottom_5 + np.array(counts_5_display)
    bars6 = ax.bar(x, counts_6_display, width, bottom=bottom_6, label='6 Instances', 
                   color=colors['6'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_7 = bottom_6 + np.array(counts_6_display)
    bars7 = ax.bar(x, counts_7_display, width, bottom=bottom_7, label='7 Instances', 
                   color=colors['7'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_8 = bottom_7 + np.array(counts_7_display)
    bars8 = ax.bar(x, counts_8_display, width, bottom=bottom_8, label='8 Instances', 
                   color=colors['8'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_9 = bottom_8 + np.array(counts_8_display)
    bars9 = ax.bar(x, counts_9_display, width, bottom=bottom_9, label='9 Instances', 
                   color=colors['9'], edgecolor='none', linewidth=0, alpha=0.85)
    
    bottom_10 = bottom_9 + np.array(counts_9_display)
    bars10 = ax.bar(x, counts_10plus_display, width, bottom=bottom_10, label='10+ Instances', 
                   color=colors['10+'], edgecolor='none', linewidth=0, alpha=0.85)

    # Add value labels inside each stacked segment and totals on top
    # Use ORIGINAL counts for labels, but DISPLAY positions for placement
    category_totals_display = bottom_10 + np.array(counts_10plus_display)
    category_totals_original = [original_counts_1[i] + original_counts_2[i] + original_counts_3[i] + 
                                original_counts_4[i] + original_counts_5[i] + original_counts_6[i] +
                                original_counts_7[i] + original_counts_8[i] + original_counts_9[i] +
                                original_counts_10plus[i]
                                for i in range(len(original_counts_1))]
    max_total = category_totals_display.max() if len(category_totals_display) > 0 else 0
    label_offset = max_total * 0.02 if max_total else 1.0
    if max_total:
        ax.set_ylim(0, max_total * 1.22)

    color_for_1 = get_contrast_text_color(colors['1'])
    color_for_2 = get_contrast_text_color(colors['2'])
    color_for_3 = get_contrast_text_color(colors['3'])
    color_for_4 = get_contrast_text_color(colors['4'])
    color_for_5 = get_contrast_text_color(colors['5'])
    color_for_6 = get_contrast_text_color(colors['6'])
    color_for_7 = get_contrast_text_color(colors['7'])
    color_for_8 = get_contrast_text_color(colors['8'])
    color_for_9 = get_contrast_text_color(colors['9'])
    color_for_10 = get_contrast_text_color(colors['10+'])

    for idx, rect in enumerate(bars1):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_1[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_1, fontweight='semibold')

    for idx, rect in enumerate(bars2):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_2[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_2, fontweight='semibold')

    for idx, rect in enumerate(bars3):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_3[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_3, fontweight='semibold')

    for idx, rect in enumerate(bars4):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_4[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_4, fontweight='semibold')

    for idx, rect in enumerate(bars5):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_5[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_5, fontweight='semibold')

    for idx, rect in enumerate(bars6):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_6[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_6, fontweight='semibold')

    for idx, rect in enumerate(bars7):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_7[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_7, fontweight='semibold')

    for idx, rect in enumerate(bars8):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_8[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_8, fontweight='semibold')

    for idx, rect in enumerate(bars9):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_9[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_9, fontweight='semibold')

    for idx, rect in enumerate(bars10):
        height = rect.get_height()
        if height <= 0:
            continue
        y_pos = rect.get_y() + height / 2.0
        ax.text(rect.get_x() + rect.get_width() / 2.0, y_pos,
                f"{original_counts_10plus[idx]:,}", ha='center', va='center', fontsize=10,
                color=color_for_10, fontweight='semibold')

    for idx, total_display in enumerate(category_totals_display):
        ax.text(x[idx], total_display + label_offset,
                f"{int(category_totals_original[idx]):,}", ha='center', va='bottom', fontsize=11,
                color='#1a1a1a', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#d0d0d0', alpha=0.95))
    
    # Add thin vertical lines to separate supercategories (on top of bands)
    current_supercategory = all_supercategories[0]
    supercategory_positions = [0]
    supercategory_labels = [current_supercategory]
    
    for i, supercategory in enumerate(all_supercategories[1:], start=1):
        if supercategory != current_supercategory:
            ax.axvline(x=i - 0.5, color='#d0d4e4', linestyle='-', linewidth=1.0, alpha=0.8)
            supercategory_positions.append(i)
            supercategory_labels.append(supercategory)
            current_supercategory = supercategory
    
    # Labels and formatting with modern style
    ax.set_xlabel('Part Category', fontweight='bold', fontsize=18, color='#333333')
    ax.set_ylabel('Number of Semantic Masks', fontweight='bold', fontsize=22, color='#333333')
    ax.set_title('Distribution of Part Instances per Semantic Mask', 
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
    
    # Legend anchored to upper left (where annotation details were)
    legend_handles = [
        Patch(facecolor=colors['1'], edgecolor='none', linewidth=0, label='1 instance'),
        Patch(facecolor=colors['2'], edgecolor='none', linewidth=0, label='2 instances'),
        Patch(facecolor=colors['3'], edgecolor='none', linewidth=0, label='3 instances'),
        Patch(facecolor=colors['4'], edgecolor='none', linewidth=0, label='4 instances'),
        Patch(facecolor=colors['5'], edgecolor='none', linewidth=0, label='5 instances'),
        Patch(facecolor=colors['6'], edgecolor='none', linewidth=0, label='6 instances'),
        Patch(facecolor=colors['7'], edgecolor='none', linewidth=0, label='7 instances'),
        Patch(facecolor=colors['8'], edgecolor='none', linewidth=0, label='8 instances'),
        Patch(facecolor=colors['9'], edgecolor='none', linewidth=0, label='9 instances'),
        Patch(facecolor=colors['10+'], edgecolor='none', linewidth=0, label='10+ instances')
    ]
    legend = ax.legend(handles=legend_handles, loc='upper left', bbox_to_anchor=(0.012, 0.98),
                       frameon=True, framealpha=0.96, edgecolor='#d5d5d5', fancybox=True,
                       ncol=2, columnspacing=0.8, handlelength=1.4, title='Instances per image',
                       borderaxespad=0.4)
    legend.get_frame().set_facecolor('white')
    legend.get_title().set_fontweight('bold')
    legend.get_title().set_color('#1a1a1a')
    
    # No grid for cleaner appearance
    ax.grid(False)
    ax.set_axisbelow(True)
    
    # Style the tick colors
    ax.tick_params(colors='#555555')
    
    # Tight layout using full width (legend is inside top-right)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save figure with high resolution for printing
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=450, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"Figure saved to {output_path}")
    
    plt.close(fig)
    
    return fig, ax

def print_statistics(supercategory_data):
    """Print summary statistics."""
    print("\n" + "="*150)
    print("ANNOTATION STATISTICS BY SUPERCATEGORY AND INSTANCE COUNT")
    print("="*150)
    
    total_1 = 0
    total_2 = 0
    total_3 = 0
    total_4 = 0
    total_5 = 0
    total_6 = 0
    total_7 = 0
    total_8 = 0
    total_9 = 0
    total_10plus = 0
    
    for supercategory in sorted(supercategory_data.keys()):
        print(f"\n{supercategory}:")
        print("-" * 150)
        print(f"{'Part Category':<25} {'1':<8} {'2':<8} {'3':<8} {'4':<8} {'5':<8} {'6':<8} {'7':<8} {'8':<8} {'9':<8} {'10+':<8} {'Total':<10}")
        print("-" * 150)
        
        supercategory_total = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0, '10+': 0}
        
        for category in sorted(supercategory_data[supercategory].keys()):
            counts = supercategory_data[supercategory][category]
            total = counts['1'] + counts['2'] + counts['3'] + counts['4'] + counts['5'] + counts['6'] + counts['7'] + counts['8'] + counts['9'] + counts['10+']
            print(f"{category:<25} {counts['1']:<8} {counts['2']:<8} {counts['3']:<8} {counts['4']:<8} {counts['5']:<8} {counts['6']:<8} {counts['7']:<8} {counts['8']:<8} {counts['9']:<8} {counts['10+']:<8} {total:<10}")
            
            supercategory_total['1'] += counts['1']
            supercategory_total['2'] += counts['2']
            supercategory_total['3'] += counts['3']
            supercategory_total['4'] += counts['4']
            supercategory_total['5'] += counts['5']
            supercategory_total['6'] += counts['6']
            supercategory_total['7'] += counts['7']
            supercategory_total['8'] += counts['8']
            supercategory_total['9'] += counts['9']
            supercategory_total['10+'] += counts['10+']
        
        supercategory_sum = sum(supercategory_total.values())
        print("-" * 150)
        print(f"{'Subtotal':<25} {supercategory_total['1']:<8} {supercategory_total['2']:<8} {supercategory_total['3']:<8} {supercategory_total['4']:<8} {supercategory_total['5']:<8} {supercategory_total['6']:<8} {supercategory_total['7']:<8} {supercategory_total['8']:<8} {supercategory_total['9']:<8} {supercategory_total['10+']:<8} {supercategory_sum:<10}")
        
        total_1 += supercategory_total['1']
        total_2 += supercategory_total['2']
        total_3 += supercategory_total['3']
        total_4 += supercategory_total['4']
        total_5 += supercategory_total['5']
        total_6 += supercategory_total['6']
        total_7 += supercategory_total['7']
        total_8 += supercategory_total['8']
        total_9 += supercategory_total['9']
        total_10plus += supercategory_total['10+']
    
    print("\n" + "="*150)
    print(f"{'GRAND TOTAL':<25} {total_1:<8} {total_2:<8} {total_3:<8} {total_4:<8} {total_5:<8} {total_6:<8} {total_7:<8} {total_8:<8} {total_9:<8} {total_10plus:<8} {total_1 + total_2 + total_3 + total_4 + total_5 + total_6 + total_7 + total_8 + total_9 + total_10plus:<10}")
    print("="*150)

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
    
    # Count instances across all datasets
    supercategory_data, category_lookup = count_instances_per_category(datasets)
    
    # Print statistics
    print_statistics(supercategory_data)
    
    # Create visualization
    create_histogram(supercategory_data)

if __name__ == "__main__":
    main()
