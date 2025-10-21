from typing import List, Optional

from app.core.interfaces.repository_interface import InventoryRepositoryInterface
from app.db.base import Inventory
from app.db.session import SessionLocal
from app.domain.entities import InventoryItem


class InventoryRepository(InventoryRepositoryInterface):
    def reorder_items(self, order_list: list[int]) -> None:
        """Update the 'order' field for each item according to the given list of IDs."""
        for idx, item_id in enumerate(order_list):
            db_item = self.db.query(Inventory).filter_by(id=item_id).first()
            if db_item:
                setattr(db_item, "order", idx)
        self.db.commit()

    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()

    def add(self, item: InventoryItem) -> InventoryItem:
        db_item = Inventory(
            nome=item.nome,
            quantidade=item.quantidade,
            observacoes=item.observacoes,
            # New items should not have a manual order by default
            order=None,
        )
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return self._to_domain(db_item)

    def update(self, item: InventoryItem) -> InventoryItem:
        db_item = self.db.query(Inventory).filter_by(id=item.id).first()
        if not db_item:
            raise ValueError("Item not found")
        setattr(db_item, "nome", item.nome)
        setattr(db_item, "quantidade", item.quantidade)
        setattr(db_item, "observacoes", item.observacoes)
        self.db.commit()
        self.db.refresh(db_item)
        return self._to_domain(db_item)

    def delete(self, item_id: int) -> None:
        db_item = self.db.query(Inventory).filter_by(id=item_id).first()
        if db_item:
            self.db.delete(db_item)
            self.db.commit()

    def get_by_id(self, item_id: int) -> Optional[InventoryItem]:
        db_item = self.db.query(Inventory).filter_by(id=item_id).first()
        return self._to_domain(db_item) if db_item else None

    def list_all(self) -> List[InventoryItem]:
        # Return items in two groups to satisfy ordering requirements:
        # 1) Items without manual 'order' (NULL) sorted by created_at DESC (newest first)
        # 2) Items with manual 'order' defined sorted by order ASC
        no_order_items = (
            self.db.query(Inventory)
            .filter(Inventory.order == None)
            .order_by(Inventory.created_at.desc())
            .all()
        )
        ordered_items = (
            self.db.query(Inventory)
            .filter(Inventory.order != None)
            .order_by(Inventory.order.asc())
            .all()
        )
        items = no_order_items + ordered_items
        return [self._to_domain(i) for i in items]

    def change_quantity(self, item_id: int, delta: int) -> InventoryItem:
        db_item = self.db.query(Inventory).filter_by(id=item_id).first()
        if not db_item:
            raise ValueError("Item not found")
        current_qtd = getattr(db_item, "quantidade", 0) or 0
        setattr(db_item, "quantidade", current_qtd + delta)
        self.db.commit()
        self.db.refresh(db_item)
        return self._to_domain(db_item)

    def _to_domain(self, db_item: Inventory) -> InventoryItem:
        return InventoryItem(
            id=getattr(db_item, "id", None),
            nome=getattr(db_item, "nome", ""),
            quantidade=getattr(db_item, "quantidade", 0),
            observacoes=getattr(db_item, "observacoes", None),
            created_at=getattr(db_item, "created_at", None),
            updated_at=getattr(db_item, "updated_at", None),
        )
