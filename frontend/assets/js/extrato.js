// Initialize extrato - check if DOM is already loaded// Initialize extrato - check if DOM is already loaded

function initializeExtrato() {function init    let html = '<h3>Sessões</h3><div class="table-wrapper"><table><thead><tr>';

  const form = document.getElementById('extrato-form');    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Status</th></tr></thead><tbody>';

  if (!form) return;

    sessoes.forEach(s => {

  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });      html += '<tr>';

      html += `<td>${formatDate(s.data)}</td>`;

  function createResultModalIfNeeded() {      html += `<td>${s.cliente_name || 'N/A'}</td>`;

    let modal = document.getElementById('extrato-result-modal');      html += `<td>${s.artista_name || 'N/A'}</td>`;

    if (modal) return modal;      html += `<td>${nf.format(s.valor || 0)}</td>`;

      html += `<td>${s.status || 'N/A'}</td>`;

    // Build modal markup reusing project classes for consistency      html += '</tr>';o() {

    modal = document.createElement('div');  const form = document.getElementById('extrato-form');

    modal.id = 'extrato-result-modal';  if (!form) return;

    modal.innerHTML = `

      <div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="extrato-result-title">  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

        <div class="modal-container" tabindex="-1">

          <div class="modal-scrollable">  function showResultModal(title, content, onNewQuery = null) {

            <h2 id="extrato-result-title">Extrato Mensal</h2>    // Use unified modal system

            <div id="extrato-result-content" aria-live="polite" class="box"></div>    openModal({

          </div>      title: title,

          <div class="modal-footer">      body: content,

            <button type="button" id="extrato-close-btn" class="button">Fechar</button>      showConfirm: !!onNewQuery,

            <button type="button" id="extrato-new-btn" class="button primary">Nova consulta</button>      showCancel: true,

          </div>      confirmText: 'Nova consulta',

        </div>      cancelText: 'Fechar',

      </div>      onConfirm: onNewQuery,

    `;      onCancel: null,

      closeOnCancel: true,

    document.body.appendChild(modal);      closeOnConfirm: true

    });

    // Close handling  }

    const closeBtn = modal.querySelector('#extrato-close-btn');

    const newBtn = modal.querySelector('#extrato-new-btn');  function formatDate(dateStr) {

    if (!dateStr) return 'N/A';

    closeBtn.addEventListener('click', function () { modal.remove(); });    try {

      return new Date(dateStr).toLocaleDateString('pt-BR');

    // Nova consulta: reset form, focus month select and remove modal    } catch (e) {

    newBtn.addEventListener('click', function () {      return dateStr;

      const formEl = document.getElementById('extrato-form');    }

      if (formEl) {  }

        try { formEl.reset(); } catch (e) { /* ignore */ }

      }  function formatTime(timeStr) {

      const first = document.getElementById('mes');    if (!timeStr) return 'N/A';

      if (first) first.focus();    try {

      modal.remove();      return timeStr.substring(0, 5); // HH:MM format

    });    } catch (e) {

      return timeStr;

    // Keyboard accessibility: close on ESC; trap focus minimally by focusing container    }

    modal.addEventListener('keydown', function (ev) {  }

      if (ev.key === 'Escape') { modal.remove(); }

    });  function renderPagamentosTable(pagamentos) {

    if (!pagamentos || pagamentos.length === 0) {

    return modal;      return '<p><strong>Nenhum pagamento encontrado.</strong></p>';

  }    }



  function formatDate(dateStr) {    let html = '<h3>Pagamentos</h3><div class="table-wrapper"><table><thead><tr>';

    if (!dateStr) return 'N/A';    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Forma Pagamento</th></tr></thead><tbody>';

    try {

      return new Date(dateStr).toLocaleDateString('pt-BR');    pagamentos.forEach(p => {

    } catch (e) {      html += '<tr>';

      return dateStr;      html += `<td>${formatDate(p.data)}</td>`;

    }      html += `<td>${p.cliente_name || 'N/A'}</td>`;

  }      html += `<td>${p.artista_name || 'N/A'}</td>`;

      html += `<td>${nf.format(p.valor || 0)}</td>`;

  function renderPagamentosTable(pagamentos) {      html += `<td>${p.forma_pagamento || 'N/A'}</td>`;

    if (!pagamentos || pagamentos.length === 0) {      html += '</tr>';

      return '<p><strong>Nenhum pagamento encontrado.</strong></p>';    });

    }

    html += '</tbody></table></div>';

    let html = '<h3>Pagamentos</h3><div class="table-wrapper"><table><thead><tr>';    return html;

    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Forma Pagamento</th></tr></thead><tbody>';  }



    pagamentos.forEach(p => {    function renderSessoesTable(sessoes) {

      html += '<tr>';    if (!sessoes || sessoes.length === 0) {

      html += `<td>${formatDate(p.data)}</td>`;      return '<h3>Sessões</h3><p><strong>Nenhuma sessão encontrada.</strong></p>';

      html += `<td>${p.cliente_name || 'N/A'}</td>`;    }

      html += `<td>${p.artista_name || 'N/A'}</td>`;

      html += `<td>${nf.format(p.valor || 0)}</td>`;    let html = '<h3>Sessões</h3><div class="table-wrapper"><table><thead><tr>';

      html += `<td>${p.forma_pagamento || 'N/A'}</td>`;    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Status</th></tr></thead><tbody>';

      html += '</tr>';

    });    sessoes.forEach(s => {

      html += '<tr>';

    html += '</tbody></table></div>';      html += `<td>${formatDate(s.data)}</td>`;

    return html;      html += `<td>${s.cliente_name || 'N/A'}</td>`;

  }      html += `<td>${s.artista_name || 'N/A'}</td>`;

      html += `<td>${nf.format(s.valor || 0)}</td>`;

  function renderSessoesTable(sessoes) {      html += `<td>${s.status || 'N/A'}</td>`;

    if (!sessoes || sessoes.length === 0) {      html += '</tr>';

      return '<h3>Sessões</h3><p><strong>Nenhuma sessão encontrada.</strong></p>';    });

    }

    html += '</tbody></table></div>';

    let html = '<h3>Sessões</h3><div class="table-wrapper"><table><thead><tr>';    return html;

    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Status</th></tr></thead><tbody>';  }



    sessoes.forEach(s => {  function renderComissoesTable(comissoes) {

      html += '<tr>';    if (!comissoes || comissoes.length === 0) {

      html += `<td>${formatDate(s.data)}</td>`;      return '<h3>Comissões</h3><p><strong>Nenhuma comissão encontrada.</strong></p>';

      html += `<td>${s.cliente_name || 'N/A'}</td>`;    }

      html += `<td>${s.artista_name || 'N/A'}</td>`;

      html += `<td>${nf.format(s.valor || 0)}</td>`;    let html = '<h3>Comissões</h3><div class="table-wrapper"><table><thead><tr>';

      html += `<td>${s.status || 'N/A'}</td>`;    html += '<th>Data</th><th>Artista</th><th>Cliente</th><th>Valor do Pagamento</th><th>Percentual</th><th>Comissão (R$)</th><th>Observações</th></tr></thead><tbody>';

      html += '</tr>';

    });    comissoes.forEach(c => {

      html += '<tr>';

    html += '</tbody></table></div>';      html += `<td>${formatDate(c.created_at)}</td>`;

    return html;      html += `<td>${c.artista_name || 'N/A'}</td>`;

  }      html += `<td>${c.cliente_name || 'N/A'}</td>`;

      html += `<td>${nf.format(c.pagamento_valor || 0)}</td>`;

  function renderComissoesTable(comissoes) {      html += `<td>${(c.percentual || 0).toFixed(1)}%</td>`;

    if (!comissoes || comissoes.length === 0) {      html += `<td>${nf.format(c.valor || 0)}</td>`;

      return '<h3>Comissões</h3><p><strong>Nenhuma comissão encontrada.</strong></p>';      html += `<td>${c.observacoes || ''}</td>`;

    }      html += '</tr>';

    });

    let html = '<h3>Comissões</h3><div class="table-wrapper"><table><thead><tr>';

    html += '<th>Data</th><th>Artista</th><th>Cliente</th><th>Valor do Pagamento</th><th>Percentual</th><th>Comissão (R$)</th><th>Observações</th></tr></thead><tbody>';    html += '</tbody></table></div>';

    return html;

    comissoes.forEach(c => {  }

      html += '<tr>';

      html += `<td>${formatDate(c.created_at)}</td>`;  function renderGastosTable(gastos) {

      html += `<td>${c.artista_name || 'N/A'}</td>`;    if (!gastos || gastos.length === 0) {

      html += `<td>${c.cliente_name || 'N/A'}</td>`;      return '<h3>Gastos</h3><p><strong>Nenhum gasto encontrado.</strong></p>';

      html += `<td>${nf.format(c.pagamento_valor || 0)}</td>`;    }

      html += `<td>${(c.percentual || 0).toFixed(1)}%</td>`;

      html += `<td>${nf.format(c.valor || 0)}</td>`;    let html = '<h3>Gastos</h3><div class="table-wrapper"><table><thead><tr>';

      html += `<td>${c.observacoes || ''}</td>`;    html += '<th>Data</th><th>Valor</th><th>Descrição</th><th>Forma Pagamento</th></tr></thead><tbody>';

      html += '</tr>';

    });    gastos.forEach(g => {

      html += '<tr>';

    html += '</tbody></table></div>';      html += `<td>${formatDate(g.data)}</td>`;

    return html;      html += `<td>${nf.format(g.valor || 0)}</td>`;

  }      html += `<td>${g.descricao || ''}</td>`;

      html += `<td>${g.forma_pagamento || 'N/A'}</td>`;

  function renderGastosTable(gastos) {      html += '</tr>';

    if (!gastos || gastos.length === 0) {    });

      return '<h3>Gastos</h3><p><strong>Nenhum gasto encontrado.</strong></p>';

    }    html += '</tbody></table></div>';

    return html;

    let html = '<h3>Gastos</h3><div class="table-wrapper"><table><thead><tr>';  }

    html += '<th>Data</th><th>Valor</th><th>Descrição</th><th>Forma Pagamento</th></tr></thead><tbody>';

  function renderTotais(totais) {

    gastos.forEach(g => {    if (!totais) return '<h3>Resumo Geral</h3><p>Dados não disponíveis.</p>';

      html += '<tr>';

      html += `<td>${formatDate(g.data)}</td>`;    let html = '<h3>Resumo Geral</h3>';

      html += `<td>${nf.format(g.valor || 0)}</td>`;    html += `<p><strong>Receita Total:</strong> ${nf.format(totais.receita_total || 0)}</p>`;

      html += `<td>${g.descricao || ''}</td>`;    html += `<p><strong>Comissões Total:</strong> ${nf.format(totais.comissoes_total || 0)}</p>`;

      html += `<td>${g.forma_pagamento || 'N/A'}</td>`;    if (typeof totais.despesas_total !== 'undefined') {

      html += '</tr>';      html += `<p><strong>Despesas (Gastos):</strong> ${nf.format(totais.despesas_total || 0)}</p>`;

    });    }

    if (typeof totais.saldo !== 'undefined') {

    html += '</tbody></table></div>';      html += `<p><strong>Saldo (Receita - Despesas):</strong> ${nf.format(totais.saldo || 0)}</p>`;

    return html;    }

  }

    return html;

  function renderTotais(totais) {  }

    if (!totais) return '<h3>Resumo Geral</h3><p>Dados não disponíveis.</p>';

  form.addEventListener('submit', async function (e) {

    let html = '<h3>Resumo Geral</h3>';    e.preventDefault();

    html += `<p><strong>Receita Total:</strong> ${nf.format(totais.receita_total || 0)}</p>`;

    html += `<p><strong>Comissões Total:</strong> ${nf.format(totais.comissoes_total || 0)}</p>`;    const mesEl = document.getElementById('mes');

    if (typeof totais.despesas_total !== 'undefined') {    const anoEl = document.getElementById('ano');

      html += `<p><strong>Despesas (Gastos):</strong> ${nf.format(totais.despesas_total || 0)}</p>`;    

    }    if (!mesEl || !anoEl) return;

    if (typeof totais.saldo !== 'undefined') {

      html += `<p><strong>Saldo (Receita - Despesas):</strong> ${nf.format(totais.saldo || 0)}</p>`;    const mes = mesEl.value;

    }    const ano = anoEl.value;



    return html;    if (!mes || !ano) {

  }      showResultModal('Erro', '<p>Por favor, selecione o mês e o ano.</p>');

      return;

  form.addEventListener('submit', async function (e) {    }

    e.preventDefault();

    // Show loading state

    const mesEl = document.getElementById('mes');    showResultModal('Processando...', '<p>Processando...</p>');

    const anoEl = document.getElementById('ano');

        try {

    if (!mesEl || !anoEl) return;      // Fetch extrato data from the API

      const response = await fetch(`/extrato/api?mes=${mes}&ano=${ano}`);

    const mes = mesEl.value;      const result = await response.json();

    const ano = anoEl.value;

      if (!result.success) {

    if (!mes || !ano) {        showResultModal('Erro', `<p><strong>Erro:</strong> ${result.message || 'Não foi possível concluir a ação. Tente novamente.'}</p>`);

      const modalErr = createResultModalIfNeeded();        return;

      modalErr.querySelector('#extrato-result-content').innerHTML = '<p>Por favor, selecione o mês e o ano.</p>';      }

      modalErr.querySelector('.modal-container').focus();

      return;      const data = result.data;

    }      const title = `Extrato - ${mes}/${ano}`;



    // Show loading state      // Build content with all sections

    const modal = createResultModalIfNeeded();      let html = '';

    const content = modal.querySelector('#extrato-result-content');      html += renderPagamentosTable(data.pagamentos);

    content.innerHTML = '<p>Carregando extrato...</p>';      html += renderSessoesTable(data.sessoes);

    modal.querySelector('.modal-container').focus();      html += renderComissoesTable(data.comissoes);



    try {      // Render detailed breakdowns from totais first

      // Fetch extrato data from the API      if (data.totais && data.totais.por_artista && data.totais.por_artista.length > 0) {

      const response = await fetch(`/extrato/api?mes=${mes}&ano=${ano}`);        html += '<h3>Comissões por Artista</h3><div class="table-wrapper"><table><thead><tr>';

      const result = await response.json();        html += '<th>Artista</th><th>Receita</th><th>Comissão</th></tr></thead><tbody>';

        data.totais.por_artista.forEach(a => {

      if (!result.success) {          html += '<tr>';

        content.innerHTML = `<p><strong>Erro:</strong> ${result.message}</p>`;          html += `<td>${a.artista || 'N/A'}</td>`;

        return;          html += `<td>${nf.format(a.receita || 0)}</td>`;

      }          html += `<td>${nf.format(a.comissao || 0)}</td>`;

          html += '</tr>';

      const data = result.data;        });

      const modalTitle = modal.querySelector('#extrato-result-title');        html += '</tbody></table></div>';

      modalTitle.textContent = `Extrato - ${mes}/${ano}`;      }



      // Build content with all sections      if (data.totais && data.totais.por_forma_pagamento && data.totais.por_forma_pagamento.length > 0) {

      let html = '';        html += '<h3>Receita por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';

      html += renderPagamentosTable(data.pagamentos);        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';

      html += renderSessoesTable(data.sessoes);        data.totais.por_forma_pagamento.forEach(f => {

      html += renderComissoesTable(data.comissoes);          html += '<tr>';

          html += `<td>${f.forma || 'N/A'}</td>`;

      // Render detailed breakdowns from totais first          html += `<td>${nf.format(f.total || 0)}</td>`;

      if (data.totais && data.totais.por_artista && data.totais.por_artista.length > 0) {          html += '</tr>';

        html += '<h3>Comissões por Artista</h3><div class="table-wrapper"><table><thead><tr>';        });

        html += '<th>Artista</th><th>Receita</th><th>Comissão</th></tr></thead><tbody>';        html += '</tbody></table></div>';

        data.totais.por_artista.forEach(a => {      }

          html += '<tr>';

          html += `<td>${a.artista || 'N/A'}</td>`;      if (data.totais && data.totais.gastos_por_forma_pagamento && data.totais.gastos_por_forma_pagamento.length > 0) {

          html += `<td>${nf.format(a.receita || 0)}</td>`;        html += '<h3>Gastos por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';

          html += `<td>${nf.format(a.comissao || 0)}</td>`;        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';

          html += '</tr>';        data.totais.gastos_por_forma_pagamento.forEach(f => {

        });          html += '<tr>';

        html += '</tbody></table></div>';          html += `<td>${f.forma || 'N/A'}</td>`;

      }          html += `<td>${nf.format(f.total || 0)}</td>`;

          html += '</tr>';

      if (data.totais && data.totais.por_forma_pagamento && data.totais.por_forma_pagamento.length > 0) {        });

        html += '<h3>Receita por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';        html += '</tbody></table></div>';

        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';      }

        data.totais.por_forma_pagamento.forEach(f => {

          html += '<tr>';      if (data.totais && data.totais.gastos_por_categoria && data.totais.gastos_por_categoria.length > 0) {

          html += `<td>${f.forma || 'N/A'}</td>`;        html += '<h3>Gastos por Categoria</h3><div class="table-wrapper"><table><thead><tr>';

          html += `<td>${nf.format(f.total || 0)}</td>`;        html += '<th>Categoria</th><th>Total</th></tr></thead><tbody>';

          html += '</tr>';        data.totais.gastos_por_categoria.forEach(c => {

        });          html += '<tr>';

        html += '</tbody></table></div>';          html += `<td>${c.categoria || 'Outros'}</td>`;

      }          html += `<td>${nf.format(c.total || 0)}</td>`;

          html += '</tr>';

      if (data.totais && data.totais.gastos_por_forma_pagamento && data.totais.gastos_por_forma_pagamento.length > 0) {        });

        html += '<h3>Gastos por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';        html += '</tbody></table></div>';

        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';      }

        data.totais.gastos_por_forma_pagamento.forEach(f => {

          html += '<tr>';      // Now render Gastos and main totals summary together at the end

          html += `<td>${f.forma || 'N/A'}</td>`;      html += renderGastosTable(data.gastos);

          html += `<td>${nf.format(f.total || 0)}</td>`;      html += renderTotais(data.totais);

          html += '</tr>';

        });      // Define the "Nova consulta" action

        html += '</tbody></table></div>';      const onNewQuery = function() {

      }        const formEl = document.getElementById('extrato-form');

        if (formEl) {

      if (data.totais && data.totais.gastos_por_categoria && data.totais.gastos_por_categoria.length > 0) {          try { formEl.reset(); } catch (e) { /* ignore */ }

        html += '<h3>Gastos por Categoria</h3><div class="table-wrapper"><table><thead><tr>';        }

        html += '<th>Categoria</th><th>Total</th></tr></thead><tbody>';        const first = document.getElementById('mes');

        data.totais.gastos_por_categoria.forEach(c => {        if (first) first.focus();

          html += '<tr>';      };

          html += `<td>${c.categoria || 'Outros'}</td>`;

          html += `<td>${nf.format(c.total || 0)}</td>`;      // Show results with "Nova consulta" button

          html += '</tr>';      showResultModal(title, html, onNewQuery);

        });

        html += '</tbody></table></div>';    } catch (error) {

      }      console.error('Error fetching extrato:', error);

      showResultModal('Erro', '<p><strong>Erro:</strong> Falha de conexão. Verifique sua internet e tente novamente.</p>');

      // Now render Gastos and main totals summary together at the end    }

      html += renderGastosTable(data.gastos);  });

      html += renderTotais(data.totais);}



      content.innerHTML = html;// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded

if (document.readyState === 'loading' || document.readyState === 'interactive') {

    } catch (error) {  document.addEventListener('DOMContentLoaded', initializeExtrato);

      console.error('Error fetching extrato:', error);} else {

      content.innerHTML = '<p><strong>Erro:</strong> Falha ao carregar dados do extrato.</p>';  initializeExtrato();

    }}

  });
}

// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  document.addEventListener('DOMContentLoaded', initializeExtrato);
} else {
  initializeExtrato();
}