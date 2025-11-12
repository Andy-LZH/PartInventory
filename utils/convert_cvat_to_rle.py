#!/usr/bin/env python3
"""
Convert CVAT polygon annotations to RLE format and fill in metadata.

This script:
1. Converts polygon segmentations to RLE format (compressed)
2. Fills in proper COCO metadata (info, contributor, etc.)
3. Adds supercategory information
4. Adds instance_id and category_name to annotations
5. Processes multiple files in a directory
"""

import json
import os
import sys
import glob
from datetime import datetime
from pycocotools import mask as mask_utils
import numpy as np
from PIL import Image, ImageDraw


def polygon_to_rle(segmentation, width, height):
    """
    Convert polygon segmentation to RLE format.
    
    Args:
        segmentation: List of polygon coordinates [x1,y1,x2,y2,...]
        width: Image width
        height: Image height
    
    Returns:
        RLE format dict with 'size' and 'counts'
    """
    if not segmentation or len(segmentation) == 0:
        return None
    
    try:
        # Handle list of polygons
        if isinstance(segmentation[0], list):
            # Multiple polygons - create a combined mask
            mask_img = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(mask_img)
            
            for poly in segmentation:
                if len(poly) >= 6:  # Need at least 3 points
                    polygon = [(poly[i], poly[i+1]) for i in range(0, len(poly), 2)]
                    draw.polygon(polygon, outline=1, fill=1)
            
            mask = np.array(mask_img, dtype=np.uint8)
        
        elif isinstance(segmentation[0], (int, float)):
            # Single polygon
            polygon = [(segmentation[i], segmentation[i+1]) for i in range(0, len(segmentation), 2)]
            mask_img = Image.new('L', (width, height), 0)
            ImageDraw.Draw(mask_img).polygon(polygon, outline=1, fill=1)
            mask = np.array(mask_img, dtype=np.uint8)
        
        else:
            print(f"   ⚠️  Unsupported segmentation format")
            return None
        
        # Convert to Fortran order as required by pycocotools
        mask = np.asfortranarray(mask)
        
        # Encode to RLE
        rle = mask_utils.encode(mask)
        
        # Convert bytes to string for JSON serialization
        if isinstance(rle['counts'], bytes):
            rle['counts'] = rle['counts'].decode('utf-8')
        
        return rle
    
    except Exception as e:
        print(f"   ⚠️  Error converting polygon to RLE: {e}")
        return None


def get_supercategory(category_name):
    """Map category names to supercategories."""
    supercategory_map = {
        'Quadruped Head': 'Quadruped',
        'Quadruped Body': 'Quadruped',
        'Quadruped Foot': 'Quadruped',
        'Quadruped Tail': 'Quadruped',
        'Biped Head': 'Biped',
        'Biped Body': 'Biped',
        'Biped Arm': 'Biped',
        'Biped Leg': 'Biped',
        'Biped Tail': 'Biped',
        'Fish Head': 'Fish',
        'Fish Body': 'Fish',
        'Fish Fin': 'Fish',
        'Fish Tail': 'Fish',
        'Bird Head': 'Bird',
        'Bird Body': 'Bird',
        'Bird Wing': 'Bird',
        'Bird Foot': 'Bird',
        'Bird Tail': 'Bird',
        'Snake Head': 'Snake',
        'Snake Body': 'Snake',
        'Reptile Head': 'Reptile',
        'Reptile Body': 'Reptile',
        'Reptile Foot': 'Reptile',
        'Reptile Tail': 'Reptile',
        'Car Body': 'Car',
        'Car Tire': 'Car',
        'Car Side Mirror': 'Car',
        'Bicycle Body': 'Bicycle',
        'Bicycle Head': 'Bicycle',
        'Bicycle Seat': 'Bicycle',
        'Bicycle Tire': 'Bicycle',
        'Boat Body': 'Boat',
        'Boat Sail': 'Boat',
        'Aeroplane Head': 'Aeroplane',
        'Aeroplane Body': 'Aeroplane',
        'Aeroplane Engine': 'Aeroplane',
        'Aeroplane Wing': 'Aeroplane',
        'Aeroplane Tail': 'Aeroplane',
        'Bottle Mouth': 'Bottle',
        'Bottle Body': 'Bottle',
    }
    return supercategory_map.get(category_name, '')


def convert_cvat_to_rle(input_file, output_file=None):
    """
    Convert CVAT annotations to RLE format with proper metadata.
    
    Args:
        input_file: Path to input CVAT JSON file
        output_file: Path to output file (default: add _rle suffix)
    """
    print(f"\n{'='*70}")
    print(f"📖 Processing: {os.path.basename(input_file)}")
    print(f"{'='*70}")
    
    # Load data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"   Images: {len(data.get('images', []))}")
    print(f"   Annotations: {len(data.get('annotations', []))}")
    print(f"   Categories: {len(data.get('categories', []))}")
    
    # Fill in metadata
    print(f"\n📝 Filling metadata...")
    data['info'] = {
        "contributor": "SPIN Instance Segmentation Team",
        "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "SPIN2 Part-level Instance Segmentation Dataset",
        "url": "https://github.com/yourusername/SPIN-Instance-CVAT",
        "version": "2.0",
        "year": datetime.now().year
    }
    
    data['licenses'] = [
        {
            "name": "Attribution-NonCommercial-ShareAlike License",
            "id": 1,
            "url": "http://creativecommons.org/licenses/by-nc-sa/2.0/"
        }
    ]
    
    # Add supercategories to categories
    print(f"📋 Adding supercategories...")
    for cat in data['categories']:
        cat['supercategory'] = get_supercategory(cat['name'])
    
    # Build image ID to image info mapping
    image_id_to_info = {img['id']: img for img in data['images']}
    
    # Build category ID to name mapping
    category_id_to_name = {cat['id']: cat['name'] for cat in data['categories']}
    
    # Group annotations by image_id and category_id to assign instance_ids
    print(f"\n🔢 Assigning instance IDs...")
    from collections import defaultdict
    image_category_instances = defaultdict(lambda: defaultdict(list))
    
    for ann in data['annotations']:
        image_id = ann['image_id']
        category_id = ann['category_id']
        image_category_instances[image_id][category_id].append(ann)
    
    # Convert polygons to RLE and add metadata
    # print(f"\n🔄 Converting polygons to RLE format...")
    converted_count = 0
    skipped_count = 0
    error_count = 0
    
    for ann in data['annotations']:
        image_id = ann['image_id']
        category_id = ann['category_id']
        
        # Get image dimensions
        if image_id not in image_id_to_info:
            print(f"   📝 Annotation {ann['id']}: category='{ann['category_name']}', instance_id={ann['instance_id']}, image_id={image_id}")
            print(f"   ❌ ERROR: Image ID {image_id} not found for annotation {ann['id']}")
            error_count += 1
            continue
        
        img_info = image_id_to_info[image_id]
        width = img_info['width']
        height = img_info['height']
        
        # Add category_name
        ann['category_name'] = category_id_to_name.get(category_id, 'Unknown')
        
        # Assign instance_id (1-indexed per image+category)
        instances_in_this_image_category = image_category_instances[image_id][category_id]
        instance_idx = instances_in_this_image_category.index(ann) + 1
        ann['instance_id'] = instance_idx
        
        
        # Convert segmentation to RLE if it's in polygon format
        segmentation = ann.get('segmentation')
        
        if segmentation:
            # Check if already in RLE format
            if isinstance(segmentation, dict) and 'counts' in segmentation:
                # Already RLE
                print(f"      ⏭️  Already in RLE format")
                skipped_count += 1
            elif isinstance(segmentation, list):
                # Polygon format - convert to RLE
                # print(f"      🔄 Converting polygon to RLE...")
                rle = polygon_to_rle(segmentation, width, height)
                
                if rle:
                    ann['segmentation'] = rle
                    # print(f"      ✅ Successfully converted to RLE")
                    converted_count += 1
                else:
                    print(f"   📝 Annotation {ann['id']}: category='{ann['category_name']}', instance_id={ann['instance_id']}, image_id={image_id}")
                    print(f"      ❌ ERROR: Failed to convert polygon to RLE")
                    error_count += 1
            else:
                print(f"   📝 Annotation {ann['id']}: category='{ann['category_name']}', instance_id={ann['instance_id']}, image_id={image_id}")
                print(f"      ❌ ERROR: Unknown segmentation format (type: {type(segmentation).__name__})")
                error_count += 1
        else:
            print(f"   📝 Annotation {ann['id']}: category='{ann['category_name']}', instance_id={ann['instance_id']}, image_id={image_id}")
            print(f"      ❌ ERROR: No segmentation data found")
            error_count += 1
    
    print(f"\n📊 Conversion Statistics:")
    print(f"   ✅ Converted to RLE: {converted_count}")
    print(f"   ⏭️  Already RLE: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    
    # Determine output filename
    if not output_file:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_rle{ext}"
    
    # Save result
    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"   ✅ Saved successfully!")
    
    # Show file size comparison
    input_size = os.path.getsize(input_file) / (1024 * 1024)
    output_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\n📏 File size:")
    print(f"   Input:  {input_size:.2f} MB")
    print(f"   Output: {output_size:.2f} MB")
    
    return output_file


def process_directory(directory, pattern="*.json", output_dir=None):
    """
    Process all JSON files in a directory.
    
    Args:
        directory: Directory containing JSON files
        pattern: File pattern to match (default: *.json)
        output_dir: Output directory (default: same as input)
    """
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)
    
    if not files:
        print(f"❌ No files found matching: {search_path}")
        return
    
    print(f"🔍 Found {len(files)} files to process")
    
    for i, input_file in enumerate(sorted(files), 1):
        print(f"\n{'#'*70}")
        print(f"# File {i}/{len(files)}")
        print(f"{'#'*70}")
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            basename = os.path.basename(input_file)
            base, ext = os.path.splitext(basename)
            output_file = os.path.join(output_dir, f"{base}_rle{ext}")
        else:
            output_file = None
        
        try:
            convert_cvat_to_rle(input_file, output_file)
        except Exception as e:
            print(f"❌ Error processing {input_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print(f"✨ Finished processing {len(files)} files!")
    print(f"{'='*70}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  # Process single file:")
        print("  python convert_cvat_to_rle.py <input.json> [output.json]")
        print("\n  # Process all JSON files in directory:")
        print("  python convert_cvat_to_rle.py <directory> [output_directory]")
        print("\nExamples:")
        print("  python convert_cvat_to_rle.py instances_default.json")
        print("  python convert_cvat_to_rle.py instances_default.json output_rle.json")
        print("  python convert_cvat_to_rle.py '/Users/andylee/Downloads/annotations 3/'")
        print("  python convert_cvat_to_rle.py '/Users/andylee/Downloads/annotations 3/' output_dir/")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("🚀 CVAT to RLE Converter")
    print("="*70)
    
    if os.path.isfile(input_path):
        # Process single file
        convert_cvat_to_rle(input_path, output_path)
    elif os.path.isdir(input_path):
        # Process directory
        process_directory(input_path, "*.json", output_path)
    else:
        print(f"❌ Path not found: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
