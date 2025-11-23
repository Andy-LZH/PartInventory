from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from pycocotools import mask as maskUtils
import numpy as np
import matplotlib
from pydantic import BaseModel

matplotlib.use("Agg")  # Use a non-interactive backend for matplotlib
import matplotlib.pyplot as plt
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://andy-lzh.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = [
    "QualificationTest_parts",
    "QualificationTest_subparts",
    "agreeTest",
    "main",
    "spin_val_parts",
    "spin_val_subparts",
    "spin_train_parts",
    "spin_train_subparts",
    "spin_test_subparts",
    "spin_test_parts"
]

categories = [
    "QuadrupedHead",
    "QuadrupedBody",
    "QuadrupedLeg",
    "QuadrupedTail",
    "BipedHead",
    "BipedBody",
    "BipedArm",
    "BipedLeg",
    "BipedTail",
    "FishHead",
    "FishBody",
    "FishFin",
    "FishTail",
    "BirdHead",
    "BirdBody",
    "BirdWing",
    "BirdFoot",
    "BirdTail",
    "SnakeHead",
    "SnakeBody",
    "ReptileHead",
    "ReptileBody",
    "ReptileFoot",
    "ReptileTail",
    "CarBody",
    "CarTire",
    "CarSideMirror",
    "BicycleBody",
    "BicycleHead",
    "BicycleSeat",
    "BicycleTire",
    "BoatBody",
    "BoatSail",
    "AeroplaneHead",
    "AeroplaneBody",
    "AeroplaneEngine",
    "AeroplaneWing",
    "AeroplaneTail",
    "BottleMouth",
    "BottleBody",
]


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/tasks/")
def get_task_ids(task: str, category: str, groupIndex: int, sandbox: bool, review: bool, assignmentId: str = Query(...)):
    try:
        print(task)
        if task not in tasks:
            raise HTTPException(status_code=400, detail="Invalid task specified")

        environment = "sandbox" if sandbox else "live"
        if review:
            url = f"https://spin-instance.s3.us-east-2.amazonaws.com/HITs/{category}/{task}/{environment}/group_{groupIndex}_{assignmentId}.json"
        else:
            url = f"https://spin-instance.s3.us-east-2.amazonaws.com/HITs/{task}/{category}/{environment}.json"

        try:
            response = requests.get(url)
            print(f"Fetching HIT file from: {url}")
            response.raise_for_status()  # raise HTTPError if status is 4xx/5xx
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch HIT file: {e}")

        if not review and (groupIndex < 0 or groupIndex >= len(data)):
            raise HTTPException(status_code=404, detail="Group index out of range")

        if not review:
            group_data = data[groupIndex]
        else:
            group_data = data
            if not group_data:
                raise HTTPException(
                    status_code=404, detail="No data found for the specified group index"
            )

        task_ids = group_data["entry_id"]
        annotations = group_data.get("annotations", [])
        answers = []

        for item in annotations:
            if "result" in item:
                print(item["result"])
                answers.append(item["result"])
            else:
                answers.append(None)
        return JSONResponse(
            content={
                "entry_ids": task_ids,
                "answers": answers,  # Include answers if available
            }
        )
    except Exception as e:
        print(f"Error occurred while fetching task IDs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/image/")
def get_image(task: str, category: str, entry_id: int = Query(...)):
    if task not in tasks:
        raise HTTPException(status_code=400, detail="Invalid task specified")
    if task == "QualificationTest_parts":
        task = "spin_val_parts"  # Use spin_val_parts for qualification tasks
    elif task == "QualificationTest_subparts":
        task = "spin_val_subparts"

    if task in ["main", "agreeTest"]:
        with open(f"data/spin-instance/spin_{category}_{task}.json", "r") as f:
            spin_val_parts = json.load(f)

        annotations = spin_val_parts

        image_name = annotations[entry_id]["image_file_name"] + ".JPEG"
        attribute = annotations[entry_id]["split"]
        full_path = os.path.join(
            f"https://spin-instance.s3.us-east-2.amazonaws.com/{attribute}", image_name
        )
        # check if the url exists
        response = requests.head(full_path)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Image file not found")

        return JSONResponse(content={"image_url": full_path})
    else:
        with open(f"data/{task}.json", "r") as f:
            spin_val_parts = json.load(f)

            images = spin_val_parts["images"]
            annotations = spin_val_parts["annotations"]

            image_id = annotations[entry_id]["image_id"]
            if image_id < 0 or image_id >= len(images):
                raise HTTPException(status_code=404, detail="Image not found")
            image_name = images[image_id]["file_name"] + ".JPEG"
            attribute = task.split("_")[1]
            full_path = os.path.join(
                f"https://spin-instance.s3.us-east-2.amazonaws.com/{attribute}", image_name
            )
            # check if the url exists
            response = requests.head(full_path)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Image file not found")

            return JSONResponse(content={"image_url": full_path})


@app.get("/api/mask/")
def get_mask(task: str, category: str, entry_id: int = Query(...)):
    if task not in tasks:
        raise HTTPException(status_code=400, detail="Invalid task specified")
    if task == "QualificationTest_parts":
        task = "spin_val_parts"  # Use spin_val_parts for qualification tasks
    elif task == "QualificationTest_subparts":
        task = "spin_val_subparts"

    if task in ["main", "agreeTest"]:
        with open(f"data/spin-instance/spin_{category}_{task}.json", "r") as f:
            spin_val_parts = json.load(f)
            annotations = spin_val_parts

            rle = annotations[entry_id]["segmentation"]
            bbox = annotations[entry_id]["bbox"]
            mask = maskUtils.decode(rle)  # shape: (H, W)

            # Centroid from bbox
            x, y, w, h = bbox
            cx = x + w / 2
            cy = y + h / 2

            # Create RGBA image: red mask on transparent background
            rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.float32)
            rgba[..., 0] = mask  # Red channel
            rgba[..., 3] = mask * 0.5  # Alpha channel (transparency)

            # Save the mask + centroid as PNG
            os.makedirs("images/temp/task", exist_ok=True)
            filename = f"images/temp/task/mask_{entry_id}.png"

            plt.figure(figsize=(6, 6))
            plt.imshow(rgba)
            # plt.scatter([cx], [cy], c="blue", s=30, marker="o")  # blue point
            plt.axis("off")
            plt.tight_layout(pad=0)
            plt.savefig(filename, bbox_inches="tight", pad_inches=0)
            plt.close()

            if not os.path.exists(filename):
                raise HTTPException(status_code=404, detail="Mask file not found")
            return FileResponse(filename)
    else:
        with open(f"data/{task}.json", "r") as f:
            spin_val_parts = json.load(f)
            annotations = spin_val_parts["annotations"]

            rle = annotations[entry_id]["segmentation"]
            bbox = annotations[entry_id]["bbox"]
            mask = maskUtils.decode(rle)  # shape: (H, W)

            # Centroid from bbox
            x, y, w, h = bbox
            cx = x + w / 2
            cy = y + h / 2

            # Create RGBA image: red mask on transparent background
            rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.float32)
            rgba[..., 0] = mask  # Red channel
            rgba[..., 3] = mask * 0.5  # Alpha channel (transparency)

            # Save the mask + centroid as PNG
            os.makedirs("images/temp/task", exist_ok=True)
            filename = f"images/temp/task/mask_{entry_id}.png"

            plt.figure(figsize=(6, 6))
            plt.imshow(rgba)
            # plt.scatter([cx], [cy], c="blue", s=30, marker="o")  # blue point
            plt.axis("off")
            plt.tight_layout(pad=0)
            plt.savefig(filename, bbox_inches="tight", pad_inches=0)
            plt.close()

            if not os.path.exists(filename):
                raise HTTPException(status_code=404, detail="Mask file not found")

            return FileResponse(filename)


@app.get("/api/category/")
def get_category(task: str, entry_id: int = Query(...)):
    if task not in tasks:
        raise HTTPException(status_code=400, detail="Invalid task specified")
    if task == "QualificationTest_parts":
        task = "spin_val_parts"  # Use spin_val_parts for qualification tasks
    elif task == "QualificationTest_subparts":
        task = "spin_val_subparts"
    with open(f"data/{task}.json", "r") as f:
        spin_val_parts = json.load(f)
        categories = spin_val_parts["categories"]
        annotations = spin_val_parts["annotations"]

        category_id = annotations[entry_id]["category_id"]

        if "subparts" in task:
            category_id -= 1

        if category_id < 0 or category_id >= len(categories):
            raise HTTPException(status_code=404, detail="Category not found")

        if category_id < 0 or category_id >= len(categories):
            raise HTTPException(status_code=404, detail="Category not found")
        # note that if tasks include subparts, then category id is not zero-started instead it starts from 1

        return JSONResponse(content=categories[category_id])
