from typing import List, Optional
from domain.entities import InventoryItem


class InventoryServiceInterface:
    def add_item(self, item: InventoryItem) -> InventoryItem:
        raise NotImplementedError

    def update_item(self, item: InventoryItem) -> InventoryItem:
        raise NotImplementedError

    def delete_item(self, item_id: int) -> None:
        raise NotImplementedError

    def get_item(self, item_id: int) -> Optional[InventoryItem]:
        raise NotImplementedError

    def list_items(self) -> List[InventoryItem]:
        raise NotImplementedError

    def change_quantity(self, item_id: int, delta: int) -> InventoryItem:
        raise NotImplementedError
