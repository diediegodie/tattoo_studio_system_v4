import logging
import os

from .controllers.drag_drop_controller import drag_drop_bp
from .db.base import Client, Inventory, OAuth, Pagamento, Sessao, TestModel, User
from .db.session import create_tables
from .main import create_app

logger = logging.getLogger(__name__)

# Create Flask app
app = create_app()

if __name__ == "__main__":
    # Create tables on startup
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(
            "Error creating tables",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )

    # Run the Flask app
    # Use PORT from environment (for Render/production) or default to 5000 (for local dev)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
