#!/usr/bin/env python3
import argparse, json, re, os
import boto3
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
from datetime import datetime

# Flat file pattern: group_0_3IXQG4....json  -> group idx = 0
GROUP_RE = re.compile(r"group_(\d+)_.*\.json$")
SUPERCATEGORY_MAPPINGS = {
    "Quadruped": [
        "QuadrupedHead",
        "QuadrupedBody",
        "QuadrupedFoot",
        "QuadrupedTail",
        "QuadrupedLeg",
    ],
    "Biped": ["BipedHead", "BipedBody", "BipedArm", "BipedLeg", "BipedTail"],
    "Fish": ["FishHead", "FishBody", "FishFin", "FishTail"],
    "Bird": ["BirdHead", "BirdBody", "BirdWing", "BirdFoot", "BirdTail"],
    "Snake": ["SnakeHead", "SnakeBody"],
    "Reptile": ["ReptileHead", "ReptileBody", "ReptileFoot", "ReptileTail"],
    "Car": ["CarBody", "CarTire", "CarSideMirror", "CarTier"],
    "Bicycle": [
        "BicycleBody",
        "BicycleHead",
        "BicycleSeat",
        "BicycleTire",
        "BicycleTier",
    ],
    "Boat": ["BoatBody", "BoatSail"],
    "Aeroplane": [
        "AeroplaneHead",
        "AeroplaneBody",
        "AeroplaneEngine",
        "AeroplaneWing",
        "AeroplaneTail",
    ],
    "Bottle": ["BottleMouth", "BottleBody"],
}


def list_all_keys(s3, bucket, prefix):
    """List all keys under prefix (handles >1k via paginator)."""
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def find_groups_from_keys(keys, base_prefix):
    """Parse group indices from filenames like group_{idx}_{aid}.json."""
    groups = set()
    for k in keys:
        if not k.startswith(base_prefix):
            continue
        fname = k[len(base_prefix) :]  # strip base
        m = GROUP_RE.match(fname)
        if m:
            groups.add(int(m.group(1)))
    return sorted(groups)


def list_group_submission_keys(keys, base_prefix, group_idx):
    """Return all submission keys for a specific group idx."""
    prefix = f"{base_prefix}group_{group_idx}_"
    return sorted(
        [
            k
            for k in keys
            if k.startswith(prefix)
            and k.endswith(".json")
            and not k.endswith("_merged.json")
        ]
    )


def read_json(s3, bucket, key):
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    return json.loads(body)


def extract_issue_texts(submission):
    """Extract issue texts from submission annotations if available"""
    issue_texts = {}
    annotations = submission.get("annotations", [])

    for i, ann in enumerate(annotations):
        if ann.get("result") == -1 and "issue_text" in ann:
            issue_texts[str(i)] = ann["issue_text"]

    return issue_texts
