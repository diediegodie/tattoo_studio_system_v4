"""
JotForm API integration service following SOLID principles.

This service:
- Handles external API communication (Single Responsibility)
- Implements IJotFormService interface (Dependency Inversion)
- Can be easily mocked for testing (Interface Segregation)
- Formats JotForm data using your existing logic
"""

import requests
import json
from typing import List, Dict, Optional
from domain.interfaces import IJotFormService


class JotFormService(IJotFormService):
    """JotForm API service implementing your existing logic."""

    def __init__(self, [REDACTED_API_KEY] form_id: str):
        self.[REDACTED_API_KEY]
        self.form_id = form_id
        self.base_url = "https://api.jotform.com"

    def fetch_submissions(self) -> List[dict]:
        """Fetch all active submissions from JotForm API."""
        url = f"{self.base_url}/form/{self.form_id}/submissions?apiKey={self.api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            submissions = []

            for item in data.get("content", []):
                if item.get("status") == "ACTIVE":
                    submissions.append(item)

            return submissions

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch JotForm submissions: {str(e)}")

    def parse_client_name(self, submission: dict) -> str:
        """Extract client name from JotForm submission using your logic."""
        answers = submission.get("answers", {})

        for key, answer in answers.items():
            if answer.get("type") == "control_fullname":
                name_data = answer.get("answer", {})
                if isinstance(name_data, dict):
                    first = name_data.get("first", "")
                    last = name_data.get("last", "")
                    return f"{first} {last}".strip()

        # Fallback: try to find any field with "name" in the label
        for key, answer in answers.items():
            label = answer.get("text", "").lower()
            if "name" in label and "answer" in answer:
                return str(answer["answer"])

        return "Nome não encontrado"

    def format_submission_data(self, submission: dict) -> dict:
        """Format submission data for display using your existing logic."""
        answers_list = []

        for key, answer in submission.get("answers", {}).items():
            label = answer.get("text")  # Nome do campo direto do JotForm
            field_type = answer.get("type")
            value = self._format_answer(answer.get("answer"), field_type)

            if value:  # só adiciona se tiver valor
                answers_list.append({"label": label, "value": value})

        return {"id": submission.get("id"), "answers": answers_list}

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
                for r_key, r_vals in answer.items():
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
