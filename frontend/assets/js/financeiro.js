(function (window) {
  'use strict';

  // FINANCEIRO.JS - Generic edit/delete/finish wiring for financial records
  // Requirements (must be present in template/backend):
  // - Rows must have `data-id="<id>"` on the <tr>
  // - Backend API endpoints under /financeiro/api (GET /, GET /<id>, PUT /<id>, DELETE /<id>)

  // Safe feature-detect the shared utilities and api base
  const apiBase = (typeof window !== 'undefined' && window.FINANCEIRO_API_BASE) ? window.FINANCEIRO_API_BASE : '/financeiro/api';
  let financeiroClient = null;
  try {
    if (typeof makeResourceClient === 'function') financeiroClient = makeResourceClient(apiBase);
  } catch (e) {
    console.error('makeResourceClient unavailable:', e);
    financeiroClient = null;
  }

  const domHelpers = (typeof window !== 'undefined' && window.domHelpers) ? window.domHelpers : null;

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

  // Async confirm helper to allow promise-based usage
  // Function to handle the Finalizar button - this is the key functionality
  async function finalizarPagamento(id) {
    if (!id) return console.warn('finalizarPagamento called without id');

    console.log('finalizarPagamento called with id:', id);
    console.log('Button clicked with id:', id);
    getStatusHelper()('Processando...', true);

    // Try to obtain payment data
    let data = null;
    try {
      console.log('Fetching payment data...');
      if (financeiroClient && typeof financeiroClient.get === 'function') {
        console.log('Using financeiroClient.get');
        data = await financeiroClient.get(id);
      } else {
        console.log('Using fetch API');
        const r = await fetch(`/financeiro/api/${id}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
        console.log('Fetch response status:', r.status);
        if (r.ok) {
          data = await r.json();
          console.log('Fetched data:', data);
        } else {
          throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        }
      }
    } catch (err) {
      console.error('Could not fetch payment data:', err);
      getStatusHelper()('Não foi possível concluir a ação. Tente novamente.', false);
      return;
    }

    if (!data || !data.data) {
      console.warn('No data received from API');
      getStatusHelper()('Dados do pagamento não encontrados.', false);
      return;
    }

    // Extract the payment data from the API response
    const paymentData = data.data;
    console.log('Payment data loaded successfully:', paymentData);

    // Build the redirect URL with query parameters
    let redirectUrl = '/financeiro/registrar-pagamento';
    const params = new URLSearchParams();
    
    if (paymentData.data) params.append('data', paymentData.data);
    if (paymentData.cliente && paymentData.cliente.id) params.append('cliente_id', paymentData.cliente.id);
    if (paymentData.artista && paymentData.artista.id) params.append('artista_id', paymentData.artista.id);
    if (paymentData.valor) params.append('valor', paymentData.valor);
    if (paymentData.forma_pagamento) params.append('forma_pagamento', paymentData.forma_pagamento);
    if (paymentData.observacoes) params.append('observacoes', paymentData.observacoes);
    
    redirectUrl += '?' + params.toString();
    console.log('Redirecting to:', redirectUrl);
    
    // Redirect to the registrar_pagamento page with pre-filled data
    window.location.href = redirectUrl;
  }

  async function deletePagamento(id, skipConfirmation = false) {
  console.log('[DEBUG] financeiro.deletePagamento called with id:', id);
  if (!id) return console.warn('deletePagamento called without id');

  if (!skipConfirmation) {
    const confirmed = await window.confirmAction('Tem certeza que deseja excluir este pagamento?');
    console.log('[DEBUG] financeiro.deletePagamento user confirmation:', confirmed);
    if (!confirmed) {
      console.log('[DEBUG] financeiro.deletePagamento cancelled by user');
      return;
    }
  }

  console.log('[DEBUG] financeiro.deletePagamento proceeding with deletion for id:', id);
  getStatusHelper()('Processando...', true);

    try {
      let payload;
      if (financeiroClient && typeof financeiroClient.delete === 'function') {
        payload = await financeiroClient.delete(id);
      } else {
        const headers = { 'Accept': 'application/json' };
        const r = await fetch(`${apiBase}/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });

        // Handle authentication redirects
        if (r.status === 302 || r.status === 401) {
          console.log('financeiro.deletePagamento: Authentication required, redirecting to login');
          getStatusHelper()('Acesso não autorizado. Faça login e tente novamente.', false);
          window.location.href = '/auth/login';
          return;
        }

        const ct = r.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) {
          payload = await r.json();
        } else {
          // non-json (HTML error), read text and surface safe message
          const text = await r.text();
          throw new Error(`Server returned non-JSON response: ${r.status}`);
        }
      }

      if (payload && payload.success) {
        const removed = domHelpers && typeof domHelpers.removeRowById === 'function'
          ? domHelpers.removeRowById('.table-wrapper table', id)
          : false;

        if (!removed) {
          window.location.reload();
          return;
        }

        getStatusHelper()(payload.message || 'Ação concluída com sucesso.', true);
        try { if (typeof closeModal === 'function') closeModal(); } catch(e) {}
      } else {
        const msg = (payload && payload.message) || 'Não foi possível concluir a ação. Tente novamente.';
        getStatusHelper()(msg, false);
      }
    } catch (err) {
      // handle HTML or text responses gracefully
      const msg = (err && err.message) || 'Falha de conexão. Verifique sua internet e tente novamente.';
      getStatusHelper()(msg, false);
      console.error('deletePagamento error', err);
    }
  }

  async function editPagamento(id) {
    if (!id) return console.warn('editPagamento called without id');

    getStatusHelper()('Processando...', true);

    try {
      let res;
      if (financeiroClient && typeof financeiroClient.get === 'function') {
        res = await financeiroClient.get(id);
      } else {
        const r = await fetch(`${apiBase}/${id}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
        const ct = r.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) {
          res = await r.json();
        } else {
          throw new Error('Server returned non-JSON response');
        }
      }

      if (!res || !res.success) {
        const msg = (res && res.message) || 'Erro ao carregar pagamento.';
        getStatusHelper()(msg, false);
        return;
      }

      const p = res.data;

      // Build modal content
      const modalContent = `
        <form id="financeiro-edit-form">
          <label>Data:<br><input type="date" name="data" required></label><br><br>
          <label>Valor:<br><input type="number" step="0.01" name="valor" required></label><br><br>
          <label>Forma de pagamento:<br>
            <select name="forma_pagamento" id="financeiro-edit-forma_pagamento" required>
              <option value="">Selecione...</option>
              <option value="Dinheiro">Dinheiro</option>
              <option value="Pix">Pix</option>
              <option value="Cartão de Crédito">Crédito</option>
              <option value="Cartão de Débito">Débito</option>
              <option value="Outros">Outros</option>
            </select>
          </label><br><br>
          <label>Cliente:<br>
            <select name="cliente_id" id="financeiro-edit-cliente"></select>
          </label><br><br>
          <label>Artista:<br>
            <select name="artista_id" id="financeiro-edit-artista"></select>
          </label><br><br>
          <label>Observações:<br><textarea name="observacoes"></textarea></label><br><br>
        </form>
      `;

      // Use unified modal system
      openCustomModal({
        title: 'Editar Pagamento',
        content: modalContent,
        showConfirm: true,
        showCancel: true,
        confirmText: 'Salvar',
        cancelText: 'Cancelar',
        onConfirm: function() {
          console.log('[DEBUG] financeiro.js onConfirm triggered for payment edit');
          const form = document.querySelector('#financeiro-edit-form');
          if (form) {
            console.log('[DEBUG] Found form, dispatching submit event');
            const submitEvent = new Event('submit', { cancelable: true });
            form.dispatchEvent(submitEvent);
          } else {
            console.error('[DEBUG] Form not found for payment edit');
          }
        },
        onCancel: null,
        closeOnConfirm: false, // Don't close on confirm, let form handler do it
        closeOnCancel: true
      });

      // Get the form after modal is created
      const form = document.querySelector('#financeiro-edit-form');

      // Fill selects from template hidden selects if present
      const tmplCliente = document.getElementById('tmpl_cliente_select');
      const tmplArtista = document.getElementById('tmpl_artista_select');
      const tmplForma = document.getElementById('tmpl_forma_pagamento_select');
      const clienteSelect = form.querySelector('#financeiro-edit-cliente');
      const artistaSelect = form.querySelector('#financeiro-edit-artista');
      const formaSelect = form.querySelector('#financeiro-edit-forma_pagamento');

      if (tmplCliente && clienteSelect) clienteSelect.innerHTML = tmplCliente.innerHTML;
      if (tmplArtista && artistaSelect) artistaSelect.innerHTML = tmplArtista.innerHTML;
      // Use template select if available, otherwise keep the hardcoded options
      if (tmplForma && formaSelect) formaSelect.innerHTML = tmplForma.innerHTML;

      // Prefill values
      form.elements['data'].value = p.data || '';
      form.elements['valor'].value = (p.valor !== null && typeof p.valor !== 'undefined') ? p.valor : '';
      // Prefill forma_pagamento select
      try {
        if (form.elements['forma_pagamento']) form.elements['forma_pagamento'].value = p.forma_pagamento || '';
      } catch (e) {
        console.warn('Could not prefill forma_pagamento select', e);
      }
      if (p.cliente && p.cliente.id) form.elements['cliente_id'].value = p.cliente.id;
      if (p.artista && p.artista.id) form.elements['artista_id'].value = p.artista.id;
      form.elements['observacoes'].value = p.observacoes || '';

      // Set up form submission handler
      form.onsubmit = function (e) {
        e.preventDefault();
        getStatusHelper()('Salvando...', true);
        const formData = new FormData(form);
        // Client-side validation: forma_pagamento must be selected
        const formaVal = formData.get('forma_pagamento');
        const formaEl = form.querySelector('[name="forma_pagamento"]');
        // remove previous error state
        if (formaEl) { formaEl.classList.remove('modal-error'); const prev = form.querySelector('.field-error-msg'); if (prev) prev.remove(); }
        if (!formaVal) {
          getStatusHelper()('Escolha uma forma de pagamento.', false);
          if (formaEl) {
            formaEl.classList.add('modal-error');
            const err = document.createElement('span'); err.className = 'field-error-msg'; err.textContent = 'Escolha uma forma de pagamento.'; formaEl.parentNode.appendChild(err);
            formaEl.focus();
          }
          return;
        }
        const payload = {
          data: formData.get('data') || null,
          valor: formData.get('valor') || null,
          forma_pagamento: formData.get('forma_pagamento') || null,
          cliente_id: formData.get('cliente_id') || null,
          artista_id: formData.get('artista_id') || null,
          observacoes: formData.get('observacoes') || null,
        };

        (async function () {
          try {
            let updated;
            if (financeiroClient && typeof financeiroClient.update === 'function') {
              updated = await financeiroClient.update(id, payload);
            } else {
              const r = await fetch(`${apiBase}/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload),
                credentials: 'same-origin'
              });
              const ct = r.headers.get('Content-Type') || '';
              if (ct.includes('application/json')) {
                updated = await r.json();
              } else {
                throw new Error('Server returned non-JSON response');
              }
            }

            if (updated && updated.success) {
              // Update DOM row if present
              const row = document.querySelector(`tr[data-id='${id}']`);
              if (row) {
                // update relevant columns (data, cliente, artista, valor, forma_pagamento, observacoes)
                const cols = row.querySelectorAll('td');
                // Expect columns: Data, Cliente, Artista, Valor, Forma de pagamento, Observações, Opções
                if (cols && cols.length >= 7) {
                  cols[0].textContent = updated.data.data ? new Date(updated.data.data).toLocaleDateString() : '';
                  // Display "Não informado" when no client is associated (consistent with registration form behavior)
                  cols[1].textContent = (updated.data.cliente && updated.data.cliente.name) ? updated.data.cliente.name : 'Não informado';
                  cols[2].textContent = (updated.data.artista && updated.data.artista.name) ? updated.data.artista.name : '';
                  cols[3].textContent = (typeof updated.data.valor !== 'undefined' && updated.data.valor !== null) ? ('R$ ' + Number(updated.data.valor).toFixed(2)) : '';
                  cols[4].textContent = updated.data.forma_pagamento || '';
                  cols[5].textContent = updated.data.observacoes || '';
                }
              }

              getStatusHelper()(updated.message || 'Pagamento atualizado.', true);
              closeModal();
            } else {
              const msg = (updated && updated.message) || 'Erro ao salvar pagamento.';
              getStatusHelper()(msg, false);
            }
          } catch (err) {
            const msg = (err && err.message) || 'Erro ao salvar pagamento.';
            getStatusHelper()(msg, false);
            console.error('editPagamento save error', err);
          }
        })();
      };

    } catch (err) {
      const msg = (err && err.message) || 'Erro ao carregar pagamento.';
      getStatusHelper()(msg, false);
      console.error('editPagamento error', err);
    }
  }

  function findRowId(el) {
    if (!el) return null;
    // Try navigating up to find the row
    let current = el;
    
    // First log the element we're starting with
    console.log('Finding row ID starting from:', current.tagName, current.className);
    
    // Look for parent tr with data-id
    const tr = current.closest('tr');
    console.log('Found parent tr:', tr ? 'yes' : 'no');
    
    if (tr) {
      // Prefer dataset.id
      if (tr.dataset && tr.dataset.id) {
        // strip common prefixes like 'sess-' or 'com-' if present so callers receive the raw id
        const raw = String(tr.dataset.id);
        const m = raw.match(/^(?:sess|com)-(.+)$/);
        const id = m ? m[1] : raw;
        console.log('Found ID from dataset:', tr.dataset.id, '-> normalized:', id);
        return id;
      }

      // Try attribute
      const attr = tr.getAttribute('data-id');
      if (attr) {
        const raw = String(attr);
        const m = raw.match(/^(?:sess|com)-(.+)$/);
        const id = m ? m[1] : raw;
        console.log('Found ID from attribute:', attr, '-> normalized:', id);
        return id;
      }

      console.log('TR found but no data-id', tr);
    }
    
    // If all else fails, check the button itself
    if (current.dataset && current.dataset.id) {
      return current.dataset.id;
    }
    
    console.log('No ID found');
    return null;
  }

  // Wire events - check if DOM is already loaded
  function setupEventListeners() {
    console.log('[financeiro] Event delegation handlers bound');

    // Use event delegation to handle dynamically added payment buttons
    document.addEventListener('click', function(e) {
      // Handle payment edit buttons
      const editBtn = e.target.closest('.edit-pagamento-btn');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = editBtn.dataset.id || editBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[financeiro] No data-id found for payment edit button');
          return;
        }
        editPagamento(id);
        return;
      }

      // Handle payment delete buttons
      const delBtn = e.target.closest('.delete-pagamento-btn');
      if (delBtn) {
        // Check if we're on the historico page - if so, let historico.js handle it
        const isHistoricoPage = document.getElementById('historico-page') !== null;
        if (isHistoricoPage) {
          console.log('[financeiro] Skipping delete button on historico page - let historico.js handle it');
          return;
        }

        e.preventDefault();
        e.stopPropagation();
        const id = delBtn.dataset.id || delBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[financeiro] No data-id found for payment delete button');
          return;
        }
        deletePagamento(id);
        return;
      }

      // Handle finish buttons (legacy support)
      const finishBtn = e.target.closest('.finish-btn');
      if (finishBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = finishBtn.dataset.id || finishBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[financeiro] No data-id found for finish button');
          return;
        }
        finalizarPagamento(id);
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
  window.financeiroClient = financeiroClient;
  window.financeiroHelpers = { deletePagamento, editPagamento, finalizarPagamento };

})(typeof window !== 'undefined' ? window : this);
