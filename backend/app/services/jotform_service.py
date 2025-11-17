"""
JotForm API integration service following SOLID principles.

This service:
- Handles external API communication (Single Responsibility)
- Implements IJotFormService interface (Dependency Inversion)
- Can be easily mocked for testing (Interface Segregation)
- Formats JotForm data using your existing logic
"""

import json
import logging
from typing import List, Optional

import requests
from app.domain.interfaces import IJotFormService
from app.utils.client_utils import normalize_display_name

logger = logging.getLogger(__name__)


class JotFormService(IJotFormService):
    """JotForm API service implementing your existing logic."""

    def __init__(self, api_key: str, form_id: str):
        self.api_key = api_key
        self.form_id = form_id
        self.base_url = "https://api.jotform.com"

    def fetch_submissions(self) -> List[dict]:
        """Fetch all relevant submissions from JotForm API with pagination.

        This method implements pagination to fetch ALL submissions, not just
        the first 20 (API default). It makes multiple requests if needed to
        retrieve all records from JotForm.

        Returns:
            List of all non-deleted submission dictionaries
        """
        all_submissions = []
        offset = 0
        limit = 100  # Fetch 100 records per request
        max_iterations = 50  # Safety limit: max 5000 records total

        logger.info(
            "Starting JotForm submissions fetch with pagination",
            extra={"context": {"form_id": self.form_id, "batch_size": limit}},
        )

        try:
            iteration = 0  # Initialize to prevent unbound variable warning
            for iteration in range(max_iterations):
                # Build URL with pagination parameters
                url = f"{self.base_url}/form/{self.form_id}/submissions"
                params = {"apiKey": self.api_key, "offset": offset, "limit": limit}

                # Fetch batch with timeout
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                batch = data.get("content", [])

                if not batch:  # Empty response, we're done
                    logger.debug(
                        "No more submissions to fetch",
                        extra={
                            "context": {
                                "offset": offset,
                                "total_fetched": len(all_submissions),
                            }
                        },
                    )
                    break

                # Filter out deleted submissions
                valid_count = 0
                for item in batch:
                    if item.get("status") not in ["DELETED", None]:
                        all_submissions.append(item)
                        valid_count += 1

                logger.info(
                    f"Fetched batch {iteration + 1}: {valid_count} valid submissions (out of {len(batch)} total)",
                    extra={
                        "context": {
                            "batch": iteration + 1,
                            "offset": offset,
                            "batch_size": len(batch),
                            "valid_in_batch": valid_count,
                            "total_valid": len(all_submissions),
                        }
                    },
                )

                # Stop if this was the last page
                if len(batch) < limit:
                    logger.info(
                        "Reached last page of submissions",
                        extra={"context": {"total_submissions": len(all_submissions)}},
                    )
                    break

                # Move to next page
                offset += limit

            logger.info(
                f"JotForm fetch complete: {len(all_submissions)} total submissions retrieved",
                extra={
                    "context": {
                        "total_submissions": len(all_submissions),
                        "batches": iteration + 1,
                    }
                },
            )

            return all_submissions

        except requests.RequestException as e:
            logger.error(
                "Failed to fetch JotForm submissions",
                extra={"context": {"offset": offset, "error": str(e)}},
                exc_info=True,
            )
            raise Exception(
                f"Failed to fetch JotForm submissions at offset {offset}: {str(e)}"
            )

    def parse_client_name(self, submission: dict) -> str:
        """Extract client name from JotForm submission using robust field-type-first logic.

        This method prioritizes field types over labels to ensure compatibility
        with any form structure, regardless of language or custom labels.

        Priority order:
        1. control_fullname field type (most reliable)
        2. Any field with 'name' in label (fallback)
        3. First non-empty text field (last resort)
        """
        answers = submission.get("answers", {})

        # PRIORITY 1: Look for control_fullname field type (most reliable)
        for _, answer in answers.items():
            if answer.get("type") == "control_fullname":
                name_data = answer.get("answer", {})
                if isinstance(name_data, dict):
                    first = name_data.get("first", "")
                    last = name_data.get("last", "")
                    full_name = f"{first} {last}".strip()
                    if full_name:  # Only return if not empty
                        return normalize_display_name(full_name)

        # PRIORITY 2: Fallback - find any field with "name" in the label
        for _, answer in answers.items():
            label = answer.get("text", "").lower()
            answer_value = answer.get("answer")

            if "name" in label and answer_value:
                # Handle both string and dict answers
                if isinstance(answer_value, dict):
                    # Try to extract name parts from dict
                    if "first" in answer_value or "last" in answer_value:
                        first = answer_value.get("first", "")
                        last = answer_value.get("last", "")
                        full_name = f"{first} {last}".strip()
                        if full_name:
                            return normalize_display_name(full_name)
                else:
                    # Simple string answer
                    name_str = str(answer_value).strip()
                    if name_str:
                        return normalize_display_name(name_str)

        # PRIORITY 3: Last resort - use first non-empty text field
        # This catches forms where the name field has an unusual label
        for _, answer in answers.items():
            field_type = answer.get("type", "")
            answer_value = answer.get("answer")

            # Look for simple text fields (textbox, email, etc.)
            if field_type in ["control_textbox", "control_email"] and answer_value:
                name_str = str(answer_value).strip()
                if name_str and len(name_str) > 2:  # Avoid single-char fields
                    return normalize_display_name(name_str)

        return "Nome não encontrado"

    def format_submission_data(self, submission: dict) -> dict:
        """Format submission data for display using your existing logic.

        Now includes the extracted client_name at the root level for reliable
        display in the frontend table, regardless of form structure.
        """
        answers_list = []

        for _, answer in submission.get("answers", {}).items():
            label = answer.get("text")  # Nome do campo direto do JotForm
            field_type = answer.get("type")
            value = self._format_answer(answer.get("answer"), field_type)

            if value:  # só adiciona se tiver valor
                answers_list.append(
                    {"label": label, "value": value, "type": field_type}
                )

        # Extract client name using the same robust logic as parse_client_name
        client_name = self.parse_client_name(submission)

        return {
            "id": submission.get("id"),
            "client_name": client_name,  # Reliable name extraction
            "answers": answers_list,
        }

    def _format_answer(self, answer, field_type: str) -> Optional[str]:
        """Format answers using your existing logic from format_answer function."""
        if not answer:
            return None

        if field_type == "control_fullname":
            if isinstance(answer, dict):
                return f"{answer.get('first','')} {answer.get('last','')}".strip()

        elif field_type == "control_address":
            if isinstance(answer, dict):
                parts = [
                    answer.get("addr_line1", ""),
                    answer.get("addr_line2", ""),
                    answer.get("city", ""),
                    answer.get("state", ""),
                    answer.get("postal", ""),
                ]
                return "<br>".join([p for p in parts if p])

        elif field_type == "control_phone":
            if isinstance(answer, dict):
                return answer.get("full", "")

        elif field_type == "control_matrix":
            # Monta mini-tabela HTML para a matriz
            if isinstance(answer, dict):
                if "prettyFormat" in answer:
                    return answer["prettyFormat"]
                # Caso não tenha prettyFormat, tenta construir manualmente
                rows = []
                for _, r_vals in answer.items():
                    try:
                        cells = json.loads(str(r_vals))
                        row_html = (
                            "<tr>" + "".join([f"<td>{c}</td>" for c in cells]) + "</tr>"
                        )
                        rows.append(row_html)
                    except:
                        rows.append(f"<tr><td>{r_vals}</td></tr>")
                return "<table border='1' cellpadding='3'>" + "".join(rows) + "</table>"

        # Campos simples: textarea, textbox, email, radio, dropdown
        return str(answer)
