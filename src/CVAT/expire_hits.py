#!/usr/bin/env python3
"""
Script to expire MTurk HITs.
Usage:
    python expire_hits.py <json_file>
    python expire_hits.py mturk_hits/Qualification_test0_3X4Q1O9UBH5KT92GZMT679N1C1BO7D.json
"""

import json
import sys
import boto3

# MTurk credentials
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""

ENVIRONMENTS = {
    "live": "https://mturk-requester.us-east-1.amazonaws.com",
    "sandbox": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
}


def get_mturk_client(environment):
    """Create MTurk client."""
    return boto3.client(
        "mturk",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name="us-east-1",
        endpoint_url=ENVIRONMENTS[environment],
    )


def expire_hit(json_file):
    """Expire a HIT by updating its expiration to now."""
    try:
        with open(json_file, 'r') as f:
            hit_data = json.load(f)

        hit_id = hit_data['mturk_info']['hit_id']
        environment = hit_data['mturk_info']['environment']

        print(f"\n{'='*60}")
        print(f"EXPIRING HIT")
        print(f"{'='*60}")
        print(f"Category: {hit_data['category']}")
        print(f"HIT ID: {hit_id}")
        print(f"Environment: {environment}")

        # Confirm action
        response = input("\nAre you sure you want to expire this HIT? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Expiration cancelled.")
            return

        # Get MTurk client
        mturk = get_mturk_client(environment)

        # Get current HIT status
        try:
            hit_response = mturk.get_hit(HITId=hit_id)
            hit = hit_response['HIT']
            print(f"\nCurrent HIT Status: {hit['HITStatus']}")
            print(f"Assignments Available: {hit['NumberOfAssignmentsAvailable']}")
            print(f"Assignments Pending: {hit['NumberOfAssignmentsPending']}")
            print(f"Assignments Completed: {hit['NumberOfAssignmentsCompleted']}")
        except Exception as e:
            print(f"⚠️  Could not fetch HIT details: {e}")

        # Expire the HIT
        try:
            mturk.update_expiration_for_hit(
                HITId=hit_id,
                ExpireAt=0  # Expire immediately
            )
            print(f"\n✅ HIT has been expired successfully!")
            print(f"   HIT ID: {hit_id}")
            print(f"\nNote: The HIT is now expired and will no longer be available to workers.")
            print("      Existing assignments can still be submitted and reviewed.")

        except Exception as e:
            print(f"\n❌ Error expiring HIT: {e}")

    except FileNotFoundError:
        print(f"❌ File not found: {json_file}")
    except KeyError as e:
        print(f"❌ Missing required field in JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python expire_hits.py <json_file>")
        print("\nExample:")
        print("  python expire_hits.py mturk_hits/Qualification_test0_3X4Q1O9UBH5KT92GZMT679N1C1BO7D.json")
        sys.exit(1)

    json_file = sys.argv[1]
    expire_hit(json_file)


if __name__ == "__main__":
    main()
