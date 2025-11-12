#!/usr/bin/env python3
"""
Validate and fix COCO annotations:
1. Check segmentation is in RLE format (dict with 'size' and 'counts')
2. Validate bbox format: [x, y, width, height] with valid numbers
3. Validate area is a positive number
4. Validate iscrowd is 0 or 1
5. Remove invalid annotations and re-index IDs sequentially
"""

import json
import numpy as np
from pycocotools import mask as maskUtils

def is_valid_rle_segmentation(seg):
    """
    Check if segmentation is in valid RLE format.
    
    Args:
        seg: Segmentation data
    
    Returns:
        bool: True if valid RLE format
    """
    if not isinstance(seg, dict):
        return False
    
    if 'size' not in seg or 'counts' not in seg:
        return False
    
    # Check size is [height, width]
    if not isinstance(seg['size'], list) or len(seg['size']) != 2:
        return False
    
    # Check counts is a string (RLE encoded)
    if not isinstance(seg['counts'], str):
        return False
    
    return True


def is_valid_bbox(bbox):
    """
    Check if bbox is valid: [x, y, width, height] with positive dimensions.
    
    Args:
        bbox: Bounding box data
    
    Returns:
        tuple: (is_valid: bool, fixed_bbox: list or None)
    """
    if not isinstance(bbox, list):
        return False, None
    
    # Handle nested bbox arrays
    if len(bbox) > 0 and isinstance(bbox[0], list):
        # Nested array - try to flatten it
        if len(bbox) == 1 and len(bbox[0]) == 4:
            bbox = bbox[0]
        elif len(bbox) >= 1:
            # Multiple bboxes, take the first valid one
            bbox = bbox[0]
        else:
            return False, None
    
    # Check format
    if len(bbox) != 4:
        return False, None
    
    # Check all values are numbers
    try:
        x, y, w, h = [float(v) for v in bbox]
    except (ValueError, TypeError):
        return False, None
    
    # Check for valid dimensions (width and height must be positive)
    if w <= 0 or h <= 0:
        return False, None
    
    # Check for reasonable coordinates (not NaN or Inf)
    if any(np.isnan([x, y, w, h])) or any(np.isinf([x, y, w, h])):
        return False, None
    
    return True, [x, y, w, h]


def is_valid_area(area):
    """
    Check if area is a valid positive number.
    
    Args:
        area: Area value
    
    Returns:
        bool: True if valid
    """
    try:
        area = float(area)
        return area > 0 and not np.isnan(area) and not np.isinf(area)
    except (ValueError, TypeError):
        return False


def is_valid_iscrowd(iscrowd):
    """
    Check if iscrowd is valid (0 or 1).
    
    Args:
        iscrowd: iscrowd value
    
    Returns:
        bool: True if valid
    """
    try:
        iscrowd = int(iscrowd)
        return iscrowd in [0, 1]
    except (ValueError, TypeError):
        return False


def polygon_to_rle(segmentation, height, width):
    """
    Convert polygon segmentation to RLE format.
    
    Args:
        segmentation: List of polygons [[x1,y1,x2,y2,...], ...]
        height: Image height
        width: Image width
    
    Returns:
        RLE format dict with 'size' and 'counts' or None if conversion fails
    """
    try:
        if isinstance(segmentation, list):
            # Polygon format
            rles = maskUtils.frPyObjects(segmentation, height, width)
            rle = maskUtils.merge(rles)
            
            return {
                'size': [height, width],
                'counts': rle['counts'].decode('utf-8') if isinstance(rle['counts'], bytes) else rle['counts']
            }
        else:
            return None
    except Exception:
        return None

def main():
    train_path = '/Users/andylee/IVC/PartInventory/data/PartImageNet/spin_train_parts_validation/annotations/spin2_train_parts_with_instances.json'
    output_path = '/Users/andylee/IVC/PartInventory/data/PartImageNet/spin_train_parts_validation/annotations/spin2_train_parts_with_instances_fixed.json'
    
    print("="*70)
    print("COCO ANNOTATION VALIDATOR & FIXER")
    print("="*70)
    print(f"\nLoading annotations from: {train_path}")
    
    with open(train_path, 'r') as f:
        data = json.load(f)
    
    original_count = len(data['annotations'])
    print(f"Original annotation count: {original_count}")
    
    # Create image_id to dimensions mapping
    image_dims = {}
    for img in data['images']:
        image_dims[img['id']] = (img['height'], img['width'])
    
    print(f"\nValidating {original_count} annotations...")
    print("-"*70)
    
    # Statistics
    stats = {
        'invalid_segmentation': [],
        'invalid_bbox': [],
        'invalid_area': [],
        'invalid_iscrowd': [],
        'bbox_fixed': 0,
        'seg_converted': 0,
        'removed': []
    }
    
    valid_annotations = []
    
    for i, ann in enumerate(data['annotations']):
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{original_count} annotations...")
        
        ann_id = ann.get('id', i+1)
        image_id = ann.get('image_id')
        is_valid = True
        removal_reasons = []
        
        # 1. Check segmentation
        seg = ann.get('segmentation')
        if seg is None:
            is_valid = False
            removal_reasons.append('missing segmentation')
            stats['invalid_segmentation'].append(ann_id)
        elif is_valid_rle_segmentation(seg):
            # Already valid RLE
            pass
        elif isinstance(seg, list):
            # Try to convert polygon to RLE
            if image_id not in image_dims:
                is_valid = False
                removal_reasons.append('image_id not found')
            else:
                height, width = image_dims[image_id]
                rle = polygon_to_rle(seg, height, width)
                if rle is not None:
                    ann['segmentation'] = rle
                    stats['seg_converted'] += 1
                    if stats['seg_converted'] <= 3:
                        print(f"  ✓ Converted polygon to RLE for annotation {ann_id}")
                else:
                    is_valid = False
                    removal_reasons.append('failed to convert polygon to RLE')
                    stats['invalid_segmentation'].append(ann_id)
        else:
            is_valid = False
            removal_reasons.append('invalid segmentation format')
            stats['invalid_segmentation'].append(ann_id)
        
        # 2. Check and fix bbox
        bbox = ann.get('bbox')
        if bbox is None:
            is_valid = False
            removal_reasons.append('missing bbox')
            stats['invalid_bbox'].append(ann_id)
        else:
            bbox_valid, fixed_bbox = is_valid_bbox(bbox)
            if not bbox_valid:
                is_valid = False
                removal_reasons.append(f'invalid bbox: {bbox}')
                stats['invalid_bbox'].append(ann_id)
            elif fixed_bbox != bbox:
                ann['bbox'] = fixed_bbox
                stats['bbox_fixed'] += 1
                if stats['bbox_fixed'] <= 3:
                    print(f"  ✓ Fixed bbox for annotation {ann_id}: {bbox} -> {fixed_bbox}")
        
        # 3. Check area
        area = ann.get('area')
        if area is None:
            is_valid = False
            removal_reasons.append('missing area')
            stats['invalid_area'].append(ann_id)
        elif not is_valid_area(area):
            is_valid = False
            removal_reasons.append(f'invalid area: {area}')
            stats['invalid_area'].append(ann_id)
        
        # 4. Check iscrowd
        iscrowd = ann.get('iscrowd')
        if iscrowd is None:
            is_valid = False
            removal_reasons.append('missing iscrowd')
            stats['invalid_iscrowd'].append(ann_id)
        elif not is_valid_iscrowd(iscrowd):
            is_valid = False
            removal_reasons.append(f'invalid iscrowd: {iscrowd}')
            stats['invalid_iscrowd'].append(ann_id)
        
        # Keep or remove
        if is_valid:
            valid_annotations.append(ann)
        else:
            stats['removed'].append({
                'id': ann_id,
                'image_id': image_id,
                'reasons': removal_reasons
            })
            if len(stats['removed']) <= 10:
                print(f"  ✗ Removing annotation {ann_id}: {', '.join(removal_reasons)}")
    
    # Re-index annotation IDs sequentially
    print(f"\nRe-indexing {len(valid_annotations)} valid annotations...")
    for new_id, ann in enumerate(valid_annotations, start=1):
        ann['id'] = new_id
    
    # Update data with valid annotations only
    data['annotations'] = valid_annotations
    
    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print(f"Original annotations:        {original_count}")
    print(f"Valid annotations:           {len(valid_annotations)}")
    print(f"Removed annotations:         {len(stats['removed'])}")
    print(f"\nFixes applied:")
    print(f"  ✓ Fixed bbox format:       {stats['bbox_fixed']}")
    print(f"  ✓ Converted to RLE:        {stats['seg_converted']}")
    print(f"\nInvalid annotations by reason:")
    print(f"  ✗ Invalid segmentation:    {len(stats['invalid_segmentation'])}")
    print(f"  ✗ Invalid bbox:            {len(stats['invalid_bbox'])}")
    print(f"  ✗ Invalid area:            {len(stats['invalid_area'])}")
    print(f"  ✗ Invalid iscrowd:         {len(stats['invalid_iscrowd'])}")
    
    if stats['removed']:
        print(f"\nFirst 10 removed annotations:")
        for item in stats['removed'][:10]:
            print(f"  - ID {item['id']} (image {item['image_id']}): {', '.join(item['reasons'])}")
        if len(stats['removed']) > 10:
            print(f"  ... and {len(stats['removed']) - 10} more")
    
    print("="*70)
    
    # Save fixed file
    print(f"\nSaving cleaned annotations to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n✅ Done! The file has been validated and cleaned.")
    print(f"\nTo convert to CVAT format:")
    print(f"  datum convert -if coco \\")
    print(f"    -i {output_path} \\")
    print(f"    -f cvat \\")
    print(f"    -o output_cvat")
    print("\n" + "="*70)

if __name__ == '__main__':
    main()
