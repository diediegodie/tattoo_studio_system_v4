// INVENTORY.JS - VERSÃO RESTAURADA COM FUNCIONALIDADES COMPLETAS
console.log('📂 INVENTORY.JS CARREGADO');

let inventoryData = [];

// Carregar dados do inventário
async function loadInventory() {
    try {
        console.log('📋 Carregando inventário...');
    const response = await fetch('/inventory/');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        inventoryData = await response.json();
        console.log('✅ Dados carregados:', inventoryData.length, 'itens');
        renderInventory();
    } catch (error) {
        console.error('❌ Erro ao carregar inventário:', error);
        // Nenhum fallback necessário, pois o backend sempre estará rodando
    }
}
// ...existing code...

// Renderizar a tabela do inventário
function renderInventory() {
    const tbody = document.querySelector('.table-wrapper table tbody');
    if (!tbody) {
        console.error('❌ Tbody não encontrado');
        return;
    }
    tbody.innerHTML = '';
    // Always use inventoryData as received from backend
    inventoryData.forEach(item => {
// Utility to add new item at the top
// Utility to add new item (no local unshift, always reload from backend)
function addItemLocally(newItem) {
    loadInventory();
}
        const tr = document.createElement('tr');
        tr.setAttribute('data-id', item.id);

        // Nome
        const tdNome = document.createElement('td');
        tdNome.textContent = item.nome;
        tr.appendChild(tdNome);

        // Quantidade (number + arrows in same cell)
        const tdQtd = document.createElement('td');
    const spanQtd = document.createElement('span');
    spanQtd.className = 'qtd-display';
    spanQtd.textContent = item.quantidade;
    tdQtd.appendChild(spanQtd);

    // Arrows inside same td, with spacing
    const qtdControls = document.createElement('span');
    qtdControls.className = 'qtd-controls';
    qtdControls.style.display = window.INVENTORY_LOCKED ? 'none' : 'inline-block';
    qtdControls.style.marginLeft = '0.75em';
    const btnUp = document.createElement('button');
    btnUp.className = 'btn-up btn-icon';
    btnUp.textContent = '↑';
    btnUp.style.marginLeft = '0.25em';
    btnUp.onclick = function(e) { e.stopPropagation(); changeQuantity(item.id, 1); };
    qtdControls.appendChild(btnUp);
    const btnDown = document.createElement('button');
    btnDown.className = 'btn-down btn-icon';
    btnDown.textContent = '↓';
    btnDown.style.marginLeft = '0.25em';
    btnDown.onclick = function(e) { e.stopPropagation(); changeQuantity(item.id, -1); };
    qtdControls.appendChild(btnDown);
    tdQtd.appendChild(qtdControls);
        tr.appendChild(tdQtd);
            // Observações
            const tdObs = document.createElement('td');
            tdObs.textContent = item.observacoes || '-';
            tr.appendChild(tdObs);

        // Opções
        const tdOptions = document.createElement('td');
        const btnOptions = document.createElement('button');
        btnOptions.className = 'button small options-btn';
        btnOptions.textContent = 'Opções';
        btnOptions.onclick = function(e) { e.stopPropagation(); toggleOptions(btnOptions); };
        tdOptions.appendChild(btnOptions);

        const spanActions = document.createElement('span');
        spanActions.className = 'options-actions';
        spanActions.style.display = 'none';
        const btnEdit = document.createElement('button');
        btnEdit.className = 'button small edit-btn';
        btnEdit.textContent = 'Editar';
        btnEdit.onclick = function(e) { e.stopPropagation(); editItem(item.id); };
        spanActions.appendChild(btnEdit);
        const btnDelete = document.createElement('button');
        btnDelete.className = 'button small delete-btn';
        btnDelete.textContent = 'Excluir';
        btnDelete.onclick = function(e) { e.stopPropagation(); deleteItem(item.id); };
        spanActions.appendChild(btnDelete);
        tdOptions.appendChild(spanActions);
        tr.appendChild(tdOptions);

        tbody.appendChild(tr);
        });
        highlightLowQuantity(); // Highlight low quantity after rendering
        console.log('🔨 Tabela renderizada com', inventoryData.length, 'itens');
}

    // Highlight low quantity in .qtd-display (only the number, not buttons/icons)
    function highlightLowQuantity() {
        document.querySelectorAll('.qtd-display').forEach(el => {
            const val = parseInt(el.textContent, 10);
            if (!isNaN(val) && val < 6) {
                el.classList.add('low-quantity');
            } else {
                el.classList.remove('low-quantity');
            }
        });
    }

// Alterar quantidade de um item
async function changeQuantity(id, delta) {
    try {
        console.log(`📊 Alterando quantidade: ID=${id}, Delta=${delta}`);
        const response = await fetch(`/inventory/${id}/quantity`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ delta: delta })
        });
        if (response.ok) {
            console.log('✅ Quantidade atualizada com sucesso');
            await loadInventory(); // Recarregar dados para persistir
        } else {
            const errorData = await response.json();
            console.error('❌ Erro na atualização:', errorData);
        }
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        // Atualização local como fallback
        const item = inventoryData.find(i => i.id == id);
        if (item) {
            item.quantidade = Math.max(0, item.quantidade + delta);
            renderInventory();
            highlightLowQuantity(); // Ensure highlight updates after local change
            console.log('🔄 Atualização local aplicada');
        }
    }
}

// ...existing code...

// Editar item
function editItem(id) {
    const item = inventoryData.find(i => i.id == id);
    if (!item) {
        alert('Item não encontrado.');
        return;
    }
    let modal = document.getElementById('edit-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'edit-modal';
        modal.innerHTML = `
            <div style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;">
                <form id="edit-form" style="background:#fff;padding:2em;border-radius:8px;min-width:300px;">
                    <h2>Editar Item</h2>
                    <label>Nome:<br><input type="text" name="nome" value="${item.nome}" required></label><br><br>
                    <label>Quantidade:<br><input type="number" name="quantidade" value="${item.quantidade}" required></label><br><br>
                    <label>Observações:<br><input type="text" name="observacoes" value="${item.observacoes || ''}"></label><br><br>
                    <button type="submit" class="button primary">Salvar</button>
                    <button type="button" id="cancel-edit" class="button">Cancelar</button>
                </form>
            </div>
        `;
        document.body.appendChild(modal);
    }
    modal.style.display = 'block';
    document.getElementById('cancel-edit').onclick = function () {
        modal.style.display = 'none';
        modal.remove();
    };
    document.getElementById('edit-form').onsubmit = function (e) {
        e.preventDefault();
        showStatus('Salvando...', true);
        const formData = new FormData(e.target);
        const payload = {
            nome: formData.get('nome'),
            quantidade: parseInt(formData.get('quantidade'), 10),
            observacoes: formData.get('observacoes')
        };
        fetch(`/inventory/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(json => {
            if (json.success) {
                Object.assign(item, json.data);
                renderInventory();
                showStatus(json.message, true);
                modal.style.display = 'none';
                modal.remove();
            } else {
                showStatus(json.message, false);
            }
        })
        .catch(() => {
            showStatus('Erro ao salvar.', false);
        });
    };
}

// Excluir item
function deleteItem(id) {
    if (!confirm('Tem certeza que deseja excluir este item?')) return;
    showStatus('Excluindo...', true);
    fetch(`/inventory/${id}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(json => {
        if (json.success) {
            inventoryData = inventoryData.filter(i => i.id != id);
            renderInventory();
            showStatus(json.message, true);
        } else {
            showStatus(json.message, false);
        }
    })
    .catch(() => {
        showStatus('Erro ao excluir.', false);
    });
}

// Status bar helper
function showStatus(message, success = true) {
    let bar = document.getElementById('status-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'status-bar';
        bar.style.position = 'fixed';
        bar.style.bottom = '0';
        bar.style.left = '0';
        bar.style.width = '100%';
        bar.style.padding = '10px';
        bar.style.background = success ? '#4caf50' : '#f44336';
        bar.style.color = '#fff';
        bar.style.textAlign = 'center';
        bar.style.zIndex = '9999';
        document.body.appendChild(bar);
    }
    bar.textContent = message;
    setTimeout(() => { bar.remove(); }, 3000);
}

// ...existing code...

// Locker controls logic
function updateLockerControls() {
    document.querySelectorAll('.qtd-controls').forEach(ctrl => {
        ctrl.style.display = window.INVENTORY_LOCKED ? 'none' : 'inline-block';
    });
}

// Options toggle logic
function toggleOptions(btn) {
    // Only show/hide .options-actions inside the Opções column for this row
    var actions = btn.parentElement.querySelector('.options-actions');
    if (actions) {
        actions.style.display = (actions.style.display === 'none' || actions.style.display === '') ? 'inline-block' : 'none';
    }
}

// Locker toggle
function toggleLockMode() {
    window.INVENTORY_LOCKED = !window.INVENTORY_LOCKED;
    document.getElementById('lock-icon').style.display = window.INVENTORY_LOCKED ? 'inline' : 'none';
    document.getElementById('edit-icon').style.display = window.INVENTORY_LOCKED ? 'none' : 'inline';
    updateLockerControls();
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM PRONTO - inicializando inventário');
    setTimeout(() => {
        loadInventory();
    }, 500);
    // Locker button
    document.getElementById('lock-toggle').onclick = toggleLockMode;
    // No need for event delegation, all handlers are attached in renderInventory
    updateLockerControls();
});
