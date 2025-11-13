#!/usr/bin/env python3
"""
Dataset Statistics Generator
Generate comprehensive statistics for the Part Inventory dataset,
similar to those found in CVPR/ECCV/ICCV dataset papers.
"""

import json
import os
from collections import defaultdict
import numpy as np


def load_json(filepath):
    """Load a JSON annotation file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_dataset(annotation_files):
    """
    Analyze annotation files and compute comprehensive statistics.
    
    Returns a dictionary with all computed statistics.
    """
    stats = {
        'splits': {},
        'overall': defaultdict(int),
        'categories': defaultdict(lambda: defaultdict(int)),
        'supercategories': defaultdict(lambda: defaultdict(int)),
        'instance_distribution': defaultdict(int),
        'annotations_per_image': [],
        'instances_per_annotation': [],
        'area_statistics': []
    }
    
    # Process each split
    for filepath in annotation_files:
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping...")
            continue
            
        split_name = os.path.basename(filepath).replace('spin2_', '').replace('_parts.json', '')
        print(f"\nProcessing {split_name} split...")
        
        data = load_json(filepath)
        
        # Initialize split stats
        split_stats = {
            'num_images': len(data['images']),
            'num_annotations': len(data['annotations']),
            'num_categories': len(data['categories']),
            'annotations_per_image': [],
            'instances_per_image': defaultdict(int),
            'category_counts': defaultdict(int),
            'supercategory_counts': defaultdict(int)
        }
        
        # Build category lookup
        category_lookup = {}
        supercategory_lookup = {}
        for cat in data['categories']:
            category_lookup[cat['id']] = cat['name']
            supercategory_lookup[cat['id']] = cat['supercategory']
        
        # Count annotations per image
        image_annotations = defaultdict(list)
        for ann in data['annotations']:
            image_annotations[ann['image_id']].append(ann)
        
        # Analyze each image
        for img_id, anns in image_annotations.items():
            num_anns = len(anns)
            split_stats['annotations_per_image'].append(num_anns)
            stats['annotations_per_image'].append(num_anns)
            
            # Count instances per category in this image
            category_instances = defaultdict(int)
            for ann in anns:
                cat_id = ann['category_id']
                category_instances[cat_id] += 1
                
                # Track category and supercategory counts
                split_stats['category_counts'][category_lookup[cat_id]] += 1
                split_stats['supercategory_counts'][supercategory_lookup[cat_id]] += 1
                
                stats['categories'][category_lookup[cat_id]]['total_annotations'] += 1
                stats['supercategories'][supercategory_lookup[cat_id]]['total_annotations'] += 1
                
                # Track annotation area if available
                if 'area' in ann:
                    stats['area_statistics'].append(ann['area'])
            
            # Track instance distribution (how many instances per image per category)
            for cat_id, count in category_instances.items():
                stats['instance_distribution'][count] += 1
                split_stats['instances_per_image'][count] += 1
                stats['instances_per_annotation'].append(count)
                
                # Track category-specific instance stats
                cat_name = category_lookup[cat_id]
                if count == 1:
                    stats['categories'][cat_name]['single_instance'] += 1
                    stats['supercategories'][supercategory_lookup[cat_id]]['single_instance'] += 1
                else:
                    stats['categories'][cat_name]['multi_instance'] += 1
                    stats['supercategories'][supercategory_lookup[cat_id]]['multi_instance'] += 1
        
        # Store split statistics
        stats['splits'][split_name] = split_stats
        
        # Update overall counts
        stats['overall']['total_images'] += split_stats['num_images']
        stats['overall']['total_annotations'] += split_stats['num_annotations']
    
    # Compute derived statistics
    stats['overall']['num_categories'] = len(stats['categories'])
    stats['overall']['num_supercategories'] = len(stats['supercategories'])
    
    return stats


def print_summary_statistics(stats):
    """Print a summary table similar to CVPR/ECCV/ICCV papers."""
    
    print("\n" + "="*80)
    print("DATASET SUMMARY STATISTICS")
    print("="*80)
    
    # Overall statistics
    print("\n📊 Overall Statistics:")
    print(f"  Total Images:              {stats['overall']['total_images']:,}")
    print(f"  Total Annotation Entries:  {stats['overall']['total_annotations']:,}")
    print(f"  Number of Categories:      {stats['overall']['num_categories']}")
    print(f"  Number of Supercategories: {stats['overall']['num_supercategories']}")
    print(f"\n  ⚠️  IMPORTANT: Total Annotation Entries = {stats['overall']['total_annotations']:,}")
    print(f"     This is the sum of all annotation objects across the 3 JSON files.")
    
    # Split statistics
    print("\n📁 Split Statistics:")
    print(f"  {'Split':<10} {'Images':<12} {'Annotations':<15} {'Avg Ann/Img':<15}")
    print("  " + "-"*52)
    for split_name in ['train', 'val', 'test']:
        if split_name in stats['splits']:
            split_data = stats['splits'][split_name]
            avg_ann = np.mean(split_data['annotations_per_image'])
            print(f"  {split_name.capitalize():<10} {split_data['num_images']:<12,} "
                  f"{split_data['num_annotations']:<15,} {avg_ann:<15.2f}")
    
    print(f"\n  Combined total annotation entries: {stats['overall']['total_annotations']:,}")
    
    # Annotations per image statistics
    if stats['annotations_per_image']:
        ann_per_img = np.array(stats['annotations_per_image'])
        print("\n📈 Annotations per Image:")
        print(f"  Mean:   {ann_per_img.mean():.2f}")
        print(f"  Median: {np.median(ann_per_img):.2f}")
        print(f"  Min:    {ann_per_img.min()}")
        print(f"  Max:    {ann_per_img.max()}")
        print(f"  Std:    {ann_per_img.std():.2f}")
    
    # Instance distribution
    print("\n🔢 Instance Distribution (Images with N instances of a category):")
    total_image_category_pairs = sum(stats['instance_distribution'].values())
    print(f"  Total image-category pairs: {total_image_category_pairs:,}")
    
    # Calculate actual total instances
    total_instances = sum(k * v for k, v in stats['instance_distribution'].items())
    single_instances = stats['instance_distribution'].get(1, 0) * 1  # 1 instance each
    multi_instances = total_instances - single_instances
    
    print(f"  Total instances: {total_instances:,}")
    print(f"\n  {'Instances':<12} {'Count':<12} {'Total Inst':<12} {'Percentage':<12}")
    print("  " + "-"*48)
    
    for i in sorted(stats['instance_distribution'].keys())[:15]:  # Show first 15
        count = stats['instance_distribution'][i]
        total_inst = i * count
        pct = (count / total_image_category_pairs) * 100
        print(f"  {i:<12} {count:<12,} {total_inst:<12,} {pct:<12.2f}%")
    
    if len(stats['instance_distribution']) > 15:
        remaining_pairs = sum(stats['instance_distribution'][k] for k in stats['instance_distribution'].keys() 
                             if k > 15)
        remaining_inst = sum(k * stats['instance_distribution'][k] for k in stats['instance_distribution'].keys() 
                            if k > 15)
        pct = (remaining_pairs / total_image_category_pairs) * 100
        print(f"  {'16+':<12} {remaining_pairs:<12,} {remaining_inst:<12,} {pct:<12.2f}%")
    
    print(f"\n  Summary:")
    print(f"    Image-category pairs with 1 instance:   {stats['instance_distribution'].get(1, 0):,} pairs")
    print(f"    Image-category pairs with 2+ instances: {total_image_category_pairs - stats['instance_distribution'].get(1, 0):,} pairs")
    print(f"\n    Total instances from single (1 each):   {single_instances:,} instances")
    print(f"    Total instances from multiple (2+):     {multi_instances:,} instances")
    print(f"    Grand total:                             {total_instances:,} instances")
    print(f"\n    Percentage of instances that are single: {single_instances/total_instances*100:.2f}%")
    print(f"    Percentage of instances that are multi:  {multi_instances/total_instances*100:.2f}%")
    
    # Area statistics (if available)
    if stats['area_statistics']:
        areas = np.array(stats['area_statistics'])
        print("\n📐 Annotation Area Statistics (pixels²):")
        print(f"  Mean:   {areas.mean():.2f}")
        print(f"  Median: {np.median(areas):.2f}")
        print(f"  Min:    {areas.min():.2f}")
        print(f"  Max:    {areas.max():.2f}")
        print(f"  Std:    {areas.std():.2f}")
    
    print("\n" + "="*80)


def print_category_statistics(stats):
    """Print detailed category statistics."""
    
    print("\n" + "="*100)
    print("CATEGORY STATISTICS")
    print("="*100)
    
    # Sort categories by total annotations
    sorted_cats = sorted(stats['categories'].items(), 
                        key=lambda x: x[1]['total_annotations'], 
                        reverse=True)
    
    print(f"\n{'Category':<30} {'Total':<12} {'Single':<12} {'Multi':<12} {'% Single':<12}")
    print("-"*100)
    
    for cat_name, cat_stats in sorted_cats:
        total = cat_stats['total_annotations']
        single = cat_stats.get('single_instance', 0)
        multi = cat_stats.get('multi_instance', 0)
        pct_single = (single / (single + multi) * 100) if (single + multi) > 0 else 0
        
        print(f"{cat_name:<30} {total:<12,} {single:<12,} {multi:<12,} {pct_single:<12.1f}%")
    
    print("="*100)


def print_supercategory_statistics(stats):
    """Print supercategory statistics."""
    
    print("\n" + "="*100)
    print("SUPERCATEGORY STATISTICS")
    print("="*100)
    
    # Sort supercategories by total annotations
    sorted_supercats = sorted(stats['supercategories'].items(), 
                             key=lambda x: x[1]['total_annotations'], 
                             reverse=True)
    
    print(f"\n{'Supercategory':<30} {'Total':<12} {'Single':<12} {'Multi':<12} {'% Single':<12}")
    print("-"*100)
    
    for supercat_name, supercat_stats in sorted_supercats:
        total = supercat_stats['total_annotations']
        single = supercat_stats.get('single_instance', 0)
        multi = supercat_stats.get('multi_instance', 0)
        pct_single = (single / (single + multi) * 100) if (single + multi) > 0 else 0
        
        print(f"{supercat_name:<30} {total:<12,} {single:<12,} {multi:<12,} {pct_single:<12.1f}%")
    
    print("="*100)


def print_split_comparison(stats):
    """Print a comparison table across splits."""
    
    print("\n" + "="*80)
    print("SPLIT COMPARISON")
    print("="*80)
    
    splits = ['train', 'val', 'test']
    available_splits = [s for s in splits if s in stats['splits']]
    
    if not available_splits:
        print("No splits available for comparison.")
        return
    
    # Print instance distribution per split
    print("\nInstance Distribution by Split:")
    print(f"{'Instances':<12}", end='')
    for split in available_splits:
        print(f"{split.capitalize():<15}", end='')
    print()
    print("-"*80)
    
    # Get all unique instance counts
    all_instances = set()
    for split in available_splits:
        all_instances.update(stats['splits'][split]['instances_per_image'].keys())
    
    for i in sorted(list(all_instances))[:10]:  # Show first 10
        print(f"{i:<12}", end='')
        for split in available_splits:
            count = stats['splits'][split]['instances_per_image'].get(i, 0)
            print(f"{count:<15,}", end='')
        print()
    
    print("\n" + "="*80)


def export_statistics_to_latex(stats, output_file='dataset_statistics.tex'):
    """Export key statistics to a LaTeX table format."""
    
    with open(output_file, 'w') as f:
        f.write("% Dataset Statistics Table\n")
        f.write("\\begin{table}[t]\n")
        f.write("\\centering\n")
        f.write("\\caption{Dataset statistics for Part Inventory.}\n")
        f.write("\\label{tab:dataset_stats}\n")
        f.write("\\begin{tabular}{lccc}\n")
        f.write("\\toprule\n")
        f.write("Split & Images & Annotations & Avg. Ann/Img \\\\\n")
        f.write("\\midrule\n")
        
        for split_name in ['train', 'val', 'test']:
            if split_name in stats['splits']:
                split_data = stats['splits'][split_name]
                avg_ann = np.mean(split_data['annotations_per_image'])
                f.write(f"{split_name.capitalize()} & "
                       f"{split_data['num_images']:,} & "
                       f"{split_data['num_annotations']:,} & "
                       f"{avg_ann:.2f} \\\\\n")
        
        f.write("\\midrule\n")
        f.write(f"Total & {stats['overall']['total_images']:,} & "
               f"{stats['overall']['total_annotations']:,} & "
               f"{np.mean(stats['annotations_per_image']):.2f} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\n✅ LaTeX table exported to: {output_file}")


def main():
    """Main execution function."""
    
    # Define annotation files
    annotation_files = [
        'data/annotations/spin2_train_parts.json',
        'data/annotations/spin2_val_parts.json',
        'data/annotations/spin2_test_parts.json'
    ]
    
    print("\n" + "="*80)
    print("Part Inventory Dataset Statistics Generator")
    print("="*80)
    
    # Analyze dataset
    stats = analyze_dataset(annotation_files)
    
    # Print all statistics
    print_summary_statistics(stats)
    print_supercategory_statistics(stats)
    print_category_statistics(stats)
    print_split_comparison(stats)
    
    # Export to LaTeX
    export_statistics_to_latex(stats)
    
    print("\n✅ Analysis complete!\n")


if __name__ == "__main__":
    main()
