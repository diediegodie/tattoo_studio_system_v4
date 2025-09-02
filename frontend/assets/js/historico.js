(function (window) {
  'use strict';

  // HISTORICO.JS - Reuse existing financeiro/sessoes modal patterns for edit/delete on historico page
  const domHelpers = window.domHelpers || null;
  const financeiro = window.financeiroHelpers || null;
  const sessoes = window.sessoesHelpers || null;

  // Promise-based confirmation modal fallback using native confirm if no custom UI
  function confirmAction(message) {
    if (typeof window.confirm === 'function') {
      return Promise.resolve(window.confirm(message));
    }
    // fallback: resolve true to avoid blocking flows
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
      const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
      const headers = { 'Accept': 'application/json' };
      if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
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
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
  if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
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
          const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
          if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
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
    if (!confirmAction('Tem certeza que deseja excluir esta comissão?')) return;
    try {
      const headers = { 'Accept': 'application/json' };
      const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
      if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
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

  async function editSessaoHandler(id) {
    if (!id) return;
    if (sessoes && typeof sessoes.editSessao === 'function') {
      sessoes.editSessao(id);
      return;
    }
    // Fallback: navigate to sessao edit page if exists
    window.location.href = `/sessoes/edit/${id}`;
  }

  async function deleteSessaoHandler(id) {
    if (!id) return;
    if (!confirmAction('Tem certeza que deseja excluir esta sessão?')) return;
    if (sessoes && typeof sessoes.deleteSessao === 'function') {
      sessoes.deleteSessao(id);
      return;
    }
    try {
      const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
      const headers = { 'Accept': 'application/json' };
      if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
      const r = await fetch(`/sessoes/api/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
      const data = await r.json();
      if (data && data.success) {
        domHelpers && domHelpers.removeRowById(null, `sess-${id}`);
        if (window.showToast) window.showToast('Sessão excluída.', 'success');
      } else {
        if (window.showToast) window.showToast((data && data.message) || 'Erro ao excluir sessão.', 'error');
      }
    } catch (e) {
      console.error(e);
      if (window.showToast) window.showToast('Erro ao excluir sessão.', 'error');
    }
  }

  // Attach handlers to buttons (guard against duplicate bindings)
  document.addEventListener('DOMContentLoaded', function () {
    if (document.body._historicoHandlersAttached) return;
    document.body._historicoHandlersAttached = true;

    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        editPagamentoHandler(id);
      });
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        deletePagamentoHandler(id);
      });
    });

    document.querySelectorAll('.edit-comissao-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        editComissaoHandler(id);
      });
    });

    document.querySelectorAll('.delete-comissao-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        deleteComissaoHandler(id);
      });
    });

    document.querySelectorAll('.edit-sessao-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        editSessaoHandler(id);
      });
    });

    document.querySelectorAll('.delete-sessao-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = this.dataset.id;
        deleteSessaoHandler(id);
      });
    });
  });

})(typeof window !== 'undefined' ? window : this);
