// Initialize calculadora - check if DOM is already loaded
function initializeCalculadora() {
  const form = document.getElementById('calculadora-form');
  if (!form) return;

  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  function createResultModalIfNeeded() {
    let modal = document.getElementById('calculadora-result-modal');
    if (modal) return modal;

    // Build modal markup reusing project classes for consistency
    modal = document.createElement('div');
    modal.id = 'calculadora-result-modal';
    modal.innerHTML = `
      <div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="calc-result-title">
        <div class="modal-container" tabindex="-1">
          <div class="modal-scrollable">
            <h2 id="calc-result-title">Resultado da Comissão</h2>
            <div id="calc-result-content" aria-live="polite" class="box"></div>
          </div>
          <div class="modal-footer">
            <button type="button" id="calc-close-btn" class="button">Fechar</button>
            <button type="button" id="calc-new-btn" class="button primary">Novo cálculo</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Close handling
    const closeBtn = modal.querySelector('#calc-close-btn');
    const newBtn = modal.querySelector('#calc-new-btn');

    closeBtn.addEventListener('click', function () { modal.remove(); });

    // Novo cálculo: reset form, focus primary input and remove modal
    newBtn.addEventListener('click', function () {
      const formEl = document.getElementById('calculadora-form');
      if (formEl) {
        try { formEl.reset(); } catch (e) { /* ignore */ }
      }
      const first = document.getElementById('valor-total');
      if (first) first.focus();
      modal.remove();
    });

    // Keyboard accessibility: close on ESC; trap focus minimally by focusing container
    modal.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { modal.remove(); }
    });

    return modal;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    const totalEl = document.getElementById('valor-total');
    const pctEl = document.getElementById('porcentagem');
    if (!totalEl || !pctEl) return;

    const rawTotal = totalEl.value;
    const rawPct = pctEl.value;

    // Parse numbers safely
    const total = parseFloat(String(rawTotal).replace(',', '.')) || 0;
    const pct = parseFloat(String(rawPct).replace(',', '.')) || 0;

    if (total < 0 || pct < 0) {
      const modalErr = createResultModalIfNeeded();
      modalErr.querySelector('#calc-result-content').textContent = 'Valores inválidos.';
      modalErr.querySelector('.modal-container').focus();
      return;
    }

    const comissao = total * (pct / 100);
    const restante = total - comissao;

    const formattedCom = nf.format(comissao);
    const formattedTotal = nf.format(total);
    const formattedRest = nf.format(restante);

    const modal = createResultModalIfNeeded();
    const content = modal.querySelector('#calc-result-content');

    // Inject semantic, styled content following project patterns
    content.innerHTML = `
      <p><strong>Valor total:</strong> ${formattedTotal}</p>
      <p><strong>${pct}%:</strong> ${formattedCom}</p>
      <p><strong>${100 - pct}%:</strong> ${formattedRest}</p>
    `;

    // focus container for accessibility and keyboard users
    const container = modal.querySelector('.modal-container');
    if (container) {
      container.focus();
    }
  });
}

// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  document.addEventListener('DOMContentLoaded', initializeCalculadora);
} else {
  initializeCalculadora();
}
