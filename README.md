# PartInventory: Navigating Semantic and Instance Segmentation

<div align="center">

![Status](https://img.shields.io/badge/Status-Under_Construction-orange)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/python-3670A0?logo=python&logoColor=ffdd54)
![React](https://img.shields.io/badge/react-%2320232a.svg?logo=react&logoColor=%2361DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
[![Hugging Face Datasets](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Datasets-F57F25)](https://huggingface.co/datasets/Andy-LZH/PartInventory)

</div>

**PartInventory** is a full-stack annotation and dataset creation system designed to navigate the transition from semantic masks to high-quality, instance-level part annotations. Specifically, this dataset provides **refined instance-level annotations** for **PartImageNet**, building upon the semantic segmentation masks from **SPIN**.

The resulting dataset is available on Hugging Face: [🤗 PartInventory Dataset](https://huggingface.co/datasets/Andy-LZH/PartInventory).

> **Disclaimer**: This project is a technical demonstration and portfolio piece. It is not intended for academic publication as original research. All credit for the underlying datasets and methodologies belongs to the respective authors of PartImageNet and SPIN.

The platform integrates CVAT-based task management with a custom crowdsourcing pipeline on MTurk, enabling efficient identification of single vs. multiple part instances and high-fidelity instance splits.

The system supports all stages of benchmark creation—from preparing COCO-style data, distributing tasks to workers, collecting classifications, exporting CVAT instance masks, and generating analytics—ensuring scalable, consistent, and reproducible part-level datasets.

---

## 🚀 Key Features

### 1. Crowdsourcing Annotation Interface
- **Interactive UI**: A modern, responsive web application built with **React**, **Vite**, and **Chakra UI**.
- **Visual Feedback**: Real-time visualization of segmentation masks overlaid on original images.
- **Quality Control**: Integrated "Gold Standard" qualification tests and agreement checks to ensure high-quality worker data.
- **MTurk Integration**: Seamless submission logic compatible with Amazon Mechanical Turk's external question API.

### 2. Robust Backend API
- **FastAPI Powered**: High-performance Python backend handling task distribution, image serving, and data validation.
- **Cloud Native**: Fully integrated with **AWS S3** for scalable storage of images, masks, and task metadata.
- **Dynamic Mask Generation**: On-the-fly generation of visualization masks from RLE (Run-Length Encoding) data using `pycocotools`.

### 3. Data Processing Pipeline
- **CVAT Integration**: Tools to synchronize data with Computer Vision Annotation Tool (CVAT), including automated task creation and annotation export.
- **COCO Format Support**: Full support for the COCO dataset format, including conversion, merging, and splitting utilities.
- **Analytics Engine**: Comprehensive statistical analysis scripts (`dataset_statistics.py`) to generate distribution metrics, confusion matrices, and instance counts similar to academic dataset papers (CVPR/ECCV).

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 18 (TypeScript)
- **Build Tool**: Vite
- **UI Library**: Chakra UI
- **State Management**: React Hooks

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **Data Processing**: NumPy, Pandas, PyCOCOTools, Matplotlib
- **Cloud Services**: AWS Boto3 (S3, MTurk)
- **Server**: Uvicorn

### Data & DevOps
- **Annotation Format**: COCO JSON
- **Version Control**: Git (with Pre-commit hooks for quality & security)
- **Deployment**: Heroku / Docker ready (`Procfile` included)

---

## 📂 Project Structure

```bash
PartInventory/
├── src/
│   ├── Classification/
│   │   ├── backend/          # FastAPI server & data processing
│   │   │   ├── main.py       # API Entry point
│   │   │   ├── data/         # Analytics scripts & local data
│   │   │   └── MturkUtility.ipynb # MTurk management notebooks
│   │   └── frontend/         # React annotation interface
│   │       ├── src/          # UI Components & Logic
│   │       └── vite.config.ts
│   └── CVAT/                 # CVAT integration tools
│       ├── create_archive_dataset.py # COCO export utilities
│       └── merged/           # Dataset merging logic
├── dataset_statistics.py     # Statistical analysis generator
├── generate_cvpr_figures.py  # Visualization for papers
└── utils/                    # Helper scripts
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v16+)
- Python (v3.9+)
- AWS Credentials (if accessing S3/MTurk features)

### 1. Backend Setup

Navigate to the backend directory and install dependencies:

```bash
cd src/Classification/backend
pip install -r requirements.txt
```

Run the development server:

```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

Navigate to the frontend directory and install dependencies:

```bash
cd src/Classification/frontend
npm install
```

Start the development server:

```bash
npm run dev
```
The UI will be available at `http://localhost:5173`.

---

## 📊 Data Pipeline Workflow

1.  **Ingestion**: Images and initial segmentations are managed in CVAT.
2.  **Export**: Use `src/CVAT/create_archive_dataset.py` to export annotations in COCO format.
    ```bash
    python src/CVAT/create_archive_dataset.py --annotations-only coco_exports/MyCategory.json
    ```
3.  **Crowdsourcing**: The backend serves these parts to the Frontend UI for instance counting (One vs. Many).
4.  **Analysis**: Run `dataset_statistics.py` to generate a comprehensive report on the dataset distribution.
    ```bash
    python dataset_statistics.py
    ```

---

## 📈 Analytics & Visualization

The project includes sophisticated tools for analyzing dataset health:

*   **`dataset_statistics.py`**: Generates LaTeX-ready tables of dataset statistics (Images, Annotations, Categories).
*   **`generate_cvpr_figures.py`**: Creates publication-quality charts showing category distributions and instance counts.

---

## 🛡️ Quality Assurance

This repository uses **pre-commit** hooks to ensure code quality and security:
*   **Gitleaks**: Scans for accidental commit of AWS keys or secrets.
*   **Trailing Whitespace / End-of-file**: Ensures consistent formatting.
*   **Large File Check**: Prevents committing massive binary files.

To install hooks locally:
```bash
pre-commit install
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📚 Citation

If you use this dataset, please cite the original PartImageNet paper and the SPIN paper:

```bibtex
@article{he2021partimagenet,
  title={PartImageNet: A Large, High-Quality Dataset of Parts},
  author={He, Ju and Yang, Shuo and Yang, Shaokang and Kortylewski, Adam and Yuan, Xiaoding and Chen, Jie-Neng and Liu, Shuai and Yang, Cheng and Yuille, Alan},
  journal={arXiv preprint arXiv:2112.00933},
  year={2021}
}

% Please add the SPIN paper citation here
```
