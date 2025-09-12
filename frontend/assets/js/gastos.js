// gastos.js
// Handle gastos page interactions

// Safe feature-detect the shared utilities
const domHelpers = (typeof window !== 'undefined' && window.domHelpers) ? window.domHelpers : null;

// Function to get status helper
function getStatusHelper() {
  return typeof window.showStatus === 'function' ? window.showStatus : function (msg, ok) {
    try {
      if (window.showToast) window.showToast(msg, ok ? 'success' : 'error', 8000);
      else console.log(msg);
    } catch(e){ console.log(msg); }
  };
}

// Async confirm helper
function confirmAction(message) {
  if (typeof window.confirm === 'function') return Promise.resolve(window.confirm(message));
  return Promise.resolve(true);
}

// Options toggle logic
function toggleOptions(btn) {
  // Only show/hide .options-actions inside the Opções column for this row
  var actions = btn.parentElement.querySelector('.options-actions');
  if (actions) {
    actions.style.display = (actions.style.display === 'none' || actions.style.display === '') ? 'inline-block' : 'none';
  }
}

// Edit gasto modal
async function editGasto(id) {
  if (!id) return console.warn('editGasto called without id');

  getStatusHelper()('Carregando gasto para edição...', true);

  try {
    const r = await fetch(`/gastos/api/${id}`, { headers: { 'Accept': 'application/json' } });
    const res = await r.json();

    if (!res || !res.success) {
      const msg = (res && res.message) || 'Erro ao carregar gasto.';
      getStatusHelper()(msg, false);
      return;
    }

    const g = res.data;

    // Build modal
    let modal = document.getElementById('gastos-edit-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'gastos-edit-modal';
      modal.innerHTML = `
        <div class="modal-overlay">
          <div class="modal-container">
            <div class="modal-scrollable">
              <h2>Editar Gasto</h2>
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
            </div>
            <div class="modal-footer">
              <button type="submit" form="gastos-edit-form" class="button primary">Salvar</button>
              <button type="button" id="gastos-cancel-edit" class="button">Cancelar</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    // Prefill values
    const form = modal.querySelector('#gastos-edit-form');
    form.elements['data'].value = g.data || '';
    form.elements['valor'].value = g.valor || '';
    form.elements['descricao'].value = g.descricao || '';
    form.elements['forma_pagamento'].value = g.forma_pagamento || '';

    modal.style.display = 'block';

    modal.querySelector('#gastos-cancel-edit').onclick = function () {
      modal.style.display = 'none';
      modal.remove();
    };

    form.onsubmit = async function (e) {
      e.preventDefault();
      getStatusHelper()('Salvando...', true);

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
          getStatusHelper()('Gasto atualizado com sucesso.', true);
          modal.style.display = 'none';
          modal.remove();
        } else {
          getStatusHelper()((updated && updated.message) || 'Erro ao atualizar gasto.', false);
        }
      } catch (err) {
        console.error('editGasto save error', err);
        getStatusHelper()('Erro ao salvar gasto.', false);
      }
    };

  } catch (err) {
    console.error('editGasto error', err);
    getStatusHelper()('Erro ao carregar gasto.', false);
  }
}

// Delete gasto
async function deleteGasto(id) {
  if (!id) return console.warn('deleteGasto called without id');

  if (!(await confirmAction('Tem certeza que deseja excluir este gasto?'))) return;

  getStatusHelper()('Excluindo...', true);

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
      getStatusHelper()('Gasto excluído com sucesso.', true);
    } else {
      getStatusHelper()((res && res.message) || 'Erro ao excluir gasto.', false);
    }
  } catch (err) {
    console.error('deleteGasto error', err);
    getStatusHelper()('Erro ao excluir gasto.', false);
  }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
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
});
