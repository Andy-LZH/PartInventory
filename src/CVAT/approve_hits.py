#!/usr/bin/env python3
"""
Simple script to view, approve, or reject MTurk HITs.
Usage:
    python approve_hits.py view mturk_hits/QuadrupedFoot_train_123.json
    python approve_hits.py approve mturk_hits/QuadrupedFoot_train_123.json
    python approve_hits.py reject mturk_hits/QuadrupedFoot_train_123.json
"""

import json
import sys
import boto3
import xml.etree.ElementTree as ET


ENVIRONMENTS = {
    "live": "https://mturk-requester.us-east-1.amazonaws.com",
    "sandbox": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
}


def parse_answer_xml(answer_xml):
    """
    Parse MTurk answer XML and extract cvat_job_id and comments.

    Args:
        answer_xml: XML string from MTurk assignment answer

    Returns:
        dict with 'cvat_job_id' and 'comments' keys
    """
    try:
        root = ET.fromstring(answer_xml)

        # Define namespace
        namespace = {'ns': 'http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd'}

        result = {
            'cvat_job_id': None,
            'comments': None
        }

        # Find all Answer elements
        for answer in root.findall('ns:Answer', namespace):
            question_id = answer.find('ns:QuestionIdentifier', namespace)
            free_text = answer.find('ns:FreeText', namespace)

            if question_id is not None and free_text is not None:
                key = question_id.text
                value = free_text.text

                if key == 'cvat_job_id':
                    result['cvat_job_id'] = value
                elif key == 'comments':
                    result['comments'] = value

        return result

    except Exception as e:
        print(f"  Error parsing XML: {e}")
        return {'cvat_job_id': None, 'comments': None}


def get_mturk_client(environment):
    """Create MTurk client."""
    return boto3.client(
        "mturk",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name="us-east-1",
        endpoint_url=ENVIRONMENTS[environment],
    )


def view(json_file):
    """View HIT details and assignments."""
    with open(json_file, 'r') as f:
        hit_data = json.load(f)

    print("\n" + "="*60)
    print("HIT INFORMATION")
    print("="*60)
    print(f"Category: {hit_data['category']}")
    print(f"HIT ID: {hit_data['mturk_info']['hit_id']}")
    print(f"Environment: {hit_data['mturk_info']['environment']}")
    # print(f"Secret Token: {hit_data['secret_token']}")
    print(f"CVAT URL: {hit_data['cvat_url']}")
    print(f"Created: {hit_data.get('created', 'N/A')}")

    # Get HIT details from MTurk API to show reward and other info
    mturk = get_mturk_client(hit_data['mturk_info']['environment'])
    try:
        hit_response = mturk.get_hit(HITId=hit_data['mturk_info']['hit_id'])
        hit = hit_response['HIT']
        print(f"\nHIT Details from MTurk:")
        print(f"  Title: {hit['Title']}")
        print(f"  Reward: ${hit['Reward']}")
        print(f"  Max Assignments: {hit['MaxAssignments']}")
        print(f"  Status: {hit['HITStatus']}")
        print(f"  Created: {hit.get('CreationTime', 'N/A')}")
        print(f"  Expiration: {hit.get('Expiration', 'N/A')}")
        print(f"  Assignments Available: {hit['NumberOfAssignmentsAvailable']}")
        print(f"  Assignments Pending: {hit['NumberOfAssignmentsPending']}")
        print(f"  Assignments Completed: {hit['NumberOfAssignmentsCompleted']}")

        # Display qualification requirements
        qualifications = hit.get('QualificationRequirements', [])
        if qualifications:
            print(f"\n  Qualification Requirements:")
            for qual in qualifications:
                qual_type_id = qual.get('QualificationTypeId', 'Unknown')
                comparator = qual.get('Comparator', 'N/A')

                # Try to get qualification name
                try:
                    qual_info = mturk.get_qualification_type(QualificationTypeId=qual_type_id)
                    qual_name = qual_info['QualificationType']['Name']
                except:
                    qual_name = qual_type_id

                # Get values
                int_values = qual.get('IntegerValues', [])
                locale_values = qual.get('LocaleValues', [])
                required_preview = qual.get('RequiredToPreview', False)

                print(f"    • {qual_name}")
                print(f"      ID: {qual_type_id}")
                print(f"      Comparator: {comparator}")
                if int_values:
                    print(f"      Integer Values: {int_values}")
                if locale_values:
                    print(f"      Locale Values: {locale_values}")
                print(f"      Required to Preview: {required_preview}")
        else:
            print(f"\n  Qualification Requirements: None")

    except Exception as e:
        print(f"\n⚠️  Could not fetch HIT details from MTurk: {e}")

    # Get assignments
    mturk = get_mturk_client(hit_data['mturk_info']['environment'])
    try:
        response = mturk.list_assignments_for_hit(HITId=hit_data['mturk_info']['hit_id'])
        assignments = response.get('Assignments', [])

        if not assignments:
            print("\nNo assignments submitted yet.")
            return

        print("\n" + "="*60)
        print("ASSIGNMENTS")
        print("="*60)

        for i, assignment in enumerate(assignments, 1):
            print(f"\nAssignment #{i}")
            print(f"  Assignment ID: {assignment['AssignmentId']}")
            print(f"  Worker ID: {assignment['WorkerId']}")
            print(f"  Status: {assignment['AssignmentStatus']}")
            print(f"  Submit Time: {assignment.get('SubmitTime', 'N/A')}")

            # Parse answer XML
            answer = assignment.get('Answer', '')
            parsed = parse_answer_xml(answer)

            print(f"  CVAT Job ID: {parsed['cvat_job_id']}")
            print(f"  Comments: {parsed['comments'] if parsed['comments'] else '(none)'}")

            # Optionally show raw XML (commented out by default)
            # print(f"  Raw Answer: {answer}")

    except Exception as e:
        print(f"\nError getting assignments: {e}")


def approve(json_file):
    """Approve all submitted assignments for this HIT."""
    with open(json_file, 'r') as f:
        hit_data = json.load(f)

    mturk = get_mturk_client(hit_data['mturk_info']['environment'])
    hit_id = hit_data['mturk_info']['hit_id']

    print(f"\nApproving assignments for HIT: {hit_id}")

    try:
        response = mturk.list_assignments_for_hit(HITId=hit_id)
        assignments = response.get('Assignments', [])

        if not assignments:
            print("No assignments to approve.")
            return

        for assignment in assignments:
            if assignment['AssignmentStatus'] == 'Submitted':
                try:
                    mturk.approve_assignment(
                        AssignmentId=assignment['AssignmentId'],
                        RequesterFeedback="Thank you for your work!"
                    )
                    print(f"✓ Approved: {assignment['AssignmentId']}")
                except Exception as e:
                    print(f"✗ Error approving {assignment['AssignmentId']}: {e}")
            else:
                print(f"- Skipped {assignment['AssignmentId']} (status: {assignment['AssignmentStatus']})")

    except Exception as e:
        print(f"Error: {e}")


def reject(json_file):
    """Reject all submitted assignments for this HIT."""
    with open(json_file, 'r') as f:
        hit_data = json.load(f)

    mturk = get_mturk_client(hit_data['mturk_info']['environment'])
    hit_id = hit_data['mturk_info']['hit_id']

    print(f"\nRejecting assignments for HIT: {hit_id}")

    try:
        response = mturk.list_assignments_for_hit(HITId=hit_id)
        assignments = response.get('Assignments', [])

        if not assignments:
            print("No assignments to reject.")
            return

        for assignment in assignments:
            if assignment['AssignmentStatus'] == 'Submitted':
                try:
                    mturk.reject_assignment(
                        AssignmentId=assignment['AssignmentId'],
                        RequesterFeedback="Work did not meet requirements."
                    )
                    print(f"✓ Rejected: {assignment['AssignmentId']}")
                except Exception as e:
                    print(f"✗ Error rejecting {assignment['AssignmentId']}: {e}")
            else:
                print(f"- Skipped {assignment['AssignmentId']} (status: {assignment['AssignmentStatus']})")

    except Exception as e:
        print(f"Error: {e}")


def main():
    if len(sys.argv) != 3:
        print("Usage:")
        print("  python approve_hits.py view <json_file>")
        print("  python approve_hits.py approve <json_file>")
        print("  python approve_hits.py reject <json_file>")
        print("  python approve_hits.py test <xml_string>  # Test XML parsing")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "test":
        # Test mode: parse XML string directly
        xml_string = sys.argv[2]
        print("\nTesting XML Parser:")
        print("="*60)
        result = parse_answer_xml(xml_string)
        print(f"CVAT Job ID: {result['cvat_job_id']}")
        print(f"Comments: {result['comments']}")
        return

    json_file = sys.argv[2]

    if action == "view":
        view(json_file)
    elif action == "approve":
        approve(json_file)
    elif action == "reject":
        reject(json_file)
    else:
        print(f"Unknown action: {action}")
        print("Valid actions: view, approve, reject, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
