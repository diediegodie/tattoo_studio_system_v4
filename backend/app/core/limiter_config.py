import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Global Limiter instance to be imported by controllers
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=os.getenv("LIMITER_STORAGE_URI", "memory://"),
)
