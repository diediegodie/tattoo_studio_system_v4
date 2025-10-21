"""
Calendar Controller - SOLID compliant HTTP handlers
Single Responsibility: Handle calendar-related HTTP requests
"""

import logging
from datetime import datetime, timedelta

from app.domain.interfaces import ICalendarService
from app.services.google_calendar_service import GoogleCalendarService
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.core.csrf_config import csrf

logger = logging.getLogger(__name__)

# Create Blueprint
calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")


def _get_calendar_service() -> ICalendarService:
    """
    Dependency injection for calendar service.
    Follows Dependency Inversion Principle.

    Returns:
        Calendar service implementation
    """
    return GoogleCalendarService()


@calendar_bp.route("/api/events", methods=["GET"])
@login_required
def get_events():
    """
    API endpoint to fetch calendar events.
    Returns JSON data for frontend consumption.

    Query Parameters:
        start (str): Start date in ISO format (optional)
        end (str): End date in ISO format (optional)

    Returns:
        JSON response with events or error
    """
    try:
        # Get date range from query parameters
        start_date_str = request.args.get("start", "")
        end_date_str = request.args.get("end", "")

        # Default to current week if no dates provided
        if not start_date_str:
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            try:
                start_date = datetime.fromisoformat(
                    start_date_str.replace("Z", "+00:00")
                )
            except ValueError:
                return (
                    jsonify(
                        {"success": False, "error": "Formato de data inicial inválido"}
                    ),
                    400,
                )

        if not end_date_str:
            end_date = start_date + timedelta(days=7)
        else:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except ValueError:
                return (
                    jsonify(
                        {"success": False, "error": "Formato de data final inválido"}
                    ),
                    400,
                )

        # Validate date range
        if end_date <= start_date:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Data final deve ser posterior à data inicial",
                    }
                ),
                400,
            )

        # Get calendar service and fetch events
        calendar_service = _get_calendar_service()

        # DEBUG: Log user authorization check
        logger.info(f"DEBUG: Checking authorization for user {current_user.id}")
        is_authorized = calendar_service.is_user_authorized(str(current_user.id))
        logger.info(f"DEBUG: User {current_user.id} authorized: {is_authorized}")

        # Check if user is authorized
        if not is_authorized:
            logger.warning(
                f"DEBUG: User {current_user.id} not authorized for Google Calendar"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não autorizado para acesso ao Google Calendar",
                        "auth_required": True,
                    }
                ),
                401,
            )

        # DEBUG: Log date range and API call
        logger.info(
            f"DEBUG: Fetching events for user {current_user.id} from {start_date} to {end_date}"
        )

        events = calendar_service.get_user_events(
            user_id=str(current_user.id), start_date=start_date, end_date=end_date
        )

        # DEBUG: Log events retrieved
        logger.info(f"DEBUG: Retrieved {len(events)} events from Google Calendar")

        # Convert events to JSON-serializable format
        events_data = []
        for event in events:
            events_data.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "start": event.start_time.isoformat() if event.start_time else None,
                    "end": event.end_time.isoformat() if event.end_time else None,
                    "location": event.location,
                    "attendees": event.attendees or [],
                    "duration": event.duration_minutes,
                    "isPast": event.is_past_event,
                    "createdBy": event.created_by,
                    "googleEventId": event.google_event_id,
                }
            )

        return jsonify(
            {
                "success": True,
                "events": events_data,
                "count": len(events_data),
                "dateRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(
            f"Error fetching calendar events for user {current_user.id}: {str(e)}"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro interno do servidor ao buscar eventos",
                }
            ),
            500,
        )


@csrf.exempt
@calendar_bp.route("/api/sync", methods=["POST"])
@login_required
def sync_calendar():
    """
    API endpoint to sync Google Calendar with local sessions.

    Returns:
        JSON response with sync result
    """
    try:
        calendar_service = _get_calendar_service()

        # Check if user is authorized
        if not calendar_service.is_user_authorized(str(current_user.id)):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não autorizado para acesso ao Google Calendar",
                        "auth_required": True,
                    }
                ),
                401,
            )

        # Perform sync
        success = calendar_service.sync_events_with_sessions(str(current_user.id))

        if success:
            return jsonify(
                {"success": True, "message": "Calendário sincronizado com sucesso"}
            )
        else:
            return (
                jsonify({"success": False, "error": "Falha ao sincronizar calendário"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error syncing calendar for user {current_user.id}: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro interno do servidor durante sincronização",
                }
            ),
            500,
        )


@csrf.exempt
@calendar_bp.route("/api/create-event", methods=["POST"])
@login_required
def create_event():
    """
    API endpoint to create a calendar event.

    Expected JSON body:
        {
            "title": "Event title",
            "description": "Event description",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T11:00:00",
            "location": "Event location",
            "attendees": ["email1@example.com", "email2@example.com"]
        }

    Returns:
        JSON response with created event ID or error
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body required"}), 400

        # Validate required fields
        required_fields = ["title", "start_time", "end_time"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        # Parse datetime fields
        try:
            start_time = datetime.fromisoformat(
                data["start_time"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))
        except ValueError as e:
            return (
                jsonify(
                    {"success": False, "error": f"Invalid datetime format: {str(e)}"}
                ),
                400,
            )

        # Create CalendarEvent domain entity
        from app.domain.entities import CalendarEvent

        calendar_event = CalendarEvent(
            title=data["title"],
            description=data.get("description", ""),
            start_time=start_time,
            end_time=end_time,
            location=data.get("location", ""),
            attendees=data.get("attendees", []),
            user_id=current_user.id,
        )

        # Create event through service
        calendar_service = _get_calendar_service()

        # Check if user is authorized
        if not calendar_service.is_user_authorized(str(current_user.id)):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não autorizado para acesso ao Google Calendar",
                        "auth_required": True,
                    }
                ),
                401,
            )

        google_event_id = calendar_service.create_session_event(
            session_id=f"manual_{current_user.id}_{int(datetime.now().timestamp())}",
            event_details=calendar_event,
        )

        if google_event_id:
            return jsonify(
                {
                    "success": True,
                    "message": "Evento criado com sucesso",
                    "google_event_id": google_event_id,
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Falha ao criar evento no Google Calendar",
                    }
                ),
                500,
            )

    except ValueError as ve:
        logger.warning(f"Validation error creating event: {str(ve)}")
        return (
            jsonify({"success": False, "error": f"Erro de validação: {str(ve)}"}),
            400,
        )
    except Exception as e:
        logger.error(
            f"Error creating calendar event for user {current_user.id}: {str(e)}"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro interno do servidor ao criar evento",
                }
            ),
            500,
        )


@calendar_bp.route("/api/status", methods=["GET"])
@login_required
def get_status():
    """
    API endpoint to check calendar integration status.

    Returns:
        JSON response with authorization status
    """
    try:
        calendar_service = _get_calendar_service()
        is_authorized = calendar_service.is_user_authorized(str(current_user.id))

        return jsonify(
            {
                "success": True,
                "authorized": is_authorized,
                "user_id": current_user.id,
                "message": "Authorization check completed",
            }
        )

    except Exception as e:
        logger.error(
            f"Error checking calendar status for user {current_user.id}: {str(e)}"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal server error while checking status",
                }
            ),
            500,
        )


@calendar_bp.route("/", methods=["GET"])
@login_required
def calendar_page():
    """
    Renders the main calendar page.

    Returns:
        Rendered HTML template with calendar events
    """
    try:
        calendar_service = _get_calendar_service()

        # Check if user is authorized
        is_authorized = calendar_service.is_user_authorized(str(current_user.id))

        events = []
        # Keep track of which events already have a session
        events_with_sessions = set()

        if is_authorized:
            try:
                # Get events for the next 30 days
                start_date = datetime.now()
                end_date = start_date + timedelta(days=30)
                events = calendar_service.get_user_events(
                    str(current_user.id), start_date, end_date
                )
                # Sort events by start_time
                events.sort(
                    key=lambda x: x.start_time if x.start_time else datetime.min
                )

                # Check which events already have a corresponding session
                if events:
                    # Get a list of all Google event IDs that have already been converted to sessions
                    from app.db.base import Sessao
                    from app.db.session import SessionLocal

                    db = SessionLocal()
                    try:
                        # Collect all google_event_ids that exist in the sessions table
                        existing_event_ids = {
                            row[0]
                            for row in db.query(Sessao.google_event_id)
                            .filter(Sessao.google_event_id.isnot(None))
                            .all()
                        }

                        # Update the events_with_sessions set
                        for event in events:
                            if event.google_event_id in existing_event_ids:
                                events_with_sessions.add(event.google_event_id)
                    finally:
                        db.close()

            except Exception as e:
                logger.error(f"Error fetching events for page: {str(e)}")
                flash("Erro ao buscar eventos do Google Calendar", "error")

        return render_template(
            "agenda.html",
            events=events,
            calendar_connected=is_authorized,
            events_with_sessions=events_with_sessions,
        )

    except Exception as e:
        logger.error(f"Error rendering calendar page: {str(e)}")
        flash("Erro ao carregar página de agenda", "error")
        return redirect(url_for("index"))


@calendar_bp.route("/sync", methods=["GET"])
@login_required
def sync_events():
    """
    Sync calendar events and redirect back to calendar page.
    Similar to the JotForm sync pattern.

    Returns:
        Redirect to calendar page with flash message
    """
    try:
        calendar_service = _get_calendar_service()

        # Check if user is authorized
        if not calendar_service.is_user_authorized(str(current_user.id)):
            flash(
                "Você precisa autorizar o acesso ao Google Calendar primeiro", "warning"
            )
            # Set session flag to indicate this is a calendar sync operation
            from flask import session

            session["oauth_purpose"] = "calendar_sync"
            return redirect(
                url_for("google_oauth_calendar.login")
            )  # Corrected endpoint

        # Sync events
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)

        # DEBUG: Log sync operation details
        logger.info(f"DEBUG: Starting calendar sync for user {current_user.id}")
        logger.info(f"DEBUG: Date range: {start_date} to {end_date}")

        try:
            events = calendar_service.get_user_events(
                str(current_user.id), start_date, end_date
            )

            # DEBUG: Log detailed event information
            logger.info(f"DEBUG: Sync retrieved {len(events)} events")
            for i, event in enumerate(events[:3]):  # Log first 3 events
                logger.info(f"DEBUG: Event {i+1}: {event.title} - {event.start_time}")

            flash(
                f"Sincronização concluída! {len(events)} eventos encontrados.",
                "success",
            )
        except Exception as e:
            logger.error(f"Error syncing calendar events: {str(e)}")
            logger.error(f"DEBUG: Full sync error traceback", exc_info=True)
            flash("Erro ao sincronizar eventos do Google Calendar", "error")

    except Exception as e:
        logger.error(f"Error in sync_events: {str(e)}")
        flash("Erro interno ao sincronizar eventos do Google Calendar", "error")

    return redirect(url_for("calendar.calendar_page"))
