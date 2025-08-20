"""
Force creation of all tables in the database, including Sessao.
Run this file inside the app container: python force_create_tables.py
"""

from app.db.session import Base, engine
from app.db.base import Sessao

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created!")
