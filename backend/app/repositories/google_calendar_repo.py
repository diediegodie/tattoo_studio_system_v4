"""
Google Calendar Repository - SOLID compliant implementation
Single Responsibility: Handle Google Calendar API operations
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
from app.core.exceptions import ExpiredAccessTokenError
from app.domain.interfaces import IGoogleCalendarRepository

logger = logging.getLogger(__name__)


class GoogleCalendarRepository(IGoogleCalendarRepository):
    """
    Repository for Google Calendar API operations.
    Follows Dependency Inversion - implements abstract interface.
    """

    def __init__(self):
        self.base_url = "https://www.googleapis.com/calendar/v3"

    def fetch_events(
        self, [REDACTED_ACCESS_TOKEN] start_date: datetime, end_date: datetime
    ) -> List[dict]:
        """
        Fetch events from Google Calendar API.

        Args:
            [REDACTED_ACCESS_TOKEN] OAuth access token
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of event dictionaries from Google Calendar API
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Format dates for Google Calendar API (RFC3339)
            time_min = (
                start_date.isoformat() + "Z"
                if start_date.tzinfo is None
                else start_date.isoformat()
            )
            time_max = (
                end_date.isoformat() + "Z"
                if end_date.tzinfo is None
                else end_date.isoformat()
            )

            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 250,  # Google Calendar API limit
            }

            # DEBUG: Log API call details
            logger.info(f"DEBUG: Making Google Calendar API call")
            logger.info(f"DEBUG: URL: {self.base_url}/calendars/primary/events")
            logger.info(f"DEBUG: Parameters: {params}")
            logger.info(f"DEBUG: Date range: {time_min} to {time_max}")

            response = requests.get(
                f"{self.base_url}/calendars/primary/events",
                headers=headers,
                params=params,
                timeout=30,
            )

            # DEBUG: Log API response
            logger.info(f"DEBUG: Google API response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                events_count = len(data.get("items", []))
                logger.info(f"DEBUG: Google API returned {events_count} events")

                # Log sample event if any exist
                if events_count > 0:
                    sample_event = data.get("items", [])[0]
                    logger.info(
                        f"DEBUG: Sample event: {sample_event.get('summary', 'No title')} - {sample_event.get('start', {})}"
                    )

                return data.get("items", [])
            elif response.status_code == 401:
                logger.warning("DEBUG: Google Calendar API: Unauthorized access token")
                raise ExpiredAccessTokenError("Access token expired, needs refresh")
            else:
                logger.error(
                    f"DEBUG: Google Calendar API error: {response.status_code}"
                )
                logger.error(f"DEBUG: Response text: {response.text}")
                return []

        except requests.RequestException as e:
            logger.error(f"Request error fetching calendar events: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching calendar events: {str(e)}")
            return []

    def create_event(self, [REDACTED_ACCESS_TOKEN] event_data: dict) -> Optional[str]:
        """
        Create an event in Google Calendar.

        Args:
            [REDACTED_ACCESS_TOKEN] OAuth access token
            event_data: Event data dictionary

        Returns:
            Google event ID if successful, None otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.base_url}/calendars/primary/events",
                headers=headers,
                json=event_data,
                timeout=30,
            )

            if response.status_code == 200:
                created_event = response.json()
                return created_event.get("id")
            elif response.status_code == 401:
                logger.warning(
                    "Google Calendar API: Unauthorized access token during event creation"
                )
                raise ExpiredAccessTokenError("Access token expired, needs refresh")
            else:
                logger.error(
                    f"Error creating calendar event: {response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Request error creating calendar event: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating calendar event: {str(e)}")
            return None

    def validate_token(self, [REDACTED_ACCESS_TOKEN] -> bool:
        """
        Validate Google access token by making a test request.

        Args:
            [REDACTED_ACCESS_TOKEN] OAuth access token

        Returns:
            True if token is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Make a simple request to validate token
            response = requests.get(
                f"{self.base_url}/calendars/primary", headers=headers, timeout=10
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                logger.warning(
                    "Google Calendar API: Unauthorized access token during validation"
                )
                raise ExpiredAccessTokenError("Access token expired, needs refresh")
            else:
                logger.warning(
                    f"Token validation failed with status {response.status_code}"
                )
                return False

        except ExpiredAccessTokenError:
            # Re-raise the exception to be handled by the service layer
            raise
        except requests.RequestException as e:
            logger.error(f"Request error validating token: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            return False

    def _format_event_for_google(self, event_data: Dict) -> Dict:
        """
        Format event data for Google Calendar API.

        Args:
            event_data: Internal event data

        Returns:
            Formatted event data for Google API
        """
        return {
            "summary": event_data.get("title", ""),
            "description": event_data.get("description", ""),
            "start": {
                "dateTime": event_data.get("start_time"),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": event_data.get("end_time"),
                "timeZone": "America/Sao_Paulo",
            },
            "location": event_data.get("location", ""),
            "attendees": [
                {"email": email} for email in event_data.get("attendees", [])
            ],
        }
