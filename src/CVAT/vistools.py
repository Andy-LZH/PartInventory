#!/usr/bin/env python3
"""
Visualization tools for SPIN-Instance annotation statistics.
Generates CVPR-style figures for LaTeX documents.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import seaborn as sns

# Set modern seaborn style
sns.set_style("whitegrid", {
    'grid.linestyle': ':',
    'grid.alpha': 0.2,
    'axes.edgecolor': '#e0e0e0',
    'axes.linewidth': 0.8
})
sns.set_context("notebook", font_scale=1.1)

# Modern matplotlib settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Open Sans', 'Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['pdf.fonttype'] = 42  # TrueType fonts for LaTeX compatibility
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

# Modern vibrant palette - clean and professional
COLOR_SINGLE = '#4A90E2'      # Vibrant blue - professional, trustworthy
COLOR_MULTIPLE = '#50C878'    # Emerald green - success, positive
COLOR_ERROR = '#E8705B'       # Coral red - alert, attention

def load_part_data(csv_path):
    """Load Part annotation data from CSV."""
    df = pd.read_csv(csv_path)

    # Extract object category from CategoryName (e.g., "Quadruped Head" -> "Quadruped")
    df['ObjectCategory'] = df['CategoryName'].str.rsplit(' ', n=1).str[0]

    return df

def create_combined_figure(df, output_path='figures/fig_combined.png', dpi=300):
    """
    Combined Figure: Part data (top row) with pie chart and histogram,
    Subpart placeholders (bottom row) in full scale matching the top.
    Emphasis on the histogram showing total cases by object category.
    """
    # Create figure with 2 rows: top for Part, bottom for Subpart
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.8], height_ratios=[1, 1],
                          wspace=0.3, hspace=0.6)
    fig.patch.set_facecolor('white')

    # ===== TOP LEFT: PIE CHART (Part) =====
    ax_pie = fig.add_subplot(gs[0, 0])

    # Calculate totals
    total_single = df['SingleInstanceCount'].sum()
    total_multiple = df['MultipleInstanceCount'].sum()
    total_error = df['SomethingWrong'].sum()
    total_all = total_single + total_multiple + total_error

    sizes = [total_single, total_multiple, total_error]
    labels = ['Single Instance', 'Multiple Instances', 'Something Wrong']
    colors = [COLOR_SINGLE, COLOR_MULTIPLE, COLOR_ERROR]

    wedges, texts, autotexts = ax_pie.pie(
        sizes,
        labels=None,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 10, 'weight': 'bold'},
        explode=(0.03, 0.03, 0.08),
        shadow=True
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(11)

    legend_labels = [
        f'Single: {total_single:,}',
        f'Multiple: {total_multiple:,}',
        f'Wrong: {total_error:,}'
    ]

    ax_pie.legend(
        wedges,
        legend_labels,
        loc='upper left',
        bbox_to_anchor=(0, 1),
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=9
    )

    ax_pie.set_title('(a) Part Instance Distribution', fontweight='bold', pad=15, fontsize=13)

    # ===== TOP RIGHT: HISTOGRAM (Part, EMPHASIZED) =====
    ax_hist = fig.add_subplot(gs[0, 1])

    # Group by object category
    category_stats = df.groupby('ObjectCategory').agg({
        'SingleInstanceCount': 'sum',
        'MultipleInstanceCount': 'sum',
        'SomethingWrong': 'sum',
        'TotalCase': 'sum'
    }).sort_values('TotalCase', ascending=False)

    x_pos = np.arange(len(category_stats))
    width = 0.7

    # Create stacked bars
    bars1 = ax_hist.bar(
        x_pos,
        category_stats['SingleInstanceCount'],
        width,
        label='Single Instance',
        color=COLOR_SINGLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    bars2 = ax_hist.bar(
        x_pos,
        category_stats['MultipleInstanceCount'],
        width,
        bottom=category_stats['SingleInstanceCount'],
        label='Multiple Instances',
        color=COLOR_MULTIPLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    # Make "Something Wrong" visible
    error_heights = category_stats['SomethingWrong'].copy()
    visual_min = category_stats['TotalCase'].max() * 0.012
    error_visual = error_heights.apply(lambda x: max(x, visual_min) if x > 0 else 0)

    bars3 = ax_hist.bar(
        x_pos,
        error_visual,
        width,
        bottom=category_stats['SingleInstanceCount'] + category_stats['MultipleInstanceCount'],
        label='Something is Wrong',
        color=COLOR_ERROR,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    ax_hist.set_xlabel('Object Category', fontweight='bold', fontsize=14)
    ax_hist.set_ylabel('Number of Cases', fontweight='bold', fontsize=14)
    ax_hist.set_title('(b) Part Annotation Statistics by Object Category',
                      fontweight='bold', pad=15, fontsize=13)
    ax_hist.set_xticks(x_pos)
    ax_hist.set_xticklabels(category_stats.index, rotation=45, ha='right', fontsize=11)

    ax_hist.legend(
        loc='upper right',
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=10,
        framealpha=0.95
    )

    ax_hist.grid(axis='y', alpha=0.3, linestyle='--', linewidth=1)
    ax_hist.set_axisbelow(True)

    # Add total count labels
    for i, (idx, row) in enumerate(category_stats.iterrows()):
        total = row['TotalCase']
        ax_hist.text(
            i, total + max(category_stats['TotalCase']) * 0.015,
            f"{int(total):,}",
            ha='center', va='bottom',
            fontsize=9,
            fontweight='bold',
            color='#2c3e50'
        )

    ymax = category_stats['TotalCase'].max() * 1.12
    ax_hist.set_ylim(0, ymax)

    # ===== BOTTOM LEFT: SUBPART INSTANCE DISTRIBUTION PLACEHOLDER =====
    ax_subpart_pie = fig.add_subplot(gs[1, 0])
    ax_subpart_pie.text(
        0.5, 0.5,
        'Subpart Data\n(To be provided)',
        ha='center',
        va='center',
        fontsize=16,
        color='#7f8c8d',
        style='italic',
        transform=ax_subpart_pie.transAxes,
        bbox=dict(
            boxstyle='round,pad=1.2',
            facecolor='#ecf0f1',
            edgecolor='#bdc3c7',
            linewidth=2
        )
    )
    ax_subpart_pie.set_title('(c) Subpart Instance Distribution', fontweight='bold', pad=15, fontsize=13)
    ax_subpart_pie.axis('off')

    # ===== BOTTOM RIGHT: SUBPART ANNOTATION STATISTICS PLACEHOLDER =====
    ax_subpart_hist = fig.add_subplot(gs[1, 1])
    ax_subpart_hist.text(
        0.5, 0.5,
        'Subpart Data\n(To be provided)',
        ha='center',
        va='center',
        fontsize=16,
        color='#7f8c8d',
        style='italic',
        transform=ax_subpart_hist.transAxes,
        bbox=dict(
            boxstyle='round,pad=1.2',
            facecolor='#ecf0f1',
            edgecolor='#bdc3c7',
            linewidth=2
        )
    )
    ax_subpart_hist.set_title('(d) Subpart Annotation Statistics by Object Category',
                             fontweight='bold', pad=15, fontsize=13)
    ax_subpart_hist.axis('off')

    plt.tight_layout()

    # Save figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: {output_file}")

    plt.close()

def create_pie_chart(df, output_path='figures/fig1_pie_chart.png', dpi=300):
    """
    Figure 1: Pie chart showing percentage of single vs multiple instances.
    Creates side-by-side layout (Part | Subpart placeholder).
    Includes "Something is Wrong" cases.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.patch.set_facecolor('white')

    # Calculate totals (including "Something Wrong" cases)
    total_single = df['SingleInstanceCount'].sum()
    total_multiple = df['MultipleInstanceCount'].sum()
    total_error = df['SomethingWrong'].sum()
    total_all = total_single + total_multiple + total_error

    # Left subplot: Part data
    sizes = [total_single, total_multiple, total_error]
    labels = ['Single Instance', 'Multiple Instances', 'Something Wrong']
    colors = [COLOR_SINGLE, COLOR_MULTIPLE, COLOR_ERROR]

    # Create pie chart with modern styling
    wedges, texts, autotexts = axes[0].pie(
        sizes,
        labels=None,  # We'll add custom legend
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 11, 'weight': 'bold'},
        explode=(0.03, 0.03, 0.08),
        shadow=True
    )

    # Style percentage text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(12)

    # Add custom legend with counts
    legend_labels = [
        f'Single Instance\n({total_single:,} cases, {100*total_single/total_all:.1f}%)',
        f'Multiple Instances\n({total_multiple:,} cases, {100*total_multiple/total_all:.1f}%)',
        f'Something Wrong\n({total_error:,} cases, {100*total_error/total_all:.1f}%)'
    ]

    axes[0].legend(
        wedges,
        legend_labels,
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=9
    )

    axes[0].set_title('Part Annotations Distribution', fontweight='bold', pad=20, fontsize=14)

    # Right subplot: Subpart placeholder
    axes[1].text(
        0.5, 0.5,
        'Subpart Data\n(To be provided)',
        ha='center',
        va='center',
        fontsize=14,
        color='#7f8c8d',
        style='italic',
        transform=axes[1].transAxes,
        bbox=dict(
            boxstyle='round,pad=1.0',
            facecolor='#ecf0f1',
            edgecolor='#bdc3c7',
            linewidth=2
        )
    )
    axes[1].set_title('Subpart Annotations Distribution', fontweight='bold', pad=20, fontsize=14)
    axes[1].axis('off')

    plt.tight_layout()

    # Save figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: {output_file}")

    # Print statistics
    print(f"\nPart Statistics:")
    print(f"  Single Instance: {total_single:,} ({100*total_single/total_all:.1f}%)")
    print(f"  Multiple Instances: {total_multiple:,} ({100*total_multiple/total_all:.1f}%)")
    print(f"  Something Wrong: {total_error:,} ({100*total_error/total_all:.1f}%)")
    print(f"  Total Cases: {total_all:,}")

    plt.close()

def create_histogram_counts(df, output_path='figures/fig2a_histogram_counts.png', dpi=300):
    """
    Figure 2a: Histogram showing total cases by object category.
    Stacked bars showing single vs multiple instances vs something wrong.
    """
    # Group by object category
    category_stats = df.groupby('ObjectCategory').agg({
        'SingleInstanceCount': 'sum',
        'MultipleInstanceCount': 'sum',
        'SomethingWrong': 'sum',
        'TotalCase': 'sum'
    }).sort_values('TotalCase', ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor('white')

    # Left subplot: Part data
    x_pos = np.arange(len(category_stats))
    width = 0.7

    # Create stacked bars with light minimalist styling
    bars1 = axes[0].bar(
        x_pos,
        category_stats['SingleInstanceCount'],
        width,
        label='Single Instance',
        color=COLOR_SINGLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    bars2 = axes[0].bar(
        x_pos,
        category_stats['MultipleInstanceCount'],
        width,
        bottom=category_stats['SingleInstanceCount'],
        label='Multiple Instances',
        color=COLOR_MULTIPLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    # Make "Something Wrong" more visible even when small
    # Add minimum visual height for visibility
    error_heights = category_stats['SomethingWrong'].copy()
    visual_min = category_stats['TotalCase'].max() * 0.012  # 1.2% of max height as minimum
    error_visual = error_heights.apply(lambda x: max(x, visual_min) if x > 0 else 0)

    bars3 = axes[0].bar(
        x_pos,
        error_visual,  # Use visual height
        width,
        bottom=category_stats['SingleInstanceCount'] + category_stats['MultipleInstanceCount'],
        label='Something is Wrong',
        color=COLOR_ERROR,
        edgecolor='white',  # Same white edge as others
        linewidth=1.5,
        alpha=0.9
    )

    axes[0].set_xlabel('Object Category', fontweight='bold', fontsize=13)
    axes[0].set_ylabel('Number of Cases', fontweight='bold', fontsize=13)
    axes[0].set_title('Part Annotations - Total Cases by Object Category',
                      fontweight='bold', pad=20, fontsize=14)
    axes[0].set_xticks(x_pos)
    axes[0].set_xticklabels(category_stats.index, rotation=45, ha='right', fontsize=10)

    # Place legend in upper right, inside plot
    axes[0].legend(
        loc='upper right',
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=10,
        framealpha=0.95
    )

    axes[0].grid(axis='y', alpha=0.3, linestyle='--', linewidth=1)
    axes[0].set_axisbelow(True)

    # Add total count labels on top of bars
    for i, (idx, row) in enumerate(category_stats.iterrows()):
        total = row['TotalCase']
        axes[0].text(
            i, total + max(category_stats['TotalCase']) * 0.015,
            f"{int(total):,}",
            ha='center', va='bottom',
            fontsize=9,
            fontweight='bold',
            color='#2c3e50'
        )

    # Add padding to y-axis
    ymax = category_stats['TotalCase'].max() * 1.12
    axes[0].set_ylim(0, ymax)

    # Right subplot: Subpart placeholder
    axes[1].text(
        0.5, 0.5,
        'Subpart Data\n(To be provided)',
        ha='center',
        va='center',
        fontsize=14,
        color='#7f8c8d',
        style='italic',
        transform=axes[1].transAxes,
        bbox=dict(
            boxstyle='round,pad=1.0',
            facecolor='#ecf0f1',
            edgecolor='#bdc3c7',
            linewidth=2
        )
    )
    axes[1].set_title('Subpart Annotations - Total Cases by Category',
                      fontweight='bold', pad=20, fontsize=14)
    axes[1].axis('off')

    plt.tight_layout()

    # Save figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: {output_file}")

    plt.close()

def create_histogram_percentage(df, output_path='figures/fig2b_histogram_percentage.png', dpi=300):
    """
    Figure 2b: Histogram showing percentage by object category.
    Stacked bars showing percentage of single vs multiple instances vs something wrong.
    """
    # Group by object category
    category_stats = df.groupby('ObjectCategory').agg({
        'SingleInstanceCount': 'sum',
        'MultipleInstanceCount': 'sum',
        'SomethingWrong': 'sum',
        'TotalCase': 'sum'
    })

    # Calculate percentages
    category_stats['SinglePct'] = 100 * category_stats['SingleInstanceCount'] / category_stats['TotalCase']
    category_stats['MultiplePct'] = 100 * category_stats['MultipleInstanceCount'] / category_stats['TotalCase']
    category_stats['ErrorPct'] = 100 * category_stats['SomethingWrong'] / category_stats['TotalCase']

    # Sort by total cases
    category_stats = category_stats.sort_values('TotalCase', ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor('white')

    # Left subplot: Part data
    x_pos = np.arange(len(category_stats))
    width = 0.7

    # Create stacked bars with light minimalist styling
    bars1 = axes[0].bar(
        x_pos,
        category_stats['SinglePct'],
        width,
        label='Single Instance',
        color=COLOR_SINGLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    bars2 = axes[0].bar(
        x_pos,
        category_stats['MultiplePct'],
        width,
        bottom=category_stats['SinglePct'],
        label='Multiple Instances',
        color=COLOR_MULTIPLE,
        edgecolor='white',
        linewidth=1.5,
        alpha=0.9
    )

    # Make "Something Wrong" more visible even when small
    # Add minimum visual height for visibility (minimum 2% visual height)
    error_pct_visual = category_stats['ErrorPct'].apply(lambda x: max(x, 2.0) if x > 0 else 0)

    bars3 = axes[0].bar(
        x_pos,
        error_pct_visual,  # Use visual height
        width,
        bottom=category_stats['SinglePct'] + category_stats['MultiplePct'],
        label='Something is Wrong',
        color=COLOR_ERROR,
        edgecolor='white',  # Same white edge as others
        linewidth=1.5,
        alpha=0.9
    )

    axes[0].set_xlabel('Object Category', fontweight='bold', fontsize=13)
    axes[0].set_ylabel('Percentage (%)', fontweight='bold', fontsize=13)
    axes[0].set_title('Part Annotations - Percentage Distribution by Category',
                      fontweight='bold', pad=20, fontsize=14)
    axes[0].set_xticks(x_pos)
    axes[0].set_xticklabels(category_stats.index, rotation=45, ha='right', fontsize=10)
    axes[0].set_ylim(0, 108)  # Increased slightly for better visibility

    # Place legend in upper right, inside plot
    axes[0].legend(
        loc='upper right',
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=10,
        framealpha=0.95
    )

    axes[0].grid(axis='y', alpha=0.3, linestyle='--', linewidth=1)
    axes[0].set_axisbelow(True)

    # Add percentage labels
    for i, (idx, row) in enumerate(category_stats.iterrows()):
        single_pct = row['SinglePct']
        multiple_pct = row['MultiplePct']
        error_pct = row['ErrorPct']

        # Label for single instance (if significant)
        if single_pct > 10:
            axes[0].text(
                i, single_pct/2, f"{single_pct:.0f}%",
                ha='center', va='center', fontsize=9,
                color='white', fontweight='bold'
            )

        # Label for multiple instances (if significant)
        if multiple_pct > 10:
            axes[0].text(
                i, single_pct + multiple_pct/2, f"{multiple_pct:.0f}%",
                ha='center', va='center', fontsize=9,
                color='white', fontweight='bold'
            )

        # Label for errors (if significant)
        if error_pct > 2:
            axes[0].text(
                i, single_pct + multiple_pct + error_pct/2, f"{error_pct:.1f}%",
                ha='center', va='center', fontsize=7,
                color='white', fontweight='bold'
            )

    # Right subplot: Subpart placeholder
    axes[1].text(
        0.5, 0.5,
        'Subpart Data\n(To be provided)',
        ha='center',
        va='center',
        fontsize=14,
        color='#7f8c8d',
        style='italic',
        transform=axes[1].transAxes,
        bbox=dict(
            boxstyle='round,pad=1.0',
            facecolor='#ecf0f1',
            edgecolor='#bdc3c7',
            linewidth=2
        )
    )
    axes[1].set_title('Subpart Annotations - Percentage Distribution by Category',
                      fontweight='bold', pad=20, fontsize=14)
    axes[1].axis('off')

    plt.tight_layout()

    # Save figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Saved: {output_file}")

    plt.close()

def print_summary_statistics(df):
    """Print detailed summary statistics."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS - PART ANNOTATIONS")
    print("="*70)

    # Overall statistics
    total_cases = df['TotalCase'].sum()
    total_single = df['SingleInstanceCount'].sum()
    total_multiple = df['MultipleInstanceCount'].sum()
    total_errors = df['SomethingWrong'].sum()

    print(f"\nOverall Statistics:")
    print(f"  Total Cases: {total_cases:,}")
    print(f"  Single Instance: {total_single:,} ({100*total_single/total_cases:.2f}%)")
    print(f"  Multiple Instances: {total_multiple:,} ({100*total_multiple/total_cases:.2f}%)")
    print(f"  Something Wrong: {total_errors:,} ({100*total_errors/total_cases:.2f}%)")

    # Per-category statistics
    print(f"\nPer-Object Category Statistics:")
    print(f"{'Category':<15} {'Total':>8} {'Single':>8} {'Multiple':>8} {'Error':>8} {'% Multiple':>12}")
    print("-" * 78)

    category_stats = df.groupby('ObjectCategory').agg({
        'TotalCase': 'sum',
        'SingleInstanceCount': 'sum',
        'MultipleInstanceCount': 'sum',
        'SomethingWrong': 'sum'
    }).sort_values('TotalCase', ascending=False)

    for category, row in category_stats.iterrows():
        total = row['TotalCase']
        single = row['SingleInstanceCount']
        multiple = row['MultipleInstanceCount']
        error = row['SomethingWrong']
        pct_multiple = 100 * multiple / total if total > 0 else 0

        print(f"{category:<15} {int(total):>8,} {int(single):>8,} {int(multiple):>8,} {int(error):>8,} {pct_multiple:>11.1f}%")

    print("="*70)

def main():
    """Main function to generate all visualizations."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate CVPR-style visualizations for SPIN-Instance annotations'
    )
    parser.add_argument(
        '--csv',
        default='data/SPIN-Part-Test-Filled.csv',
        help='Path to CSV file with Part annotation data (default: data/SPIN-Part-Test-Filled.csv)'
    )
    parser.add_argument(
        '--output-dir',
        default='figures',
        help='Output directory for figures (default: figures)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for output figures (default: 300)'
    )
    parser.add_argument(
        '--format',
        choices=['png', 'pdf', 'both'],
        default='png',
        help='Output format: png, pdf, or both (default: png)'
    )

    args = parser.parse_args()

    print("="*70)
    print("SPIN-Instance Annotation Visualization Tool")
    print("="*70)

    # Load data
    print(f"\nLoading data from: {args.csv}")
    df = load_part_data(args.csv)
    print(f"✓ Loaded {len(df)} categories")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate figures
    print(f"\nGenerating figures (DPI={args.dpi}, format={args.format})...")

    formats = ['png', 'pdf'] if args.format == 'both' else [args.format]

    for fmt in formats:
        print(f"\n--- Generating {fmt.upper()} figures ---")

        # Combined Figure: Pie chart + Histogram (emphasized)
        fig_combined_path = output_dir / f'fig_combined.{fmt}'
        create_combined_figure(df, fig_combined_path, dpi=args.dpi)

    # Print summary statistics
    print_summary_statistics(df)

    print(f"\n✓ All figures saved to: {output_dir.absolute()}")
    print("\nFigure generated:")
    print("  - fig_combined: Instance distribution (pie) + Annotation statistics by category (histogram)")
    print("\nNote: Histogram emphasized with larger size")
    print("="*70)

if __name__ == '__main__':
    main()
