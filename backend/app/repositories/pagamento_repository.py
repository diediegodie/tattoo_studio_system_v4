from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..db.base import Pagamento


class PagamentoRepository:
    """Repository for Pagamento model operations following SOLID principles."""

    def __init__(self, db: Session):
        """
        Initialize the repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, pagamento: Pagamento) -> Union[Pagamento, None]:
        """
        Create a new pagamento record.

        Args:
            pagamento: Pagamento object to create

        Returns:
            Created Pagamento object or None if error
        """
        try:
            self.db.add(pagamento)
            self.db.commit()
            self.db.refresh(pagamento)
            return pagamento
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Error creating pagamento: {str(e)}")
            return None

    def get_by_id(self, pagamento_id: int) -> Optional[Pagamento]:
        """
        Get a pagamento by ID.

        Args:
            pagamento_id: ID of pagamento to retrieve

        Returns:
            Pagamento object or None if not found
        """
        return self.db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()

    def list_all(self) -> List[Pagamento]:
        """
        List all pagamentos.

        Returns:
            List of Pagamento objects
        """
        return self.db.query(Pagamento).order_by(Pagamento.data.desc()).all()

    def update(self, pagamento_id: int, data: Dict[str, Any]) -> Optional[Pagamento]:
        """
        Update a pagamento.

        Args:
            pagamento_id: ID of pagamento to update
            data: Dictionary of fields to update

        Returns:
            Updated Pagamento object or None if not found or error
        """
        try:
            pagamento = self.get_by_id(pagamento_id)
            if not pagamento:
                return None

            # Update fields
            for key, value in data.items():
                if hasattr(pagamento, key):
                    setattr(pagamento, key, value)

            self.db.commit()
            self.db.refresh(pagamento)
            return pagamento
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Error updating pagamento: {str(e)}")
            return None

    def delete(self, pagamento_id: int) -> bool:
        """
        Delete a pagamento.

        Args:
            pagamento_id: ID of pagamento to delete

        Returns:
            True if deleted, False if not found or error
        """
        try:
            pagamento = self.get_by_id(pagamento_id)
            if not pagamento:
                return False

            self.db.delete(pagamento)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"Error deleting pagamento: {str(e)}")
            return False
