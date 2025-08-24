// DRAG_DROP.JS - Drag & Drop reordering for inventory table
console.log('🟦 DRAG_DROP.JS CARREGADO');

document.addEventListener('DOMContentLoaded', function() {
    const tbody = document.querySelector('.table-wrapper table tbody');
    if (!tbody) return;

    let draggedRow = null;

    // Enable drag events on each row
    Array.from(tbody.children).forEach(row => {
        if (!row.hasAttribute('data-id')) return;
        row.draggable = true;
        row.addEventListener('dragstart', function(e) {
            draggedRow = row;
            row.classList.add('dragging');
        });
        row.addEventListener('dragend', function(e) {
            draggedRow = null;
            row.classList.remove('dragging');
        });
    });

    tbody.addEventListener('dragover', function(e) {
        e.preventDefault();
        const afterElement = getDragAfterElement(tbody, e.clientY);
        if (draggedRow && afterElement && afterElement !== draggedRow) {
            tbody.insertBefore(draggedRow, afterElement);
        } else if (draggedRow && !afterElement) {
            tbody.appendChild(draggedRow);
        }
    });

    function getDragAfterElement(container, y) {
        const rows = [...container.querySelectorAll('tr[data-id]:not(.dragging)')];
        return rows.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: -Infinity }).element;
    }

    // On submit, send new order via PATCH and reload inventory from backend
    const form = document.getElementById('drag-drop-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const order = Array.from(tbody.querySelectorAll('tr[data-id]')).map(row => row.getAttribute('data-id'));
        fetch(form.action, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ order: order })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Always reload inventory from backend to reflect new order
                fetch('/inventory/')
                    .then(res => res.json())
                    .then(invData => {
                        // Replace local inventoryData and re-render if needed
                        if (typeof inventoryData !== 'undefined') {
                            inventoryData = invData;
                            if (typeof renderInventory === 'function') {
                                renderInventory();
                            }
                        }
                        window.location.href = data.redirect_url;
                    });
            } else {
                alert('Erro ao aplicar ordem.');
            }
        })
        .catch(() => alert('Erro na requisição.'));
    });
});
