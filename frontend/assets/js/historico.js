(function (window) {
  'use strict';

  // HISTORICO.JS - Handle payments and commissions on historico page
  // Session buttons are handled by sessoes.js
  const domHelpers = window.domHelpers || null;
  const financeiro = window.financeiroHelpers || null;

  // Promise-based confirmation modal fallback using native confirm if no custom UI
  async function editPagamentoHandler(id) {
    if (!id) return;
    if (financeiro && typeof financeiro.editPagamento === 'function') {
      financeiro.editPagamento(id);
      return;
    }
    // Fallback: redirect to edit page
    window.location.href = `/financeiro/editar-pagamento/${id}`;
  }

    // Unified deletion utility to standardize behavior across all delete operations
  async function performDeletion(endpoint, id, dataIdPrefix = '', successMessage = 'Ação concluída com sucesso.', errorMessage = 'Não foi possível concluir a ação. Tente novamente.') {
    console.log('[DEBUG] performDeletion called with endpoint:', endpoint, 'id:', id);
    try {
      console.log(`[historico] Attempting to delete item ${id} from ${endpoint}`);
      if (window.showToast) window.showToast('Processando...', 'info');
      const headers = { 'Accept': 'application/json' };
      const r = await fetch(endpoint, {
        method: 'DELETE',
        headers: headers,
        credentials: 'same-origin'
      });

      console.log(`[historico] Delete response status: ${r.status}`);
      console.log('[DEBUG] Delete API call completed, status:', r.status);

      if (r.ok) {
        let json;
        try {
          const responseText = await r.text();
          console.log(`[historico] Raw response: ${responseText}`);
          json = JSON.parse(responseText);
          console.log(`[historico] Parsed JSON:`, json);
        } catch (parseError) {
          console.error(`[historico] JSON parse error:`, parseError);
          if (window.showToast) window.showToast('Erro ao processar resposta do servidor.', 'error');
          return false;
        }

        if (json && json.success) {
          console.log(`[historico] Deletion successful for item ${id}`);
          // Use consistent DOM removal
          const dataId = dataIdPrefix ? `${dataIdPrefix}-${id}` : id;
          const rowElement = document.querySelector(`tr[data-id="${dataId}"]`);
          if (rowElement) {
            rowElement.remove();
            console.log(`[historico] DOM element removed: tr[data-id="${dataId}"]`);
          } else if (domHelpers && typeof domHelpers.removeRowById === 'function') {
            domHelpers.removeRowById('.table-wrapper table', dataId);
            console.log(`[historico] DOM element removed via domHelpers: ${dataId}`);
          } else {
            console.log(`[historico] Reloading page due to DOM manipulation failure`);
            window.location.reload();
          }

          if (window.notifySuccess) window.notifySuccess('Ação concluída com sucesso.');
          // Close the unified modal if it's open (caller may have left it open)
          try { if (typeof closeModal === 'function') closeModal(); } catch(e) { /* ignore */ }
          return true;
        } else {
          console.log(`[historico] Deletion failed with message: ${json?.message || 'Unknown error'}`);
          if (window.notifyError) window.notifyError('Não foi possível concluir a ação. Tente novamente.');
          return false;
        }
      } else {
        // Handle HTTP errors with more detail
        const errorText = await r.text();
        console.error(`[historico] Delete failed with HTTP ${r.status}: ${errorText}`);

        // Don't show generic error for authentication issues
        if (r.status === 302 || r.status === 401) {
          if (window.notifyError) window.notifyError('Acesso não autorizado. Faça login e tente novamente.');
          window.location.href = '/auth/login';
          return false;
        }

        if (window.showToast) window.showToast(`${errorMessage} (HTTP ${r.status})`, 'error');
        return false;
      }
    } catch (e) {
      console.error('[historico] Delete error:', e);
      if (window.notifyError) window.notifyError('Falha de conexão. Verifique sua internet e tente novamente.');
      return false;
    }
  }

  async function deletePagamentoHandler(id) {
    console.log('[DEBUG] deletePagamentoHandler called with id:', id);
    if (!id) {
      console.error('[DEBUG] No ID provided to deletePagamentoHandler');
      return;
    }

    const confirmed = await window.confirmAction('Tem certeza que deseja excluir este pagamento?');
    console.log('[DEBUG] User confirmation result:', confirmed);
    if (!confirmed) return;

    console.log('[DEBUG] Proceeding with payment deletion, id:', id);
    await performDeletion(`/financeiro/api/${id}`, id, '', 'Pagamento excluído.', 'Erro ao excluir pagamento.');
  }

  async function deleteComissaoHandler(id) {
    console.log('[DEBUG] deleteComissaoHandler called with id:', id);
    if (!id) {
      console.error('[DEBUG] No ID provided to deleteComissaoHandler');
      return;
    }

    const confirmed = await window.confirmAction('Tem certeza que deseja excluir esta comissão?');
    console.log('[DEBUG] User confirmation result:', confirmed);
    if (!confirmed) return;

    console.log('[DEBUG] Proceeding with commission deletion, id:', id);
    await performDeletion(`/historico/api/comissao/${id}`, id, 'com', 'Comissão excluída.', 'Erro ao excluir comissão.');
  }

  async function editComissaoHandler(id) {
    if (!id) return;
    // Try to fetch commission data and open a modal similar to financeiro/sessoes
    try {
      const headers = { 'Accept': 'application/json' };
      const r = await fetch(`/historico/api/comissao/${id}`, { headers: headers, credentials: 'same-origin' });
      if (!r.ok) {
        if (window.notifyError) window.notifyError('Falha ao carregar comissão.');
        return;
      }
      const payload = await r.json();
      if (!payload || !payload.success) {
        if (window.notifyError) window.notifyError(payload.message || 'Falha ao carregar comissão.');
        return;
      }
      const c = payload.data;

      // Build modal content
      const modalContent = `
        <form id="historico-comissao-edit-form">
          <label>Percentual:<br><input type="number" step="0.01" name="percentual" required></label><br><br>
          <label>Valor:<br><input type="number" step="0.01" name="valor" required></label><br><br>
          <label>Observações:<br><textarea name="observacoes"></textarea></label><br><br>
        </form>
      `;

      // Use unified modal system
      openCustomModal({
        title: 'Editar Comissão',
        content: modalContent,
        showConfirm: true,
        showCancel: true,
        confirmText: 'Salvar',
        cancelText: 'Cancelar',
        onConfirm: async function() {
          console.log('[DEBUG] historico.js onConfirm triggered for commission edit');
          const form = document.querySelector('#historico-comissao-edit-form');
          if (form) {
            console.log('[DEBUG] Found form, dispatching submit event');
            const submitEvent = new Event('submit', { cancelable: true });
            form.dispatchEvent(submitEvent);
          } else {
            console.error('[DEBUG] Form not found for commission edit');
          }
        },
        onCancel: null,
        closeOnConfirm: false, // Don't close on confirm, let form handler do it
        closeOnCancel: true
      });

      // Get the form after modal is created and prefill values
      const form = document.querySelector('#historico-comissao-edit-form');
      form.elements['percentual'].value = c.percentual || '';
      form.elements['valor'].value = c.valor || '';
      form.elements['observacoes'].value = c.observacoes || '';

      // Set up form submission handler
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
            if (window.notifySuccess) window.notifySuccess('Comissão atualizada.');
            closeModal();
          } else {
            if (window.notifyError) window.notifyError((data && data.message) || 'Erro ao atualizar comissão.');
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
    if (!(await window.confirmAction('Tem certeza que deseja excluir esta comissão?'))) return;

    await performDeletion(`/historico/api/comissao/${id}`, id, 'com', 'Comissão excluída.', 'Erro ao excluir comissão.');
  }

  // Attach handlers - check if DOM is already loaded
  function setupEventListeners() {
    // Prevent multiple attachments if this script is executed more than once
    if (document.body._historicoBound) return;
    document.body._historicoBound = true;

    console.log('[historico] Event delegation handlers bound');

    // Use event delegation to handle dynamically added buttons
    // Only handle buttons that are specific to the historico page
    document.addEventListener('click', function(e) {
      // Handle commission edit buttons (historico-specific)
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

      // Handle commission delete buttons (historico-specific)
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

      // Handle payment buttons only if we're on historico page and financeiro hasn't handled them
      // Check if we're on the historico page by looking for historico-specific elements
      const isHistoricoPage = document.getElementById('historico-page') !== null;

      if (isHistoricoPage) {
        // Handle payment edit buttons (only on historico page to avoid conflicts with financeiro.js)
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

        // Handle payment delete buttons (only on historico page to avoid conflicts with financeiro.js)
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
      }
    });
  }

  // Set up event listeners immediately if DOM is ready, otherwise wait for DOMContentLoaded
  if (document.readyState === 'loading' || document.readyState === 'interactive') {
    document.addEventListener('DOMContentLoaded', setupEventListeners);
  } else {
    setupEventListeners();
  }

})(typeof window !== 'undefined' ? window : this);
