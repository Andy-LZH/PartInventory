#!/usr/bin/env python3
"""
Fix COCO annotations to match working test file format:
1. Fix nested bbox arrays: [[x,y,w,h]] -> [x,y,w,h]
2. Convert polygon segmentations to RLE format
"""

import json
import numpy as np
from pycocotools import mask as maskUtils

def polygon_to_rle(segmentation, height, width):
    """
    Convert polygon segmentation to RLE format.
    
    Args:
        segmentation: List of polygons [[x1,y1,x2,y2,...], ...]
        height: Image height
        width: Image width
    
    Returns:
        RLE format dict with 'size' and 'counts'
    """
    if isinstance(segmentation, list):
        # Polygon format
        rles = maskUtils.frPyObjects(segmentation, height, width)
        rle = maskUtils.merge(rles)
    else:
        # Already in some other format
        return segmentation
    
    return {
        'size': [height, width],
        'counts': rle['counts'].decode('utf-8') if isinstance(rle['counts'], bytes) else rle['counts']
    }

def fix_bbox_format(bbox):
    """
    Fix nested bbox arrays to flat format.
    
    Args:
        bbox: Could be [x,y,w,h] or [[x,y,w,h]] or [[x1,y1,w1,h1], [x2,y2,w2,h2]]
    
    Returns:
        Flat [x,y,w,h] array
    """
    if isinstance(bbox, list) and len(bbox) > 0:
        if isinstance(bbox[0], list):
            # Nested array - take the first bbox
            return bbox[0]
    return bbox

def main():
    train_path = '/Users/andylee/IVC/PartInventory/data/PartImageNet/spin_train_parts_validation/annotations/spin2_train_parts_with_instances.json'
    output_path = '/Users/andylee/IVC/PartInventory/data/PartImageNet/spin_train_parts_validation/annotations/spin2_train_parts_with_instances_fixed.json'
    
    print("Loading train annotations...")
    with open(train_path, 'r') as f:
        data = json.load(f)
    
    # Create image_id to dimensions mapping
    image_dims = {}
    for img in data['images']:
        image_dims[img['id']] = (img['height'], img['width'])
    
    print(f"Processing {len(data['annotations'])} annotations...")
    
    bbox_fixes = 0
    seg_conversions = 0
    errors = []
    
    for i, ann in enumerate(data['annotations']):
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{len(data['annotations'])} annotations...")
        
        # Fix bbox format
        original_bbox = ann['bbox']
        fixed_bbox = fix_bbox_format(original_bbox)
        if original_bbox != fixed_bbox:
            ann['bbox'] = fixed_bbox
            bbox_fixes += 1
            print(f"  Fixed bbox for annotation {ann['id']}: {original_bbox} -> {fixed_bbox}")
        
        # Convert segmentation to RLE if needed
        seg = ann.get('segmentation')
        if seg and isinstance(seg, list) and len(seg) > 0:
            # Check if it's polygon format (list of lists of coordinates)
            if isinstance(seg[0], list) or isinstance(seg[0], (int, float)):
                try:
                    image_id = ann['image_id']
                    if image_id not in image_dims:
                        errors.append(f"Annotation {ann['id']}: image_id {image_id} not found")
                        continue
                    
                    height, width = image_dims[image_id]
                    # Convert to RLE
                    rle = polygon_to_rle(seg[0], height, width)
                    ann['segmentation'] = rle
                    seg_conversions += 1
                    
                    if seg_conversions <= 5:
                        print(f"  Converted polygon to RLE for annotation {ann['id']}")
                
                except Exception as e:
                    errors.append(f"Annotation {ann['id']}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  ✓ Fixed {bbox_fixes} bbox format issues")
    print(f"  ✓ Converted {seg_conversions} polygon segmentations to RLE")
    if errors:
        print(f"  ⚠ {len(errors)} errors encountered:")
        for err in errors[:10]:
            print(f"    - {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    print(f"{'='*60}")
    
    # Save fixed file
    print(f"\nSaving fixed annotations to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✅ Done! Now you can submit the fixed file to CVAT.")
    print(f"\nTo use with Datumaro:")
    print(f"  datum convert -if coco_instances \\")
    print(f"    -i {output_path} \\")
    print(f"    -f cvat \\")
    print(f"    -o output_cvat")

if __name__ == '__main__':
    main()
