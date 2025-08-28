"""
Custom exceptions for the application.
Following SOLID principles - centralized error handling.
"""


class ExpiredAccessTokenError(Exception):
    """
    Exception raised when Google Calendar API access token has expired.
    Used to trigger automatic token refresh.
    """

    pass
