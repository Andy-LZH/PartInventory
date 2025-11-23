# Creating Annotation-Only Archives for CVAT

## When to Use `--annotations-only`

Use this flag when:
- ✅ Images already exist in CVAT
- ✅ You want to avoid "duplicate key" errors
- ✅ You only need to upload/update annotations
- ✅ You want to skip image downloads

---

## Quick Usage

### Create annotations for all splits
```bash
python create_archive_dataset.py coco_exports/QuadrupedFoot_coco.json --annotations-only --zip
```

**Output:**
```
archive_datasets/QuadrupedFoot_archive/
├── annotations/
│   ├── QuadrupedFoot_train.json
│   ├── QuadrupedFoot_val.json
│   └── QuadrupedFoot_test.json
└── dataset_info.txt
```

---

## Upload to CVAT

### Option 1: CVAT Web UI
1. Open your CVAT task
2. Click **"Upload annotations"**
3. Select format: **"COCO 1.0"**
4. Upload the JSON file (e.g., `QuadrupedFoot_train.json`)
5. Click **"Submit"**

### Option 2: CVAT API
```python
import requests
from requests.auth import HTTPBasicAuth

cvat_url = "http://your-cvat-url"
task_id = 1234
annotation_file = "archive_datasets/QuadrupedFoot_archive/annotations/QuadrupedFoot_train.json"

with open(annotation_file, 'rb') as f:
    response = requests.put(
        f"{cvat_url}/api/tasks/{task_id}/annotations",
        params={"format": "COCO 1.0"},
        files={"annotation_file": f},
        auth=HTTPBasicAuth("username", "password")
    )

if response.status_code in [201, 202]:
    print("✅ Annotations uploaded!")
else:
    print(f"❌ Error: {response.text}")
```

---

## Examples

### All categories in a directory
```bash
python create_archive_dataset.py --all-coco coco_exports/ --annotations-only --zip
```

### Single category
```bash
python create_archive_dataset.py coco_exports/BipedArm_coco.json --annotations-only --zip
```

### Custom output directory
```bash
python create_archive_dataset.py \
  coco_exports/QuadrupedFoot_coco.json \
  --annotations-only \
  --output-dir ./cvat_annotations \
  --zip
```

---

## Important Notes

1. **File Names:** The annotation JSON files reference images with paths like `train/image.jpg`, `val/image.jpg`
2. **Compatibility:** Works with CVAT's "COCO 1.0" format
3. **No Images:** No images are downloaded - only annotation JSON files are created
4. **Existing Images:** Images must already exist in CVAT with matching filenames

---

## Troubleshooting

### Error: "duplicate key value violates unique constraint"
**Solution:** Use `--annotations-only` flag - images already exist in CVAT

### Error: "Images not found"
**Problem:** Filenames in annotations don't match images in CVAT
**Solution:** Ensure images were uploaded to CVAT with same filenames as in the COCO JSON

### Need to separate splits?
Currently, `--annotations-only` creates all splits in one archive. If you need individual split files, you can extract them from the `annotations/` folder.

---

## File Format

The generated annotation files follow COCO format:
```json
{
  "info": {...},
  "licenses": [...],
  "categories": [...],
  "images": [
    {
      "id": 1,
      "file_name": "train/image001.jpg",
      "width": 640,
      "height": 480
    }
  ],
  "annotations": [...]
}
```

Image paths use format: `{split}/{filename}` (e.g., `train/n02356798_5587.JPEG`)
