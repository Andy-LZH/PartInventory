# Instance Tracking and Retrieval Guide

This guide explains the instance tracking metadata added to processed CVAT annotations and how to efficiently retrieve ground truth instances during experiments.

## 📊 Instance Tracking Metadata

After processing with `process_cvat_annotations.py`, each annotation includes:

### Added Fields:

1. **`category_name`** (string)
   - Human-readable category name (e.g., "QuadrupedLeg", "BipedArm")
   - Easier than looking up category_id in categories list
   - Example: `"category_name": "QuadrupedLeg"`

2. **`instance_id`** (integer)
   - Sequential instance number per (image, category) pair
   - Starts from 0 for each unique combination
   - Consistent ordering: sorted by annotation order
   - Example: `"instance_id": 0`, `"instance_id": 1`, etc.

3. **`image_category_key`** (string)
   - Fast lookup key: `"{image_id}_{category_id}"`
   - Enables O(1) retrieval with pre-built index
   - Example: `"image_category_key": "501_7"`

### Example Annotation Structure:

```json
{
  "id": 15432,
  "image_id": 501,
  "category_id": 7,
  "category_name": "QuadrupedLeg",
  "instance_id": 0,
  "image_category_key": "501_7",
  "segmentation": {
    "size": [375, 500],
    "counts": "RLE_encoded_string..."
  },
  "area": 2852,
  "bbox": [x, y, w, h],
  "iscrowd": 0
}
```

## 🔍 Retrieval Patterns

### Pattern 1: Get All Instances of a Category for One Image

**Use Case:** Processing ground truth for a specific category

```python
def get_instances_by_category(annotations, image_id, category_name):
    instances = [
        ann for ann in annotations
        if ann.get('image_id') == image_id
        and ann.get('category_name') == category_name
    ]
    # Sort by instance_id for consistent ordering
    instances.sort(key=lambda x: x.get('instance_id', 0))
    return instances

# Example usage
quadruped_legs = get_instances_by_category(data['annotations'], 501, 'QuadrupedLeg')
print(f"Found {len(quadruped_legs)} quadruped leg instances")

for inst in quadruped_legs:
    print(f"Instance {inst['instance_id']}: bbox={inst['bbox']}")
    mask = decode_rle(inst['segmentation'])
    # Process mask...
```

### Pattern 2: Get All Categories for One Image

**Use Case:** Multi-task learning, analyzing all parts of an object

```python
from collections import defaultdict

def get_all_instances_for_image(annotations, image_id):
    category_groups = defaultdict(list)

    for ann in annotations:
        if ann.get('image_id') == image_id:
            cat_name = ann.get('category_name')
            category_groups[cat_name].append(ann)

    # Sort each category's instances
    for cat in category_groups:
        category_groups[cat].sort(key=lambda x: x.get('instance_id', 0))

    return dict(category_groups)

# Example usage
all_instances = get_all_instances_for_image(data['annotations'], 501)

for category_name, instances in all_instances.items():
    print(f"{category_name}: {len(instances)} instances")
```

### Pattern 3: Fast Batch Retrieval (Recommended for Experiments)

**Use Case:** Training/evaluation loops processing many images

```python
from collections import defaultdict

# Build index once at start of experiment
def build_instance_index(annotations):
    index = defaultdict(list)

    for ann in annotations:
        key = ann.get('image_category_key')
        if key:
            index[key].append(ann)

    # Sort each group by instance_id
    for key in index:
        index[key].sort(key=lambda x: x.get('instance_id', 0))

    return index

# Build index once
instance_index = build_instance_index(data['annotations'])

# Fast retrieval during training
def get_instances_fast(index, image_id, category_id):
    key = f"{image_id}_{category_id}"
    return index.get(key, [])

# Example: Training loop
for image_id in train_images:
    # O(1) lookup instead of O(N) scan
    instances = get_instances_fast(instance_index, image_id, category_id=7)

    for inst in instances:
        mask = decode_rle(inst['segmentation'])
        # Train model...
```

### Pattern 4: Processing Multiple Categories

**Use Case:** Part-based recognition, hierarchical models

```python
def process_image_with_multiple_categories(annotations, image_id, target_categories):
    results = {}

    for category_name in target_categories:
        instances = get_instances_by_category(annotations, image_id, category_name)

        masks = []
        bboxes = []

        for inst in instances:
            mask = decode_rle(inst['segmentation'])
            masks.append(mask)
            bboxes.append(inst['bbox'])

        results[category_name] = {
            'instances': instances,
            'masks': masks,
            'bboxes': bboxes,
            'count': len(instances)
        }

    return results

# Example usage
target_categories = ['QuadrupedLeg', 'QuadrupedHead', 'QuadrupedBody', 'QuadrupedTail']
results = process_image_with_multiple_categories(data['annotations'], 501, target_categories)

for cat_name, cat_data in results.items():
    print(f"{cat_name}: {cat_data['count']} instances")
```

## 🎯 Experiment Workflow Example

### Complete Pipeline:

```python
import json
from pycocotools import mask as mask_utils
import numpy as np

# 1. Load data
with open('merged/spin2/spin2_val_parts.json', 'r') as f:
    data = json.load(f)

# 2. Build fast lookup index
instance_index = build_instance_index(data['annotations'])

# 3. Define experiment parameters
target_categories = ['QuadrupedLeg', 'BipedArm', 'BirdWing']
category_id_map = {cat['name']: cat['id'] for cat in data['categories']}

# 4. Process each image
results = []

for image in data['images']:
    image_id = image['id']

    for category_name in target_categories:
        category_id = category_id_map.get(category_name)
        if not category_id:
            continue

        # Fast retrieval
        instances = get_instances_fast(instance_index, image_id, category_id)

        # Process each instance
        for inst in instances:
            # Decode ground truth
            gt_mask = mask_utils.decode(inst['segmentation'])
            gt_bbox = inst['bbox']

            # Run your model
            pred_mask, pred_bbox = your_model.predict(image, category_name)

            # Compute metrics
            iou = compute_iou(gt_mask, pred_mask)

            # Store results with instance tracking
            results.append({
                'image_id': image_id,
                'category_name': category_name,
                'instance_id': inst['instance_id'],
                'iou': iou,
                'gt_area': inst['area'],
                'pred_area': pred_mask.sum()
            })

# 5. Analyze results per category and instance
from collections import defaultdict

category_results = defaultdict(list)
for result in results:
    category_results[result['category_name']].append(result)

for cat_name, cat_results in category_results.items():
    mean_iou = np.mean([r['iou'] for r in cat_results])
    print(f"{cat_name}: mean IoU = {mean_iou:.3f} ({len(cat_results)} instances)")
```

## 📝 Best Practices

### 1. **Always Sort by instance_id**
Ensures consistent ordering across runs:
```python
instances.sort(key=lambda x: x.get('instance_id', 0))
```

### 2. **Use Fast Index for Batch Processing**
Build once, reuse many times:
```python
# Build at start
index = build_instance_index(annotations)

# Use in loops (O(1) instead of O(N))
for image_id in all_images:
    instances = get_instances_fast(index, image_id, category_id)
```

### 3. **Check for Empty Results**
Not all images have all categories:
```python
instances = get_instances_by_category(annotations, image_id, category_name)
if not instances:
    print(f"No {category_name} instances in image {image_id}")
    continue
```

### 4. **Use category_name for Readability**
More maintainable than numeric IDs:
```python
# Good
instances = get_instances_by_category(annotations, 501, 'QuadrupedLeg')

# Less readable
instances = [a for a in annotations if a['image_id']==501 and a['category_id']==7]
```

## 🔧 Utility Functions

See `example_retrieve_instances.py` for complete implementations:

- `get_instances_by_category()` - Get instances for one category
- `get_all_instances_for_image()` - Get all categories for one image
- `build_instance_index()` - Build fast lookup index
- `decode_rle_mask()` - Convert RLE to binary mask
- `experiment_template()` - Complete workflow template

## 📊 Performance Comparison

| Method | Time Complexity | Use Case |
|--------|----------------|----------|
| Linear scan | O(N) per query | One-off queries |
| With index | O(1) per query | Training loops, batch processing |
| Pre-sorted | O(N log N) once | Consistent ordering needed |

For experiments processing 1000s of images, use the indexed approach!

## 🎓 Example Output

```
Image 501 - QuadrupedLeg:
Found 4 instances

  Instance 0:
    Annotation ID: 15432
    BBox: [123.0, 98.0, 45.0, 62.0]
    Area: 2852
    Mask shape: (375, 500)

  Instance 1:
    Annotation ID: 15433
    BBox: [234.0, 102.0, 38.0, 54.0]
    Area: 1852
    Mask shape: (375, 500)
```

This structure makes it easy to:
- ✅ Iterate through all instances of a category
- ✅ Track which instance is which
- ✅ Maintain consistent ordering
- ✅ Quickly retrieve relevant annotations
- ✅ Debug and visualize specific instances
