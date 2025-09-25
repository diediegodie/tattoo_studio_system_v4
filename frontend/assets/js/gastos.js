// gastos.js
// Handle gastos page interactions

// Safe feature-detect the shared utilities
const domHelpers = (typeof window !== 'undefined' && window.domHelpers) ? window.domHelpers : null;

// Function to get status helper
function getStatusHelper() {
  return typeof window.showStatus === 'function' ? window.showStatus : function (msg, ok) {
    try {
      if (ok) {
        if (window.notifySuccess) window.notifySuccess(msg);
      } else {
        if (window.notifyError) window.notifyError(msg);
      }
    } catch(e){ console.log(msg); }
  };
}

// Async confirm helper
// Options toggle logic - removed local function, using global window.toggleOptions

// Edit gasto modal
async function editGasto(id) {
  if (!id) return console.warn('editGasto called without id');

  getStatusHelper()('Processando...', true);

  try {
    const r = await fetch(`/gastos/api/${id}`, { headers: { 'Accept': 'application/json' } });
    const res = await r.json();

    if (!res || !res.success) {
      const msg = (res && res.message) || 'Não foi possível concluir a ação. Tente novamente.';
      getStatusHelper()(msg, false);
      return;
    }

    const g = res.data;

    // Build modal content
    const modalContent = `
      <form id="gastos-edit-form">
        <label>Data:<br><input type="date" name="data" required></label><br><br>
        <label>Valor (R$):<br><input type="number" step="0.01" name="valor" required></label><br><br>
        <label>Descrição:<br><input type="text" name="descricao" required></label><br><br>
        <label>Forma de pagamento:<br>
          <select name="forma_pagamento" id="gastos-edit-forma_pagamento" required>
            <option value="">Selecione...</option>
            <option value="Dinheiro">Dinheiro</option>
            <option value="Pix">Pix</option>
            <option value="Cartão de Crédito">Cartão de Crédito</option>
            <option value="Cartão de Débito">Cartão de Débito</option>
            <option value="Cheque">Cheque</option>
            <option value="Transferência">Transferência</option>
          </select>
        </label><br><br>
      </form>
    `;

    // Use unified modal system
    openCustomModal({
      title: 'Editar Gasto',
      content: modalContent,
      showConfirm: true,
      showCancel: true,
      confirmText: 'Salvar',
      cancelText: 'Cancelar',
      onConfirm: function() {
        console.log('[DEBUG] gastos.js onConfirm triggered for expense edit');
        const form = document.querySelector('#gastos-edit-form');
        if (form) {
          console.log('[DEBUG] Found form, dispatching submit event');
          const submitEvent = new Event('submit', { cancelable: true });
          form.dispatchEvent(submitEvent);
        } else {
          console.error('[DEBUG] Form not found for expense edit');
        }
      },
      onCancel: null,
      closeOnConfirm: false, // Don't close on confirm, let form handler do it
      closeOnCancel: true
    });

    // Get the form after modal is created and prefill values
    const form = document.querySelector('#gastos-edit-form');
    form.elements['data'].value = g.data || '';
    form.elements['valor'].value = g.valor || '';
    form.elements['descricao'].value = g.descricao || '';
    form.elements['forma_pagamento'].value = g.forma_pagamento || '';

    form.onsubmit = async function (e) {
      e.preventDefault();
      getStatusHelper()('Processando...', true);

      const formData = new FormData(form);
      const payload = {
        data: formData.get('data'),
        valor: formData.get('valor'),
        descricao: formData.get('descricao'),
        forma_pagamento: formData.get('forma_pagamento'),
      };

      try {
        const r = await fetch(`/gastos/api/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload),
        });
        const updated = await r.json();

        if (updated && updated.success) {
          // Update DOM row
          const row = document.querySelector(`tr[data-id='${id}']`);
          if (row) {
            const cols = row.querySelectorAll('td');
            if (cols && cols.length >= 5) {
              cols[0].textContent = payload.data ? new Date(payload.data).toLocaleDateString('pt-BR') : '-';
              cols[1].textContent = 'R$ ' + Number(payload.valor).toFixed(2);
              cols[2].textContent = payload.descricao;
              cols[3].textContent = payload.forma_pagamento;
            }
          }
          getStatusHelper()('Ação concluída com sucesso.', true);
          closeModal();
        } else {
          getStatusHelper()((updated && updated.message) || 'Não foi possível concluir a ação. Tente novamente.', false);
        }
      } catch (err) {
        console.error('editGasto save error', err);
        getStatusHelper()('Falha de conexão. Verifique sua internet e tente novamente.', false);
      }
    };

  } catch (err) {
    console.error('editGasto error', err);
    getStatusHelper()('Não foi possível concluir a ação. Tente novamente.', false);
  }
}

// Delete gasto
async function deleteGasto(id) {
  if (!id) return console.warn('deleteGasto called without id');

  console.log('[DEBUG] deleteGasto called with id:', id);
  if (!(await window.confirmAction('Tem certeza que deseja excluir este gasto?'))) {
    console.log('[DEBUG] deleteGasto cancelled by user');
    return;
  }

  console.log('[DEBUG] deleteGasto proceeding with deletion for id:', id);
  getStatusHelper()('Processando...', true);

  try {
    const r = await fetch(`/gastos/api/${id}`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' },
    });
    const res = await r.json();

    if (res && res.success) {
      // Remove row from DOM
      const row = document.querySelector(`tr[data-id='${id}']`);
      if (row) {
        row.remove();
      }
      getStatusHelper()('Ação concluída com sucesso.', true);
      try { if (typeof closeModal === 'function') closeModal(); } catch(e) {}
    } else {
      getStatusHelper()((res && res.message) || 'Não foi possível concluir a ação. Tente novamente.', false);
    }
  } catch (err) {
    console.error('deleteGasto error', err);
    getStatusHelper()('Falha de conexão. Verifique sua internet e tente novamente.', false);
  }
}

// Initialize event listeners
// Set up event listeners - check if DOM is already loaded
function setupEventListeners() {
  console.log('[gastos] Event delegation handlers bound');

  // Use event delegation for dynamically added buttons
  document.addEventListener('click', function(e) {
    // Handle edit buttons
    const editBtn = e.target.closest('.edit-gasto-btn');
    if (editBtn) {
      e.preventDefault();
      e.stopPropagation();
      const id = editBtn.dataset.id || editBtn.getAttribute('data-id');
      if (!id) {
        console.warn('[gastos] No data-id found for edit button');
        return;
      }
      editGasto(id);
      return;
    }

    // Handle delete buttons
    const delBtn = e.target.closest('.delete-gasto-btn');
    if (delBtn) {
      e.preventDefault();
      e.stopPropagation();
      const id = delBtn.dataset.id || delBtn.getAttribute('data-id');
      if (!id) {
        console.warn('[gastos] No data-id found for delete button');
        return;
      }
      deleteGasto(id);
      return;
    }
  });
}

// Set up event listeners immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  document.addEventListener('DOMContentLoaded', setupEventListeners);
} else {
  setupEventListeners();
}
