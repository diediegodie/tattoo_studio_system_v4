(function (window) {
  'use strict';

  // HISTORICO.JS - Handle payments and commissions on historico page
  // Session buttons are handled by sessoes.js
  const domHelpers = window.domHelpers || null;
  const financeiro = window.financeiroHelpers || null;

  // Promise-based confirmation modal fallback using native confirm if no custom UI
  function confirmAction(message) {
    if (typeof window.confirm === 'function') {
      return Promise.resolve(window.confirm(message));
    }
    return Promise.resolve(true);
  }

  async function editPagamentoHandler(id) {
    if (!id) return;
    if (financeiro && typeof financeiro.editPagamento === 'function') {
      financeiro.editPagamento(id);
      return;
    }
    // Fallback: redirect to edit page
    window.location.href = `/financeiro/editar-pagamento/${id}`;
  }

  async function deletePagamentoHandler(id) {
    if (!id) return;
    // Reuse financeiro delete which asks confirmation inside
    if (financeiro && typeof financeiro.deletePagamento === 'function') {
      financeiro.deletePagamento(id);
      return;
    }
    if (!(await confirmAction('Tem certeza que deseja excluir este pagamento?'))) return;
    // Fallback: submit form
    try {
      const headers = { 'Accept': 'application/json' };
      const r = await fetch(`/financeiro/api/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
      if (r.ok) {
        const json = await r.json();
        if (json && json.success) {
          domHelpers && domHelpers.removeRowById(null, id);
          if (window.showToast) window.showToast('Pagamento excluído.', 'success');
        } else {
          if (window.showToast) window.showToast(json.message || 'Erro ao excluir pagamento.', 'error');
        }
      } else {
        if (window.showToast) window.showToast('Erro ao excluir pagamento.', 'error');
      }
    } catch (e) {
      console.error(e);
      if (window.showToast) window.showToast('Erro ao excluir pagamento.', 'error');
    }
  }

  async function editComissaoHandler(id) {
    if (!id) return;
    // Try to fetch commission data and open a modal similar to financeiro/sessoes
    try {
      const headers = { 'Accept': 'application/json' };
      const r = await fetch(`/historico/api/comissao/${id}`, { headers: headers, credentials: 'same-origin' });
      if (!r.ok) {
        if (window.showToast) window.showToast('Falha ao carregar comissão.', 'error');
        return;
      }
      const payload = await r.json();
      if (!payload || !payload.success) {
        if (window.showToast) window.showToast(payload.message || 'Falha ao carregar comissão.', 'error');
        return;
      }
      const c = payload.data;

      // Build a small modal reusing modal styles
      let modal = document.getElementById('historico-comissao-edit-modal');
      if (!modal) {
        modal = document.createElement('div');
        modal.id = 'historico-comissao-edit-modal';
        modal.innerHTML = `
          <div class="modal-overlay">
            <div class="modal-container">
              <div class="modal-scrollable">
                <h2>Editar Comissão</h2>
                <form id="historico-comissao-edit-form">
                  <label>Percentual:<br><input type="number" step="0.01" name="percentual" required></label><br><br>
                  <label>Valor:<br><input type="number" step="0.01" name="valor" required></label><br><br>
                  <label>Observações:<br><textarea name="observacoes"></textarea></label><br><br>
                </form>
              </div>
              <div class="modal-footer">
                <button type="submit" form="historico-comissao-edit-form" class="button primary">Salvar</button>
                <button type="button" id="historico-comissao-cancel" class="button">Cancelar</button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modal);
      }

      const form = modal.querySelector('#historico-comissao-edit-form');
      form.elements['percentual'].value = c.percentual || '';
      form.elements['valor'].value = c.valor || '';
      form.elements['observacoes'].value = c.observacoes || '';

      modal.style.display = 'block';
      modal.querySelector('#historico-comissao-cancel').onclick = function () { modal.remove(); };

      form.onsubmit = async function (e) {
        e.preventDefault();
        const fd = new FormData(form);
        const payload = {
          percentual: fd.get('percentual'),
          valor: fd.get('valor'),
          observacoes: fd.get('observacoes'),
        };

        try {
          const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
          const res = await fetch(`/historico/api/comissao/${id}`, {
              method: 'PUT',
              headers: headers,
              credentials: 'same-origin',
              body: JSON.stringify(payload),
            });
          const data = await res.json();
          if (data && data.success) {
            // Update row values in-place if present
            const row = document.querySelector(`tr[data-id="com-${id}"]`);
            if (row) {
              const cols = row.querySelectorAll('td');
              if (cols && cols.length >= 6) {
                cols[4].textContent = 'R$ ' + Number(data.data.valor).toFixed(2);
                cols[5].textContent = data.data.observacoes || '';
              }
            }
            if (window.showToast) window.showToast('Comissão atualizada.', 'success');
            modal.remove();
          } else {
            if (window.showToast) window.showToast((data && data.message) || 'Erro ao atualizar comissão.', 'error');
          }
        } catch (err) {
          console.error(err);
          if (window.showToast) window.showToast('Erro ao atualizar comissão.', 'error');
        }
      };
    } catch (e) {
      console.error(e);
      if (window.showToast) window.showToast('Erro ao carregar comissão.', 'error');
    }
  }

  async function deleteComissaoHandler(id) {
    if (!id) return;
    if (!(await confirmAction('Tem certeza que deseja excluir esta comissão?'))) return;
    try {
      const headers = { 'Accept': 'application/json' };
      const r = await fetch(`/historico/api/comissao/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
      const data = await r.json();
      if (data && data.success) {
        domHelpers && domHelpers.removeRowById(null, `com-${id}`);
        if (window.showToast) window.showToast('Comissão excluída.', 'success');
      } else {
        if (window.showToast) window.showToast((data && data.message) || 'Erro ao excluir comissão.', 'error');
      }
    } catch (e) {
      console.error(e);
      if (window.showToast) window.showToast('Erro ao excluir comissão.', 'error');
    }
  }

  // Attach handlers on DOMContentLoaded - Use event delegation for dynamic buttons
  document.addEventListener('DOMContentLoaded', function () {
    // Prevent multiple attachments if this script is executed more than once
    if (document.body._historicoBound) return;
    document.body._historicoBound = true;

    console.log('[historico] Event delegation handlers bound');

    // Use event delegation to handle dynamically added buttons
    document.addEventListener('click', function(e) {
      // Handle payment edit buttons
      const editPagBtn = e.target.closest('.edit-pagamento-btn');
      if (editPagBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = editPagBtn.dataset.id || editPagBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[historico] No data-id found for payment edit button');
          return;
        }
        editPagamentoHandler(id);
        return;
      }

      // Handle payment delete buttons
      const delPagBtn = e.target.closest('.delete-pagamento-btn');
      if (delPagBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = delPagBtn.dataset.id || delPagBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[historico] No data-id found for payment delete button');
          return;
        }
        deletePagamentoHandler(id);
        return;
      }

      // Handle commission edit buttons
      const editComBtn = e.target.closest('.edit-comissao-btn');
      if (editComBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = editComBtn.dataset.id || editComBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[historico] No data-id found for commission edit button');
          return;
        }
        editComissaoHandler(id);
        return;
      }

      // Handle commission delete buttons
      const delComBtn = e.target.closest('.delete-comissao-btn');
      if (delComBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = delComBtn.dataset.id || delComBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[historico] No data-id found for commission delete button');
          return;
        }
        deleteComissaoHandler(id);
        return;
      }
    });
  });

})(typeof window !== 'undefined' ? window : this);
