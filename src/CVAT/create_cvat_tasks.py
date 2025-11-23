#!/usr/bin/env python3
"""
Simplified script to create MTurk HITs for existing CVAT tasks.
"""

import json
import argparse
import os
import boto3
from datetime import datetime


# HTML template for MTurk HITs with validation
HTML_TEMPLATE = """<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
<HTMLContent><![CDATA[
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
    <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h2 {{
            color: #1976d2;
            border-bottom: 2px solid #1976d2;
            padding-bottom: 10px;
        }}
        .step-box {{
            background-color: #f5f5f5;
            border-left: 4px solid #1976d2;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .step-box h3 {{
            color: #1976d2;
            margin-top: 0;
            font-size: 18px;
        }}
        .step-box p {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        .link-button {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #1976d2;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin: 5px 5px 5px 0;
        }}
        .link-button:hover {{
            background-color: #1565c0;
        }}
        input[type="text"], textarea {{
            width: 100%;
            max-width: 500px;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }}
        textarea {{
            resize: vertical;
        }}
        input[type='submit'] {{
            background-color: #1976d2;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }}
        input[type='submit']:hover {{
            background-color: #1565c0;
        }}
        .field-label {{
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 5px;
        }}
        .step-box.disabled {{
            opacity: 0.4;
            pointer-events: none;
            background-color: #e0e0e0;
            border-left: 4px solid #999;
        }}
        .step-box.disabled h3 {{
            color: #999;
        }}
        .step-box.disabled input[type='submit'] {{
            background-color: #ccc;
            cursor: not-allowed;
        }}
        .step-box.disabled textarea {{
            background-color: #f0f0f0;
        }}
    </style>
</head>
<body>
<form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
<input type='hidden' value='' name='assignmentId' id='assignmentId'/>

<h2>Split one large mask into smaller masks for each part of the object</h2>
<p><strong>Category:</strong> {CATEGORY_NAME}</p>

<div style="background-color: #e8f4f8; padding: 15px; border-radius: 4px; margin: 20px 0; line-height: 1.6;">
    <p><strong>What you'll be doing:</strong></p>
    <p>You will be working with images that already have colored segmentation masks covering parts of an object (like arms of the monkey in the example below). Your job is to separate one large mask into masks that correspond to individual parts of an object.</p>

    <div style="display: flex; gap: 20px; margin-top: 15px; flex-wrap: wrap; align-items: flex-end;">
        <div style="flex: 1; min-width: 250px; min-height: 250px; text-align: center;">
            <img src="https://spin-instance.s3.us-east-2.amazonaws.com/semantic_mask_example.png" alt="Semantic Segmentation" style="max-width: 100%; border: 2px solid #ccc; border-radius: 4px;">
            <p style="margin-top: 8px; font-size: 14px;"><strong>Before:</strong> One red mask covers both arms</p>
        </div>
        <div style="flex: 1; min-width: 250px; min-height: 250px; text-align: center;">
            <img src="https://spin-instance.s3.us-east-2.amazonaws.com/instance_mask_example.png" alt="Instance Segmentation" style="max-width: 100%; border: 2px solid #ccc; border-radius: 4px;">
            <p style="margin-top: 8px; font-size: 14px; text-align: center;"><strong>After:</strong> Left arm: blue mask; Right arm: green mask</p>
        </div>
    </div>
</div>

<!-- Step 1: Getting started -->
<div class="step-box">
    <h3>Step 1: Getting started</h3>
    <ul style="line-height: 1.8;">
        <li><strong>Step 1: Please use Google Chrome browser</strong> - This gives the best experience with our annotation tool.</li>
        <li><strong>Step 2: Log into CVAT with credentials</strong> - Use the credentials we emailed you. If you need assistance, <a href="https://youtu.be/TIvjeD5LTJw" target="_blank" style="color: #1976d2; text-decoration: underline;">watch this video</a>.</li>
    </ul>
</div>

<!-- Step 2: Accessing the task -->
<div class="step-box" id="step2">
    <h3>Step 2: Accessing the task</h3>
    <p style="margin-top: 20px; font-size: 16px; color: #888;"><em>Instruction Materials:</em></p>
    <p style="font-size: 15px;">
        <a href="https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance-Mask-Qualification.pdf" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: underline;">Tutorial document</a>
        &nbsp;|&nbsp;
        <a href="https://youtu.be/PoL43USIn1s" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: underline;">Video tutorial on CVAT and task</a>
    </p>
    <p><a href="{CVAT_URL}" target="_blank" rel="noopener noreferrer" class="link-button" id="cvatLink">Click here to access CVAT task</a></p>

</div>

<!-- Step 3: Submission (initially disabled) -->
<div class="step-box disabled" id="step3">
    <h3>Step 3: Completion</h3>

    <p><strong>Once you've completed all images on CVAT, navigate back to MTurk and click the submit button below.</strong></p>

    <div class="field-label">Comments (optional):</div>
    <textarea name="comments" id="comments" rows="4" placeholder="Feel free to share anything..."></textarea>

    <p><input type='submit' id='submitButton' value='Submit Results' /></p>
</div>

<script language='Javascript'>
turkSetAssignmentID();

// Enable Step 3 when CVAT link is clicked
document.getElementById('cvatLink').addEventListener('click', function() {{
    setTimeout(function() {{
        var step3 = document.getElementById('step3');
        step3.classList.remove('disabled');
    }}, 500); // Small delay to ensure the link opens
}});
</script>
</body>
</html>
]]></HTMLContent>
<FrameHeight>700</FrameHeight>
</HTMLQuestion>"""


def load_cvat_urls(cvat_urls_file="cvat_urls.json"):
    """Load CVAT URLs from JSON file."""
    try:
        with open(cvat_urls_file, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️  Could not load CVAT URLs from {cvat_urls_file}: {e}")
        return {}


def get_cvat_url_for_category(category_name, cvat_data):
    """Get CVAT URL for a specific category."""
    # Try exact match first
    if category_name in cvat_data:
        return cvat_data[category_name]

    # Try case-insensitive match
    for key, value in cvat_data.items():
        if key.lower() == category_name.lower():
            return value

    # Try partial match
    for key, value in cvat_data.items():
        if category_name.lower() in key.lower() or key.lower() in category_name.lower():
            return value

    return None


def get_worker_requirements(live, worker_group):
    """Get worker qualification requirements based on environments.py."""

    # Qualification IDs from environments.py
    QidDic = {}

    if live:
        if worker_group == "SPIN-Instance-Excellence0":
            requirements = [
                {
                    "QualificationTypeId": QidDic["SPIN-Instance-Excellence0"],
                    "Comparator": "EqualTo",
                    "IntegerValues": [2],
                    "RequiredToPreview": True,
                }
            ]
        elif worker_group == "SPIN-Instance-Excellence1":
            requirements = [
                {
                    "QualificationTypeId": QidDic["SPIN-Instance-Excellence1"],
                    "Comparator": "EqualTo",
                    "IntegerValues": [2],
                    "RequiredToPreview": True,
                }
            ]
        elif worker_group in QidDic.keys():
            # raise ValueError(f"Worker group '{worker_group}' not valid for live environment.")
            requirements = [
                {
                    "QualificationTypeId": QidDic[worker_group],
                    "Comparator": "EqualTo",
                    "IntegerValues": [1],
                    "RequiredToPreview": True,
                }
            ]

        else:
            raise ValueError(
                f"Unknown worker group for live environment: {worker_group}"
            )
    else:  # Sandbox
        if worker_group == "SPIN-Instance-Excellence0":
            requirements = [
                {
                    "QualificationTypeId": QidDic["SPIN-Instance-Excellence0"],
                    "Comparator": "EqualTo",
                    "IntegerValues": [2],
                    "RequiredToPreview": True,
                }
            ]
        elif worker_group == "SPIN-Instance-Excellence1":
            requirements = [
                {
                    "QualificationTypeId": QidDic["SPIN-Instance-Excellence1"],
                    "Comparator": "EqualTo",
                    "IntegerValues": [2],
                    "RequiredToPreview": True,
                }
            ]
        elif worker_group in QidDic.keys():
            requirements = []
            # requirements = [
            #     {
            #         "QualificationTypeId": QidDic[worker_group],
            #         "Comparator": "EqualTo",
            #         "IntegerValues": [1],
            #         "RequiredToPreview": True,
            #     }
            # ]

        else:
            requirements = []

    return requirements


def create_mturk_hit(
    category_name, cvat_url, live=False, worker_group="Excellence", reward=None, n_images=None
):
    """Create MTurk HIT for CVAT task using environments.py setup."""

    try:
        # Setup environments (from environments.py)
        environments = {
            "live": {
                "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
                "preview": "https://www.mturk.com/mturk/preview",
                "manage": "https://requester.mturk.com/mturk/manageHITs",
            },
            "sandbox": {
                "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
                "preview": "https://workersandbox.mturk.com/mturk/preview",
                "manage": "https://requestersandbox.mturk.com/mturk/manageHITs",
            },
        }

        mturk_environment = environments["live"] if live else environments["sandbox"]

        # Create MTurk client (using credentials from environments.py)
        mturk = boto3.client(
            "mturk",
            aws_access_key_id="",
            aws_secret_access_key="",
            region_name="us-east-1",
            endpoint_url=mturk_environment["endpoint"],
        )

        # Determine reward amount
        if reward is None:
            if live:
                if "Qualification" in category_name:
                    reward = "7.00"
                else:
                    reward = "0.30"
            else:
                reward = "0.00"
        else:
            reward = f"{float(reward):.2f}"

        print(
            f"💡 Creating MTurk HIT in {'live' if live else 'sandbox'} environment for category '{category_name}' with reward ${reward}..."
        )

        # Get worker requirements
        requirements = get_worker_requirements(live, worker_group)

        # Fill in HTML template
        html_content = HTML_TEMPLATE.format(
            CATEGORY_NAME=category_name, CVAT_URL=cvat_url
        )

        # Create HIT title with optional image count
        if n_images:
            hit_title = f"{category_name} ({n_images} images)"
        else:
            hit_title = f"Instance Segmentation Annotation - {category_name}"

        # Create HIT
        response = mturk.create_hit(
            Title=hit_title,
            Description=f"Complete instance segmentation annotations for {category_name} in CVAT",
            Keywords="computer vision, annotation, segmentation, CVAT",
            Reward=reward,
            MaxAssignments=1,
            LifetimeInSeconds=604800,  # 7 days
            AssignmentDurationInSeconds=604800,  # 7 days since this might include many images
            AutoApprovalDelayInSeconds=604800,  # Auto-approve after 7 days
            Question=html_content,
            RequesterAnnotation=f"CVAT_{category_name}",
            QualificationRequirements=requirements,
        )

        hit_id = response["HIT"]["HITId"]
        hit_group_id = response["HIT"]["HITGroupId"]
        hit_url = f"{mturk_environment['preview']}?groupId={hit_group_id}"

        # Get account balance
        try:
            balance_response = mturk.get_account_balance()
            available_balance = balance_response["AvailableBalance"]
        except Exception as e:
            print(f"⚠️  Could not retrieve account balance: {e}")
            available_balance = "N/A"

        return {
            "hit_id": hit_id,
            "hit_url": hit_url,
            "hit_group_id": hit_group_id,
            "status": "created",
            "environment": "live" if live else "sandbox",
            "worker_group": worker_group,
            "reward": reward,
            "account_balance": available_balance,
            "n_images": n_images,
        }

    except Exception as e:
        print(f"❌ Error creating MTurk HIT: {e}")
        return None


def generate_hit_summary(category_name, cvat_url, mturk_info):
    """Generate a summary of the MTurk HIT created."""

    balance_info = ""
    if mturk_info.get('account_balance') and mturk_info['account_balance'] != "N/A":
        balance_info = f"- Account Balance: ${mturk_info['account_balance']}\n"

    n_images_info = ""
    if mturk_info.get('n_images'):
        n_images_info = f"- Number of Images: {mturk_info['n_images']}\n"

    summary = f"""
🎯 MTurk HIT Summary
==================

Category: {category_name}
CVAT URL: {cvat_url}
Document (PDF): https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance-Mask-Qualification.pdf
Tutorial Video: https://youtu.be/PoL43USIn1s

MTurk Information:
- HIT ID: {mturk_info['hit_id']}
- HIT Group ID: {mturk_info['hit_group_id']}
- HIT URL: {mturk_info['hit_url']}
- Environment: {mturk_info['environment']}
- Worker Group: {mturk_info['worker_group']}
- Reward: ${mturk_info['reward']}
{n_images_info}{balance_info}- Status: {mturk_info['status']}

Next Steps:
1. Workers will review the document and tutorial video
2. Workers will access CVAT task via: {cvat_url}
3. Workers must submit their CVAT Job ID
4. Review submissions in MTurk console
5. Approve valid work based on CVAT Job ID verification
"""

    return summary


def save_hit_info(category_name, cvat_url, mturk_info, output_dir="mturk_hits"):
    """Save MTurk HIT information to file."""

    os.makedirs(output_dir, exist_ok=True)

    hit_info = {
        "category": category_name,
        "cvat_url": cvat_url,
        "pdf_url": "https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance-Mask-Qualification.pdf",
        "youtube_url": "https://youtu.be/PoL43USIn1s",
        "mturk_info": mturk_info,
        "created": datetime.now().isoformat(),
        "status": "active",
    }

    filename = f"{category_name}_{mturk_info['hit_id']}.json"
    config_file = os.path.join(output_dir, filename)

    try:
        with open(config_file, "w") as f:
            json.dump(hit_info, f, indent=2)

        print(f"💾 Saved HIT information: {config_file}")
        return config_file

    except Exception as e:
        print(f"❌ Error saving HIT information: {e}")
        return None


def create_html_hit_file(category_name, cvat_url, output_dir="cvat_tasks"):
    """Create standalone HTML file for MTurk HIT."""

    os.makedirs(output_dir, exist_ok=True)

    html_content = HTML_TEMPLATE.format(CATEGORY_NAME=category_name, CVAT_URL=cvat_url)

    html_file = os.path.join(output_dir, f"{category_name}_mturk_hit.html")

    try:
        with open(html_file, "w") as f:
            f.write(html_content)

        print(f"🌐 Saved MTurk HTML file: {html_file}")
        return html_file

    except Exception as e:
        print(f"❌ Error saving HTML file: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create MTurk HITs for existing CVAT tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates MTurk HITs for existing CVAT tasks using URLs from a JSON file.

Examples:
  python create_cvat_tasks.py --category "QuadrupedFoot" --split "train"
  python create_cvat_tasks.py --category "QuadrupedFoot" --split "test" --cvat-urls-file "my_cvat_urls.json"
  python create_cvat_tasks.py --category "QuadrupedFoot" --split "val" --live --worker-group "Excellence"
  python create_cvat_tasks.py --category "Qualification" --split "test" --live --reward 7.00
  python create_cvat_tasks.py --category "QuadrupedFoot" --split "train" --live --reward 0.50
  python create_cvat_tasks.py --category "QuadrupedFoot" --split "train" --live --n-images 50
  python create_cvat_tasks.py --list-cvat-urls
        """,
    )

    parser.add_argument(
        "--category",
        "-c",
        type=str,
        required=True,
        help="Category name to create HIT for (e.g., 'QuadrupedFoot')",
    )

    parser.add_argument(
        "--split",
        "-s",
        type=str,
        required=True,
        help="Data split to use (train, test, val)",
    )

    parser.add_argument(
        "--cvat-urls-file",
        type=str,
        default="cvat_urls.json",
        help="JSON file containing CVAT URLs for categories (default: cvat_urls.json)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="mturk_hits",
        help="Output directory for HIT information (default: mturk_hits)",
    )

    parser.add_argument(
        "--list-cvat-urls",
        action="store_true",
        help="List all available CVAT URLs and exit",
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live MTurk environment (default: sandbox)",
    )

    parser.add_argument(
        "--worker-group",
        type=str,
        default="Excellence",
        help="Worker group for qualification requirements (default: Excellence)",
    )

    parser.add_argument(
        "--reward",
        "-r",
        type=float,
        default=None,
        help="Reward amount in USD (default: auto-determined based on category and environment)",
    )

    parser.add_argument(
        "--n-images",
        "-n",
        type=int,
        default=None,
        help="Number of images in the task (displayed in HIT title)",
    )

    parser.add_argument(
        "--create-html-file",
        action="store_true",
        help="Create standalone HTML file for MTurk HIT",
    )

    args = parser.parse_args()

    # Load CVAT URLs
    cvat_data = load_cvat_urls(args.cvat_urls_file)

    if args.list_cvat_urls:
        print("📋 Available CVAT URLs:")
        if cvat_data:
            for category, url in cvat_data.items():
                print(f"   • {category}: {url}")
        else:
            print(f"   No CVAT URLs found in {args.cvat_urls_file}")
        return

    if not cvat_data:
        print(f"❌ No CVAT URLs loaded from {args.cvat_urls_file}")
        return

    # Get CVAT URL for the specified category and split
    category_with_split = f"{args.category}_{args.split}"
    cvat_url = get_cvat_url_for_category(category_with_split, cvat_data)

    if not cvat_url:
        print(f"❌ No CVAT URL found for category: {category_with_split}")
        print("Available categories:")
        for category in cvat_data.keys():
            print(f"   • {category}")
        return

    print(f"🚀 Creating MTurk HIT for category: {args.category} ({args.split} split)")
    print(f"📋 CVAT URL: {cvat_url}")
    print(
        f"📄 PDF Document: https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance-Mask-Qualification.pdf"
    )
    print(f"🎥 Tutorial Video: https://youtu.be/PoL43USIn1s")

    # Create MTurk HIT
    print(f"🔄 Creating MTurk HIT...")
    mturk_info = create_mturk_hit(
        category_name=f"{args.category}_{args.split}",
        cvat_url=cvat_url,
        live=args.live,
        worker_group=args.worker_group,
        reward=args.reward,
        n_images=args.n_images,
    )

    if not mturk_info:
        print("❌ Failed to create MTurk HIT")
        return

    print(f"✅ Created MTurk HIT: {mturk_info['hit_id']}")

    # Save HIT information
    config_file = save_hit_info(
        f"{args.category}_{args.split}", cvat_url, mturk_info, args.output_dir
    )

    # Create HTML file if requested
    html_file = None
    if args.create_html_file:
        html_file = create_html_hit_file(
            f"{args.category}_{args.split}", cvat_url, args.output_dir
        )

    # Generate and display summary
    summary = generate_hit_summary(
        f"{args.category}_{args.split}", cvat_url, mturk_info
    )
    print(summary)

    # Final summary
    print(f"\n🎉 Successfully created MTurk HIT:")
    print(f"   • Category: {args.category} ({args.split} split)")
    print(f"   • HIT ID: {mturk_info['hit_id']}")
    print(f"   • HIT URL: {mturk_info['hit_url']}")
    print(
        f"   • PDF Document: https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance-Mask-Qualification.pdf"
    )
    print(f"   • Tutorial Video: https://youtu.be/PoL43USIn1s")
    print(f"   • Environment: {mturk_info['environment']}")
    print(f"   • Worker Group: {mturk_info['worker_group']}")
    print(f"   • Reward: ${mturk_info['reward']}")
    if mturk_info.get('n_images'):
        print(f"   • Number of Images: {mturk_info['n_images']}")
    if mturk_info.get('account_balance') and mturk_info['account_balance'] != "N/A":
        print(f"   • Account Balance: ${mturk_info['account_balance']}")
    if config_file:
        print(f"   • Config File: {config_file}")
    if html_file:
        print(f"   • HTML File: {html_file}")

    print(f"\n🔗 Next steps:")
    print(f"   1. Workers will review the document and tutorial")
    print(f"   2. Workers will access CVAT at: {cvat_url}")
    print(f"   3. Workers must submit their CVAT Job ID")
    print(f"   4. Monitor submissions in MTurk console: {mturk_info['hit_url']}")
    print(f"   5. Approve valid work based on CVAT Job ID verification")


if __name__ == "__main__":
    main()
