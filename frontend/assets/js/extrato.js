// extrato.js
// Handler for extrato.html - fetches extrato data and shows result in a modal
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('extrato-form');
  if (!form) return;

  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  function createResultModalIfNeeded() {
    let modal = document.getElementById('extrato-result-modal');
    if (modal) return modal;

    // Build modal markup reusing project classes for consistency
    modal = document.createElement('div');
    modal.id = 'extrato-result-modal';
    modal.innerHTML = `
      <div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="extrato-result-title">
        <div class="modal-container" tabindex="-1">
          <div class="modal-scrollable">
            <h2 id="extrato-result-title">Extrato Mensal</h2>
            <div id="extrato-result-content" aria-live="polite" class="box"></div>
          </div>
          <div class="modal-footer">
            <button type="button" id="extrato-close-btn" class="button">Fechar</button>
            <button type="button" id="extrato-new-btn" class="button primary">Nova consulta</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Close handling
    const closeBtn = modal.querySelector('#extrato-close-btn');
    const newBtn = modal.querySelector('#extrato-new-btn');

    closeBtn.addEventListener('click', function () { modal.remove(); });

    // Nova consulta: reset form, focus month select and remove modal
    newBtn.addEventListener('click', function () {
      const formEl = document.getElementById('extrato-form');
      if (formEl) {
        try { formEl.reset(); } catch (e) { /* ignore */ }
      }
      const first = document.getElementById('mes');
      if (first) first.focus();
      modal.remove();
    });

    // Keyboard accessibility: close on ESC; trap focus minimally by focusing container
    modal.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { modal.remove(); }
    });

    return modal;
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('pt-BR');
    } catch (e) {
      return dateStr;
    }
  }

  function formatTime(timeStr) {
    if (!timeStr) return 'N/A';
    try {
      return timeStr.substring(0, 5); // HH:MM format
    } catch (e) {
      return timeStr;
    }
  }

  function renderPagamentosTable(pagamentos) {
    if (!pagamentos || pagamentos.length === 0) {
      return '<p><strong>Nenhum pagamento encontrado.</strong></p>';
    }

    let html = '<h3>Pagamentos</h3><div class="table-wrapper"><table><thead><tr>';
    html += '<th>Data</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Forma Pagamento</th></tr></thead><tbody>';

    pagamentos.forEach(p => {
      html += '<tr>';
      html += `<td>${formatDate(p.data)}</td>`;
      html += `<td>${p.cliente_name || 'N/A'}</td>`;
      html += `<td>${p.artista_name || 'N/A'}</td>`;
      html += `<td>${nf.format(p.valor || 0)}</td>`;
      html += `<td>${p.forma_pagamento || 'N/A'}</td>`;
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
  }

  function renderSessoesTable(sessoes) {
    if (!sessoes || sessoes.length === 0) {
      return '<h3>Sessões</h3><p><strong>Nenhuma sessão encontrada.</strong></p>';
    }

    let html = '<h3>Sessões</h3><div class="table-wrapper"><table><thead><tr>';
    html += '<th>Data</th><th>Hora</th><th>Cliente</th><th>Artista</th><th>Valor</th><th>Status</th></tr></thead><tbody>';

    sessoes.forEach(s => {
      html += '<tr>';
      html += `<td>${formatDate(s.data)}</td>`;
      html += `<td>${formatTime(s.hora)}</td>`;
      html += `<td>${s.cliente_name || 'N/A'}</td>`;
      html += `<td>${s.artista_name || 'N/A'}</td>`;
      html += `<td>${nf.format(s.valor || 0)}</td>`;
      html += `<td>${s.status || 'N/A'}</td>`;
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
  }

  function renderComissoesTable(comissoes) {
    if (!comissoes || comissoes.length === 0) {
      return '<h3>Comissões</h3><p><strong>Nenhuma comissão encontrada.</strong></p>';
    }

    let html = '<h3>Comissões</h3><div class="table-wrapper"><table><thead><tr>';
    html += '<th>Data</th><th>Artista</th><th>Cliente</th><th>Valor do Pagamento</th><th>Percentual</th><th>Comissão (R$)</th><th>Observações</th></tr></thead><tbody>';

    comissoes.forEach(c => {
      html += '<tr>';
      html += `<td>${formatDate(c.created_at)}</td>`;
      html += `<td>${c.artista_name || 'N/A'}</td>`;
      html += `<td>${c.cliente_name || 'N/A'}</td>`;
      html += `<td>${nf.format(c.pagamento_valor || 0)}</td>`;
      html += `<td>${(c.percentual || 0).toFixed(1)}%</td>`;
      html += `<td>${nf.format(c.valor || 0)}</td>`;
      html += `<td>${c.observacoes || ''}</td>`;
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
  }

  function renderGastosTable(gastos) {
    if (!gastos || gastos.length === 0) {
      return '<h3>Gastos</h3><p><strong>Nenhum gasto encontrado.</strong></p>';
    }

    let html = '<h3>Gastos</h3><div class="table-wrapper"><table><thead><tr>';
    html += '<th>Data</th><th>Valor</th><th>Descrição</th><th>Forma Pagamento</th></tr></thead><tbody>';

    gastos.forEach(g => {
      html += '<tr>';
      html += `<td>${formatDate(g.data)}</td>`;
      html += `<td>${nf.format(g.valor || 0)}</td>`;
      html += `<td>${g.descricao || ''}</td>`;
      html += `<td>${g.forma_pagamento || 'N/A'}</td>`;
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
  }

  function renderTotais(totais) {
    if (!totais) return '<h3>Resumo Geral</h3><p>Dados não disponíveis.</p>';

    let html = '<h3>Resumo Geral</h3>';
    html += `<p><strong>Receita Total:</strong> ${nf.format(totais.receita_total || 0)}</p>`;
    html += `<p><strong>Comissões Total:</strong> ${nf.format(totais.comissoes_total || 0)}</p>`;
    if (typeof totais.despesas_total !== 'undefined') {
      html += `<p><strong>Despesas (Gastos):</strong> ${nf.format(totais.despesas_total || 0)}</p>`;
    }
    if (typeof totais.saldo !== 'undefined') {
      html += `<p><strong>Saldo (Receita - Despesas):</strong> ${nf.format(totais.saldo || 0)}</p>`;
    }

    return html;
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const mesEl = document.getElementById('mes');
    const anoEl = document.getElementById('ano');
    
    if (!mesEl || !anoEl) return;

    const mes = mesEl.value;
    const ano = anoEl.value;

    if (!mes || !ano) {
      const modalErr = createResultModalIfNeeded();
      modalErr.querySelector('#extrato-result-content').innerHTML = '<p>Por favor, selecione o mês e o ano.</p>';
      modalErr.querySelector('.modal-container').focus();
      return;
    }

    // Show loading state
    const modal = createResultModalIfNeeded();
    const content = modal.querySelector('#extrato-result-content');
    content.innerHTML = '<p>Carregando extrato...</p>';
    modal.querySelector('.modal-container').focus();

    try {
      // Fetch extrato data from the API
      const response = await fetch(`/extrato/api?mes=${mes}&ano=${ano}`);
      const result = await response.json();

      if (!result.success) {
        content.innerHTML = `<p><strong>Erro:</strong> ${result.message}</p>`;
        return;
      }

      const data = result.data;
      const modalTitle = modal.querySelector('#extrato-result-title');
      modalTitle.textContent = `Extrato - ${mes}/${ano}`;

      // Build content with all sections
      let html = '';
      html += renderPagamentosTable(data.pagamentos);
      html += renderSessoesTable(data.sessoes);
      html += renderComissoesTable(data.comissoes);

      // Render detailed breakdowns from totais first
      if (data.totais && data.totais.por_artista && data.totais.por_artista.length > 0) {
        html += '<h3>Comissões por Artista</h3><div class="table-wrapper"><table><thead><tr>';
        html += '<th>Artista</th><th>Receita</th><th>Comissão</th></tr></thead><tbody>';
        data.totais.por_artista.forEach(a => {
          html += '<tr>';
          html += `<td>${a.artista || 'N/A'}</td>`;
          html += `<td>${nf.format(a.receita || 0)}</td>`;
          html += `<td>${nf.format(a.comissao || 0)}</td>`;
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }

      if (data.totais && data.totais.por_forma_pagamento && data.totais.por_forma_pagamento.length > 0) {
        html += '<h3>Receita por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';
        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';
        data.totais.por_forma_pagamento.forEach(f => {
          html += '<tr>';
          html += `<td>${f.forma || 'N/A'}</td>`;
          html += `<td>${nf.format(f.total || 0)}</td>`;
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }

      if (data.totais && data.totais.gastos_por_forma_pagamento && data.totais.gastos_por_forma_pagamento.length > 0) {
        html += '<h3>Gastos por Forma de Pagamento</h3><div class="table-wrapper"><table><thead><tr>';
        html += '<th>Forma</th><th>Total</th></tr></thead><tbody>';
        data.totais.gastos_por_forma_pagamento.forEach(f => {
          html += '<tr>';
          html += `<td>${f.forma || 'N/A'}</td>`;
          html += `<td>${nf.format(f.total || 0)}</td>`;
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }

      if (data.totais && data.totais.gastos_por_categoria && data.totais.gastos_por_categoria.length > 0) {
        html += '<h3>Gastos por Categoria</h3><div class="table-wrapper"><table><thead><tr>';
        html += '<th>Categoria</th><th>Total</th></tr></thead><tbody>';
        data.totais.gastos_por_categoria.forEach(c => {
          html += '<tr>';
          html += `<td>${c.categoria || 'Outros'}</td>`;
          html += `<td>${nf.format(c.total || 0)}</td>`;
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }

      // Now render Gastos and main totals summary together at the end
      html += renderGastosTable(data.gastos);
      html += renderTotais(data.totais);

      content.innerHTML = html;

    } catch (error) {
      console.error('Error fetching extrato:', error);
      content.innerHTML = '<p><strong>Erro:</strong> Falha ao carregar dados do extrato.</p>';
    }
  });
});
