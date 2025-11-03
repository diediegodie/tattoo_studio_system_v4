import logging
from typing import Any, Dict, List, Optional, Union

from app.db.base import Pagamento
from sqlalchemy.orm import Session


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
        except Exception as e:
            self.db.rollback()
            logging.error(
                "Error creating pagamento",
                extra={"context": {"error": str(e)}},
                exc_info=True,
            )
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
        except Exception as e:
            self.db.rollback()
            logging.error(
                "Error updating pagamento",
                extra={"context": {"pagamento_id": pagamento_id, "error": str(e)}},
                exc_info=True,
            )
            return None

    def delete(self, pagamento_id: int) -> bool:
        """
        Delete a pagamento by ID. Note: Associated commissions are NOT deleted automatically
        to maintain data independence. Commissions should be managed separately.

        Args:
            pagamento_id: ID of pagamento to delete

        Returns:
            True if deleted, False if not found or error
        """
        try:
            pagamento = self.get_by_id(pagamento_id)
            if not pagamento:
                return False

            # Handle Comissao relationships - set pagamento_id to NULL for related comissoes
            # This maintains data independence between payments and commissions
            from app.db.base import Comissao

            self.db.query(Comissao).filter(
                Comissao.pagamento_id == pagamento_id
            ).update({"pagamento_id": None})

            # Handle Sessao relationships - set payment_id to NULL for related sessoes
            from app.db.base import Sessao

            self.db.query(Sessao).filter(Sessao.payment_id == pagamento_id).update(
                {"payment_id": None}
            )

            # Now delete the pagamento
            self.db.delete(pagamento)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logging.error(
                "Error deleting pagamento",
                extra={"context": {"pagamento_id": pagamento_id, "error": str(e)}},
                exc_info=True,
            )
            return False
