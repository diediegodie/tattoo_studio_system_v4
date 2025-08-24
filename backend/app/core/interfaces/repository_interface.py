from typing import List, Optional
from domain.entities import InventoryItem


class InventoryRepositoryInterface:
    def add(self, item: InventoryItem) -> InventoryItem:
        raise NotImplementedError

    def update(self, item: InventoryItem) -> InventoryItem:
        raise NotImplementedError

    def delete(self, item_id: int) -> None:
        raise NotImplementedError

    def get_by_id(self, item_id: int) -> Optional[InventoryItem]:
        raise NotImplementedError

    def list_all(self) -> List[InventoryItem]:
        raise NotImplementedError

    def change_quantity(self, item_id: int, delta: int) -> InventoryItem:
        raise NotImplementedError
