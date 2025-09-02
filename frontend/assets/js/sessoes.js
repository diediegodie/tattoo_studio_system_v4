(function (window) {
  'use strict';

  // SESSOES.JS - Generic edit/delete wiring for sessions using makeResourceClient & domHelpers
  // Requirements (must be present in template/backend):
  // - Rows must have `data-id="<id>"` on the <tr>
  // - Backend API endpoints under /sessoes/api (GET /, GET /<id>, PUT /<id>, DELETE /<id>)
  // - Optional: window.showStatus(message, isSuccess) helper

  // Safe feature-detect the shared utilities
  let sessoesClient = null;
  try {
    if (typeof makeResourceClient === 'function') sessoesClient = makeResourceClient('/sessoes/api');
  } catch (e) {
    console.error('makeResourceClient unavailable:', e);
    sessoesClient = null;
  }

  const domHelpers = (typeof window !== 'undefined' && window.domHelpers) ? window.domHelpers : null;

  function getStatusHelper() {
  return typeof window.showStatus === 'function' ? window.showStatus : function (msg, ok) { try { if (window.showToast) window.showToast(msg, ok ? 'success' : 'error', 8000); else console.log(msg); } catch(e){ console.log(msg); } };
  }

  // Async confirm helper to allow promise-based usage
  function confirmAction(message) {
    if (typeof window.confirm === 'function') return Promise.resolve(window.confirm(message));
    return Promise.resolve(true);
  }

  async function deleteSessao(id) {
    if (!id) return console.warn('deleteSessao called without id');
    if (!(await confirmAction('Tem certeza que deseja excluir esta sessão?'))) return;

    getStatusHelper()('Excluindo...', true);

    try {
      let res;
      if (sessoesClient && typeof sessoesClient.delete === 'function') {
        res = await sessoesClient.delete(id);
      } else {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
  const headers = { 'Accept': 'application/json' };
  if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
  const r = await fetch(`/sessoes/api/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
  const ct = r.headers.get('Content-Type') || '';
  if (ct.includes('application/json')) res = await r.json(); else res = await r.json().catch(() => ({ success: false, message: 'Resposta inesperada do servidor.' }));
      }

      if (res && res.success) {
        const removed = domHelpers && typeof domHelpers.removeRowById === 'function'
          ? domHelpers.removeRowById('.table-wrapper table', id)
          : false;

        if (!removed) {
          // fallback: reload list
          window.location.reload();
          return;
        }

        getStatusHelper()(res.message || 'Sessão excluída.', true);
      } else {
        const msg = (res && res.message) || 'Erro ao excluir sessão.';
        getStatusHelper()(msg, false);
      }
    } catch (err) {
      const msg = (err && err.message) || 'Erro ao excluir sessão.';
      getStatusHelper()(msg, false);
      console.error('deleteSessao error', err);
    }
  }

  async function editSessao(id) {
    if (!id) return console.warn('editSessao called without id');

    console.log('editSessao called with id:', id);
    getStatusHelper()('Carregando dados da sessão...', true);

    // Try to obtain session data
    let data = null;
    try {
      console.log('Fetching session data...');
      if (sessoesClient && typeof sessoesClient.get === 'function') {
        console.log('Using sessoesClient.get');
        data = await sessoesClient.get(id);
      } else {
        console.log('Using fetch API');
        const r = await fetch(`/sessoes/api/${id}`, { headers: { 'Accept': 'application/json' } });
        console.log('Fetch response status:', r.status);
        if (r.ok) {
          data = await r.json();
          console.log('Fetched data:', data);
        } else {
          throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        }
      }
    } catch (err) {
      console.error('Could not fetch session data:', err);
      getStatusHelper()('Erro ao carregar dados da sessão.', false);
      return;
    }

    if (!data) {
      console.warn('No data received from API');
      getStatusHelper()('Dados da sessão não encontrados.', false);
      return;
    }

    // Extract the actual session data from the API response
    const sessionData = data.data || data; // Handle both wrapped and unwrapped responses
    console.log('Session data loaded successfully:', sessionData);

    // Build or reuse a modal
    let modal = document.getElementById('sessoes-edit-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'sessoes-edit-modal';
      modal.innerHTML = `
        <div class="modal-overlay">
          <div class="modal-container">
            <div class="modal-scrollable">
              <h2>Editar Sessão</h2>
              <form id="sessoes-edit-form">
                <label>Data:<br><input type="date" name="data" required></label><br><br>
                <label>Hora:<br><input type="time" name="hora" required></label><br><br>
                <label>Cliente:<br><select name="cliente_id" id="modal_cliente_id" required></select></label><br><br>
                <label>Artista:<br><select name="artista_id" id="modal_artista_id" required></select></label><br><br>
                <label>Valor:<br><input type="number" step="0.01" name="valor" required></label><br><br>
                <label>Observações:<br><textarea name="observacoes"></textarea></label><br><br>
              </form>
            </div>
            <div class="modal-footer">
              <button type="submit" form="sessoes-edit-form" class="button primary">Salvar</button>
              <button type="button" id="sessoes-cancel-edit" class="button">Cancelar</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    // Populate form using server-rendered select templates so names are shown
    const form = modal.querySelector('#sessoes-edit-form');
    console.log('Form element found:', form);
    
    try {
      // Clone server-rendered select options into modal selects
      const tmplCliente = document.getElementById('tmpl_cliente_select');
      const tmplArtista = document.getElementById('tmpl_artista_select');
      const modalCliente = form.querySelector('#modal_cliente_id');
      const modalArtista = form.querySelector('#modal_artista_id');
      
      console.log('Template elements:', { tmplCliente, tmplArtista });
      console.log('Modal elements:', { modalCliente, modalArtista });
      
      if (tmplCliente && modalCliente) {
        modalCliente.innerHTML = tmplCliente.innerHTML;
        console.log('Cliente options cloned');
      } else {
        console.warn('Missing cliente template or modal element');
      }
      
      if (tmplArtista && modalArtista) {
        modalArtista.innerHTML = tmplArtista.innerHTML;
        console.log('Artista options cloned');
      } else {
        console.warn('Missing artista template or modal element');
      }

      // Populate form fields with fetched data
      console.log('Populating form fields with data:', sessionData);
      
      const dateField = form.querySelector('[name="data"]');
      const timeField = form.querySelector('[name="hora"]');
      const valueField = form.querySelector('[name="valor"]');
      const obsField = form.querySelector('[name="observacoes"]');
      
      console.log('Form fields found:', { dateField, timeField, valueField, obsField });
      
      if (dateField) dateField.value = sessionData.data || '';
      if (timeField) timeField.value = sessionData.hora || '';
      if (valueField) valueField.value = sessionData.valor || '';
      if (obsField) obsField.value = sessionData.observacoes || '';

      // Set dropdown selections
      // sessionData.cliente and sessionData.artista may be objects with id/name
      const clientId = sessionData.cliente ? sessionData.cliente.id : (sessionData.cliente_id || '');
      const artistId = sessionData.artista ? sessionData.artista.id : (sessionData.artista_id || '');
      
      console.log('Setting dropdown values:', { clientId, artistId });
      
      if (clientId && modalCliente) {
        modalCliente.value = clientId;
        console.log('Set cliente_id to:', clientId, 'actual value:', modalCliente.value);
      }
      if (artistId && modalArtista) {
        modalArtista.value = artistId;
        console.log('Set artista_id to:', artistId, 'actual value:', modalArtista.value);
      }
      
    } catch (e) {
      console.error('Failed to populate modal selects', e);
      getStatusHelper()('Erro ao popular campos do formulário.', false);
    }

    // Focus management: show and focus first input
    const firstInput = modal.querySelector('input, textarea, select, button');
    setTimeout(() => { if (firstInput) firstInput.focus(); }, 100);
    
    const cancelBtn = modal.querySelector('#sessoes-cancel-edit');
    cancelBtn.onclick = function () { modal.remove(); };

    form.onsubmit = function (e) {
      e.preventDefault();
      getStatusHelper()('Salvando alterações...', true);
      const data = new FormData(form);
      // Client-side validation: ensure forma_pagamento is selected
      const formaVal = data.get('forma_pagamento');
      const formaEl = form.querySelector('[name="forma_pagamento"]');
      if (formaEl) { formaEl.classList.remove('modal-error'); const prev = form.querySelector('.field-error-msg'); if (prev) prev.remove(); }
      if (!formaVal) {
        // Use the shared status helper for consistent UX
        getStatusHelper()('Escolha uma forma de pagamento.', false);
        if (formaEl) {
          formaEl.classList.add('modal-error');
          const err = document.createElement('span'); err.className = 'field-error-msg'; err.textContent = 'Escolha uma forma de pagamento.'; formaEl.parentNode.appendChild(err);
          formaEl.focus();
        }
        return;
      }

      const params = new URLSearchParams();
      for (const [k, v] of data.entries()) params.append(k, v);

      // Build payload for PUT
      const fd = data;
      const payload = {
        data: fd.get('data'),
        hora: fd.get('hora'),
        cliente_id: parseInt(fd.get('cliente_id'), 10) || null,
        artista_id: parseInt(fd.get('artista_id'), 10) || null,
        valor: parseFloat(fd.get('valor')) || 0,
        observacoes: fd.get('observacoes') || ''
      };

      console.log('Submitting payload:', payload);

      (async function () {
        try {
          let res;
          if (sessoesClient && typeof sessoesClient.update === 'function') {
            res = await sessoesClient.update(id, payload);
          } else {
            const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;
            const headers = { 'Content-Type': 'application/json' };
            if (csrf) { headers['X-CSRFToken'] = csrf; headers['X-CSRF-Token'] = csrf; }
            const r = await fetch(`/sessoes/api/${id}`, { 
              method: 'PUT', 
              headers: headers,
              credentials: 'same-origin',
              body: JSON.stringify(payload) 
            });
            
            if (!r.ok) {
              throw new Error(`HTTP ${r.status}: ${r.statusText}`);
            }
            const ct = r.headers.get('Content-Type') || '';
            if (ct.includes('application/json')) res = await r.json(); else res = await r.json().catch(() => ({ success: false, message: 'Resposta inesperada do servidor.' }));
          }

          if (res && res.success) {
            getStatusHelper()(res.message || 'Sessão atualizada com sucesso.', true);
            modal.remove();
            // reload page to reflect changes
            setTimeout(() => window.location.reload(), 1000);
          } else {
            const msg = (res && res.message) || 'Erro ao salvar sessão.';
            getStatusHelper()(msg, false);
          }
        } catch (err) {
          const msg = (err && err.message) || 'Erro ao salvar sessão.';
          getStatusHelper()(msg, false);
          console.error('editSessao error', err);
        }
      })();
    };
  }

  // Function to handle the Finalizar button - call server to finalize, then follow server redirect
  async function finalizarSessao(button) {
    // Get data from button data attributes
    const id = button.dataset.id;
    const data = button.dataset.data;
    const clienteId = button.dataset.clienteId;
    const artistaId = button.dataset.artistaId;
    const valor = button.dataset.valor;
    const observacoes = button.dataset.observacoes;

    console.log('finalizarSessao called with data:', { id, data, clienteId, artistaId, valor, observacoes });

    const statusHelper = getStatusHelper();
    statusHelper('Finalizando sessão...', true);

    try {
      if (!id) throw new Error('Sessão inválida (sem id)');

      const endpoint = `/sessoes/finalizar/${encodeURIComponent(id)}`;

      // Try to read CSRF token from meta tag if present (common patterns)
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || null;

      const headers = {};
      if (csrfToken) {
        // Add common header names for various CSRF setups
        headers['X-CSRFToken'] = csrfToken;
        headers['X-CSRF-Token'] = csrfToken;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin', // include session cookie
        headers: headers,
        redirect: 'follow',
      });

      if (!res) throw new Error('No response from server');

      // If server returned an error status, surface it
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        console.error('finalizarSessao: server error', res.status, text);
        statusHelper('Erro ao finalizar sessão.', false);
        return;
      }

      // Use the final response URL after redirects (Flask redirects to registrar_pagamento)
      const finalUrl = res.url || res.headers.get('Location');
      console.log('finalizarSessao: server responded, navigating to', finalUrl, 'redirected=', res.redirected);

      if (finalUrl) {
        window.location.href = finalUrl;
      } else {
        // Fallback to known page
        window.location.href = '/financeiro/registrar-pagamento';
      }
    } catch (err) {
      console.error('finalizarSessao error', err);
      statusHelper('Erro ao finalizar sessão.', false);
    }
  }

  function findRowId(el) {
    if (!el) return null;
    const tr = el.closest('tr');
    if (!tr) return null;
    // Prefer dataset.id
    if (tr.dataset && tr.dataset.id) return tr.dataset.id;
    // Try attribute
    const attr = tr.getAttribute('data-id') || tr.getAttribute('data-id');
    if (attr) return attr;
    return null;
  }

  // Wire events on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM loaded, setting up event handlers');
    // Attach handlers to finish/edit/delete buttons if present
    document.querySelectorAll('.options-actions').forEach(span => {
      const finishBtn = span.querySelector('.finish-btn');
      const editBtn = span.querySelector('.edit-btn') || span.querySelector('button:nth-child(1)');
      const delBtn = span.querySelector('.delete-btn') || span.querySelector('button:nth-child(2)');

      if (finishBtn) {
        finishBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          e.preventDefault();
          console.log('Finalizar button clicked with data-attributes:', this.dataset);
          finalizarSessao(this);
        });
      }

      if (editBtn) editBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        const id = findRowId(this) || this.dataset.id;
        if (!id) return console.warn('No data-id found for this row. Add data-id to <tr> in template.');
        editSessao(id);
      });

      if (delBtn) delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        const id = findRowId(this) || this.dataset.id;
        if (!id) return console.warn('No data-id found for this row. Add data-id to <tr> in template.');
        deleteSessao(id);
      });
    });
  });

  // Expose for debugging
  window.sessoesClient = sessoesClient;
  window.sessoesHelpers = { deleteSessao, editSessao, finalizarSessao };

})(typeof window !== 'undefined' ? window : this);
