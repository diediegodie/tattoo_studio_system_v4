#!/usr/bin/env python3
"""
Debug script to analyze Jotform API response structure.

This script helps you understand the exact structure of your client's
Jotform form and identify which fields contain the client name.

Usage:
    python scripts/debug_jotform_structure.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.jotform_service import JotFormService


def analyze_jotform_structure():
    """Fetch and analyze Jotform submissions to understand field structure."""

    # Get credentials from environment
    api_key = os.getenv("JOTFORM_API_KEY")
    form_id = os.getenv("JOTFORM_FORM_ID")

    if not api_key or not form_id:
        print(
            "ERROR: JOTFORM_API_KEY and JOTFORM_FORM_ID must be set in environment variables"
        )
        print("\nSet them in your .env file or export them:")
        print("  export JOTFORM_API_KEY='your-api-key'")
        print("  export JOTFORM_FORM_ID='your-form-id'")
        sys.exit(1)

    print("=" * 80)
    print("JOTFORM FORM STRUCTURE ANALYZER")
    print("=" * 80)
    print(f"\nAPI Key: {api_key[:10]}... (hidden)")
    print(f"Form ID: {form_id}")
    print("\nFetching submissions...\n")

    try:
        # Create service
        service = JotFormService(api_key, form_id)

        # Fetch submissions
        submissions = service.fetch_submissions()

        if not submissions:
            print("⚠️  No submissions found in this form.")
            print("    Make sure the form has at least one submission.")
            return

        print(f"✓ Found {len(submissions)} submissions\n")

        # Analyze first submission in detail
        first_submission = submissions[0]
        print("=" * 80)
        print("ANALYZING FIRST SUBMISSION")
        print("=" * 80)
        print(f"\nSubmission ID: {first_submission.get('id')}")
        print(f"Status: {first_submission.get('status')}")

        # Analyze answers
        answers = first_submission.get("answers", {})
        print(f"\nTotal fields: {len(answers)}\n")

        print("-" * 80)
        print("FIELD STRUCTURE:")
        print("-" * 80)

        for key, answer in answers.items():
            field_type = answer.get("type", "unknown")
            label = answer.get("text", "No label")
            answer_value = answer.get("answer")

            print(f"\n📋 Field ID: {key}")
            print(f"   Type: {field_type}")
            print(f"   Label: {label}")
            print(f"   Answer Type: {type(answer_value).__name__}")

            # Show answer preview
            if isinstance(answer_value, dict):
                print(
                    f"   Answer (dict): {json.dumps(answer_value, indent=6, ensure_ascii=False)}"
                )
            else:
                answer_preview = str(answer_value)[:100]
                if len(str(answer_value)) > 100:
                    answer_preview += "..."
                print(f"   Answer: {answer_preview}")

        print("\n" + "=" * 80)
        print("NAME EXTRACTION TEST")
        print("=" * 80)

        # Test name extraction
        extracted_name = service.parse_client_name(first_submission)
        print(f"\n✓ Extracted Name: '{extracted_name}'")

        # Show which field was used
        print("\n🔍 Name Detection Analysis:")

        # Check for control_fullname
        has_fullname = False
        for key, answer in answers.items():
            if answer.get("type") == "control_fullname":
                has_fullname = True
                print(f"\n   ✓ Found control_fullname field (ID: {key})")
                print(f"     Label: {answer.get('text')}")
                print(f"     This is the PREFERRED field for names")
                break

        if not has_fullname:
            print("\n   ⚠️  No control_fullname field found")
            print("     Using fallback name detection...")

            # Show fields with "name" in label
            name_fields = []
            for key, answer in answers.items():
                label = answer.get("text", "").lower()
                if "name" in label:
                    name_fields.append((key, answer.get("text"), answer.get("answer")))

            if name_fields:
                print(f"\n   Found {len(name_fields)} fields with 'name' in label:")
                for field_id, label, value in name_fields:
                    print(f"     - {label} (ID: {field_id}): {value}")
            else:
                print("\n   ⚠️  No fields with 'name' in label")
                print("     Using first text field as fallback")

        print("\n" + "=" * 80)
        print("FORMATTED SUBMISSION TEST")
        print("=" * 80)

        # Test formatting
        formatted = service.format_submission_data(first_submission)
        print(f"\n✓ Formatted client_name: '{formatted.get('client_name')}'")
        print(f"✓ Total formatted answers: {len(formatted.get('answers', []))}")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        if has_fullname:
            print("\n✅ Your form uses control_fullname field - OPTIMAL!")
            print("   The name extraction should work perfectly.")
        else:
            print("\n⚠️  Your form doesn't use the standard Full Name field")
            print("\n   RECOMMENDATIONS:")
            print("   1. If possible, use Jotform's 'Full Name' field type")
            print("      (This provides first/last name structure)")
            print("   2. OR make sure a field has 'name' in its label")
            print("   3. The script will use the first text field as last resort")

        if extracted_name == "Nome não encontrado":
            print("\n❌ ISSUE: Could not extract name from form!")
            print("   This is why you're seeing 'Sem nome' in the table.")
            print("\n   ACTION REQUIRED:")
            print("   1. Check the field structure above")
            print("   2. Ensure at least one field contains client name")
            print("   3. Update form to use 'Full Name' field type if possible")

        print("\n" + "=" * 80)
        print("FULL SUBMISSION JSON (for debugging)")
        print("=" * 80)
        print(json.dumps(first_submission, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Verify API key is correct")
        print("2. Verify Form ID is correct")
        print("3. Check if form has submissions")
        print("4. Check your internet connection")
        import traceback

        print("\nFull traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    analyze_jotform_structure()
