"""
Google Calendar Service - SOLID compliant business logic
Single Responsibility: Handle calendar business operations
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from ..domain.interfaces import ICalendarService, IGoogleCalendarRepository
from ..domain.entities import CalendarEvent
from ..repositories.google_calendar_repo import GoogleCalendarRepository
from .oauth_token_service import OAuthTokenService
from ..core.exceptions import ExpiredAccessTokenError

logger = logging.getLogger(__name__)


class GoogleCalendarService(ICalendarService):
    """
    Google Calendar service implementing business logic.
    Follows Dependency Inversion - depends on abstract interfaces.
    """

    def __init__(self, calendar_repo: Optional[IGoogleCalendarRepository] = None):
        """
        Initialize service with dependency injection.

        Args:
            calendar_repo: Calendar repository implementation
        """
        self.calendar_repo = calendar_repo or GoogleCalendarRepository()
        self.oauth_service = OAuthTokenService()

    def get_user_events(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """
        Get user's calendar events within date range.
        Handles automatic token refresh on expiration.

        Args:
            user_id: User identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of CalendarEvent domain entities
        """
        try:
            # Get access token for user
            [REDACTED_ACCESS_TOKEN]
            if not [REDACTED_ACCESS_TOKEN]"No access token found for user {user_id}")
                return []

            # Validate token before making API calls
            try:
                if not self.calendar_repo.validate_token(access_token):
                    logger.warning(f"Invalid access token for user {user_id}")
                    return []
            except ExpiredAccessTokenError:
                # Token validation failed due to expiration, refresh will be handled below
                pass

            # Fetch events from Google Calendar
            events_data = self.calendar_repo.fetch_events(
                access_token, start_date, end_date
            )

            # Convert to domain entities
            return self._parse_events_to_domain(events_data, user_id)

        except ExpiredAccessTokenError as e:
            logger.info(f"Access token expired for user {user_id}, attempting refresh")
            try:
                # Refresh the token
                new_token = self.oauth_service.refresh_access_token(user_id)
                if new_token:
                    # Retry the request with new token
                    events_data = self.calendar_repo.fetch_events(
                        new_token, start_date, end_date
                    )
                    return self._parse_events_to_domain(events_data, user_id)
                else:
                    logger.error(f"Failed to refresh token for user {user_id}")
                    return []
            except Exception as refresh_error:
                logger.error(
                    f"Error during token refresh for user {user_id}: {str(refresh_error)}"
                )
                return []
        except Exception as e:
            logger.error(f"Error fetching calendar events for user {user_id}: {str(e)}")
            return []

    def sync_events_with_sessions(self, user_id: str) -> bool:
        """
        Sync Google Calendar events with local sessions.
        Business logic for synchronization.

        Args:
            user_id: User identifier

        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Get events from the next 30 days
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)

            events = self.get_user_events(user_id, start_date, end_date)

            # TODO: Implement sync logic with session repository
            # This would involve:
            # 1. Check existing sessions for the user
            # 2. Create new sessions from calendar events
            # 3. Update existing sessions if needed
            # 4. Handle conflicts and duplicates

            logger.info(
                f"Retrieved {len(events)} events for user {user_id} (sync logic pending)"
            )
            return True

        except Exception as e:
            logger.error(f"Error syncing events for user {user_id}: {str(e)}")
            return False

    def create_session_event(
        self, session_id: str, event_details: CalendarEvent
    ) -> Optional[str]:
        """
        Create a Google Calendar event for a session.

        Args:
            session_id: Local session identifier
            event_details: Calendar event details

        Returns:
            Google event ID if successful, None otherwise
        """
        if not event_details.user_id:
            logger.error("User ID required to create calendar event")
            return None

        # Prepare event data for Google Calendar
        event_data = {
            "title": event_details.title,
            "description": event_details.description
            or f"Sessão de tatuagem - ID: {session_id}",
            "start_time": (
                event_details.start_time.isoformat()
                if event_details.start_time
                else None
            ),
            "end_time": (
                event_details.end_time.isoformat() if event_details.end_time else None
            ),
            "location": event_details.location or "",
            "attendees": event_details.attendees or [],
        }

        try:
            # Get access token for user
            [REDACTED_ACCESS_TOKEN]
            if not [REDACTED_ACCESS_TOKEN]
                    f"No access token found for user {event_details.user_id}"
                )
                return None

            # Create event in Google Calendar
            google_event_id = self.calendar_repo.create_event(access_token, event_data)

            if google_event_id:
                logger.info(
                    f"Created Google Calendar event {google_event_id} for session {session_id}"
                )

            return google_event_id

        except ExpiredAccessTokenError as e:
            logger.info(
                f"Access token expired for user {event_details.user_id}, attempting refresh"
            )
            try:
                # Refresh the token
                new_token = self.oauth_service.refresh_access_token(
                    str(event_details.user_id)
                )
                if new_token:
                    # Retry the request with new token
                    google_event_id = self.calendar_repo.create_event(
                        new_token, event_data
                    )
                    if google_event_id:
                        logger.info(
                            f"Created Google Calendar event {google_event_id} for session {session_id} (after refresh)"
                        )
                    return google_event_id
                else:
                    logger.error(
                        f"Failed to refresh token for user {event_details.user_id}"
                    )
                    return None
            except Exception as refresh_error:
                logger.error(
                    f"Error during token refresh for user {event_details.user_id}: {str(refresh_error)}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Error creating calendar event for session {session_id}: {str(e)}"
            )
            return None

    def is_user_authorized(self, user_id: str) -> bool:
        """
        Check if user has authorized calendar access.

        Args:
            user_id: User identifier

        Returns:
            True if user is authorized, False otherwise
        """
        return self.oauth_service.is_token_valid(user_id)

    def _get_user_access_token(self, user_id: str) -> Optional[str]:
        """
        Get Google access token for user using OAuth service.

        Args:
            user_id: User identifier

        Returns:
            Access token if available, None otherwise
        """
        return self.oauth_service.get_user_access_token(user_id)

    def _parse_events_to_domain(
        self, events_data: List[dict], user_id: str
    ) -> List[CalendarEvent]:
        """
        Parse Google Calendar events into domain entities.

        Args:
            events_data: Raw event data from Google Calendar API
            user_id: User identifier

        Returns:
            List of CalendarEvent domain entities
        """
        parsed_events = []

        for event_data in events_data:
            try:
                # Parse start and end times
                start_time = self._parse_datetime(event_data.get("start", {}))
                end_time = self._parse_datetime(event_data.get("end", {}))

                if not start_time or not end_time:
                    logger.warning(
                        f"Skipping event with invalid dates: {event_data.get('id', 'unknown')}"
                    )
                    continue

                # Extract attendees
                attendees = []
                for attendee in event_data.get("attendees", []):
                    if attendee.get("email"):
                        attendees.append(attendee["email"])

                # Create domain entity
                calendar_event = CalendarEvent(
                    id=event_data.get("id", ""),
                    title=event_data.get("summary", "Evento sem título"),
                    description=event_data.get("description", ""),
                    start_time=start_time,
                    end_time=end_time,
                    location=event_data.get("location", ""),
                    attendees=attendees,
                    created_by=event_data.get("creator", {}).get("email", ""),
                    google_event_id=event_data.get("id"),
                    user_id=int(user_id) if user_id.isdigit() else None,
                )

                parsed_events.append(calendar_event)

            except ValueError as ve:
                logger.warning(f"Validation error parsing event: {str(ve)}")
                continue
            except Exception as e:
                logger.warning(
                    f"Error parsing event {event_data.get('id', 'unknown')}: {str(e)}"
                )
                continue

        return parsed_events

    def _parse_datetime(self, time_data: dict) -> Optional[datetime]:
        """
        Parse Google Calendar datetime format.

        Args:
            time_data: Time data from Google Calendar API

        Returns:
            Parsed datetime or None if invalid
        """
        try:
            if "dateTime" in time_data:
                # Event with specific time
                datetime_str = time_data["dateTime"]
                # Handle timezone info
                if datetime_str.endswith("Z"):
                    datetime_str = datetime_str[:-1] + "+00:00"
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            elif "date" in time_data:
                # All-day event
                date_str = time_data["date"]
                return datetime.strptime(date_str, "%Y-%m-%d")
            return None
        except (ValueError, KeyError) as e:
            logger.warning(f"Error parsing datetime: {str(e)}")
            return None
