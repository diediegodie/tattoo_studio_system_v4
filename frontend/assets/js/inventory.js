// INVENTORY.JS - VERSÃO RESTAURADA COM FUNCIONALIDADES COMPLETAS
console.log('📂 INVENTORY.JS CARREGADO');

let inventoryData = [];
// Generic resource client for inventory
try {
    var inventoryClient = typeof makeResourceClient === 'function' ? makeResourceClient('/inventory') : null;
} catch (e) {
    console.error('makeResourceClient not available', e);
    var inventoryClient = null;
}
// domHelpers namespace (optional)
var domHelpers = typeof window !== 'undefined' && window.domHelpers ? window.domHelpers : null;

// Carregar dados do inventário
async function loadInventory() {
    try {
        console.log('📋 Carregando inventário...');
        if (inventoryClient && typeof inventoryClient.getAll === 'function') {
            inventoryData = await inventoryClient.getAll();
        } else {
            const response = await fetch('/inventory/', { credentials: 'same-origin' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            inventoryData = await response.json();
        }
    // Backend provides authoritative ordering; render as received
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
        btnEdit.className = 'button small edit-item-btn';
        btnEdit.textContent = 'Editar';
        btnEdit.onclick = function(e) { e.stopPropagation(); editItem(item.id); };
        spanActions.appendChild(btnEdit);
        const btnDelete = document.createElement('button');
        btnDelete.className = 'button small delete-item-btn';
        btnDelete.textContent = 'Excluir';
        btnDelete.onclick = function(e) { e.stopPropagation(); deleteItem(item.id); };
        spanActions.appendChild(btnDelete);
        tdOptions.appendChild(spanActions);
        tr.appendChild(tdOptions);

    // Append rows in order of inventoryData (already sorted newest-first)
    tbody.appendChild(tr);
        });
        highlightLowQuantity(); // Highlight low quantity after rendering
        console.log('🔨 Tabela renderizada com', inventoryData.length, 'itens');
}

// Utility to add a newly created item locally at the top without full reload
function addItemLocally(newItem) {
    // Do not manipulate client-side ordering; reload authoritative data from server
    // This ensures both estoque and drag_drop pages display identical order
    loadInventory();
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
    console.log(`📊 Alterando quantidade: ID=${id}, Delta=${delta}`);
    // Update local state
    const item = inventoryData.find(i => i.id == id);
    if (item) {
        item.quantidade = Math.max(0, item.quantidade + delta);
    }
    // Update only the DOM for this row
    const row = document.querySelector(`tr[data-id='${id}']`);
    if (row) {
        const qtdDisplay = row.querySelector('.qtd-display');
        if (qtdDisplay) {
            qtdDisplay.textContent = item ? item.quantidade : qtdDisplay.textContent;
        }
    }
    // Reapply highlighting
    highlightLowQuantity();
    // Sync with backend
    try {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
        const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
        if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
        const response = await fetch(`/inventory/${id}/quantity`, {
            method: 'PATCH',
            headers: headers,
            credentials: 'same-origin',
            body: JSON.stringify({ delta: delta })
        });
        if (response.ok) {
            console.log('✅ Quantidade atualizada com sucesso');
        } else {
            const errorData = await response.json();
            console.error('❌ Erro na atualização:', errorData);
        }
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
    }
}

// ...existing code...

// Editar item
function editItem(id) {
    const item = inventoryData.find(i => i.id == id);
    if (!item) {
        if (window.showToast) window.showToast('Item não encontrado.', 'error');
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
        (async function () {
            try {
                let json;
                if (inventoryClient && typeof inventoryClient.update === 'function') {
                    json = await inventoryClient.update(id, payload);
                } else {
                    const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
                    const headers = { 'Content-Type': 'application/json' };
                    if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
                    const res = await fetch(`/inventory/${id}`, {
                        method: 'PUT',
                        headers: headers,
                        credentials: 'same-origin',
                        body: JSON.stringify(payload)
                    });
                    json = await res.json();
                }

                // api_response returns { success, message, data }
                if (json && json.success) {
                    Object.assign(item, json.data);
                    renderInventory();
                    showStatus(json.message, true);
                    modal.style.display = 'none';
                    modal.remove();
                } else {
                    const msg = (json && json.message) || 'Erro ao salvar.';
                    showStatus(msg, false);
                }
            } catch (err) {
                const msg = (err && err.payload && err.payload.message) || 'Erro ao salvar.';
                showStatus(msg, false);
            }
        })();
    };
}

// Excluir item
function deleteItem(id) {
    // use async confirm helper if available
    if (typeof window.confirm === 'function') {
        if (!window.confirm('Tem certeza que deseja excluir este item?')) return;
    }
    showStatus('Excluindo...', true);
    (async function () {
        try {
            let json;
                if (inventoryClient && typeof inventoryClient.delete === 'function') {
                json = await inventoryClient.delete(id);
            } else {
                const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
                const headers = {};
                if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
                const res = await fetch(`/inventory/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
                json = await res.json();
            }

            if (json && json.success) {
                // Prefer DOM removal for minimal reflow when possible
                const removed = domHelpers && typeof domHelpers.removeRowById === 'function'
                    ? domHelpers.removeRowById('.table-wrapper table', id)
                    : false;

                if (!removed) {
                    inventoryData = inventoryData.filter(i => i.id != id);
                    renderInventory();
                }
                showStatus(json.message, true);
            } else {
                const msg = (json && json.message) || 'Erro ao excluir.';
                showStatus(msg, false);
            }
        } catch (err) {
            const msg = (err && err.payload && err.payload.message) || 'Erro ao excluir.';
            showStatus(msg, false);
        }
    })();
}

// Status bar helper
function showStatus(message, success = true) {
    // Thin wrapper: delegate to the global toast. Keep minimal fallback.
    try {
        if (window.showToast) {
            window.showToast(message, success ? 'success' : 'error', 8000);
            return;
        }
    } catch (e) {
        console.error('Error calling global showToast', e);
    }
    // Extremely minimal fallback: alert so messages are never silently lost.
    try { alert(message); } catch (e) { console.error('Fallback alert failed', e); }
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
    // Delegate clicks for quantity buttons (works for server-rendered and JS-rendered rows)
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-up, .btn-down');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        const delta = parseInt(btn.getAttribute('data-delta') || '0', 10);
        if (id && delta !== 0) {
            console.log(`🔢 Botão quantidade clicado: ID=${id}, Delta=${delta}`);
            changeQuantity(id, delta);
        }
    });
    // Delegate clicks for options, edit, and delete buttons
    document.addEventListener('click', function(e) {
        const optionsBtn = e.target.closest('.options-btn');
        if (optionsBtn) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔽 Botão opções clicado');
            toggleOptions(optionsBtn);
            return;
        }
        const editBtn = e.target.closest('.edit-item-btn');
        if (editBtn) {
            e.preventDefault();
            e.stopPropagation();
            const row = editBtn.closest('tr');
            const id = row ? row.getAttribute('data-id') : editBtn.getAttribute('data-id');
            if (id) {
                console.log(`✏️ Botão editar clicado: ID=${id}`);
                editItem(id);
            } else {
                console.error('❌ ID não encontrado para botão editar');
            }
            return;
        }
        const deleteBtn = e.target.closest('.delete-item-btn');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const row = deleteBtn.closest('tr');
            const id = row ? row.getAttribute('data-id') : deleteBtn.getAttribute('data-id');
            if (id) {
                console.log(`🗑️ Botão excluir clicado: ID=${id}`);
                deleteItem(id);
            } else {
                console.error('❌ ID não encontrado para botão excluir');
            }
            return;
        }
    });
    updateLockerControls();

    // Intercept add item form (on /estoque/novo) and submit via fetch to insert locally
    const addForm = document.getElementById('addItemForm');
    if (addForm) {
        addForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const formData = new FormData(addForm);
            const payload = {
                nome: formData.get('nome'),
                quantidade: parseInt(formData.get('quantidade') || '0', 10),
                observacoes: formData.get('observacoes')
            };
            try {
                const res = await fetch('/inventory/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.status === 201) {
                    const created = await res.json();
                    // Add locally at top and navigate back to estoque page
                    addItemLocally(created);
                    window.location.href = '/estoque';
                } else {
                    // Fallback: let the form submit normally to preserve behavior
                    addForm.submit();
                }
            } catch (err) {
                console.error('Erro ao enviar novo item via AJAX', err);
                addForm.submit();
            }
        });
    }
});
