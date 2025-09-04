from typing import Optional
from ..core.interfaces.service_interface import InventoryServiceInterface
from ..core.interfaces.repository_interface import InventoryRepositoryInterface
from ..domain.entities import InventoryItem


class InventoryService(InventoryServiceInterface):
    def reorder_items(self, order_list: list[int]) -> None:
        """Reorder inventory items by list of IDs."""
        self.repository.reorder_items(order_list)

    def __init__(self, repository: InventoryRepositoryInterface):
        self.repository = repository

    def add_item(self, item: InventoryItem) -> InventoryItem:
        return self.repository.add(item)

    def update_item(self, item: InventoryItem) -> InventoryItem:
        return self.repository.update(item)

    def delete_item(self, item_id: int) -> None:
        self.repository.delete(item_id)

    def get_item(self, item_id: int) -> Optional[InventoryItem]:
        return self.repository.get_by_id(item_id)

    def list_items(self) -> list[InventoryItem]:
        return self.repository.list_all()

    def change_quantity(self, item_id: int, delta: int) -> InventoryItem:
        return self.repository.change_quantity(item_id, delta)
