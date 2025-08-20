from db.base import User, OAuth, TestModel, Client, Sessao
from db.session import create_tables
from main import create_app

# Create Flask app
app = create_app()

if __name__ == "__main__":
    # Create tables on startup
    try:
        create_tables()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
