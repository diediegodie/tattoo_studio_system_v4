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
  async function deleteSessao(id) {
  console.log('[DEBUG] sessoes.deleteSessao called with id:', id);
  if (!id) return console.warn('deleteSessao called without id');

  const confirmed = await window.confirmAction('Tem certeza que deseja excluir esta sessão?');
  console.log('[DEBUG] sessoes.deleteSessao user confirmation:', confirmed);
  if (!confirmed) {
    console.log('[DEBUG] sessoes.deleteSessao cancelled by user');
    return;
  }

  console.log('[DEBUG] sessoes.deleteSessao proceeding with deletion for id:', id);
  getStatusHelper()('Processando...', true);

    try {
      let res;
      if (sessoesClient && typeof sessoesClient.delete === 'function') {
        res = await sessoesClient.delete(id);
      } else {
        const headers = { 'Accept': 'application/json' };
        const r = await fetch(`/sessoes/api/${id}`, { method: 'DELETE', headers: headers, credentials: 'same-origin' });
        const ct = r.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) res = await r.json(); else res = await r.json().catch(() => ({ success: false, message: 'Resposta inesperada do servidor.' }));
      }

      if (res && res.success) {
        const removed = domHelpers && typeof domHelpers.removeRowById === 'function'
          ? domHelpers.removeRowById('.table-wrapper table', `sess-${id}`)
          : false;

        if (!removed) {
          // fallback: reload list
          window.location.reload();
          return;
        }

        getStatusHelper()(res.message || 'Ação concluída com sucesso.', true);
        // Close the unified modal
        try { if (typeof closeModal === 'function') closeModal(); } catch(e) {}
      } else {
        const msg = (res && res.message) || 'Não foi possível concluir a ação. Tente novamente.';
        getStatusHelper()(msg, false);
      }
    } catch (err) {
      const msg = (err && err.message) || 'Falha de conexão. Verifique sua internet e tente novamente.';
      getStatusHelper()(msg, false);
      console.error('deleteSessao error', err);
    }
  }

  async function editSessao(id) {
    if (!id) return console.warn('editSessao called without id');

    console.log('editSessao called with id:', id);
    getStatusHelper()('Processando...', true);

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
      getStatusHelper()('Não foi possível concluir a ação. Tente novamente.', false);
      return;
    }

    if (!data) {
      console.warn('No data received from API');
      getStatusHelper()('Dados da sessão não encontrados.', false);
      return;
    }

    // Extract the actual session data from the API response
    const sessionData = data.data || data; // Handle both wrapped and unwrapped responses
    console.log('[DEBUG] Session data loaded successfully:', sessionData);

        // Build or reuse a modal using unified modal system
    const formContent = `
      <form id="sessoes-edit-form">
        <label>Data:<br><input type="date" name="data" required></label><br><br>
        <label>Cliente:<br><select name="cliente_id" id="modal_cliente_id" required></select></label><br><br>
        <label>Artista:<br><select name="artista_id" id="modal_artista_id" required></select></label><br><br>
        <label>Valor:<br><input type="number" step="0.01" name="valor" required></label><br><br>
        <label>Observações:<br><textarea name="observacoes"></textarea></label><br><br>
      </form>
    `;

    // Open modal with custom content
    openCustomModal({
      title: 'Editar Sessão',
      content: formContent,
      confirmText: 'Salvar',
      cancelText: 'Cancelar',
      onConfirm: async function() {
        const form = document.getElementById('sessoes-edit-form');
        if (!form) return;

        getStatusHelper()('Salvando alterações...', true);
        const data = new FormData(form);
        
        // Client-side validation: ensure required fields are present
        const requiredFields = ['data', 'cliente_id', 'artista_id', 'valor'];
        for (const fieldName of requiredFields) {
          const fieldEl = form.querySelector(`[name="${fieldName}"]`);
          if (fieldEl && (!data.get(fieldName) || data.get(fieldName).trim() === '')) {
            getStatusHelper()(`Campo ${fieldName} é obrigatório.`, false);
            if (fieldEl) {
              fieldEl.classList.add('modal-error');
              const err = document.createElement('span'); 
              err.className = 'field-error-msg'; 
              err.textContent = `Campo ${fieldName} é obrigatório.`; 
              fieldEl.parentNode.appendChild(err);
              fieldEl.focus();
            }
            return;
          }
        }

        const params = new URLSearchParams();
        for (const [k, v] of data.entries()) params.append(k, v);

        // Build payload for PUT
        const fd = data;
        const payload = {
          data: fd.get('data'),
          cliente_id: parseInt(fd.get('cliente_id'), 10) || null,
          artista_id: parseInt(fd.get('artista_id'), 10) || null,
          valor: parseFloat(fd.get('valor')) || 0,
          observacoes: fd.get('observacoes') || ''
        };

        console.log('[DEBUG] Submitting payload:', payload);

        // Debug: Log the actual request details
        console.log('[DEBUG] Sending PUT request to:', `/sessoes/api/${id}`);
        console.log('[DEBUG] Payload keys:', Object.keys(payload));

        try {
          let res;
          if (sessoesClient && typeof sessoesClient.update === 'function') {
            res = await sessoesClient.update(id, payload);
          } else {
            const headers = { 'Content-Type': 'application/json' };
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
            closeModal();
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
      },
      onCancel: function() {
        // Clear any error states
        const form = document.getElementById('sessoes-edit-form');
        if (form) {
          form.querySelectorAll('.modal-error').forEach(el => el.classList.remove('modal-error'));
          form.querySelectorAll('.field-error-msg').forEach(el => el.remove());
        }
      }
    });

    // Wait for modal to be rendered, then populate form
    setTimeout(() => {
      const form = document.getElementById('sessoes-edit-form');
      if (!form) return;

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
        console.log('[DEBUG] Populating form fields with data:', sessionData);
        
        const dateField = form.querySelector('[name="data"]');
        const valueField = form.querySelector('[name="valor"]');
        const obsField = form.querySelector('[name="observacoes"]');
        
        console.log('[DEBUG] Form fields found:', { dateField, valueField, obsField });
        
        if (dateField) dateField.value = sessionData.data || '';
        if (valueField) valueField.value = sessionData.valor || '';
        if (obsField) obsField.value = sessionData.observacoes || '';

        // Set dropdown selections
        // sessionData.cliente and sessionData.artista may be objects with id/name
        const clientId = sessionData.cliente ? sessionData.cliente.id : (sessionData.cliente_id || '');
        const artistId = sessionData.artista ? sessionData.artista.id : (sessionData.artista_id || '');
        
        console.log('[DEBUG] Setting dropdown values:', { clientId, artistId });
        
        if (clientId && modalCliente) {
          modalCliente.value = clientId;
          console.log('[DEBUG] Set cliente_id to:', clientId, 'actual value:', modalCliente.value);
        }
        if (artistId && modalArtista) {
          modalArtista.value = artistId;
          console.log('[DEBUG] Set artista_id to:', artistId, 'actual value:', modalArtista.value);
        }
        
      } catch (e) {
        console.error('Failed to populate modal selects', e);
        getStatusHelper()('Erro ao popular campos do formulário.', false);
      }
    }, 100);
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

      const headers = { 'Accept': 'application/json' };

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
    if (tr.dataset && tr.dataset.id) {
      const raw = String(tr.dataset.id);
      const m = raw.match(/^(?:sess|com)-(.+)$/);
      return m ? m[1] : raw;
    }
    // Try attribute
    const attr = tr.getAttribute('data-id') || tr.getAttribute('data-id');
    if (attr) {
      const raw = String(attr);
      const m = raw.match(/^(?:sess|com)-(.+)$/);
      return m ? m[1] : raw;
    }
    return null;
  }

  // Wire events on DOMContentLoaded - Use event delegation for dynamic buttons
  // Set up event listeners - check if DOM is already loaded
  function setupEventListeners() {
    console.log('[sessoes] Event delegation handlers bound');

    // Use event delegation to handle dynamically added session buttons
    document.addEventListener('click', function(e) {
      // Handle session edit buttons
      const editBtn = e.target.closest('.edit-sessao-btn');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = editBtn.dataset.id || editBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[sessoes] No data-id found for edit button');
          return;
        }
        editSessao(id);
        return;
      }

      // Handle session delete buttons
      const delBtn = e.target.closest('.delete-sessao-btn');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = delBtn.dataset.id || delBtn.getAttribute('data-id');
        if (!id) {
          console.warn('[sessoes] No data-id found for delete button');
          return;
        }
        deleteSessao(id);
        return;
      }

      // Handle finish buttons (legacy support)
      const finishBtn = e.target.closest('.finish-btn');
      if (finishBtn) {
        e.preventDefault();
        e.stopPropagation();
        finalizarSessao(finishBtn);
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
  window.sessoesClient = sessoesClient;
  window.sessoesHelpers = { deleteSessao, editSessao, finalizarSessao };

})(typeof window !== 'undefined' ? window : this);
