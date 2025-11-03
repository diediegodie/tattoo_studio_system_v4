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
    
    // Aplica estado de lock aos controles (oculta se bloqueado)
    const isLocked = window.INVENTORY_LOCKED === true;
    if (isLocked) {
        qtdControls.classList.add('hidden-with-margin');
    }
    
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
        btnOptions.onclick = function(e) { e.stopPropagation(); window.toggleOptions(btnOptions); };
        tdOptions.appendChild(btnOptions);

        const spanActions = document.createElement('span');
        spanActions.className = 'options-actions';
        // Removed inline style.display = 'none' - using CSS class instead
        const btnEdit = document.createElement('button');
        btnEdit.className = 'button small edit-item-btn';
        btnEdit.textContent = 'Editar';
        btnEdit.onclick = function(e) { e.stopPropagation(); editItem(item.id); };
        spanActions.appendChild(btnEdit);
        const btnDelete = document.createElement('button');
        btnDelete.className = 'button small delete-item-btn';
        btnDelete.textContent = 'Excluir';
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
    console.log('[DEBUG] editItem called with id:', id);
    const item = inventoryData.find(i => i.id == id);
    console.log('[DEBUG] Found item:', item);
    
    if (!item) {
        console.error('[DEBUG] Item not found in inventoryData');
        if (window.showToast) window.showToast('Item não encontrado.', 'error');
        return;
    }

    // Create form content for unified modal
    const formContent = `
        <form id="edit-form">
            <label>Nome:<br><input type="text" name="nome" value="${item.nome}" required></label><br><br>
            <label>Quantidade:<br><input type="number" name="quantidade" value="${item.quantidade}" required></label><br><br>
            <label>Observações:<br><input type="text" name="observacoes" value="${item.observacoes || ''}"></label><br><br>
        </form>
    `;

    console.log('[DEBUG] Checking if window.openCustomModal is available:', typeof window.openCustomModal);
    
    // Check if modal system is available
    if (typeof window.openCustomModal !== 'function') {
        console.error('[ERROR] window.openCustomModal is not available! Modal.js may not be loaded.');
        alert('Sistema de modal não disponível. Recarregue a página.');
        return;
    }

    console.log('[DEBUG] Opening custom modal for edit...');
    
    // Open modal with unified system
    window.openCustomModal({
        title: 'Editar Item',
        content: formContent,
        confirmText: 'Salvar',
        cancelText: 'Cancelar',
        onConfirm: async function() {
            const form = document.getElementById('edit-form');
            if (!form) return;

            window.notifySuccess('Salvando...');
            const formData = new FormData(form);
            const payload = {
                nome: formData.get('nome'),
                quantidade: parseInt(formData.get('quantidade'), 10),
                observacoes: formData.get('observacoes')
            };

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
                    window.notifySuccess(json.message);
                        window.closeModal();
                } else {
                    const msg = (json && json.message) || 'Erro ao salvar.';
                    window.notifyError(msg);
                }
            } catch (err) {
                const msg = (err && err.payload && err.payload.message) || 'Erro ao salvar.';
                window.notifyError(msg);
            }
        }
    });
}

// Excluir item
async function deleteItem(id) {
    console.log('[DEBUG] deleteItem called with id:', id);
    // Use unified modal system for consistency (require it)
    if (typeof window.confirmAction === 'function') {
        console.log('[DEBUG] inventory.deleteItem delegating to window.confirmAction with id:', id);
        const confirmed = await window.confirmAction('Tem certeza que deseja excluir este item?');
        console.log('[DEBUG] User confirmation result for item deletion:', confirmed);
        if (!confirmed) {
            console.log('[DEBUG] inventory.deleteItem cancelled by user');
            return;
        }
    } else {
        console.error('[DEBUG] window.confirmAction not available in inventory.js — refusing to proceed with deletion for id:', id);
        return;
    }

    console.log('[DEBUG] Proceeding with item deletion, id:', id);
    window.notifySuccess('Excluindo...');
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
                console.log('[DEBUG] Item deletion successful, id:', id, 'response:', json);
                // Prefer DOM removal for minimal reflow when possible
                const removed = domHelpers && typeof domHelpers.removeRowById === 'function'
                    ? domHelpers.removeRowById('.table-wrapper table', id)
                    : false;

                if (!removed) {
                    inventoryData = inventoryData.filter(i => i.id != id);
                    renderInventory();
                }
                    window.notifySuccess(json.message);
                        try { if (typeof window.closeModal === 'function') window.closeModal(); } catch(e) {}
            } else {
                console.error('[DEBUG] Item deletion failed, id:', id, 'response:', json);
                const msg = (json && json.message) || 'Erro ao excluir.';
                window.notifyError(msg);
            }
        } catch (err) {
            const msg = (err && err.payload && err.payload.message) || 'Erro ao excluir.';
            window.notifyError(msg);
        }
    })();
}

// Status bar helper - removed local function, using global window.notifySuccess/window.notifyError

// ...existing code...

// ====================================
// LOCK/UNLOCK CONTROLS - Refatorado
// ====================================
/**
 * Atualiza a visibilidade dos controles de quantidade (+/-) baseado no estado de lock
 * Quando locked: esconde os controles
 * Quando unlocked: mostra os controles
 */
function updateLockerControls() {
    const isLocked = window.INVENTORY_LOCKED === true;
    
    // Toggle qty controls visibility
    document.querySelectorAll('.qtd-controls').forEach(ctrl => {
        if (isLocked) {
            ctrl.classList.add('hidden-with-margin');
        } else {
            ctrl.classList.remove('hidden-with-margin');
        }
    });
    
    console.log(`🔒 Controles atualizados: ${isLocked ? 'BLOQUEADO' : 'DESBLOQUEADO'}`);
}

/**
 * Alterna entre modo bloqueado e desbloqueado
 * Atualiza ícones e controles de quantidade
 */
function toggleLockMode() {
    // Toggle state
    window.INVENTORY_LOCKED = !window.INVENTORY_LOCKED;
    const isLocked = window.INVENTORY_LOCKED;
    
    // Update icons
    const lockIcon = document.getElementById('lock-icon');
    const editIcon = document.getElementById('edit-icon');
    
    if (lockIcon) {
        if (isLocked) {
            lockIcon.classList.remove('hidden');
        } else {
            lockIcon.classList.add('hidden');
        }
    }
    
    if (editIcon) {
        if (isLocked) {
            editIcon.classList.add('hidden');
        } else {
            editIcon.classList.remove('hidden');
        }
    }
    
    // Update quantity controls
    updateLockerControls();
    
    console.log(`🔓 Lock toggle: Agora ${isLocked ? 'BLOQUEADO' : 'DESBLOQUEADO'}`);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM PRONTO - inicializando inventário');
    setTimeout(() => {
        loadInventory();
    }, 500);
    // Locker button
    const lockToggle = document.getElementById('lock-toggle');
    if (lockToggle) lockToggle.onclick = toggleLockMode;
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
    // Delegate clicks for edit and delete buttons (options handled globally in common.js)
    document.addEventListener('click', function(e) {
        console.log('[INVENTORY] Click detected on:', e.target, 'with classes:', e.target.className);
        
        const editBtn = e.target.closest('.edit-item-btn');
        if (editBtn) {
            console.log('[INVENTORY] ✅ Edit button detected:', editBtn);
            e.preventDefault();
            e.stopPropagation();
            const row = editBtn.closest('tr');
            const id = row ? row.getAttribute('data-id') : editBtn.getAttribute('data-id');
            console.log('[INVENTORY] Row:', row, 'ID:', id);
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
    // ====================================
    // INICIALIZAÇÃO DO ESTADO DE LOCK
    // ====================================
    // Sempre inicializa como BLOQUEADO (true) por segurança
    window.INVENTORY_LOCKED = true;
    console.log('🔐 Estado inicial: BLOQUEADO (inventory locked)');
    
    // Sincroniza ícones com estado inicial
    const lockIconInit = document.getElementById('lock-icon');
    const editIconInit = document.getElementById('edit-icon');
    
    if (lockIconInit) {
        // Lock icon visível quando bloqueado
        lockIconInit.classList.remove('hidden');
    }
    
    if (editIconInit) {
        // Edit icon escondido quando bloqueado
        editIconInit.classList.add('hidden');
    }
    
    // Aplica estado aos controles de quantidade
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
