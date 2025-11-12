import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import os

# Set style for publication-quality figures
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 13

def load_annotation_data(json_path):
    """Load annotation data from JSON file."""
    print(f"Loading data from {json_path}...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def count_instances_per_category(data):
    """
    Count annotations grouped by part category and supercategory,
    split by instance count (1, 2, 3+).
    """
    # Create category lookup
    category_lookup = {}
    for cat in data['categories']:
        category_lookup[cat['id']] = {
            'name': cat['name'],
            'supercategory': cat['supercategory']
        }
    
    # Count instances per image and category
    # Structure: {image_id: {category_id: [instance_type_list]}}
    image_category_instances = defaultdict(lambda: defaultdict(list))
    
    for ann in data['annotations']:
        image_id = ann['image_id']
        category_id = ann['category_id']
        instance_type = ann.get('instance_type', 0)
        image_category_instances[image_id][category_id].append(instance_type)
    
    # Count annotations by category and instance count
    # Structure: {category_id: {'1': count, '2': count, '3+': count}}
    category_instance_counts = defaultdict(lambda: {'1': 0, '2': 0, '3+': 0})
    
    for image_id, categories in image_category_instances.items():
        for category_id, instances in categories.items():
            num_instances = len(set(instances))  # Count unique instances
            
            if num_instances == 1:
                category_instance_counts[category_id]['1'] += 1
            elif num_instances == 2:
                category_instance_counts[category_id]['2'] += 1
            else:  # 3 or more
                category_instance_counts[category_id]['3+'] += 1
    
    # Group by supercategory
    supercategory_data = defaultdict(lambda: defaultdict(lambda: {'1': 0, '2': 0, '3+': 0}))
    
    for category_id, counts in category_instance_counts.items():
        cat_info = category_lookup[category_id]
        supercategory = cat_info['supercategory']
        category_name = cat_info['name']
        supercategory_data[supercategory][category_name] = counts
    
    return supercategory_data, category_lookup

def create_histogram(supercategory_data, output_path='cvpr_figures/instance_histogram.png'):
    """
    Create a grouped histogram showing annotations by part category,
    grouped by supercategory, with splits for 1, 2, and 3+ instances.
    """
    # Prepare data for plotting
    supercategories = sorted(supercategory_data.keys())
    
    # Colors for instance counts
    colors = {
        '1': '#2E86AB',    # Blue
        '2': '#A23B72',    # Purple
        '3+': '#F18F01'    # Orange
    }
    
    # Calculate figure size based on number of categories
    total_categories = sum(len(cats) for cats in supercategory_data.values())
    fig_width = max(12, total_categories * 0.4)
    fig_height = 6
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Prepare data
    all_categories = []
    all_supercategories = []
    counts_1 = []
    counts_2 = []
    counts_3plus = []
    
    for supercategory in supercategories:
        categories = sorted(supercategory_data[supercategory].keys())
        for category in categories:
            all_categories.append(category)
            all_supercategories.append(supercategory)
            counts = supercategory_data[supercategory][category]
            counts_1.append(counts['1'])
            counts_2.append(counts['2'])
            counts_3plus.append(counts['3+'])
    
    # Create grouped bar chart
    x = np.arange(len(all_categories))
    width = 0.25
    
    bars1 = ax.bar(x - width, counts_1, width, label='1 Instance', 
                   color=colors['1'], edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x, counts_2, width, label='2 Instances', 
                   color=colors['2'], edgecolor='black', linewidth=0.5)
    bars3 = ax.bar(x + width, counts_3plus, width, label='3+ Instances', 
                   color=colors['3+'], edgecolor='black', linewidth=0.5)
    
    # Add vertical lines to separate supercategories
    current_supercategory = all_supercategories[0]
    supercategory_positions = [0]
    supercategory_labels = [current_supercategory]
    
    for i, supercategory in enumerate(all_supercategories[1:], start=1):
        if supercategory != current_supercategory:
            ax.axvline(x=i - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            supercategory_positions.append(i)
            supercategory_labels.append(supercategory)
            current_supercategory = supercategory
    
    # Labels and formatting
    ax.set_xlabel('Part Category', fontweight='bold')
    ax.set_ylabel('Number of Annotations', fontweight='bold')
    ax.set_title('Part Category Annotations by Instance Count', fontweight='bold', pad=20)
    
    # X-axis: show category names rotated
    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, rotation=45, ha='right')
    
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
    ax2.set_xticklabels(supercategory_labels, fontweight='bold', fontsize=10)
    ax2.tick_params(axis='x', which='major', pad=10)
    
    # Legend
    ax.legend(loc='upper right', framealpha=0.9)
    
    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to {output_path}")
    
    # Also save as PDF for publications
    pdf_path = output_path.replace('.png', '.pdf')
    plt.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to {pdf_path}")
    
    plt.show()
    
    return fig, ax

def print_statistics(supercategory_data):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("ANNOTATION STATISTICS BY SUPERCATEGORY AND INSTANCE COUNT")
    print("="*80)
    
    total_1 = 0
    total_2 = 0
    total_3plus = 0
    
    for supercategory in sorted(supercategory_data.keys()):
        print(f"\n{supercategory}:")
        print("-" * 80)
        print(f"{'Part Category':<30} {'1 Instance':<15} {'2 Instances':<15} {'3+ Instances':<15} {'Total':<10}")
        print("-" * 80)
        
        supercategory_total = {'1': 0, '2': 0, '3+': 0}
        
        for category in sorted(supercategory_data[supercategory].keys()):
            counts = supercategory_data[supercategory][category]
            total = counts['1'] + counts['2'] + counts['3+']
            print(f"{category:<30} {counts['1']:<15} {counts['2']:<15} {counts['3+']:<15} {total:<10}")
            
            supercategory_total['1'] += counts['1']
            supercategory_total['2'] += counts['2']
            supercategory_total['3+'] += counts['3+']
        
        supercategory_sum = sum(supercategory_total.values())
        print("-" * 80)
        print(f"{'Subtotal':<30} {supercategory_total['1']:<15} {supercategory_total['2']:<15} {supercategory_total['3+']:<15} {supercategory_sum:<10}")
        
        total_1 += supercategory_total['1']
        total_2 += supercategory_total['2']
        total_3plus += supercategory_total['3+']
    
    print("\n" + "="*80)
    print(f"{'GRAND TOTAL':<30} {total_1:<15} {total_2:<15} {total_3plus:<15} {total_1 + total_2 + total_3plus:<10}")
    print("="*80)

def main():
    # Path to annotation file
    annotation_file = 'data/spin2_train_parts_with_instances_fixed.json'
    
    # Check if file exists
    if not os.path.exists(annotation_file):
        print(f"Error: File not found: {annotation_file}")
        return
    
    # Load data
    data = load_annotation_data(annotation_file)
    
    # Count instances
    supercategory_data, category_lookup = count_instances_per_category(data)
    
    # Print statistics
    print_statistics(supercategory_data)
    
    # Create visualization
    create_histogram(supercategory_data)

if __name__ == "__main__":
    main()
